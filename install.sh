#!/bin/sh

# set permissions
chmod -R 777 /data/VenusOS-NmeaTransmitter/

# create a symlink to the service directory to make it start automatically by the daemon manager
ln -sf /data/VenusOS-NmeaTransmitter/service /service/VenusOS-NmeaTransmitter
ln -sf /data/VenusOS-NmeaTransmitter/service /opt/victronenergy/service/VenusOS-NmeaTransmitter

echo "Service symlink created"

# start service
svc -t /service/VenusOS-NmeaTransmitter
echo "Service started"

# ── GUI v2 (Venus OS 2.80+) ────────────────────────────────────────────────
GUI_V2_COMPILER="/opt/victronenergy/gui-v2/gui-v2-plugin-compiler.py"
GUI_V2_APP_DIR="/data/apps/available/NmeaTransmitter"
GUI_V2_QML="/data/VenusOS-NmeaTransmitter/GUI/v2/NmeaTransmitter_PageNmeaTransmitter.qml"

if [ -f "$GUI_V2_COMPILER" ]; then
    mkdir -p "$GUI_V2_APP_DIR/gui-v2"
    cp "$GUI_V2_QML" "$GUI_V2_APP_DIR/gui-v2/$(basename $GUI_V2_QML)"
    ( cd "$GUI_V2_APP_DIR/gui-v2" && python3 "$GUI_V2_COMPILER" \
        --name NmeaTransmitter \
        --settings "$(basename $GUI_V2_QML)" )
    mkdir -p /data/apps/enabled
    ln -sfn "$GUI_V2_APP_DIR" /data/apps/enabled/NmeaTransmitter
    svc -t /service/gui-v2 2>/dev/null || svc -t /service/gui 2>/dev/null
    echo "GUI v2 plugin installed"
fi

# ── GUI v1 (legacy Venus OS) ──────────────────────────────────────────────
GUI_V1_QML_DIR="/opt/victronenergy/gui/qml"

if [ -d "$GUI_V1_QML_DIR" ]; then
    cp /data/VenusOS-NmeaTransmitter/GUI/PageNmeaTransmitter.qml "$GUI_V1_QML_DIR/PageNmeaTransmitter.qml"
    if ! grep -q "PageNmeaTransmitter" "$GUI_V1_QML_DIR/PageSettingsGeneral.qml"; then
        python3 << 'EOF'
import re
path = "/opt/victronenergy/gui/qml/PageSettingsGeneral.qml"
entry = """
//////// NMEA Transmitter
MbSubMenu {
  description: qsTr("NMEA Transmitter")
  subpage: Component { PageNmeaTransmitter {} }
  show: true
}
"""
with open(path) as f: content = f.read()
content = re.sub(r'(\s*\}\s*\}\s*)$', entry + r'\1', content, count=1)
with open(path, 'w') as f: f.write(content)
EOF
    fi
    svc -t /service/gui-v2 2>/dev/null || svc -t /service/gui 2>/dev/null
    echo "GUI v1 plugin installed"
fi