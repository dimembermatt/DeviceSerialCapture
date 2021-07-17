"""
packet.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 07/10/21
Last Modified: 07/12/21
"""
import csv
import os.path
import re
import sys
import time
from abc import ABC
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, TypeVar, Union, List, Tuple

T = TypeVar("T", bound="Packet")


@dataclass
class Packet(ABC):
    """The standard packet IR that is collected by the program."""

    plaintext: str = ""
    packet_series: str = ""
    packet_id: Any = ""
    packet_value: Any = ""

    @classmethod
    def parse(
        cls, bytestream: bytes, _config: dict = None
    ) -> Tuple[Union[List[T], str], bytes]:
        """
        Method called when a byte stream must be parsed into a packet.

        Parameters
        ----------
        bytestream: bytes
            Input bytes that may or may not represent valid packets.
        config: dict
            A dict for guiding parsing. In the following or similar format:
            {
                "type": int,
                "packet_delimiters": [char],
                "packet_ids": [str]
                ...
            }
            Consult the README packet JSON formatting for more information.

        Returns
        -------
        A tuple consisting of:
        - a set of Packet instances on success or a string error on failure.
        - the bytes that were not consumed from the bytestream on packet
          generation.
        """
        packet = Packet(bytestream.decode("utf-8"), "None", time.time_ns(), 0)
        return ([packet], b"")

    @classmethod
    def _split_char_bytestream_into_packets(
        cls, bytestream: bytes, delims: List[str]
    ) -> Tuple[List[str], bytes, bytes]:
        """
        Splits the bytearray into different packets using a set of
        delimiters.

        Parameters
        ----------
        bytestream: bytes
            Input bytes that may or may not represent valid packets.
        delims: [str]
            Delimiters used to split the packets.

        Returns
        -------
        A tuple consisting of:
        - a set of strings consisting of potential packets.
        - bytes that were consumed to make these packets.
        - bytes that were not consumed.
        """
        exp_delimiters = "|".join(map(re.escape, delims))
        str_stream = bytestream.decode("utf-8")
        packets = re.split(exp_delimiters, str_stream)

        # Last entry in packets is typically incomplete; throw it back to the
        # unconsumed bytes list.
        unconsumed = packets[-1].encode("utf-8")
        consumed = bytestream[: len(bytestream) - len(unconsumed)]
        return (packets[:-1], consumed, unconsumed)

    @classmethod
    def _split_packets_by_data_delims(
        cls, packets: List[str], delims: List[str]
    ) -> List[List[str]]:
        """
        Splits packet strings into substrings representing the id and value.

        Parameters
        ----------
        packets: [str]
            A list of packets to split.
        delims: [str]
            A list of delimiters to split packets by.

        Returns
        -------
        [[str]]
            A list of lists representing the packet id, data, and plaintext.
        """
        delims_exp = "|".join(map(re.escape, delims))
        return [re.split(delims_exp, packet) + [packet] for packet in packets]

    @classmethod
    def _split_byte_bytestream_into_packets(
        cls, bytestream: bytes, header_bytes: int
    ) -> Tuple[List[bytes], bytes, bytes]:
        """
        Splits the bytearray into different packets using the total number of
        header bits.

        Parameters
        ----------
        bytestream: bytes
            Input bytes that may or may not represent valid packets.
        header_bytes: int
            The total number of bytes representing the packet length.

        Returns
        -------
        A tuple consisting of:
        - a set of strings consisting of potential packets.
        - bytes that were consumed to make these packets.
        - bytes that were not consumed.
        """
        packets = [
            bytestream[i : i + header_bytes]
            for i in range(0, len(bytestream), header_bytes)
        ]
        # Throw incomplete packets back into the bytestream.
        remainder = len(packets[-1])
        if remainder == header_bytes:
            remainder = 0
        else:
            packets = packets[:-1]
        consumed = len(bytestream) - remainder
        return (packets, bytestream[:consumed], bytestream[consumed:])


