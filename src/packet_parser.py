"""
packet_parser.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 05/17/21
Last Modified: 05/21/21

Description: Implements the PacketParser class, which consumes a stream of bytes
and converts them into readable packets defined by a configuration.

 - TODO:Does not handle packet sizes of 5, 6, or 7 bits. Might want to do bit
   padding.
"""
# Library Imports.
import re

# Class Implementation.
class PacketParser:
    """
    The PacketParser class generates a set of packets given a serial stream.
    A packet is of the format:
    {
        "text": str,    # Plaintext equivalent of the packet.
        "series": str,  # Series the packet belongs to, defined by a config.
        "x_val": int,   # The independent variable of the packet.
        "y_val": Any    # The dependent variable of the packet.
    }
    """

    def __init__(self, config):
        """
        Initializes and configures a new packet parser.

        Parameters
        ----------
        config : Dict
            Packet configuration to consult.
        """
        self._packet_ID = 0
        self._packets = []
        self._byte_stream = b""
        self._cleaned_byte_stream = None
        self._config = config

    def parse(self, byte_stream):
        """
        Appends the byte_stream to the current set of bytes and updates the list
        of packets to report after parsing it.

        Parameters
        ----------
        byte_stream : ByteArray
            Bytes to translate into a packet.
        """
        self._byte_stream += byte_stream
        if self._config is not None:
            packet_type = self._config["packet_format"]["type"]
            if packet_type == 0:
                # 1. Split the bytearray into packets using the packet_delimiter.
                packets = self._split_bytes_into_packets(
                    self._byte_stream,
                    self._config["packet_format"]["packet_delimiters"],
                )

                # 2. Scrub ignored strings from all packets.
                packets_scrubbed = self._scrub_ignored_strings(
                    packets, self._config["packet_format"]["ignore"]
                )

                # 3. Attempt to split strings via data_delimiters.
                packets_split = self._split_packets_by_data_delims(
                    packets_scrubbed, self._config["packet_format"]["data_delimiters"]
                )

                # 4. Capture incomplete packets from the rear and
                #    re-insert into the cleaned_byte_stream.
                (
                    packets_complete,
                    self._byte_stream,
                ) = self._capture_incomplete_packets_t0(
                    packets_split,
                    packets,
                    self._byte_stream,
                    len(self._config["packet_format"]["data_delimiters"]) + 1,
                )

                # 5. Check the packets list. Throw out invalid packets.
                packets_valid = self._generate_valid_packets_t0(
                    packets_complete,
                    self._config["packet_format"]["packet_ids"],
                    len(self._config["packet_format"]["data_delimiters"]) + 1,
                )

                self._packets += packets_valid
                return
            elif packet_type == 1:
                # 1. Split the bytearray into packets using the packet_delimiter.
                packets = self._split_bytes_into_packets(
                    self._byte_stream,
                    self._config["packet_format"]["packet_delimiters"],
                )

                # 2. Attempt to split strings via data_delimiters.
                packets_split = self._split_packets_by_data_delims(
                    packets,
                    self._config["packet_format"]["data_delimiters"],
                )

                # 3. Order packets by specifiers and trim if necessary.
                packets_ordered = self._sort_packets_by_specifiers(
                    packets_split,
                    self._config["packet_format"]["specifiers"],
                    len(self._config["packet_format"]["data_delimiters"]) + 1,
                )

                # 4. Capture incomplete packets from the rear and
                #    re-insert into the cleaned_byte_stream.
                (
                    packets_complete,
                    self._byte_stream,
                ) = self._capture_incomplete_packets_t1(
                    packets_ordered,
                    packets,
                    self._byte_stream,
                    len(self._config["packet_format"]["data_delimiters"]) + 1,
                )

                # 5. Check the packets list. Throw out invalid packets.
                packets_valid = self._generate_valid_packets_t1(
                    packets_complete,
                    self._config["packet_format"]["packet_ids"],
                    len(self._config["packet_format"]["data_delimiters"]) + 1,
                )

                self._packets += packets_valid
                return
            elif packet_type == 2:
                # TODO: Type 2 parsing using bytearray.
                packets = self._split_bits_into_packets()

                print("\ntype 2 case unimplemented.")

                return
            elif packet_type == 3:
                # TODO: Type 3 parsing usingbitarray.
                packets = self._split_bits_into_packets()

                print("\ntype 3 case unimplemented.")

                return

        # Default case. Just capture the entire thing as a string.
        self._packets.append(
            {
                "text": self._byte_stream.decode("utf-8"),
                "series": "all",
                "x_val": self._packet_ID,
                "y_val": 0,
            }
        )
        self._byte_stream = bytearray()

    def _split_bytes_into_packets(self, byte_stream, delims):
        """
        Splits the bytearray into different packets. Used by packet types 0, 1.

        Parameters
        ----------
        byte_stream : ByteArray
            An array of bytes to split into packets.
        delims : [Str]
            A list of delimiter strings to cut packets with.

        Returns
        -------
        [Str]
            A list of packets split by either delimiter or length definition.
        """
        delims_exp = "|".join(map(re.escape, delims))
        str_stream = byte_stream.decode("utf8")
        packets = re.split(delims_exp, str_stream)
        return packets

    def _scrub_ignored_strings(self, packets, ignored_strings):
        """
        Scrubs a list of strings from a list of potential packets.

        Parameters
        ----------
        packets : [Str]
            A list of packets to scrub.
        ignored_strings : [Str]
            A list of strings to remove from packets.

        Returns
        -------
        [Str]
            A list of packets with ignored_strings scrubbed.
        """
        str_list_scrub = []
        for packet in packets:
            for entry in ignored_strings:
                packet = packet.replace(entry, "")
            str_list_scrub.append(packet)
        return str_list_scrub

    def _split_packets_by_data_delims(self, packets, data_delimiters):
        """
        Splits a list of packets into subpackets using data_delimiters.

        Parameters
        ----------
        packets : [Str]
            A list of packets to split into subpackets.
        data_delimiters : [Str]
            A list of strings to split each packet in packets with.

        Returns
        -------
        [[Str, Str], ...]
            A list of lists split by data_delimiters.
        """
        str_list_split = []
        for packet in packets:
            delims_exp = "|".join(map(re.escape, data_delimiters))
            str_split = re.split(delims_exp, packet)
            str_list_split.append(str_split)
        return str_list_split

    def _sort_packets_by_specifiers(self, packets, specifiers, num_data_delims):
        """
        Sorts a list of split packets into subpackets using specifiers.
        It also checks packets for specifier value; packets must be in order of
        specifiers defined; otherwise they are thrown out until this condition
        is met.

        Parameters
        ----------
        packets : [[Str, Str], ...]
            A list of packets to split into subpackets.
        specifiers : [Str]
            A list of strings identifying ordering of subpackets in a packet.
        num_data_delims : int
            The number of expected subfields for each packet.

        Returns
        -------
        [[Str, Str], ...]
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
        #   - [[id, ''], [data, ''], [id, '']] (Missing next packet.)
        # Throw out the packet (or pair of packets) if one of these rules
        #   fail, save the packets state, and retry.

        # Remove remnant of packet splitting.
        if packets[-1] == [""]:
            packets = packets[:-1]

        # Organize the packets as a stack and build a usable set of packets.
        new_packets = []
        while len(packets) > 0:
            # Using packets like a stack:
            packet_id_candidate = packets.pop(0)
            if len(packets) > 0:
                packet_data_candidate = packets.pop(0)

                # Now that we have two candidates, we look at the two
                # candidates.
                bad_ID = False
                bad_DATA = False

                # Check if ID candidate is correct (Has correct num
                # args, matches specifier)
                if (
                    len(packet_id_candidate) != num_data_delims
                    or packet_id_candidate[0] != specifiers[0]
                ):
                    bad_ID = True

                # Check if DATA candidate is correct (Has correct num
                # args, matches specifier)
                if (
                    len(packet_data_candidate) != num_data_delims
                    or packet_data_candidate[0] != specifiers[1]
                ):
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
                    new_packets.append(packet_id_candidate)
                    new_packets.append(packet_data_candidate)
            else:
                # Only one candidate to look at. Append it for the next round.
                new_packets.append(packet_id_candidate)

        return new_packets

    def _capture_incomplete_packets_t0(
        self, packets, packets_full, byte_stream, num_data_delims
    ):
        """
        Identifies incomplete packets (Typically the last one), and re-inserts
        their bytes back into the cleaned_byte_stream for a later iteration.

        Parameters
        ----------
        packets : [[Str, Str], ...]
            A list of subpackets to check.
        packets_full : [Str]
            A list of packets without string scrubbing.
        byte_stream : ByteArray
            An array of bytes to search for the position of the incomplete
            subpacket.
        num_data_delims : int
            The number of expected subfields for each packet.

        Returns
        -------
        ([[Str, Str], ...], ByteArray)
            The list of subpackets, and the cleaned byte array containing only
            incomplete packets.
        """
        if len(packets[-1]) != num_data_delims:
            return (
                packets[:-1],
                byte_stream[len(byte_stream) - len(packets_full[-1]) :],
            )
        return (packets, bytearray())

    def _generate_valid_packets_t0(self, packets, packet_ids, num_data_delims):
        """
        Generates valid packet information for t0 packet configuration.

        Parameters
        ----------
        packets : [[Str, Str], ...]
            A list of subpackets to convert into valid packet formats.
        packet_ids: [Str]
            A list of relevant packet IDs to capture.
        num_data_delims : int
            The number of expected subfields for each packet.

        Returns
        -------
        [{
            "text": Str,
            "series": Str,
            "x_val": Int,
            "y_val": Any
        }, ...]
            A list of packet metadata for retrieval.
        """
        valid_packets = []
        for packet in packets:
            if len(packet) == num_data_delims:
                if packet[0] in packet_ids and packet[1] != "":
                    valid_packets.append(
                        {
                            "text": packet[0] + ": " + packet[1],
                            "series": packet[0],
                            "x_val": self._packet_ID,
                            "y_val": packet[1],
                        }
                    )
                    self._packet_ID += 1
        return valid_packets

    def _capture_incomplete_packets_t1(
        self, packets, packets_full, byte_stream, num_data_delims
    ):
        """
        Identifies incomplete packets (Typically the last one), and re-inserts
        their bytes back into the cleaned_byte_stream for a later iteration.
        For T1 packet configurations, we also retain the ID subpacket in the
        following case: [[id, ''], [data, ''], [id, '']] (Missing next packet.)

        Parameters
        ----------
        packets : [[Str, Str], ...]
            A list of subpackets to check.
        packets_full : [Str]
            A list of packets without string scrubbing.
        byte_stream : ByteArray
            An array of bytes to search for the position of the incomplete
            subpacket.
        num_data_delims : int
            The number of expected subfields for each packet.

        Returns
        -------
        ([[Str, Str], ...], ByteArray)
            The list of subpackets, and the cleaned byte array containing only
            incomplete packets.
        """
        # Remove remnant of packet splitting.
        comparison_list = packets_full
        if packets_full[-1] == "":
            comparison_list = packets_full[:-1]

        if len(packets) % 2:
            return (
                packets[:-1],
                byte_stream[len(byte_stream) - len(comparison_list[-1]) - 1 :],
            )
        return (packets, bytearray())

    def _generate_valid_packets_t1(self, packets, packet_ids, num_data_delims):
        """
        Generates valid packet information for t1 packet configuration.

        Parameters
        ----------
        packets : [[Str, Str], ...]
            A list of subpackets to convert into valid packet formats.
        packet_ids: [Str]
            A list of relevant packet IDs to capture.
        num_data_delims : int
            The number of expected subfields for each packet.

        Returns
        -------
        [{
            "text": Str,
            "series": Str,
            "x_val": Int,
            "y_val": Any
        }, ...]
            A list of packet metadata for retrieval.
        """
        # We can assume that every even idx packet (0, 2, ...) has the 'id'
        # parameter, and that every odd idx packet (1, 3, ...) has the 'data'
        # parameter. If either of these parameters are paired with a missing
        # throw both packets out.
        valid_packets = []
        for idx in range(0, len(packets), 2):
            packet_id = packets[idx]
            packet_data = packets[idx + 1]

            if (
                len(packet_id) == num_data_delims
                and len(packet_data) == num_data_delims
            ):
                if packet_id[1] in packet_ids and packet_data[1] != "":
                    valid_packets.append(
                        {
                            "text": packet_id[1] + ": " + packet_data[1],
                            "series": packet_id[1],
                            "x_val": self._packet_ID,
                            "y_val": packet_data[1],
                        }
                    )
                    self._packet_ID += 1
        return valid_packets

    def get_packets(self):
        """
        Returns the packets generated, if any.

        Returns
        -------
        [Dict]
            List of Packet dictionaries. Format defined in the class definition.
        """
        packets = self._packets
        self._packets = []
        return packets
