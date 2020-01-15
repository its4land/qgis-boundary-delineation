"""Utility functions and definitions.

Attributes:
    APP_NAME (str): application name
    GROUP_NAME (str): layer tree group name
    PLUGIN_DIR (TYPE): plugin directory absolute path
    TMP_DIR (str): temporary directory path

Notes:
    begin                : 2019-02-14
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

import functools
import collections.abc
import typing
import os
import json

from enum import Enum
from collections import defaultdict

from PyQt5.QtCore import Qt, QDir, QCoreApplication
from PyQt5.QtGui import QCursor, QColor, QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QPushButton, QLabel

import processing

from qgis.core import Qgis, QgsProject, QgsMarkerSymbol, QgsLineSymbol, QgsSingleSymbolRenderer, QgsGraduatedSymbolRenderer, QgsLayerTreeNode, QgsLayerTreeLayer, QgsVectorLayer, QgsRasterLayer, QgsMapLayer, QgsPoint, QgsVectorFileWriter, QgsCoordinateReferenceSystem, QgsLayerTreeGroup
from qgis.utils import iface

PLUGIN_DIR = os.path.dirname(__file__)
TMP_DIR = 'boundarydeleniation'
APP_NAME = 'BoundaryDelineation'
GROUP_NAME = 'BoundaryDelineation'

def __(msg: str) -> str:
    """Get the translation for a string using Qt translation API.

    Args:
        msg (str): string to translate

    Returns:
        str: translated string

    """
    return QCoreApplication.translate(APP_NAME, msg)

def show_info(msg: str, duration: int = 5) -> None:
    """Show info message.

    Args:
        msg (str): Message to be shown
        duration (int, optional): Duration to have the message visible
    """
    iface.messageBar().pushMessage(APP_NAME, msg, Qgis.Info, duration)

def show_error(msg: str, duration: int = 5) -> None:
    """Show error message.

    Args:
        msg (str): Message to be shown
        duration (int, optional): Duration to have the message visible
    """
    iface.messageBar().pushMessage(APP_NAME, msg, Qgis.Error, duration)

def create_icon(icon: str) -> QIcon:
    """Create icon object with icon image.

    Args:
        icon (str): path to file inside the icons dir

    Returns:
        QIcon: created icon

    """
    return QIcon(os.path.join(PLUGIN_DIR, 'icons', icon))

def set_button_icon(button: QPushButton, icon: str) -> None:
    """Set icon object on a button.

    Args:
        button (QPushButton): Button to set the icon to
        icon (str): path to file inside the icons dir

    """
    button.setIcon(create_icon(icon))

def set_label_icon(label: QLabel, icon: str) -> None:
    """Set icon as background of an label.

    Args:
        label (QLabel): Label to set the icon to
        icon (str): path to file inside the icons dir

    """
    label.setPixmap(QPixmap(os.path.join(PLUGIN_DIR, 'icons', icon)))

def get_group(index: int = 0) -> QgsLayerTreeGroup:
    """Get or create group in the layer tree.

    Args:
        index (int, optional): Index position where to put the group in case of creation

    Returns:
        QgsLayerTreeGroup: The group element

    """
    layerTree = QgsProject.instance().layerTreeRoot()
    group = layerTree.findGroup(GROUP_NAME)

    if not group:
        group = layerTree.insertGroup(index, GROUP_NAME)

    return group

def zoom_to_layer(layer: QgsMapLayer) -> None:
    iface.setActiveLayer(layer)
    iface.actionZoomToLayer().trigger()

def processing_cursor(cursor=QCursor(Qt.WaitCursor)) -> typing.Callable:
    def processing_cursor_decorator(func):
        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):
            show_processing_cursor(cursor=cursor)

            try:
                return func(*args, **kwargs)
            except Exception:
                hide_processing_cursor()
                raise
            finally:
                hide_processing_cursor()

        return func_wrapper
    return processing_cursor_decorator

def show_processing_cursor(cursor=QCursor(Qt.WaitCursor)) -> None:
    QApplication.setOverrideCursor(cursor)
    QApplication.processEvents()

def hide_processing_cursor() -> None:
    QApplication.restoreOverrideCursor()
    QApplication.processEvents()

def remove_layer(layer) -> bool:
    if not layer:
        return False

    QgsProject.instance().removeMapLayer(layer.id())
    iface.mapCanvas().refresh()

    return True

def move_tree_node(node: typing.Union[QgsMapLayer, QgsLayerTreeNode], index: int, parent: QgsLayerTreeNode = None) -> None:
    root = QgsProject.instance().layerTreeRoot()
    node = root.findLayer(node.id()) if isinstance(node, QgsMapLayer) else node

    if node is None:
        return

    layer_clone = node.clone()
    parent = parent if parent else node.parent()
    parent.insertChildNode(index, layer_clone)
    parent.removeChildNode(node)

def get_tree_node_index(node: typing.Union[QgsMapLayer, QgsLayerTreeNode], top: bool = False) -> int:
    root = QgsProject.instance().layerTreeRoot()
    node = root.findLayer(node.id()) if isinstance(node, QgsMapLayer) else node
    node_parent = node.parent()

    if top:
        tmp = node_parent
        while(tmp):
            tmp = tmp.parent()

            if not tmp:
                break

            node = node_parent
            node_parent = tmp

    for i, n in enumerate(node_parent.children()):
        if n is node:
            return i

    return -1

def add_group(group: QgsLayerTreeNode, name: str = None, index: int = -1, parent: QgsLayerTreeNode = None) -> None:
    parent = parent if parent else QgsProject.instance().layerTreeRoot()
    parent.insertGroup(index, group)

def add_layer(layer: QgsMapLayer, name: str = None, index: int = -1, color: typing.Tuple[int, int, int] = None, size: float = None, file: str = None, parent: QgsLayerTreeNode = None, show_feature_count: bool = True) -> None:
    if name:
        layer.setName(name)

    if isinstance(layer, QgsVectorLayer):
        if color or size or file:
            update_symbology(layer, color=color, size=size, file=file)
    elif isinstance(layer, QgsRasterLayer):
        # TODO update symbology
        pass

    instance = QgsProject.instance()
    instance.addMapLayer(layer, False)

    layerTreeNode = QgsLayerTreeLayer(layer)
    layerTreeNode.setCustomProperty('showFeatureCount', show_feature_count)

    parent = parent if parent else instance.layerTreeRoot()
    parent.insertChildNode(index, layerTreeNode)

def update_symbology(layer: QgsMapLayer, color: typing.Tuple[int, int, int] = None, size: float = None, file: str = None) -> None:
    assert layer, 'Layer is not defined'

    if file:
        assert isinstance(file, str)

        (msg, noError) = layer.loadNamedStyle(file)

        if not noError:
            raise Exception(msg)

    renderer = layer.renderer()

    symbol = None

    if isinstance(renderer, QgsSingleSymbolRenderer):
        symbol = renderer.symbol()
    elif isinstance(renderer, QgsGraduatedSymbolRenderer):
        symbol = renderer.sourceSymbol()
    else:
        raise Exception('Unknown renderer!')

    if color:
        assert isinstance(color, collections.abc.Sequence), 'Color should be a iteratable of three numbers for Red, Green, Blue; Each of them between 0 and 255'
        assert len(color) in (3, 4), 'There should be three numbers passed for Red, Green, Blue; Each of them between 0 and 255'

        symbol.setColor(QColor.fromRgb(*color))

    if size:
        # For lines
        if type(symbol) == QgsLineSymbol:
            symbol.setWidth(size)

        # For points
        if type(symbol) == QgsMarkerSymbol:
            symbol.setSize(size)

        layer.triggerRepaint()
        iface.layerTreeView().refreshLayerSymbology(layer.id())

def set_active_layer(layer: QgsMapLayer) -> None:
    assert isinstance(layer, QgsVectorLayer)

    iface.setActiveLayer(layer)


def selected_features_to_layer(vector_layer: QgsVectorLayer, name: str = None) -> QgsVectorLayer:
    if name is None:
        name = 'SelectedFeatures'

    result = processing.run('native:saveselectedfeatures', {
        'INPUT': vector_layer,
        'OUTPUT': 'memory:%s' % name
    })

    return result['OUTPUT']

def dissolve_layer(vector_layer: QgsVectorLayer, name: str = None) -> QgsVectorLayer:
    if name is None:
        name = 'DissolvedFeatures'

    result = processing.run('native:dissolve', {
        'INPUT': vector_layer,
        'FIELD': [],
        'OUTPUT': 'memory:%s' % name,
    })

    return result['OUTPUT']

def merge_lines_layer(vector_layer: QgsVectorLayer, name: str = None) -> QgsVectorLayer:
    if name is None:
        name = 'MergedLines'

    result = processing.run('native:mergelines', {
        'INPUT': vector_layer,
        'FIELD': [],
        'OUTPUT': 'memory:%s' % name,
    })

    return result['OUTPUT']

def polygons_layer_to_lines_layer(vector_layer: QgsVectorLayer, name: str = None) -> QgsVectorLayer:
    if name is None:
        name = 'polygonstolines'

    result = processing.run('qgis:polygonstolines', {
        'INPUT': vector_layer,
        'OUTPUT': 'memory:%s' % name,
    })

    return result['OUTPUT']

def lines_to_polygons(vector_layer: QgsVectorLayer, name: str = None) -> QgsVectorLayer:
    if name is None:
        name = 'LinesToPolygons'

    result = processing.run('qgis:linestopolygons', {
        'INPUT': vector_layer,
        'OUTPUT': 'memory:%s' % name,
    })

    return result['OUTPUT']

def multipart_to_singleparts(vector_layer: QgsVectorLayer, name: str = None) -> QgsVectorLayer:
    if name is None:
        name = 'MultipartToSingleparts'

    result = processing.run('native:multiparttosingleparts', {
        'INPUT': vector_layer,
        'OUTPUT': 'memory:%s' % name,
    })

    return result['OUTPUT']

def split_with_lines(vector_layer: QgsVectorLayer, lines_layer: QgsVectorLayer, name: str = 'Splitted') -> QgsVectorLayer:
    splitted = processing.run('native:splitwithlines', {
        'INPUT': vector_layer,
        'LINES': lines_layer,
        'OUTPUT': 'memory:%s' % name,
    })

    return splitted['OUTPUT']

def difference(vector_layer: QgsVectorLayer, lines_layer: QgsVectorLayer, name: str = 'Difference') -> QgsVectorLayer:
    splitted = processing.run('native:difference', {
        'INPUT': vector_layer,
        'OVERLAY': lines_layer,
        'OUTPUT': 'memory:%s' % name,
    })

    return splitted['OUTPUT']

def reproject(vector_layer: QgsVectorLayer, target_crs: str, name: str = 'Reprojected') -> QgsVectorLayer:
    reprojected = processing.run('qgis:reprojectlayer', {
        'INPUT': vector_layer,
        'TARGET_CRS': target_crs,
        'OUTPUT': 'memory:%s' % name,
    })

    return reprojected['OUTPUT']

def polyginize_lines(vector_layer: QgsVectorLayer, name: str = None) -> QgsVectorLayer:
    if name is None:
        name = 'PolygonizedLines'

    polygonizedResult = processing.run('qgis:polygonize', {
        'INPUT': vector_layer,
        'OUTPUT': 'memory:%s' % name,
    })

    return polygonizedResult['OUTPUT']


def delete_duplicate_geometries(vector_layer: QgsVectorLayer, name: str = 'PolygonizedLines') -> QgsVectorLayer:
    result = processing.run('qgis:deleteduplicategeometries', {
        'INPUT': vector_layer,
        'OUTPUT': 'memory:%s' % name,
    })

    return result['OUTPUT']

def extract_specific_vertices(vector_layer: QgsVectorLayer, vertices: str = '0', name: str = 'Vertices') -> QgsVectorLayer:
    verticesResult = processing.run('qgis:extractspecificvertices', {
        'INPUT': vector_layer,
        'VERTICES': vertices,
        'OUTPUT': 'memory:%s' % name,
    })

    return verticesResult['OUTPUT']

def lines_unique_vertices(vector_layer: QgsVectorLayer, feature_ids: typing.List[int] = None) -> typing.List[QgsPoint]:
    points: typing.Dict[QgsPoint, int] = defaultdict(int)
    features = vector_layer.getFeatures(feature_ids) if feature_ids else vector_layer.getFeatures()

    for f in features:
        geom = f.geometry()

        is_multipart = geom.isMultipart()

        if is_multipart:
            lines = geom.asMultiPolyline()
        else:
            lines = [geom.asPolyline()]

        for idx, line in enumerate(lines):
            startPoint = line[0]
            endPoint = line[-1]

            points[startPoint] += 1
            points[endPoint] += 1

        lines.append(f)

    return [k for k, v in points.items() if v == 1]

# get temporary directory
def get_tmp_path(filename: str = None) -> str:
    path = str(os.path.join(QDir.tempPath(), TMP_DIR))

    if not QDir(path).exists():
        os.makedirs(path)

    if str is not None:
        path = os.path.join(path, filename)

    return path

def utf8len(s: str) -> int:
    return len(s.encode('utf-8'))

def get_geojson(layer: QgsVectorLayer) -> dict:
    filename = get_tmp_path('final')
    error, msg = QgsVectorFileWriter.writeAsVectorFormat(layer, filename, 'utf-8', driverName='GeoJSON')

    if error != QgsVectorFileWriter.NoError:
        raise error

    with open(filename + '.geojson', 'r') as file:
        contents = file.read()

    geojson = json.loads(contents)

    return geojson

def load_geojson(geojson: dict, name: str = 'geojson') -> QgsVectorLayer:
    filename = get_tmp_path(name + '.geojson')

    with open(filename, 'w') as file:
        print(json.dumps(geojson), file=file)

    return QgsVectorLayer(filename, name, 'ogr')

class SelectionModes(Enum):
    NONE = 0
    MANUAL = 1
    ENCLOSING = 2
    NODES = 3
    LINES = 4
