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
from typing import List, Dict, Optional

from .Its4landAPI import Its4landException
from .utils import get_tmp_dir
from . import utils

from qgis.core import QgsVectorLayer, QgsWkbTypes
from PyQt5 import uic
# from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QShowEvent
from PyQt5.QtWidgets import QDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'BoundaryDelineationIts4landWindow.ui'))

class BoundaryDelineationIts4landWindow(QDialog, FORM_CLASS):
    # login = pyqtSignal()
    # logout = pyqtSignal()
    # projectSelected = pyqtSignal()
    # validationSetSelected = pyqtSignal()

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

        self.projects = None
        self.validationSets = None
        self.contentItem = None
        self.contentItemFilename = None

        self.loginInput.textChanged.connect(self.onLoginInputChanged)
        self.passwordInput.textChanged.connect(self.onLoginInputChanged)
        self.loginButton.clicked.connect(self.onLoginButtonClicked)
        self.logoutButton.clicked.connect(self.onLogoutButtonClicked)
        self.projectsListWidget.currentRowChanged.connect(self.onProjectListWidgetCurrentRowChanged)
        self.validationSetsListWidget.currentRowChanged.connect(self.onValidationSetsListWidgetCurrentRowChanged)
        self.validationSetsLoadButton.clicked.connect(self.onValidationSetsLoadButtonClicked)

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
            msg = e.msg if 'msg' in e else self.tr('Unable to login')

            self.plugin.showMessage(msg, type=Qgis.Error)
            self.loginInput.setEnabled(True)
            self.passwordInput.setEnabled(True)
            self.loginButton.setEnabled(True)
            self.passwordInput.setText('')
            raise e

        self.logoutButton.setEnabled(True)

        try:
            projects = self.plugin.service.get_projects()
        except Exception as e:
            self.plugin.showMessage('Oopsie' + str(e))
            return

        self.projectsGroupBox.setEnabled(True)

        assert projects.get('features'), 'Please contact HansaLuftbild, there is "features" missing from ./projects'

        self.projects = projects['features']
        self.setProjects(self.projects)

    def onLogoutButtonClicked(self) -> None:
        self.logoutButton.setEnabled(False)
        self.loginInput.setText('')
        self.passwordInput.setText('')
        self.loginInput.setEnabled(True)
        self.passwordInput.setEnabled(True)
        self.loginButton.setEnabled(True)

        self.projectsListWidget.clear()
        self.validationSetsListWidget.clear()

        self.projectsGroupBox.setEnabled(False)
        self.validationSetsGroupBox.setEnabled(False)

    def onProjectListWidgetCurrentRowChanged(self, index: int) -> None:
        assert self.projects

        try:
            if index >= 0:
                project = self.projects[index]
            else:
                project = None
        except ValueError:
            project = None
        except Exception as e:
            raise e

        self._updateProjectDetails(project)

        try:
            self.validationSets = self.service.get_validation_sets(project['properties']['UID'])
            self.setValidationSets(project, self.validationSets)

            if project:
                self.validationSetsGroupBox.setEnabled(True)
        except Its4landException as e:
            raise e
            if e.code == 404:
                msg = self.tr('No validation sets found for this project')
            else:
                msg = str(e)

            self.plugin.showMessage(msg)
        except Exception as e:
            self.plugin.showMessage(str(e))

    def onValidationSetsListWidgetCurrentRowChanged(self, index: int) -> None:
        assert self.validationSets

        self.validationSetsLoadButton.setEnabled(False)

        try:
            if index >= 0:
                self.validationSet = self.validationSets[index]
            else:
                self.validationSet = None
        except ValueError:
            self.validationSet = None
        except Exception as e:
            raise e

        if self.validationSet:
            try:
                self.contentItem = self.service.get_content_item(self.validationSet['ContentItem'])
                self.contentItem = self.contentItem[0] if len(self.contentItem) else None
                self.contentItemFilename = None

                self.validationSetsLoadButton.setEnabled(True)
            except Exception as e:
                raise e

        self._updateValidationSetDetails(self.validationSet, self.contentItem)

    def onValidationSetsLoadButtonClicked(self) -> None:
        assert self.contentItem
        assert self.contentItem['ContentID']

        self.contentItemFilename = os.path.join(get_tmp_dir(), self.contentItem['ContentID'])

        # TODO this lock is not working for some reason :/
        self.loginGroupBox.setEnabled(False)
        self.projectsGroupBox.setEnabled(False)
        self.validationSetsGroupBox.setEnabled(False)

        try:
            self.service.download_content_item(self.contentItem['ContentID'], self.contentItemFilename)
            layer = QgsVectorLayer(self.contentItemFilename, self.validationSet['Name'], 'ogr')

            if layer.geometryType() != QgsWkbTypes.LineGeometry:
                self.plugin.showMessage(self.tr('Validation set file is not with line geometries'))
                return

            utils.add_layer(layer, self.validationSet['Name'], parent=self.plugin.getGroup(), index=0)
            layer = self.plugin.setSegmentsLayer(layer, name=self.validationSet['Name'])

            if layer:
                # TODO the ugliest thing in the whole project
                self.plugin.dockWidget.segmentsLayerComboBox.setLayer(layer)
        except Its4landException as e:
            if e.code == 404:
                self.plugin.showMessage(self.tr('Unable to load the selected validation set, check the web interface for more information'))
                return
            else:
                raise e
        finally:
            self.loginGroupBox.setEnabled(True)
            self.projectsGroupBox.setEnabled(True)
            self.validationSetsGroupBox.setEnabled(True)


    def accept(self):
        self.close()
        self.hide()

    def reject(self):
        self.close()
        self.hide()

    def _updateProjectDetails(self, project: Optional[Dict[str, str]]):
        if not project:
            self.projectsNameValueLabel.setText('')
            self.projectsDescriptionValueLabel.setText('')
            self.projectsModelsValueLabel.setText('')
            self.projectsSpatialSourcesValueLabel.setText('')
            self.projectsTagsValueLabel.setText('')
            return

        self.projectsNameValueLabel.setText(project['properties']['Name'])
        self.projectsDescriptionValueLabel.setText(project['properties']['Description'])
        self.projectsModelsValueLabel.setText(str(len(project['properties']['Models'])))
        self.projectsSpatialSourcesValueLabel.setText(str(len(project['properties']['SpatialSources'])))
        self.projectsTagsValueLabel.setText(','.join(project['properties']['Tags']))

    def _updateValidationSetDetails(self, validationSet: Optional[Dict[str, str]], contentItem: Optional[Dict[str, str]]) -> None:
        if validationSet:
            self.validationSetsNameValueLabel.setText(validationSet['Name'])
            self.validationSetsDescriptionValueLabel.setText(validationSet['Description'])
            self.validationSetsModelsValueLabel.setText(str(len(validationSet['Models'])))
            self.validationSetsTagsValueLabel.setText(','.join(validationSet['Tags']))

            if contentItem:
                self.validationSetsSizeValueLabel.setText(str(contentItem['ContentSize']))
        else:
            self.validationSetsNameValueLabel.setText('')
            self.validationSetsDescriptionValueLabel.setText('')
            self.validationSetsModelsValueLabel.setText('')
            self.validationSetsTagsValueLabel.setText('')
            self.validationSetsSizeValueLabel.setText('')

    def showEvent(self, event: QShowEvent):
        pass

    def setValidationSets(self, project, validationSets):
        list_items = []

        for validationSet in validationSets:
            assert validationSet.get('Name'), 'Please contact HansaLuftbild, there is "Name" missing from a single validationSet'

            list_items.append(validationSet['Name'])

        self.validationSetsListWidget.clear()
        self.validationSetsListWidget.addItems(list_items)

    def setProjects(self, projects: List[Dict]):
        list_items = []

        for project in projects:
            assert project.get('properties')
            assert project['properties'].get('Name'), 'Please contact HansaLuftbild, there is "Name" missing from a single Project'

            list_items.append(project['properties']['Name'])

        self.projectsListWidget.clear()
        self.projectsListWidget.addItems(list_items)

