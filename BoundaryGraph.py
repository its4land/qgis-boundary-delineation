import os
import sys

LOCAL_NETWORKX_PATH = os.path.join(os.path.dirname(__file__) + '/lib/networkx')

if LOCAL_NETWORKX_PATH not in sys.path:
    sys.path.insert(0, LOCAL_NETWORKX_PATH)

import networkx as nx
from networkx.algorithms.approximation.steinertree import steiner_tree, metric_closure
from qgis.core import QgsWkbTypes
from collections.abc import Collection
from typing import Collection as CollectionT
from pprint import pprint

class BoundaryDelineationError(Exception):
    pass

class NoSuitableGraphError(BoundaryDelineationError):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


def prepare_graph_from_lines(layer, weight_expr_str=None):
    if layer.geometryType() != QgsWkbTypes.LineGeometry:
        raise Exception('Only line layers are accepted')

    G = nx.MultiGraph()

    weight_expr = None

    if weight_expr_str:
        weight_expr = QgsExpression(weight_expr_str)

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
            # due to buggy behaviour, weight should never be None (for now)
            weight = 1
            fid = f.id()

            if is_multipart:
                fid = (fid, idx)

            if weight_expr:
                weight = expression.evaluate(f)

            G.add_edge(startPoint, endPoint, fid, weight=weight, length=geom.length())

    return G

def prepare_subgraphs(G):
    return tuple(nx.connected_component_subgraphs(G))

def find_steiner_tree(graphs:CollectionT, terminal_nodes:CollectionT, metric_closures=None):
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


def calculate_subgraphs_metric_closures(graphs:CollectionT):
    metric_closures = []

    for g in graphs:
        metric_closures.append(metric_closure(g))

    return metric_closures

def printGraph(G, keysOnly=False):
    edges = G.edges(data=True,keys=True)

    if keysOnly:
        pprint(e[2] for e in edges)
    else:
        pprint(edges)





