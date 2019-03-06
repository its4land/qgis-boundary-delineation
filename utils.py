import functools
import collections.abc
import typing

from enum import Enum

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QColor
from PyQt5.QtWidgets import QApplication

import processing

from qgis.core import QgsProject, QgsMarkerSymbol, QgsLineSymbol, QgsSingleSymbolRenderer, QgsGraduatedSymbolRenderer, QgsLayerTreeNode, QgsVectorLayer, QgsRasterLayer, QgsMapLayer
from qgis.utils import iface


def processing_cursor(cursor=QCursor(Qt.WaitCursor)):
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

def show_processing_cursor(cursor=QCursor(Qt.WaitCursor)):
    QApplication.setOverrideCursor(cursor)
    QApplication.processEvents()

def hide_processing_cursor():
    QApplication.restoreOverrideCursor()
    QApplication.processEvents()

def remove_layer(layer):
    if not layer:
        return False

    QgsProject.instance().removeMapLayer(layer.id())
    iface.mapCanvas().refresh()

    return True

def move_tree_node(node: typing.Union[QgsMapLayer, QgsLayerTreeNode], index: int, parent: QgsLayerTreeNode = None):
    root = QgsProject.instance().layerTreeRoot()
    node = root.findLayer(node.id()) if isinstance(node, QgsMapLayer) else node

    if node is None:
        return None

    layer_clone = node.clone()
    parent = parent if parent else node.parent()
    parent.insertChildNode(index, layer_clone)
    parent.removeChildNode(node)

def get_tree_node_index(node: typing.Union[QgsMapLayer, QgsLayerTreeNode], top: bool = False):
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

    return None

def add_group(group: QgsLayerTreeNode, name: str = None, index: int = -1, parent: QgsLayerTreeNode = None):
    parent = parent if parent else QgsProject.instance().layerTreeRoot()
    parent.insertGroup(index, group)

def add_layer(layer: QgsMapLayer, name: str = None, index: int = -1, color: typing.List = None, size: float = None, file: str = None, parent: QgsLayerTreeNode = None) -> None:
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
    print('index', index, layer.name())
    parent.insertLayer(index, layer)

def update_symbology(layer, color=None, size=None, file: str = None) -> None:
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


def set_active_layer(layer):
    assert isinstance(layer, QgsVectorLayer)

    iface.setActiveLayer(layer)


def selected_features_to_layer(vectorLayer, name=None):
    if name is None:
        name = 'SelectedFeatures'

    result = processing.run('native:saveselectedfeatures', {
        'INPUT': vectorLayer,
        'OUTPUT': 'memory:%s' % name
    })

    return result['OUTPUT']

def dissolve_layer(vectorLayer, name=None):
    if name is None:
        name = 'DissolvedFeatures'

    result = processing.run('native:dissolve', {
        'INPUT': vectorLayer,
        'FIELD': [],
        'OUTPUT': 'memory:%s' % name,
    })

    return result['OUTPUT']

def polygons_layer_to_lines_layer(vectorLayer, name=None):
    if name is None:
        name = 'polygonstolines'

    result = processing.run('qgis:polygonstolines', {
        'INPUT': vectorLayer,
        'OUTPUT': 'memory:%s' % name,
    })

    return result['OUTPUT']

def lines_to_polygons(vectorLayer, name: str = None):
    if name is None:
        name = 'LinesToPolygons'

    result = processing.run('qgis:linestopolygons', {
        'INPUT': vectorLayer,
        'OUTPUT': 'memory:%s' % name,
    })

    return result['OUTPUT']

def multipart_to_singleparts(vectorLayer, name: str = None):
    if name is None:
        name = 'MultipartToSingleparts'

    result = processing.run('native:multiparttosingleparts', {
        'INPUT': vectorLayer,
        'OUTPUT': 'memory:%s' % name,
    })

    return result['OUTPUT']

class SelectionModes(Enum):
    NONE = 0
    MANUAL = 1
    ENCLOSING = 2
    NODES = 3


