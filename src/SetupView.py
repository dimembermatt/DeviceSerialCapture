"""
SetupView.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 04/29/21
Last Modified: 04/29/21

Description: Implements the SetupView class, which inherits View class.
"""
# Library Imports.
import json
from PyQt5.QtCore import Qt, QDir, QTimer
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
import serial.tools.list_ports

# Custom Imports.
from src.View import View


class SetupView(View):
    """
    The SetupView class...
    """

    # Pre-filled dropdown options.
    BAUD_RATE = [115200, 1200, 2400, 4800, 19200, 38400, 57600]
    DATA_BITS = ["EIGHT", "FIVE", "SIX", "SEVEN"]
    ENDIAN = ["LSB", "MSB"]
    SYNC_BITS = ["ONE", "TWO"]
    PARITY_BITS = ["None", "Odd", "Even"]

    def __init__(self, data_controller, framerate):
        """
        Upon initialization, we perform any data and UI setup required to get
        the SetupView into a default state.
        """
        super(SetupView, self).__init__(
            data_controller=data_controller, framerate=framerate
        )

        self._serial_datastream = data_controller["serial_datastream"]

        self._widget_pointers = self._data_controller["widget_pointers"]

        # Set Status to DISCONNECTED.
        self._widget_pointers["lbl_status"].setAutoFillBackground(True)
        self._widget_pointers["lbl_status"].setText(self._data_controller["status"])

        # Set labels to default values.
        self._widget_pointers["cb_baud"].addItems([str(x) for x in SetupView.BAUD_RATE])
        self._widget_pointers["cb_databits"].addItems(SetupView.DATA_BITS)
        self._widget_pointers["cb_endian"].addItems(SetupView.ENDIAN)
        self._widget_pointers["cb_paritybits"].addItems(SetupView.PARITY_BITS)
        self._widget_pointers["cb_portname"].addItems(
            self._data_controller["port_names"]
        )
        self._widget_pointers["cb_syncbits"].addItems(SetupView.SYNC_BITS)

        # Setup file configuration button.
        self._widget_pointers["bu_serial_config_filesearch"].clicked.connect(
            self.get_file_name
        )

        # Setup connect button.
        self._widget_pointers["bu_connect"].clicked.connect(self._connect_disconnect)
        self._widget_pointers["lbl_status"].setStyleSheet(
            "QLabel { background-color: rgba(122, 122, 122, 255); }"
        )

        self._setup_timer = QTimer()
        self._setup_timer.timeout.connect(self._update_console)
        self._setup_timer.start(View.SECOND / self._framerate)

    def _update_console(self):
        if self._data_controller["status"] == "CONNECTED":
            self._widget_pointers["lbl_status"].setText(self._data_controller["status"])
            self._widget_pointers["lbl_status"].setStyleSheet(
                "QLabel { background-color: rgba(122, 255, 122, 255); }"
            )

            # Modify connect button to say "DISCONNECT".
            self._widget_pointers["bu_connect"].setText("DISCONNECT")
        elif self._data_controller["status"] == "DISCONNECTED":
            self._widget_pointers["lbl_status"].setText(self._data_controller["status"])
            self._widget_pointers["lbl_status"].setStyleSheet(
                "QLabel { background-color: rgba(122, 122, 122, 255); }"
            )

            # Modify connect button to say "CONNECT".
            self._widget_pointers["bu_connect"].setText("CONNECT")

    def update_ports(self):
        """
        Update list of active ports.
        """
        self._widget_pointers["cb_portname"].clear()
        self._widget_pointers["cb_portname"].addItems(
            self._data_controller["port_names"]
        )

    def get_file_name(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setFilter(QDir.Files)

        if dialog.exec_():
            file_name = dialog.selectedFiles()
            self._widget_pointers["le_serial_config"].setText(file_name[0])

            # File validation.
            if file_name[0].endswith(".json"):
                with open(file_name[0], "r") as f:
                    data = json.load(f)

                    if "port_name" in data and type(data["port_name"]) is str:
                        self._get_file_name_helper(data, "cb_portname", "port_name")

                    if "baud_rate" in data and type(data["baud_rate"]) is int:
                        self._get_file_name_helper(data, "cb_baud", "baud_rate")

                    if "data_bits" in data and type(data["data_bits"]) is str:
                        self._get_file_name_helper(data, "cb_databits", "data_bits")

                    if "endian" in data and type(data["endian"]) is str:
                        self._get_file_name_helper(data, "cb_endian", "endian")

                    if "sync_bits" in data and type(data["sync_bits"]) is str:
                        self._get_file_name_helper(data, "cb_syncbits", "sync_bits")

                    if "parity_bits" in data and type(data["parity_bits"]) is str:
                        self._get_file_name_helper(data, "cb_paritybits", "parity_bits")
                    f.close()
            else:
                self._raise_error("Invalid file type.")

    def _get_file_name_helper(self, data, cb_string, data_id):
        index = self._widget_pointers[cb_string].findText(
            str(data[data_id]), Qt.MatchFixedString
        )
        if index < 0:
            self._widget_pointers[cb_string].addItem(str(data[data_id]))
            index = self._widget_pointers[cb_string].findText(
                str(data[data_id]), Qt.MatchFixedString
            )
        self._widget_pointers[cb_string].setCurrentIndex(index)

    def _connect_disconnect(self):
        if self._data_controller["status"] == "DISCONNECTED":
            self.connect()
        elif self._data_controller["status"] == "CONNECTED":
            self.disconnect()

    def connect(self):
        """
        Validates the existing inputs and attempts to connect to the serial device.
        """
        port = self._widget_pointers["cb_portname"].currentText()
        baud_rate = self._widget_pointers["cb_baud"].currentText()
        data_bits = self._widget_pointers["cb_databits"].currentText()
        endianness = self._widget_pointers["cb_endian"].currentText()
        parity_bits = self._widget_pointers["cb_paritybits"].currentText()
        sync_bits = self._widget_pointers["cb_syncbits"].currentText()

        # Check if port is currently open.
        listed_ports = serial.tools.list_ports.comports()
        listed_ports = [port for port, desc, hwid in sorted(listed_ports)]
        if not any(listed_port in port for listed_port in listed_ports):
            self._raise_error("Port is not open.")
            return

        # Check if baud_rate is a positive integer.
        if not baud_rate.isdigit():
            self._raise_error("Baud rate must be a positive integer.")
            return
        if int(baud_rate) <= 0:
            self._raise_error("Baud rate must be a positive integer.")
            return

        # Check if data_bits is from five to eight.
        if not any(data_bit in data_bits for data_bit in SetupView.DATA_BITS):
            self._raise_error("Data bits must be either FIVE, SIX, SEVEN, or EIGHT.")
            return

        # Check if Endianness is MSB or LSB.
        if not any(endian in endianness for endian in SetupView.ENDIAN):
            self._raise_error("Endianness should be either MSB or LSB.")
            return

        # Check if parity bits is either None, Odd, or Even.
        if not any(parity in parity_bits for parity in SetupView.PARITY_BITS):
            self._raise_error("Parity bits should be either None, Odd, or Even.")
            return

        # Check if sync bits is either one or two.
        if not any(sync_bit in sync_bits for sync_bit in SetupView.SYNC_BITS):
            self._raise_error("Sync bits must be either ONE or TWO.")
            return

        # Successful validation. Update the _data_controller["config"] and call
        # the parent to startup a serial connection.
        self._data_controller["config"]["port_name"] = str(port)
        self._data_controller["config"]["baud_rate"] = int(baud_rate)
        self._data_controller["config"]["data_bits"] = str(data_bits)
        self._data_controller["config"]["endian"] = str(endianness)
        self._data_controller["config"]["sync_bits"] = str(sync_bits)
        self._data_controller["config"]["parity_bits"] = str(parity_bits)

        # Set status box to "CONNECTING" and set to blue.
        self._widget_pointers["lbl_status"].setText("CONNECTING")
        self._widget_pointers["lbl_status"].setStyleSheet(
            "QLabel { background-color: rgba(122, 122, 255, 255); }"
        )

        # Activate a serial connection.
        self._data_controller["app"]._start_serial_thread()

        # Check for status == READY by the serialWorker in serial_datastream.
        # TODO: add timeout error for bad connection.

        ready = False
        while not ready:
            while not self._serial_datastream["status_lock"].tryLock(
                View.SECOND / self._framerate
            ):
                pass
            if (
                len(self._serial_datastream["status"]) != 0
                and self._serial_datastream["status"][0] == "READY"
            ):
                self._serial_datastream["status"] = self._serial_datastream["status"][
                    1:
                ]
                ready = True
            self._serial_datastream["status_lock"].unlock()

        # Upon success, set status to connected.
        self._data_controller["status"] = "CONNECTED"

    def disconnect(self):
        """
        Disconnects an existing serial line and updates the UI.
        """
        # Stop an existing serial communication.
        self._data_controller["app"]._stop_serial_thread()

        # Upon success, set status to disconnected.
        self._data_controller["status"] = "DISCONNECTED"

    def _raise_error(self, error_str):
        """
        Raises an error on the status label.

        Parameters
        ----------
        error_str: str
            Error string to display.
        """
        self._widget_pointers["lbl_status"].setText(error_str)
        self._widget_pointers["lbl_status"].setStyleSheet(
            "QLabel { background-color: rgba(255, 0, 0, 255); }"
        )

        # Set timer to set status back to OK.
        QTimer.singleShot(15000, self._revert_error)

    def _revert_error(self):
        """
        Resets the status bar after an error has been displayed for X amount of
        time.
        """
        self._widget_pointers["lbl_status"].setText(self._data_controller["status"])
        if self._data_controller["status"] == "DISCONNECTED":
            self._widget_pointers["lbl_status"].setStyleSheet(
                "QLabel { background-color: rgba(122, 122, 122, 255); }"
            )
        elif self._data_controller["status"] == "CONNECTED":
            self._widget_pointers["lbl_status"].setStyleSheet(
                "QLabel { background-color: rgba(122, 255, 122, 255); }"
            )
        else:
            pass
