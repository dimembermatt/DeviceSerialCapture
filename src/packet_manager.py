"""
packet_manager.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 05/14/21
Last Modified: 05/14/21

Description: Implements the PacketManager class, which collects, sorts, and
manages serial data packets.
"""

from collections import OrderedDict
import csv
import datetime


class PacketManager:
    """
    The PacketManager class manages serial data packets. It has the ability to
    capture, sort, and save packets for visualization or analysis.
    """

    def __init__(self):
        # The packets collected over the course of the program lifetime. Packets
        # are sorted by type, and then by capture time.
        self._packets = OrderedDict()
        self._packets["all"] = OrderedDict()

    def insert_packet(self, packet_series, packet_name, packet_data):
        self._packets["all"][packet_name] = packet_data
        if packet_series not in self._packets:
            self._packets[packet_series] = OrderedDict()
        self._packets[packet_series][packet_name] = packet_data

    def remove_packet(self, packet_series, packet_name):
        """
        Removes a packet of a specific type and name from the overall set and
        the specific set, if it exists.

        Parameters
        ----------
        packet_series: Type of the packet.
        packet_name: Unique identifier of the packet.
        """
        if packet_name in self._packets["all"]:
            del self._packets["all"][packet_name]
        if packet_series in self._packets:
            if packet_name in self._packets[packet_series]:
                del self._packets[packet_series][packet_name]

    def get_packet_series(self, packet_series):
        """
        Returns the set of packets associated with a packet type.

        Parameters
        ----------
        packet_series: Type of the packet.

        Returns
        -------
        Ordered dict of the series specified, or None if the packet_series is
        invalid.
        """
        if packet_series in self._packets:
            return self._packets[packet_series]
        return None

    def save_packet_series(self, packet_series):
        """
        Saves the packet_series, if valid, into a CSV organized by order of
        insertion. The CSV has two columns: the packet_name and the packet_data.
        The file is named after the packet_series + the latest timestamp.

        Parameters
        ----------
        packet_series: series to save.
        """
        if packet_series in self._packets:
            with open(packet_series + datetime.datetime.now() + ".csv", "w") as file:
                writer = csv.writer(file, delimiter=",", lineterminator="\n")
                writer.writerow(["key", "value"])
                for key, value in self._packets[packet_series].items():
                    writer.writerow([key, value])
