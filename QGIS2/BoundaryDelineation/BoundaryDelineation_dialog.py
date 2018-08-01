# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BoundaryDelineationDialog
                                 A QGIS plugin
 Supports the semi-automatic delineation of boundaries
                             -------------------
        begin                : 2017-05-10
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Sophie Crommelinck
        email                : s.crommelinck@utwente.nl
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

import os

from PyQt4 import QtGui, uic
from PyQt4.QtGui import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'BoundaryDelineation_dialog_base.ui'))


class BoundaryDelineationDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, callbackFunction, parent=None):
        """Constructor."""
        super(BoundaryDelineationDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.buttonBox.clicked.connect(self.closeMe)
        self.buttonBox_2.clicked.connect(self.closeMe)
        self.buttonBox_3.clicked.connect(self.closeMe)
        self.pushButton.clicked.connect(callbackFunction)

        # Set path to images used in Plugin interface
        self.label_4.setPixmap(QtGui.QPixmap(":/plugins/BoundaryDelineation/icon_its4land.png"))
        self.label_13.setPixmap(QtGui.QPixmap(":/plugins/BoundaryDelineation/icon_SelectNode.png"))
        self.label_9.setPixmap(QtGui.QPixmap(":/plugins/BoundaryDelineation/icon_AcceptLine.png"))
        self.label_10.setPixmap(QtGui.QPixmap(":/plugins/BoundaryDelineation/icon_SimplifyLine.png"))
        self.label_14.setPixmap(QtGui.QPixmap(":/plugins/BoundaryDelineation/icon_EditLine.png"))
        self.label_12.setPixmap(QtGui.QPixmap(":/plugins/BoundaryDelineation/icon_DeleteLine.png"))
        self.label_15.setPixmap(QtGui.QPixmap(":/plugins/BoundaryDelineation/icon_ManualDelineation.png"))

    def closeMe(self):
        """close is clicked"""
        self.close()
