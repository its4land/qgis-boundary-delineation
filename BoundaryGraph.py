import networkx as nx
from networkx.algorithms.approximation.steinertree import steiner_tree
import qgis.core.QgsWkbTypes as QgsWkbTypes
from collections.abc import Collection
from typing import Collection as CollectionT

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
            weight = None
            fid = f.id()

            if is_multipart:
                fid = (fid, idx)

            if weight_expr:
                weight = expression.evaluate(f)

            G.add_edge(startPoint, endPoint, fid, weight=weight, length=geom.length())

    return G

terminal_nodes = [2, 4, 5]
connected_subgraphs = tuple(nx.connected_component_subgraphs(G))

def getSteinerTree(graphs:CollectionT, terminal_nodes:CollectionT):
    terminal_graph = None

    for g in graphs:
        if not all(node in g for node in terminal_nodes):
            continue

        terminal_graph = g

    if not terminal_graph:
        raise Exception('No suitable graph found!')

    T = steiner_tree(G, terminal_nodes)

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







