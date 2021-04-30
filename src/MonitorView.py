"""
MonitorView.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 04/29/21
Last Modified: 04/30/21

Description: Implements the MonitorView class, which inherits View class.
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

# Custom Imports.
from src.View import View


class MonitorView(View):
    """
    The MonitorView class manages the backend functions for displaying serial
    output and graphs for specific packet configurations.
    """

    SPAN_RED = [
        '<span style=" font-size:8pt; font-weight:300; color:#ff0000;" >',
        "</span>",
    ]
    SPAN_GREEN = [
        '<span style=" font-size:8pt; font-weight:300; color:#00ff00;" >',
        "</span>",
    ]
    SPAN_BLUE = [
        '<span style=" font-size:8pt; font-weight:300; color:#0000ff;" >',
        "</span>",
    ]

    # Pre-filled dropdown options.
    def __init__(self, data_controller, framerate):
        """
        Upon initialization, we perform any data and UI setup required to get
        the SetupView into a default state.
        """
        super(MonitorView, self).__init__(
            data_controller=data_controller, framerate=framerate
        )

        self._widget_pointers = self._data_controller["widget_pointers"]

        # Setup Status.
        self._widget_pointers["lbl_status2"].setAutoFillBackground(True)
        self._widget_pointers["lbl_status2"].setText(self._data_controller["status"])

        # Setup transmission textbox and send button.
        self._widget_pointers["le_transmit_txt"].returnPressed.connect(self.send_data)
        self._widget_pointers["bu_send"].clicked.connect(self.send_data)

        # Setup save button.
        self._widget_pointers["bu_save"].clicked.connect(self.save_packets)

        # Setup packet file configuration.
        self._widget_pointers["bu_packet_config_filesearch"].clicked.connect(
            self.get_file_name
        )

        # TODO: Setup viewbox for qtgraph.

        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._update_console)
        self._monitor_timer.start(View.SECOND / self._framerate)

    def _update_console(self):
        # Update status.
        if self._data_controller["status"] == "CONNECTED":
            self._widget_pointers["lbl_status2"].setText(self._data_controller["status"])
            self._widget_pointers["lbl_status2"].setStyleSheet(
                "QLabel { background-color: rgba(122, 255, 122, 255); }"
            )
        elif self._data_controller["status"] == "DISCONNECTED":
            self._widget_pointers["lbl_status2"].setText(self._data_controller["status"])
            self._widget_pointers["lbl_status2"].setStyleSheet(
                "QLabel { background-color: rgba(122, 122, 122, 255); }"
            )

        # Capture read data from serial_datastream and display on text browser.
        while not self._serial_datastream["read_lock"].tryLock(50):
            pass
        text = ""
        for entry in self._serial_datastream["read"]:
            text += entry.decode("utf-8")
        # TODO: do some packet processing here if required.
        if text:
            self._widget_pointers["te_serial_output"].append(text)
            self._serial_datastream["read"].clear()
        self._serial_datastream["read_lock"].unlock()

        # TODO: Display on graph if data packets are a match.

        # TODO: Capture status data from serial_datastream and display on textedit.
        while not self._serial_datastream["status_lock"].tryLock(50):
            pass

        new_status = []
        errors = []
        for entry in self._serial_datastream["status"]:
            text = ""
            if entry == "Serial connection was closed." or entry == "READY":
                text = MonitorView.SPAN_GREEN[0] + entry + MonitorView.SPAN_GREEN[1]
                # Capture all closed messages, but keep any READY messages.
                if entry == "READY":
                    new_status.append(entry)
            else:
                text = MonitorView.SPAN_RED[0] + entry + MonitorView.SPAN_RED[1]
                errors.append(entry)
            if text:
                self._widget_pointers["te_serial_output"].append(text)

        self._serial_datastream["status"] = new_status
        self._serial_datastream["status_lock"].unlock()

        if errors:
            # Raise the first error.
            self._raise_error(errors[0])

    def send_data(self):
        """
        Pushes data to be written into the serial_datastream.
        """
        # Check if there is text in the line edit
        text = self._widget_pointers["le_transmit_txt"].text()
        if text and self._data_controller["status"] == "CONNECTED":
            # Lock the write FIFO and append to queue, then unlock.
            while not self._serial_datastream["write_lock"].tryLock(200):
                pass
            self._serial_datastream["write"].append(text.encode("utf-8"))
            self._serial_datastream["write_lock"].unlock()

            # Echo to the text edit.
            text = MonitorView.SPAN_BLUE[0] + text + MonitorView.SPAN_BLUE[1]
            self._widget_pointers["te_serial_output"].append(text)
        # Echo errors to the text edit.
        elif self._data_controller["status"] != "CONNECTED":
            text = (
                MonitorView.SPAN_RED[0]
                + "Device is not connected."
                + MonitorView.SPAN_RED[1]
            )
            self._widget_pointers["te_serial_output"].append(text)
        else:
            text = (
                MonitorView.SPAN_RED[0]
                + "There is nothing to send!"
                + MonitorView.SPAN_RED[1]
            )
            self._widget_pointers["te_serial_output"].append(text)

        # Clear the line edit.
        self._widget_pointers["le_transmit_txt"].clear()

    def save_packets(self):
        """
        Checks storage of all packets, filters them if a filter is in place, then
        stashes them as a CSV.
        """
        pass

    def get_file_name(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setFilter(QDir.Files)

        if dialog.exec_():
            file_name = dialog.selectedFiles()
            self._widget_pointers["le_packet_config"].setText(file_name[0])

            # File validation.
            if file_name[0].endswith(".json"):
                with open(file_name[0], "r") as f:
                    data = json.load(f)

                    # Graph inputs.
                    if "title" in data and type(data["title"]) is str:
                        pass

                    if "x_axis" in data and type(data["x_axis"]) is int:
                        pass

                    if "y_axis" in data and type(data["y_axis"]) is str:
                        pass

                    if "intrapacket" in data and type(data["intrapacket"]) is dict:
                        self._data_controller["packet_config"]["intrapacket"] = data[
                            "intrapacket"
                        ]

                    if "interpacket" in data and type(data["interpacket"]) is dict:
                        self._data_controller["packet_config"]["interpacket"] = data[
                            "interpacket"
                        ]

                    # TODO: automatically load the graph and filter monitor.
                    self.update_state()
                    f.close()
            else:
                self._raise_error("Invalid file type.")

    def _raise_error(self, error_str):
        """
        Raises an error on the status label.

        Parameters
        ----------
        error_str: str
            Error string to display.
        """
        self._widget_pointers["lbl_status2"].setText(error_str)
        self._widget_pointers["lbl_status2"].setStyleSheet(
            "QLabel { background-color: rgba(255, 0, 0, 255); }"
        )

        # Set timer to set status back to OK.
        QTimer.singleShot(15000, self._revert_error)

    def _revert_error(self):
        """
        Resets the status bar after an error has been displayed for X amount of
        time.
        """
        self._widget_pointers["lbl_status2"].setText(self._data_controller["status"])
        if self._data_controller["status"] == "DISCONNECTED":
            self._widget_pointers["lbl_status2"].setStyleSheet(
                "QLabel { background-color: rgba(122, 122, 122, 255); }"
            )
        elif self._data_controller["status"] == "CONNECTED":
            self._widget_pointers["lbl_status2"].setStyleSheet(
                "QLabel { background-color: rgba(122, 255, 122, 255); }"
            )
        else:
            pass