class T0_Packet(Packet):
    """
    Innput: byte string representing ASCII, hex, decimal, or boolean values.
    Output: packet_series: Str, packet_id: Time, packet_data: Str
    """

    @classmethod
    def parse(
        cls, bytestream: bytes, config: dict
    ) -> Tuple[Union[List[T], str], bytes]:
        # 1. Split the bytearray into packets using the packet_delimiter field
        #    in the config.
        (
            packets,
            _used_bytes,
            remaining_bytes,
        ) = Packet._split_char_bytestream_into_packets(
            bytestream, config["packet_delimiters"]
        )
        # By now the packets should be in the format: [PLAINTEXT].

        # 2. Scrub all ignored strings from all packets.
        packets = cls._scrub_packets(packets, config["ignore"])
        # By now the packets should be in the format: [PLAINTEXT].

        # 3. Attempt to split strings via data delimiters.
        packets = Packet._split_packets_by_data_delims(
            packets, config["data_delimiters"]
        )
        # By now the packets should be in the format: [[ID, DATA]].

        # 4. Throw out packets not explicitly defined in "packet_ids".
        packets = cls._retain_valid_packets(packets, config["packet_ids"])
        # By now the packets should be in the format: [[ID, DATA]].

        # 5. Generate packets from strings.
        #    The packet_id is adjusted later based on graph_definitions.
        packets = [
            Packet(
                plaintext=packet[0] + ": " + packet[1],
                packet_series=packet[0],
                packet_id=time.time_ns() + idx,
                packet_value=packet[1],
            )
            for idx, packet in enumerate(packets)
        ]
        # By now the packets should be in the format: [Packet].

        return (packets, remaining_bytes)

    @classmethod
    def _scrub_packets(cls, packets: List[str], ignore: List[str]) -> List[str]:
        """
        Scrubs a list of strings from a list of potential packets.

        Parameters
        ----------
        packets : [str]
            A list of packets to scrub.
        ignore : [str]
            A list of strings to remove from packets.

        Returns
        -------
        [str]
            A list of packets with ignore strings scrubbed.
        """

        def scrub(packet: str, ignore: List[str]) -> str:
            for entry in ignore:
                packet = packet.replace(entry, "")
            return packet

        return [scrub(packet, ignore) for packet in packets]

    @classmethod
    def _retain_valid_packets(
        cls, packets: List[List[str]], ids: List[str]
    ) -> List[List[str]]:
        """
        Retain only packets with explicitly defined packet ids.

        Parameters
        ----------
        packets: [[str, str]]
            A list of packets to filter.
        ids: [str]
            A list of ids to filter packets by.

        Returns
        -------
        [[str, str]]
            A list of lists representing the packet id and data.
        """
        return [packet for packet in packets if packet[0] in ids]


