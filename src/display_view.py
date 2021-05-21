"""
display_view.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 05/21/21
Last Modified: 05/21/21

Description: Implements the child DisplayView class for tabs in the Controller.
"""
# Library Imports.
from PyQt5.QtCore import QTimer

# Custom Imports.
from src.view import View

# Class Implementation.
class DisplayView(View):
    """
    The DisplayView is a concrete child class of View which provides additional
    functionality for tab-like displays. Additional functionality includes:
    - status port access (ability to raise messages, errors)
    - data controller access
    """

    def __init__(self, controller=None, framerate=30):
        """
        Upon initialization, we perform any data and UI setup required to get
        the DisplayView into a default state.

        Parameters
        ----------
        controller : Dict
            Reference to the data controller.
        framerate : int
            Framerate of the program (or rather, execution rate).
        """
        super(DisplayView, self).__init__(framerate=30)

        self._controller = controller

        # References to UI elements generated from the controller.
        self._widget_pointers = controller.get_data_pointer("widget_pointers")

    def raise_status(self, status_str, status_color_str):
        """
        Raises a status message indefinitely.
        """
        self._widget_pointers["lbl_status"].setText(status_str)
        self._widget_pointers["lbl_status"].setStyleSheet(
            "QLabel { background-color: " + status_color_str + "; }"
        )

    def raise_temp_status(self, status_str, status_color_str):
        """
        Raises a status message on the status label for 10 seconds.
        """
        self._widget_pointers["lbl_status"].setText(status_str)
        self._widget_pointers["lbl_status"].setStyleSheet(
            "QLabel { background-color: " + status_color_str + "; }"
        )

        # Set timer to set status back to OK.
        QTimer.singleShot(10000, self.revert_temp_status)

    def raise_error(self, error_str):
        """
        Raises an error on the status label.

        Parameters
        ----------
        error_str: str
            Error string to display.
        """
        self.raise_temp_status(error_str, "rgba(255, 0, 0, 255)")

    def revert_temp_status(self):
        """
        Resets the status bar after an error has been displayed for X amount of
        time.
        """
        status = self._controller.get_data_pointer("status")
        self._widget_pointers["lbl_status"].setText(status)
        if status == "DISCONNECTED":
            self._widget_pointers["lbl_status"].setStyleSheet(
                "QLabel { background-color: rgba(122, 122, 122, 255); }"
            )
        elif status == "CONNECTED":
            self._widget_pointers["lbl_status"].setStyleSheet(
                "QLabel { background-color: rgba(122, 255, 122, 255); }"
            )
