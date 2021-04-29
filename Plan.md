# Device Serial Capture Plan

## Resources

- https://programmer.group/python-uses-pyqt5-to-write-a-simple-serial-assistant.html
- https://en.wikipedia.org/wiki/Serial_port
- https://learn.sparkfun.com/tutorials/serial-communication/all

## Promising alternatives

- https://github.com/Serial-Studio/Serial-Studio

Serial interfacing in pyserial, UI is in PyQt5.

## Known target applications
- Spectroscopy capture
- IV Curve Tracer capture
- Robotathon Distance sensor capture
- Senior Design LoRa Network testing capture
- Other solar car capture boards (CAN Sniffer, telemetry)

## Design

```
tab 1: Configuration screen
-------------------------------
| A | B |                     | <- tabs
|-----------------------------|
| - - - - - - -8- - - - - - - | <- status
|-----------------------------|
|                     |   1   |
|                     |   2   |
| Load Config  OR     |   3   | <- options
|      0              |   4   |
|                     |   5   |
|              7      |   6   |
-------------------------------

tab 2: Capture screen
-------------------------------
| A | B |                     | <- tabs
|-----------------------------|
| - - - - - - -9- - - - - - - | <- status
|-----------------------------|
|              |            13|
|              |              |
|      10      |      14      | <- monitor
|              |              |
|--------------|--------------|
|      11   |12|      15      |
-------------------------------
```

0. Configuration selector, non-editable textbox, opens a file selector.
    - Select a configuration file and populate textbox
    - Fills in boxes on the right after parsing.
1. Port name (i.e. '/dev/ttyUSB0', 'COM3'), textbox & dropdown menu
    - dropdown populated by the following code:
    ```python
    ports = serial.tools.list_ports.comports()

    for port, desc, hwid in sorted(ports):
            print("{}: {} [{}]".format(port, desc, hwid))

    """
    Output: 
    COM3: Stellaris Virtual Serial Port (COM3) [USB VID:PID=1CBE:00FD SER=0E225345 LOCATION=1-1:x.0]
    """
    ```
2. Baud rate (i.e., 19200), textbox & dropdown menu
    - dropdown populated by list of common baud rates:
        - 1200
        - 2400
        - 4800
        - 19200
        - 38400
        - 57600
        - 115200 (default)
3. Data bits per character, textbox & dropdown menu
    - dropdown populated by list of common data bit values
        - 5
        - 6
        - 7
        - 8 (default)
        - 9
4. Data Endianness, dropdown menu
    - dropdown populated by two options
        - LSB (default)
        - MSB
5. Synchronization bits, dropdown menu
    - dropdown populated by list of common options
        - 1 stop bit
        - 2 stop bits
6. Parity bits, dropdown menu
    - dropdown populated by list of common parity types
        - None (default)
        - Odd
        - Even
7. Connect button. Opens up the port and begins listening for packets.
    - Pressing the connect button switches to disconnect text. Pressing 7 again disconnects the program from the serial port.
    - Connecting the program highlights Tab B. Highlight is turned off when Tab is entered.
8. Status dialogue. Non-editable textbox.
    - Displays error result (red bar) when 6 is selected or 0 is loaded:
        - Port does not exist
        - Parsing error in config
            - invalid field
            - missing field
        - Box field is invalid or missing
    - When no error, it can show either Disconnected (grey) or Connected (blue).
9. Status dialogue. Same as above, but error conditions are different.
    - Error when the following occurs:
        - Disconnect happens abruptly (then shift to Disconnect message and color).
        - No text in 11 when ENTER or 12 is pressed.
        - 13 gets an invalid config
            - invalid field
            - missing field
10. Packet monitor. Copyable text box. Data is displayed per character unparsed or parsed.
11. Transmit text box. Use ENTER key or 12 to send. Attempts to send text as characters across serial. Does not work if the receiver is not set up to catch data.
12. Enter button. Submits whatever is in the textbox. If there is nothing in the textbox, nothing is submitted.
13. Visualizer configuration selector, non-editable textbox, opens a file selector.
    - Select a configuration file and populate textbox
    - If valid configuration upon parsing, loads a pyqt time series graph
        - Maybe other types of graphs eventually
        - All current and future data that matches the configuration specifications are loaded into the graph.
    - If invalid configuration, do nothing and display error on 9.
14. PyQt time series graph. Displays packets filtered by config if selected. 
15. Save button. Saves all packets captured since connection into a CSV.