class T1_Packet(Packet):
    """
    Innput: byte string representing ASCII, hex, decimal, or boolean values.
    Output: packet_series: Str, packet_id: Time, packet_data: Str
    """

    @classmethod
    def parse(
        cls, bytestream: bytes, config: dict
    ) -> Tuple[Union[List[T], str], bytes]:
        # 1. Split the bytearray into packets using the packet_delimiter field
        #    in the config.
        (
            packets,
            _used_bytes,
            remaining_bytes,
        ) = Packet._split_char_bytestream_into_packets(
            bytestream, config["packet_delimiters"]
        )
        # By now the packets should be in the format: [PLAINTEXT].

        # 2. Attempt to split strings via data delimiters.
        packets = Packet._split_packets_by_data_delims(
            packets, config["data_delimiters"]
        )
        # By now the packets should be in the format: [[NAME, VALUE, PLAINTEXT]].

        # 3. Order packets by specifiers and trim if necessary.
        packets = cls._order_packets_by_specifiers(
            # +1 for unsplit string, len+1 for substrings split by delimiters.
            packets,
            config["specifiers"],
            len(config["data_delimiters"]) + 2,
        )
        # By now the packets should be in the format: [[NAME, VALUE, PLAINTEXT]].

        # 4. Throw out packets not explicitly defined in "packet_ids" and
        #    invalid data packets.
        (packets, unused_packet_bytes) = cls._retain_valid_packets(
            packets, config["packet_ids"]
        )
        # By now the packets should be in the format: [[ID, VALUE]].

        # 5. Generate packets from strings.
        #    The packet_id is adjusted later based on graph_definitions.
        packets = [
            Packet(
                plaintext=packet[0] + ": " + packet[1],
                packet_series=packet[0],
                packet_id=time.time_ns() + idx,
                packet_value=packet[1],
            )
            for idx, packet in enumerate(packets)
        ]
        # By now the packets should be in the format: [Packet].

        # Add back in the packet delimiter.
        bytestream = (
            unused_packet_bytes
            + config["packet_delimiters"][0].encode("utf-8")
            + remaining_bytes
        )
        return (packets, bytestream)

    @classmethod
    def _order_packets_by_specifiers(
        cls, packets: List[List[str]], specifiers: List[str], num_data_delims: int
    ) -> List[List[str]]:
        """
        Sorts a list of split packets into subpackets using specifiers.
        It also checks packets for specifier value; packets must be in order of
        specifiers defined; otherwise they are thrown out until this condition
        is met.

        Parameters
        ----------
        packets : [[str, ...], ...]
            A list of packets to split into subpackets.
        specifiers : [str]
            A list of strings identifying ordering of subpackets in a packet.
        num_data_delims : int
            The number of expected subfields for each packet.

        Returns
        -------
        [[str, ...], ...]
            A list of lists split by data_delimiters.
        """

        # Check the list until all errors are purged.
        # For each packet in the current list, check for the following:
        # - The number of arguments match.
        # - specifiers[0] is first.
        # - specifiers alternate after each other.
        #   - [[id, ''], [data, ''], [id, ''], ... ] (Good)
        #   - [[id, ''], [id, ''], [data, ''], ... ] (Throw out first id)
        #   - [[id, ''], [data, ''], [data, ''], ... ] (Throw out second
        #     data)
        #   - [[id, ''], [data, ''], [id, '']] (Missing next packet, but we
        #     don't check for this.)
        # Throw out the packet (or pair of packets) if one of these rules
        #   fail, save the packets state, and retry.
        def bad_candidate(candidate: str, specifier: str) -> bool:
            return (
                len(candidate) != num_data_delims
                or candidate[0] != specifier
                or candidate[1] == ""
            )

        remaining_packets = []
        while len(packets) > 0:
            packet_id_candidate = packets.pop(0)
            if len(packets) > 0:
                packet_data_candidate = packets.pop(0)

                # Now that we have two candidates, we look at the two
                # candidates.
                bad_ID = False
                bad_DATA = False

                # Check if ID candidate is correct (Has correct num
                # args, matches specifier)
                if bad_candidate(packet_id_candidate, specifiers[0]):
                    bad_ID = True

                # Check if DATA candidate is correct (Has correct num
                # args, matches specifier)
                if bad_candidate(packet_data_candidate, specifiers[1]):
                    bad_DATA = True

                if bad_ID and bad_DATA:
                    # GARBAGE:GARBAGE or DATA:ID; throw the first packet out and
                    # put the second back onto the stack.
                    packets.insert(0, packet_data_candidate)
                elif bad_ID and not bad_DATA:
                    # GARBAGE:DATA or DATA:DATA; throw both packets out.
                    pass
                elif not bad_ID and bad_DATA:
                    # ID:GARBAGE or ID:ID; throw first packet out and put the
                    # second back onto the stack.
                    packets.insert(0, packet_data_candidate)
                else:
                    # ID: DATA; keep both packets and put into our new list.
                    remaining_packets.append(packet_id_candidate)
                    remaining_packets.append(packet_data_candidate)
            else:
                # Only one candidate to look at. Make sure it's an ID packet and
                # then keep it.
                if not bad_candidate(packet_id_candidate, specifiers[0]):
                    remaining_packets.append(packet_id_candidate)

        return remaining_packets

    @classmethod
    def _retain_valid_packets(
        cls, subpackets: List[List[str]], packet_ids: List[str]
    ) -> Tuple[List[List[str]], bytes]:
        """
        Packages ID and DATA subpackets into packets, and filters out packets
        with ids not explicitly specified and data that is null.

        Parameters
        ----------
        packets: [[str, ...], ...]
            Ordered subpackets.
        packet_ids: [str]
            List of packet_ids to be captured.

        Returns
        -------
        ([[int], ...], bytes)
            A list of agglomerated packets, along with a bytestream of
            incomplete subpackets to be reinserted back into the queue.
        """
        valid_packets = []
        bytestream = b""
        while len(subpackets) > 0:
            id_packet = subpackets.pop(0)
            if subpackets:
                data_packet = subpackets.pop(0)
                if id_packet[1] in packet_ids and data_packet[1] != "":
                    valid_packets.append([id_packet[1], data_packet[1]])
            else:
                bytestream = id_packet[2].encode("utf-8")

        return (valid_packets, bytestream)


