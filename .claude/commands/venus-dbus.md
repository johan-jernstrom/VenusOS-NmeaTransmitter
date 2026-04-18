# Venus OS D-Bus Code Scaffolding

See global `~/.claude/commands/venus-dbus.md` for the full reference.

This project-level command inherits all global knowledge. Additional context specific to this repo:

- Vendored libs: `velib_python/` (dbusmonitor, vedbus, settingsdevice, ve_utils)
- Main service: `Dbus2NmeaRelayService.py`
- Serial transmitter: `Nmea0183Transmitter.py`
- Settings namespace: `/Settings/NmeaTransmitter/`
- D-Bus status service: `com.victronenergy.nmeatransmitter`
- GUI pages: `GUI/v2/NmeaTransmitter_PageNmeaTransmitter.qml` (v2), `GUI/PageNmeaTransmitter.qml` (v1)
- Target device: `root@192.168.4.23`, deployed to `/data/VenusOS-NmeaTransmitter/`

**User request / args:** $ARGUMENTS

Generate code following the patterns in this codebase and the Venus OS D-Bus conventions from the global command.
