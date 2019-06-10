"""Main file boundary delineation.

Attributes:
    API_KEY (str): ITS4LAND API key
    API_URL (str): its4land API url
    BOUNDARY_ATTR_NAME (str): default boundary weight attribute, that comes from the extraction algorithm
    DEFAULT_SELECTION_MODE (SelectionMode): the default values that is preselected as candidate selection mode
    MODE_VERTICES_EXTENT_LIMIT (int): the maximum number of vertices in the current map extent, when the NODES mode can be enabled
    MODE_VERTICES_LIMIT (int): the maximum number of vertices in the whole map, when the NODES mode graph can be precalculated
    PRECALCULATE_METRIC_CLOSURES (bool): should precalculate vertices graphs, or delay it until immediate need
    SelectBehaviour (TYPE): Default select behaviour

Notes:
    begin                : 2018-05-23
    git sha              : $Format:%H$

    development          : Sophie Crommelinck
    email                : s.crommelinck@utwente.nl
    copyright            : (C) 2018 by Sophie Crommelinck

    development          : Reiner Borchert, Hansa Luftbild AG Münster
    email                : borchert@hansaluftbild.de

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
import sys
import typing
from typing import Optional, Collection

if os.path.join(os.path.dirname(__file__) + '/lib') not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__) + '/lib'))

import networkx as nx
import processing

from PyQt5.QtCore import QSettings, QTranslator, Qt, QVariant, QCoreApplication
from PyQt5.QtWidgets import QAction, QToolBar, QMessageBox
from PyQt5.QtGui import QIcon

from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsLayerTree, QgsLayerTreeNode, QgsPointXY, QgsVectorLayer, \
    QgsRasterLayer, QgsMapLayer, QgsWkbTypes, QgsVectorFileWriter, QgsCoordinateTransform, QgsField, QgsDefaultValue, QgsRectangle, QgsFeatureIterator, \
    QgsFeature, QgsGeometry, QgsTolerance, QgsMapSettings
from qgis.gui import QgisInterface, QgsMapTool
from qgis.utils import iface
from qgis.utils import *

# Initialize Qt resources from file resources.py
# from .resources import *

from .Its4landAPI import Its4landAPI
from .BoundaryDelineationDock import BoundaryDelineationDock
from .MapSelectionTool import MapSelectionTool
from . import utils
from .utils import PLUGIN_DIR, APP_NAME, SelectionModes, processing_cursor, __, show_info, get_group
from .BoundaryGraph import NoSuitableGraphError, prepare_graph_from_lines, prepare_subgraphs, calculate_subgraphs_metric_closures, \
    find_steiner_tree, DEFAULT_WEIGHT_NAME

BOUNDARY_ATTR_NAME = 'boundary'
PRECALCULATE_METRIC_CLOSURES = False
DEFAULT_SELECTION_MODE = SelectionModes.ENCLOSING
MODE_VERTICES_EXTENT_LIMIT = 300
MODE_VERTICES_LIMIT = 1000

SelectBehaviour = int

API_URL = 'http://i4ldev1dmz.hansaluftbild.de/sub/'
API_KEY = '1'


class BoundaryDelineation:
    """Functions created by Plugin Builder"""
    def __init__(self, iface: QgisInterface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.project = QgsProject.instance()
        self.layerTree = self.project.layerTreeRoot()

        self.service = Its4landAPI(API_URL, API_KEY)

        self._initLocale()

        self.baseRasterLayerName = __('Raster')
        self.segmentsLayerName = __('Segments')
        self.simplifiedSegmentsLayerName = __('Simplified Segments')
        self.verticesLayerName = __('Vertices')
        self.candidatesLayerName = __('Candidates')
        self.finalLayerName = __('Final')
        self.finalLayerPolygonsName = __('Final Polygons')
        self.groupName = __('BoundaryDelineation')

        # map layers
        self.baseRasterLayer: Optional[QgsRasterLayer] = None
        self.segmentsLayer: Optional[QgsVectorLayer] = None
        self.simplifiedSegmentsLayer: Optional[QgsVectorLayer] = None
        self.verticesLayer: Optional[QgsVectorLayer] = None
        self.candidatesLayer: Optional[QgsVectorLayer] = None
        self.finalLayer: Optional[QgsVectorLayer] = None
        self.finalLayerPolygons: Optional[QgsVectorLayer] = None

        self.actions: typing.List[QAction] = []
        self.canvas = self.iface.mapCanvas()

        self.isMapSelectionToolEnabled = False
        self.isEditCandidatesToggled = False
        self.shouldAddLengthAttribute = False
        self.wasBaseRasterLayerInitiallyInLegend = True
        self.wasSegmentsLayerInitiallyInLegend = True
        self.previousMapTool = None
        self.selectionMode = SelectionModes.NONE
        self.previousSelectionMode = SelectionModes.NONE
        self.dockWidget: Optional[BoundaryDelineationDock] = None
        self.edgesWeightField = DEFAULT_WEIGHT_NAME
        self.lengthAttributeName = 'BD_LEN'
        self.metricClosureGraphs: typing.Dict[str, typing.Any] = {}
        self.graph: Optional[nx.MultiGraph] = None
        self.subgraphs: Optional[Collection[nx.Graph]] = None

        self.mapSelectionTool = MapSelectionTool(self.canvas)
        self.mapSelectionTool.polygonCreated.connect(self.onPolygonSelectionCreated)

        # Define visible toolbars
        iface.mainWindow().findChild(QToolBar, 'mDigitizeToolBar').setVisible(True)
        iface.mainWindow().findChild(QToolBar, 'mAdvancedDigitizeToolBar').setVisible(True)
        iface.mainWindow().findChild(QToolBar, 'mSnappingToolBar').setVisible(True)

        snappingConfig = self.canvas.snappingUtils().config()
        snappingConfig.setEnabled(True)

        self.canvas.snappingUtils().setConfig(snappingConfig)

        # Set projections settings for newly created layers, possible values are: prompt, useProject, useGlobal
        QSettings().setValue('/Projections/defaultBehaviour', 'useProject')

        # self.layerTree.willRemoveChildren.connect(self.onLayerTreeWillRemoveChildren)

    def _initLocale(self) -> None:
        # Initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        localePath = os.path.join(PLUGIN_DIR, 'i18n', '{}_{}.qm'.format(APP_NAME, locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            QCoreApplication.installTranslator(self.translator)

    def initGui(self) -> None:
        # Create action that will start plugin configuration
        action = QAction(QIcon(os.path.join(PLUGIN_DIR, 'icons/icon.png')), APP_NAME, self.iface.mainWindow())
        self.actions.append(action)

        action.setWhatsThis(APP_NAME)

        # Add toolbar button to the Plugins toolbar
        self.iface.addToolBarIcon(action)

        # Add menu item to the Plugins menu
        self.iface.addPluginToMenu(APP_NAME, action)

        # Connect the action to the run method
        action.triggered.connect(self.run)

        # Create the dockwidget (after translation) and keep reference
        self.dockWidget = BoundaryDelineationDock(self)
        self.dockWidget.init()

        # show the dockwidget
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dockWidget)
        self.dockWidget.closingPlugin.connect(self.onClosePlugin)

        self.canvas.mapToolSet.connect(self.onMapToolSet)
        self.canvas.extentsChanged.connect(self.onExtentsChanged)


    def unload(self) -> None:
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(__(APP_NAME), action)
            self.iface.removeToolBarIcon(action)

        # TODO very stupid workaround. Should find a way to check if method is connected!
        try:
            self.mapSelectionTool.polygonCreated.disconnect(self.onPolygonSelectionCreated)
        except:
            pass
        # self.layerTree.willRemoveChildren.disconnect(self.onLayerTreeWillRemoveChildren)

        self.toggleMapSelectionTool(False)

        self.canvas.mapToolSet.disconnect(self.onMapToolSet)
        self.canvas.extentsChanged.disconnect(self.onExtentsChanged)

        if self.dockWidget:
            self.iface.removeDockWidget(self.dockWidget)

            # self.dockWidget.closingPlugin.disconnect(self.onClosePlugin)
            self.dockWidget.hide()
            self.dockWidget.destroy()

            del self.dockWidget

            self.dockWidget = None

        self.resetProcessed()

    def run(self, checked: bool) -> None:
        assert self.dockWidget

        if self.dockWidget.isVisible():
            self.dockWidget.hide()
        else:
            self.dockWidget.show()

    def toggleMapSelectionTool(self, toggle: bool = None) -> None:
        if toggle is None:
            toggle = not self.isMapSelectionToolEnabled

        if toggle:
            self.canvas.setMapTool(self.mapSelectionTool)
        else:
            self.canvas.unsetMapTool(self.mapSelectionTool)

        self.isMapSelectionToolEnabled = toggle

    def onMapToolSet(self, newTool: QgsMapTool, oldTool: Optional[QgsMapTool]) -> None:
        assert self.dockWidget

        if newTool is self.mapSelectionTool and self.previousMapTool is None:
            self.previousMapTool = oldTool

        if oldTool is self.mapSelectionTool and newTool is not self.mapSelectionTool:
            self.dockWidget.updateSelectionModeButtons()

            if self.selectionMode is not SelectionModes.MANUAL:
                self.setSelectionMode(SelectionModes.NONE)

    def onPolygonSelectionCreated(self, startPoint: QgsPointXY, endPoint: QgsPointXY, modifiers: Qt.KeyboardModifiers) -> None:
        self.syntheticFeatureSelection(startPoint, endPoint, modifiers)

    def onCandidatesLayerFeatureChanged(self, featureIds: typing.Union[int, typing.List[int]]) -> None:
        assert self.candidatesLayer
        assert self.dockWidget

        enable = self.candidatesLayer.featureCount() > 0

        self.dockWidget.setCandidatesButtonsEnabled(enable)

    def onFinalLayerFeaturesAdded(self, featureIds: typing.Union[int, typing.List[int]]) -> None:
        assert self.finalLayer
        assert self.dockWidget

        enable = self.finalLayer.featureCount() > 0

        self.dockWidget.toggleFinalButtonEnabled(enable)

    def onFinalLayerFeaturesDeleted(self, featureIds: typing.Union[int, typing.List[int]]) -> None:
        assert self.finalLayer
        assert self.dockWidget

        enable = self.finalLayer.featureCount() > 0

        self.dockWidget.toggleFinalButtonEnabled(enable)

    @processing_cursor()
    def updateLayersTopology(self) -> None:
        assert self.finalLayer
        assert self.simplifiedSegmentsLayer

        splittedLayer = utils.split_with_lines(self.finalLayer, self.simplifiedSegmentsLayer)
        diffLayer = utils.difference(splittedLayer, self.simplifiedSegmentsLayer)
        mergedLinesLayer = utils.merge_lines_layer(diffLayer)

        # if there are no features, that are manually drawn outside the already existing segments, break
        if mergedLinesLayer.featureCount() == 0:
            return

        self.simplifiedSegmentsLayer.startEditing()

        assert self.simplifiedSegmentsLayer.isEditable(), 'Unable to begin editing'

        for f in mergedLinesLayer.getFeatures():
            newFeature = QgsFeature(self.simplifiedSegmentsLayer.fields())
            newFeature.setGeometry(f.geometry())

            # this was used when the ./styles/segments.qml was a graduated style, however is no longer the case
            # # make the line visible, otherwise there is no value for such values in the QML style
            # newFeature.setAttribute(BOUNDARY_ATTR_NAME, 1)

            assert self.simplifiedSegmentsLayer.addFeature(newFeature), 'Unable to add new feature'

        assert self.simplifiedSegmentsLayer.commitChanges(), 'Unable to commit newly added features'

        # update the supporting layers
        self.extractSegmentsVertices()
        self.polygonizeSegmentsLayer()
        self.buildVerticesGraph()

    def onLayerTreeWillRemoveChildren(self, node: QgsLayerTreeNode, startIndex: int, endIndex: int) -> None:
        # TODO try to fix this...
        return

        if self.isPluginLayerTreeNode(node):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText('This is a message box')
            msg.setInformativeText('This is additional information')
            msg.setWindowTitle('MessageBox demo')
            msg.setDetailedText('The details are as follows:')
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

    def onCandidatesLayerBeforeEditingStarted(self) -> None:
        pass
        # TODO this is nice, when somebody starts manually editing the layer and we are in different mode,
        # however does not work properly if we use the plugin in the normal way :(
        # if not self.selectionMode == SelectionModes.MANUAL:
        #     self.setSelectionMode(SelectionModes.MANUAL)

    def onClosePlugin(self) -> None:
        self.actions[0].setChecked(False)

    def onExtentsChanged(self) -> None:
        assert self.dockWidget

        if not self.verticesLayer:
            return

        extent = self.canvas.extent()
        count = len(list(self.verticesLayer.getFeatures(extent)))

        self.buildVerticesGraph()

        if count <= MODE_VERTICES_EXTENT_LIMIT:
            self.verticesLayer.selectByIds([])
            self.dockWidget.toggleVerticesRadioEnabled(True)
        else:
            if self.selectionMode == SelectionModes.NODES:
                self.setSelectionMode(DEFAULT_SELECTION_MODE)
                show_info(__('Selection mode change to default'))

            self.dockWidget.toggleVerticesRadioEnabled(False)

    @processing_cursor()
    def processFirstStep(self) -> None:
        assert self.dockWidget

        self.dockWidget.step1ProgressBar.setValue(5)

        self.simplifySegmentsLayer()

        self.addLengthAttribute()

        self.createCandidatesLayer()

        self.dockWidget.step1ProgressBar.setValue(25)

        self.extractSegmentsVertices()

        self.dockWidget.step1ProgressBar.setValue(50)

        self.polygonizeSegmentsLayer()

        self.dockWidget.step1ProgressBar.setValue(75)

        self.buildVerticesGraph()

        self.dockWidget.step1ProgressBar.setValue(100)

        self.setSelectionMode(DEFAULT_SELECTION_MODE)

    @processing_cursor()
    def processFinish(self) -> None:
        assert self.dockWidget

        show_info(__('Boundary deliniation finished, see the currently active layer for all the results'))
        self.iface.setActiveLayer(self.finalLayer)

        if self.dockWidget.getPolygonizeChecked():
            self.finalLayerPolygons = utils.polyginize_lines(self.finalLayer)
            utils.add_layer(self.finalLayerPolygons, self.finalLayerPolygonsName, parent=get_group())

        self.resetProcessed()

        self.dockWidget.its4landWindow.updateEnabledBoundaryStringButtons()


    def resetProcessed(self) -> None:
        self.toggleMapSelectionTool(False)

        if not self.wasBaseRasterLayerInitiallyInLegend:
            utils.remove_layer(self.baseRasterLayer)
            self.baseRasterLayer = None

        if not self.wasSegmentsLayerInitiallyInLegend:
            utils.remove_layer(self.segmentsLayer)
            self.segmentsLayer = None

        try:
            if self.candidatesLayer:
                self.candidatesLayer.featureAdded.disconnect(self.onCandidatesLayerFeatureChanged)
                self.candidatesLayer.featuresDeleted.disconnect(self.onCandidatesLayerFeatureChanged)
                self.candidatesLayer.beforeEditingStarted.disconnect(self.onCandidatesLayerBeforeEditingStarted)
                self.candidatesLayer.rollBack()
        except:
            show_info(__('Unable clean-up #%s' % 1))

        try:
            utils.remove_layer(self.simplifiedSegmentsLayer)
            utils.remove_layer(self.verticesLayer)
            utils.remove_layer(self.candidatesLayer)
        except:
            show_info(__('Unable clean-up #%s' % 2))

        try:
            if self.finalLayer:
                self.finalLayer.featureAdded.disconnect(self.onFinalLayerFeaturesAdded)
                self.finalLayer.featuresDeleted.disconnect(self.onFinalLayerFeaturesDeleted)
        except:
            show_info(__('Unable clean-up #%s' % 3))

        self.simplifiedSegmentsLayer = None
        self.verticesLayer = None
        self.candidatesLayer = None

    def zoomToLayer(self, layer: QgsMapLayer) -> None:
        self.iface.setActiveLayer(layer)
        self.iface.actionZoomToLayer().trigger()
        # rect = self.__getCoordinateTransform(layer).transform(layer.extent())

        # self.canvas.setExtent(rect)
        # self.canvas.refresh()

    def setBaseRasterLayer(self, baseRasterLayer: typing.Union[QgsRasterLayer, str]) -> None:
        if self.baseRasterLayer is baseRasterLayer:
            return

        if isinstance(baseRasterLayer, str):
            if self.baseRasterLayer and not self.wasBaseRasterLayerInitiallyInLegend:
                utils.remove_layer(self.baseRasterLayer)

            self.wasBaseRasterLayerInitiallyInLegend = False
            baseRasterLayer = QgsRasterLayer(baseRasterLayer, self.baseRasterLayerName, )

            utils.add_layer(baseRasterLayer, self.baseRasterLayerName, index=-1)
            self.project.addMapLayer(baseRasterLayer)
        else:
            self.wasBaseRasterLayerInitiallyInLegend = True

            baseRasterLayerTreeIdx = utils.get_tree_node_index(baseRasterLayer, top=True) or 0

            group = get_group(baseRasterLayerTreeIdx)

            if baseRasterLayerTreeIdx is not None and not group.findLayer(baseRasterLayer.id()):
                utils.move_tree_node(group, baseRasterLayerTreeIdx)

        self.baseRasterLayer = baseRasterLayer

    def setSegmentsLayer(self, segmentsLayer: typing.Union[QgsVectorLayer, str], name: str = None) -> Optional[QgsVectorLayer]:
        assert self.dockWidget

        if self.segmentsLayer is segmentsLayer:
            return segmentsLayer

        name = name if name else self.segmentsLayerName

        if isinstance(segmentsLayer, str):
            if self.segmentsLayer and not self.wasSegmentsLayerInitiallyInLegend:
                utils.remove_layer(self.segmentsLayer)

            self.wasSegmentsLayerInitiallyInLegend = False
            segmentsLayer = QgsVectorLayer(segmentsLayer, name, 'ogr')

            utils.add_layer(segmentsLayer, name, parent=get_group(), index=0)
        else:
            self.wasSegmentsLayerInitiallyInLegend = True

        # BUG if I keep this, I have double adding to the map
        # if not self.layerTree.findLayer(segmentsLayer.id()):
        #     utils.add_layer(segmentsLayer, name, parent=get_group(), index=0)

        if segmentsLayer.geometryType() != QgsWkbTypes.LineGeometry:
            show_info(__('Please use segments layer that is with lines geometry'))
            return

        self.segmentsLayer = segmentsLayer

        if self.isAddingLengthAttributePossible():
            self.dockWidget.toggleAddLengthAttributeCheckBoxEnabled(True)

        return segmentsLayer

    def isAddingLengthAttributePossible(self) -> bool:
        if self.segmentsLayer and self.segmentsLayer.fields().indexFromName(self.lengthAttributeName) != -1:
            return True

        return False

    @processing_cursor()
    def simplifySegmentsLayer(self) -> None:
        assert self.segmentsLayer
        assert self.dockWidget

        tolerance = self.dockWidget.getSimplificationValue()
        result = processing.run('qgis:simplifygeometries', {
            'INPUT': self.segmentsLayer,
            'METHOD': 0,
            'TOLERANCE': tolerance,
            'OUTPUT': 'memory:simplifygeometries'
        })

        # if self.wasSegmentsLayerInitiallyInLegend:
        if self.layerTree.findLayer(self.segmentsLayer.id()):
            self.layerTree.findLayer(self.segmentsLayer.id()).setItemVisibilityChecked(False)

        self.simplifiedSegmentsLayer = result['OUTPUT']

        weight_attribute = None

        if self.simplifiedSegmentsLayer.fields().indexFromName(BOUNDARY_ATTR_NAME) != -1:
            weight_attribute = BOUNDARY_ATTR_NAME

        self.dockWidget.setComboboxLayer(self.simplifiedSegmentsLayer, weight_attribute)

        layerTreeIndex = utils.get_tree_node_index(self.verticesLayer) + 1 if self.verticesLayer else 0

        utils.add_layer(
            self.simplifiedSegmentsLayer,
            self.simplifiedSegmentsLayerName,
            color=(0, 255, 0),
            # file=self.__getStylePath('segments.qml'), # behaves funny with some features different width ...
            parent=get_group(),
            index=layerTreeIndex
        )

    def addLengthAttribute(self) -> None:
        assert self.simplifiedSegmentsLayer

        if self.shouldAddLengthAttribute:
            assert self.simplifiedSegmentsLayer.fields().indexFromName(self.lengthAttributeName) == -1

            field = QgsField(self.lengthAttributeName, QVariant.Double)
            field.setDefaultValueDefinition(QgsDefaultValue('$length', True))

            self.simplifiedSegmentsLayer.dataProvider().addAttributes([field])
            self.simplifiedSegmentsLayer.updateFields()
            self.simplifiedSegmentsLayer.startEditing()

            for f in self.simplifiedSegmentsLayer.getFeatures():
                self.simplifiedSegmentsLayer.changeAttributeValue(
                    f.id(),
                    self.simplifiedSegmentsLayer.fields().indexFromName(self.lengthAttributeName),
                    f.geometry().length()
                )

            self.simplifiedSegmentsLayer.commitChanges()

    def setWeightField(self, name: str) -> None:
        self.edgesWeightField = name or DEFAULT_WEIGHT_NAME

        if PRECALCULATE_METRIC_CLOSURES:
            if not self.graph:
                self.buildVerticesGraph()

            self.metricClosureGraphs[self.edgesWeightField] = calculate_subgraphs_metric_closures(self.subgraphs, weight=self.edgesWeightField)
        else:
            self.metricClosureGraphs[self.edgesWeightField] = None

    def isPluginLayerTreeNode(self, node: QgsLayerTree) -> bool:
        # for some reason even the normal nodes are behaving like groups...
        if QgsLayerTree.isGroup(node):
            # unfortunately this does not work in Python, it's cpp only...
            # group = QgsLayerTree.toGroup(node)

            # All my other attempts also failed miserably
            # group = self.layerTree.findGroup(self.groupName)
            # return group is get_group()
            pass
        else:
            layer = self.project.mapLayer(node.layerId())

            if layer in (self.simplifiedSegmentsLayer, self.verticesLayer, self.candidatesLayer, self.finalLayer):
                return True

            if self.wasBaseRasterLayerInitiallyInLegend and layer is self.baseRasterLayer:
                return True
            if self.wasSegmentsLayerInitiallyInLegend and layer is self.segmentsLayer:
                return True

        return False

    def createFinalLayer(self) -> QgsVectorLayer:
        assert self.dockWidget

        filename = self.dockWidget.getOutputLayer()
        crs = self.__getCrs(self.segmentsLayer)

        if os.path.isfile(filename):
            finalLayer = QgsVectorLayer(filename, self.finalLayerName, 'ogr')
        else:
            finalLayer = QgsVectorLayer('MultiLineString?crs=%s' % crs.authid(), self.finalLayerName, 'memory')
            finalLayer.dataProvider().addAttributes([QgsField('FID', QVariant.Int)])
            finalLayer.updateFields()
            finalLayer.updateExtents()

            if filename:
                (writeErrorCode, writeErrorMsg) = QgsVectorFileWriter.writeAsVectorFormat(finalLayer, filename, 'utf-8', crs, 'ESRI Shapefile')

                if writeErrorMsg:
                    show_info('[%s] %s' % (writeErrorCode, writeErrorMsg))

                finalLayer = QgsVectorLayer(filename, self.finalLayerName, 'ogr')

        return finalLayer

    def createCandidatesLayer(self) -> QgsVectorLayer:
        crs = self.__getCrs(self.segmentsLayer).authid()
        candidatesLayer = QgsVectorLayer('MultiLineString?crs=%s' % crs, self.candidatesLayerName, 'memory')
        finalLayer = self.createFinalLayer()
        # lineLayerFields = self.simplifiedSegmentsLayer.dataProvider().fields().toList()
        # candidatesLayerFields= [QgsField(field.name(),field.type()) for field in lineLayerFields]
        # candidatesLayer.dataProvider().addAttributes(candidatesLayerFields)
        # candidatesLayer.updateFields()

        layerTreeIndex = utils.get_tree_node_index(self.simplifiedSegmentsLayer)

        utils.add_layer(candidatesLayer, file=self.__getStylePath('candidates.qml'), parent=get_group(), index=layerTreeIndex + 1)
        utils.add_layer(finalLayer, file=self.__getStylePath('final.qml'), parent=get_group(), index=layerTreeIndex + 2)

        candidatesLayer.featureAdded.connect(self.onCandidatesLayerFeatureChanged)
        candidatesLayer.featuresDeleted.connect(self.onCandidatesLayerFeatureChanged)
        candidatesLayer.beforeEditingStarted.connect(self.onCandidatesLayerBeforeEditingStarted)
        finalLayer.featureAdded.connect(self.onFinalLayerFeaturesAdded)
        finalLayer.featuresDeleted.connect(self.onFinalLayerFeaturesDeleted)

        self.candidatesLayer = candidatesLayer
        self.finalLayer = finalLayer

    def extractSegmentsVertices(self) -> QgsVectorLayer:
        assert self.simplifiedSegmentsLayer

        # if there is already created vertices layer, remove it
        utils.remove_layer(self.verticesLayer)

        verticesResult = processing.run('qgis:extractspecificvertices', {
            'INPUT': self.simplifiedSegmentsLayer,
            'VERTICES': '0',
            'OUTPUT': 'memory:extract',
        })

        verticesNoDuplicatesResult = processing.run('qgis:deleteduplicategeometries', {
            'INPUT': verticesResult['OUTPUT'],
            'OUTPUT': 'memory:vertices',
        })

        self.verticesLayer = verticesNoDuplicatesResult['OUTPUT']

        utils.add_layer(self.verticesLayer, self.verticesLayerName, color=(255, 0, 0), size=1.3, parent=get_group(), index=0)

        return self.verticesLayer

    def polygonizeSegmentsLayer(self) -> QgsVectorLayer:
        assert self.simplifiedSegmentsLayer

        self.polygonizedLayer = utils.polyginize_lines(self.simplifiedSegmentsLayer)

    def buildVerticesGraph(self) -> None:
        assert self.verticesLayer
        assert self.simplifiedSegmentsLayer

        extent = self.canvas.extent()
        count = len(list(self.verticesLayer.getFeatures(extent)))

        if self.verticesLayer.featureCount() <= MODE_VERTICES_LIMIT:
            if not self.graph:
                self.graph = prepare_graph_from_lines(self.simplifiedSegmentsLayer)
                self.subgraphs = prepare_subgraphs(self.graph)
                self.metricClosureGraphs[self.edgesWeightField] = self.calculateMetricClosure(self.subgraphs) if PRECALCULATE_METRIC_CLOSURES else None
        elif count <= MODE_VERTICES_EXTENT_LIMIT:
            self.graph = prepare_graph_from_lines(self.simplifiedSegmentsLayer, filter_expr=extent)
            self.subgraphs = prepare_subgraphs(self.graph)
            self.metricClosureGraphs[self.edgesWeightField] = self.calculateMetricClosure(self.subgraphs) if PRECALCULATE_METRIC_CLOSURES else None
        else:
            self.graph = None
            self.subgraphs = None
            self.metricClosureGraphs[self.edgesWeightField] = None

    @processing_cursor()
    def calculateMetricClosure(self, subgraphs: Collection) -> typing.List[typing.Any]:
        show_info(__('It may take some time to precalculate the most optimal boundaries...'))
        return calculate_subgraphs_metric_closures(self.subgraphs, weight=self.edgesWeightField)

    def setSelectionMode(self, mode: SelectionModes) -> None:
        assert self.dockWidget

        self.previousSelectionMode = self.selectionMode
        self.selectionMode = mode

        self.refreshSelectionModeBehavior()
        self.dockWidget.updateSelectionModeButtons()

    def restoreSelectionMode(self):
        if self.selectionMode is not self.previousSelectionMode:
            self.setSelectionMode(self.previousSelectionMode)

    def refreshSelectionModeBehavior(self) -> None:
        if self.selectionMode is SelectionModes.NONE:
            return
        else:
            assert self.candidatesLayer

            if self.selectionMode == SelectionModes.MANUAL:
                self.toggleMapSelectionTool(False)
                self.iface.setActiveLayer(self.candidatesLayer)

                self.candidatesLayer.rollBack()
                self.candidatesLayer.startEditing()

                assert self.candidatesLayer.isEditable()

                self.iface.actionAddFeature().trigger()
            else:
                self.iface.setActiveLayer(self.simplifiedSegmentsLayer)
                self.toggleMapSelectionTool(True)

    @processing_cursor()
    def syntheticFeatureSelection(self, startPoint: QgsPointXY, endPoint: QgsPointXY, modifiers: Qt.KeyboardModifiers) -> None:
        if startPoint is None or endPoint is None:
            raise Exception('Something went very bad, unable to create selection without start or end point')

        assert self.simplifiedSegmentsLayer

        if self.selectionMode != SelectionModes.LINES:
            self.simplifiedSegmentsLayer.removeSelection()

        # check the Shift and Control modifiers to reproduce the navive selection
        if modifiers & Qt.ShiftModifier:
            selectBehaviour = QgsVectorLayer.AddToSelection
        elif modifiers & Qt.ControlModifier:
            selectBehaviour = QgsVectorLayer.RemoveFromSelection
        else:
            selectBehaviour = QgsVectorLayer.SetSelection

        if startPoint.x() == endPoint.x() and startPoint.y() == endPoint.y():
            tolerance = QgsTolerance.defaultTolerance(iface.activeLayer(), QgsMapSettings())
            startPoint = QgsPointXY(startPoint.x() - tolerance/20, startPoint.y() - tolerance/20)
            endPoint = QgsPointXY(endPoint.x() + tolerance/20, endPoint.y() + tolerance/20)

        lines = None
        rect = QgsRectangle(startPoint, endPoint)

        if self.selectionMode == SelectionModes.ENCLOSING:
            lines = self.getLinesSelectionModeEnclosing(selectBehaviour, rect)
        elif self.selectionMode == SelectionModes.LINES:
            lines = self.getLinesSelectionModeLines(selectBehaviour, rect)
        elif self.selectionMode == SelectionModes.NODES:
            lines = self.getLinesSelectionModeVertices(selectBehaviour, rect)

            if lines is None:
                return
        else:
            raise Exception('Wrong selection mode selected, should never be the case')

        if not len(lines):
            show_info(__('No results found!'))
            self.deleteAllCandidates()
            return

        if not self.addCandidates(lines):
            show_info(__('Unable to add candidates'))
            return

    def getLinesSelectionModeEnclosing(self, selectBehaviour: SelectBehaviour, rect: QgsRectangle) -> typing.Tuple:
        rect = self.__getCoordinateTransform(self.polygonizedLayer).transform(rect)

        self.polygonizedLayer.selectByRect(rect, selectBehaviour)

        selectedPolygonsLayer = utils.selected_features_to_layer(self.polygonizedLayer)
        dissolvedPolygonsLayer = utils.dissolve_layer(selectedPolygonsLayer)

        return tuple(utils.polygons_layer_to_lines_layer(dissolvedPolygonsLayer).getFeatures())

    def getLinesSelectionModeLines(self, selectBehaviour: SelectBehaviour, rect: QgsRectangle) -> typing.Tuple:
        assert self.simplifiedSegmentsLayer

        rect = self.__getCoordinateTransform(self.simplifiedSegmentsLayer).transform(rect)

        self.simplifiedSegmentsLayer.selectByRect(rect, selectBehaviour)

        if self.simplifiedSegmentsLayer.selectedFeatureCount() == 0:
            return ()

        selectedLinesLayer = utils.selected_features_to_layer(self.simplifiedSegmentsLayer)
        dissolvedLinesLayer = utils.dissolve_layer(selectedLinesLayer)
        mergedLinesLayer = utils.merge_lines_layer(dissolvedLinesLayer)
        singlepartsLayer = utils.multipart_to_singleparts(mergedLinesLayer)

        # INFO: this is disabled, it causes the selecteBehaviour to be ignored.
        # Could be written in much more clever way, but does not worth it
        # self.simplifiedSegmentsLayer.deselect(list(self.simplifiedSegmentsLayer.selectedFeatureIds()))

        enclosingLineFeatures = list(dissolvedLinesLayer.getFeatures())
        points_dict = dict()

        for f in singlepartsLayer.getFeatures():
            points_dict[f.id()] = utils.lines_unique_vertices(singlepartsLayer, [f.id()])

        points = list(points_dict.values())

        if len(points) == 1 and len(points[0]) == 2:
            pointX1 = points[0][0]
            pointY1 = points[0][0]
            pointX2 = points[0][1]
            pointY2 = points[0][1]
        elif len(points) == 2 and len(points[0]) == 2 and len(points[1]) == 2:
            pointX1 = points[0][0]
            pointY1 = points[0][1]
            pointX2 = points[1][0]
            pointY2 = points[1][1]
        else:
            show_info(__('Selected lines can have exactly two or four unconnected endpoints'))
            return tuple(enclosingLineFeatures)

        selectedLinesLayer.startEditing()

        f1 = QgsFeature(selectedLinesLayer.fields())
        f2 = QgsFeature(selectedLinesLayer.fields())

        if pointX1.distance(pointX2) + pointY1.distance(pointY2) < pointX1.distance(pointY2) + pointY1.distance(pointX2):
            # x1->x2 y1->y2
            f1.setGeometry(QgsGeometry.fromMultiPolylineXY([[pointX1, pointX2]]))
            f2.setGeometry(QgsGeometry.fromMultiPolylineXY([[pointY1, pointY2]]))
        else:
            # x1->y2 y1->x
            f1.setGeometry(QgsGeometry.fromMultiPolylineXY([[pointX1, pointY2]]))
            f2.setGeometry(QgsGeometry.fromMultiPolylineXY([[pointY1, pointX2]]))

        selectedLinesLayer.addFeatures([f1, f2])

        selectedLinesLayer.commitChanges()

        dissolvedLinesLayer2 = utils.dissolve_layer(selectedLinesLayer)

        return tuple(dissolvedLinesLayer2.getFeatures())

    def getLinesSelectionModeVertices(self, selectBehaviour: SelectBehaviour, rect: QgsRectangle) -> Optional[Collection]:
        assert self.verticesLayer
        assert self.simplifiedSegmentsLayer
        assert self.candidatesLayer

        if not self.graph:
            self.buildVerticesGraph()

        assert self.graph
        assert self.subgraphs

        rect = self.__getCoordinateTransform(self.polygonizedLayer).transform(rect)

        self.verticesLayer.selectByRect(rect, selectBehaviour)

        selectedPoints = [f.geometry().asPoint() for f in self.verticesLayer.selectedFeatures()]

        if len(selectedPoints) <= 1:
            neighbors: typing.List[typing.Any] = []

            if len(selectedPoints) == 1:
                neighbors = list(self.graph.neighbors(selectedPoints[0]))

            if len(neighbors) == 1:
                edges = self.graph[selectedPoints[0]][selectedPoints[0]]
                edgeId = list(edges.keys())[0]

                return [f for f in self.simplifiedSegmentsLayer.getFeatures([edgeId])]

            self.candidatesLayer.rollBack()
            # TODO there are self enclosing blocks that can be handled here (one vertex that is conected to itself)
            show_info(__('Please select two or more vertices to be connected'))
            return None

        try:
            if self.metricClosureGraphs[self.edgesWeightField] is None:
                self.metricClosureGraphs[self.edgesWeightField] = self.calculateMetricClosure(self.subgraphs)

            T = find_steiner_tree(self.subgraphs, selectedPoints, metric_closures=self.metricClosureGraphs[self.edgesWeightField])
        except NoSuitableGraphError:
            # this is hapenning when the user selects vertices from two separate graphs
            return None

        # edge[2] stays for the line ids
        featureIds = [edge[2] for edge in T.edges(keys=True)]
        points = utils.lines_unique_vertices(self.simplifiedSegmentsLayer, featureIds)

        if len(points) != 2:
            show_info(__('Unable to find the shortest path'))
            return None

        if self.graph.has_edge(*points):
            edgesDict = self.graph[points[0]][points[1]]
            bestEdgeKey = None
            bestEdgeValue = None

            for k, e in edgesDict.items():
                # find the cheapest edge that is not already selected (in case there are two vertices
                # selected and there are more than one edges connecting them)
                if k not in featureIds and (bestEdgeValue is None or bestEdgeValue > e[self.edgesWeightField]):
                    bestEdgeKey = k
                    bestEdgeValue = e[self.edgesWeightField]

            if bestEdgeKey:
                featureIds.append(bestEdgeKey)

        return tuple(self.simplifiedSegmentsLayer.getFeatures(featureIds))

    def addCandidates(self, lineFeatures: QgsFeatureIterator) -> bool:
        assert self.candidatesLayer

        self.candidatesLayer.rollBack()
        self.candidatesLayer.startEditing()

        if not self.candidatesLayer.isEditable():
            show_info(__('Unable to add features as candidates #1'))
            return False

        features = []

        for f in lineFeatures:
            # TODO this is really ugly hack to remove all the attributes that do not match between layers
            f.setAttributes([])
            features.append(f)

        if not self.candidatesLayer.addFeatures(features):
            show_info(__('Unable to add features as candidates #2'))
            return False

        self.candidatesLayer.triggerRepaint()

        return True

    def deleteAllCandidates(self) -> bool:
        assert self.candidatesLayer

        self.candidatesLayer.rollBack()
        self.candidatesLayer.startEditing()

        if not self.candidatesLayer.isEditable():
            show_info(__('Unable to add features as candidates #1'))
            return False

        if not self.candidatesLayer.deleteFeatures([f.id() for f in self.candidatesLayer.getFeatures()]):
            show_info(__('Unable to delete all candidate features'))
            return False

        self.candidatesLayer.triggerRepaint()

        return True

    def acceptCandidates(self) -> bool:
        assert self.simplifiedSegmentsLayer
        assert self.candidatesLayer
        assert self.finalLayer
        assert self.candidatesLayer.featureCount() > 0

        self.finalLayer.startEditing()

        features = []

        for f in self.candidatesLayer.getFeatures():
            c = QgsFeature(f)
            c.setFields(self.finalLayer.fields())

            features.append(c)

        if self.finalLayer.isEditable() and \
                self.finalLayer.addFeatures(features) and \
                self.finalLayer.commitChanges() and \
                self.rejectCandidates():  # empty the canidates layer :)
            self.simplifiedSegmentsLayer.removeSelection()
            return True
        else:
            show_info(__('Failed to accept'))
            return False

    def rejectCandidates(self) -> bool:
        assert self.candidatesLayer
        assert self.simplifiedSegmentsLayer

        self.candidatesLayer.startEditing()
        self.candidatesLayer.selectAll()

        if self.candidatesLayer.isEditable() and \
                self.candidatesLayer.deleteSelectedFeatures() and \
                self.candidatesLayer.commitChanges():
            self.simplifiedSegmentsLayer.removeSelection()
            return True
        else:
            return False

    def toggleEditCandidates(self, toggled: bool = None) -> bool:
        assert self.candidatesLayer

        if toggled is None:
            toggled = not self.isEditCandidatesToggled

        if toggled:
            self.candidatesLayer.startEditing()

            if not self.candidatesLayer.isEditable():
                return False

            self.iface.setActiveLayer(self.candidatesLayer)
            self.iface.actionVertexTool().trigger()
        else:
            # TODO maybe ask before rollBack?
            self.candidatesLayer.rollBack()
            self.restoreSelectionMode()
            self.refreshSelectionModeBehavior()

        self.isEditCandidatesToggled = toggled

        return toggled

    def __getCrs(self, layer: QgsMapLayer = None) -> QgsCoordinateReferenceSystem:
        if layer:
            return layer.sourceCrs()

        return self.project.crs()

    def __getCoordinateTransform(self, layer: QgsMapLayer) -> QgsCoordinateTransform:
        return QgsCoordinateTransform(
            self.__getCrs(),
            self.__getCrs(layer),
            self.project
        )

    def __getStylePath(self, file: str) -> str:
        return os.path.join(PLUGIN_DIR, 'styles', file)
