# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DsgTools
                                 A QGIS plugin
 Brazilian Army Cartographic Production Tools
                              -------------------
        begin                : 2023-03-29
        git sha              : $Format:%H$
        copyright            : (C) 2023 by Philipe Borba - Cartographic Engineer @ Brazilian Army
        email                : borba.philipe@eb.mil.br
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
from collections import defaultdict
from enum import Enum
from itertools import tee
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from qgis.PyQt.QtCore import QByteArray
from itertools import chain
from itertools import product
import processing

from qgis.core import (
    QgsGeometry,
    QgsFeature,
    QgsProcessingMultiStepFeedback,
    QgsVectorLayer,
    QgsFeedback,
    QgsProcessingContext,
    QgsPointXY,
)



class GraphType(Enum):
    GRAPH = 0
    DIGRAPH = 1
    MULTIGRAPH = 2
    MULTIDIGRAPH = 3

def buildGraph(
    nx: Any,
    hashDict: Dict[int, List[QByteArray]],
    nodeDict: Dict[QByteArray, int],
    feedback: Optional[QgsFeedback] = None,
    graphType: GraphType = 0,
    add_inside_river_attribute: bool = True,
) -> Any:
    """
    Build a graph from hash dictionary and node dictionary.

    Args:
        nx: NetworkX library instance or module.
        hashDict: A dictionary mapping edge ID to a list with the wkbs of the first and the last nodes of the edge.
        nodeDict: A dictionary mapping node geometry to an auxiliary ID.
        feedback: An optional object for providing feedback during processing.
        directed: A boolean flag indicating whether the graph is directed.
                  Default is False (undirected graph).

    Returns:
        The constructed graph object.

    Notes:
        This function iterates over the hash dictionary and adds edges to the graph based on node geometry mappings.
        The graph can be either undirected or directed based on the value of the 'directed' parameter.
        The optional 'feedback' object can be used to monitor the progress of the function.

    """
    graphType = GraphType.GRAPH if graphType == 0 else graphType
    graphDict = {
        GraphType.GRAPH: nx.Graph,
        GraphType.DIGRAPH: nx.DiGraph,
        GraphType.MULTIGRAPH: nx.MultiGraph,
        GraphType.MULTIDIGRAPH: nx.MultiDiGraph,
    }
    graphObject = graphDict.get(graphType, None)
    if graphObject is None:
        raise NotImplementedError("Invalid graph type")
    G = graphObject()
    progressStep = 100 / len(hashDict) if len(hashDict) > 0 else 0
    for current, (edgeId, (wkb_1, wkb_2)) in enumerate(hashDict.items()):
        if feedback is not None and feedback.isCanceled():
            break
        if wkb_1 == [] or wkb_2 == []:
            continue
        if add_inside_river_attribute:
            G.add_edge(
                nodeDict[wkb_1], nodeDict[wkb_2], featid=edgeId, inside_river=False
            )
        else:
            G.add_edge(nodeDict[wkb_1], nodeDict[wkb_2], featid=edgeId)
        if feedback is not None:
            feedback.setProgress(current * progressStep)
    return G

def fetch_connected_nodes(
    G, node: int, max_degree: int, feedback: Optional[QgsFeedback] = None
) -> List[int]:
    """
    Fetch nodes connected to a given node within a maximum degree limit using a non-recursive approach.

    Args:
        G: The input graph.
        node: The starting node from which to fetch connected nodes.
        max_degree: The maximum degree allowed for connected nodes.
        feedback: An optional QgsFeedback object to provide feedback during processing.

    Returns:
        A list of nodes connected to the starting node within the maximum degree limit.

    Note:
        The function uses a non-recursive approach with a stack to traverse the graph and fetch nodes connected to the
        starting node. It only considers nodes with a degree less than or equal to the specified max_degree.

        If the feedback parameter is provided and the feedback object indicates cancellation,
        the function will stop the traversal and return the list of nodes found so far.

    """
    seen = [node]
    stack = [node]

    while stack:
        current_node = stack.pop()

        if feedback is not None and feedback.isCanceled():
            break

        for neighbor in G.neighbors(current_node):
            if G.degree(neighbor) <= max_degree and neighbor not in seen:
                seen.append(neighbor)
                stack.append(neighbor)

    return seen


