import os
import sys
import typing

LOCAL_NETWORKX_PATH = os.path.join(os.path.dirname(__file__) + '/lib')

if LOCAL_NETWORKX_PATH not in sys.path:
    sys.path.insert(0, LOCAL_NETWORKX_PATH)

import networkx as nx
from networkx.algorithms.approximation.steinertree import steiner_tree, metric_closure
from qgis.core import QgsWkbTypes
from collections.abc import Collection
from typing import Collection as CollectionT

DEFAULT_WEIGHT_NAME = 'weight'
DEFAULT_WEIGHT_VALUE = 1

class BoundaryDelineationError(Exception):
    pass

class NoSuitableGraphError(BoundaryDelineationError):
    def __init__(self, expression: str = None, message: str = None):
        self.expression = expression
        self.message = message


def prepare_graph_from_lines(layer, weight_expr_str: str = None) -> nx.MultiGraph:
    if layer.geometryType() != QgsWkbTypes.LineGeometry:
        raise Exception('Only line layers are accepted')

    G = nx.MultiGraph()

    weight_expr = None

    if weight_expr_str:
        weight_expr = QgsExpression(weight_expr_str)

    numeric_fields_names = []

    for field in layer.fields():
        if field.isNumeric():
            numeric_fields_names.append(field.name())

    for f in layer.getFeatures():
        geom = f.geometry()
        is_multipart = geom.isMultipart()

        if is_multipart:
            lines = geom.asMultiPolyline()
        else:
            lines = [geom.asPolyline()]

        for idx, line in enumerate(lines):
            startPoint = line[0]
            endPoint = line[-1]
            fid = f.id()

            if is_multipart:
                fid = (fid, idx)

            # due to buggy behaviour, weight should never be None (for now)
            data = { DEFAULT_WEIGHT_NAME: DEFAULT_WEIGHT_VALUE }

            if weight_expr:
                expression.evaluate(f)
                data[weight_expr_str] = res if res is not None else DEFAULT_WEIGHT_VALUE

            for field_name in numeric_fields_names:
                data[field_name] = 1 / f[field_name] if f[field_name] else f[field_name] or DEFAULT_WEIGHT_VALUE

            G.add_edge(startPoint, endPoint, fid, **data)

    return G

def prepare_subgraphs(G: nx.MultiGraph) -> tuple:
    return tuple(nx.connected_component_subgraphs(G))

def find_steiner_tree(graphs: CollectionT, terminal_nodes: CollectionT, metric_closures: typing.List[nx.Graph] = None) -> nx.Graph:
    terminal_graph = None
    terminal_metric_closure = None

    for idx, g in enumerate(graphs):
        if not all(node in g for node in terminal_nodes):
            continue

        terminal_graph = g
        terminal_metric_closure = metric_closures[idx] if metric_closures else None

    if not terminal_graph:
        raise NoSuitableGraphError()


    T = steiner_tree(terminal_graph, terminal_nodes, metric_closure=terminal_metric_closure)

    return T


def calculate_subgraphs_metric_closures(graphs: CollectionT, weight: str = None) -> typing.List[nx.Graph]:
    metric_closures = []

    for g in graphs:
        metric_closures.append(metric_closure(g, weight=weight))

    return metric_closures
