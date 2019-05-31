import functools
import collections.abc
import typing
import os

from enum import Enum
from collections import defaultdict

from PyQt5.QtCore import Qt, QDir
from PyQt5.QtGui import QCursor, QColor
from PyQt5.QtWidgets import QApplication

import processing

from qgis.core import QgsProject, QgsMarkerSymbol, QgsLineSymbol, QgsSingleSymbolRenderer, QgsGraduatedSymbolRenderer, QgsLayerTreeNode, QgsVectorLayer, QgsRasterLayer, QgsMapLayer, QgsPoint
from qgis.utils import iface

TMP_DIR = 'boundarydeleniation'

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

def add_layer(layer: QgsMapLayer, name: str = None, index: int = -1, color: typing.Tuple[int, int, int] = None, size: float = None, file: str = None, parent: QgsLayerTreeNode = None) -> None:
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

    parent = parent if parent else instance.layerTreeRoot()
    parent.insertLayer(index, layer)

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

def polyginize_lines(vector_layer: QgsVectorLayer, name: str = None) -> QgsVectorLayer:
    if name is None:
        name = 'PolygonizedLines'

    polygonizedResult = processing.run('qgis:polygonize', {
        'INPUT': vector_layer,
        'OUTPUT': 'memory:%s' % name,
    })

    return polygonizedResult['OUTPUT']

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
def get_tmp_dir() -> str:
    tmpDir = str(os.path.join(QDir.tempPath(), TMP_DIR))

    if not QDir(tmpDir).exists():
        os.makedirs(tmpDir)

    return tmpDir

def utf8len(s):
    return len(s.encode('utf-8'))

class SelectionModes(Enum):
    NONE = 0
    MANUAL = 1
    ENCLOSING = 2
    NODES = 3
    LINES = 4