def pairwise(iterable: Iterable) -> Iterable:
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def buildAuxStructures(
    nx: Any,
    nodesLayer: QgsVectorLayer,
    edgesLayer: QgsVectorLayer,
    feedback: Optional[QgsFeedback] = None,
    graphType: Optional[GraphType] = 0,
    useWkt: Optional[bool] = False,
    computeNodeLayerIdDict: Optional[bool] = False,
) -> Tuple[
    Dict[QByteArray, int],
    Dict[int, QByteArray],
    Dict[int, QgsFeature],
    Dict[int, Dict[int, QByteArray]],
    Any,
]:
    """
    Build auxiliary data structures for network analysis.

    Args:
        nx: A NetworkX library instance or module.
        nodesLayer: A QgsVectorLayer representing the nodes in the network.
        edgesLayer: A QgsVectorLayer representing the edges in the network.
        feedback: An optional QgsFeedback object to provide feedback during processing.
        graphType: An optional enum flag indicating whether the network is directed.
                  Default is GraphType.GRAPH = 0 (undirected network).
        useWkt: An optional boolean flag indicating whether to use Well-Known Text (WKT)
                representation for node geometries. Default is False (use WKB representation).
        computeNodeLayerIdDict: An optional boolean flag indicating whether to compute
                                a dictionary mapping node layer ID to auxiliary ID.
                                Default is False.
        addEdgeLength: An optional boolean flag that adds the segment length to the graph.
    Returns:
        A tuple containing the following auxiliary data structures:
        - nodeDict: A dictionary mapping node geometry to an auxiliary ID.
        - nodeIdDict: A dictionary mapping auxiliary ID to node geometry.
        - edgeDict: A dictionary mapping edge feature ID to edge feature.
        - hashDict: A dictionary mapping node feature ID and vertex position to node geometry.
        - networkBidirectionalGraph: A NetworkX graph representing the network.

    Notes:
        This function builds auxiliary data structures by iterating over the nodesLayer and edgesLayer.
        It assigns unique IDs to nodes, maps node geometries to IDs, and stores edge features and node geometries
        in corresponding dictionaries. It also constructs a bidirectional graph representation of the network
        using the provided NetworkX library or module.

        The feedback argument can be used to monitor the progress of the function if a QgsFeedback object is provided.

        By default, the function uses the Well-Known Binary (WKB) representation for node geometries.
        If the useWkt parameter is set to True, the function will use Well-Known Text (WKT) representation instead.
    """
    multiStepFeedback = (
        QgsProcessingMultiStepFeedback(3, feedback) if feedback is not None else None
    )
    if multiStepFeedback is not None:
        multiStepFeedback.setCurrentStep(0)
    edgeDict = {feat["featid"]: feat for feat in edgesLayer.getFeatures()}
    if multiStepFeedback is not None:
        multiStepFeedback.setCurrentStep(1)
    nodeDict = defaultdict(list)
    nodeIdDict = defaultdict(list)
    nodeCount = nodesLayer.featureCount()
    stepSize = 100 / nodeCount if nodeCount > 0 else 0
    auxId = 0
    nodeLayerIdDict = dict()
    for current, nodeFeat in enumerate(nodesLayer.getFeatures()):
        if multiStepFeedback is not None and multiStepFeedback.isCanceled():
            break
        geom = nodeFeat.geometry()
        geomKey = geom.asWkb() if not useWkt else geom.asWkt()
        if geomKey not in nodeDict:
            nodeDict[geomKey] = auxId
            nodeIdDict[auxId] = geomKey
            auxId += 1
        if computeNodeLayerIdDict:
            nodeLayerIdDict[nodeFeat["nfeatid"]] = geomKey

    if multiStepFeedback is not None:
        multiStepFeedback.setCurrentStep(2)
    G = buildGraph(
        nx, nodeDict, feedback=multiStepFeedback, graphType=graphType
    )

    return (
        (nodeDict, nodeIdDict, edgeDict, G)
        if not computeNodeLayerIdDict
        else (
            nodeDict,
            nodeIdDict,
            edgeDict,
            G,
            nodeLayerIdDict,
        )
    )

