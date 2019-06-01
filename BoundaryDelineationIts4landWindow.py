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
import json
from typing import List, Dict, Optional

from .Its4landAPI import Its4landException
from .utils import get_tmp_dir
from . import utils

from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsVectorFileWriter
from PyQt5 import uic
# from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QShowEvent
from PyQt5.QtWidgets import QDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'BoundaryDelineationIts4landWindow.ui'))
HL_HARDCODED_PROJECTION = 'urn:ogc:def:crs:OGC:1.3:CRS84'

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

        self.project: Optional[str] = None
        self.projects = None
        self.validationSets = None
        self.contentItem = None
        self.contentItemFilename = None
        self.boundaryString: Optional[Dict] = None
        self.boundaryStrings: Optional[List] = None

        self.loginInput.textChanged.connect(self.onLoginInputChanged)
        self.passwordInput.textChanged.connect(self.onLoginInputChanged)
        self.loginButton.clicked.connect(self.onLoginButtonClicked)
        self.connectButton.clicked.connect(self.onConnectButtonClicked)
        self.logoutButton.clicked.connect(self.onLogoutButtonClicked)
        self.projectsListWidget.currentRowChanged.connect(self.onProjectListWidgetCurrentRowChanged)
        self.validationSetsListWidget.currentRowChanged.connect(self.onValidationSetsListWidgetCurrentRowChanged)
        self.validationSetsLoadButton.clicked.connect(self.onValidationSetsLoadButtonClicked)
        self.boundaryStringsListWidget.currentRowChanged.connect(self.onBoundaryStringsListWidgetCurrentRowChanged)
        self.boundaryStringsLoadButton.clicked.connect(self.onBoundaryStringsLoadButtonClicked)
        self.boundaryStringsUploadButton.clicked.connect(self.onBoundaryStringsUploadButtonClicked)
        self.boundaryStringsUpdateButton.clicked.connect(self.onBoundaryStringsUpdateButtonClicked)

        self.boundaryStringsUploadButton.setEnabled(True)

        # self.__setIcon(self.uploadButton, 'icon.png')


    def onLoginInputChanged(self, text: str) -> None:
        pass

    def onPasswordInputChanged(self, text: str) -> None:
        pass

    def onConnectButtonClicked(self) -> None:
        """Temporary replacement of onLoginButtonClicked."""
        self.onLoginButtonClicked()

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
        self.updateEnabledBoundaryStringButtons()

        try:
            projects = self.plugin.service.get_projects()
            self.setProjectsError('')
        except Its4landException as e:
            msg = self.plugin.tr('[%s] %s' % (str(e.code), str(e)))
            self.setProjectsError(msg)
            self.plugin.showMessage(msg)
            return
        except Exception as e:
            self.setProjectsError(self.plugin.tr('[%s] Error has occured!' % '???'))
            self.plugin.showMessage(str(e))
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
        self.boundaryStringsListWidget.clear()

        self.projectsGroupBox.setEnabled(False)
        self.validationSetsGroupBox.setEnabled(False)
        self.boundaryStringsGroupBox.setEnabled(False)

    def onProjectListWidgetCurrentRowChanged(self, index: int) -> None:
        assert self.projects

        try:
            if index >= 0:
                self.project = self.projects[index]
            else:
                self.project = None
        except ValueError:
            self.project = None
        except Exception as e:
            raise e

        self._updateProjectDetails(self.project)
        self.validationSetsListWidget.clear()
        self.boundaryStringsListWidget.clear()

        try:
            self.validationSets = self.service.get_validation_sets(self.project['properties']['UID'])
            self.setValidationSets(self.project, self.validationSets)

            self.setValidationSetsError('')
        except Its4landException as e:
            if e.code == 404:
                msg = self.tr('No validation sets found for this project')
            else:
                msg = str(self.plugin.tr('[%s] %s' % (str(e.code), str(e))))

            self.setValidationSetsError(msg)
        except Exception as e:
            self.setValidationSetsError(self.plugin.tr('[%s] Error has occured!' % '???'))
            self.plugin.showMessage(str(e))
        finally:
            if self.project:
                self.validationSetsGroupBox.setEnabled(True)

        try:
            self.boundaryStrings = self.service.get_boundary_strings(self.project['properties']['UID'])
            # TODO this is because hansaluft have funny API
            self.boundaryStrings = self.boundaryStrings if isinstance(self.boundaryStrings, list) else [self.boundaryStrings]
            self.setBoundaryStrings(self.project, self.boundaryStrings)

            self.setBoundaryStringsError('')
        except Its4landException as e:
            if e.code == 404:
                msg = self.tr('No boundary strings found for this project')
            else:
                msg = str(self.plugin.tr('[%s] %s' % (str(e.code), str(e))))

            self.setBoundaryStringsError(msg)
        except Exception as e:
            self.setBoundaryStringsError(self.plugin.tr('[%s] Error has occured!' % '???'))
            self.plugin.showMessage(str(e))
        finally:
            if self.project:
                self.boundaryStringsGroupBox.setEnabled(True)

    def onValidationSetsListWidgetCurrentRowChanged(self, index: int) -> None:
        assert self.validationSets

        self.validationSetsLoadButton.setEnabled(False)
        self.contentItemFilename = None

        try:
            if index >= 0:
                self.validationSet = self.validationSets[index]
                self.validationSetsLoadButton.setEnabled(True)
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

                self.setValidationSetsError('')
            except Exception as e:
                self.setValidationSetsError(str(e))
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
        self.boundaryStringsGroupBox.setEnabled(False)

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
            self.boundaryStringsGroupBox.setEnabled(True)

    def onBoundaryStringsListWidgetCurrentRowChanged(self, index: int) -> None:
        assert self.boundaryStrings

        self.boundaryStringsLoadButton.setEnabled(False)

        try:
            if index >= 0:
                self.boundaryString = self.boundaryStrings[index]
                self.boundaryStringsLoadButton.setEnabled(True)
            else:
                self.boundaryString = None
        except ValueError:
            self.boundaryString = None
        except Exception as e:
            raise e

        self._updateBoundaryStringDetails(self.boundaryString)

    def onBoundaryStringsLoadButtonClicked(self) -> None:
        assert self.boundaryString

        layer = utils.load_geojson(self.boundaryString, self.boundaryString['name'])

        if layer.geometryType() != QgsWkbTypes.LineGeometry:
            self.plugin.showMessage(self.tr('Boundary face strings file is not with line geometries'))
            return

        utils.add_layer(layer, self.boundaryString['name'], parent=self.plugin.getGroup(), index=0)

    def _prepareBoundaryStringsGeojson(self, layer: QgsVectorLayer, project_id: str) -> dict:
        layer = utils.multipart_to_singleparts(layer)
        # layer = utils.reproject(layer, 'EPSG::4326')
        geojson = utils.get_geojson(layer)

        counter = 1

        for f in geojson['features']:
            f['properties']['Projects'] = [{
                'UID': project_id
            }]
            # don't use double quotes, cause it is reserved for HL...
            f['properties']['Name'] = '%s__%s' % (project_id, counter)
            counter += 1

        geojson['crs']['properties']['name'] = HL_HARDCODED_PROJECTION
        geojson['name'] = 'BoundaryFaceString'

        return geojson

    def onBoundaryStringsUploadButtonClicked(self) -> None:
        assert self.project
        assert self.plugin.finalLayer

        geojson = self._prepareBoundaryStringsGeojson(self.plugin.finalLayer, self.project['properties']['UID'])

        self.boundaryStringsUploadButton.setEnabled(False)

        try:
            self.service.post_boundary_strings(geojson)
            self.plugin.showMessage(self.plugin.tr('Successfully uploaded boundary face strings!'))
        except Its4landException as e:
            self.plugin.showMessage(self.plugin.tr('[%s] %s' % (str(e.code), str(e))))
            self.boundaryStringsUploadButton.setEnabled(True)
        except Exception as e:
            self.plugin.showMessage(self.plugin.tr('[%s] Error has occured! %s' % ('???', str(e))))
            self.boundaryStringsUploadButton.setEnabled(True)

    def onBoundaryStringsUpdateButtonClicked(self) -> None:
        assert self.project
        assert self.boundaryString
        assert self.plugin.finalLayer

        geojson = self._prepareBoundaryStringsGeojson(self.plugin.finalLayer, self.project['properties']['UID'])

        self.boundaryStringsUpdateButton.setEnabled(False)

        try:
            self.service.patch_boundary_strings(self.boundaryString['UID'], geojson)
            self.plugin.showMessage(self.plugin.tr('Successfully updated boundary face strings!'))
        except Its4landException as e:
            self.plugin.showMessage(self.plugin.tr('[%s] %s' % (str(e.code), str(e))))
            self.boundaryStringsUpdateButton.setEnabled(True)
        except Exception as e:
            self.plugin.showMessage(self.plugin.tr('[%s] Error has occured! %s' % ('???', str(e))))
            self.boundaryStringsUpdateButton.setEnabled(True)

    def updateEnabledBoundaryStringButtons(self) -> None:
        upload_enabled = bool(self.project and self.plugin.finalLayer)
        print(111111, str(upload_enabled), bool(self.project), bool(self.plugin.finalLayer))
        self.boundaryStringsUploadButton.setEnabled(upload_enabled)
        update_enabled = bool(self.project and self.plugin.finalLayer and self.boundaryString)
        print(222222, str(update_enabled), bool(self.project), bool(self.plugin.finalLayer), bool(self.boundaryString))
        self.boundaryStringsUpdateButton.setEnabled(update_enabled)

    def setValidationSetsError(self, msg: str) -> None:
        self.validationSetsErrorLabel.setVisible(msg != '')
        self.validationSetsErrorLabel.setText(msg)

    def setBoundaryStringsError(self, msg: str) -> None:
        self.boundaryStringsErrorLabel.setVisible(msg != '')
        self.boundaryStringsErrorLabel.setText(msg)

    def setProjectsError(self, msg: str) -> None:
        self.projectsErrorLabel.setVisible(msg != '')
        self.projectsErrorLabel.setText(msg)

    def accept(self):
        self.close()
        self.hide()

    def reject(self):
        self.close()
        self.hide()

    def _updateProjectDetails(self, project: Optional[Dict[str, str]]):
        self.updateEnabledBoundaryStringButtons()

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
        self.updateEnabledBoundaryStringButtons()

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

    def _updateBoundaryStringDetails(self, boundaryString: Optional[Dict[str, str]]) -> None:
        self.updateEnabledBoundaryStringButtons()

        if boundaryString:
            self.boundaryStringsNameValueLabel.setText(boundaryString['name'])
            self.boundaryStringsFeaturesValueLabel.setText(str(len(boundaryString['features'])))
            self.boundaryStringsSizeValueLabel.setText(str(utils.utf8len(json.dumps(self.boundaryString))))
        else:
            self.boundaryStringsNameValueLabel.setText('')
            self.boundaryStringsFeaturesValueLabel.setText('')
            self.boundaryStringsSizeValueLabel.setText('')

    def showEvent(self, event: QShowEvent):
        pass

    def setValidationSets(self, project, validation_sets):
        list_items = []

        for validation_set in validation_sets:
            assert validation_set.get('Name'), 'Please contact HansaLuftbild, there is "Name" missing from a single validationSet'

            list_items.append(validation_set['Name'])

        self.validationSetsListWidget.clear()
        self.validationSetsListWidget.addItems(list_items)

    def setBoundaryStrings(self, project, boundaries) -> None:
        list_items = []

        for boundary in boundaries:
            assert boundary.get('name'), 'Please contact HansaLuftbild, there is "Name" missing from a single BoundaryFaceStrings'

            list_items.append(boundary['name'])

        self.boundaryStringsListWidget.clear()
        self.boundaryStringsListWidget.addItems(list_items)

    def setProjects(self, projects: List[Dict]):
        list_items = []

        for project in projects:
            assert project.get('properties')
            assert project['properties'].get('Name'), 'Please contact HansaLuftbild, there is "Name" missing from a single Project'

            list_items.append(project['properties']['Name'])

        self.projectsListWidget.clear()
        self.projectsListWidget.addItems(list_items)
