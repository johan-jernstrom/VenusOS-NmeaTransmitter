import QtQuick 1.1
import "utils.js" as Utils
import com.victron.velib 1.0

MbPage {
    id: root
    title: qsTr("NMEA Transmitter")
    model: VisibleItemModel {
        MbItemValue {
            description: qsTr("Serial port status")
            item.bind: Utils.path("com.victronenergy.nmeatransmitter", "/Connected")
        }
        MbItemValue {
            description: qsTr("Battery service status")
            item.bind: Utils.path("com.victronenergy.nmeatransmitter", "/BatteryConnected")
        }
        MbItemValue {
            description: qsTr("Last current (A)")
            item.bind: Utils.path("com.victronenergy.nmeatransmitter", "/LastCurrent")
        }
        MbEditBox {
            description: qsTr("Serial port")
            item.bind: Utils.path("com.victronenergy.settings", "/Settings/NmeaTransmitter/SerialPort")
            maximumLength: 32
        }
        MbEditBox {
            description: qsTr("Battery D-Bus service")
            item.bind: Utils.path("com.victronenergy.settings", "/Settings/NmeaTransmitter/BatteryService")
            maximumLength: 64
        }
    }
}
