"""UI controller of the its4land window.

Attributes:
    HL_HARDCODED_PROJECTION (str): the hardcoded projection expected by Hansaluft (officially part of the geojson RFC)

Notes:
    begin                : 2019-05-23
    git sha              : $Format:%H$

    development          : 2019, Ivan Ivanov @ ITC, University of Twente
    email                : ivan.ivanov@suricactus.com
    copyright            : (C) 2019 by Ivan Ivanov

License:
    /***************************************************************************
     *                                                                         *
     *   This program is free software; you can redistribute it and/or modify  *
     *   it under the terms of the GNU General Public License as published by  *
     *   the Free Software Foundation; either version 2 of the License, or     *
     *   (at your option) any later version.                                   *
     *                                                                         *
    /***************************************************************************

"""

import os
import json
from typing import List, Dict, Optional

from .Its4landAPI import Its4landException
from .utils import get_tmp_dir
from . import utils
from .utils import __, show_info, show_error, get_group

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
        self.service = plugin.service

        self.project: Optional[str] = None
        self.projects = None
        self.validationSets = None
        self.contentItem = None
        self.contentItemFilename = None
        self.boundaryStrings: Optional[Dict] = None

        self.loginInput.textChanged.connect(self.onLoginInputChanged)
        self.passwordInput.textChanged.connect(self.onLoginInputChanged)
        self.loginButton.clicked.connect(self.onLoginButtonClicked)
        self.connectButton.clicked.connect(self.onConnectButtonClicked)
        self.logoutButton.clicked.connect(self.onLogoutButtonClicked)
        self.projectsListWidget.currentRowChanged.connect(self.onProjectListWidgetCurrentRowChanged)
        self.validationSetsListWidget.currentRowChanged.connect(self.onValidationSetsListWidgetCurrentRowChanged)
        self.validationSetsLoadButton.clicked.connect(self.onValidationSetsLoadButtonClicked)
        self.boundaryStringsLoadButton.clicked.connect(self.onBoundaryStringsLoadButtonClicked)
        self.boundaryStringsUploadButton.clicked.connect(self.onBoundaryStringsUploadButtonClicked)
        # self.__setIcon(self.uploadButton, 'icon.png')

    def onLoginInputChanged(self, text: str) -> None:
        """Dummy, currently not used due to lack of authentication in its4land."""
        pass

    def onPasswordInputChanged(self, text: str) -> None:
        """Dummy, currently not used due to lack of authentication in its4land."""
        pass

    def onConnectButtonClicked(self) -> None:
        """Temporary replacement of onLoginButtonClicked."""
        self.onLoginButtonClicked()

    def onLoginButtonClicked(self) -> None:
        """Responsible for login of the user."""
        self.loginInput.setEnabled(False)
        self.passwordInput.setEnabled(False)
        self.loginButton.setEnabled(False)
        self.logoutButton.setEnabled(False)

        try:
            self.service.login(self.loginInput.text(), self.passwordInput.text())
        except Exception as e:
            msg = e.msg if 'msg' in e else __('Unable to login')

            show_error(msg)
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
            msg = __('[%s] %s' % (str(e.code), str(e)))
            self.setProjectsError(msg)
            show_info(msg)
            return
        except Exception as e:
            self.setProjectsError(__('[%s] Error has occured!' % '???'))
            show_info(str(e))
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

        try:
            self.validationSets = self.service.get_validation_sets(self.project['properties']['UID'])
            self.setValidationSets(self.project, self.validationSets)

            self.setValidationSetsError('')
        except Its4landException as e:
            if e.code == 404:
                msg = __('No validation sets found for this project')
            else:
                msg = str(__('[%s] %s' % (str(e.code), str(e))))

            self.setValidationSetsError(msg)
        except Exception as e:
            self.setValidationSetsError(__('[%s] Error has occured!' % '???'))
            show_info(str(e))
        finally:
            if self.project:
                self.validationSetsGroupBox.setEnabled(True)

        self.getAndUpdateDataForBoundaryStrings(self.project['properties']['UID'])

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
                show_info(__('Validation set file is not with line geometries'))
                return

            utils.add_layer(layer, self.validationSet['Name'], parent=get_group(), index=0)
            layer = self.plugin.setSegmentsLayer(layer, name=self.validationSet['Name'])

            if layer:
                # TODO the ugliest thing in the whole project
                self.plugin.dockWidget.segmentsLayerComboBox.setLayer(layer)
        except Its4landException as e:
            if e.code == 404:
                show_info(__('Unable to load the selected validation set, check the web interface for more information'))
                return
            else:
                raise e
        finally:
            self.loginGroupBox.setEnabled(True)
            self.projectsGroupBox.setEnabled(True)
            self.validationSetsGroupBox.setEnabled(True)
            self.boundaryStringsGroupBox.setEnabled(True)

    def onBoundaryStringsLoadButtonClicked(self) -> None:
        assert self.boundaryStrings

        layer = utils.load_geojson(self.boundaryStrings, self.boundaryStrings['name'])

        if layer.geometryType() != QgsWkbTypes.LineGeometry:
            show_info(__('Boundary face strings file is not with line geometries'))
            return

        utils.add_layer(layer, self.boundaryStrings['name'], parent=get_group(), index=0)

    def _prepareBoundaryStringsGeojson(self, layer: QgsVectorLayer, project_id: str) -> dict:
        layer = utils.multipart_to_singleparts(layer)
        layer = utils.reproject(layer, 'EPSG:4326')
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
            show_info(__('Successfully uploaded boundary face strings!'))

            self.getAndUpdateDataForBoundaryStrings(self.project['properties']['UID'])
        except Its4landException as e:
            show_info(__('[%s] %s' % (str(e.code), str(e))))
            self.boundaryStringsUploadButton.setEnabled(True)
        except Exception as e:
            show_info(__('[%s] Error has occured! %s' % ('???', str(e))))
            self.boundaryStringsUploadButton.setEnabled(True)

    def updateEnabledBoundaryStringButtons(self) -> None:
        upload_enabled = bool(self.project and self.plugin.finalLayer)
        self.boundaryStringsUploadButton.setEnabled(upload_enabled)

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

    def _updateBoundaryStringDetails(self, boundaryStrings: Optional[Dict[str, str]]) -> None:
        self.updateEnabledBoundaryStringButtons()

        if boundaryStrings:
            self.boundaryStringsNameValueLabel.setText(boundaryStrings['name'])
            self.boundaryStringsFeaturesValueLabel.setText(str(len(boundaryStrings['features'])))
            self.boundaryStringsSizeValueLabel.setText(str(utils.utf8len(json.dumps(self.boundaryStrings))))
        else:
            self.boundaryStringsNameValueLabel.setText('')
            self.boundaryStringsFeaturesValueLabel.setText('')
            self.boundaryStringsSizeValueLabel.setText('')

    def showEvent(self, event: QShowEvent) -> None:
        pass

    def setValidationSets(self, project, validation_sets) -> None:
        list_items = []

        for validation_set in validation_sets:
            assert validation_set.get('Name'), 'Please contact HansaLuftbild, there is "Name" missing from a single validationSet'

            list_items.append(validation_set['Name'])

        self.validationSetsListWidget.clear()
        self.validationSetsListWidget.addItems(list_items)

    def setProjects(self, projects: List[Dict]) -> None:
        list_items = []

        for project in projects:
            assert project.get('properties')
            assert project['properties'].get('Name'), 'Please contact HansaLuftbild, there is "Name" missing from a single Project'

            list_items.append(project['properties']['Name'])

        self.projectsListWidget.clear()
        self.projectsListWidget.addItems(list_items)

    def getAndUpdateDataForBoundaryStrings(self, project_id: str) -> None:
        try:
            self.boundaryStrings = self.service.get_boundary_strings(project_id)
            self.setBoundaryStringsError('')
        except Its4landException as e:
            if e.code == 404:
                msg = __('No boundary strings found for this project')
            else:
                msg = str(__('[%s] %s' % (str(e.code), str(e))))

            self.boundaryStrings = None

            self.setBoundaryStringsError(msg)
        except Exception as e:
            self.boundaryStrings = None

            self.setBoundaryStringsError(__('[%s] Error has occured!' % '???'))
            show_info(str(e))
        finally:
            self.boundaryStringsLoadButton.setEnabled(bool(self.boundaryStrings))
            self._updateBoundaryStringDetails(self.boundaryStrings)

            if self.project:
                self.boundaryStringsGroupBox.setEnabled(True)
