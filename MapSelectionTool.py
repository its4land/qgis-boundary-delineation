"""MapSelectionTool to draw a polygon and get the coordinates of it.

This script was based on https://github.com/lcoandrade/OSMDownloader/blob/master/rectangleAreaTool.py

Notes:
    begin                : 2019-02-09
    git sha              : $Format:%H$

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


from qgis.gui import QgsMapTool, QgsRubberBand, QgsMapMouseEvent, QgsMapCanvas
from qgis.core import QgsWkbTypes, QgsPointXY
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QApplication

class MapSelectionTool(QgsMapTool):

    polygonCreated = pyqtSignal(QgsPointXY, QgsPointXY, Qt.KeyboardModifiers)

    def __init__(self, canvas: QgsMapCanvas) -> None:
        QgsMapTool.__init__(self, canvas)

        mFillColor = QColor(254, 178, 76, 63)

        self.canvas = canvas
        self.active = True

        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(mFillColor)
        self.rubberBand.setWidth(1)
        self.reset()

    def reset(self) -> None:
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)

    def canvasPressEvent(self, e: QgsMapMouseEvent) -> None:
        self.startPoint = self.toMapCoordinates(e.pos())
        self.endPoint = self.startPoint
        self.isEmittingPoint = True
        self.showRect(self.startPoint, self.endPoint)

    def canvasReleaseEvent(self, e: QgsMapMouseEvent) -> None:
        self.isEmittingPoint = False
        self.rubberBand.hide()
        self.polygonCreated.emit(self.startPoint, self.endPoint, QApplication.keyboardModifiers())

    def canvasMoveEvent(self, e: QgsMapMouseEvent) -> None:
        if not self.isEmittingPoint:
            return
        self.endPoint = self.toMapCoordinates(e.pos())
        self.showRect(self.startPoint, self.endPoint)

    def showRect(self, startPoint: QgsPointXY, endPoint: QgsPointXY) -> None:
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
            return
        point1 = QgsPointXY(startPoint.x(), startPoint.y())
        point2 = QgsPointXY(startPoint.x(), endPoint.y())
        point3 = QgsPointXY(endPoint.x(), endPoint.y())
        point4 = QgsPointXY(endPoint.x(), startPoint.y())

        self.rubberBand.addPoint(point1, False)
        self.rubberBand.addPoint(point2, False)
        self.rubberBand.addPoint(point3, False)
        self.rubberBand.addPoint(point4, True)    # true to update canvas
        self.rubberBand.show()

    def deactivate(self) -> None:
        self.rubberBand.hide()
        QgsMapTool.deactivate(self)
