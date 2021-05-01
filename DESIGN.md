# Design

Serial interfacing in pyserial, UI is in PyQt5.

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
        - FIVE
        - SIX
        - SEVEN
        - EIGHT (default)
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
10. Packet monitor. Copyable text box. Data is displayed per character unparsed
    or parsed.
11. Transmit text box. Use ENTER key or 12 to send. Attempts to send text as
    characters across serial. Does not work if the receiver is not set up to
    catch data.
12. Enter button. Submits whatever is in the textbox. If there is nothing in the
    textbox, nothing is submitted.
13. Visualizer configuration selector, non-editable textbox, opens a file selector.
    - Select a configuration file and populate textbox
    - If valid configuration upon parsing, loads a pyqt time series graph
        - Maybe other types of graphs eventually
        - All current and future data that matches the configuration
          specifications are loaded into the graph.
    - If invalid configuration, do nothing and display error on 9.
14. PyQt time series graph. Displays packets filtered by config if selected.
15. Save button. Saves all packets captured since connection into a CSV.