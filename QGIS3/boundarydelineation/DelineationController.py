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
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QVariant, Qt
from PyQt5.QtGui import QIcon, QColor, QPixmap, QCursor
from PyQt5.QtWidgets import QApplication, QAction, QFileDialog, QToolBar

from qgis.core import QgsProject, Qgis, QgsMapLayer, QgsVectorLayer, QgsVectorFileWriter, \
    QgsLineSymbol, QgsMarkerSymbol, QgsProcessingUtils, QgsFeature, QgsGeometry, QgsField, \
    QgsSingleSymbolRenderer, QgsLineSymbol, QgsProperty, QgsCoordinateReferenceSystem
from qgis.utils import iface

import processing
import os

class DelineationController:
    
    # Define layer and plugin name
    appName = 'BoundaryDelineation'
    pluginName = appName + ' plugin'
    rasterLayerName = 'input image'
    lineLayerName = 'input lines'
    nodeLayerName = 'nodes'
    candidateBoundaryLayerName = 'candidate boundary'
    boundaryColumnName = 'boundary'
    finalBoundaryLayerName = 'final boundary'
    pluginPath = os.path.dirname(__file__)
    
    mainWidget = None

    inputRaster = None
    inputFileName = None
    outputFileName = None
    edgesGraph = None
    metricClosureGraph = None
    
    @staticmethod
    def showMessage(message, level = Qgis.Info, duration=5):
        iface.messageBar().pushMessage(DelineationController.pluginName, message, level, duration)
        
    @staticmethod
    def showBusyCursor():
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

    @staticmethod
    def hideBusyCursor():
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()

    @staticmethod
    def getActiveLayer():
        return iface.activeLayer()
    
    @staticmethod
    def setActiveLayer(layer):
        if not isinstance(layer, QgsMapLayer):
            layer = DelineationController.getLayerByName(layer)
        if layer is not None:
            iface.setActiveLayer(layer)
    
    @staticmethod
    def setLayerVisibility (layer, visible):
        if layer is not None:
            layerNode = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
            if layerNode is not None:
                layerNode.setItemVisibilityChecked(visible)
                return True
        return False

    @staticmethod
    def getLayerByName (name, showError = False):
        try:
            return QgsProject.instance().mapLayersByName(name)[0]
        except Exception as exc:
            if showError:
                DelineationController.showMessage("Layer {0} not found! Message: {1}".format(name, exc), Qgis.Critical)
            return None

    @staticmethod
    def addRasterLayer (layerName, fileName):
        return iface.addRasterLayer(fileName, layerName)

    @staticmethod
    def checkRasterLayer (layerName, fileName, showMsg = False):
        layer = DelineationController.getLayerByName (layerName)
        if layer is None:
            if fileName:
                try:
                    return DelineationController.addRasterLayer(layerName, fileName)
                except:
                    DelineationController.showMessage("Unable to open %s" % fileName, Qgis.Critical)
            return None
        if showMsg:
            DelineationController.showMessage("%s already loaded" % layerName, Qgis.Warning)
        return layer
    
    @staticmethod
    def _getCrs():
        layer = DelineationController.getLineLayer()
        if layer is not None:
            return layer.crs()
        else:
            return QgsProject.instance().crs()

    @staticmethod
    def _getLineVectorPath(crs = None):
        if crs is None:
            crs = DelineationController._getCrs()
        return "MultiLineString?{0}".format(crs.authid())

    @staticmethod
    def addVectorLayer (layerName, fileName, create = True):
        if bool(fileName) and os.path.isfile(fileName): 
            layer = QgsVectorLayer(fileName, layerName, 'ogr')
        elif create:
            layer = QgsVectorLayer(DelineationController._getLineVectorPath(), layerName, 'ogr')
        else:
            layer = None
        DelineationController.addLayerToMap(layer, layerName)
        return layer

    @staticmethod
    def checkVectorLayer (layerName, fileName, showMsg = True):
        layer = DelineationController.getLayerByName (layerName)
        if layer is None:
            if fileName:
                try:
                    return DelineationController.addVectorLayer(layerName, fileName, create = False)
                except:
                    DelineationController.showMessage("Unable to open %s" % fileName, Qgis.Critical)
            return None
        if showMsg:
            DelineationController.showMessage("%s already loaded" % layerName, Qgis.Warning)
        return layer

    @staticmethod
    def removeLayer(layer):
        if layer is not None:
            QgsProject.instance().removeMapLayer(layer.id())
            return True
        return False

    @staticmethod
    def replaceLayer(layerName, newUri):
        # Check if layer is already loaded
        layer = DelineationController.getLayerByName (layerName, False)
        if layer is not None:
            return DelineationController.replaceLayerUri(layer, DelineationController.getLayerUri(layer), newUri) 
        return None

    @staticmethod
    def replaceLayerUri(layer, currentUri, newUri):
        # Check if layer is already loaded
        if layer is not None:
            if currentUri:
                if currentUri == newUri or (os.path.isfile(currentUri) and os.path.isfile(newUri) and os.path.samefile(currentUri, newUri)):
                    return layer
            DelineationController.removeLayer(layer)
        return None

    @staticmethod
    def getRasterLayer(showError = True):
        return DelineationController.getLayerByName(DelineationController.rasterLayerName, showError)
    
    @staticmethod
    def getLineLayer(showError = True):
        return DelineationController.getLayerByName(DelineationController.lineLayerName, showError)
    
    @staticmethod
    def getNodeLayer(showError = True):
        return DelineationController.getLayerByName(DelineationController.nodeLayerName, showError)

    @staticmethod
    def getCandidatesLayer(create = False, showError = True):
        layer = DelineationController.getLayerByName(DelineationController.candidateBoundaryLayerName, showError)
        if create and layer is None:
            layer = DelineationController.createMemoryLayer(DelineationController.candidateBoundaryLayerName)
        DelineationController.addLayerToMap(layer, DelineationController.candidateBoundaryLayerName, 0, 255, 255, 0.5)
        return layer

    @staticmethod
    def getFinalBoundaryLayer(create = True, showError = True):
        layer = DelineationController.getLayerByName(DelineationController.finalBoundaryLayerName, showError and not create)
        if layer is None and bool(DelineationController.outputFileName) and (create or os.path.isfile(DelineationController.outputFileName)):
            if os.path.isfile(DelineationController.outputFileName):
                layer = QgsVectorLayer(DelineationController.outputFileName, DelineationController.finalBoundaryLayerName, 'ogr')
            if layer is None and create:
                layer = DelineationController.createVectorLayer(DelineationController.finalBoundaryLayerName,
                                                                DelineationController.outputFileName)
            DelineationController.addLayerToMap(layer, DelineationController.finalBoundaryLayerName, 0, 0, 255, 0.5)
        return layer

    @staticmethod
    def getLayerNameUri(layerName):
        return DelineationController.getLayerUri(DelineationController.getLayerByName(layerName))

    @staticmethod
    def getLayerUri(layer):
        if layer is not None:
            uri = layer.dataProvider().dataSourceUri(expandAuthConfig = False)
            if uri:
                return uri.split('|')[0]
            return 
        return None
    
    @staticmethod
    def _setLayerEditable(layer, activateAdd):
        if layer is not None:
            if layer.isEditable():
                return True
            # Start editing mode for layer
            layer.startEditing()
            if layer.isEditable():
                if activateAdd:
                    # Enable add feature mode
                    iface.actionAddFeature().trigger()
                return True
        return False

    @staticmethod
    def copyFeatures(fromLayer, toLayer):
        if fromLayer is not None and toLayer is not None:
            if fromLayer.featureCount() > 0:
                prov = toLayer.dataProvider()
                if len(toLayer.attributeList()) <= 0:
                    prov.addAttributes(fromLayer.fields())
                    toLayer.updateFields() 
                toLayer.startEditing()
                if toLayer.isEditable():
                    prov.addFeatures(fromLayer.getFeatures())
                    toLayer.commitChanges()
                else:
                    return False
            return True
        return False
    
    # Set symbology for vector layer (lines and points)
    @staticmethod
    def addLayerToMap(layer, name = None, red = None, green = None, blue = None, size = None):
        if layer is not None:
            if name:
                layer.setName(name)
            if red is not None:
                DelineationController.updateSymbology(layer, red, green, blue, size)
            layer.setCrs(QgsProject.instance().crs())
            QgsProject.instance().addMapLayer(layer)

    # Set symbology for vector layer (lines and points)
    @staticmethod
    def updateSymbology(layer, red, green, blue, size):
        if layer is not None:
            # Get symbology renderer
            renderer = layer.renderer()
            if renderer is not None:
                symbol = renderer.symbol()

                # Set color and width
                symbol.setColor(QColor.fromRgb(red, green, blue))
                if size is not None:
                    # For lines
                    if type(symbol) == QgsLineSymbol:
                        symbol.setWidth(size)
                    # For points
                    if type(symbol) == QgsMarkerSymbol:
                        symbol.setSize(size)
            # Repaint layer
            layer.triggerRepaint()
            # Repaint layer legend
            iface.layerTreeView().refreshLayerSymbology(layer.id())


    ### Step I ###
    
    @staticmethod
    def currentInputRasterUri():
        return DelineationController.getLayerNameUri(DelineationController.rasterLayerName)
    
    @staticmethod
    def currentInputLineUri():
        if DelineationController.getLineLayer(False) is None:
            DelineationController.inputFileName = None
        return DelineationController.inputFileName
        #return DelineationController.getLayerNameUri(DelineationController.lineLayerName)
    
    @staticmethod
    def currentOutputLineUri():
        layer = DelineationController.getFinalBoundaryLayer(create = False, showError = False)
        if layer is not None:
            DelineationController.outputFileName = DelineationController.getLayerUri(layer)
        return DelineationController.outputFileName
    
    # Load layer to canvas
    @staticmethod
    def openRaster(rasterFile):
        # Check if layer is already loaded
        layer = DelineationController.replaceLayer(DelineationController.rasterLayerName, rasterFile)
        DelineationController.inputRaster = DelineationController.rasterLayerName
        if layer is None:
            layer = DelineationController.checkRasterLayer (DelineationController.rasterLayerName, rasterFile, False)
            if layer is not None:
                DelineationController.mainWidget.canvas.setExtent(layer.extent())
                iface.zoomFull()
        return layer

    # Load layer to canvas
    @staticmethod
    def openInputVector(vectorFile):
        # Check if layer is already loaded
        layer = DelineationController.replaceLayerUri(DelineationController.getLineLayer(False), DelineationController.inputFileName, vectorFile)
        if layer is None:
            DelineationController.inputFileName = None
            DelineationController.edgesGraph = None
            DelineationController.metricClosureGraph = None
            try:
                DelineationController.showBusyCursor()
                # Douglas-Peucker line simplification
                result = processing.run('qgis:simplifygeometries',
                                             {"INPUT": vectorFile,
                                              "METHOD": 0,
                                              "TOLERANCE": 1.0,
                                              "OUTPUT": 'memory:simplifygeometries'})
                layer = result['OUTPUT']
                if isinstance(layer, QgsMapLayer):
                    DelineationController.removeLayer(DelineationController.getNodeLayer(False))
                    DelineationController.removeLayer(DelineationController.getCandidatesLayer(create = False, showError = False))
                    DelineationController.inputFileName = vectorFile
                    # property = QgsProperty()
                    # property.setExpressionString('"boundary" * -1')
                    # symbol = QgsLineSymbol()
                    # symbol.setDataDefinedWidth(property)
                    # renderer = QgsSingleSymbolRenderer(symbol)
                    # layer.setRenderer(renderer)
                    DelineationController.addLayerToMap(layer, DelineationController.lineLayerName, 0, 255, 0, None)
                    styleFilepath = DelineationController.pluginPath + "/style.qml"
                    layer.loadNamedStyle(styleFilepath)
            finally:
                DelineationController.hideBusyCursor()
        return layer

    @staticmethod
    def openOutputVector(vectorFile):
        # Check if layer is already loaded
        layer = DelineationController.replaceLayerUri(DelineationController.getFinalBoundaryLayer(create = False, showError = False), DelineationController.outputFileName, vectorFile)
        DelineationController.outputFileName = vectorFile
        if layer is None and bool(vectorFile):
            layer = DelineationController.getFinalBoundaryLayer(create = False, showError = False)
        return layer

    # create vector layer
    @staticmethod
    def createVectorLayer(layerName, fileName):
        # Check if layer is already loaded
        layer = DelineationController.getLayerByName(layerName)
        if layer is None and bool(fileName):
            crs = DelineationController._getCrs()
            layerPath = DelineationController._getLineVectorPath(crs)
            layer = DelineationController.addVectorLayer(layerName, fileName, create = True)
            QgsVectorFileWriter.writeAsVectorFormat(layer, fileName, "utf-8", crs, "ESRI Shapefile")
            layer = DelineationController.addVectorLayer(layerName, fileName, create = False)
        return layer

    @staticmethod
    def createMemoryLayer(layerName):
        # Check if layer is already loaded
        layer = DelineationController.getLayerByName (layerName)
        if layer is None:
            layerPath = DelineationController._getLineVectorPath()
            layer = QgsVectorLayer(path = layerPath, baseName = layerName, providerLib = "memory")
        return layer        

    # Get layer extent
    @staticmethod
    def getExtent(layer):
        extent = layer.extent()
        xmin = extent.xMinimum()
        xmax = extent.xMaximum()
        ymin = extent.yMinimum()
        ymax = extent.yMaximum()
        return "%f,%f,%f,%f" % (xmin, xmax, ymin, ymax)

    # Create nodes where two or more input lines intersect
    @staticmethod
    def extractVertices(layer):
        DelineationController.removeLayer(DelineationController.getNodeLayer(False))
        
        try:
            DelineationController.showBusyCursor()
            #processing.runAndLoadResults('qgis:extractspecificvertices',
            processing.runAndLoadResults('qgis:extractvertices',
                                         {"INPUT": layer,
                                          #"VERTICES": '0',
                                          "OUTPUT": 'memory:nodes'})
        finally:
            DelineationController.hideBusyCursor()
            
        nodeLayer = DelineationController.checkVectorLayer("Vertices", None, False)
        DelineationController.addLayerToMap(nodeLayer, DelineationController.nodeLayerName, 255, 0, 0, 1.3)

    @staticmethod
    def _xy2str(point):
        return "{0}/{1}".format(int(point.x()*100), int(point.y()*100))

    ### Step II ###
    @staticmethod
    def connectNodes():
        lineLayer = DelineationController.getLineLayer() 
        nodeLayer = DelineationController.getNodeLayer()
        if lineLayer is not None and nodeLayer is not None:
            # Check if user has selected 2 or more nodes
            if nodeLayer.selectedFeatureCount() > 1:
                try:
                    DelineationController.showBusyCursor()
                    
                    # Save selected nodes in new layer
                    nodesLayerFilename = QgsProcessingUtils.generateTempFilename('nodeLayer.shp')
                    processing.run('native:saveselectedfeatures',
                                      {"INPUT": nodeLayer,
                                       "OUTPUT": nodesLayerFilename})

                    # Create output file names
                    networkLayerFilename = QgsProcessingUtils.generateTempFilename('networkLayer.shp')
                    # Steiner least-cost path calculation
                    processing.run('grass7:v.net.steiner',
                                     {"input": lineLayer,
                                      "points": nodesLayerFilename,
                                      "threshold": 50,
                                      "arc_type": [0, 1],
                                      "terminal_cats": '1-100000',
                                      "acolumn": DelineationController.boundaryColumnName,
                                      "npoints": -1,
                                      "-g": False,
                                      "GRASS_REGION_PARAMETER": DelineationController.getExtent(lineLayer),
                                      "GRASS_OUTPUT_TYPE_PARAMETER": 0,
                                      "GRASS_SNAP_TOLERANCE_PARAMETER": -1,
                                      "GRASS_MIN_AREA_PARAMETER": 0.0001,
                                      "GRASS_VECTOR_DSCO": '',
                                      "GRASS_VECTOR_LCO": '',
                                      "output": networkLayerFilename})

                    # Check if nodes could be connected
                    tempLayer = QgsVectorLayer(networkLayerFilename, "Network Steiner", 'ogr')
                    if tempLayer is not None:
                        if tempLayer.featureCount() <= 0:
                            DelineationController.showMessage("Could not connect these nodes to boundaries! Please "
                                                              "select nodes that are connected via %s."
                                                              %DelineationController.lineLayerName,
                                                              Qgis.Warning)
                        else:
                            DelineationController.checkVectorLayer(DelineationController.candidateBoundaryLayerName,
                                                                    networkLayerFilename, False)
                            candidateBoundaryLayer = DelineationController.getActiveLayer()
                            candidateBoundaryLayer.setName(DelineationController.candidateBoundaryLayerName)
                            DelineationController.updateSymbology(candidateBoundaryLayer, 255, 0, 0, 0.3)
                            return True

                except Exception as exc:
                    DelineationController.showMessage("Error in running Steiner algorithm: {0}".format(exc),
                                                      Qgis.Critical)
                finally:
                    DelineationController.hideBusyCursor()
            else:
                DelineationController.showMessage("Please select two or more nodes to be connected from %s"% DelineationController.nodeLayerName,  
                                                  Qgis.Warning)
        return False

    # Restore canvas view to its initial state
    @staticmethod
    def initialview():
        layer = DelineationController.getCandidatesLayer(create = False, showError = False)
        if layer is not None:
            # Remove candidateBoundaryLayer
            DelineationController.removeLayer(layer)
            # Enable feature selection
            DelineationController.setActiveLayer(DelineationController.nodeLayerName)
            iface.actionSelect().trigger()

    # Candidate boundary should be accepted
    @staticmethod
    def acceptCandidate():
        candidates = DelineationController.getCandidatesLayer(create = False, showError = True)
        if candidates is not None and candidates.featureCount() > 0:
            tempLayer = None
            # Merge layer geometries into multipart geometry
            try:
                DelineationController.showBusyCursor()
                result = processing.run('native:dissolve',
                                        {"INPUT": candidates,
                                         "FIELD": [],
                                         "OUTPUT": 'memory:collect'})
                tempLayer = result['OUTPUT']
            finally:
                DelineationController.hideBusyCursor()

            if isinstance(tempLayer, QgsMapLayer):
                finalLayer = DelineationController.getFinalBoundaryLayer(create = True, showError = True)  
                # Add features to existing shapefile
                if DelineationController.copyFeatures(tempLayer, finalLayer):
                    finalLayer.triggerRepaint()
                    candidates.startEditing()
                    if candidates.isEditable():
                        candidates.selectAll()
                        candidates.deleteSelectedFeatures()
                        candidates.commitChanges()
                        candidates.triggerRepaint()
                        QApplication.processEvents()
                        DelineationController.initialview()
                    return True
        return False

    # Candidate boundary should be edited
    
    @staticmethod
    def editCandidate():
        layer = DelineationController.getCandidatesLayer(create = False, showError = True)
        return DelineationController._setLayerEditable(layer, True)

    # Candidate boundary should be deleted
    @staticmethod
    def deleteCandidate():
        DelineationController.initialview()

    # Manually delineated lines should be added
    @staticmethod
    def manualDelineation():
        layer = DelineationController.getFinalBoundaryLayer(create = True, showError = True)
        return DelineationController._setLayerEditable(layer, True)

    # Boundary delineation is finished
    @staticmethod
    def finishDelineation():
        layer = DelineationController.getFinalBoundaryLayer(create = False, showError = True)
        if layer is not None:
            # Stop editing and save changes
            layer.commitChanges()
            # Change layer visibility
            DelineationController.setLayerVisibility(layer, True)
            DelineationController.removeLayer(DelineationController.getNodeLayer(False))
            DelineationController.removeLayer(DelineationController.getLineLayer(False))
            # Zoom to full extent
            iface.actionZoomFullExtent().trigger()
            

