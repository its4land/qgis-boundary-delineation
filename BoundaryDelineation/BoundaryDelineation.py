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
        self.dlg.pB_Input_3.clicked.connect(self.selectInput_3)
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

        global txtFeedback_3
        txtFeedback_3 = self.dlg.txtFeedback_3

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

    def selectInput_3(self):
        self.Input_3 = QFileDialog.getOpenFileName(self.dlg, 'Open File', '', '*.shp')
        self.dlg.lineEdit_Input_3.setText(self.Input_3)

    def selectInput_4(self):
        self.outputFile = QFileDialog.getSaveFileName(self.dlg, 'Save File as', '', '*.shp')
        self.dlg.lineEdit_Input_4.setText(self.outputFile)

    # Define main button action for Step I
    def run(self):

        # show the dialog
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
        global LayerInput_3
        LayerInput_3 = self.dlg.lineEdit_Input_3.text()
        global LayerInput_4
        LayerInput_4 = self.dlg.lineEdit_Input_4.text()

        # Run the dialog event loop
        result = self.dlg.exec_()

        # Load data according to input files provided by user
        if result:
            # Load UAV orthoimage
            if LayerInput_1:
                fileInfo = QFileInfo(LayerInput_1)
                baseName = fileInfo.baseName()
                rlayer = QgsRasterLayer(LayerInput_1, baseName)
                if not rlayer.isValid():
                    txtFeedback.append("Input orthoimage: Could not open %s\n" % LayerInput_1)
                if rlayer.isValid() and not QgsMapLayerRegistry.instance().mapLayersByName('Input orthoimage'):
                    iface.addRasterLayer(LayerInput_1, 'Input orthoimage')
                    txtFeedback.append("> Input orthoimage: Successfully loaded\n")
                    count += 1

            # Load gPb shapefile
            if LayerInput_2:
                layer_2 = QgsVectorLayer(LayerInput_2, 'Input gPb', 'ogr')
                if not layer_2.isValid():
                    txtFeedback.append("Input gPb: Could not open %s\n" % LayerInput_2)
                if layer_2.isValid() and not QgsMapLayerRegistry.instance().mapLayersByName('Input gPb'):
                    iface.addVectorLayer(LayerInput_2, 'Input gPb', 'ogr')

                    # Change symbology of current boundary layer
                    symbols = iface.activeLayer().rendererV2().symbols()
                    symbol = symbols[0]
                    symbol.setColor(QColor.fromRgb(75, 0, 130))
                    symbol.setWidth(0.2)
                    qgis.utils.iface.mapCanvas().refresh()
                    qgis.utils.iface.legendInterface().refreshLayerSymbology(iface.activeLayer())
                    txtFeedback.append("> Input gPb: Successfully loaded\n")
                    count += 1

            # Load SLIC shapefile
            if LayerInput_3:
                layer_3 = QgsVectorLayer(LayerInput_3, 'Input SLIC', 'ogr')
                if not layer_3.isValid():
                    txtFeedback.append("Input SLIC: Could not open %s\n" % LayerInput_3)
                if layer_3.isValid() and not QgsMapLayerRegistry.instance().mapLayersByName('Input SLIC'):
                    iface.addVectorLayer(LayerInput_3, 'Input SLIC', 'ogr')

                    # Change symbology of current boundary layer
                    symbols = iface.activeLayer().rendererV2().symbols()
                    symbol = symbols[0]
                    symbol.setColor(QColor.fromRgb(255, 0, 255))
                    symbol.setWidth(0.2)
                    qgis.utils.iface.mapCanvas().refresh()
                    qgis.utils.iface.legendInterface().refreshLayerSymbology(iface.activeLayer())
                    txtFeedback.append("> Input SLIC: Successfully loaded\n")
                    count += 1

            # Define output shapefile
            if LayerInput_4:
                txtFeedback.append("> Output boundaries: Successfully defined output file\n")
                txtFeedback.append("All processing files will be saved to the directory of the output file\n")
                count += 1

            # Check if all 4 input files are correctly provided by the user
            if count == 4:
                # Get map canvas
                global canvas
                canvas = qgis.utils.iface.mapCanvas()

                # Set canvas extent to the extent of raster layer
                canvas.setExtent(rlayer.extent())

                # Zoom to full extent
                qgis.utils.iface.zoomFull()

                # Inform the user
                txtFeedback.append(">>> Successfully loaded all data\n")
                txtFeedback.append("Please click 'Process Data' before proceeding to Step II\n")

    ####################################################################################################################
    # Process Data: Create network and nodes layer through combining gPb and SLIC layers
    def ProcessData(self):
        # Check if current gPb and SLIC layers exist
        if not QgsMapLayerRegistry.instance().mapLayersByName('Input gPb'):
            txtFeedback.append("'Input gPb' layer does not exist.\n")
            txtFeedback.append(
                "Please select a valid path to an input gPb layer and load it\n")
        if not QgsMapLayerRegistry.instance().mapLayersByName('Input SLIC'):
            txtFeedback.append("'Input SLIC' layer does not exist.\n")
            txtFeedback.append(
                "Please select a valid path to an input SLIC layer and load it\n")
        if QgsMapLayerRegistry.instance().mapLayersByName('Input gPb') and QgsMapLayerRegistry.instance( \
                ).mapLayersByName('Input SLIC'):

            # Clear text field
            txtFeedback.clear()

            # Inform the user
            txtFeedback.append("gPb and SLIC will now be merged to network and nodes...\n")

            # Refresh dialog with text field
            self.dlg.repaint()

            # Initialize counter
            c = 0

            # Load data for gPb and SLIC from canvas
            gPb = QgsMapLayerRegistry.instance().mapLayersByName('Input gPb')[0]
            SLIC = QgsMapLayerRegistry.instance().mapLayersByName('Input SLIC')[0]

            # Define extent
            extent = SLIC.extent()
            xmin = extent.xMinimum()
            xmax = extent.xMaximum()
            ymin = extent.yMinimum()
            ymax = extent.yMaximum()

            # Buffer gPb output
            buffer = LayerInput_4.rpartition('/')[0] + '/processingFile1_buffer.shp'
            buff_dist = 5
            if not os.path.isfile(buffer):
                processing.runalg('qgis:fixeddistancebuffer',
                                  {"INPUT": gPb,
                                   "DISTANCE": buff_dist,
                                   "DISSOLVE": True,
                                   "OUTPUT": buffer})
            self.dlg.progressBar.setValue(5)
            QApplication.processEvents()

            # Clip gPb buffer with SLIC lines
            clip = LayerInput_4.rpartition('/')[0] + '/processingFile2_clip.shp'
            if not os.path.isfile(clip):
                processing.runalg('qgis:clip', {"INPUT": SLIC, "OVERLAY": buffer,
                                                "OUTPUT": clip})
            self.dlg.progressBar.setValue(20)
            QApplication.processEvents()

            # Merge SLIC lines in blocks --> Merging all features at ones results in a long processing time
            clip_layer = QgsVectorLayer(clip, 'clip_layer', "ogr")
            i = int(round(float(clip_layer.featureCount()) / 1000))

            # Initialize counter
            j = 0

            while j < i:
                # Create temporary layer
                vl = QgsVectorLayer("LineString?crs=EPSG:4326", "SLIC_temp", "memory")
                vl.setCrs(clip_layer.crs())
                pr = vl.dataProvider()
                vl.startEditing()

                # Select block of 1000 features to be merged
                start = j * 1 + j * 1000
                end = (j + 1) * 1000

                # Copy features to temporary layer
                iter = clip_layer.getFeatures()
                for feature in iter:
                    if start < feature.id() < end:
                        pr.addFeatures([feature])
                        vl.commitChanges()

                        # Add memory layer to registry
                        # Note: Layer needs to be added to the canvas in order to be usable in processing.runalg
                QgsMapLayerRegistry.instance().addMapLayer(vl)

                # Merge line segments to one feature
                multipart = LayerInput_4.rpartition('/')[0] + '/processingFile3a_multipart' + str(j) + '.shp'
                if not os.path.isfile(multipart):
                    processing.runalg('qgis:singlepartstomultipart',
                                      {"INPUT": vl,
                                       "FIELD": "FID",
                                       "OUTPUT": multipart})

                # Remove memory layer from registry
                QgsMapLayerRegistry.instance().removeMapLayer(vl.id())

                # Increment counter
                j += 1

            # Create list to store created files
            list = []

            # Check for files to be merged in data directory
            data_dir = LayerInput_4.rpartition('/')[0]

            # Change into data directory
            os.chdir(data_dir)

            # Append all files to be merged to a list
            for file in os.listdir(data_dir):
                if 'processingFile3a_multipart' in file and '.shp' in file:
                    SLIC_temp = QgsVectorLayer(file, 'SLIC_temp', "ogr")
                    list.append(file)

            # Merge detected files
            multipart_merge = LayerInput_4.rpartition('/')[0] + '/processingFile3b_multipart.shp'
            if not os.path.isfile(multipart_merge):
                processing.runalg('qgis:mergevectorlayers',
                                  {"LAYERS": list,
                                   "OUTPUT": multipart_merge})
            self.dlg.progressBar.setValue(40)
            QApplication.processEvents()

            # Merge features in merged shapefiles
            final_merge = QgsVectorLayer(multipart_merge, multipart_merge, "ogr")
            multipart = LayerInput_4.rpartition('/')[0] + '/processingFile3c_multipart.shp'
            if not os.path.isfile(multipart):
                processing.runalg('qgis:singlepartstomultipart',
                                  {"INPUT": final_merge,
                                   "FIELD": "FID",
                                   "OUTPUT": multipart})
            self.dlg.progressBar.setValue(60)
            QApplication.processEvents()

            # Clean topology: Snap all lines to closest vertex
            snap = LayerInput_4.rpartition('/')[0] + '/processingFile4_snap.shp'
            if not os.path.isfile(snap):
                processing.runalg('grass7:v.clean', {"input": multipart,
                                                     "tool": 1,  # snap
                                                     "threshold": 0.01,
                                                     "GRASS_REGION_PARAMETER": "%f,%f,%f,%f" % (xmin, xmax, ymin, ymax),
                                                     "output": snap})
            self.dlg.progressBar.setValue(70)
            QApplication.processEvents()

            # Clean topology: Break each line at each point shared between 2 and more lines (vertices)
            network = LayerInput_4.rpartition('/')[0] + '/processingFile5_network.shp'
            if not os.path.isfile(network):
                processing.runalg('grass7:v.clean', {"input": snap,
                                                     "tool": 8,  # bpol
                                                     "GRASS_REGION_PARAMETER": "%f,%f,%f,%f" % (xmin, xmax, ymin, ymax),
                                                     "output": network})
            self.dlg.progressBar.setValue(80)
            QApplication.processEvents()

            # Create nodes
            nodes = LayerInput_4.rpartition('/')[0] + '/processingFile6_nodes.shp'
            if not os.path.isfile(nodes):
                processing.runalg('grass7:v.net.nodes',
                                  {"input": network,
                                   "GRASS_REGION_PARAMETER": "%f,%f,%f,%f" % (xmin, xmax, ymin, ymax),
                                   "GRASS_OUTPUT_TYPE_PARAMETER": 0,
                                   "output": nodes})
            self.dlg.progressBar.setValue(100)
            QApplication.processEvents()

            # Load network file to canvas
            if os.path.isfile(network):
                network_layer = QgsVectorLayer(network, 'Input gPb', 'ogr')
                if not network_layer.isValid():
                    txtFeedback.append("Network file: Could not open %s\n" % network)
                if network_layer.isValid() and not QgsMapLayerRegistry.instance().mapLayersByName('Input network'):
                    iface.addVectorLayer(network, 'Input network', 'ogr')

                    # Change symbology of current boundary layer
                    symbols = iface.activeLayer().rendererV2().symbols()
                    symbol = symbols[0]
                    symbol.setColor(QColor.fromRgb(0, 225, 0))
                    symbol.setWidth(0.2)
                    qgis.utils.iface.mapCanvas().refresh()
                    qgis.utils.iface.legendInterface().refreshLayerSymbology(iface.activeLayer())
                    self.dlg.progressBar.setValue(90)
                    txtFeedback.append("> Input network: Successfully loaded\n")
                    c += 1

            # Load nodes file to canvas
            if os.path.isfile(nodes):
                nodes_layer = QgsVectorLayer(nodes, 'Input nodes', 'ogr')
                if not nodes_layer.isValid():
                    txtFeedback.append("Input nodes: Could not open %s\n" % nodes)
                if nodes_layer.isValid() and not QgsMapLayerRegistry.instance().mapLayersByName('Input nodes'):
                    iface.addVectorLayer(nodes, 'Input nodes', 'ogr')

                    # Change symbology of current boundary layer
                    symbols = iface.activeLayer().rendererV2().symbols()
                    symbol = symbols[0]
                    symbol.setColor(QColor.fromRgb(255, 0, 0))
                    symbol.setSize(1.5)
                    qgis.utils.iface.mapCanvas().refresh()
                    qgis.utils.iface.legendInterface().refreshLayerSymbology(iface.activeLayer())
                    self.dlg.progressBar.setValue(96)
                    txtFeedback.append("> Input nodes: Successfully loaded\n")
                    c += 1

            if c == 2:
                iface.legendInterface().setLayerVisible(gPb, False)
                iface.legendInterface().setLayerVisible(SLIC, False)
                # Inform the user
                self.dlg.progressBar.setValue(100)
                QApplication.processEvents()
                txtFeedback.append(">>> Successfully finished Step I. "
                                   "Proceed to Step II by clicking on the second tab.")

    ####################################################################################################################
    ### STEP II ###
    # Connect Nodes: Connects nodes based on shortest path (steiner network method)
    def SteinerConnect(self):
        # Clear text field
        txtFeedback_2.clear()

        # Get nodes and network layer
        global nodes
        nodes = QgsMapLayerRegistry.instance().mapLayersByName('Input nodes')[0]
        global network
        network = QgsMapLayerRegistry.instance().mapLayersByName('Input network')[0]

        # Define extent according to selected nodes
        extent = nodes.boundingBoxOfSelected()
        xmin = extent.xMinimum() - 20
        xmax = extent.xMaximum() + 20
        ymin = extent.yMinimum() - 20
        ymax = extent.yMaximum() + 20

        # Create new layer to clip layer to extent
        # Note: Done to to decrease processing time of v.net.steiner.
        # v.net.steiner makes QGIS crash if the entire nodes layer is considered since too much memory space is
        # allocated
        extentLayer = QgsVectorLayer("Polygon?crs=EPSG:4326&field=ID:integer", "extentLayer", "memory")
        extentLayer.setCrs(network.crs())
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
            txtFeedback_2.append("> Error: You are about to overwrite existing processing files.\n")
            txtFeedback_2.append("> Please remove all processingFiles with a number > 6 in the filename in the "
                                 "directory you provided for the output boundaries and reclick on 'Connect Nodes'.\n")

            # Remove memory layer from registry
            QgsMapLayerRegistry.instance().removeMapLayer(extentLayer.id())

        else:
            processing.runalg('qgis:clip', {"INPUT": network,
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
            if nodes.selectedFeatureCount() > 1 and nodes.geometryType() == 0:

                # Clear text field
                txtFeedback_3.clear()

                # Inform the user
                txtFeedback_2.append("> Successfully selected nodes that will now be connected...\n")

                # Refresh dialog with text field
                self.dlg.repaint()

                # Connect selected nodes with steiner network
                networkClipLayer = QgsVectorLayer(networkClip, 'networkClip', 'ogr')
                processing.runalg('grass7:v.net.steiner',
                                  {"input": networkClipLayer,
                                   "points": nodes,
                                   "GRASS_REGION_PARAMETER": "%f,%f,%f,%f" % (xmin, xmax, ymin, ymax),
                                   "GRASS_OUTPUT_TYPE_PARAMETER": 0,
                                   "output": steinerLine})
                txtFeedback_2.append(">>> Successfully connected nodes\n")

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

                    multipartSteiner = LayerInput_4.rpartition('/')[0] + '/processingFile7d' + str(i) + \
                                       '_steiner_network_merged.shp'
                    processing.runalg('qgis:singlepartstomultipart',
                                      {"INPUT": smoothSteinerLine,
                                       "FIELD": "FID",
                                       "OUTPUT": multipartSteiner})

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
                    iface.addVectorLayer(sinuositySteinerLine, 'Current boundary', 'ogr')

                    # Change display settings to display current boundary only
                    iface.legendInterface().setLayerVisible(nodes, False)
                    iface.legendInterface().setLayerVisible(network, False)

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
                            "The sinuosity (%.1f) of the line indicates that this line requires further "
                            "consideration.\n" % sinuosity)
                        txtFeedback_2.append(
                            "Would you like to accept, simplify, edit or delete the displayed boundary line?")

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
                        txtFeedback_2.append("The sinuosity (%.1f) of the line indicates that this line might require "
                                             "further consideration.\n" % sinuosity)
                        txtFeedback_2.append(
                            "Would you like to accept, simplify, edit or delete the displayed boundary line?")

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
                            "further consideration.\n" % sinuosity)
                        txtFeedback_2.append(
                            "Would you like to accept, simplify, edit or delete the displayed boundary line?")

                else:
                    # Clear text field
                    txtFeedback_2.clear()

                    # Inform the user
                    txtFeedback_2.append(
                        "Selected nodes could not be connected. Please select nodes that are connected via the 'Input "
                        "network' layer.")
            else:
                txtFeedback_2.append("Please select nodes from 'Input nodes'")

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
            txtFeedback_3.append(
                ">>> Successfully saved the current boundary in %s\n" % (LayerInput_4.rpartition('/')[-1]))
            txtFeedback_3.append(
                "Please select new nodes and click on 'Connect nodes' to create a 'Current boundary' layer.\n")
            txtFeedback_3.append(
                "If you don't want to add more boundary lines to %s click on 'Finish Delineation'.\n"
                % (LayerInput_4.rpartition('/')[-1]))

            # Clear text field
            txtFeedback_2.clear()

            # Change display setting to display current boundary only
            iface.legendInterface().setLayerVisible(nodes, True)
            iface.legendInterface().setLayerVisible(network, True)

            # Remove current boundary layer
            QgsMapLayerRegistry.instance().removeMapLayer(boundaryLayer.id())

            if not QgsMapLayerRegistry.instance().mapLayersByName('Final boundaries'):
                # Add final boundary layer
                iface.addVectorLayer(LayerInput_4, 'Final boundaries', 'ogr')

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

            return 0

        ################################################################################################################
        # Main AcceptLine function body
        # Clear text fields
        txtFeedback_2.clear()
        txtFeedback_3.clear()

        # Remove simplified lines
        if QgsMapLayerRegistry.instance().mapLayersByName('Previous boundary'):
            layer = QgsMapLayerRegistry.instance().mapLayersByName('Previous boundary')[0]
            QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

        # Check if current boundary layer exists
        if not QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):
            txtFeedback_3.append("'Current boundary' layer does not exist.\n")
            txtFeedback_3.append(
                "Please select new nodes and click on 'Connect nodes' to create a 'Current boundary' layer.")

        if QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):
            boundaryLayer = QgsMapLayerRegistry.instance().mapLayersByName('Current boundary')[0]

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
                    txtFeedback_3.append(
                        "Please select new nodes and click on 'Connect nodes' to create a 'Current boundary' layer.")

                # Reset display
                display(self)

    ####################################################################################################################
    # Delete Line: Delete line of current boundary layer
    def DeleteLine(self):

        # Clear text fields
        txtFeedback_2.clear()
        txtFeedback_3.clear()

        # Remove simplified lines
        if QgsMapLayerRegistry.instance().mapLayersByName('Previous boundary'):
            layer = QgsMapLayerRegistry.instance().mapLayersByName('Previous boundary')[0]
            QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

        if not QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):
            txtFeedback_3.append("'Current boundary' layer does not exist.\n")
            txtFeedback_3.append(
                "Please select new nodes and click on 'Connect nodes' to create a 'Current boundary' layer.")

        # Check if current boundary layer exists
        if QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):
            boundaryLayer = QgsMapLayerRegistry.instance().mapLayersByName('Current boundary')[0]

            # Remove current boundary layer
            QgsMapLayerRegistry.instance().removeMapLayer(boundaryLayer.id())

            # Change display setting to display current boundary only
            iface.legendInterface().setLayerVisible(nodes, True)
            iface.legendInterface().setLayerVisible(network, True)

            txtFeedback_3.append("'Current boundary' layer has been deleted.\n")
            txtFeedback_3.append(
                "Please select new nodes and click on 'Connect nodes' to create a 'Current boundary' layer.")

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
                    txtFeedback_2.append(">>> Successfully simplified boundary line.\n")
                    txtFeedback_2.append(
                        "Would you like to accept, simplify, edit or delete the displayed boundary line?")
                    return 1

        ################################################################################################################
        # Main SimplifyLine function body
        # Clear text fields
        txtFeedback_2.clear()
        txtFeedback_3.clear()

        # Check if current boundary layer exists
        if not QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):
            txtFeedback_3.append("'Current boundary' layer does not exist.\n")
            txtFeedback_3.append(
                "Please select new nodes and click on 'Connect nodes' to create a 'Current boundary' layer.")

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
                txtFeedback_2.append("> Error: You are about to overwrite existing processing files.\n")
                txtFeedback_2.append("> Please remove all processingFiles with a number > 7 in the filename "
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
                iface.addVectorLayer(currBoundary_out, 'Current boundary', 'ogr')

                # Change symbology of current boundary layer
                layer = iface.activeLayer()
                symbols = layer.rendererV2().symbols()
                symbol = symbols[0]
                symbol.setColor(QColor.fromRgb(255, 0, 0))
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
        txtFeedback_3.clear()

        # Check if current boundary layer exists
        if QgsMapLayerRegistry.instance().mapLayersByName('Current boundary'):
            layer = QgsMapLayerRegistry.instance().mapLayersByName('Current boundary')[0]

            # Start editing session for current boundary layer
            layer.startEditing()

            # Inform the user
            txtFeedback_3.append("Please edit 'Current boundary' and click on 'Accept Line' when finished.\n")
            txtFeedback_3.append("Instructions on editing in QGIS can be found in the help tab.")
        else:
            # Inform the user
            txtFeedback_3.append("'Current boundary' layer does not exist.\n")
            txtFeedback_3.append(
                "Please select new nodes and click on 'Connect nodes' to create a 'Current boundary' layer.")

    ###################################################################################################################
    # Finish Line Delineation: No more changes need to be made and teh final boundary file can be saved
    def FinishDelineation(self):

        # Show final boundary layer
        if QgsMapLayerRegistry.instance().mapLayersByName('Final boundaries'):
            finalBoundaries = QgsMapLayerRegistry.instance().mapLayersByName('Final boundaries')[0]
            iface.legendInterface().setLayerVisible(finalBoundaries, True)

            # Hide remaining layers layer
            if QgsMapLayerRegistry.instance().mapLayersByName('Input gPb'):
                iface.legendInterface().setLayerVisible \
                    (QgsMapLayerRegistry.instance().mapLayersByName('Input gPb')[0], False)
            if QgsMapLayerRegistry.instance().mapLayersByName('Input SLIC'):
                iface.legendInterface().setLayerVisible \
                    (QgsMapLayerRegistry.instance().mapLayersByName('Input SLIC')[0], False)
            if QgsMapLayerRegistry.instance().mapLayersByName('Input nodes'):
                iface.legendInterface().setLayerVisible \
                    (QgsMapLayerRegistry.instance().mapLayersByName('Input nodes')[0], False)
            if QgsMapLayerRegistry.instance().mapLayersByName('Input network'):
                iface.legendInterface().setLayerVisible \
                    (QgsMapLayerRegistry.instance().mapLayersByName('Input network')[0], False)

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
                txtFeedback_3.clear()

                # Inform the user
                txtFeedback_3.append(
                    ">>> All final boundaries are displayed and saved in %s\n" % (LayerInput_4.rpartition('/')[-1]))
                txtFeedback_3.append(
                    "If you don't consider making further changes to this file, you may delete all processing files "
                    "in the same directory and close the Plugin.\n")
                txtFeedback_3.append(
                    "If you would like to manually add further lines, click on 'Manual Delineation'.\n")
        else:
            # Clear text fields
            txtFeedback_2.clear()
            txtFeedback_3.clear()

            # Inform the user
            txtFeedback_3.append("'Current boundary' layer does not exist.\n")
            txtFeedback_3.append(
                "Please select new nodes and click on 'Connect nodes' to create a 'Current boundary' layer.")

            # Refresh dialog with text field
            self.dlg.repaint()

    ###################################################################################################################
    # Finish Line Delineation: No more changes need to be made and teh final boundary file can be saved
    def ManualDelineation(self):

        # Show final boundary layer
        if QgsMapLayerRegistry.instance().mapLayersByName('Final boundaries'):
            finalBoundaries = QgsMapLayerRegistry.instance().mapLayersByName('Final boundaries')[0]
            iface.legendInterface().setLayerVisible(finalBoundaries, True)

            # Start editing final boundary layer
            finalBoundaries.startEditing()

            # Hide remaining layers layer
            if QgsMapLayerRegistry.instance().mapLayersByName('Input gPb'):
                iface.legendInterface().setLayerVisible \
                    (QgsMapLayerRegistry.instance().mapLayersByName('Input gPb')[0], False)
            if QgsMapLayerRegistry.instance().mapLayersByName('Input SLIC'):
                iface.legendInterface().setLayerVisible \
                    (QgsMapLayerRegistry.instance().mapLayersByName('Input SLIC')[0], False)
            if QgsMapLayerRegistry.instance().mapLayersByName('Input nodes'):
                iface.legendInterface().setLayerVisible \
                    (QgsMapLayerRegistry.instance().mapLayersByName('Input nodes')[0], False)
            if QgsMapLayerRegistry.instance().mapLayersByName('Input network'):
                iface.legendInterface().setLayerVisible \
                    (QgsMapLayerRegistry.instance().mapLayersByName('Input network')[0], False)

            # Zoom to full extent
            qgis.utils.iface.zoomFull()

            # Clear text fields
            txtFeedback_2.clear()
            txtFeedback_3.clear()

            # Inform the user
            txtFeedback_3.append(
                "> Final boundary layer is now editable\n")
            txtFeedback_3.append(
                "Please add features (click add feature in QGIS Digitizing Toolbar) and save these in the same "
                "toolbar.\n")

        else:

            # Clear text fields
            txtFeedback_2.clear()
            txtFeedback_3.clear()

            # Inform the user
            txtFeedback_3.append("'Current boundary' layer does not exist.\n")
            txtFeedback_3.append(
                "Please select new nodes and click on 'Connect nodes' to create a 'Current boundary' layer.")

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

# sinuosity_index = sinuosityLineLayer.fieldNameIndex('sinuosity')
# feature = sinuosityLineLayer.getFeatures()
# sinuosity = feature.attributes([sinuosity_index])

### Create log file for debugging ###
def write_log_message(message, tag, level):
    filename = cwd + r'\LogFile.log'
    with open(filename, 'w') as logfile:
        logfile.write('{tag}({level}): {message}'.format(tag=tag, level=level, message=message))
/***************************************************************************
"""
