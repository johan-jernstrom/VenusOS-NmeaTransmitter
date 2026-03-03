import serial
import logging

class Nmea0183Transmitter:
    def __init__(self, serial_port="/dev/ttyACM0", baudrate=4800):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.logger = logging.getLogger(self.__class__.__name__)
        self._serial = None

    def open(self):
        """Open the serial port connection."""
        try:
            self._serial = serial.Serial(port=self.serial_port, baudrate=self.baudrate, timeout=1)
            self.logger.info(f"Opened serial port {self.serial_port}")
        except serial.SerialException as e:
            self.logger.error(f"Failed to open serial port {self.serial_port}: {e}")
            self._serial = None

    def close(self):
        """Close the serial port connection."""
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None

    def _calculate_checksum(self, nmea_str):
        """Calculate NMEA 0183 checksum"""
        checksum = 0
        for char in nmea_str:
            checksum ^= ord(char)
        return f"{checksum:02X}"

    def _build_nmea_sentence(self, code, value, unit):
        """Build the NMEA sentence."""
        body = f"{code},{value},{unit}"
        checksum = self._calculate_checksum(body)
        return f"${body}*{checksum}\r\n"

    def send_nmea_sentence(self, code="PSILTBS", value=None, unit="N"):
        """Send the NMEA sentence over serial port.
        Default code is 'PSILTBS' (Silva Nexus Special NMEA Sentence for Target Boat Speed) and unit is 'N' (Knot).
        """
        if value is None:
            raise ValueError("Value must be provided to build NMEA sentence")
        if not isinstance(value, (int, float)):
            raise TypeError("Value must be an integer or float")
        value = float(value)  # Ensure value is a float
        value = round(value, 1)  # Round to one decimal place
        try:
            if self._serial is None or not self._serial.is_open:
                self.open()
            if self._serial is None:
                return  # Failed to open port, error already logged
            sentence = self._build_nmea_sentence(code, value, unit)
            self.logger.debug(f"Sending NMEA sentence: {sentence.strip()}")
            self._serial.write(sentence.encode('ascii'))
        except serial.SerialException as e:
            self.logger.error(f"Serial error: {e}")
            self.close()  # Force reconnect on next send
