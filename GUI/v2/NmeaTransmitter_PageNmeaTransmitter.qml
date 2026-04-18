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
                secondaryText: {
                    const v = serialConnected.value
                    if (v === undefined || v === null) return "--"
                    return v ? qsTr("Connected") : qsTr("Disconnected")
                }
                DataItem { id: serialConnected; uid: "dbus/com.victronenergy.nmeatransmitter/Connected" }
            }
            ListText {
                text: qsTr("Battery service status")
                secondaryText: {
                    const v = batteryConnected.value
                    if (v === undefined || v === null) return "--"
                    return v ? qsTr("Connected") : qsTr("Disconnected")
                }
                DataItem { id: batteryConnected; uid: "dbus/com.victronenergy.nmeatransmitter/BatteryConnected" }
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
                maximumLength: 32
                userHasWriteAccess: VenusOS.User_AccessType_User
            }
            ListTextField {
                text: qsTr("Battery D-Bus service")
                dataItem.uid: "dbus/com.victronenergy.settings/Settings/NmeaTransmitter/BatteryService"
                maximumLength: 64
                userHasWriteAccess: VenusOS.User_AccessType_User
            }
        }
    }
}
