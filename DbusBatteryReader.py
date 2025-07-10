import os
import sys
import dbus
import logging
# import victron package for updating dbus (using lib from built in service)
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-modem'))
from vedbus import VeDbusItemImport

class DbusBatteryReader:
    def __init__(self, service_name="com.victronenergy.battery.ttyUSB1"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.service_name = service_name
        
        # Connect to the sessionbus. Note that on ccgx we use systembus instead.
        dbusConn = dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()

        self.current_item = VeDbusItemImport(
            bus=dbusConn,
            serviceName=self.service_name,
            path="/Dc/0/Current",
            eventCallback=None,
            createsignal=False
        )

    def get_batt_current(self):
        current = self.current_item.get_value()
        if current is None:
            self.logger.error("Failed to read battery current from D-Bus")
            return None
        if not isinstance(current, (int, float)):
            self.logger.error(f"Invalid battery current type: {type(current)}")
            return None
        self.logger.debug(f"Battery current read from D-Bus: {current}")
        return float(current)
