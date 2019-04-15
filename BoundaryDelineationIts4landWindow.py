# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BoundaryDelineation
                                 A QGIS plugin
 BoundaryDelineation
                             -------------------
        begin                : 2019-05-23
        git sha              : $Format:%H$
        development          : 2019, Ivan Ivanov @ ITC, University of Twente <ivan.ivanov@suricactus.com>
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
from typing import List, Dict

from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QShowEvent
from PyQt5.QtWidgets import QDialog, QAction

from .utils import SelectionModes

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'BoundaryDelineationIts4landWindow.ui'))

class BoundaryDelineationIts4landWindow(QDialog, FORM_CLASS):
    closingPlugin = pyqtSignal()

    def __init__(self, plugin, parent=None):
        """Constructor."""
        super(BoundaryDelineationIts4landWindow, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.plugin = plugin
        self.tr = plugin.tr
        self.service = plugin.service
        self.projectsListWidget.currentRowChanged.connect(self.onProjectListWidgetCurrentRowChanged)

        self.loginInput.textChanged.connect(self.onLoginInputChanged)
        self.passwordInput.textChanged.connect(self.onLoginInputChanged)
        self.loginButton.clicked.connect(self.onLoginButtonClicked)
        self.logoutButton.clicked.connect(self.onLogoutButtonClicked)

    def onLoginInputChanged(self, text: str) -> None:
        pass

    def onPasswordInputChanged(self, text: str) -> None:
        pass

    def onLoginButtonClicked(self) -> None:
        self.loginInput.setEnabled(False)
        self.passwordInput.setEnabled(False)
        self.loginButton.setEnabled(False)
        self.logoutButton.setEnabled(False)

        try:
            self.service.login(self.loginInput.text(), self.passwordInput.text())
        except Exception as e:
            self.loginInput.setEnabled(True)
            self.passwordInput.setEnabled(True)
            self.loginButton.setEnabled(True)
            self.passwordInput.setText('')
            raise e

        self.logoutButton.setEnabled(True)

        self.projectsGroupBox.setEnabled(True)

        try:
            projects = self.plugin.service.get_projects()
        except Exception as e:
            self.plugin.showMessage('Oopsie' + str(e))
            return

        assert projects.get('features'), 'Please contact HansaLuftbild, there is "features" missing from ./projects'

        self.setProjects(projects['features'])


    def onLogoutButtonClicked(self) -> None:
        self.logoutButton.setEnabled(False)
        self.loginInput.setText('')
        self.passwordInput.setText('')
        self.loginInput.setEnabled(True)
        self.passwordInput.setEnabled(True)
        self.loginButton.setEnabled(True)

        self.projectsGroupBox.setEnabled(False)

    def onProjectListWidgetCurrentRowChanged(self, index):
        assert self.projects

        if index < 0:
            self.nameValueLabel.setText('')
            self.descriptionValueLabel.setText('')
            self.modelsValueLabel.setText('')
            self.spatialSourcesValueLabel.setText('')
            self.tagsValueLabel.setText((''))

            return

        project = self.projects[index]

        self.nameValueLabel.setText(project['properties']['Name'])
        self.descriptionValueLabel.setText(project['properties']['Description'])
        self.modelsValueLabel.setText(str(len(project['properties']['Models'])))
        self.spatialSourcesValueLabel.setText(str(len(project['properties']['SpatialSources'])))
        self.tagsValueLabel.setText(','.join(project['properties']['Tags']))

    def accept(self):
        self.close()
        self.hide()

    def reject(self):
        self.close()
        self.hide()

    def showEvent(self, event: QShowEvent):
        self.projectsListWidget.clear()

    def setProjects(self, projects: List[Dict]):
        self.projects = projects

        list_items = []

        for project in projects:
            assert project.get('properties')
            assert project['properties'].get('Name'), 'Please contact HansaLuftbild, there is "Name" missing from a single Project'

            list_items.append(project['properties']['Name'])

        self.projectsListWidget.addItems(list_items)

