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
from src.MonitorView import MonitorView


class Controller:
    """
    The Controller class manages the main application window. It loads
    resources, sets up the internal data structures, and manages the runtime
    threads.
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
            "packet_config": {},
            "serial_thread": None,
            "serial_datastream": {
                "read": [],
                "read_lock": QMutex(),
                "write": [],
                "write_lock": QMutex(),
                "status": [],
                "status_lock": QMutex(),
            },
            "widget_pointers": None,
        }

        self._widget_pointers = {}

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
        self._widget_pointers["bu_connect"] = self.widget.bu_connect
        self._widget_pointers[
            "bu_serial_config_filesearch"
        ] = self.widget.bu_serial_config_filesearch
        self._widget_pointers["cb_baud"] = self.widget.cb_baud
        self._widget_pointers["cb_databits"] = self.widget.cb_databits
        self._widget_pointers["cb_endian"] = self.widget.cb_endian
        self._widget_pointers["cb_paritybits"] = self.widget.cb_paritybits
        self._widget_pointers["cb_portname"] = self.widget.cb_portname
        self._widget_pointers["cb_syncbits"] = self.widget.cb_syncbits
        self._widget_pointers["lbl_status"] = self.widget.lbl_status
        self._widget_pointers["le_serial_config"] = self.widget.le_serial_config

        # Serial Monitor Tab
        self._widget_pointers[
            "bu_packet_config_filesearch"
        ] = self.widget.bu_packet_config_filesearch
        self._widget_pointers["bu_save"] = self.widget.bu_save
        self._widget_pointers["bu_send"] = self.widget.bu_send
        self._widget_pointers["lbl_status2"] = self.widget.lbl_status2
        self._widget_pointers["le_transmit_txt"] = self.widget.le_transmit_txt
        self._widget_pointers["le_packet_config"] = self.widget.le_packet_config
        self._widget_pointers["te_serial_output"] = self.widget.te_serial_output

        # 3. Initialize the tabs.
        self._data_controller["widget_pointers"] = self._widget_pointers
        self._setup_view = SetupView(self._data_controller, self._framerate)
        self._monitor_view = MonitorView(self._data_controller, self._framerate)
        self.win.show()

        # 4. Enable callbacks.
        self._data_controller["serial_thread"] = SerialWorker(self._data_controller)
        self._data_controller["serial_thread"].start()

        # 5. Set up timers.
        # Sigint shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        sigint_timer = QTimer()
        sigint_timer.timeout.connect(lambda: None)
        sigint_timer.start(100)

        # Capture port names every 10000 ms.
        portname_timer = QTimer()
        portname_timer.timeout.connect(self._capture_port_names)
        portname_timer.start(10000)
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
            self._data_controller["serial_thread"].exit()
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

    def _start_serial_thread(self):
        """
        Sets up a serial thread.
        """
        self._data_controller["serial_thread"].enable_serial(
            self._data_controller["config"]
        )

    def _stop_serial_thread(self):
        """
        Stops an existing serial thread.
        """
        self._data_controller["serial_thread"].disable_serial()


class SerialWorker(QThread):
    def __init__(self, data_controller):
        super(SerialWorker, self).__init__()
        self._data_controller = data_controller
        self._serial_datastream = data_controller["serial_datastream"]
        self._update_config(data_controller["config"])
        self._enabled = False

    def enable_serial(self, config):
        self._update_config(config)
        self._enabled = True

    def disable_serial(self):
        self._enabled = False

    def _update_config(self, config):
        self._config = config.copy()
        # Convert config fields into pyserial recognized inputs
        if config["data_bits"] == "FIVE":
            self._config["data_bits"] = serial.FIVEBITS
        elif config["data_bits"] == "SIX":
            self._config["data_bits"] = serial.SIXBITS
        elif config["data_bits"] == "SEVEN":
            self._config["data_bits"] = serial.SEVENBITS
        else:
            self._config["data_bits"] = serial.EIGHTBITS

        if config["parity_bits"] == "None":
            self._config["parity_bits"] = serial.PARITY_NONE
        elif config["parity_bits"] == "Odd":
            self._config["parity_bits"] = serial.PARITY_ODD
        else:
            self._config["parity_bits"] = serial.PARITY_EVEN

        if config["sync_bits"] == "ONE":
            self._config["sync_bits"] = serial.STOPBITS_ONE
        else:
            self._config["sync_bits"] = serial.STOPBITS_TWO

    def run(self):
        """
        Initiates a serial connection that communicates with a device. Bytes are
        read from the device and put into serial_datastream["read"] and bytes in
        serial_datastream["write"] are sent to the device.
        """
        # Infinite loop.
        while True:
            # Run serial when enabled.
            if self._enabled:
                self._run_serial()
            else:
                self.msleep(50)

    def _run_serial(self):
        """
        Main loop where serial is managed.
        """
        # Attempt to open the serial connection.
        try:
            self._serial_connection = Serial(
                self._config["port_name"],
                self._config["baud_rate"],
                self._config["data_bits"],
                self._config["parity_bits"],
                self._config["sync_bits"],
                timeout=0.5,
                write_timeout=0.5,
            )
            self._update_status("READY")
        except Exception as e:
            self._close_serial("Serial EOPEN: " + str(e))

        id = 0
        # Poll the serial connection until exit.
        while self._serial_connection.isOpen() and self._enabled:
            try:
                # While alive, any received packets are captured and dumped into
                # serial_datastream["read"].
                response = self._serial_connection.read(500)
                while not self._serial_datastream["read_lock"].tryLock(50):
                    pass
                if response != b"":
                    print("Read({}): {}".format(id, response.decode("utf-8")))
                    self._serial_datastream["read"].append(response)
                self._serial_datastream["read_lock"].unlock()

                # While alive, any packets in serial_datastream["write"] are
                # sent.
                if self._serial_datastream["write"]:
                    # To reduce lock time, capture first read in write array only.
                    write_set_len = len(self._serial_datastream["write"])
                    write_set = self._serial_datastream["write"][0:write_set_len]
                    print("Write({}): {}".format(id, str(write_set)))
                    try:
                        for entry in write_set:
                            self._serial_connection.write(entry)
                    except Exception as e:
                        _update_status("Serial Write: " + str(e))

                    # Clear out what we have read.
                    while not self._serial_datastream["write_lock"].tryLock(50):
                        pass
                    self._serial_datastream["write"] = self._serial_datastream["write"][
                        write_set_len:
                    ]
                    self._serial_datastream["write_lock"].unlock()
            except Exception as e:
                self._close_serial("Serial EACCESS: " + str(e))

        self._close_serial("Serial connection was closed.")

    def _update_status(self, msg):
        """
        Updates the status FIFO in the datastream.
        """
        print(msg)
        while not self._serial_datastream["status_lock"].tryLock(50):
            pass
        self._serial_datastream["status"].append(msg)
        self._serial_datastream["status_lock"].unlock()

    def _close_serial(self, msg):
        """
        Update status on connection close or exception.
        """
        self._update_status(msg)
        self._serial_connection.close()
        self._data_controller["status"] = "DISCONNECTED"
        self._enabled = False
