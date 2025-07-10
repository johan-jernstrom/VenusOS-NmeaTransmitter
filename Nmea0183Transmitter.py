import serial
import logging

class Nmea0183Transmitter:
    def __init__(self, serial_port="/dev/ttyACM0", baudrate=4800):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.logger = logging.getLogger(self.__class__.__name__) 
        
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
        """Send the NMEA sentence over serial port
        Default code is 'PSILTBS' (Silva Nexus Special NMEA Sentence for Target Boat Speed) and unit is 'N' (Knot).
        """
        if value is None:
            raise ValueError("Value must be provided to build NMEA sentence")
        if not isinstance(value, (int, float)):
            raise TypeError("Value must be an integer or float")
        value = float(value)  # Ensure value is a float
        value = round(value, 1)  # Round to two decimal places
        try:
            with serial.Serial(port=self.serial_port, baudrate=self.baudrate, timeout=1) as ser:
                sentence = self._build_nmea_sentence(code, value, unit)
                self.logger.debug(f"Sending NMEA sentence: {sentence.strip()}")
                ser.write(sentence.encode('ascii'))
        except serial.SerialException as e:
            self.logger.error(f"Serial error: {e}")

