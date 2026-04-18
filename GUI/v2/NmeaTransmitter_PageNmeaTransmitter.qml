import QtQuick
import Victron.VenusOS

Page {
    id: root
    title: qsTr("NMEA Transmitter")

    GradientListView {
        model: VisibleItemModel {

            // ── Status (read-only) ──────────────────────────────────
            ListText {
                text: qsTr("Serial port status")
                dataItem.uid: "dbus/com.victronenergy.nmeatransmitter/Connected"
                secondaryText: dataItem.valid ? (dataItem.value ? qsTr("Connected") : qsTr("Disconnected")) : "--"
            }
            ListText {
                text: qsTr("Battery service status")
                dataItem.uid: "dbus/com.victronenergy.nmeatransmitter/BatteryConnected"
                secondaryText: dataItem.valid ? (dataItem.value ? qsTr("Connected") : qsTr("Disconnected")) : "--"
            }
            ListQuantity {
                text: qsTr("Last current")
                dataItem.uid: "dbus/com.victronenergy.nmeatransmitter/LastCurrent"
                unit: VenusOS.Units_Amp
                preferredVisible: dataItem.valid
            }

            // ── Settings (editable) ─────────────────────────────────
            ListTextField {
                text: qsTr("Serial port")
                dataItem.uid: "dbus/com.victronenergy.settings/Settings/NmeaTransmitter/SerialPort"
                textField.maximumLength: 32
                writeAccessLevel: VenusOS.User_AccessType_User
            }
            ListTextField {
                text: qsTr("Battery D-Bus service")
                dataItem.uid: "dbus/com.victronenergy.settings/Settings/NmeaTransmitter/BatteryService"
                textField.maximumLength: 64
                writeAccessLevel: VenusOS.User_AccessType_User
            }
        }
    }
}