## Config Format

### Port Configuration

Format
```c++
{
    "name": string,             // OPTIONAL
    "port_name": string,        // OPTIONAL, default first listed by `..list_ports.comports()`
    "baud_rate": int,           // OPTIONAL, default 115200
    "data_bits": int,           // OPTIONAL, default 8
    "endian": "LSB"/"MSB",      // OPTIONAL, default LSB
    "sync_bits": int,           // OPTIONAL, default 1
    "parity_bits": "N"/"O"/"E", // OPTIONAL, default NONE
}
```

Example
```json
{
    "name": "RTD Sensor",
    "port_name": "/dev/ttyUSB0",
    "baud_rate": 115200,
    "data_bits": 8,
    "endian": "LSB",
    "sync_bits": 1,
    "parity_bits": "N",
}
```

### Packet Configuration

Two types of packet configurations can be used: _intrapacket_ or _interpacket_.
- _intrapacket_ means that the data is stored inside of the serial packet data bits itself. 

    Some bits may be allocated for the following:
    - packet type
    - data value
    
    At the moment, all data are converted as integers, but custom functions may be introduced later to interpret decimal or float values.

    ```c++
    Packet 1                            | Packet 2
    Start Data              Parity Stop | Start Data              Parity Stop
    x     [7 6 5 4 3 2 1 0] x      x x  | x     [7 6 5 4 3 2 1 0] x      x x
          [2 1 0|4 3 2 1 0]
            ID      DATA

    // I.e.
    0x28 -> 0b0010_1000 -> ID = 1, DATA = 8
    ```
- _interpacket_ means that the data is delimited by a successive stream of packets interpreted as characters (the number of data bits here can be either 7 or 8). The packets are split into four fields, an ID, a ID-value delimiter, a value, and a message-message delimeter.

    The ID and first delimiter are optional.

    ```c++
    Packet
     1    2   3  4   5   6   7   8
    'V' 'A' 'L' ':' '1' '0' '2' ','
    [    ID    ][D1][    val   ][D2]

    // I.e.
    VAL:102,VAL:302,VAL2:492, ...
    ```

Format
```c++
{
    "title": string,                // OPTIONAL
    "x-axis": string,               // OPTIONAL
    "y-axis": string,               // OPTIONAL
    "intrapacket": {                // MANDATORY
        "id": [int],                // OPTIONAL, default all packets
        "x-id": int,                // OPTIONAL, default no packets
        "y-id": int,                // OPTIONAL, default all packets
        "data": [int],              // OPTIONAL, default all data bits
    },
    "interpacket": {                // OPTIONAL
        "id": string,               // OPTIONAL, default disabled
        "id-delim": string,         // OPTIONAL, default disabled
        "message-delim": string,    // MANDATORY, default ','
    }
}
```

As can be seen, the intrapacket format has parameters to accept the bits in the packet data bits that represent the packet id and data (as the y value). In contrast, the interpacket format requires at least the `message-delim` parameter to determine the difference between two messages. The ID and ID-value delimeter can be specified to differentiate between packets.

By default, if the interpacket format is specified, then the loaded config does not use the intrapacket format.

Example (intrapacket)
```json
{
    "title": "Temperature Over Time",
    "x-axis": "Time (s)",
    "y-axis": "Temp (C)",
    "intrapacket": {
        "id": [7, 6, 5],
        "x-id": 0,
        "y-id": 2,
        "data": [4, 3, 2, 1, 0]
    }
}
```
This example takes a packet with a 3 bit ID and a 5 bit data. It looks at only packets with IDs 0 and 2. The data value for packets with ID 0 are the times in seconds, and the data value for packets with ID 2 are the temperatures in C.

Example (interpacket)
```json
{
    "title": "680 nm intensity",
    "x-axis": "Time (ms)",
    "y-axis": "F8 680nm (relative)",
    "interpacket": {
        "id": "F8 680nm",
        "id-delim": " : ",
        "message-delim": "\n"
    }
}
```
This example takes a serial set of packets from the adafruit AS7341 10 channel light color sensor breakout [example code](https://learn.adafruit.com/adafruit-as7341-10-channel-light-color-sensor-breakout?view=all).
The input stream is as follows: `F8 680nm : xxx\n...\nF8 680nm : yyy\n`. This format allows us to extract the id: `F8 680nm`, match it, and then capture the data after the id-delimeter.