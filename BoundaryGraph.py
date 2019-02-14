import os
import sys

LOCAL_NETWORKX_PATH = os.path.join(os.path.dirname(__file__) + '/lib/networkx')

if LOCAL_NETWORKX_PATH not in sys.path:
    sys.path.insert(0, LOCAL_NETWORKX_PATH)

import networkx as nx
from networkx.algorithms.approximation.steinertree import steiner_tree
from qgis.core import QgsWkbTypes
from collections.abc import Collection
from typing import Collection as CollectionT
from pprint import pprint

class BoundaryDelineationError(Exception):
    pass

class NoResultsGraphError(BoundaryDelineationError):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


def prepareLinesGraph(layer, weight_expr_str=None):
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

def prepareSubgraphs(G):
    return tuple(nx.connected_component_subgraphs(G))

def steinerTree(graphs:CollectionT, terminal_nodes:CollectionT):
    terminal_graph = None

    for g in graphs:
        # print('terminals', printGraph(g))
        # print('terminals', terminal_nodes[0], terminal_nodes[0] in g, nx.is_connected(g))
        if not all(node in g for node in terminal_nodes):
            continue

        terminal_graph = g

    if not terminal_graph:
        raise NoSuitableGraphError()

    T = steiner_tree(terminal_graph, terminal_nodes)

    return T

# TODO I think it would be much easier if I just don't have any multipart geometries
def getFeaturesFromSteinerTree(layer, steinerTree):
    edges = steinerTree.edges(keys=True)
    edgeKeys = map(lambda e: e[2], edges)
    featureIds = edgeKeys

    if isinstance(edgeKeys[0], Collection):
        featureIds = map(lambda e: e[0], edgeKeys)

    features = layer.getFeatures(featureIds)

    return features

def printGraph(G, keysOnly=False):
    edges = G.edges(data=True,keys=True)

    if keysOnly:
        pprint(e[2] for e in edges)
    else:
        pprint(edges)





