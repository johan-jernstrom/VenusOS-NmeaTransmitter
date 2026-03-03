# VenusOS-NmeaTransmitter

## Project Overview

A D-Bus to NMEA 0183 relay service for Venus OS (Victron Energy devices). It monitors battery current data from the Victron D-Bus system and transmits it as NMEA 0183 sentences over a serial port to marine navigation devices (e.g. Silva Nexus chart plotters).

**Flow:** Victron battery → D-Bus → `Dbus2NmeaRelayService.py` → `Nmea0183Transmitter.py` → `/dev/ttyACM0` (4800 baud) → navigation device

## File Structure

```
Dbus2NmeaRelayService.py   # Main relay service (D-Bus monitor + relay thread)
Nmea0183Transmitter.py     # Serial NMEA 0183 transmitter
install.sh                 # Installation script (symlinks + daemon start)
service/run                # Daemon entry point (runs with softlimit)
service/log/run            # Logging config (multilog → /var/log/VenusOS-NmeaTransmitter)
velib_python/              # Vendored Victron library (do not modify)
  dbusmonitor.py           # D-Bus service monitor abstraction
  ve_utils.py              # Utility functions
```

## Install & Run

```bash
# Install and start as a daemon (Venus OS)
sh install.sh

# Run manually for development/debugging
python3 Dbus2NmeaRelayService.py --log-level DEBUG

# Command-line options
python3 Dbus2NmeaRelayService.py \
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}  # default: INFO
  --min-interval <float>                           # default: 0.5 seconds
  --max-interval <float>                           # default: 60.0 seconds
```

## Key Configuration Constants

| Setting | Value | Location |
|---|---|---|
| D-Bus service class | `com.victronenergy.battery` | `Dbus2NmeaRelayService.py` |
| Monitored path | `/Dc/0/Current` | `Dbus2NmeaRelayService.py` |
| Ignored service | `com.victronenergy.battery.ttyUSB0` | `Dbus2NmeaRelayService.py` |
| Serial port | `/dev/ttyACM0` | `Nmea0183Transmitter.py` |
| Baud rate | 4800 | `Nmea0183Transmitter.py` |
| NMEA sentence code | `PSILTBS` | `Nmea0183Transmitter.py` |
| NMEA unit | `N` (knots) | `Nmea0183Transmitter.py` |

## Architecture

- **Main thread**: GLib event loop — handles D-Bus signals and OS signals (SIGINT, SIGTERM)
- **Relay thread**: Daemon thread — sends NMEA sentences at rate-limited intervals
- **Thread safety**: `threading.Lock()` guards the sensor data cache; `threading.Event()` signals the relay thread immediately on data change (no polling)
- **Rate limiting**: Min 0.5s between sends (prevents flooding), max 60s (keeps connection alive)
- **Serial port**: Persistent connection with auto-reconnect on failure

## Coding Conventions

- **Language**: Python 3
- **Classes**: `CamelCase`
- **Methods/variables**: `snake_case`; private methods prefixed with `_`
- **Constants/NMEA codes**: `UPPERCASE`
- Comprehensive logging at DEBUG/INFO/WARNING/ERROR levels throughout
- Validate inputs at boundaries (NaN checks for D-Bus values, interval validation at startup)
- No external dependencies beyond standard library, `dbus`, `gi` (PyGObject), and `pyserial`

## velib_python

Vendored from [Victron Energy's velib_python](https://github.com/victronenergy/velib_python). **Do not modify these files.** If an update is needed, replace them wholesale from the upstream repo.

## Logs

```bash
# View live logs (Venus OS)
tail -f /var/log/VenusOS-NmeaTransmitter/current
```
