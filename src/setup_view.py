"""
setup_view.py

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
from src.view import View
from src.misc import capture_port_names


class SetupView(View):
    """
    The SetupView class manages setup and connection with an open serial port to
    a serial device.
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

        self.init_frame(self._update_console)

    def _update_console(self):
        # TODO: handle this in monitor_view.py.
        # Clear the status buffer of error messages, if necessary.
        status_lock = self._serial_datastream["status_lock"]
        status_msg = None
        if not status_lock.tryLock(View.SECOND / self._framerate):
            return

        status_buffer = self._serial_datastream["status"]
        if len(status_buffer) != 0 and status_buffer[0] != "READY":
            status_msg = status_buffer[0]
            self._serial_datastream["status"] = status_buffer[1:]
            
        status_lock.unlock()

        # if status_msg is not None:
        #     self.raise_temp_status(status_msg, "rgba(0, 0, 255, 255)")

    def update_ports(self):
        """
        Updates the list of active ports.
        """
        self._widget_pointers["cb_portname"].clear()
        self._widget_pointers["cb_portname"].addItems(
            self._data_controller["port_names"]
        )

    def get_file_name(self):
        """
        Selects a file and attempts to load a configuration.
        """
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
                self.raise_error("Invalid file type.")

    def _get_file_name_helper(self, data, cb_string, data_id):
        """
        Helper for get_file_name. Attempts to look for a pre-existing value in a
        specific dropdown menu; if it doesn't exist, makes it and inserts it at
        the back of the list.

        Parameters
        ----------
        data: Any
            Data to look for.
        cb_string: Str
            Combo-box string to search for.
        data_id: Str
            String key in the unwrapped JSON file to capture.
        """
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
        """
        Connects or disconnects the application.
        """
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

        if self._validate_config(
            port, baud_rate, data_bits, endianness, parity_bits, sync_bits
        ):
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
            ready = False
            timeout = 0

            _status_lock = self._serial_datastream["status_lock"]
            while not ready:
                print("Looping..")
                while not _status_lock.tryLock(View.SECOND / self._framerate):
                    timeout += 1

                _status_buffer = self._serial_datastream["status"]
                if len(_status_buffer) != 0 and _status_buffer[0] == "READY":
                    self._serial_datastream["status"] = _status_buffer[1:]
                    ready = True
                _status_lock.unlock()

                # If we haven't connected after 5 seconds, time out.
                if timeout >= View.SECOND * 5 / self._framerate:
                    print("timeout!")
                    self.disconnect()
                    self.raise_error("TIMEOUT")
                    return

            # Upon success, set status to connected.
            self._data_controller["status"] = "CONNECTED"
            self.raise_status(self._data_controller["status"], "rgba(0, 255, 0, 255)")

    def _validate_config(
        self, port, baud_rate, data_bits, endianness, parity_bits, sync_bits
    ):
        """
        Helper method to connect. Validates the current set configuration in the
        setup menu.

        Parameters
        ----------
        port: Any
            Proposed port name.
        baud_rate: Any
            Proposed baud rate.
        data_bits: Any
            Proposed data bits.
        endianness: Any
            Proposed endianness.
        parity_bits: Any
            Proposed parity bits.
        sync_bits: Any
            Proposed sync bits.

        Returns
        -------
        Bool: True if valid config, false otherwise.
        """
        # Check if port is currently open.
        listed_ports = capture_port_names()
        if not any(listed_port in port for listed_port in listed_ports):
            self.raise_error("Port is not open.")
            return False

        # Check if baud_rate is a positive integer.
        if not baud_rate.isdigit():
            self.raise_error("Baud rate must be a positive integer.")
            return False
        if int(baud_rate) <= 0:
            self.raise_error("Baud rate must be a positive integer.")
            return False

        # Check if data_bits is from five to eight.
        if not any(data_bit in data_bits for data_bit in SetupView.DATA_BITS):
            self.raise_error("Data bits must be either FIVE, SIX, SEVEN, or EIGHT.")
            return False

        # Check if Endianness is MSB or LSB.
        if not any(endian in endianness for endian in SetupView.ENDIAN):
            self.raise_error("Endianness should be either MSB or LSB.")
            return False

        # Check if parity bits is either None, Odd, or Even.
        if not any(parity in parity_bits for parity in SetupView.PARITY_BITS):
            self.raise_error("Parity bits should be either None, Odd, or Even.")
            return False

        # Check if sync bits is either one or two.
        if not any(sync_bit in sync_bits for sync_bit in SetupView.SYNC_BITS):
            self.raise_error("Sync bits must be either ONE or TWO.")
            return False

        return True

    def disconnect(self):
        """
        Disconnects an existing serial line and updates the UI.
        """
        # Stop an existing serial communication.
        self._data_controller["app"]._stop_serial_thread()

        # Upon success, set status to disconnected.
        self._data_controller["status"] = "DISCONNECTED"
        self.raise_status(self._data_controller["status"], "rgba(122, 122, 255, 255)")
