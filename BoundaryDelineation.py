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
import typing
from collections import defaultdict

from PyQt5.QtCore import QSettings, QTranslator, Qt, QVariant
from PyQt5.QtWidgets import QAction, QToolBar, QMessageBox
from PyQt5.QtGui import QIcon

from qgis.core import *
from qgis.gui import QgisInterface, QgsMapTool
from qgis.utils import *

import processing

# Initialize Qt resources from file resources.py
from .resources import *

from .BoundaryDelineationDock import BoundaryDelineationDock
from .MapSelectionTool import MapSelectionTool
from . import utils
from .utils import SelectionModes, processing_cursor
from .BoundaryGraph import NoSuitableGraphError, prepare_graph_from_lines, prepare_subgraphs, calculate_subgraphs_metric_closures, find_steiner_tree, DEFAULT_WEIGHT_NAME

PRECALCULATE_METRIC_CLOSURES = False
DEFAULT_SELECTION_MODE = SelectionModes.ENCLOSING

SelectBehaviour = int
MessageLevel = int

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
        self.group = self.getGroup()

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

        self.isMapSelectionToolEnabled = False
        self.isEditCandidatesToggled = False
        self.shouldAddLengthAttribute = False
        self.wasBaseRasterLayerInitiallyInLegend = True
        self.wasSegmentsLayerInitiallyInLegend = True
        self.previousMapTool = None
        self.dockWidget = None
        self.selectionMode = None
        self.edgesWeightField = DEFAULT_WEIGHT_NAME
        self.lengthAttributeName = 'BD_LEN'
        self.metricClosureGraphs = {}

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
        localePath = os.path.join(self.pluginDir, 'i18n', '{}_{}.qm'.format(self.appName, locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            QCoreApplication.installTranslator(self.translator)


    def tr(self, message: str) -> None:
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate(self.appName, message)

    def initGui(self) -> None:
        # Create action that will start plugin configuration
        action = QAction(QIcon(os.path.join(self.pluginDir, 'icons/icon.png')), self.appName, self.iface.mainWindow())
        self.actions.append(action)

        action.setWhatsThis(self.appName)

        # Add toolbar button to the Plugins toolbar
        self.iface.addToolBarIcon(action)

        # Add menu item to the Plugins menu
        self.iface.addPluginToMenu(self.appName, action)

        # Connect the action to the run method
        action.triggered.connect(self.run)

        # Create the dockwidget (after translation) and keep reference
        self.dockWidget = BoundaryDelineationDock(self)

        # show the dockwidget
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dockWidget)
        self.dockWidget.closingPlugin.connect(self.onClosePlugin)

        self.canvas.mapToolSet.connect(self.onMapToolSet)

    def unload(self) -> None:
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(self.appName), action)
            self.iface.removeToolBarIcon(action)

        # TODO very stupid workaround. Should find a way to check if method is connected!
        try:
            self.mapSelectionTool.polygonCreated.disconnect(self.onPolygonSelectionCreated)
        except:
            pass
        # self.layerTree.willRemoveChildren.disconnect(self.onLayerTreeWillRemoveChildren)

        self.toggleMapSelectionTool(False)

        if self.dockWidget:
            self.iface.removeDockWidget(self.dockWidget)

            # self.dockWidget.closingPlugin.disconnect(self.onClosePlugin)
            self.dockWidget.hide()
            self.dockWidget.destroy()

            del self.dockWidget

            self.dockWidget = None

        self.resetProcessed()

    def run(self, checked: bool) -> None:
        if self.dockWidget.isVisible():
            self.dockWidget.hide()
        else:
            self.dockWidget.show()

    def getGroup(self) -> QgsLayerTreeGroup:
        group = self.layerTree.findGroup(self.groupName)

        if not group:
            group = self.layerTree.insertGroup(0, self.groupName)

        return group

    def showMessage(self, message: str, level: MessageLevel = Qgis.Info, duration: int = 5) -> None:
        self.iface.messageBar().pushMessage(self.appName, message, level, duration)

    def toggleMapSelectionTool(self, toggle: bool = None) -> None:
        if toggle is None:
            toggle = not self.isMapSelectionToolEnabled

        if toggle:
            self.canvas.setMapTool(self.mapSelectionTool)
        else:
            self.canvas.unsetMapTool(self.mapSelectionTool)

        self.isMapSelectionToolEnabled = toggle

    def onMapToolSet(self, newTool: QgsMapTool, oldTool: typing.Optional[QgsMapTool]) -> None:
        if newTool is self.mapSelectionTool and self.previousMapTool is None:
            self.previousMapTool = oldTool

        if oldTool is self.mapSelectionTool and newTool is not self.mapSelectionTool:
            self.dockWidget.updateSelectionModeButtons()

            if self.selectionMode is not SelectionModes.MANUAL:
                self.setSelectionMode(SelectionModes.NONE)

    def onPolygonSelectionCreated(self, startPoint: QgsPointXY, endPoint: QgsPointXY, modifiers: Qt.KeyboardModifiers) -> None:
        self.syntheticFeatureSelection(startPoint, endPoint, modifiers)

    def onCandidatesLayerFeatureChanged(self, featureIds: typing.Union[int, typing.List[int]]) -> None:
        enable = self.candidatesLayer.featureCount() > 0

        self.dockWidget.setCandidatesButtonsEnabled(enable)

    def onFinalLayerFeaturesChanged(self, featureIds: typing.Union[int, typing.List[int]]) -> None:
        enable = self.finalLayer.featureCount() > 0

        self.dockWidget.setFinalButtonEnabled(enable)

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

    @processing_cursor()
    def processFirstStep(self) -> None:
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
        self.showMessage(self.tr('Boundary deliniation finished, see the currently active layer for all the results'))
        self.iface.setActiveLayer(self.finalLayer)
        self.resetProcessed()

    def resetProcessed(self) -> None:
        self.toggleMapSelectionTool(False)

        if not self.wasBaseRasterLayerInitiallyInLegend:
            utils.remove_layer(self.baseRasterLayer)
            self.baseRasterLayer = None

        if not self.wasSegmentsLayerInitiallyInLegend:
            utils.remove_layer(self.segmentsLayer)
            self.segmentsLayer = None

        if self.candidatesLayer:
            self.candidatesLayer.featureAdded.disconnect(self.onCandidatesLayerFeatureChanged)
            self.candidatesLayer.featuresDeleted.disconnect(self.onCandidatesLayerFeatureChanged)
            self.candidatesLayer.beforeEditingStarted.disconnect(self.onCandidatesLayerBeforeEditingStarted)
            self.candidatesLayer.rollBack()

        utils.remove_layer(self.simplifiedSegmentsLayer)
        utils.remove_layer(self.verticesLayer)
        utils.remove_layer(self.candidatesLayer)

        if self.finalLayer:
            self.finalLayer.featureAdded.disconnect(self.onFinalLayerFeaturesChanged)
            self.finalLayer.featuresDeleted.disconnect(self.onFinalLayerFeaturesChanged)

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
            return baseRasterLayer

        self.group = self.getGroup()

        if isinstance(baseRasterLayer, str):
            self.wasBaseRasterLayerInitiallyInLegend = False
            baseRasterLayer = QgsRasterLayer(baseRasterLayer, self.baseRasterLayerName)

            self.project.addMapLayer(baseRasterLayer)

        self.baseRasterLayer = baseRasterLayer

        return baseRasterLayer

    def setSegmentsLayer(self, segmentsLayer: typing.Union[QgsVectorLayer, str]) -> None:
        if self.segmentsLayer is segmentsLayer:
            return segmentsLayer

        self.group = self.getGroup()

        if isinstance(segmentsLayer, str):
            self.wasSegmentsLayerInitiallyInLegend = False
            segmentsLayer = QgsVectorLayer(segmentsLayer, self.segmentsLayerName, 'ogr')

            utils.add_vector_layer(segmentsLayer, self.segmentsLayerName, parent=self.group)

        if segmentsLayer.geometryType() != QgsWkbTypes.LineGeometry:
            self.showMessage(self.tr('Please use segments layer that is with lines geometry'))

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

        result = processing.run('qgis:simplifygeometries', {
            'INPUT': self.segmentsLayer,
            'METHOD': 0,
            'TOLERANCE': 1.0,
            'OUTPUT': 'memory:simplifygeometries'
        })

        # if self.wasSegmentsLayerInitiallyInLegend:
        if self.layerTree.findLayer(self.segmentsLayer.id()):
            self.layerTree.findLayer(self.segmentsLayer.id()).setItemVisibilityChecked(False)

        self.simplifiedSegmentsLayer = result['OUTPUT']

        self.dockWidget.setComboboxLayer(self.simplifiedSegmentsLayer)

        utils.add_vector_layer(
            self.simplifiedSegmentsLayer,
            self.simplifiedSegmentsLayerName,
            colors=(0, 255, 0),
            file=self.__getStylePath('segments.qml'),
            parent=self.group
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
        self.metricClosureGraphs[self.edgesWeightField] = calculate_subgraphs_metric_closures(self.subgraphs, weight=self.edgesWeightField) if PRECALCULATE_METRIC_CLOSURES else None

    def isPluginLayerTreeNode(self, node: QgsLayerTree) -> bool:
        # for some reason even the normal nodes are behaving like groups...
        if QgsLayerTree.isGroup(node):
            # unfortunately this does not work in Python, it's cpp only...
            # group = QgsLayerTree.toGroup(node)

            # All my other attempts also failed miserably
            # group = self.layerTree.findGroup(self.groupName)
            # print(111, group, node, len(node.name()), node.name())
            # return group is self.group
            pass
        else:
            layer = self.project.mapLayer(node.layerId())
            print(111, node, layer)

            if layer in (self.simplifiedSegmentsLayer, self.verticesLayer, self.candidatesLayer, self.finalLayer):
                return True

            if self.wasBaseRasterLayerInitiallyInLegend and layer is self.baseRasterLayer:
                return True
            if self.wasSegmentsLayerInitiallyInLegend and layer is self.segmentsLayer:
                return True

        return False

    def createFinalLayer(self) -> QgsVectorLayer:
        filename = self.dockWidget.getOutputLayer()
        crs = self.__getCrs()

        if os.path.isfile(filename):
            finalLayer = QgsVectorLayer(filename, self.finalLayerName, 'ogr')
        else:
            finalLayer = QgsVectorLayer('MultiLineString?crs=%s' % crs.authid(), self.finalLayerName, 'memory')

            if filename:
                (writeErrorCode, writeErrorMsg) = QgsVectorFileWriter.writeAsVectorFormat(finalLayer, filename, 'utf-8', crs, 'ESRI Shapefile')
                if writeErrorMsg:
                    self.showMessage('[%s] %s' % (writeErrorCode, writeErrorMsg))

        return finalLayer

    def createCandidatesLayer(self) -> QgsVectorLayer:
        crs = self.__getCrs(self.segmentsLayer).authid()
        candidatesLayer = QgsVectorLayer('MultiLineString?crs=%s' % crs, self.candidatesLayerName, 'memory')
        finalLayer = self.createFinalLayer()
        lineLayerFields = self.simplifiedSegmentsLayer.dataProvider().fields().toList()
        candidatesLayerFields= [QgsField(field.name(),field.type()) for field in lineLayerFields]
        # candidatesLayer.dataProvider().addAttributes(candidatesLayerFields)
        # candidatesLayer.updateFields()

        utils.add_vector_layer(candidatesLayer, file=self.__getStylePath('candidates.qml'), parent=self.group)
        utils.add_vector_layer(finalLayer, file=self.__getStylePath('final.qml'), parent=self.group)

        candidatesLayer.featureAdded.connect(self.onCandidatesLayerFeatureChanged)
        candidatesLayer.featuresDeleted.connect(self.onCandidatesLayerFeatureChanged)
        candidatesLayer.beforeEditingStarted.connect(self.onCandidatesLayerBeforeEditingStarted)
        finalLayer.featureAdded.connect(self.onFinalLayerFeaturesChanged)
        finalLayer.featuresDeleted.connect(self.onFinalLayerFeaturesChanged)

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

        utils.add_vector_layer(self.verticesLayer, self.verticesLayerName, (255, 0, 0), 1.3, parent=self.group)

        return self.verticesLayer

    def polygonizeSegmentsLayer(self) -> QgsVectorLayer:
        assert self.simplifiedSegmentsLayer

        polygonizedResult = processing.run('qgis:polygonize', {
            'INPUT': self.simplifiedSegmentsLayer,
            'OUTPUT': 'memory:polygonized',
        })

        self.polygonizedLayer = polygonizedResult['OUTPUT']

        return self.polygonizedLayer

    def buildVerticesGraph(self) -> None:
        assert self.simplifiedSegmentsLayer

        self.graph = prepare_graph_from_lines(self.simplifiedSegmentsLayer)
        self.subgraphs = prepare_subgraphs(self.graph)
        self.metricClosureGraphs[self.edgesWeightField] = self.calculateMetricClosure() if PRECALCULATE_METRIC_CLOSURES else None

    def calculateMetricClosure(self) -> typing.List[typing.Any]:
        self.showMessage(self.tr('It may take some time to precalculate the most optimal boundaries...'))
        return calculate_subgraphs_metric_closures(self.subgraphs, weight=self.edgesWeightField)

    def setSelectionMode(self, mode: SelectionModes) -> None:
        self.selectionMode = mode

        self.refreshSelectionModeBehavior()
        self.dockWidget.updateSelectionModeButtons()

    def refreshSelectionModeBehavior(self) -> None:
        if self.selectionMode is SelectionModes.NONE:
            return
        elif self.selectionMode == SelectionModes.MANUAL:
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

    def getLinesSelectionModeEnclosing(self, selectBehaviour: SelectBehaviour, rect: QgsRectangle) -> None:
        rect = self.__getCoordinateTransform(self.polygonizedLayer).transform(rect)

        self.polygonizedLayer.selectByRect(rect, selectBehaviour)

        selectedPolygonsLayer = utils.selected_features_to_layer(self.polygonizedLayer)
        dissolvedPolygonsLayer = utils.dissolve_layer(selectedPolygonsLayer)
        return utils.polygons_layer_to_lines_layer(dissolvedPolygonsLayer).getFeatures()

    def getLinesSelectionModeNodes(self, selectBehaviour: SelectBehaviour, rect: QgsRectangle) -> None:
        rect = self.__getCoordinateTransform(self.polygonizedLayer).transform(rect)

        self.verticesLayer.selectByRect(rect, selectBehaviour)

        selectedPoints = [f.geometry().asPoint() for f in self.verticesLayer.selectedFeatures()]

        if len(selectedPoints) <= 1:
            neighbors = []

            if len(selectedPoints) == 1:
                neighbors = list(self.graph.neighbors(selectedPoints[0]))

            if len(neighbors) == 1:
                edges = self.graph[selectedPoints[0]][selectedPoints[0]]
                edgeId = list(edges.keys())[0]

                return [f for f in self.simplifiedSegmentsLayer.getFeatures([edgeId])]

            self.candidatesLayer.rollBack()
            # TODO there are self enclosing blocks that can be handled here (one node that is conected to itself)
            self.showMessage(self.tr('Please select two or more nodes to be connected'))
            return

        try:
            if self.metricClosureGraphs[self.edgesWeightField] is None:
                self.metricClosureGraphs[self.edgesWeightField] = self.calculateMetricClosure()

            T = find_steiner_tree(self.subgraphs, selectedPoints, metric_closures=self.metricClosureGraphs[self.edgesWeightField])
        except NoSuitableGraphError:
            # this is hapenning when the user selects nodes from two separate graphs
            return

        # edge[2] stays for the line ids
        featureIds = [edge[2] for edge in T.edges(keys=True)]

        # The following allows closing the lines if the two endpoints are also connected by an edge
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
                if k not in featureIds and (bestEdgeValue is None or bestEdgeValue > e[self.edgesWeightField]):
                    bestEdgeKey = k
                    bestEdgeValue = e[self.edgesWeightField]

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
        else:
            # TODO maybe ask before rollback?
            self.candidatesLayer.rollBack()
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

    def __getStylePath(self, file: str) -> None:
        return os.path.join(self.pluginDir, 'styles', file)
