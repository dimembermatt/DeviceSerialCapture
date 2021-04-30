"""
Console.py

Author: Matthew Yu (2021).
Contact: matthewjkyu@gmail.com
Created: 11/18/20
Last Modified: 11/24/20

Description: The Console class is a concrete base class that provides a common 
API for derived classes to use. It allows for the generation of textboxes and
buttons in a wrapped widget that can connect to program functions.
"""
# Library Imports.
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import (
    QComboBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Custom Imports.
from src.View import View


class Console(View):
    """
    The Console class is a concrete base class that provides a common
    API for derived classes to use. It allows for the generation of textboxes
    and buttons in a wrapped widget that can connect to program functions.
    """

    def __init__(self):
        self._components = {}
        layout_widget = QWidget()
        layout_widget.layout = QGridLayout()
        layout_widget.setLayout(layout_widget.layout)

        self._layout = layout_widget

    def add_button(self, ID, flavor_text, position, size, callback=None):
        """
        Adds a button to the layout with a bindable callback.

        Parameters
        ----------
        ID: String
            Unique identifier for the button.
        flavorText: String
            Text to be displayed on the button.
        position: (x:int, y:int)
            Location of the button in grid coordinates.
        size: (x:int, y:int)
            Size of the button in grid coordinates.
        callback: function reference
            Function that will trigger when pressed.
        """
        self._components[ID] = QPushButton(flavor_text)
        self._layout.layout.addWidget(
            self._components[ID], position[1], position[0], size[1], size[0]
        )

        if callback is not None:
            self._components[ID].clicked.connect(callback)

    def add_textbox(self, ID, position, size, hint=""):
        """
        Adds a textbox to the layout.

        Parameters
        ----------
        ID: String
            Unique identifier for the button.
        position: (x:int, y:int)
            Location of the button in grid coordinates.
        size: (x:int, y:int)
            Size of the button in grid coordinates.
        hint: String
            Optional text to be displayed on an empty textbox.
        """
        self._components[ID] = QLineEdit()
        self._components[ID].setStyleSheet("border: 1px solid blue;")
        self._components[ID].setPlaceholderText(hint)
        self._layout.layout.addWidget(
            self._components[ID], position[1], position[0], size[1], size[0]
        )

    def add_label(self, ID, position, size, default_text=""):
        """
        Adds a label to the layout.

        Parameters
        ----------
        ID: String
            Unique identifier for the button.
        position: (x:int, y:int)
            Location of the button in grid coordinates.
        size: (x:int, y:int)
            Size of the button in grid coordinates.
        defaultText: String
            Optional starter text to display on the label.
        """
        self._components[ID] = QLabel(default_text)
        self._layout.layout.addWidget(
            self._components[ID], position[1], position[0], size[1], size[0]
        )

    def add_combo_box(self, ID, position, size, options, callback=None):
        """
        Adds a combo box to the layout. The combo box can have a callback
        attached to do something when the user clicks an item.

        Parameters
        ----------
        ID: String
            Unique identifier for the button.
        position: (x:int, y:int)
            Location of the button in grid coordinates.
        size: (x:int, y:int)
            Size of the button in grid coordinates.
        options: [String]
            A list of strings representing each item in the combo box.
        """
        self._components[ID] = QComboBox()
        self._components[ID].setStyleSheet("border: 1px solid red;")
        self._components[ID].addItems(options)
        self._layout.layout.addWidget(
            self._components[ID], position[1], position[0], size[1], size[0]
        )

        if callback is not None:
            self._components[ID].currentIndexChanged.connect(callback)

    def hide_console_widgets(self, IDs=[]):
        """
        Hides a list of widgets from the console.

        Parameters
        ----------
        IDs: [String]
            A list of IDs of widgets that should be hidden.
        """
        for ID in IDs:
            component = self._components.get(ID)
            if component is not None:
                component.hide()

    def show_console_widgets(self, IDs=[]):
        """
        Shows a list of widgets from the console.

        Parameters
        ----------
        IDs: [String]
            A list of IDs of widgets that should be shown.
            Assumes they were created prior.
        """
        for ID in IDs:
            component = self._components.get(ID)
            if component is not None:
                component.show()

    def get_reference(self, ID):
        """
        Returns the widget, if any, of the console corresponding to the correct
        ID.

        Parameters
        ----------
        ID: String
            ID reference to the widget.

        Returns
        -------
        Reference to the widget, or None.
        """
        return self._components.get(ID)
