"""
view.py

Author: Matthew Yu, Array Lead (2020).
Contact: matthewjkyu@gmail.com
Created: 04/29/21
Last Modified: 05/16/21

Description: Implements the parent View class for tabs in the Controller. Based
off of the View class used for PVSim (https://github.com/lhr-solar/Array-Simulation).
"""
# Library Imports.
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import QTimer

# Custom Imports.


class View:
    """
    The View class is a concrete base class that provides a common API
    for derived classes to use. It manages the widgets within each tab during their
    lifetimes. A View roughly corresponds to a tab in the Controller.
    """

    # Some internal color palettes.
    LIGHT_GRAY = QColor(76, 76, 76, 255)
    MEDIUM_GRAY = QColor(64, 64, 64, 255)
    DARK_GRAY = QColor(51, 51, 51, 255)
    BLUE = QColor(0, 0, 255, 255)
    RED = QColor(255, 0, 0, 255)
    GREEN = QColor(0, 255, 0, 255)

    # Timing constants.
    SECOND = 1000  # in milliseconds.

    def __init__(self, data_controller=None, framerate=30):
        """
        Initializes a view object for displaying data.

        Parameters
        ----------
        dataController: Dictionary
            reference to the DataController object which manages the program
            simulation pipeline.
        framerate: int
            Number of updates per second for realtime graphing and graphics.
        """
        self._framerate = framerate
        self._layout = None

        # The datastoreParent is a reference to the overarching DataController,
        # which exposes its API to user Views.
        self._data_controller = data_controller

        # References to UI elements generated from the controller.
        self._widget_pointers = self._data_controller["widget_pointers"]

    def get_layout(self):
        """
        Returns a reference to the View layout.

        Returns
        -------
        reference: layout of the View.
        """
        return self._layout

    def get_data_controller(self):
        """
        Returns a reference to the internal data representation.

        Returns
        -------
        any: Data store of the view.
        """
        return self._data_controller

    def get_framerate(self):
        """
        Returns the current execution framerate.

        Returns
        -------
        int: Framerate.
        """
        return self._framerate

    def init_frame(self, function=None):
        """
        Initializes execution for a defined function at the current frame rate.

        Parameters
        ----------
        function: Reference
            Reference to a function to execute every frame.
        """
        if function is not None:
            self._frame_timer = QTimer()
            self._frame_timer.timeout.connect(function)
            self._frame_timer.start(View.SECOND / self._framerate)

    def stop_frame(self):
        """
        Stops execution for function put on timer by init_frame.
        """
        if self._frame_timer:
            self._frame_timer.stop()

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
        self._widget_pointers["lbl_status"].setText(self._data_controller["status"])
        if self._data_controller["status"] == "DISCONNECTED":
            self._widget_pointers["lbl_status"].setStyleSheet(
                "QLabel { background-color: rgba(122, 122, 122, 255); }"
            )
        elif self._data_controller["status"] == "CONNECTED":
            self._widget_pointers["lbl_status"].setStyleSheet(
                "QLabel { background-color: rgba(122, 255, 122, 255); }"
            )
