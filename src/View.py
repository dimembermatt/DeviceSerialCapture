"""
view.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 04/29/21
Last Modified: 05/21/21

Description: Implements the parent View class for program UI elements. Based
off of the View class used for PVSim (https://github.com/lhr-solar/Array-Simulation).
"""
# Library Imports.
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QTimer

# Class Implementation.
class View:
    """
    The View class is a concrete base class that provides a common API
    for derived classes to use. It manages the widgets within each tab during their
    lifetimes. A View roughly corresponds to a single composite UI element.
    The View class contains three elements:
    - A layout, which is the widget UI reference.
    - A framerate, which is tied to a recurring function which can be set by the
      user. Typically the recurring function is for updating the UI or
      processing data.
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

    def __init__(self, framerate=30):
        """
        Initializes a view object for displaying data.

        Parameters
        ----------
        framerate: int
            Number of updates per second for realtime graphing and graphics.
        """
        # Execution framerate and QTimer.
        self._framerate = framerate
        self._frame_timer = None

        # Reference to the view widget.
        self._layout = None

    def get_layout(self):
        """
        Returns a reference to the View layout.

        Returns
        -------
        reference: layout of the View.
        """
        return self._layout

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
        # Stop any other frame timers already running.
        if self._frame_timer is not None:
            self._frame_timer.stop()

        # Set up a new frame timer.
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
