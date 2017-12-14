# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BoundaryDelineation
                                 A QGIS plugin
 BoundaryDelineation
                              -------------------
        begin                : 2017-03-27
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
# Import PyQt4 modules
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QColor

# Import qgis modules
from qgis.core import *
from qgis.utils import *
from qgis.gui import *
import qgis
import processing

# Import os modules
import os

# Initialize Qt resources from file resources.py
import resources

# Import the code for the dialog
from BoundaryDelineation_dialog import BoundaryDelineationDialog

### QGIS Plugin Implementation ###
class BoundaryDelineation:
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'BoundaryDelineation_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&BoundaryDelineation')
        self.toolbar = self.iface.addToolBar(u'BoundaryDelineation')
        self.toolbar.setObjectName(u'BoundaryDelineation')

        # Create the dialog and keep reference, dlg holds all the dialog elements
        self.dlg = BoundaryDelineationDialog(self.run)

        # Define dialog functions
        self.dlg.pB_Input_1.clicked.connect(self.selectInput_1)
        self.dlg.pB_Input_2.clicked.connect(self.selectInput_2)
        self.dlg.pB_Input_4.clicked.connect(self.selectInput_4)
        self.dlg.pushButton_9.clicked.connect(self.ProcessData)
        self.dlg.pushButton_2.clicked.connect(self.SteinerConnect)
        self.dlg.pushButton_3.clicked.connect(self.AcceptLine)
        self.dlg.pushButton_4.clicked.connect(self.SimplifyLine)
        self.dlg.pushButton_5.clicked.connect(self.EditLine)
        self.dlg.pushButton_6.clicked.connect(self.DeleteLine)
        self.dlg.pushButton_8.clicked.connect(self.FinishDelineation)
        self.dlg.pushButton_7.clicked.connect(self.ManualDelineation)

        # Get text field objects from GUI
        global txtFeedback
        txtFeedback = self.dlg.txtFeedback

        global txtFeedback_2
        txtFeedback_2 = self.dlg.txtFeedback_2

    # Get the translation for a string using Qt translation API
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('BoundaryDelineation', message)

    # Add a toolbar icon to the toolbar
    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    # Create the menu entries and toolbar icons inside the QGIS GUI
    def initGui(self):
        icon_path = ':/plugins/BoundaryDelineation/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Cadastral boundary delineation'),
            callback=self.run,
            parent=self.iface.mainWindow())

    # Write message to log window for degbugging
    def log(self, message, tab='BoundaryDelineation'):
        if self.do_log:
            QgsMessageLog.logMessage(str(message), tab, QgsMessageLog.INFO)

    # Wirte message to log
    # self.log(SLIC)

    # Removes the plugin menu item and icon from QGIS GUI
    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&BoundaryDelineation'),
                action)
            self.iface.removeToolBarIcon(action)

        # remove the toolbar
        del self.toolbar

    ### STEP I ###
    # Define button actions for Step I
    def selectInput_1(self):
        self.Input_1 = QFileDialog.getOpenFileName(self.dlg, 'Open File', '', '*.tif')
        self.dlg.lineEdit_Input_1.setText(self.Input_1)

    def selectInput_2(self):
        self.Input_2 = QFileDialog.getOpenFileName(self.dlg, 'Open File', '', '*.shp')
        self.dlg.lineEdit_Input_2.setText(self.Input_2)

    def selectInput_4(self):
        self.outputFile = QFileDialog.getSaveFileName(self.dlg, 'Save File as', '', '*.shp')
        self.dlg.lineEdit_Input_4.setText(self.outputFile)

    # Define main button action for Step I
    def run(self):

        # Show the plugin window and ensure that it stays the top level window
        self.dlg.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.dlg.show()

        # Clear text field
        txtFeedback.clear()

        # Initialize counter
        count = 0

        # Read lineEdit inputs
        global LayerInput_1
        LayerInput_1 = self.dlg.lineEdit_Input_1.text()
        global LayerInput_2
        LayerInput_2 = self.dlg.lineEdit_Input_2.text()
        global LayerInput_4
        LayerInput_4 = self.dlg.lineEdit_Input_4.text()

        # Run the dialog event loop
        result = self.dlg.exec_()

        # Load data according to input files provided by user
        if result:
            # Load UAV orthoimage
            if LayerInput_1 and not QgsMapLayerRegistry.instance().mapLayersByName('Input orthoimage'):
                # Load layer
                rlayer = iface.addRasterLayer(LayerInput_1, 'Input orthoimage')

                # Inform user
                if rlayer.isValid():
                    txtFeedback.append(">+> Input orthoimage: Successfully loaded\n")
                    count += 1
                else:
                    txtFeedback.append(">!> Input orthoimage: Could not open %s\n" % LayerInput_1)

            # Load line shapefile
            if LayerInput_2:
                # Load layer
                global network_layer
                network_layer = QgsVectorLayer(LayerInput_2, "network_layer", "ogr")
                if not network_layer.isValid():
                    txtFeedback.append(">!> Input network: Could not open %s\n" % LayerInput_2)
                else:
                    txtFeedback.append(">+> Input network: Successfully loaded\n")
                count += 1

            # Define output shapefile
            if LayerInput_4:
                txtFeedback.append(">+> Output boundaries: Successfully defined output file. All processing files "
                                   "will be saved to the directory of the output file\n")
                count += 1

            # Check if all fields are filled
            if count == 3:
                # Get map canvas
                global canvas
                canvas = qgis.utils.iface.mapCanvas()

                # Set canvas extent to the extent of raster layer
                canvas.setExtent(rlayer.extent())

                # Zoom to full extent
                qgis.utils.iface.zoomFull()

                # Inform the user
                txtFeedback.append(">+> Successfully loaded all data. Please click 'Process Data' to create nodes "
                                   "before proceeding to Step II\n")

    ####################################################################################################################
    # Process Data: Create network and nodes layer from lines layer
    def ProcessData(self):
        # Check if line layer exists
        if not network_layer.isValid():
            txtFeedback.append(">!>'Input lines' layer does not exist. Please select a valid path to an input line "
                               "layer and load it\n")

        if network_layer.isValid():
            # Clear text field
            txtFeedback.clear()

            # Inform the user
            txtFeedback.append(">>> Nodes will now be created from line layer...\n")

            # Refresh dialog with text field
            self.dlg.repaint()

            # Define extent
            extent = network_layer.extent()
            xmin = extent.xMinimum()
            xmax = extent.xMaximum()
            ymin = extent.yMinimum()
            ymax = extent.yMaximum()

            # Create nodes
            nodes = LayerInput_4.rpartition('/')[0] + '/processingFile1_nodes.shp'
            if not os.path.isfile(nodes):
                processing.runalg('grass7:v.net.nodes',
                                  {"input": network_layer,
                                   "GRASS_REGION_PARAMETER": "%f,%f,%f,%f" % (xmin, xmax, ymin, ymax),
                                   "GRASS_OUTPUT_TYPE_PARAMETER": 0,
                                   "output": nodes})
            self.dlg.progressBar.setValue(50)
            QApplication.processEvents()

            # Load nodes file to canvas
            if os.path.isfile(nodes):
                global nodes_layer
                nodes_layer = iface.addVectorLayer(nodes, 'Input nodes', 'ogr')
                nodes_layer.setLayerName('Input nodes')
                # Make nodes layer active layer
                iface.setActiveLayer(nodes_layer)

                if not nodes_layer.isValid():
                    txtFeedback.append(">!> Input nodes: Could not open %s\n" % nodes)

                else:
                    # Change symbology of layer
                    symbols = iface.activeLayer().rendererV2().symbols()
                    symbol = symbols[0]
                    symbol.setColor(QColor.fromRgb(255, 0, 0))
                    symbol.setSize(1.3)
                    symbol.setAlpha(0.95)
                    qgis.utils.iface.mapCanvas().refresh()
                    qgis.utils.iface.legendInterface().refreshLayerSymbology(iface.activeLayer())
                    self.dlg.progressBar.setValue(80)
                    txtFeedback.append(">+> Input nodes: Successfully loaded\n")

                    # Inform the user
                    self.dlg.progressBar.setValue(100)
                    QApplication.processEvents()
                    txtFeedback.append(">+> Successfully finished Step I. To proceed, click on Step II")

    ####################################################################################################################
    ### STEP II ###
    # Connect Nodes: Connects nodes based on shortest path (steiner network method)
    def SteinerConnect(self):
        # Clear text field
        txtFeedback_2.clear()

        # Define extent according to selected nodes
        extent = nodes_layer.boundingBoxOfSelected()
        xmin = extent.xMinimum() - 20
        xmax = extent.xMaximum() + 20
        ymin = extent.yMinimum() - 20
        ymax = extent.yMaximum() + 20

        # Create new layer to clip layer to extent
        # Note: Done to to decrease processing time of further processing.
        # v.net.steiner makes QGIS crash if the entire nodes layer is considered since too much memory space is
        # allocated
        extentLayer = QgsVectorLayer("Polygon?crs=EPSG:32632&field=ID:integer", "extentLayer", "memory")
        extentLayer.setCrs(network_layer.crs())
        provider = extentLayer.dataProvider()

        # Add a feature
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPolygon(
            [[QgsPoint(xmin, ymin), QgsPoint(xmin, ymax), QgsPoint(xmax, ymax), QgsPoint(xmax, ymin)]]))
        feat.setAttributes([1])
        provider.addFeatures([feat])

        # Add memory layer to registry
        QgsMapLayerRegistry.instance().addMapLayer(extentLayer)

        # Initialize and increment counter for name of processing file
        try:
            i
        except NameError:
            global i
            i = 0
        else:
            i += 1

        # Clip layer to extent
        networkClip = LayerInput_4.rpartition('/')[0] + '/processingFile7a' + str(i) + '_steiner_network.shp'

        # Check if processing files already exist and stop processing if yes
        if os.path.isfile(networkClip):
            txtFeedback_2.append(">!> Error: You are about to overwrite existing processing files. Please remove all "
                                 "processingFiles with a number > 6 in the filename in the directory you provided "
                                 "for the output boundaries and reclick on 'Connect Nodes'.\n")

            # Remove memory layer from registry
            QgsMapLayerRegistry.instance().removeMapLayer(extentLayer.id())

        else:
            processing.runalg('qgis:clip', {"INPUT": network_layer,
                                            "OVERLAY": extentLayer,
                                            "OUTPUT": networkClip})

            # Remove memory layer from registry
            QgsMapLayerRegistry.instance().removeMapLayer(extentLayer.id())

            # Clip raster layer by extent of selected features
            #       Note: Instead of creating a layer around the selected features and clipping the network layer with the
            #       created layer, it would be shorter to do this with the gdal module, which does not work (memory layers
            #       cannot be used as input for GDAL/OGR processing scripts because Processing fails to properly prepare
            #       the data for use with ogr2ogr.)
            #       processing.runalg('gdalogr:clipvectorsbyextent',
            #                   {"INPUT_LAYER": network,
            #                    "CLIP_EXTENT": "%f,%f,%f,%f" % (xmin, xmax, ymin, ymax),
            #                   "OUTPUT_LAYER":clip_layer})
            #       Even shorter would be to set the extent around the selected features directly in the
            #       v.net.steiner function for "GRASS_REGION_PARAMETER", which doesn't work (#unsolved)

            # Define output file
            steinerLine = LayerInput_4.rpartition('/')[0] + '/processingFile7b' + str(i) + '_steiner_network.shp'

            # Check if several nodes are selected and both are points
            if nodes_layer.selectedFeatureCount() > 1 and nodes_layer.geometryType() == 0:

                # Inform the user
                txtFeedback_2.append(">>> Successfully selected nodes that will now be connected...\n")

                # Refresh dialog with text field
                self.dlg.repaint()

                # Connect selected nodes with steiner network (#unsolved: better would a network module where each
                # line segment can only be used once)
                networkClipLayer = QgsVectorLayer(networkClip, 'networkClip', 'ogr')
                processing.runalg('grass7:v.net.steiner',
                                  {"input": networkClipLayer,
                                   "points": nodes_layer,
                                   "acolumn": 'proba_bo',
                                   "GRASS_REGION_PARAMETER": "%f,%f,%f,%f" % (xmin, xmax, ymin, ymax),
                                   "GRASS_OUTPUT_TYPE_PARAMETER": 0,
                                   "output": steinerLine})

                # # Connect selected nodes with traveling salesman network -> does not work, as salesman has to return
                # # to start point, however, one line is not passed twice
                # networkClipLayer = QgsVectorLayer(networkClip, 'networkClip', 'ogr')
                # processing.runalg('grass7:v.net.salesman',
                #                   {"input": networkClipLayer,
                #                    "points": nodes_layer,
                #                    "arc_column": 'proba_bo',
                #                    "arc_backward_column": 'back',
                #                    "GRASS_REGION_PARAMETER": "%f,%f,%f,%f" % (xmin, xmax, ymin, ymax),
                #                    "GRASS_OUTPUT_TYPE_PARAMETER": 2,
                #                    "output": steinerLine})

                # Clear text field
                txtFeedback_2.clear()
                txtFeedback_2.append(">+> Successfully connected nodes\n")

                # Check if output layer was correctly created:
                steinerLineLayer = QgsVectorLayer(steinerLine, 'steiner_layer', 'ogr')
                if steinerLineLayer.isValid():
                    # Smooth output layer
                    smoothSteinerLine = LayerInput_4.rpartition('/')[0] + '/processingFile7c' + str(i) + \
                                        '_steiner_network.shp'
                    # Based on Chaikin algorithm
                    processing.runalg('qgis:smoothgeometry',
                                      {"INPUT_LAYER": steinerLine,
                                       "ITERATIONS": 1,
                                       "OFFSET": 0.5,
                                       "OUTPUT_LAYER": smoothSteinerLine})

                    # Based on snakes method (alternative algorithm with similar result)
                    # processing.runalg('grass7:v.generalize.smooth',
                    #                   {"input": steinerLine,
                    #                    "method": 5,
                    #                    "threshold": 1,
                    #                    "GRASS_REGION_PARAMETER": "%f,%f,%f,%f" % (xmin, xmax, ymin, ymax),
                    #                    "GRASS_OUTPUT_TYPE_PARAMETER": 0,
                    #                    "output": smoothSteinerLine})

                    # Merge resulting line to one segment
                    smoothSteinerLineLayer = QgsVectorLayer(smoothSteinerLine, 'smoothSteinerLineLayer', 'ogr')
                    smoothSteinerLineLayer.startEditing()
                    provider = smoothSteinerLineLayer.dataProvider()
                    provider.addAttributes([QgsField("FID", QVariant.Int)])
                    provider.deleteAttributes([0])
                    smoothSteinerLineLayer.commitChanges()

                    # Check if there is the need to merge features
                    if smoothSteinerLineLayer.selectedFeatureCount() > 1:
                        multipartSteiner = LayerInput_4.rpartition('/')[0] + '/processingFile7d' + str(i) + \
                                           '_steiner_network_merged.shp'
                        processing.runalg('qgis:singlepartstomultipart',
                                          {"INPUT": smoothSteinerLine,
                                           "FIELD": "FID",
                                           "OUTPUT": multipartSteiner})
                    else:
                        multipartSteiner = smoothSteinerLine
                    # Calculate sinuosity to indicate usability of created line
                    # Note: Sinuosity measures to what extent a line between two points varies from their directest
                    # connection (range [0; 1]). It expresses the ratio between the euclidean distance between two
                    # points and the length of the line connecting the two points.
                    # To assess the line usability the following traffic light evaluation system is applied:
                    # [0 - 0.30]    -> red
                    # [0.31 -0.66]  -> yellow
                    # [0.67 - 1]    -> green

                    sinuositySteinerLine = LayerInput_4.rpartition('/')[0] + '/processingFile7e' + str(i) + \
                                           '_steiner_sinuosity.shp'
                    processing.runalg('qgis:fieldcalculator',
                                      {"INPUT_LAYER": multipartSteiner,
                                       "FIELD_NAME": "sinuosity",
                                       "FIELD_TYPE": 0,
                                       "FORMULA": 'distance( '
                                                  'make_point( $x_at(0), $y_at(0)),'
                                                  'make_point( $x_at( num_points($geometry)-1), $y_at( num_points('
                                                  '$geometry)-1)))/ $length ',
                                       "NEW_FIELD": True, "OUTPUT_LAYER": sinuositySteinerLine})

                    # Display result according to sinuosity
                    sinuosityLineLayer = QgsVectorLayer(sinuositySteinerLine, 'sinuosity_layer', 'ogr')

                    # Open attribute table of layer
                    sinuosity_list = sinuosityLineLayer.getValues('sinuosity')
                    sinuosity = float(sinuosity_list[0][0])

                    # Add current boundary layer to canvas
                    layer_display = iface.addVectorLayer(sinuositySteinerLine, 'Current boundary', 'ogr')
                    layer_display.setLayerName('Current boundary')

                    # Change display settings to display nodes only
                    iface.legendInterface().setLayerVisible(nodes_layer, False)

                    # Zoom to extent of current boundary layer
                    canvas = qgis.utils.iface.mapCanvas()
                    canvas.setExtent(extent)

                    if sinuosity <= 0.3:
                        # Change symbology of current boundary layer
                        layer = iface.activeLayer()
                        symbols = layer.rendererV2().symbols()
                        symbol = symbols[0]
                        symbol.setColor(QColor.fromRgb(255, 0, 0))
                        symbol.setWidth(0.75)
                        qgis.utils.iface.mapCanvas().refresh()
                        qgis.utils.iface.legendInterface().refreshLayerSymbology(layer)

                        # Inform the user
                        txtFeedback_2.append(
                            ">>> The sinuosity (%.1f) of the line indicates that this line requires further "
                            "consideration. Would you like to accept, simplify, edit or delete the displayed "
                            "boundary line?" % sinuosity)

                    if 0.3 < sinuosity <= 0.6:
                        # Change symbology of current boundary layer
                        layer = iface.activeLayer()
                        symbols = layer.rendererV2().symbols()
                        symbol = symbols[0]
                        symbol.setColor(QColor.fromRgb(255, 255, 0))
                        symbol.setWidth(0.75)
                        qgis.utils.iface.mapCanvas().refresh()
                        qgis.utils.iface.legendInterface().refreshLayerSymbology(layer)

                        # Inform the user
                        txtFeedback_2.append(">>> The sinuosity (%.1f) of the line indicates that this line might "
                                             "require further consideration. Would you like to accept, simplify, "
                                             "edit or delete the displayed "
                            "boundary line?" % sinuosity)

                    if sinuosity > 0.6:
                        # Change symbology of current boundary layer
                        layer = iface.activeLayer()
                        symbols = layer.rendererV2().symbols()
                        symbol = symbols[0]
                        symbol.setColor(QColor.fromRgb(0, 255, 0))
                        symbol.setWidth(0.75)
                        qgis.utils.iface.mapCanvas().refresh()
                        qgis.utils.iface.legendInterface().refreshLayerSymbology(layer)

                        # Inform the user
                        txtFeedback_2.append(
                            "The sinuosity (%.1f) of the line indicates that this line does not require "
                            "further consideration. Would you like to accept, simplify, edit or delete the displayed "
                            "boundary line?" % sinuosity)

                else:
                    # Clear text field
                    txtFeedback_2.clear()

                    # Inform the user
                    txtFeedback_2.append(
                        ">!> Selected nodes could not be connected. Please select nodes that are connected via the "
                        "'Input network' layer.\n")
            else:
                txtFeedback_2.append(">>> Please select nodes from 'Input nodes'")

    ####################################################################################################################
    # Accept Line: Save line in current layer to output boundary file
    def AcceptLine(self):

        # Function that merges all line parts of current boundary layer to one feature
        def SingleToMulipart(layer):

            # Check if there is a need to merge multiple features
            if layer.featureCount() > 1:
                # Set cat value of all line segments to 1
                layer.startEditing()
                features = processing.features(layer)
                for feat in features:
                    fid = int(feat.id())
                    layer.changeAttributeValue(fid, 0, 1)
                layer.commitChanges()

                # Define output file
                currBoundary_out = LayerInput_4.rpartition('/')[0] + '/processingFile8_boundaryMultipart.shp'

                # Run feature merging
                processing.runalg('qgis:singlepartstomultipart',
                                  {"INPUT": layer,
                                   "FIELD": "FID",
                                   "OUTPUT": currBoundary_out})

                # Load output as vector layer
                multipart = QgsVectorLayer(currBoundary_out, 'currLayer', 'ogr')

                # Return output
                return multipart

            # If layer contains one feature only, the layer is not changed and returned as it is
            else:
                return layer

        # Function to display result
        def display(self):
            txtFeedback_2.append(
                ">+> Successfully saved the current boundary in %s\n" % (LayerInput_4.rpartition('/')[-1]))
            txtFeedback_2.append(
                ">>> Please select new nodes and click on 'Connect nodes' to create a 'Current boundary' layer. If "
                "you don't want to add more boundary lines to %s click on 'Finish Delineation'.\n"
                % (LayerInput_4.rpartition('/')[-1]))

            # Clear text field
            txtFeedback_2.clear()

            # Change display setting to display nodes only
            iface.legendInterface().setLayerVisible(nodes_layer, True)

            # Remove all layers named 'Previous boundary'. Since 'Simplify can be pressed multiple times,
            # there can be multiple of these layers.
            for i in range(0, len(QgsMapLayerRegistry.instance().mapLayersByName('Previous boundary'))):
                layer = QgsMapLayerRegistry.instance().mapLayersByName('Previous boundary')[0]
                QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

            # Remove current boundary layer
            QgsMapLayerRegistry.instance().removeMapLayer(boundaryLayer.id())

            if not QgsMapLayerRegistry.instance().mapLayersByName('Final boundaries'):
                # Add final boundary layer
                layer_display = iface.addVectorLayer(LayerInput_4, 'Final boundaries', 'ogr')
                layer_display.setLayerName('Final boundaries')

                # Change layer symbology
                symbols = iface.activeLayer().rendererV2().symbols()
                symbol = symbols[0]
                symbol.setColor(QColor.fromRgb(0, 225, 0))
                symbol.setWidth(0.75)
                qgis.utils.iface.mapCanvas().refresh()
                qgis.utils.iface.legendInterface().refreshLayerSymbology(iface.activeLayer())

                # Change layer visibility
                finalBoundaries = QgsMapLayerRegistry.instance().mapLayersByName('Final boundaries')[0]
                iface.legendInterface().setLayerVisible(finalBoundaries, False)

            # Make nodes layer active layer
            if QgsMapLayerRegistry.instance().mapLayersByName('Input nodes'):
                nodesLayer = QgsMapLayerRegistry.instance().mapLayersByName('Input nodes')[0]
                iface.setActiveLayer(nodesLayer)

            return 0

        ################################################################################################################
        # Main AcceptLine function body
        # Clear text fields
        txtFeedback_2.clear()

        # Remove simplified lines
        if QgsMapLayerRegistry.instance().mapLayersByName('Previous boundary'):
            layer = QgsMapLayerRegistry.instance().mapLayersByName('Previous boundary')[0]
            QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

        # Check if current boundary layer exists
        if not QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):
            txtFeedback_2.append(">!> 'Current boundary' layer does not exist. Please select new nodes and click on "
                                 "'Connect nodes' to create a 'Current boundary' layer.")

        if QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):
            boundaryLayer = QgsMapLayerRegistry.instance().mapLayersByName('Current boundary')[0]

            # Unload final boundary file in case it is already displayed, since it will be edited
            if QgsMapLayerRegistry.instance().mapLayersByName('Final boundaries'):
                finalBoundaries = QgsMapLayerRegistry.instance().mapLayersByName('Final boundaries')[0]
                iface.legendInterface().setLayerVisible(finalBoundaries, False)

            # Check if output layer already exists
            if os.path.isfile(LayerInput_4):
                # Converts line parts of current boundary layer to one feature
                layer = SingleToMulipart(boundaryLayer)

                # Open saved boundary layer
                finalBoundaryLayer = QgsVectorLayer(LayerInput_4, 'LayerInput_4', 'ogr')

                # Add current feature to existing file
                finalBoundaryLayer.startEditing()
                features = processing.features(layer)
                for feat in features:
                    finalBoundaryLayer.addFeature(feat)
                finalBoundaryLayer.commitChanges()

                # Reset display
                display(self)

            # Create new output boundary file if it is not created yet
            if not os.path.isfile(LayerInput_4):
                # Check if current boundary layer exists
                if QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):

                    # Get boundary layer
                    layer = SingleToMulipart(boundaryLayer)

                    # Write boundary layer to output file
                    provider = layer.dataProvider()
                    writer = QgsVectorFileWriter(LayerInput_4, provider.encoding(), provider.fields(),
                                                 QGis.WKBLineString, provider.crs())

                    # Write features to output file
                    features = processing.features(layer)
                    for feat in features:
                        writer.addFeature(feat)

                if not QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):
                    txtFeedback_2.append(
                        ">!> 'Current boundary' layer does not exist. Please select new nodes and click on "
                        "'Connect nodes' to create a 'Current boundary' layer.")
                # Reset display
                display(self)

    ####################################################################################################################
    # Delete Line: Delete line of current boundary layer
    def DeleteLine(self):

        # Clear text fields
        txtFeedback_2.clear()

        # Remove simplified lines
        if QgsMapLayerRegistry.instance().mapLayersByName('Previous boundary'):
            layer = QgsMapLayerRegistry.instance().mapLayersByName('Previous boundary')[0]
            QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

        if not QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):
            txtFeedback_2.append(">!> 'Current boundary' layer does not exist. Please select new nodes and click on "
                                 "'Connect nodes' to create a 'Current boundary' layer.")

        # Check if current boundary layer exists
        if QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):
            boundaryLayer = QgsMapLayerRegistry.instance().mapLayersByName('Current boundary')[0]

            # Remove current boundary layer
            QgsMapLayerRegistry.instance().removeMapLayer(boundaryLayer.id())

            # Change display setting to display nodes only
            iface.legendInterface().setLayerVisible(nodes_layer, True)

            txtFeedback_2.append(">!> 'Current boundary' layer has been deleted. Please select new nodes and click on "
                                 "'Connect nodes' to create a 'Current boundary' layer.")

        # Make nodes layer active layer
        if QgsMapLayerRegistry.instance().mapLayersByName('Input nodes'):
            nodesLayer = QgsMapLayerRegistry.instance().mapLayersByName('Input nodes')[0]
            iface.setActiveLayer(nodesLayer)
    ####################################################################################################################
    # Simplify Line: Simplify line of current boundary layer (Douglas-Peucker)
    def SimplifyLine(self):

        # Function that compares to layers and informs the user if they are equal (line cannot be further simplified)
        def CompareLayers(layer1, layer2):
            # Get features of two layers
            features1 = layer1.getFeatures()
            features2 = layer2.getFeatures()

            # Create lists to store features in
            feat1 = []
            feat2 = []

            # Store features of both layers in lists
            for feat in features1:
                geom = feat.geometry()
                feat1.append(geom.length())

            for feat in features2:
                geom = feat.geometry()
                feat2.append(geom.length())

            # Initialize iterator
            k = 0
            m = 0

            # Loop over lists and check if features are the same
            while m < len(feat1):
                if feat1[m] == feat2[m]:
                    k += 1
                    m += 1
                    if k == len(feat1):
                        txtFeedback_2.clear()
                        txtFeedback_2.append(
                            "The line cannot be simplified more. Please edit the line if further changes are needed.\n")
                        return 0
                else:
                    # Inform the user
                    txtFeedback_2.append(">+> Successfully simplified boundary line.\n")
                    txtFeedback_2.append(
                        ">>> Would you like to accept, simplify, edit or delete the displayed boundary line?")
                    return 1

        ################################################################################################################
        # Main SimplifyLine function body
        # Clear text fields
        txtFeedback_2.clear()

        # Check if current boundary layer exists
        if not QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):
            txtFeedback_2.append(">!> 'Current boundary' layer does not exist. Please select new nodes and click on "
                                 "'Connect nodes' to create a 'Current boundary' layer.")

        if QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):

            # Define input file
            currBoundary_in = QgsMapLayerRegistry.instance().mapLayersByName('Current boundary')[0]

            # Initialize and increment counter for name of output file
            try:
                c
            except NameError:
                global c
                c = 0
            else:
                c += 1

            # Define output file
            currBoundary_out = LayerInput_4.rpartition('/')[0] + '/processingFile8_boundarySimplify' + str(c) + '.shp'
            # Check if processing files already exist and stop processing if yes.
            if os.path.isfile(currBoundary_out):
                txtFeedback_2.append(">!> You are about to overwrite existing processing files. Please remove all "
                                     "processingFiles with a number > 7 in the filename "
                                     "in the directory you provided for the output boundaries.\n")
            else:

                # Connect selected nodes with steiner network, Douglas-Peucker algorithm
                processing.runalg('qgis:simplifygeometries',
                                  {"INPUT": currBoundary_in,
                                   "TOLERANCE": 1,
                                   "OUTPUT": currBoundary_out})

                # (alternative algorithm with similar result)
                # # Define extent
                # extent = currBoundary_in.extent()
                # xmin = extent.xMinimum()
                # xmax = extent.xMaximum()
                # ymin = extent.yMinimum()
                # ymax = extent.yMaximum()

                # processing.runalg('grass7:v.generalize.simplify',
                #                   {"input": currBoundary_in,
                #                    "method": 0,
                #                    "threshold": 1,
                #                    "GRASS_REGION_PARAMETER": "%f,%f,%f,%f" % (xmin, xmax, ymin, ymax),
                #                    "GRASS_OUTPUT_TYPE_PARAMETER": 0,
                #                    "output": currBoundary_out})

                # Change name of previous boundary layer
                currBoundary_in.setLayerName('Previous boundary')

                # Change color of previous boundary layer
                symbols = iface.activeLayer().rendererV2().symbols()
                symbol = symbols[0]
                symbol.setColor(QColor.fromRgb(204, 0, 0))

                # Add new boundary layer to canvas
                layer_display = iface.addVectorLayer(currBoundary_out, 'Current boundary', 'ogr')
                layer_display.setLayerName('Current boundary')

                # Change symbology of current boundary layer
                layer = iface.activeLayer()
                symbols = layer.rendererV2().symbols()
                symbol = symbols[0]
                symbol.setColor(QColor.fromRgb(0, 255, 0))
                symbol.setWidth(0.75)
                qgis.utils.iface.mapCanvas().refresh()
                qgis.utils.iface.legendInterface().refreshLayerSymbology(layer)

                # Change display setting to display current boundary only
                iface.legendInterface().setLayerVisible(currBoundary_in, False)

                # Check if current boundary is identical to previous boundary
                currBoundary_out = QgsMapLayerRegistry.instance().mapLayersByName('Current boundary')[0]
                CompareLayers(currBoundary_in, currBoundary_out)

    ###################################################################################################################
    # Edit Line: Change to manual editing mode
    def EditLine(self):
        # Clear text fields
        txtFeedback_2.clear()

        # Check if current boundary layer exists
        if QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):
            layer = QgsMapLayerRegistry.instance().mapLayersByName('Current boundary')[0]

            # Start editing session for current boundary layer
            layer.startEditing()

            # Inform the user
            txtFeedback_2.append(">>> Please edit 'Current boundary' and click on 'Accept Line' when finished. "
                                 "Instructions on editing in QGIS can be found in the help tab.")
        else:
            # Inform the user
            txtFeedback_2.append(">!> 'Current boundary' layer does not exist. Please select new nodes and click on "
                                 "'Connect nodes' to create a 'Current boundary' layer.")

    ###################################################################################################################
    # Finish Line Delineation: No more changes need to be made and teh final boundary file can be saved
    def FinishDelineation(self):

        # Show final boundary layer
        if QgsMapLayerRegistry.instance().mapLayersByName('Final boundaries'):
            finalBoundaries = QgsMapLayerRegistry.instance().mapLayersByName('Final boundaries')[0]
            iface.legendInterface().setLayerVisible(finalBoundaries, True)

            # Hide remaining layers layer
            if QgsMapLayerRegistry.instance().mapLayersByName('Input nodes'):
                iface.legendInterface().setLayerVisible \
                    (QgsMapLayerRegistry.instance().mapLayersByName('Input nodes')[0], False)

            # Zoom to full extent
            qgis.utils.iface.zoomFull()

            if len(LayerInput_4) > 1:
                # Delete all processing files
                # Note: This doesn't remove the files, since they are still used in QGIS.
                # Also removing them with QgsMapLayerRegistry.instance().removeMapLayer(extentLayer.id())
                # does not work. Unsure if this step should be done, because if the lines are needed again,
                # all processing needs to be redone(#unsolved)
                """
                inputDir = LayerInput_4.rpartition('/')[0]
                for file in os.listdir(inputDir):
                    if 'processingFile' in file:
                        filepath = inputDir + '/' + str(file)
                        try:
                            os.remove(filepath)
                        except OSError:
                            pass
                """
                # Clear text fields
                txtFeedback_2.clear()

                # Inform the user
                txtFeedback_2.append(
                    ">+> All final boundaries are displayed and saved in %s\n" % (LayerInput_4.rpartition('/')[-1]))
                txtFeedback_2.append(
                    ">>> To manually add further lines, click 'Manual Delineation'. Click 'Close' to terminate the "
                    "delineation process.\n")
        else:
            # Clear text fields
            txtFeedback_2.clear()

            # Inform the user
            txtFeedback_2.append(">!> 'Current boundary' layer does not exist. Please select new nodes and click on "
                                 "'Connect nodes' to create a 'Current boundary' layer.")

            # Refresh dialog with text field
            self.dlg.repaint()

    ###################################################################################################################
    # Finish Line Delineation: No more changes need to be made and the final boundary file can be saved
    def ManualDelineation(self):

        # Show final boundary layer
        if QgsMapLayerRegistry.instance().mapLayersByName('Final boundaries'):
            finalBoundaries = QgsMapLayerRegistry.instance().mapLayersByName('Final boundaries')[0]
            iface.legendInterface().setLayerVisible(finalBoundaries, True)

            # Start editing final boundary layer
            finalBoundaries.startEditing()

            # Hide remaining layer
            if QgsMapLayerRegistry.instance().mapLayersByName('Input nodes'):
                iface.legendInterface().setLayerVisible \
                    (QgsMapLayerRegistry.instance().mapLayersByName('Input nodes')[0], False)

            # Zoom to full extent
            qgis.utils.iface.zoomFull()

            # Clear text fields
            txtFeedback_2.clear()

            # Inform the user
            txtFeedback_2.append(
                ">>> Final boundary layer is now editable. Please add features (click add feature in QGIS Digitizing "
                "Toolbar) and save these in the same "
                "toolbar.\n")

        else:

            # Clear text fields
            txtFeedback_2.clear()

            # Inform the user
            txtFeedback_2.append(">!> 'Current boundary' layer does not exist. Please select new nodes and click on "
                                 "'Connect nodes' to create a 'Current boundary' layer.")

            # Refresh dialog with text field
            self.dlg.repaint()