def buildAuxLayersPriorGraphBuilding(
    networkLayer,
    context=None,
    geographicBoundsLayer=None,
    feedback=None,
    clipOnGeographicBounds=False,
    idFieldName=None,
):
    nSteps = 6 if geographicBoundsLayer is not None else 4
    multiStepFeedback = (
        QgsProcessingMultiStepFeedback(nSteps, feedback)
        if feedback is not None
        else None
    )
    context = QgsProcessingContext() if context is None else context
    currentStep = 0
    if multiStepFeedback is not None:
        multiStepFeedback.setCurrentStep(currentStep)
    localCache = runCreateFieldWithExpression(
        inputLyr=networkLayer,
        expression="$id",
        fieldName="featid" if idFieldName is None else idFieldName,
        fieldType=1,
        context=context,
        feedback=multiStepFeedback,
    )
    currentStep += 1
    if geographicBoundsLayer is not None:
        if multiStepFeedback is not None:
            multiStepFeedback.setCurrentStep(currentStep)
        runCreateSpatialIndex(
            inputLyr=localCache,
            context=context,
            feedback=multiStepFeedback,
            is_child_algorithm=True,
        )
        currentStep += 1
        if multiStepFeedback is not None:
            multiStepFeedback.setCurrentStep(currentStep)
        localCache = (
            runExtractByLocation(
                inputLyr=localCache,
                intersectLyr=geographicBoundsLayer,
                context=context,
                feedback=multiStepFeedback,
            )
            if not clipOnGeographicBounds
            else runClip(
                inputLayer=localCache,
                overlayLayer=geographicBoundsLayer,
                context=context,
                feedback=multiStepFeedback,
            )
        )
        currentStep += 1
    if multiStepFeedback is not None:
        multiStepFeedback.setCurrentStep(currentStep)
    runCreateSpatialIndex(
        inputLyr=localCache,
        context=context,
        feedback=multiStepFeedback,
        is_child_algorithm=True,
    )
    currentStep += 1
    if multiStepFeedback is not None:
        multiStepFeedback.setCurrentStep(currentStep)
    nodesLayer = runExtractSpecificVertices(
        inputLyr=localCache,
        vertices="0,-1",
        context=context,
        feedback=multiStepFeedback,
    )
    currentStep += 1
    if multiStepFeedback is not None:
        multiStepFeedback.setCurrentStep(currentStep)
    nodesLayer = runCreateFieldWithExpression(
        inputLyr=nodesLayer,
        expression="$id",
        fieldName="nfeatid" if idFieldName is None else f"n{idFieldName}",
        fieldType=1,
        context=context,
        feedback=multiStepFeedback,
    )
    return localCache, nodesLayer

def build_graph_with_photo_ids(
        nx,
        linesLyr: QgsVectorLayer,
        photosNodeLyr: QgsVectorLayer,
        photoIdField: str,
        graphType: GraphType = 0,
        feedback: Optional[QgsFeedback] = None,
):
    multiStepFeedback = QgsProcessingMultiStepFeedback(2, feedback) if feedback is not None else None
    nodesHashDict = dict()
    graphType = GraphType.GRAPH if graphType == 0 else graphType
    graphDict = {
        GraphType.GRAPH: nx.Graph,
        GraphType.DIGRAPH: nx.DiGraph,
        GraphType.MULTIGRAPH: nx.MultiGraph,
        GraphType.MULTIDIGRAPH: nx.MultiDiGraph,
    }
    graphObject = graphDict.get(graphType, None)
    if graphObject is None:
        raise NotImplementedError("Invalid graph type")
    G = graphObject()

    if multiStepFeedback is not None:
        multiStepFeedback.setCurrentStep(0)
    nSteps = photosNodeLyr.featureCount()
    stepSize = 100 / nSteps
    for current, feat in enumerate(photosNodeLyr.getFeatures()):
        if multiStepFeedback is not None and multiStepFeedback.isCanceled():
            break
        geom = feat.geometry()
        geomKey = geom.asWkb()
        nodesHashDict[geomKey] = feat[photoIdField]
        if multiStepFeedback is not None:
            multiStepFeedback.setProgress(current * stepSize)
    
    
    nSteps = linesLyr.featureCount()
    progressStep = 100 / nSteps if nSteps > 0 else 0

    for current, feat in enumerate(linesLyr.getFeatures()):
        if multiStepFeedback is not None and multiStepFeedback.isCanceled():
            break
        geom = feat.geometry()
        for node1, node2 in pairwise(geom.vertices()):
            node1 = QgsPointXY(node1)
            node2 = QgsPointXY(node2)
            geom1 = QgsGeometry.fromPointXY(node1)
            geom2 = QgsGeometry.fromPointXY(node2)
            if geom1.asWkb() not in nodesHashDict or geom2.asWkb() not in nodesHashDict:
                raise ValueError("Vertice da linha não é coincidente com ponto")
            G.add_edge(nodesHashDict[geom1.asWkb()], nodesHashDict[geom2.asWkb()])
        if multiStepFeedback is not None:
            multiStepFeedback.setProgress(current * progressStep)
    return G


