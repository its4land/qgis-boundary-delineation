"""UI controller of the dock.

Attributes:
    SC_ACCEPT (str): shortcut for accepting candidates
    SC_EDIT (str): shortcut for editing candidates
    SC_MODE_LINES (str): shortcut for toggling lines mode
    SC_MODE_MANUAL (str): shortcut for toggling manual mode
    SC_MODE_POLYGONS (str): shortcut for toggling polygons mode
    SC_MODE_VERTICES (str): shortcut for toggling vertices mode
    SC_REJECT (str): shortcut for rejecting candidate
    SC_UPDATE (str): shortcut for updating the candidates layer

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
MIT License

Copyright (c) 2020 "its4land project", "ITC, University of Twente"

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os

from typing import Callable

from PyQt5 import uic
from PyQt5.QtCore import (pyqtSignal, QUrl)
from PyQt5.QtGui import QCloseEvent, QKeySequence
from PyQt5.QtWidgets import QDockWidget, QAction, QFileDialog, QWidget, QMessageBox, QShortcut

from qgis.core import QgsMapLayerProxyModel, QgsFieldProxyModel, QgsVectorLayer, QgsRasterLayer
from qgis.utils import iface

from .utils import SelectionModes, __, create_icon, set_button_icon, set_label_icon, zoom_to_layer
from .BoundaryDelineationIts4landWindow import BoundaryDelineationIts4landWindow

SC_MODE_POLYGONS = 'Ctrl+Alt+1'
SC_MODE_LINES = 'Ctrl+Alt+2'
SC_MODE_VERTICES = 'Ctrl+Alt+3'
SC_MODE_MANUAL = 'Ctrl+Alt+4'
SC_ACCEPT = 'Ctrl+Alt+A'
SC_REJECT = 'Ctrl+Alt+C'
SC_EDIT = 'Ctrl+Alt+E'
SC_UPDATE = 'Ctrl+Alt+U'

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'BoundaryDelineationDock.ui'))
class BoundaryDelineationDock(QDockWidget, FORM_CLASS):
    closingPlugin = pyqtSignal()

    def __init__(self, plugin, parent=None):
        """Constructor."""
        super(BoundaryDelineationDock, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.plugin = plugin
        self.its4landWindow = BoundaryDelineationIts4landWindow(plugin)
        self.isAlreadyProcessed = False
        self.isLoadingLayer = False
        self.isBeingProcessed = False

        self.tabs.setTabEnabled(1, False)
        self.step1ProgressBar.setValue(0)

    def init(self) -> None:
        self.baseRasterLayerComboBox.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.segmentsLayerComboBox.setFilters(QgsMapLayerProxyModel.LineLayer)

        self.baseRasterLayerButton.clicked.connect(self.onBaseRasterInputButtonClicked)
        self.baseRasterLayerComboBox.layerChanged.connect(self.onBaseRasterLayerComboBoxChanged)
        self.segmentsLayerButton.clicked.connect(self.onSegmentsLayerButtonClicked)
        self.segmentsLayerComboBox.layerChanged.connect(self.onSegmentsLayerComboBoxChanged)
        self.outputLayerButton.clicked.connect(self.onOutputLayerButtonClicked)
        self.outputLayerLineEdit.textChanged.connect(self.onOutputLayerLineEditChanged)
        self.its4landButton.clicked.connect(self.onIts4landButtonClicked)
        self.addLengthAttributeCheckBox.toggled.connect(self.onAddLengthAttributeCheckBoxToggled)
        self.processButton.clicked.connect(self.onProcessButtonClicked)

        self.modePolygonsRadio.toggled.connect(self.onModePolygonsRadioToggled)
        self.modeVerticesRadio.toggled.connect(self.onModeVerticesRadioToggled)
        self.modeLinesRadio.toggled.connect(self.onModeLinesRadioToggled)
        self.modeManualRadio.toggled.connect(self.onModeManualRadioToggled)

        self.weightComboBox.fieldChanged.connect(self.onWeightComboBoxChanged)

        self.acceptButton.clicked.connect(self.onAcceptButtonClicked)
        self.rejectButton.clicked.connect(self.onRejectButtonClicked)
        self.editButton.toggled.connect(self.onEditButtonToggled)
        self.updateEditsButton.clicked.connect(self.onUpdateEditsButtonClicked)
        self.finishButton.clicked.connect(self.onFinishButtonClicked)

        self.weightComboBox.setFilters(QgsFieldProxyModel.Numeric)

        set_label_icon(self.its4landLabel, 'its4landLogo.png')
        set_button_icon(self.acceptButton, 'accept.png')
        set_button_icon(self.editButton, 'edit.png')
        set_button_icon(self.rejectButton, 'reject.png')
        set_button_icon(self.finishButton, 'finishFlag.png')

        self.action = QAction(create_icon('icon.png'), 'ITS4LAND Settings', iface.mainWindow())
        self.action.setWhatsThis('Settings')
        self.action.setStatusTip('ITS4LAND Settings')
        self.action.setObjectName('its4landButton')
        self.action.triggered.connect(self.onIts4landButtonClicked)

        iface.addPluginToMenu('&BoundaryDelineation', self.action)

        # TODO enable to row below for faster debugging
        # self.its4landWindow.show()

        if self.baseRasterLayerComboBox.currentLayer():
            self.baseRasterLayerComboBox.layerChanged.emit(self.baseRasterLayerComboBox.currentLayer())

        if self.segmentsLayerComboBox.currentLayer():
            self.segmentsLayerComboBox.layerChanged.emit(self.segmentsLayerComboBox.currentLayer())

        self.createShortcut(SC_MODE_POLYGONS, self.modePolygonsRadio, self.onShortcutModePolygons)
        self.createShortcut(SC_MODE_LINES, self.modeLinesRadio, self.onShortcutModeLines)
        self.createShortcut(SC_MODE_VERTICES, self.modeVerticesRadio, self.onShortcutModeVertices)
        self.createShortcut(SC_MODE_MANUAL, self.modeManualRadio, self.onShortcutModeManual)
        self.createShortcut(SC_ACCEPT, self.acceptButton, self.onShortcutAccept)
        self.createShortcut(SC_REJECT, self.rejectButton, self.onShortcutReject)
        self.createShortcut(SC_EDIT, self.editButton, self.onShortcutEdit)
        self.createShortcut(SC_UPDATE, self.updateEditsButton, self.onShortcutUpdate)

        try:
            from PyQt5.QtWebKitWidgets import QWebView

            helpView = QWebView()
            helpView.setUrl(QUrl('https://its4land.com/automate-it-wp5/'))
            self.helpWrapper.addWidget(helpView)
        except Exception as err:
            print(err)
            pass

    def createShortcut(self, sequence: str, widget: QWidget, callback: Callable):
        """Create shortcut and add the key sequence to the tooltip.

        Args:
            sequence (str): The key sequece of the shorcut (e.g. Ctrl+2)
            widget (QWidget): The widget that is applied on
            callback (Callable): Callback
        """
        widget.setToolTip(widget.toolTip() + ' (%s)' % sequence)
        shortcut = QShortcut(QKeySequence(sequence), self)
        shortcut.activated.connect(callback)

    def onShortcutModePolygons(self) -> None:
        """Trigger activation of mode Polygons."""
        if self.isAlreadyProcessed:
            self.plugin.setSelectionMode(SelectionModes.ENCLOSING)

    def onShortcutModeLines(self) -> None:
        """Trigger activation of mode Lines."""
        if self.isAlreadyProcessed:
            self.plugin.setSelectionMode(SelectionModes.LINES)

    def onShortcutModeVertices(self) -> None:
        """Trigger activation of mode Vertices."""
        if self.isAlreadyProcessed:
            self.plugin.setSelectionMode(SelectionModes.NODES)

    def onShortcutModeManual(self) -> None:
        """Trigger activation of mode Manual."""
        if self.isAlreadyProcessed:
            self.plugin.setSelectionMode(SelectionModes.MANUAL)

    def onShortcutAccept(self) -> None:
        """Accept the current candidate."""
        if self.isAlreadyProcessed:
            self.acceptButton.animateClick()

    def onShortcutReject(self) -> None:
        """Reject the current candidate."""
        if self.isAlreadyProcessed:
            self.rejectButton.animateClick()

    def onShortcutEdit(self) -> None:
        """Edit the current candidate."""
        if self.isAlreadyProcessed:
            self.editButton.animateClick()

    def onShortcutUpdate(self) -> None:
        """Update the edits."""
        if self.isAlreadyProcessed:
            self.updateEditsButton.animateClick()

    def onIts4landButtonClicked(self):
        self.its4landWindow.show()

    def onBaseRasterInputButtonClicked(self):
        result = QFileDialog.getOpenFileName(self, __('Open Base Raster Layer File'), '', 'Raster Image (*.tif *.tiff *.geotiff *.ascii *.map)')

        if not result or not result[0]:
            return

        layer = self.plugin.setBaseRasterLayer(result[0])
        self.baseRasterLayerComboBox.setLayer(layer)

    def onSegmentsLayerButtonClicked(self):
        result = QFileDialog.getOpenFileName(self, __('Open Segments Layer File'), '', 'ESRI Shapefile (*.shp)')

        if not result or not result[0]:
            return

        layer = self.plugin.setSegmentsLayer(result[0])
        self.segmentsLayerComboBox.setLayer(layer)

    def onBaseRasterLayerComboBoxChanged(self, layer: QgsRasterLayer) -> None:
        if self.isLoadingLayer:
            return

        if not layer:
            return

        self.isLoadingLayer = True

        self.plugin.setBaseRasterLayer(layer)

        self.isLoadingLayer = False

        zoom_to_layer(layer)

    def onSegmentsLayerComboBoxChanged(self, layer: QgsVectorLayer) -> None:
        if self.isLoadingLayer:
            return

        if not layer:
            return

        self.isLoadingLayer = True

        layer = self.plugin.setSegmentsLayer(layer)

        self.isLoadingLayer = False

        zoom_to_layer(layer)

        if not self.isBeingProcessed:
            self.processButton.setEnabled(True)

    def onOutputLayerButtonClicked(self) -> None:
        result = QFileDialog.getSaveFileName(self, __('Save Boundary Layer File'), '', 'ESRI Shapefile (*.shp)')

        if not result or not result[0]:
            return

        self.outputLayerLineEdit.setText(result[0])

    def onOutputLayerLineEditChanged(self, text: str) -> None:
        pass

    def onModeVerticesRadioToggled(self, checked: bool) -> None:
        self.weightComboBox.setEnabled(checked)

        if checked:
            self.plugin.setSelectionMode(SelectionModes.NODES)
            self.editButton.setChecked(False)

    def onModeLinesRadioToggled(self, checked: bool) -> None:
        if checked:
            self.plugin.setSelectionMode(SelectionModes.LINES)
            self.editButton.setChecked(False)

    def onModePolygonsRadioToggled(self, checked: bool) -> None:
        if checked:
            self.plugin.setSelectionMode(SelectionModes.ENCLOSING)
            self.editButton.setChecked(False)

    def onModeManualRadioToggled(self, checked: bool) -> None:
        if checked:
            self.plugin.setSelectionMode(SelectionModes.MANUAL)
            self.editButton.setChecked(False)

    def onAddLengthAttributeCheckBoxToggled(self, checked: bool) -> None:
        self.plugin.shouldAddLengthAttribute = checked

    def onAcceptButtonClicked(self) -> None:
        self.plugin.acceptCandidates()
        # TODO see the self.onRejectButtonClicked
        self.plugin.refreshSelectionModeBehavior()
        self.editButton.setChecked(False)

    def onRejectButtonClicked(self) -> None:
        self.plugin.rejectCandidates()
        # TODO for some reason this refresh is needed in case we are in manual mode.
        # If we are in manual mode and then rejected, it swtitches to manual too and
        # the selection mode is undefined...
        self.plugin.refreshSelectionModeBehavior()
        self.editButton.setChecked(False)

    def onEditButtonToggled(self) -> None:
        self.plugin.toggleEditCandidates()
        # putting here self.plugin.refreshSelectionModeBehavior() causes infinite loop.

    def onUpdateEditsButtonClicked(self) -> None:
        self.plugin.updateLayersTopology()

    def onFinishButtonClicked(self) -> None:
        self.plugin.processFinish()
        self.tabs.setCurrentWidget(self.stepOneTab)
        self.tabs.setTabEnabled(1, False)
        self.step1ProgressBar.setValue(0)
        self.isAlreadyProcessed = False

    def onProcessButtonClicked(self) -> None:
        self.step1ProgressBar.setValue(0)
        self.toggleFirstStepLock(True)

        if self.isAlreadyProcessed:
            userConfirms = self.getConfirmation(
                __('Already processed'),
                __('Are you sure you want to proceed?')
            )

            if userConfirms:
                self.plugin.resetProcessed()
            else:
                self.toggleFirstStepLock(False)
                return

        self.plugin.processFirstStep()

        self.toggleFirstStepLock(False)
        self.tabs.setCurrentWidget(self.stepTwoTab)
        self.updateSelectionModeButtons()

        self.isAlreadyProcessed = True

        self.step1ProgressBar.setValue(100)

    def onWeightComboBoxChanged(self, name: str) -> None:
        self.plugin.setWeightField(name)

    def toggleFirstStepLock(self, disabled: bool) -> None:
        self.isBeingProcessed = disabled

        self.tabs.setTabEnabled(1, not disabled)

        self.baseRasterLayerButton.setDisabled(disabled)
        self.baseRasterLayerComboBox.setDisabled(disabled)
        self.segmentsLayerButton.setDisabled(disabled)
        self.segmentsLayerSimplifyInput.setDisabled(disabled)
        self.segmentsLayerComboBox.setDisabled(disabled)
        self.outputLayerLineEdit.setDisabled(disabled)
        self.outputLayerButton.setDisabled(disabled)
        self.processButton.setDisabled(disabled)
        self.its4landButton.setDisabled(disabled)
        self.addLengthAttributeCheckBox.setDisabled(disabled or not self.plugin.isAddingLengthAttributePossible())

    def getSimplificationValue(self) -> float:
        return self.segmentsLayerSimplifyInput.value()

    def updateSelectionModeButtons(self) -> None:
        if self.plugin.selectionMode is SelectionModes.NONE:
            # using QRadioButton.setAutoExclusive gives the ability to deselect all the radio buttons at once
            self.modePolygonsRadio.setAutoExclusive(False)
            self.modePolygonsRadio.setChecked(False)
            self.modePolygonsRadio.setAutoExclusive(True)
            self.modeVerticesRadio.setAutoExclusive(False)
            self.modeVerticesRadio.setChecked(False)
            self.modeVerticesRadio.setAutoExclusive(True)
            self.modeLinesRadio.setAutoExclusive(False)
            self.modeLinesRadio.setChecked(False)
            self.modeLinesRadio.setAutoExclusive(True)
            self.modeManualRadio.setAutoExclusive(False)
            self.modeManualRadio.setChecked(False)
            self.modeManualRadio.setAutoExclusive(True)
            return

        if self.plugin.isMapSelectionToolEnabled and self.plugin.selectionMode == SelectionModes.ENCLOSING:
            self.modePolygonsRadio.setChecked(True)
            return

        if self.plugin.isMapSelectionToolEnabled and self.plugin.selectionMode == SelectionModes.NODES:
            self.modeVerticesRadio.setChecked(True)
            return

        if self.plugin.isMapSelectionToolEnabled and self.plugin.selectionMode == SelectionModes.LINES:
            self.modeLinesRadio.setChecked(True)
            return

        self.modeManualRadio.setChecked(True)

    def toggleVerticesRadioEnabled(self, enabled: bool = None) -> None:
        if enabled is None:
            enabled = not self.modeVerticesRadio.enabled()

        self.modeVerticesRadio.setEnabled(enabled)

    def toggleAddLengthAttributeCheckBoxEnabled(self, enabled: bool = None) -> None:
        if enabled is None:
            enabled = not self.addLengthAttributeCheckBox.enabled()

        self.addLengthAttributeCheckBox.setEnabled(enabled)

    # def closeEvent(self, event: QCloseEvent):
    #     userConfirm = self.getConfirmation(
    #       __('Message'),
    #       __('Are you sure you want to quit? All the layers execpt the results will be removed.')
    #     )
    #
    #     if reply == QMessageBox.Yes:
    #         self.closingPlugin.emit()
    #         event.accept()
    #     else:
    #         event.ignore()

    def getOutputLayer(self) -> str:
        return self.outputLayerLineEdit.text()

    def getPolygonizeChecked(self) -> bool:
        return self.polygonizeCheckBox.isChecked()

    def getConfirmation(self, title: str, body: str) -> bool:
        reply = QMessageBox.question(
            self,
            title,
            body,
            QMessageBox.Yes,
            QMessageBox.No
        )

        return reply == QMessageBox.Yes

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closingPlugin.emit()
        event.accept()

    def setCandidatesButtonsEnabled(self, enable: bool) -> None:
        self.acceptButton.setEnabled(enable)
        self.rejectButton.setEnabled(enable)
        self.editButton.setEnabled(enable)

    def toggleFinalButtonEnabled(self, enabled: bool = None) -> bool:
        if enabled is None:
            enabled = not self.finishButton.enabled()

        self.finishButton.setEnabled(enabled)
        self.updateEditsButton.setEnabled(enabled)

        return enabled

    def setComboboxLayer(self, layer: QgsVectorLayer, weight_attribute: str = None) -> None:
        self.weightComboBox.setLayer(layer)

        if weight_attribute is not None:
            self.weightComboBox.setField(weight_attribute)
