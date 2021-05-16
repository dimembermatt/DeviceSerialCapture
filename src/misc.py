"""
misc.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 05/14/21
Last Modified: 05/14/21

Description: Contains miscellaneous, shared functions.
"""
from serial import Serial
import serial.tools.list_ports


def capture_port_names():
    """
    Returns the list of ports currently active.

    Returns
    -------
    list of ports currently active.
    """
    return [port for port, desc, hwid in sorted(serial.tools.list_ports.comports())]
