"""
Controller.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 04/29/21
Last Modified: 04/29/21

Description: Implements the Controller class, which manages the front end logic
and main process loop of the DeviceSerialCapture program.
"""
# Library Imports.
from PyQt5 import uic
from PyQt5.QtCore import QObject, QTimer, QThread, pyqtSignal, QMutex
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QGridLayout,
    QVBoxLayout,
    QWidget,
)
import signal
import sys
from serial import Serial
import serial.tools.list_ports

# Custom Imports.
from src.SetupView import SetupView


class Controller:
    """
    The Controller class ...
    """

    def __init__(self):
        self._framerate = 30

        self._data_controller = {
            "app": self,
            "status": "DISCONNECTED",
            "port_names": [],
            "config": {
                "port_name": "",
                "baud_rate": 115200,
                "data_bits": "EIGHT",
                "endian": "LSB",
                "sync_bits": 1,
                "parity_bits": "None",
            },
            "serial_thread": None,
            "serial_datastream": {
                "read": "",
                "read_lock": QMutex(),
                "write": "",
                "write_lock": QMutex(),
            },
            "widget_pointers": None,
        }

        self._widgetPointers = {}

    def startup(self, window_width=800, window_height=500):
        """
        The setup routine performs any data and UI operations required to get
        the DeviceSerialCapture app operational. In particular it looks to do
        the following, in order:

        1. Startup the application UI runtime.
        2. Generate all tabs for the program and link their references.
        3. Initialize the tabs.
        4. Enable callbacks.
        5. Set up timers.

        Parameters
        ----------
        window_width: int
            Width of the window. Defaults to 800p.
        window_height: int
            Height of the window. Defaults to 500p.
        """
        # 1. Startup the application UI runtime.
        self.app = QApplication(sys.argv)

        # 2. Generate all tabs for the program and link their references.
        self.win = QMainWindow()
        self.win.setGeometry(0, 0, window_width, window_height)
        self.widget = QDialog()
        uic.loadUi("src/DeSeCa_UI.ui", self.widget)
        self.win.setCentralWidget(self.widget)

        # Serial Connect Tab
        self._widgetPointers["bu_connect"] = self.widget.bu_connect
        self._widgetPointers[
            "bu_serial_config_filesearch"
        ] = self.widget.bu_serial_config_filesearch
        self._widgetPointers["cb_baud"] = self.widget.cb_baud
        self._widgetPointers["cb_databits"] = self.widget.cb_databits
        self._widgetPointers["cb_endian"] = self.widget.cb_endian
        self._widgetPointers["cb_paritybits"] = self.widget.cb_paritybits
        self._widgetPointers["cb_portname"] = self.widget.cb_portname
        self._widgetPointers["cb_syncbits"] = self.widget.cb_syncbits
        self._widgetPointers["lbl_status"] = self.widget.lbl_status
        self._widgetPointers["le_serial_config"] = self.widget.le_serial_config

        # Serial Monitor Tab
        self._widgetPointers[
            "bu_packet_config_filesearch"
        ] = self.widget.bu_packet_config_filesearch
        self._widgetPointers["bu_save"] = self.widget.bu_save
        self._widgetPointers["bu_send"] = self.widget.bu_send
        self._widgetPointers["lbl_status2"] = self.widget.lbl_status2
        self._widgetPointers["le_transmit_txt"] = self.widget.le_transmit_txt
        self._widgetPointers["tb_serial_output"] = self.widget.tb_serial_output

        # 3. Initialize the tabs.
        self._data_controller["widget_pointers"] = self._widgetPointers
        self._setup_view = SetupView(self._data_controller, self._framerate)
        # self._monitor_view = SetupView(self._data_controller, self._framerate)
        self.win.show()

        # 4. Enable callbacks.

        # 5. Set up timers.
        # Sigint shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        sigint_timer = QTimer()
        sigint_timer.timeout.connect(lambda: None)
        sigint_timer.start(100)

        # Capture port names every 30000 ms.
        portname_timer = QTimer()
        portname_timer.timeout.connect(self._capture_port_names)
        portname_timer.start(30000)
        self._capture_port_names()

        self.exe = self.app.exec_()

    def shutdown(self, *args):
        """
        Cleans up the main window and associated Views and shuts down the
        application.

        Handler for the SIGINT signal.
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
            QApplication.quit()

    def _capture_port_names(self):
        """
        Updates the list of connected port names.
        """
        self._data_controller["port_names"] = []
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in sorted(ports):
            self._data_controller["port_names"].append(port)

        self._setup_view.update_ports()

    def _setup_serial_thread(self):
        """
        Sets up a serial thread and worker.
        """
        self._data_controller["serial_thread"] = SerialWorker(self._data_controller)
        self._data_controller["serial_thread"].start()


class SerialWorker(QThread):
    DATA_BITS = [serial.FIVEBITS, serial.SIXBITS, serial.SEVENBITS, serial.EIGHTBITS]
    PARITY = [serial.PARITY_NONE, serial.PARITY_EVEN, serial.PARITY_ODD]
    SYNC_BITS = [serial.STOPBITS_ONE, serial.STOPBITS_TWO]

    def __init__(self, data_controller):
        super(SerialWorker, self).__init__()
        self._config = data_controller["config"].copy()
        self._serial_datastream = data_controller["serial_datastream"]

    def run(self):
        # Set up a serial connection outputting to the data.

        if self._config["data_bits"] == "FIVE":
            self._config["data_bits"] = serial.FIVEBITS
        elif self._config["data_bits"] == "SIX":
            self._config["data_bits"] = serial.SIXBITS
        elif self._config["data_bits"] == "SEVEN":
            self._config["data_bits"] = serial.SEVENBITS
        else:
            self._config["data_bits"] = serial.EIGHTBITS

        if self._config["parity_bits"] == "None":
            self._config["parity_bits"] = serial.PARITY_NONE
        elif self._config["parity_bits"] == "Odd":
            self._config["parity_bits"] = serial.PARITY_ODD
        else:
            self._config["parity_bits"] = serial.PARITY_EVEN

        if self._config["sync_bits"] == "ONE":
            self._config["sync_bits"] = serial.STOPBITS_ONE
        else:
            self._config["sync_bits"] = serial.STOPBITS_TWO

        # ser = Serial(
        #     self._config["port_name"],
        #     self._config["baud_rate"],
        #     self._config["data_bits"],
        #     self._config["parity_bits"],
        #     self._config["sync_bits"]
        # )

        # Keep serial alive until exception
        while not self._serial_datastream["read_lock"].tryLock(50):
            pass
        self._serial_datastream["read"] += "READY"
        self._serial_datastream["read_lock"].unlock()

        # While alive, any received packets are captured and dumped into serial_datastream["read"].

        # While alive, any packets in serial_datastream["write"] are sent.

        # Close on exception and update the interface.
