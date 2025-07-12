#!/usr/bin/env python3
import logging
import signal
from DbusBatteryReader import DbusBatteryReader
from Nmea0183Transmitter import Nmea0183Transmitter

from gi.repository import GLib # type: ignore
from dbus.mainloop.glib import DBusGMainLoop # type: ignore

nmea_transmitter = Nmea0183Transmitter() # Initialize NMEA transmitter
mainloop = None  # Initialize mainloop variable

def relay_dbus_value():
    """Relay the battery current value from D-Bus to NMEA 0183."""
    try:
        battery_reader = DbusBatteryReader() 
        current = battery_reader.get_batt_current()
        if current is not None:
            nmea_transmitter.send_nmea_sentence(value=current)
            logging.debug(f"Sent NMEA sentence with current value: {current}")
        else:
            logging.error("Failed to read battery current from D-Bus.")
        return True  # Return True to keep the timer running
    except Exception as e:
        logging.error(f"Error relaying D-Bus value: {e}")
        return True  # Return True to keep the timer running even on error

def signal_handler(signum, frame):
    """Handle termination signals to stop the main loop."""
    logging.info(f"Received signal {signum}, stopping main loop...")
    global mainloop
    mainloop.quit()


def main():
    """Main function to set up the D-Bus to NMEA 0183 relay service
    and start the main loop."""
    
    global mainloop, nmea_transmitter

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s")
    logging.info("Starting Dbus2Nmea0183 relay service...")
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    # Set up a timer to relay the D-Bus value every second
    GLib.timeout_add_seconds(1, relay_dbus_value)

    logging.info('Connected to dbus, and switching over to GLib.MainLoop() (= event based)')
    mainloop = GLib.MainLoop()
    mainloop.run()
    
    logging.info("Mainloop stopped, cleaning up...")

if __name__ == "__main__":
    main()
    logging.info("Dbus2Nmea0183 service has been stopped.")