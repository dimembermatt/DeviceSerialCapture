"""
controller.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 04/29/21
Last Modified: 05/14/21

Description: Implements the Controller class, which manages the front end logic
and main process loop of the DeviceSerialCapture program.
"""
# Library Imports.
from PyQt5 import uic
from PyQt5.QtCore import Qt, QObject, QTimer, QThread, pyqtSignal, QMutex
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
from src.setup_view import SetupView
from src.monitor_view import MonitorView
from src.packet_manager import PacketManager
from src.misc import capture_port_names


class Controller:
    """
    The Controller class manages the main application window. It loads
    resources, sets up the internal data structures, and manages the runtime
    threads.
    """

    def __init__(self):
        # Framerate of the program (or rather, execution rate).
        self._framerate = 30

        # Data controller storage.
        self._data_controller = {
            # Reference to self for serial worker management.
            "app": self,
            # The current status of the application. One of two states:
            # - DISCONNECTED
            # - CONNECTED
            "status": "DISCONNECTED",
            # The current list of available ports to connect to.
            "port_names": [],
            # The current listed port configuration to connect to.
            "config": {
                "port_name": "",
                "baud_rate": 115200,
                "data_bits": "EIGHT",
                "endian": "LSB",
                "sync_bits": 1,
                "parity_bits": "None",
            },
            # A dictionary of currently set packet filters for display.
            "packet_config": None,
            # Data structure for managing collected serial packets.
            "packet_manager": PacketManager(),
            # The serial thread executing communication with the port.
            "serial_thread": None,
            # The shared serial datastream for reading and writing messages.
            "serial_datastream": {
                "read": [],
                "read_lock": QMutex(),
                "write": [],
                "write_lock": QMutex(),
                "status": [],
                "status_lock": QMutex(),
            },
            # References to UI elements.
            "widget_pointers": None,
        }

    def startup(self):
        """
        The setup routine performs any data and UI operations required to get
        the DeviceSerialCapture app operational. In particular it looks to do
        the following, in order:

        1. Startup the application UI runtime.
        2. Generate all tabs for the program and link their references.
        3. Initialize the tabs.
        4. Enable callbacks.
        5. Set up timers.
        """
        # 1. Startup the application UI runtime.
        self.app = QApplication(sys.argv)

        # 2. Generate all tabs for the program and link their references.
        self.win = QMainWindow()
        self.win.setWindowFlags(Qt.FramelessWindowHint)
        self.win.setAttribute(Qt.WA_TranslucentBackground)
        uic.loadUi("src/ui_main.ui", self.win)

        # 2.1 Grab Serial Connect Tab references.
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

        # 2.2 Grab Serial Monitor Tab references.
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

        # 2.3 Feed references to the _data_controller.
        self._data_controller["widget_pointers"] = _widget_pointers

        # 3. Initialize the tabs.
        # 3.1. Status is DISCONNECTED.
        _widget_pointers["lbl_status"].setAutoFillBackground(True)
        _widget_pointers["lbl_status"].setText(self._data_controller["status"])

        # 3.2. Tie functionality to edge buttons.
        _widget_pointers["bu_min"].clicked.connect(lambda: self.win.showMinimized())
        _widget_pointers["bu_max"].clicked.connect(lambda: self.win.showMaximized())
        _widget_pointers["bu_close"].clicked.connect(lambda: self.shutdown())

        # 3.3. Set up setup and monitor view.
        self._setup_view = SetupView(self._data_controller, self._framerate)
        self._monitor_view = MonitorView(self._data_controller, self._framerate)
        self.win.show()

        # 4. Enable callbacks.
        self._data_controller["serial_thread"] = self.SerialWorker(
            self._data_controller
        )
        self._data_controller["serial_thread"].start()

        # 5. Set up timers.
        # 5.1. Sigint shutdown.
        signal.signal(signal.SIGINT, self.shutdown)
        sigint_timer = QTimer()
        sigint_timer.timeout.connect(lambda: None)
        sigint_timer.start(100)

        # 5.2. Capture port names every 10000 ms.
        portname_timer = QTimer()
        portname_timer.timeout.connect(self._capture_port_names)
        portname_timer.start(10000)
        self._capture_port_names()

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
            self._data_controller["serial_thread"].exit()
            QApplication.quit()

    def _capture_port_names(self):
        """
        Updates the list of connected port names.
        """
        self._data_controller["port_names"] = capture_port_names()
        self._setup_view.update_ports()

    def _start_serial_thread(self):
        """
        Enables SerialWorker execution.
        """
        self._data_controller["serial_thread"].enable_serial(
            self._data_controller["config"]
        )

    def _stop_serial_thread(self):
        """
        Disables SerialWorker execution.
        """
        self._data_controller["serial_thread"].disable_serial()

    class SerialWorker(QThread):
        """
        The SerialWorker class manages communication with the serial device over
        USB. It propagates sent and received messages, and manages status messages.
        """

        def __init__(self, data_controller):
            """
            Initializes the serial worker.

            Parameters
            ----------
            data_controller : Dict
                Reference to the data controller defined in Controller.__init__()
            """
            super(Controller.SerialWorker, self).__init__()
            self._data_controller = data_controller
            self._serial_datastream = data_controller["serial_datastream"]
            self._update_config(data_controller["config"])
            self._enabled = False

        def enable_serial(self, config):
            """
            Enables serial communication.

            Parameters
            ----------
            config : Dict
                Reference to the configuration of the serial device.
            """
            self._update_config(config)
            self._enabled = True

        def disable_serial(self):
            """
            Disables serial communication.
            """
            self._enabled = False

        def _update_config(self, config):
            """
            Normalizes the passed config with Serial readable enums.

            Parameters
            ----------
            config : Dict
                Reference to the configuration of the serial device.
            """
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

            # Poll the serial connection until exit.
            _read_buffer = self._serial_datastream["read"]
            _read_lock = self._serial_datastream["read_lock"]
            _write_buffer = self._serial_datastream["write"]
            _write_lock = self._serial_datastream["write_lock"]
            id = 0
            while self._serial_connection.isOpen() and self._enabled:
                try:
                    # While alive, any received packets are captured and dumped into
                    # serial_datastream["read"].
                    response = self._serial_connection.read(500)
                    while not _read_lock.tryLock(50):
                        pass
                    if response != b"":
                        print("Read({}): {}".format(id, response.decode("utf-8")))
                        _read_buffer.append(response)
                    _read_lock.unlock()

                    # While alive, any packets in serial_datastream["write"] are
                    # sent.
                    if _write_buffer:
                        # To reduce lock time, capture first read in write array only.
                        write_set_len = len(_write_buffer)
                        write_set = _write_buffer[0:write_set_len]
                        print("Write({}): {}".format(id, str(write_set)))
                        try:
                            for entry in write_set:
                                self._serial_connection.write(entry)
                        except Exception as e:
                            _update_status("Serial Write: " + str(e))

                        # Clear out what we have read.
                        while not _write_lock.tryLock(50):
                            pass
                        _write_buffer = _write_buffer[write_set_len:]
                        _write_lock.unlock()

                    id += 1
                except Exception as e:
                    self._close_serial("Serial EACCESS: " + str(e))

            self._close_serial("Serial connection was closed.")

        def _update_status(self, msg):
            """
            Updates the status FIFO in the datastream.

            Parameters
            ----------
            msg : Str
                Message to pass to the serial datastream.
            """
            while not self._serial_datastream["status_lock"].tryLock(50):
                pass
            self._serial_datastream["status"].append(msg)
            self._serial_datastream["status_lock"].unlock()

        def _close_serial(self, msg):
            """
            Update status on connection close or exception.

            Parameters
            ----------
            msg : Str
                Message to pass to the serial datastream.
            """
            self._enabled = False
            self._update_status(msg)
            self._serial_connection.close()
            self._data_controller["status"] = "DISCONNECTED"
