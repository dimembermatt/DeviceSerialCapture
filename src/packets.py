"""
packet.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 05/17/21
Last Modified: 05/17/21

Description: Implements the Packets class, which consumes a stream of bytes and
converting it into a packet defined by a configuration.
"""

import re
import time


class Packets:
    """
    The Packets class generates packets given a serial stream. A packet is of the
    format:
    {
        "text": str,
        "series": str,
        "name": str,
        "data": Any
    }
    """

    def __init__(self, byte_stream, config):
        """
        Initializes and configures a new packet.

        Parameters
        ----------
        byte_stream : ByteArray
            Bytes to translate into a packet.
        config : Dict
            Packet configuration to consult.
        """
        self._packets = []
        self._byte_stream = byte_stream
        self._cleaned_byte_stream = None
        self._config = config

        if config is not None:
            packet_type = config["packet_format"]["type"]
            if packet_type == 0:
                print("type 0 case")
                # 1. Split the bytearray into packets using the packet_delimiter.
                str_list = self._split_bytes_into_packets()
                print(str_list)

                # 2. Scrub ignored strings from all packets.
                str_list_scrub = []
                for packet in str_list:
                    for ignore_entry in self._config["packet_format"]["ignore"]:
                        packet = packet.replace(ignore_entry, "")
                    str_list_scrub.append(packet)
                print(str_list_scrub)

                # 3. Attempt to split strings via data_delimiters.
                str_list_split = []
                for packet in str_list_scrub:
                    delims = self._config["packet_format"]["data_delimiters"]
                    delims_exp = "|".join(map(re.escape, delims))
                    str_split = re.split(delims_exp, packet)
                    str_list_split.append(str_split)
                print(str_list_split)

                # 4. Check the packets list. Throw out invalid packets.
                valid_packets = []
                for packet in str_list_split:
                    if len(packet) == 2:
                        if packet[0] in self._config["packet_format"]["packet_ids"]:
                            valid_packets.append(
                                {
                                    "text": packet[0] + ": " + packet[1],
                                    "series": packet[0],
                                    "name": "",  # TODO: pass in time of byte arrival.
                                    "data": packet[1],
                                }
                            )
                print("Valid packets:", valid_packets)
                self._cleaned_byte_stream = bytearray()
                self._packets = valid_packets[:-1]
                print("Proposed packets:", self._packets)
                return
            elif packet_type == 1:
                packets = self._split_bytes_into_packets()
                return
            elif packet_type == 2:
                packets = self._split_bits_into_packets()
                return
            elif packet_type == 3:
                packets = self._split_bits_into_packets()
                return

        # Default case. Just capture the entire thing as a string.
        print("Default case")
        self._cleaned_byte_stream = bytearray()
        self._packets = [
            {
                "text": self._byte_stream.decode("utf-8"),
                "series": "all",
                "name": "text",
                "data": 0,
            }
        ]

    def _split_bytes_into_packets(self):
        """
        Splits the bytearray into different packets. Used by packet types 0 and
        1.

        Returns
        -------
        [ByteArray]
            A list of packets split by either delimiter or length definition.
        """
        delims = self._config["packet_format"]["packet_delimiters"]
        delims_exp = "|".join(map(re.escape, delims))
        str_stream = self._byte_stream.decode("utf8")
        packets = re.split(delims_exp, str_stream)
        return packets

    def _split_bits_into_packets(self):
        """
        Splits the bytearray into different packets. Used by packet types 2 and
        3.

        Returns
        -------
        [BitArray]
            A list of packets split by header len.
        """
        return None

    def _remove_ignore(self, str_packet):
        """
        Takes a packet string and cleans out invalid data.

        Parameters
        ----------
        str_packet : Str
            The string representing packet data.

        Returns
        -------
        str/None The valid packet string after cleaning.
        """
        # Strip out ignore_entries.

        # If packet is empty, throw it out.
        if str_packet == "":
            return None
        return str_packet

    def get_packets(self):
        """
        Returns the packets generated, if any.

        Returns
        -------
        [Dict]
            List of Packet dictionaries. Format defined in the class definition.
        """
        return self._packets

    def get_full_bytestream(self):
        """
        Returns the input bytestream.

        Returns
        -------
        ByteArray
            Input ByteArray at generation.
        """
        return self._byte_stream

    def get_cleaned_bytestream(self):
        """
        Returns the input bytestream sans the bytes used for the packets.

        Returns
        -------
        ByteArray
            Remaining ByteArray after extracting n packets from it.
        """
        return self._cleaned_byte_stream
