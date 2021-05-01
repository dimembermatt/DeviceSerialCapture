"""
View.py

Author: Matthew Yu, Array Lead (2020).
Contact: matthewjkyu@gmail.com
Created: 04/29/21
Last Modified: 04/29/21

Description: Implements the parent View class for tabs in the Controller. Based
off of the View class used for PVSim (https://github.com/lhr-solar/Array-Simulation).
"""
# Library Imports.
from PyQt5.QtGui import QColor, QPalette


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

    def get_layout(self):
        """
        Returns a reference to the View layout.

        Returns
        -------
        layout of the View.
        """
        return self._layout

    def get_data_controller(self):
        """
        Returns a reference to the internal data representation.

        Returns
        -------
        Data store of the view. Could be any type.
        """
        return self._data_controller