class T2_Packet(Packet):
    """
    Input: byte string representing hex values.
    Output: packet_series: Int, packet_id: Time, packet_data: Int
    """

    @classmethod
    def parse(
        cls, bytestream: bytes, config: dict
    ) -> Tuple[Union[List[T], str], bytes]:
        # 1. Split packets by header_len.
        (
            packets,
            _used_bytes,
            remaining_bytes,
        ) = Packet._split_byte_bytestream_into_packets(
            bytestream, sum(config["header_len"])
        )
        # By now the packets should be in the format: [bytes].

        # 2. Split by header order.
        packets = cls._split_by_header_order(
            packets, config["header_order"], config["header_len"]
        )
        # By now the packets should be in the format: [[ID(Int), DATA(Int)]].

        # 3. Throw out packets not explicitly defined in "packet_ids" and
        #    invalid data packets.
        packets = cls._retain_valid_packets(packets, config["packet_ids"])
        # By now the packets should be in the format: [[ID(Int), DATA(Int)]].

        # 4. Generate packets from strings.
        #    The packet_id is adjusted later based on graph_definition.
        packets = [
            Packet(
                plaintext=str(packet[0]) + ": " + str(packet[1]),
                packet_series=packet[0],
                packet_id=time.time_ns() + idx,
                packet_value=packet[1],
            )
            for idx, packet in enumerate(packets)
        ]
        # By now the packets should be in the format: [PACKET].

        return (packets, remaining_bytes)

    @classmethod
    def _split_by_header_order(
        cls, packets: List[str], header_order: List[str], header_len: List[List[bytes]]
    ) -> List[List[int]]:
        """
        Splits the packet strings by their headers and maps them together.

        Parameters
        ----------
        packets: [str]
            List of packet strings.
        header_order: [str]
            Headers in parsing order.
        header_len; [int]
            Length of each header, mapped in order.

        Returns
        -------
        [[int], ...]
            A list of packets in order of header order.
        """

        def arrange_packets(
            packet: str, header_order: List[str], header_len: List[int]
        ) -> List[int]:
            list_idx = 0
            result = []
            for header, hlen in zip(header_order, header_len):
                result.append(int(packet[list_idx : list_idx + hlen], base=16))
                list_idx += hlen
            return result

        return [arrange_packets(packet, header_order, header_len) for packet in packets]

    @classmethod
    def _retain_valid_packets(
        cls, packets: List[List[int]], packet_ids: List[str]
    ) -> List[List[int]]:
        """
        Retains and agglomerates valid packets.

        Parameters
        ----------
        packets: [[str]]
            A list of packet dicts, in order of parsing.
        packet_ids: [str]
            List of packet_ids to be captured.

        Returns
        -------
        [[int]]
            A list of lists representing the packet id and data.
        """
        return [
            [packet[0], packet[1]]
            for packet in packets
            if any(packet[0] == int(packet_id, base=16) for packet_id in packet_ids)
        ]


