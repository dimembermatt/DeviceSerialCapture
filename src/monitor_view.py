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
from PyQt5.QtGui import QColor, QPalette, QTextCursor
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
from src.packet_manager import PacketManager
from src.packets import Packets


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
        the MonitorView into a default state.

        Parameters
        ----------
        data_controller : Dict
            Reference to the data controller.
        framerate : int
            Framerate of the program (or rather, execution rate).
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

        self.init_frame(self._update_console)

        # The packets collected.
        self._packet_man = self._data_controller["packet_manager"]

        # The bytes that have yet to be parsed.
        self._bytes_to_parse = bytearray()

    def _update_console(self):
        """
        Performs any required actions at FPS.
        """
        # Capture read data from serial_datastream, if available.
        while not self._serial_datastream["read_lock"].tryLock(50):
            pass
        for byte in self._serial_datastream["read"]:
            self._bytes_to_parse += bytearray(byte)
        self._serial_datastream["read"].clear()
        self._serial_datastream["read_lock"].unlock()

        if len(self._bytes_to_parse) > 0:
            # Parse any packets if we can.
            self._bytes_to_parse, packets_parsed = self._parse_packet(
                self._bytes_to_parse
            )

            # TODO: Update the active graphs and the text edit based on packets in
            # the packet_man.
            print("Packets:", packets_parsed)
            for packet in packets_parsed:
                # Update active graphs.

                # Update the text edit.
                self._widget_pointers["te_serial_output"].append(packet["text"])
            self._widget_pointers["te_serial_output"].moveCursor(QTextCursor.End)

        # Capture status data from serial_datastream and display on textedit.
        if not self._serial_datastream["status_lock"].tryLock(50):
            return

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
            self.raise_error(errors[0])

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
                    data = json.load(f)
                    # load into a packet configuration.
                    self._add_packet_config(data)
                    f.close()
            else:
                self.raise_error("Invalid file type.")

    def _add_graph(self, data):
        """
        Adds an active graph to the UI tabview.

        Parameters
        ----------
        data : TODO: this
        """
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

        Parameters
        ----------
        packet : Dict
            Adds a packet to an active graph.
        """
        self.graph.addPoint("packetData", packet["x"], packet["y"])

    # Packet management.
    def _add_packet_config(self, config):
        """
        Attempts to add a packet configuration filter to the program.

        Parameters
        ----------
        config : Dict
            Configuration generated from the json file.
        """
        # Check for mandatory packet_title.
        if "packet_title" not in config or type(config["packet_title"]) is not str:
            self.raise_error("Invalid config packet title.")
            return

        # Check for mandatory packet_format.
        if "packet_format" not in config or type(config["packet_format"]) is not dict:
            self.raise_error("Invalid packet format.")
            return

        # Check fields in packet_format.
        subconfig = config["packet_format"]
        if (
            "type" not in subconfig
            or type(subconfig["type"]) is not int
            or subconfig["type"] not in [0, 1, 2, 3]
        ):
            self.raise_error("Invalid packet type.")
            return

        if subconfig["type"] == 0:
            # Check for mandatory packet_delimiters, and packet_ids.
            if not self._valid_packet_config_helper(
                subconfig, str, "packet_delimiters", "packet_delimiters"
            ) or not self._valid_packet_config_helper(
                subconfig, str, "packet_ids", "packet_ids"
            ):
                return

            # Check for optional data_delimiters and ignore strings.
            if not self._valid_packet_config_helper(
                subconfig, str, "data_delimiters", "data_delimiters"
            ):
                subconfig["data_delimiters"] = []

            if not self._valid_packet_config_helper(subconfig, str, "ignore", "ignore"):
                subconfig["ignore"] = []

        elif subconfig["type"] == 1:
            # Check for mandatory packet_delimiters, packet_ids, and specifiers.
            if (
                not self._valid_packet_config_helper(
                    subconfig, str, "packet_delimiters", "packet_delimiters"
                )
                or not self._valid_packet_config_helper(
                    subconfig, str, "packet_ids", "packet_ids"
                )
                or not self._valid_packet_config_helper(
                    subconfig, str, "specifiers", "specifiers"
                )
            ):
                return

            # Check for optional data_delimiters.
            if not self._valid_packet_config_helper(
                subconfig, str, "data_delimiters", "data_delimiters"
            ):
                subconfig["data_delimiters"] = []

        elif subconfig["type"] == 2 or subconfig["type"] == 3:
            # Check for mandatory header_order, header_len, and packet_ids.
            if (
                not self._valid_packet_config_helper(
                    subconfig, str, "header_order", "header_order"
                )
                or not self._valid_packet_config_helper(
                    subconfig, int, "header_len", "header_len"
                )
                or not self._valid_packet_config_helper(
                    subconfig, str, "packet_ids", "packet_ids"
                )
            ):
                return

        if (
            "graph_definitions" not in subconfig
            or type(subconfig["graph_definitions"]) is not list
        ):
            # Check each entry in graph_definitions.
            for entry in subconfig["packet_ids"]:
                if entry not in subconfig["graph_definitions"]:
                    subconfig["graph_definitions"][entry] = {
                        "title": "Unconfigured",
                        "x_axis": "Unconfigured",
                        "y_axis": "Unconfigured",
                    }
                else:
                    graph_config = subconfig["graph_definitions"][entry]
                    if (
                        "title" not in graph_config
                        or type(graph_config["title"]) is not str
                    ):
                        graph_config["title"] = "Unconfigured"
                    if (
                        "x_axis" not in graph_config
                        or type(graph_config["x_axis"]) is not str
                    ):
                        graph_config["x_axis"] = "Unconfigured"
                    if (
                        "y_axis" not in graph_config
                        or type(graph_config["y_axis"]) is not str
                    ):
                        graph_config["y_axis"] = "Unconfigured"

        # Passing all mandatory checks, update the packet_config dict with the
        # newest config.
        self._data_controller["packet_config"] = config
        print(self._data_controller["packet_config"])

    def _valid_packet_config_helper(self, config, type, key, error=None):
        """
        Validate three things:
        - Whether a given key exists in a presumed dictionary called config
        - Whether the value associated with the key is a list
        - Whether elements in that list are all of a given type

        Upon failure, return an error code.

        Parameters
        ----------
        config: Dict
            Dictionary of the packet to check.
        type: Type
            Type of value to check in the list.
        key: Str
            Key in the dictionary to check.
        error: None/Str
            Optional error message to display if something should be done.
        """
        if (
            key not in config
            or not isinstance(config[key], list)
            or any(not isinstance(el, type) for el in config[key])
        ):
            if error is not None:
                self.raise_error("Invalid " + error + ".")
            return False
        return True

    def _parse_packet(self, curr_bytes):
        """
        Take all current bytes to parse, pull, out the first relevant packet,
        and insert into the packet manager.

        Parameters
        ----------
        curr_bytes: ByteArray
            Bytes that have yet to be parsed.

        Returns
        -------
        (ByteArray, [Dict]) Remaining bytes that have not been parsed and a list
        of dictionaries representing packets that were parsed.

        Parsed packets have the following format:
        - text: the plaintext value.
        - series: the packet series the packet belongs to.
        - name: the x value mapped to the data.
        - data: the y value, or data of the packet.

        By default, no packet configuration set results in only a default packet
        being generated for returning the plaintext value of curr_bytes.
        """
        obj_packets = Packets(curr_bytes, self._data_controller["packet_config"])
        packets = obj_packets.get_packets()
        for packet in packets:
            self._packet_man.insert_packet(
                packet["series"], packet["name"], packet["data"]
            )
        return (obj_packets.get_cleaned_bytestream(), packets)

    def _send_packet(self):
        """
        Pushes data to be written into the serial_datastream.
        """
        # Check if there is text in the line edit.
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
        Saves all possible series in the packet_manager as csv files.
        """
        for series in self._packet_man.get_all_packet_series():
            self._packet_man.save_packet_series(series)