"""
/***************************************************************************
### Code Snippets ###
# Get current layer from canvas
currLayer = canvas.currentLayer()

# refresh map canvas to see the result
iface.mapCanvas().refresh()
self.iface.mapCanvas().layers()  

# Get processing help in QGIS python console
# processing.alghelp("grass7:v.clean")


### Create new vector layer
if result:
    # Do something useful here - delete the line containing pass and
    # substitute with your code.
    distance = self.dlg.distance_buf.value()
    new_distance = 0
    number = self.dlg.number_buf.value()
    layer = self.iface.activeLayer()
    selected = layer.selectedFeatures()
    crs = layer.crs()
    print layer.name()
    for i in range(0,number):
        new_distance += distance
        result = QgsVectorLayer("Polygon?crs=" + str(crs.authid()), "result_" + str(new_distance), "memory")
        new_features = []
        result_provider = result.dataProvider()
        for feature in selected:
            feature.setGeometry(feature.geometry().buffer(new_distance,20))
            new_features.append(feature)
        result_provider.addFeatures(new_features)
        QgsMapLayerRegistry.instance().addMapLayer(result)
    pass

### Change attributes of layer ###
# Open output file
boundaries.startEditing()
boundaryData = boundaries.dataProvider()

# Remove existing attributes
fields_to_delete = [fid for fid in range(len(boundaryData.fields()))]
boundaryData.deleteAttributes(fields_to_delete)
boundaries.updateFields()

# Create new attribute
boundaryData.addAttributes([QgsField("cat", QVariant.Int)])
boundaries.commitChanges()

# Write vector layer: not working
QgsVectorFileWriter(currLayer,"my_shapes.shp", "utf-8", None, "ESRI Shapefile")    

# Get layer ID:
gPb_ID = layer_2.id()
                    
# sinuosity_index = sinuosityLineLayer.fieldNameIndex('sinuosity')
# feature = sinuosityLineLayer.getFeatures()
# sinuosity = feature.attributes([sinuosity_index])


### Allow plugin window to be docked to QGIS console ###
# Create dockwidget
dock = QDockWidget()

# Add Qt dialog to dockwidget
dock.setWidget(self.dlg)

# Add dockwidget to main window, i.e., QGIS console
wnd = iface.mainWindow()
wnd.addDockWidget(Qt.TopDockWidgetArea, dock)

# Allow window to be moved between docks by user
# dock.DockWidgetMovable
# dock.AllDockWidgetFeatures
# dock.setAllowedAreas(Qt.AllDockWidgetAreas)
# dock.setWindowTitle("BoundaryDelination")
# dock.setFloating(True)
        
### Create log file for debugging ###
def write_log_message(message, tag, level):
    filename = cwd + r'\LogFile.log'
    with open(filename, 'w') as logfile:
        logfile.write('{tag}({level}): {message}'.format(tag=tag, level=level, message=message))
        
### Least-cost path with v.net.path ###
            # Define output file
            steinerLine = LayerInput_4.rpartition('/')[0] + '/processingFile7b' + str(i) + '_steiner_network.shp'

            # Check if several nodes are selected and both are points
            if nodes_layer.selectedFeatureCount() > 1 and nodes_layer.geometryType() == 0:

                # Inform the user
                txtFeedback_2.append(">>> Successfully selected nodes that will now be connected...\n")

                # Refresh dialog with text field
                self.dlg.repaint()

                # Save coordinates of selected nodes in txt file (required as input for grass7:v.net.path
                nodes_selected = LayerInput_4.rpartition('/')[0] + '/processingFile7b' + str(i) + \
                                        '_selected_nodes.txt'

                # Open txt file for writing
                txt_output = open(nodes_selected, 'w')

                # Iterate over all selected nodes and write ID, and x/y coordinates to txt file
                c = 0
                for feature in nodes_layer.selectedFeatures():
                    geom = feature.geometry()
                    # Each line should contain: id start_point_x start_point_y end_point_x end_point_y
                    # Each point needs to inserted as endpoint of current line and as startpoint of subsequent line
                    if c == 0:
                        x_start = geom.asPoint()[0]
                        y_start = geom.asPoint()[1]
                        c+=1
                    else:
                        x_end = geom.asPoint()[0]
                        y_end = geom.asPoint()[1]

                        x_next = geom.asPoint()[0]
                        y_next = geom.asPoint()[1]

                        line_output = str(c) + " " + str(x_start) + " " + str(y_start) + " " + str(x_end) + " " + str(
                            y_end) + "\n"
                        txt_output.write(line_output)

                        x_start = x_next
                        y_start = y_next

                        c+=1

                txt_output.close()

                # Connect selected nodes with least cost path (has nothing to with the Steiner approach)
                networkClipLayer = QgsVectorLayer(networkClip, 'networkClip', 'ogr')
                processing.runalg('grass7:v.net.path',
                                  {"input": networkClipLayer,
                                   "points": nodes_layer,
                                   "file": nodes_selected,
                                   "arc_column": 'proba_bo',
                                   "arc_backward_column": 'back',
                                   "GRASS_REGION_PARAMETER": "%f,%f,%f,%f" % (xmin, xmax, ymin, ymax),
                                   "GRASS_OUTPUT_TYPE_PARAMETER": 0,
                                   "output": steinerLine})
/***************************************************************************
"""