class T3_Packet(Packet):
    """
    Input: bit string representing hex values.
    Output: packet_series: Int, packet_id: Time, packet_data: Int
    """

    @classmethod
    def parse(
        cls, bytestream: bytes, config: dict
    ) -> Tuple[Union[List[T], str], bytes]:
        # 1. Split packets by header_len.
        def round_bits(x):
            return (int)(((x + 7) & -8) / 8)

        (
            packets,
            _used_bytes,
            remaining_bytes,
        ) = Packet._split_byte_bytestream_into_packets(
            bytestream, round_bits(sum(config["header_len"]))
        )
        # By now the packets should be in the format: [bytes].

        # 2. Split by header order.
        packets = cls._split_by_header_order(
            packets, config["header_order"], config["header_len"]
        )
        # By now the packets should be in the format: [[ID(Byte), DATA(Int)]].

        # 3. Throw out packets not explicitly defined in "packet_ids" and
        #    invalid data packets.
        packets = cls._retain_valid_packets(packets, config["packet_ids"])
        # By now the packets should be in the format: [[ID(Int), DATA(Int)]].

        # 4. Generate packets from strings.
        #    The packet_id is adjusted later based on graph_definition.
        packets = [
            Packet(
                plaintext=str(packet[0]) + ": " + str(packet[1]),
                packet_series=packet[0],
                packet_id=time.time_ns() + idx,
                packet_value=packet[1],
            )
            for idx, packet in enumerate(packets)
        ]
        # By now the packets should be in the format: [PACKET].

        return (packets, remaining_bytes)

    @classmethod
    def _split_by_header_order(
        cls, packets: List[str], header_order: List[str], header_len: List[str]
    ) -> List[List[int]]:
        """
        Splits the packet strings by their headers and maps them together.

        Parameters
        ----------
        packets: [str]
            List of packet strings.
        header_order: [str]
            Headers in parsing order.
        header_len; [int]
            Length of each header, mapped in order.

        Returns
        -------
        [{str: str}, ...]
            A list of packet dicts split and mapped by headers.
        """

        def bits_to_value(bin_packet: int, bits_len: int) -> Tuple[str, str]:
            # sub 2 to remove '0b' from string.
            mask = (1 << bits_len) - 1
            captured_bits = bin_packet & mask
            remaining_bits = bin_packet >> bits_len
            return (captured_bits, remaining_bits)

        def arrange_packets(
            packet: str, header_order: List[str], header_len: List[int]
        ) -> List[int]:
            packet = int.from_bytes(packet, "big")
            list_idx = 0
            result = []
            for header, hlen in zip(reversed(header_order), reversed(header_len)):
                (out, packet) = bits_to_value(packet, hlen)
                result.append(out)
                list_idx += hlen
            return result[::-1]

        return [arrange_packets(packet, header_order, header_len) for packet in packets]

    @classmethod
    def _retain_valid_packets(
        cls, packets: List[List[int]], packet_ids: List[str]
    ) -> List[List[int]]:
        """
        Retains and agglomerates valid packets.

        Parameters
        ----------
        packets: [{str}]
            A list of packet dicts, in order of parsing.
        packet_ids: [int]
            List of packet_ids to be captured.

        Returns
        -------
        [[str], ...]
            A list of agglomerated packets.
        """
        return [
            [packet[0], packet[1]]
            for packet in packets
            if any(packet[0] == int(packet_id, base=2) for packet_id in packet_ids)
        ]


