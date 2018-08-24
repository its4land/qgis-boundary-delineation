# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BoundaryDelineation
                                 A QGIS plugin
 BoundaryDelineation
                              -------------------
        begin                : 2018-05-23
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Sophie Crommelinck
        email                : s.crommelinck@utwente.nl
        development          : Reiner Borchert, Hansa Luftbild AG Münster
        email                : borchert@hansaluftbild.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

# Import required modules
from PyQt5.QtCore import QSettings, QTranslator, qVersion, Qt
from PyQt5.QtWidgets import QAction, QToolBar
import qgis
from qgis.core import *
from qgis.utils import *
import processing
import os

# Initialize Qt resources from file resources.py
from .resources import *

from .DelineationController import *
# Import the code for the dialog
from .BoundaryDelineation_dialog import BoundaryDelineationDialog

class BoundaryDelineation:
    """Functions created by Plugin Builder"""
    def __init__(self, iface):
        """Constructor.
        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # Initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # Initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            DelineationController.appName + '_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&'+DelineationController.appName)
        self.toolbar = self.iface.addToolBar(DelineationController.appName)
        self.toolbar.setObjectName(DelineationController.appName)
        self.canvas = qgis.utils.iface.mapCanvas()

        # Define visible toolbars
        iface.mainWindow().findChild(QToolBar, 'mDigitizeToolBar').setVisible(True)
        iface.mainWindow().findChild(QToolBar, 'mAdvancedDigitizeToolBar').setVisible(True)
        iface.mainWindow().findChild(QToolBar, 'mSnappingToolBar').setVisible(True)
        iface.mapCanvas().snappingUtils().toggleEnabled()

        # Set projections settings for newly created layers, possible values are: prompt, useProject, useGlobal
        QSettings().setValue("/Projections/defaultBehaviour", "useProject")

        DelineationController.mainWidget = self

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate(DelineationController.appName, message)

    def initGui(self):
        # Create action that will start plugin configuration
        action = QAction(QIcon(os.path.dirname(os.path.realpath(__file__)) +
                                    "/icon.png"), DelineationController.appName, self.iface.mainWindow())
        self.actions.append(action)
        
        # Add information
        action.setWhatsThis(DelineationController.appName)

        # Add toolbar button to the Plugins toolbar
        self.iface.addToolBarIcon(action)

        # Add menu item to the Plugins menu
        self.iface.addPluginToMenu("&"+DelineationController.appName, action)

        # Connect the action to the run method
        action.triggered.connect(self.run)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&'+DelineationController.appName),
                action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        dlg = BoundaryDelineationDialog.dialog
        if dlg is None:
            # Create the dialog (after translation) and keep reference
            dlg = BoundaryDelineationDialog()
            # Show the plugin window and ensure that it stays the top level window
            dlg.setWindowFlags(Qt.WindowStaysOnTopHint)
            # Show the dialog
            dlg.show()
            # Run the dialog event loop
            dlg.exec_()

