"""
monitor_view.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 04/29/21
Last Modified: 05/21/21

Description: Implements the MonitorView class, which inherits DisplayView class.
"""
# Library Imports.
import json
from time import sleep
from PyQt5.QtCore import QDir
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QFileDialog
import random
from typing import Any, TypeVar, Union, List, Tuple

# Custom Imports.
from src.display_view import DisplayView
from src.graph import Graph
from src.packet import PacketParser, Packet

# Class Implementation.
class MonitorView(DisplayView):
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
    def __init__(self, controller, framerate):
        """
        Upon initialization, we perform any data and UI setup required to get
        the MonitorView into a default state.

        Parameters
        ----------
        controller : Dict
            Reference to the controller.
        framerate : int
            Framerate of the program (or rather, execution rate).
        """
        super(MonitorView, self).__init__(controller=controller, framerate=framerate)

        self._serial_datastream = self._controller.get_data_pointer("serial_datastream")

        # The packets collected.
        self._packet_parser = PacketParser(None)
        self._packet_man = self._controller.get_data_pointer("packet_manager")

        # Dict referring to graphs in the monitor view.
        self.graphs = {}

        # Setup transmission textbox and send button.
        self._widget_pointers["le_transmit_txt"].returnPressed.connect(
            self._send_packet
        )
        self._widget_pointers["bu_send"].clicked.connect(self._send_packet)

        # Setup save button.
        self._widget_pointers["bu_save"].clicked.connect(self._packet_man.save_all)

        # Setup packet file configuration.
        self._widget_pointers["bu_packet_config_filesearch"].clicked.connect(
            self._get_file_name
        )

        self.init_frame(self._update_console)

    def _update_console(self):
        """
        Performs any required actions at FPS.
        """
        # Capture read data from serial_datastream, if available.
        # bytes_to_parse = b""
        i = random.randint(0, 10)
        bytes_to_parse = (
            b"id:0x632;data:"
            + f"{i}".encode("utf-8")
            + b";id:0x633;data:"
            + f"{i*2}".encode("utf-8")
            + b";"
        )
        while not self._serial_datastream["read_lock"].tryLock(50):
            pass
        # for byte in self._serial_datastream["read"]:
        # bytes_to_parse += bytearray(byte)
        self._serial_datastream["read"].clear()
        self._serial_datastream["read_lock"].unlock()

        if len(bytes_to_parse) > 0:
            # Parse any packets if we can.
            print("\nParsing: ", bytes_to_parse)
            self._packet_parser.append_bytestream(bytes_to_parse)
            packets = self._packet_parser.process_packets()
            print("Packets received:", packets)
            for packet in packets:
                config = self._packet_parser.get_config()
                print("Config:", config)
                if config:
                    # Filter packets.
                    packet = self._filter_packet(packet, config)
                    # Adjust packet_id.
                    packet = self._adjust_packet_id(packet, config)
                # Update packet manager.
                self._packet_man.insert_packet(packet)
                # Update active graphs.
                self._apply_data_to_graph(packet)

                # Update the text edit.
                self._widget_pointers["te_serial_output"].append(packet.plaintext)

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

        sleep(0.3)

    def _filter_packet(self, packet: Packet, config: dict) -> Packet:
        return packet

    def _adjust_packet_id(self, packet: Packet, config: dict) -> Packet:
        graph_definitions = config["packet_format"]["graph_definitions"]
        graph_definition = graph_definitions.get(packet.packet_series)

        # Only look at Y series.
        if graph_definition and graph_definition["y_series"] == packet.packet_series:
            capture_mode = graph_definition.get("capture_mode")
            if capture_mode:
                if capture_mode == "TIME":
                    pass
                elif capture_mode == "IDX":
                    packet.packet_id = self._packet_man.get_series_packet_count(packet.packet_series)
                elif capture_mode == "INLINE":
                    x_series = graph_definition.get("x_series")
                    packet.packet_id = next(reversed(self._packet_man.get_series(x_series).values()))

        return packet

    # Graph management.
    def _add_graph(self, graph_config: dict) -> None:
        """
        Adds an active graph to the UI tabview.

        Parameters
        ----------
        graph_config: Dict
            Parameters of the graph to define.
        """

        # Graphs are keyed by the key: this key should be unique within the
        # configuration json. Each graph is paired with at least one Y series;
        # packets with a matching Y series are identified by graph_config["series"].
        self.graphs[graph_config["key"]] = [Graph(
            series={
                "packetData": {
                    "data": {"x": [], "y": []},
                    "multiplier": 1,
                    "color": tuple(graph_config["color"]),
                },
                "list": ("packetData",),
            },
            graphType=graph_config["graph_type"],
            xAxisLabel=graph_config["x_axis"],
            yAxisLabel=graph_config["y_axis"],
            title=graph_config["title"],
        ), graph_config["y_series"]]

        # Add graph widget to the layout.
        widget = self.graphs[graph_config["key"]].get_layout()
        self._widget_pointers["tab_packet_visualizer"].addTab(
            widget, graph_config["title"]
        )

    def _remove_graph(self):
        """
        TODO: Sets the graphing region to a label asking to set the packet configuration.
        """
        pass

    def _apply_data_to_graph(self, packet):
        """
        Take a packet and use the config file, if any, to add to the graph.
        Additionally, adds the packet to a data structure for future saving.

        Parameters
        ----------
        packet : Packet
            Adds a packet to an active graph.
        """
        try:
            print("PACKET", packet)
            print("SERIES", packet.packet_series)
            print("ID", packet.packet_id)
            print("DATA", packet.packet_value)
            print("GRAPHS", self.graphs)
            for graph in self.graphs.values():
                print("Graph series:", graph[1])
                if packet.packet_series in int(graph[1]):
                    graph.addPoint(
                        "packetData", packet.packet_id, float(packet.packet_value)
                    )
        except:
            pass

    # Packet management.
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

    def _add_packet_config(self, config):
        """
        Attempts to add a packet configuration filter to the program.

        Parameters
        ----------
        config : Dict
            Configuration generated from the json file.
        """

        def is_valid(key: str, loc: dict, val_type) -> bool:
            return key in loc and type(loc[key]) is val_type

        # Check for mandatory packet_title.
        if not is_valid("packet_title", config, str):
            self.raise_error("Invalid config packet title.")
            return

        # Check for mandatory packet_format.
        if not is_valid("packet_format", config, dict):
            self.raise_error("Invalid packet format.")
            return

        # Check fields in packet_format.
        subconfig = config["packet_format"]
        if not is_valid("type", subconfig, int) or subconfig["type"] not in [
            0,
            1,
            2,
            3,
        ]:
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

        if is_valid("graph_definitions", subconfig, dict):
            # Clear prior graphs from the monitor view.
            self._widget_pointers["tab_packet_visualizer"].clear()

            # Check each entry in graph_definitions.
            for entry in subconfig["graph_definitions"]:
                graph_definition = subconfig["graph_definitions"][entry]
                graph_config = {
                    "key": entry,
                    "title": entry,
                    "x_axis": "Packet Idx",
                    "x_series": None,
                    "y_axis": "Unconfigured",
                    "y_series": None,
                    "capture_mode": "IDX",
                    "graph_type": "Line",
                    "color": (255, 255, 255),
                }

                # Plot Title.
                if is_valid("title", graph_definition, str):
                    graph_config["title"] = graph_definition["title"]

                # Plot Type.
                if is_valid("use_scatter", graph_definition, bool):
                    if graph_definition["use_scatter"] is True:
                        graph_config["graph_type"] = "Scatter"

                # X axis.
                if is_valid("x", graph_definition, dict):
                    x_config = graph_definition["x"]

                    if is_valid("use_time", x_config, bool):
                        if x_config["use_time"] is True:
                            graph_config["x_axis"] = "Time (ns)"
                            graph_config["capture_mode"] = "TIME"

                    if is_valid("packet_id", x_config, str):
                        if x_config["packet_id"] in subconfig["packet_ids"]:
                            graph_config["x_axis"] = x_config["packet_id"]
                            graph_config["capture_mode"] = "INLINE"

                    if is_valid("x_axis", x_config, str):
                        graph_config["x_axis"] = x_config["x_axis"]

                # Y axis.
                if is_valid("y", graph_definition, dict):
                    y_config = graph_definition["y"]

                    if is_valid("packet_id", y_config, str):
                        if y_config["packet_id"] in subconfig["packet_ids"]:
                            graph_config["y_series"] = y_config["packet_id"]

                    if is_valid("y_axis", y_config, str):
                        graph_config["y_axis"] = y_config["y_axis"]

                    if is_valid("color", y_config, list):
                        graph_config["color"] = y_config["color"]

                self._add_graph(graph_config)
                subconfig["graph_definitions"][entry] = graph_config

        # Passing all mandatory checks, update the packet_config dict with the
        # newest config.
        self._controller.set_data_pointer("packet_config", config)

        # Then update the packet manager.
        self._packet_parser.set_config(config)
        print("Set config:", config)

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

    def _send_packet(self):
        """
        Pushes data to be written into the serial_datastream.
        """
        # Check if there is text in the line edit.
        text = self._widget_pointers["le_transmit_txt"].text()
        status = self._controller.get_data_pointer("status")
        if text and status == "CONNECTED":
            # Lock the write FIFO and append to queue, then unlock.
            while not self._serial_datastream["write_lock"].tryLock(200):
                pass
            self._serial_datastream["write"].append(text.encode("utf-8"))
            self._serial_datastream["write_lock"].unlock()

            # Echo to the text edit.
            text = MonitorView.SPAN_BLUE[0] + text + MonitorView.SPAN_BLUE[1]
            self._widget_pointers["te_serial_output"].append(text)
        # Echo errors to the text edit.
        elif status != "CONNECTED":
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