class PacketManager:
    """
    Manages storage and sorting of packets for visualization or analysis.
    """

    def __init__(self) -> None:
        """Creates an empty data structure for incoming packets."""
        # The packets collected over the course of the program lifetime. Packets
        # are sorted by series and then by ID.
        self._packets = OrderedDict()

    def insert_packet(self, packet: Packet) -> None:
        """Inserts a packet into the packet manager."""
        if isinstance(packet, Packet):
            series = packet.packet_series
            id = packet.packet_id
            if series not in self._packets:
                self._packets[series] = OrderedDict()
            self._packets[series][id] = packet
        else:
            print(packet)

    def remove_packet(self, packet_series: int, packet_id: int) -> None:
        """Deletes a matching packet if any from the packet manager."""
        if packet_series in self._packets and packet_id in self._packets[packet_series]:
            del self._packets[packet_series][packet_id]

    def get_series(self, packet_series: int) -> OrderedDict:
        """Retrieve a reference to a packet series, organized by packet ID."""
        if packet_series in self._packets:
            return self._packets[packet_series]
        return OrderedDict()

    def get_packet_series(self) -> list:
        """Returns a list of packet series."""
        return list(self._packets.keys())

    def get_series_packet_count(self, series: int) -> int:
        return len(self._packets.get(series, []))
        
    def get_packet_count(self) -> int:
        return sum(len(keys) for keys in self._packets.items())

    def save_all(self) -> None:
        """
        Saves all packet series in the packet manager into individual CSVs. The
        CSVs have two columns: the packet id and packet value. The file is named
        after the packet series and is a folder in output/ named after the
        latest timestamp.
        """
        for series in self._packets:
            self.save_packet_series(series)

    def save_packet_series(self, packet_series: int) -> None:
        """
        Saves the packet_series, if valid, into a CSV organized by order of
        insertion. The CSV has two columns: the packet id and the packet value.
        The file is named after the packet series and is in a folder in output/
        named after the latest timestamp.
        """
        curr_dir = os.getcwd()
        new_dir = os.path.join(curr_dir, r"output/" + time.strftime("%Y%m%d-%H%M%S"))
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)

        if packet_series in self._packets:
            with open(new_dir + "/" + packet_series + ".csv", "w") as file:
                writer = csv.writer(file, delimiter=",", lineterminator="\n")
                writer.writerow(["id", "value"])
                for key, packet in self._packets[packet_series].items():
                    writer.writerow([packet.packet_id, packet.packet_value])

    def _print_internals(self) -> None:
        for key, value in self._packets.items():
            print(f"{key}")
            for key2, value2 in value.items():
                print(f"{key2}\t|{value2}")


class PacketParser:
    """
    Manages parsing of a bytestream to generate packets.
    """

    def __init__(self, config: dict) -> None:
        """
        Sets up the bytestream and configuration settings used for
        parsing.
        """
        self._bytestream = b""
        self._config = config

    def set_config(self, config: dict) -> None:
        """Updates the parser configurations."""
        self._config = config

    def get_config(self) -> dict:
        return self._config

    def clear_bytestream(self, bytestream: bytes) -> None:
        """Clears the internal bytestream from being processed."""
        self._bytestream = b""

    def append_bytestream(self, bytestream: bytes) -> None:
        """Adds a set of bytes to the internal bytestream for processing."""
        self._bytestream += bytestream

    def process_packets(self) -> List[Packet]:
        """Attempts to process a packet from the internal bytestream."""
        if not self._bytestream:
            return []

        if not self._config:
            packets, self._bytestream = Packet.parse(self._bytestream)
            return packets

        # TODO: It would be nice to bump the python version requirement to 3.10
        # and replace this with a match statement.
        packet_type = self._config["packet_format"]["type"]
        if packet_type == 0:
            packets, self._bytestream = T0_Packet.parse(
                self._bytestream, self._config["packet_format"]
            )
            return packets
        elif packet_type == 1:
            packets, self._bytestream = T1_Packet.parse(
                self._bytestream, self._config["packet_format"]
            )
            return packets
        elif packet_type == 2:
            packets, self._bytestream = T2_Packet.parse(
                self._bytestream, self._config["packet_format"]
            )
            return packets
        elif packet_type == 3:
            packets, self._bytestream = T3_Packet.parse(
                self._bytestream, self._config["packet_format"]
            )
            return packets
        else:
            return f"Type {packet_type} is not a supported packet type."


