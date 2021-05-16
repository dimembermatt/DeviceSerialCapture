"""
main.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 04/29/21
Last Modified: 05/14/21

Description: Main program for executing the DeviceSerialCapture application.
"""

# Library Imports.
import sys

# Custom Imports.
from src.controller import Controller

if __name__ == "__main__":
    if sys.version_info[0] < 3:
        raise Exception("This program only supports Python 3.")

    controller = Controller()
    controller.startup()
