"""
controller.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 04/29/21
Last Modified: 05/21/21

Description: Implements the Controller class, which manages the front end logic
and main process loop of the DeviceSerialCapture program.
"""
# Library Imports.
from PyQt5.QtCore import QThread, QTimer, QMutex
from serial import Serial
import serial.tools.list_ports

# Custom Imports.
from src.misc import capture_port_names
from src.packet_manager import PacketManager

# Class Implementation.
class Controller:
    """
    The Controller class manages the main application window. It loads
    resources, sets up the internal data structures, and manages the runtime
    threads.
    """

    def __init__(self):
        # Data controller storage.
        self.data_controller = {
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

        # Initialize a SerialWorker instance thread for managing serial
        # communication.
        self.data_controller["serial_thread"] = self.SerialWorker(self.data_controller)
        self.data_controller["serial_thread"].start()

        # Initialize a QTimer to update the port names every 10s.
        portname_timer = QTimer()
        portname_timer.timeout.connect(self._capture_port_names)
        portname_timer.start(10000)
        self._capture_port_names()

    def get_data_pointer(self, key):
        if key in self.data_controller:
            return self.data_controller[key]
        return None

    def set_data_pointer(self, key, value):
        if key in self.data_controller:
            self.data_controller[key] = value

    def _capture_port_names(self):
        """
        Updates the list of connected port names.
        """
        self.data_controller["port_names"] = capture_port_names()

    def start_serial_thread(self):
        """
        Enables SerialWorker execution.
        """
        self.data_controller["serial_thread"].enable_serial(
            self.data_controller["config"]
        )

    def stop_serial_thread(self):
        """
        Disables SerialWorker execution.
        """
        self.data_controller["serial_thread"].disable_serial()

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
