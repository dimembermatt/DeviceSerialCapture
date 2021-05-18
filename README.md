# Device Serial Capture (DeSeCa)

DeSeCa is a customizable application for capturing formatted serial packets
from different devices and visualizing it. Users can load specific serial
configurations and packet configurations and monitor traffic from their
laptop over USB.

This was created from 04/29/21 to 05/01/21 to use in my personal applications,
namely:
- [IV Curve Tracer](https://github.com/lhr-solar/Array-CurveTracerPCB) packet
  capture
- [RASWare](https://github.com/ut-ras/Rasware) student distance sensor
  visualization
- Senior Design LoRa Network testing
- And a couple others I can't divulge

## Resources

- https://programmer.group/python-uses-pyqt5-to-write-a-simple-serial-assistant.html
- https://en.wikipedia.org/wiki/Serial_port
- https://learn.sparkfun.com/tutorials/serial-communication/all

## Recommended Alternatives

- https://github.com/Serial-Studio/Serial-Studio:
    - This is a beautiful, highly fleshed out application, with a lot of bells
      and whistles. However, it needs to be built from source and may be too
      complicated for the first time beginner. I recommend more experienced
      students or users to play with this.

## Optional features
- color code option for packets

## Current known bugs
- Freeze up on packet selection

---
## Device Configuration File Formats

The device configuration file format is an optional file that can load your
preset settings for your device on the fly. You can just as easily use the
dropdown menus to set your device, but this might be handy if you have a bunch
of devices with different configurations and can't remember them all.

### Format
```c++
{
    "name": string,                             // OPTIONAL
    "port_name": string,                        // OPTIONAL, default first listed by `..list_ports.comports()`
    "baud_rate": int,                           // OPTIONAL, default 115200
    "data_bits": "FIVE"/"SIX"/"SEVEN"/"EIGHT",  // OPTIONAL, default EIGHT
    "endian": "LSB"/"MSB",                      // OPTIONAL, default LSB
    "sync_bits": "ONE"/"TWO",                   // OPTIONAL, default 1
    "parity_bits": "None"/"Odd"/"Even"          // OPTIONAL, default NONE
}
```

### Examples
```json
// Without port name specified.
{
    "name": "Default Serial Configuration for an arduino device running at 115200 baud.",
    "baud_rate": 115200,
    "data_bits": "EIGHT",
    "endian": "LSB",
    "sync_bits": "ONE",
    "parity_bits": "None"
}

// With port name specified.
{
    "name": "RTD Sensor",
    "port_name": "/dev/ttyUSB0",
    "baud_rate": 115200,
    "data_bits": "EIGHT",
    "endian": "LSB",
    "sync_bits": "ONE",
    "parity_bits": "None"
}
```

Note that if you specify the port_name in your file, it might not be correct at
the time of you plugging the device into your USB port. The application has a
10s timer to update the port config to the list of active devices.

---
## Packet Configuration File Formats

Packet configuration files are very useful for filtering out your data and for
visualizing the data on the fly. A packet configuration file, when loaded, will
initialize a graph to display your packet data vs time.

A couple types of packet configurations are supported. They are are in order of
decreasing human readability and increasing data rate (i.e. they take up less
space and are typically faster to process, so you can send more of these at once).
- Type 0: "Human Readable Format"
- Type 1: "Compressed CSV Format"
- Type 2: "Encoded Chars Format"
- Type 3: "Encoded Bit Format"

### Format
```json
{
    "packet_title": str,            // MANDATORY
    "packet_description": str,      // OPTIONAL
    "example_line": str,            // OPTIONAL
    "packet_format": {              // MANDATORY
        "type": int,                // MANDATORY

        // type 0
        "packet_delimiters": [str], // MANDATORY
        "packet_ids": [str],        // MANDATORY
        "data_delimiters": [str],   // OPTIONAL
        "ignore": [str],            // OPTIONAL
        
        // type 1
        "packet_delimiters": [str], // MANDATORY
        "packet_ids": [str],        // MANDATORY
        "specifiers": [str],        // MANDATORY
        "data_delimiters": [str],   // OPTIONAL

        // type 2, 3
        "header_order": [str],      // MANDATORY
        "header_len": [int],        // MANDATORY
        "packet_ids": [str],        // MANDATORY

        "graph_definitions": {      // OPTIONAL
            "id": {
                "title": str,       // OPTIONAL
                "x_axis": str,      // OPTIONAL
                "y_axis": str       // OPTIONAL
            }
        }
    }
}
```

---

### Packet Graphs

Packet graphs offer a real time display of the packets entering the system.
These are defined in key-value pair `"graph_definitions"`, and are optional.
Each entry in the dictionary must correspond to the entries in the
`"packet_ids"` list; whenever a packet with a matching ID is found, the
corresponding graph, if any, is updated. 

---

### Type 0: "Human Readable Format"

This packet type is primarily for interpreting human readable serial output
from the serial monitor. The format trades data efficiency for readability. It
doesn't work very well at high frequencies (i.e. using Serial.print() every ms).

- `packet_delimiters`: Characters or Strings used to split all types of packets
  from each other. These are typically whitespace characters.
- `packet_ids`: Packet IDs identify all packets that should be captured; packets
  not matching this list are scrubbed.
- `data_delimiters`: All strings in this list are used to split the packet into
  two halves: the ID and data. They are scrubbed during parsing.
- `ignore`: Any strings encountered in this list are removed from the data
  packets screened by `packet_ids`.

#### Example

An example stream of input from the device might be the following:

```css
motor speed: 200 rpm\nmotor speed: 215 rpm\nhello world\nmotor speed: 199 rpm\n
```

It should be pretty clear that there are two types of messages:
- a message displaying the motor speed: `motor speed: xxx rpm`
- a hello world message: `hello world`

These messages are delimited by the newline character, `\n`.

Say we want to ignore all `hello world` messages, and just capture the motor
speed. Our configuration format will be as follows:

```json
{
    "packet_title": "Motor speed packet.",
    "example_line": "motor speed: 200 rpm\nmotor speed: 215 rpm\nhello world\nmotor speed: 199 rpm\n",
    "packet_format": {
        "type": 0,
        "packet_delimiters": ["\n"],
        "packet_ids": ["motor speed"],
        "data_delimiters": [": "],
        "ignore": [" rpm"],
        "graph_definitions": {
            "motor speed": {
                "title": "Motor speed over time.",
                "x_axis": "Time (ms)",
                "y_axis": "RPM"
            }
        }
    }
}
```

This packet format splits packets by the newline, `\n`, and splits each packet
into an ID component and DATA component to the left and right of the
data_delimiters, `" : "`, respectively. We discard all packets with an ID
component that is not `motor speed`, and finally we scrub `" rpm"` from all DATA
components remaining.

---

### Type 1: "Compressed CSV Format"

The __Type 1__ format attempts to standardize device output for many competing
sources. All sources of data are submitted with an ID and DATA field.

This packet type revolves around the following format:

`<header><data_delimiter><val><packet_delimiter>`

Each packet must have these four fields. The `<header>` is a string that either
identifies the packet is specifying an ID or DATA.

- `packet_delimiters`: Characters or Strings used to split all types of packets
  from each other. These are typically semicolons or commas (thus the misnomer,
  'CSV' in the type name).
- `packet_ids`: Packet IDs identify all packets that should be captured; packets
  not matching this list are scrubbed.
- `specifiers`: These specifiers identify the different fields in each packet.
    - The first position in the list is the ID - it specifies the source of the
    packet.
    - The second position in the list is the DATA - it specifies the value being
    emitted by the source to measure.
    - Other specifiers are currently not supported for now. Perhaps more than
      one DATA field can be supported. Alternatively, you can just specify
      multiple packet_ids for the same source, i.e. RTD_TEMP, RTD_MOD_TEMP.
- `data_delimiters`: All strings in this list are used to split the packet into
  its specifiers. They are scrubbed during parsing.

#### Example

An example stream of input from the device might be the following:

```css
id:temp;data:128;id:light;data:8000;
```

We have two types of messages here: 
- a temperature measurement message `id:temp;data:128;`
- a light measurement message `id:light;data:8000;`

Say we only want the temperature measurement messages. The configuration format
would be as follows:

```json
{
    "packet_title": "Temperature data packet.",
    "example_line": "id:temp;data:128;id:light;data:8000;",
    "packet_format": {
        "type": 1,
        "packet_delimiters": [";"],
        "packet_ids": ["temp"],
        "specifiers": ["id", "data"],
        "data_delimiters": [":"],
        "graph_definitions": {
            "temp": {
                "title": "Temperature over time.",
                "x_axis": "Time (ms)",
                "y_axis": "Temp (C)"
            }
        }
    }
}
```

This packet format splits packets by the semicolon, `;`, and splits each packet
into an ID component and DATA component to the left and right of the
data_delimiters, `:`, respectively. We say that every packet with an ID
component `id` has a DATA component specifying the source ID. Every packet with
an ID component `data` has a DATA component specifying the source data. We
assume that any packet with an ID component `data` must follow a packet with an
ID component `id`. If not, the current packet and any other packets before it
waiting for a completion are thrown out. Finally, only packets with `temp` are
accepted.

---

### Type 2: "Encoded Chars Format"

Compared to the __Type 1__ format, the __Type 2__ format has a device streaming
a series of bytes, and every X bytes represents a packet. The user then
identifies the sections of the packet, in order, and the byte length of each
section. 

This packet type revolves around the following format:

`<ID><DATA>`

Where ID and DATA are fixed byte lengths. ID and DATA positions can be swapped.

- `header_order`: This list specifies the sections inside the packet. For now,
  only the "ID" and "DATA" sections are supported, but feel free to submit a
  patch to add more sections.
- `header_len`: This list specifies the length of each section inside of the
  packet. The minimum section length is 1 byte for now. For more compressed
  encodings, see the __intrapacket format__.
- `packet_ids`: Packet IDs identify all packets that should be captured; packets
  not matching this list are scrubbed.

#### Example

An example stream of input from the device might be the following:

```css
432000072FF
```

This is incomprehensible to the average reader. This is actually an encoded CAN
message, of the format:

`[CAN ID][CAN DATA]`

Where the CAN ID is 11 bits wide (but extended to 12 bits/3 bytes) and the CAN
DATA is 8 bytes wide (a 32 bit integer).

Of course, this is all stripped from the CAN standard data frame, leaving only
the essential data.

The decoded data might be the following:

```json
CAN ID: 0x432     ->  ID:  Miles driven
CAN DATA: 0x72FF  ->  Val: 29,439 miles
```

Anyways, the configuration would look like this:

```json
{
    "packet_title": "Miles driven packet.",
    "example_line": "432000072FF00000000000",
    "packet_format": {
        "type": 2,
        "header_order": ["ID", "DATA"],
        "header_len": [3, 8],
        "packet_ids": ["0x432"],
        "graph_definitions": {
            "0x432": {
                "title": "Miles driven over time.",
                "x_axis": "Time (s)",
                "y_axis": "Miles Driven"
            }
        }
    }
}
```

This configuration tells us the ID comes first in the packet, followed by the
DATA. The ID is 3 bytes wide, and the DATA is 8 bytes wide. Both fields are
converted into hex values. Only packets with the `ID = 0x432` should be
captured, and the rest thrown away.

Note that all packets must be of these specifications for header order and
length. You can't match packets of different data lengths.

---

### Type 3: "Encoded Bits Format"

Finally, __Type 3__ format is an extreme version of __Type 2__ format; instead
of bytes you can specify the specific bits across a stream of bits to represent
your ID and DATA.

It's essentially the same as __Type 2__, except the `header_len` entries
represent bits, not bytes.