def get_neighbors(G, photoId: int):
    return [node for node in G.neighbors(photoId)]

def runCreateSpatialIndex(
        inputLyr, context, feedback=None, is_child_algorithm=True
    ):
    processing.run(
        "native:createspatialindex",
        {"INPUT": inputLyr},
        feedback=feedback,
        context=context,
        is_child_algorithm=is_child_algorithm,
    )
    return None

def runCreateFieldWithExpression(
        inputLyr,
        expression,
        fieldName,
        context,
        fieldType=0,
        fieldLength=1000,
        fieldPrecision=0,
        feedback=None,
        outputLyr=None,
        is_child_algorithm=False,
    ):
    outputLyr = "memory:" if outputLyr is None else outputLyr
    output = processing.run(
        "native:fieldcalculator",
        {
            "INPUT": inputLyr,
            "FIELD_NAME": fieldName,
            "FIELD_TYPE": fieldType,
            "FIELD_LENGTH": fieldLength,
            "FORMULA": expression,
            "OUTPUT": outputLyr,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=is_child_algorithm,
    )
    return output["OUTPUT"]

def runExtractByLocation(
        inputLyr,
        intersectLyr,
        context,
        predicate=None,
        feedback=None,
        outputLyr=None,
        is_child_algorithm=False,
    ):
    predicate = [0] if predicate is None else predicate
    outputLyr = "memory:" if outputLyr is None else outputLyr
    output = processing.run(
        "native:extractbylocation",
        {
            "INPUT": inputLyr,
            "INTERSECT": intersectLyr,
            "PREDICATE": predicate,
            "OUTPUT": outputLyr,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=is_child_algorithm,
    )
    return output["OUTPUT"]

def runClip(
        inputLayer,
        overlayLayer,
        context,
        feedback=None,
        outputLyr=None,
        is_child_algorithm=False,
    ):
    outputLyr = "memory:" if outputLyr is None else outputLyr
    parameters = {"INPUT": inputLayer, "OVERLAY": overlayLayer, "OUTPUT": outputLyr}
    output = processing.run(
        "native:clip",
        parameters,
        context=context,
        feedback=feedback,
        is_child_algorithm=is_child_algorithm,
    )
    return output["OUTPUT"]

def runExtractSpecificVertices(
        inputLyr, vertices, context, feedback=None, outputLyr=None, is_child_algorithm=False,
    ):
    outputLyr = "memory:" if outputLyr is None else outputLyr
    output = processing.run(
        "native:extractspecificvertices",
        {
            "INPUT": inputLyr,
            "VERTICES": vertices,
            "OUTPUT": outputLyr,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=is_child_algorithm,
    )
    return output["OUTPUT"]

def runBuffer(
        inputLayer,
        distance,
        context,
        dissolve=False,
        endCapStyle=None,
        joinStyle=None,
        segments=None,
        mitterLimit=None,
        feedback=None,
        outputLyr=None,
        is_child_algorithm=False,
    ):
    endCapStyle = 0 if endCapStyle is None else endCapStyle
    joinStyle = 0 if joinStyle is None else joinStyle
    segments = 5 if segments is None else segments
    mitterLimit = 2 if mitterLimit is None else mitterLimit
    outputLyr = "memory:" if outputLyr is None else outputLyr
    parameters = {
        "INPUT": inputLayer,
        "DISTANCE": distance,
        "DISSOLVE": dissolve,
        "END_CAP_STYLE": endCapStyle,
        "JOIN_STYLE": endCapStyle,
        "SEGMENTS": segments,
        "MITER_LIMIT": mitterLimit,
        "OUTPUT": outputLyr,
    }
    output = processing.run(
        "native:buffer",
        parameters,
        context=context,
        feedback=feedback,
        is_child_algorithm=is_child_algorithm,
    )
    return output["OUTPUT"]