if __name__ == "__main__":
    assert sys.version_info >= (3, 8), "This program only supports Python 3.8+."

    print("T0 TEST\n")
    config = {
        "packet_title": "Type 0 Example",
        "example_line": "sensor = <VAL>\toutput = <VAL>\nsensor = <VAL>\toutput = <VAL>\n",
        "packet_description": "A human readable character stream where packets are split by the tab and newline delimiters. The serial output of Arduino's AnalogInOutSerial sketch. Only the mapped output packets are captured.",
        "packet_format": {
            "type": 0,
            "packet_delimiters": ["\n", "\t"],
            "packet_ids": ["output"],
            "data_delimiters": ["="],
            "ignore": ["\r", " "],
            "graph_definitions": {
                "output": {
                    "title": "Temperature data over time.",
                    "x": {"use_time": True, "x_axis": "Packet idx (1 ms)"},
                    "y": {"packet_id": "output", "y_axis": "Temperature (C)"},
                }
            },
        },
    }
    parser = PacketParser(config)
    pacman = PacketManager()
    parser.append_bytestream(b"sensor = 1\toutput = a\nsensor = 2\toutput = b\n")
    res = parser.process_packet()
    for packet in res:
        pacman.insert_packet(packet)
    pacman._print_internals()

    print("\n----------------------------------------\nT1 TEST\n")
    config = {
        "packet_title": "Type 1 Example",
        "packet_description": "A character stream where packets are split by semicolons; Sources are represented by the specifier 'id', and source data is represented by the specifier 'data'.",
        "example_line": "id:0x632;data:0x88;id:0x632;data:0x44;",
        "packet_format": {
            "type": 1,
            "packet_delimiters": [";"],
            "packet_ids": ["0x632", "0x45"],
            "data_delimiters": [":"],
            "specifiers": ["id", "data"],
            "graph_definitions": {
                "0x632": {
                    "title": "Temperature data over time.",
                    "x": {"use_time": True, "x_axis": "Time (ms)"},
                    "y": {"packet_id": "0x632", "y_axis": "Temperature (C)"},
                }
            },
        },
    }
    parser = PacketParser(config)
    pacman = PacketManager()
    parser.append_bytestream(b"id:0x632;data:0x88;id:0x632;data:0xbb;id:0x45;")
    res = parser.process_packet()
    for packet in res:
        pacman.insert_packet(packet)
    parser.append_bytestream(b"data:0xff;")
    res = parser.process_packet()
    for packet in res:
        pacman.insert_packet(packet)
    pacman._print_internals()

    import math

    def number_to_bytes(num):
        hex_str = format(num, "x")
        hex_len = (int(math.log2(num) / 8) + 1) * 2
        return bytearray.fromhex(hex_str.zfill(hex_len))

    print("\n----------------------------------------\nT2 TEST\n")
    config = {
        "packet_title": "Type 2 Example",
        "packet_description": "A bytestream where every 11 bytes represents a packet. 3 bytes are used to represent the source ID, and 8 bytes are used to represent the source DATA. This is similar to a stripped down version of the CAN standard data frame.",
        "example_line": "0x43200007241",
        "packet_format": {
            "type": 2,
            "header_order": ["ID", "DATA"],
            "header_len": [3, 8],
            "packet_ids": ["0x432"],
            "graph_definitions": {
                "0x432": {
                    "title": "Temperature data over time.",
                    "x": {"use_time": True, "x_axis": "Time (ms)"},
                    "y": {"packet_id": "0x432", "y_axis": "Temperature (C)"},
                }
            },
        },
    }
    parser = PacketParser(config)
    pacman = PacketManager()
    parser.append_bytestream(b"4320000724143200007999434000071104300")
    res = parser.process_packet()
    for packet in res:
        pacman.insert_packet(packet)
    pacman._print_internals()

    print("\n----------------------------------------\nT3 TEST\n")
    config = {
        "packet_title": "Type 3 Example",
        "packet_description": "A bytestream where every 12 bits represents a packet. 4 bits are used to represent the source ID, and 8 bits are used to represent the source DATA.",
        "example_line": "0b0001_1000_1010",
        "packet_format": {
            "type": 3,
            "header_order": ["ID", "DATA"],
            "header_len": [4, 8],
            "packet_ids": ["0b0001"],
            "graph_definitions": {
                "0b0001": {
                    "title": "Temperature data over time.",
                    "x": {"use_time": True, "x_axis": "Time (ms)"},
                    "y": {"packet_id": "0b0001", "y_axis": "Temperature (C)"},
                }
            },
        },
    }
    parser = PacketParser(config)
    pacman = PacketManager()

    def bits_to_bytes(bits, length):
        return bits.to_bytes(length // 8, byteorder="big")

    parser.append_bytestream(
        bits_to_bytes(0b0000_0001_1000_1010_0000_0001_1111_1111, 32)
    )
    res = parser.process_packet()
    if isinstance(res, list):
        for packet in res:
            pacman.insert_packet(packet)
    pacman._print_internals()
