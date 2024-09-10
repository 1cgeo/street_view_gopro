import pandas as pd
import numpy as np
from datetime import datetime
import math
from qgis.core import *
from itertools import chain
import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import re
import copy
import json
import glob
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor
import processing
import random

class ProcessPointsAndLines:


    def process(self, pointsLayer, linesLayer, distance):
        print(distance)
        processedPoints = self.snapGeometries(pointsLayer, linesLayer, distance)
        processedLines = self.snapGeometries(linesLayer, processedPoints, 0.000001) # distancia pequena para criar vertice nos pontos processados
        self.deleteVertexNotOnPoint(processedPoints, processedLines)
        self.stylePointLayer(processedPoints)
        self.styleLineLayer(processedLines)

    
    def snapGeometries(self, layer1, layer2, distance, outputLyr=None, context=None, feedback=None, is_child_algorithm=False):
        outputLyr = "memory:" if outputLyr is None else outputLyr
        output = processing.run(
            "native:snapgeometries",
            {
                "INPUT": layer1,
                "REFERENCE_LAYER": layer2,
                "TOLERANCE": distance,
                "BEHAVIOR": 1, # Prefer aligning nodes, insert extra vertices when required
                "OUTPUT": outputLyr,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=is_child_algorithm,
        )       
        return output["OUTPUT"]
    
    def deleteVertexNotOnPoint(self, pointsLayer:QgsVectorLayer, linesLayer:QgsVectorLayer, removeEmptyGeom = False):
        geomPointsAsWkbSet = set()
        print('aqui')
        linesLayer.startEditing()
        for point in pointsLayer.getFeatures():
            geomPoint = point.geometry()
            geomPointsAsWkbSet.add(geomPoint.asWkb())
        for line in linesLayer.getFeatures():
            geomLine = line.geometry()
            deletedCount = 0
            for index, vertex in enumerate(geomLine.vertices()):
                vertex = QgsPointXY(vertex)
                geomVertex = QgsGeometry.fromPointXY(vertex)
                if geomVertex.asWkb() in geomPointsAsWkbSet:
                    continue
                geomLine.deleteVertex(index-deletedCount) # depois de deletar um vertice, a contagem do index continua, mas a posicao dos próximos vertices muda
                deletedCount += 1
            if geomLine.isEmpty() and not removeEmptyGeom:
                raise 'Geometria Vazia, não será alterada'
            else:
                print(f'atualizando linha {deletedCount}')
                line.setGeometry(geomLine)
                linesLayer.updateFeature(line)
    def buildFillStyle(self, count):
        fills = []
        for _ in range(count):
            layer_style = {}
            layer_style['color'] = '%d, %d, %d' % (random.randrange(0, 256), random.randrange(0, 256), random.randrange(0, 256))
            layer_style['outline'] = '#000000'
            fills.append( QgsSimpleFillSymbolLayer.create(layer_style) )
        return fills

    def stylePointLayer(self, pointLayer:QgsVectorLayer):
        pointLayer.startEditing()
        pointLayer.setName('Pontos Processados')
        pointLayer.commitChanges()
        QgsProject().instance().addMapLayer(pointLayer)
        fni = pointLayer.dataProvider().fieldNameIndex('faixa_img')
        uniqueValues = pointLayer.uniqueValues(fni)
        fills = self.buildFillStyle( len(uniqueValues) )
        categories = []
        for idx, uniqueValue in enumerate(uniqueValues):
            symbol = QgsSymbol.defaultSymbol(pointLayer.geometryType())
            symbolLayer = fills[idx]
            if symbolLayer is not None:
                symbol.changeSymbolLayer(0, symbolLayer)
            category = QgsRendererCategory(uniqueValue, symbol, str(uniqueValue))
            categories.append(category)
        renderer = QgsCategorizedSymbolRenderer('faixa_img', categories)
        if renderer is not None:
            pointLayer.setRenderer(renderer)
        pointLayer.triggerRepaint()

    def random_color(self):
        return '#{:06x}'.format(random.randint(0, 0xFFFFFF))

    def buildLineStyle(self, count):
        lines = []
        for _ in range(count):
            layer_style = {}
            layer_style['color'] = '%d, %d, %d' % (random.randrange(0, 256), random.randrange(0, 256), random.randrange(0, 256))
            layer_style['width'] = '1'
            lines.append( QgsSimpleLineSymbolLayer.create(layer_style) )
        return lines
    
    def styleLineLayer(self, lineLayer:QgsVectorLayer, fieldName="faixa_img", width=1.0):
        if not lineLayer:
            return
        else:
            lineLayer.startEditing()
            lineLayer.setName('Linhas Processadas')
            lineLayer.commitChanges()
            QgsProject.instance().addMapLayer(lineLayer)
            # Obter os valores únicos do atributo
            fni = lineLayer.dataProvider().fieldNameIndex(fieldName)
            unique_values = lineLayer.uniqueValues(fni)
            lineStyle = self.buildLineStyle( len(unique_values) )
            
            # Criar as categorias
            categories = []
            symbolLine = QgsSymbol.defaultSymbol(lineLayer.geometryType())
            if symbolLine is None:
                color = self.random_color()
                symbolLine = QgsLineSymbol.createSimple({'color': color.name(), 'width': str(width)})
            if symbolLine.symbolLayer(0):
                symbolLine.symbolLayer(0).setWidth(width)
            
            for idx, value in enumerate(unique_values):
                symbolLayer = lineStyle[idx]
                if symbolLayer is not None:
                    symbolLine.changeSymbolLayer(0, symbolLayer)
                    symbolLine2 = QgsLineSymbol.createSimple({'color': self.random_color(), 'width': '1'})
                
                    categoryLine = QgsRendererCategory()
                    categoryLine.setValue(value)
                    categoryLine.setSymbol(symbolLine2)
                    categoryLine.setLabel(str(value))
                    categories.append(categoryLine)
            
            # Criar o renderizador categorizado
            renderer = QgsCategorizedSymbolRenderer(fieldName, categories)
            
            # Aplicar o renderizador à camada
            if renderer is not None:
                lineLayer.setRenderer(renderer)
            
            # Atualizar a exibição da camada
            lineLayer.triggerRepaint()

