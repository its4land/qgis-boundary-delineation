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
import os
from collections import defaultdict
from typing import Optional, Union

from PyQt5.QtCore import QSettings, QTranslator, Qt
from PyQt5.QtWidgets import QAction, QToolBar
from PyQt5.QtGui import QIcon

from qgis.core import *
from qgis.core import QgsFeatureRequest, Qgis
from qgis.utils import *

import processing

# Initialize Qt resources from file resources.py
from .resources import *

from .BoundaryDelineationDock import BoundaryDelineationDock
from .MapSelectionTool import MapSelectionTool
from . import utils
from .utils import SelectionModes, processing_cursor
from .BoundaryGraph import NoSuitableGraphError, prepare_graph_from_lines, prepare_subgraphs, calculate_subgraphs_metric_closures, find_steiner_tree

PRECALCULATE_METRIC_CLOSURES = False
DEFAULT_SELECTION_MODE = SelectionModes.ENCLOSING

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
        self.project = QgsProject.instance()
        self.layerTree = self.project.layerTreeRoot()
        self.pluginDir = os.path.dirname(__file__)
        self.appName = 'BoundaryDelineation'

        self._initLocale()

        self.baseRasterLayerName = self.tr('Raster')
        self.segmentsLayerName = self.tr('Segments')
        self.simplifiedSegmentsLayerName = self.tr('Simplified Segments')
        self.verticesLayerName = self.tr('Vertices')
        self.candidatesLayerName = self.tr('Candidates')
        self.finalLayerName = self.tr('Final')
        self.groupName = self.tr('BoundaryDelineation')

        # groups
        # TODO finish this
        # self.group = self.layerTree.insertGroup(0, self.groupName)

        # map layers
        self.baseRasterLayer = None
        self.segmentsLayer = None
        self.simplifiedSegmentsLayer = None
        self.verticesLayer = None
        self.candidatesLayer = None
        self.finalLayer = None

        # Declare instance attributes
        self.actions = []
        self.canvas = self.iface.mapCanvas()

        self.pluginIsActive = False
        self.isMapSelectionToolEnabled = False
        self.isEditCandidatesToggled = False
        self.shouldAddLengthAttribute = False
        self.wasBaseRasterLayerInitiallyInLegend = True
        self.wasSegmentsLayerInitiallyInLegend = True
        self.previousMapTool = None
        self.dockWidget = None
        self.selectionMode = None
        self.edgesWeight = 'weight'

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


    def _initLocale(self):
        # Initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        localePath = os.path.join(self.pluginDir, 'i18n', '{}_{}.qm'.format(self.appName, locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            QCoreApplication.installTranslator(self.translator)


    def tr(self, message: str):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate(self.appName, message)

    def initGui(self):
        # Create action that will start plugin configuration
        action = QAction(QIcon(os.path.join(self.pluginDir, 'icons/icon.png')), self.appName, self.iface.mainWindow())
        self.actions.append(action)

        # Add information
        action.setWhatsThis(self.appName)

        # Add toolbar button to the Plugins toolbar
        self.iface.addToolBarIcon(action)

        # Add menu item to the Plugins menu
        self.iface.addPluginToMenu(self.appName, action)

        # Connect the action to the run method
        action.triggered.connect(self.run)

        self.canvas.mapToolSet.connect(self.onMapToolSet)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(self.appName), action)
            self.iface.removeToolBarIcon(action)

        self.mapSelectionTool.polygonCreated.disconnect(self.onPolygonSelectionCreated)
        self.toggleMapSelectionTool(False)

        if self.dockWidget:
            self.canvas.mapToolSet.disconnect(self.onMapToolSet)

        if not self.wasBaseRasterLayerInitiallyInLegend:
            utils.remove_layer(self.baseRasterLayer)

        if not self.wasSegmentsLayerInitiallyInLegend:
            utils.remove_layer(self.segmentsLayer)

        if self.candidatesLayer:
            self.candidatesLayer.rollBack()

        utils.remove_layer(self.simplifiedSegmentsLayer)
        utils.remove_layer(self.verticesLayer)
        utils.remove_layer(self.candidatesLayer)

    def run(self):
        if self.pluginIsActive:
            self.dockWidget.show()
            return

        self.pluginIsActive = True

        #print "** STARTING PCRasterShell"

        # dockwidget may not exist if:
        #    first run of plugin
        #    removed on close (see self.onClosePlugin method)
        if self.dockWidget == None:
            # Create the dockwidget (after translation) and keep reference
            self.dockWidget = BoundaryDelineationDock(self)

        # connect to provide cleanup on closing of dockwidget
        self.dockWidget.closingPlugin.connect(self.onClosePlugin)

        # show the dockwidget
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dockWidget)
        self.dockWidget.show()

    def showMessage(self, message, level = Qgis.Info, duration = 5):
        self.iface.messageBar().pushMessage(self.appName, message, level, duration)

    def toggleMapSelectionTool(self, toggle: bool = None):
        if toggle is None:
            toggle = not self.isMapSelectionToolEnabled

        if toggle:
            self.canvas.setMapTool(self.mapSelectionTool)
        else:
            self.canvas.unsetMapTool(self.mapSelectionTool)

        self.isMapSelectionToolEnabled = toggle

    def onMapToolSet(self, newTool, oldTool):
        if newTool is self.mapSelectionTool and self.previousMapTool is None:
            self.previousMapTool = oldTool

        if oldTool is self.mapSelectionTool and newTool is not self.mapSelectionTool:
            if self.dockWidget:
                self.dockWidget.updateSelectionModeButtons()

    def onPolygonSelectionCreated(self, startPoint: QgsPointXY, endPoint: QgsPointXY, modifiers: Qt.KeyboardModifiers):
        self.syntheticFeatureSelection(startPoint, endPoint, modifiers)

    def onCandidatesLayerFeatureChanged(self, featureId):
        self.dockWidget.updateCandidatesButtons()

    def onCandidatesLayerBeforeEditingStarted(self):
        pass
        # TODO this is nice, when somebody starts manually editing the layer and we are in different mode,
        # however does not work properly if we use the plugin in the normal way :(
        # if not self.selectionMode == SelectionModes.MANUAL:
        #     self.setSelectionMode(SelectionModes.MANUAL)

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        # disconnects
        # self.dockWidget.closingPlugin.disconnect(self.onClosePlugin)
        # self.canvas.mapToolSet.disconnect(self.onMapToolSet)
        # self.mapSelectionTool.polygonCreated.disconnect(self.onPolygonSelectionCreated)
        # self.toggleMapSelectionTool(False)


        # utils.remove_layer(self.segmentsLayer)
        # utils.remove_layer(self.simplifiedSegmentsLayer)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockWidget = None

        self.pluginIsActive = False

    @processing_cursor()
    def processFirstStep(self):
        self.dockWidget.step1ProgressBar.setValue(5)

        self.simplifySegmentsLayer()

        if self.shouldAddLengthAttribute:
            # TODO actually add the length attribute
            pass

        self.createCandidatesLayer()

        self.dockWidget.step1ProgressBar.setValue(25)

        self.extractSegmentsVertices()

        self.dockWidget.step1ProgressBar.setValue(50)

        self.polygonizeSegmentsLayer()

        self.dockWidget.step1ProgressBar.setValue(75)

        self.buildVerticesGraph()

        self.dockWidget.step1ProgressBar.setValue(100)

        self.setSelectionMode(DEFAULT_SELECTION_MODE)

        # TODO prevent deletion of the layers
        # self.layerTree.willRemoveChildren.connect(def (QgsLayerTreeNode *node, int indexFrom, int indexTo))

    def setBaseRasterLayer(self, baseRasterLayer: Union[QgsRasterLayer, str]):
        if isinstance(baseRasterLayer, str):
            self.wasBaseRasterLayerInitiallyInLegend = False
            baseRasterLayer = QgsRasterLayer(baseRasterLayer, self.baseRasterLayerName, 'ogr')

        self.baseRasterLayer = baseRasterLayer

        return baseRasterLayer

    def setSegmentsLayer(self, segmentsLayer: Union[QgsVectorLayer, str]):
        if isinstance(segmentsLayer, str):
            self.wasSegmentsLayerInitiallyInLegend = False
            segmentsLayer = QgsVectorLayer(segmentsLayer, self.segmentsLayerName, 'ogr')

        assert segmentsLayer.geometryType() == QgsWkbTypes.LineGeometry

        self.segmentsLayer = segmentsLayer

        return segmentsLayer

    def simplifySegmentsLayer(self):
        assert self.segmentsLayer

        result = processing.run('qgis:simplifygeometries', {
            'INPUT': self.segmentsLayer,
            'METHOD': 0,
            'TOLERANCE': 1.0,
            'OUTPUT': 'memory:simplifygeometries'
        })

        self.simplifiedSegmentsLayer = result['OUTPUT']
        utils.add_vector_layer(
            self.simplifiedSegmentsLayer,
            self.simplifiedSegmentsLayerName,
            colors=(0, 255, 0),
            file=self.__getStylePath('segments.qml')
            )

    def createCandidatesLayer(self) -> QgsVectorLayer:
        crs = self.__getCrs(self.segmentsLayer).authid()
        candidatesLayer = QgsVectorLayer('MultiLineString?crs=%s' % crs, self.candidatesLayerName, 'memory')
        finalLayer = QgsVectorLayer('MultiLineString?crs=%s' % crs, self.finalLayerName, 'memory')
        lineLayerFields = self.simplifiedSegmentsLayer.dataProvider().fields().toList()
        candidatesLayerFields= [QgsField(field.name(),field.type()) for field in lineLayerFields]
        # candidatesLayer.dataProvider().addAttributes(candidatesLayerFields)
        # candidatesLayer.updateFields()

        # utils.add_vector_layer(self.simplifiedSegmentsLayer, 'self.simplifiedSegmentsLayerName')
        # utils.add_vector_layer(self.segmentsLayer, 'self.segmentsLayerName')
        # utils.add_vector_layer(candidatesLayer, self.candidatesLayerName)
        utils.add_vector_layer(candidatesLayer, file=self.__getStylePath('candidates.qml'))
        utils.add_vector_layer(finalLayer, file=self.__getStylePath('final.qml'))

        candidatesLayer.featureAdded.connect(self.onCandidatesLayerFeatureChanged)
        candidatesLayer.featuresDeleted.connect(self.onCandidatesLayerFeatureChanged)
        candidatesLayer.beforeEditingStarted.connect(self.onCandidatesLayerBeforeEditingStarted)

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

        # utils.add_vector_layer(self.verticesLayer, self.verticesLayerName, (255, 0, 0), 1.3, legend=False)
        utils.add_vector_layer(self.verticesLayer, self.verticesLayerName, (255, 0, 0), 1.3)

        return self.verticesLayer

    def polygonizeSegmentsLayer(self) -> QgsVectorLayer:
        assert self.simplifiedSegmentsLayer

        polygonizedResult = processing.run('qgis:polygonize', {
            'INPUT': self.simplifiedSegmentsLayer,
            'OUTPUT': 'memory:polygonized',
        })

        self.polygonizedLayer = polygonizedResult['OUTPUT']

        return self.polygonizedLayer

    def buildVerticesGraph(self):
        assert self.simplifiedSegmentsLayer

        self.graph = prepare_graph_from_lines(self.simplifiedSegmentsLayer)
        self.subgraphs = prepare_subgraphs(self.graph)
        self.metricClosureGraphs = calculate_subgraphs_metric_closures(self.subgraphs) if PRECALCULATE_METRIC_CLOSURES else None

        return self.graph

    def setSelectionMode(self, mode: SelectionModes):
        self.selectionMode = mode

        self.refreshSelectionModeBehavior()
        self.dockWidget.updateSelectionModeButtons()

    def refreshSelectionModeBehavior(self):
        if self.selectionMode == SelectionModes.MANUAL:
            self.toggleMapSelectionTool(False)
            self.iface.setActiveLayer(self.candidatesLayer)
            self.candidatesLayer.rollBack()
            self.candidatesLayer.startEditing()

            assert self.candidatesLayer.isEditable()

            self.iface.actionAddFeature().trigger()
        else:
            self.toggleMapSelectionTool(True)

    @processing_cursor()
    def syntheticFeatureSelection(self, startPoint: QgsPointXY, endPoint: QgsPointXY, modifiers: Qt.KeyboardModifiers) -> None:
        if startPoint is None or endPoint is None:
            raise Exception('Something went very bad, unable to create selection without start or end point')

        isControlPressed = False

        # check the Shift and Control modifiers to reproduce the navive selection
        if modifiers & Qt.ShiftModifier:
            selectBehaviour = QgsVectorLayer.AddToSelection
        elif modifiers & Qt.ControlModifier:
            selectBehaviour = QgsVectorLayer.RemoveFromSelection
        else:
            selectBehaviour = QgsVectorLayer.SetSelection

        lines = None
        rect = QgsRectangle(startPoint, endPoint)

        if self.selectionMode == SelectionModes.ENCLOSING:
            lines = self.getLinesSelectionModeEnclosing(selectBehaviour, rect)
        elif self.selectionMode == SelectionModes.NODES:
            lines = self.getLinesSelectionModeNodes(selectBehaviour, rect)

            if lines is None:
                return
        else:
            raise Exception('Wrong selection mode selected, should never be the case')

        assert lines, 'There should be at least one feature'

        if not self.addCandidates(lines):
            self.showMessage(self.tr('Unable to add candidates'))
            return

    def getLinesSelectionModeEnclosing(self, selectBehaviour, rect):
        rect = self.__getCoordinateTransform(self.polygonizedLayer).transform(rect)

        self.polygonizedLayer.selectByRect(rect, selectBehaviour)

        selectedPolygonsLayer = utils.selected_features_to_layer(self.polygonizedLayer)
        dissolvedPolygonsLayer = utils.dissolve_layer(selectedPolygonsLayer)
        return utils.polygons_layer_to_lines_layer(dissolvedPolygonsLayer).getFeatures()

    def getLinesSelectionModeNodes(self, selectBehaviour, rect):
        rect = self.__getCoordinateTransform(self.polygonizedLayer).transform(rect)

        self.verticesLayer.selectByRect(rect, selectBehaviour)

        if self.verticesLayer.selectedFeatureCount() <= 1:
            self.candidatesLayer.rollBack()
            # TODO there are self enclosing blocks that can be handled here (one node that is conected to itself)
            self.showMessage(self.tr('Please select two or more nodes to be connected'))
            return

        selectedPoints = [f.geometry().asPoint() for f in self.verticesLayer.selectedFeatures()]

        try:
            if self.metricClosureGraphs is None:
                self.metricClosureGraphs = calculate_subgraphs_metric_closures(self.subgraphs)

            T = find_steiner_tree(self.subgraphs, selectedPoints, metric_closures=self.metricClosureGraphs)
        except NoSuitableGraphError:
            # this is hapenning when the user selects nodes from two separate graphs
            return

        # edge[2] stays for the line ids
        featureIds = [edge[2] for edge in T.edges(keys=True)]

        pointsMap = defaultdict(int)

        for f in self.simplifiedSegmentsLayer.getFeatures(featureIds):
            geom = f.geometry()

            is_multipart = geom.isMultipart()

            if is_multipart:
                lines = geom.asMultiPolyline()
            else:
                lines = [geom.asPolyline()]

            for idx, line in enumerate(lines):
                startPoint = line[0]
                endPoint = line[-1]

                pointsMap[startPoint] += 1
                pointsMap[endPoint] += 1

            lines.append(f)

        points = [k for k, v in pointsMap.items() if v == 1]

        if len(points) != 2:
            self.showMessage(self.tr('Unable to find the shortest path'))
            return

        if self.graph.has_edge(*points):
            edgesDict = self.graph[points[0]][points[1]]
            bestEdgeKey = None
            bestEdgeValue = None

            for k, e in edgesDict.items():
                # find the cheapest edge that is not already selected (in case there are two nodes
                # selected and there are more than one edges connecting them)
                if k not in featureIds and (bestEdgeValue is None or bestEdgeValue > e[self.edgesWeight]):
                    bestEdgeKey = k
                    bestEdgeValue = e[self.edgesWeight]

            if bestEdgeKey:
                featureIds.append(bestEdgeKey)

        return [f for f in self.simplifiedSegmentsLayer.getFeatures(featureIds)]


    def addCandidates(self, lineFeatures: QgsFeatureIterator) -> bool:
        self.candidatesLayer.rollBack()
        self.candidatesLayer.startEditing()

        if not self.candidatesLayer.isEditable():
            self.showMessage(self.tr('Unable to add features as candidates #1'))
            return False

        features = []

        for f in lineFeatures:
            # TODO this is really ugly hack to remove all the attributes that do not match between layers
            f.setAttributes([])
            features.append(f)

        if not self.candidatesLayer.addFeatures(features):
            self.showMessage(self.tr('Unable to add features as candidates #2'))
            return False

        self.candidatesLayer.triggerRepaint()

        return True

    def acceptCandidates(self) -> bool:
        assert self.candidatesLayer.featureCount() > 0

        self.finalLayer.startEditing()

        return self.finalLayer.isEditable() and \
            self.finalLayer.addFeatures(self.candidatesLayer.getFeatures()) and \
            self.finalLayer.commitChanges() and \
            self.rejectCandidates() # empty the canidates layer :)

    def rejectCandidates(self) -> bool:
        self.candidatesLayer.startEditing()
        self.candidatesLayer.selectAll()

        return self.candidatesLayer.isEditable() and \
            self.candidatesLayer.deleteSelectedFeatures() and \
            self.candidatesLayer.commitChanges()

    def toggleEditCandidates(self, toggled: bool = None) -> bool:
        if toggled is None:
            toggled = not self.isEditCandidatesToggled

        if toggled:
            self.candidatesLayer.startEditing()

            if not self.candidatesLayer.isEditable():
                return False

            self.iface.setActiveLayer(self.candidatesLayer)
            self.iface.actionVertexTool().trigger()

        self.isEditCandidatesToggled = toggled

        return toggled

    def __getCrs(self, layer: Union[QgsVectorLayer, QgsRasterLayer] = None) -> QgsCoordinateReferenceSystem:
        if layer:
            return layer.sourceCrs()

        return self.project.crs()

    def __getCoordinateTransform(self, layer: Union[QgsVectorLayer, QgsRasterLayer]) -> QgsCoordinateTransform:
        return QgsCoordinateTransform(
            self.__getCrs(),
            self.__getCrs(layer),
            self.project
        )

    def __getStylePath(self, file: str) -> None:
        return os.path.join(self.pluginDir, 'styles', file)
