#!/usr/bin/env python3
"""
Venus OS D-Bus 2 NMEA Relay Service
This script is designed to run on Venus OS systems, such as those used in Victron Energy products.
It uses the built-in DbusMonitor class for automatic service discovery and robust monitoring.

"""

import os
import sys
import logging
import time
import signal
import threading
import dbus

from Nmea0183Transmitter import Nmea0183Transmitter

# Import victron packages, use locally downloaded copy of latest version of DbusMonitor that supports ignoreServices: https://github.com/victronenergy/velib_python/blob/master/dbusmonitor.py
from velib_python.dbusmonitor import DbusMonitor
from velib_python.settingsdevice import SettingsDevice
from velib_python.vedbus import VeDbusService

# Import GLib for mainloop
try:
    from gi.repository import GLib
    from dbus.mainloop.glib import DBusGMainLoop
except ImportError:
    import gobject as GLib
    from dbus.mainloop.glib import DBusGMainLoop


class Dbus2NmeaRelayService:
    def __init__(self, min_relay_interval=0.5, max_relay_interval=60.0, log_level=logging.INFO):
        # Validate intervals
        if min_relay_interval <= 0.1:
            raise ValueError("min_relay_interval must be greater than 0.1")
        if max_relay_interval <= min_relay_interval:
            raise ValueError("max_relay_interval must be greater than min_relay_interval")

        self.min_relay_interval = min_relay_interval  # Minimum interval to relay data, to prevent flooding
        self.max_relay_interval = max_relay_interval  # Maximum interval to relay data, to keep relay alive

        # Set up logger for this instance with specified log level
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(log_level)

        try:
            self.nmea_transmitter = Nmea0183Transmitter()  # Initialize NMEA transmitter
        except Exception as e:
            self.logger.error(f"Error initializing NMEA transmitter: {e}")
            raise

        # Persistent settings stored in com.victronenergy.settings
        self._settings = SettingsDevice(
            bus=dbus.SystemBus(),
            supportedSettings={
                'SerialPort':     ['/Settings/NmeaTransmitter/SerialPort',     '/dev/ttyACM0',                           0, 0],
                'BatteryService': ['/Settings/NmeaTransmitter/BatteryService', 'com.victronenergy.battery.ttyUSB1', 0, 0],
            },
            eventCallback=self._on_setting_changed
        )

        # Apply persisted serial port immediately
        self.nmea_transmitter.serial_port = self._settings['SerialPort']

        # Battery service filter — updated live when the GUI changes the setting
        self._battery_service = self._settings['BatteryService']
        self.logger.info(f"Monitoring battery service: {self._battery_service}")
        self.logger.info(f"Using serial port: {self.nmea_transmitter.serial_port}")

        # Define what services and paths to monitor using DbusMonitor format
        self.monitor_list = {
            'com.victronenergy.battery': {
                '/Dc/0/Current': {'code': 'current', 'whenToLog': 'always'}
            }
        }

        # Pre-compute expected sensor keys to avoid rebuilding on every get_sensor_data() call
        self._expected_sensors = {
            config['code']
            for paths in self.monitor_list.values()
            for config in paths.values()
        }

        # Cache for sensor data
        self.sensor_data = {}

        # Thread lock for sensor data and shared state
        self.data_lock = threading.Lock()

        # D-Bus monitor will be initialized later
        self.dbusMonitor = None

        # Status service published to D-Bus so the GUI can display live state
        self._dbus_service = None

        # Initialize control variables
        self.running = False
        self.last_relay_time = 0.0

        # Event used to wake the relay thread immediately when data changes,
        # or to signal shutdown. Replaces the data_changed bool + polling sleep.
        self._relay_event = threading.Event()

        # Init relay thread
        self.relay_thread = threading.Thread(target=self._relay_worker)
        self.relay_thread.daemon = True

    def _init_dbus_status_service(self):
        """Publish com.victronenergy.nmeatransmitter for GUI status display."""
        self._dbus_service = VeDbusService(
            'com.victronenergy.nmeatransmitter',
            bus=dbus.SystemBus(),
            register=False
        )
        self._dbus_service.add_path('/Connected',        0, writeable=False)
        self._dbus_service.add_path('/BatteryConnected', 0, writeable=False)
        self._dbus_service.add_path('/LastCurrent',      None, writeable=False)
        self._dbus_service.register()

    def _update_status(self, serial_connected=None, battery_connected=None, last_current=None):
        """Update the D-Bus status paths. Pass None to leave a value unchanged."""
        if self._dbus_service is None:
            return
        if serial_connected is not None:
            self._dbus_service['/Connected'] = 1 if serial_connected else 0
        if battery_connected is not None:
            self._dbus_service['/BatteryConnected'] = 1 if battery_connected else 0
        if last_current is not None:
            self._dbus_service['/LastCurrent'] = last_current

    def start(self):
        """Initialize D-Bus monitor and start the relaying thread"""
        # Open the serial port once for persistent use
        self.nmea_transmitter.open()
        self._update_status(serial_connected=self.nmea_transmitter._serial is not None)

        self._init_dbus_status_service()

        try:
            # Initialize DbusMonitor with our monitor list and callbacks
            self.dbusMonitor = DbusMonitor(
                dbusTree=self.monitor_list,
                valueChangedCallback=self._on_value_changed,
                deviceAddedCallback=self._on_device_added,
                deviceRemovedCallback=self._on_device_removed,
                namespace="com.victronenergy",
            )

            # Initialize sensor data cache with current values
            self._initialize_sensor_cache()

        except Exception as e:
            self.logger.error(f"Error initializing DbusMonitor: {e}")
            raise

        # Start the relaying thread
        try:
            if not self.relay_thread.is_alive():
                self.running = True  # Set running flag before starting thread
                self.relay_thread.start()
                self.logger.info("Relay thread started")
        except Exception as e:
            self.logger.error(f"Error starting relay thread: {e}")
            raise

    def _initialize_sensor_cache(self):
        """Initialize sensor data cache with current values from DbusMonitor"""
        if not self.dbusMonitor:
            return

        with self.data_lock:
            current_time = time.time()

            for service_class, paths in self.monitor_list.items():
                service_list = self.dbusMonitor.get_service_list(classfilter=service_class)
                for path, config in paths.items():
                    sensor_key = config['code']

                    value = None
                    for service_name in service_list:
                        if service_name != self._battery_service:
                            continue
                        value = self.dbusMonitor.get_value(service_name, path)
                        if value is not None:
                            break

                    self.sensor_data[sensor_key] = {
                        'value': value,
                        'timestamp': current_time
                    }
                    self.logger.debug(f"Initialized sensor {sensor_key} with value: {value}")

        battery_connected = any(
            info.get('value') is not None for info in self.sensor_data.values()
        )
        self._update_status(battery_connected=battery_connected)

        self._relay_event.set()
        self.logger.debug(f"Initialized sensor cache with {len(self.sensor_data)} sensors: {list(self.sensor_data.keys())}")

    def _on_device_added(self, service_name, device_instance):
        """Callback when a new device is added to the bus"""
        self.logger.info(f"Device added: {service_name} (instance: {device_instance})")
        self._update_cache_from_service(service_name)

    def _on_device_removed(self, service_name, device_instance):
        """Callback when a device is removed from the bus"""
        self.logger.info(f"Device removed: {service_name} (instance: {device_instance})")
        self._clear_cache_for_service(service_name)

    def _clear_cache_for_service(self, service_name):
        """Clear cached sensor values that were provided by the given service."""
        if service_name != self._battery_service:
            return

        matching_service_class = next(
            (sc for sc in self.monitor_list if service_name.startswith(sc)), None
        )
        if not matching_service_class:
            return

        paths = self.monitor_list[matching_service_class]
        with self.data_lock:
            for config in paths.values():
                sensor_key = config['code']
                if sensor_key in self.sensor_data:
                    self.sensor_data[sensor_key]['value'] = None

        self._update_status(battery_connected=False)
        self.logger.debug(f"Cleared cache for removed service {service_name}")

    def _update_cache_from_service(self, service_name):
        """Update cache with values from a specific service"""
        if not self.dbusMonitor or service_name != self._battery_service:
            return

        matching_service_class = next(
            (sc for sc in self.monitor_list if service_name.startswith(sc)), None
        )
        if not matching_service_class:
            return

        paths = self.monitor_list[matching_service_class]

        with self.data_lock:
            current_time = time.time()
            for path, config in paths.items():
                sensor_key = config['code']
                value = self.dbusMonitor.get_value(service_name, path)

                if value is not None:
                    self.sensor_data[sensor_key] = {
                        'value': value,
                        'timestamp': current_time
                    }

        battery_connected = any(
            info.get('value') is not None for info in self.sensor_data.values()
        )
        self._update_status(battery_connected=battery_connected)
        self._relay_event.set()

    def _on_value_changed(self, service_name, path, options, changes, device_instance):
        """Callback when a monitored value changes"""
        if service_name != self._battery_service:
            return

        if 'Value' not in changes:
            return

        sensor_key = options.get('code')
        if not sensor_key:
            return

        value = changes['Value']
        current_time = time.time()

        with self.data_lock:
            self.sensor_data[sensor_key] = {
                'value': value,
                'timestamp': current_time
            }

        self._relay_event.set()
        self.logger.debug(f"Value changed for {sensor_key}: {value}")

    def _on_setting_changed(self, setting, old_value, new_value):
        """Callback when a GUI-persisted setting changes."""
        self.logger.info(f"Setting changed: {setting} = {new_value!r} (was {old_value!r})")
        if setting == 'BatteryService':
            self._battery_service = new_value
            # Re-init cache to pick up values from the newly selected service
            self._initialize_sensor_cache()
        elif setting == 'SerialPort':
            self.nmea_transmitter.set_port(new_value)
            self._update_status(serial_connected=False)  # will reconnect on next send

    def get_sensor_data(self):
        """Get current sensor values from cache"""
        with self.data_lock:
            data = {}
            for sensor_key, sensor_info in self.sensor_data.items():
                value = sensor_info.get('value')
                data[sensor_key] = value if value is not None else float('nan')

            for sensor_key in self._expected_sensors:
                if sensor_key not in data:
                    data[sensor_key] = float('nan')

        return data

    def _relay_worker(self):
        """Worker thread that relays data"""
        self.last_relay_time = time.time()

        while self.running:
            # Wait until data changes or the max relay interval elapses.
            remaining = self.max_relay_interval - (time.time() - self.last_relay_time)
            self._relay_event.wait(timeout=max(0, remaining))

            if not self.running:
                break

            current_time = time.time()

            # Consume the event before sleeping so any new set() during the
            # rate-limit sleep re-arms it and is not missed.
            self._relay_event.clear()

            # Rate-limit: if the event fired very quickly, sleep the remainder
            # of the minimum interval before sending.
            elapsed = current_time - self.last_relay_time
            if elapsed < self.min_relay_interval:
                time.sleep(self.min_relay_interval - elapsed)
                if not self.running:
                    break
                current_time = time.time()

            data_to_relay = self.get_sensor_data()

            self.logger.debug(f"Relaying data: {data_to_relay}")

            # Send the NMEA sentence using the NMEA transmitter
            try:
                current_value = data_to_relay.get('current', 0)
                # Ensure we have a valid numeric value
                if current_value is None or (isinstance(current_value, float) and current_value != current_value):  # NaN check
                    current_value = 0

                self.nmea_transmitter.send_nmea_sentence(
                    code='PSILTBS', # Silva Nexus Special NMEA Sentence for Target Boat Speed
                    value=current_value,
                    unit='N' # NMEA unit for speed in knots
                )

                serial_open = self.nmea_transmitter._serial is not None and self.nmea_transmitter._serial.is_open
                self._update_status(
                    serial_connected=serial_open,
                    last_current=float(current_value)
                )
            except Exception as e:
                self.logger.error(f"Error sending NMEA sentence: {e}")
                self._update_status(serial_connected=False)

            self.last_relay_time = current_time


    def stop(self):
        """Stop the relaying thread and clean up resources"""
        self.running = False
        # Wake the relay thread so it can check the running flag and exit
        self._relay_event.set()

        if self.relay_thread.is_alive():
            self.relay_thread.join(timeout=5)
            if self.relay_thread.is_alive():
                self.logger.warning("Relay thread did not stop within timeout")

        # Close the serial port
        self.nmea_transmitter.close()

        # Release the DbusMonitor reference (signal receivers are owned by dbus and cleaned up by GC)
        self.dbusMonitor = None

        self.logger.info("Relay service stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger = logging.getLogger('Dbus2NmeaRelayService')
    logger.info(f"Received signal {signum}, shutting down relay service...")
    global relayService
    if 'relayService' in globals() and relayService is not None:
        try:
            relayService.stop()
        except Exception as e:
            logger.error(f"Error stopping relay service: {e}")
    sys.exit(0)

if __name__ == "__main__":
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='D-Bus 2 NMEA Relay Service for Venus OS')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set the logging level (default: INFO)')
    parser.add_argument('--min-interval', type=float, default=0.5,
                        help='Minimum interval to relay data in seconds (default: 0.5)')
    parser.add_argument('--max-interval', type=float, default=60.0,
                        help='Maximum interval to relay data in seconds (default: 60.0)')

    args = parser.parse_args()

    # Convert log level string to logging constant
    log_level = getattr(logging, args.log_level.upper())

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logging.basicConfig(level=log_level, format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s")

    # Initialize relayService to None for signal handler
    relayService = None

    try:
        # Must be set before any D-Bus connections are made (including DbusMonitor init)
        DBusGMainLoop(set_as_default=True)

        relayService = Dbus2NmeaRelayService(
            min_relay_interval=args.min_interval,
            max_relay_interval=args.max_interval,
            log_level=log_level
        )
        mainloop = GLib.MainLoop()

        # Initialize DBusMonitor and start relaying
        relayService.start()

        logging.info('Connected to dbus, and switching over to GLib.MainLoop() (= event based)')
        mainloop.run()

    except Exception as e:
        logging.error(f"Error starting relay service: {e}")
        if relayService:
            relayService.stop()
        sys.exit(1)
    finally:
        logging.info("Mainloop stopped, cleaning up...")
        if relayService:
            relayService.stop()
