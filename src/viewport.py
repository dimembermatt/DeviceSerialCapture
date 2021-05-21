"""
viewport.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 05/21/21
Last Modified: 05/21/21

Description: Implements the Viewport class, which represents the UI specific code.
"""
# Library Imports.
from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
)
import signal
import sys

# Custom Imports.
from src.setup_view import SetupView
from src.monitor_view import MonitorView

# Class Implementation.
class Viewport:
    """
    The Viewport class manages the main application window. It loads resources
    and manages the UI states of the application.
    """

    def __init__(self):
        # Framerate of the program (or rather, execution rate).
        self._framerate = 15

        # Startup the application UI runtime.
        self.app = QApplication(sys.argv)

    def startup(self, controller):
        """
        The startup routine sets up the views for the application.
        We assume that the controller has been initialized and started.

        1. Startup the application UI runtime.
        2. Generate all tabs for the program and link their references.
        3. Initialize the tabs.

        Parameters
        ----------
        controller : Reference
            Reference to the application controller.
        """
        # Set the reference for the controller.
        self._controller = controller

        # Generate all tabs for the program and link their references.
        self.win = QMainWindow()
        self.win.setWindowFlags(Qt.FramelessWindowHint)
        self.win.setAttribute(Qt.WA_TranslucentBackground)
        uic.loadUi("src/ui_main.ui", self.win)

        # Grab Serial Connect Tab references.
        _widget_pointers = {}
        _widget_pointers["bu_connect"] = self.win.bu_connect
        _widget_pointers[
            "bu_serial_config_filesearch"
        ] = self.win.bu_serial_config_filesearch
        _widget_pointers["cb_baud"] = self.win.cb_baud
        _widget_pointers["cb_databits"] = self.win.cb_databits
        _widget_pointers["cb_endian"] = self.win.cb_endian
        _widget_pointers["cb_paritybits"] = self.win.cb_paritybits
        _widget_pointers["cb_portname"] = self.win.cb_portname
        _widget_pointers["cb_syncbits"] = self.win.cb_syncbits
        _widget_pointers["lbl_status"] = self.win.lbl_status
        _widget_pointers["le_serial_config"] = self.win.le_serial_config

        # Grab Serial Monitor Tab references.
        _widget_pointers[
            "bu_packet_config_filesearch"
        ] = self.win.bu_packet_config_filesearch
        _widget_pointers["bu_save"] = self.win.bu_save
        _widget_pointers["bu_send"] = self.win.bu_send
        _widget_pointers["le_transmit_txt"] = self.win.le_transmit_txt
        _widget_pointers["le_packet_config"] = self.win.le_packet_config
        _widget_pointers["te_serial_output"] = self.win.te_serial_output

        # We don't include tab stuff here sans the frame since that is
        # dynamically generated.
        _widget_pointers["tab_packet_visualizer"] = self.win.tab_packet_visualizer

        # Edge buttons.
        _widget_pointers["bu_close"] = self.win.bu_close
        _widget_pointers["bu_min"] = self.win.bu_minimize
        _widget_pointers["bu_max"] = self.win.bu_maximize

        # Feed references to the _data_controller.
        self._controller.set_data_pointer("widget_pointers", _widget_pointers)

        # Initialize the tabs.
        # Status is DISCONNECTED.
        _widget_pointers["lbl_status"].setAutoFillBackground(True)
        _widget_pointers["lbl_status"].setText(
            self._controller.get_data_pointer("status")
        )

        # Tie functionality to edge buttons.
        _widget_pointers["bu_min"].clicked.connect(lambda: self.win.showMinimized())
        _widget_pointers["bu_max"].clicked.connect(lambda: self.win.showMaximized())
        _widget_pointers["bu_close"].clicked.connect(lambda: self.shutdown())

        # Set up setup and monitor view.
        self._setup_view = SetupView(self._controller, self._framerate)
        self._monitor_view = MonitorView(self._controller, self._framerate)
        self.win.show()

        # Set SIGINT shutdown.
        signal.signal(signal.SIGINT, self.shutdown)
        sigint_timer = QTimer()
        sigint_timer.timeout.connect(lambda: None)
        sigint_timer.start(100)

        # Begin program execution.
        self.exe = self.app.exec_()

    def shutdown(self, *args):
        """
        Cleans up the main window and associated Views and shuts down the
        application.

        Handler for the SIGINT signal.

        Parameters
        ----------
        args: Any
            Unused.
        """
        sys.stderr.write("\r")
        if (
            QMessageBox.question(
                None,
                "",
                "Are you sure you want to quit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            serial_thread = self._controller.get_data_pointer("serial_thread")
            if serial_thread:
                serial_thread.exit()
                QApplication.quit()
