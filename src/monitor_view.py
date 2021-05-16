"""
monitor_view.py

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
import sys

# Custom Imports.
from src.view import View
from src.graph import Graph


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

        self._serial_datastream = data_controller["serial_datastream"]

        # Setup transmission textbox and send button.
        self._widget_pointers["le_transmit_txt"].returnPressed.connect(
            self._send_packet
        )
        self._widget_pointers["bu_send"].clicked.connect(self._send_packet)

        # Setup save button.
        self._widget_pointers["bu_save"].clicked.connect(self._save_packets)

        # Setup packet file configuration.
        self._widget_pointers["bu_packet_config_filesearch"].clicked.connect(
            self._get_file_name
        )

        # Setup viewbox for qtgraph.
        # self._remove_graph()

        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._update_console)
        self._monitor_timer.start(View.SECOND / self._framerate)

        # Current iteration of _update_console.
        self._cycle = 0

        # The bytes that have yet to be parsed.
        self._bytes_to_parse = bytearray()

        # Packets that have been captured and translated.
        self._parsed_packets = []

    def _update_console(self):
        self._cycle += 1

        # Capture read data from serial_datastream, if available.
        while not self._serial_datastream["read_lock"].tryLock(50):
            pass
        for byte in self._serial_datastream["read"]:
            self._bytes_to_parse += bytearray(byte)
        self._serial_datastream["read"].clear()
        self._serial_datastream["read_lock"].unlock()

        # Add to display or text edit, if applicable.
        parsed_packet, parsed_text = self._parse_packet()
        if parsed_text:
            self._widget_pointers["te_serial_output"].append(parsed_text)
        # # Only update graph if config is set up.
        # if parsed_packet and self.graph is not None:
        #     self._apply_data_to_graph(parsed_packet)

        # Capture status data from serial_datastream and display on textedit.
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

    # Graph management.
    def _get_file_name(self):
        """
        Called when the user wants to load a packet configuration file.
        The function attempts to validate the file, and if it is valid, it
        displays a graph on the screen and sets up the packet filter.
        """
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setFilter(QDir.Files)

        if dialog.exec_():
            file_name = dialog.selectedFiles()
            self._widget_pointers["le_packet_config"].setText(file_name[0])

            # File validation. Only checks whether the graph can be constructed.
            if file_name[0].endswith(".json"):
                with open(file_name[0], "r") as f:
                    packet_config = self._is_config_valid(json.load(f))
                    # if packet_config is not None:
                    # self._add_graph(packet_config)
                    f.close()
            else:
                self._raise_error("Invalid file type.")

    def _add_graph(self, data):
        # Remove any existing widgets first.
        for i in reversed(range(self._widget_pointers["graph_layout"].count())):
            widgetToRemove = self._widget_pointers["graph_layout"].itemAt(i).widget()
            # Remove it from the layout list.
            self._widget_pointers["graph_layout"].removeWidget(widgetToRemove)
            # Remove it from the gui.
            widgetToRemove.setParent(None)

        # Construct the graph.
        self.graph = Graph(
            title=data["graph_params"]["title"],
            xAxisLabel=data["graph_params"]["x_axis"],
            yAxisLabel=data["graph_params"]["y_axis"],
            series={
                "packetData": {
                    "data": {"x": [], "y": []},
                    "multiplier": 1,
                    "color": (255, 0, 0),
                },
                "list": ("packetData",),
            },
        )

        # Add graph widget to the layout.
        self._widget_pointers["graph_layout"].addWidget(
            self.graph.get_layout(), 0, 0, 1, 1
        )

    def _remove_graph(self):
        """
        Sets the graphing region to a label asking to set the packet configuration.
        """
        for i in reversed(range(self._widget_pointers["graph_layout"].count())):
            widgetToRemove = self._widget_pointers["graph_layout"].itemAt(i).widget()
            # Remove it from the layout list.
            self._widget_pointers["graph_layout"].removeWidget(widgetToRemove)
            # Remove it from the gui.
            widgetToRemove.setParent(None)

        label = QLabel("No packet configuration selected.")
        label.setStyleSheet("QLabel { color : white; }")
        self._widget_pointers["graph_layout"].addWidget(label, 0, 0, 1, 1)

        self.graph = None

    def _apply_data_to_graph(self, packet):
        """
        Take a packet and use the config file, if any, to add to the graph.
        Additionally, adds the packet to a data structure for future saving.
        """
        self.graph.addPoint("packetData", packet["x"], packet["y"])

    # Packet management.
    def _parse_packet(self):
        """
        TODO: this
        Take all current bytes to parse, and pull out the first packet and/or text.
        """

        # Parse according to config, generically.

        # By default, we pass the bytes unimpeded as text and the packet with a
        # data of 0. All data is cleared.
        text = self._bytes_to_parse.decode("utf-8")
        packet = {"x": self._cycle, "y": 0}
        self._bytes_to_parse = bytearray()
        return packet, text

    def _send_packet(self):
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

    def _save_packets(self):
        """
        Checks storage of all packets, filters them if a filter is in place, then
        stashes them as a CSV.
        """
        pass

    def _is_config_valid(self, config):
        print("Testing", config)
        packet_config = {"graph_params": {}, "packet_format": {}}
        try:
            # Check graph parameters.
            graph_params = config["graph_params"]
            if type(graph_params["title"]) is str:
                packet_config["graph_params"]["title"] = graph_params["title"]
            else:
                raise Exception("Title must be a string.")

            if type(config["graph_params"]["x_axis"]) is str:
                packet_config["graph_params"]["x_axis"] = graph_params["x_axis"]
            else:
                raise Exception("X-axis must be a string.")

            if type(graph_params["y_axis"]) is str:
                packet_config["graph_params"]["y_axis"] = graph_params["y_axis"]
            else:
                raise Exception("Y-axis must be a string.")

            # Check packet format.
            packet_format = config["packet_format"]
            if packet_format["type"] in [0, 1, 2, 3]:
                packet_config["packet_format"]["type"] = packet_format["type"]
            else:
                raise Exception("Type should be [0, 1, 2, 3].")

            if packet_format["type"] == 0:
                pass
            elif packet_format["type"] == 1:
                pass
            else:
                # Header order must only be ["ID", "DATA"] or ["DATA", "ID"]
                if packet_format["header_order"] is list:
                    pass
                else:
                    raise Exception("Header order should be a list.")

                # Header length must be integers > 0 for both indexes.
                if packet_format["header_len"] is list:
                    pass
                else:
                    raise Exception("Header order should be a list.")

                # Packet IDs must be a list of strings that can be converted
                # into hex/binary/dec.
                if packet_format["packet_ids"] is list:
                    pass
                else:
                    raise Exception("Header order should be a list.")

        except Exception as e:
            print("Exception:", e)
            self._raise_error("INV_CFG")
            return None

        print(packet_config)
        return packet_config
