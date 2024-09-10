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

class BuildStruct:
    
    def getExif(self, filename):
        exif = Image.open(filename)._getexif()
        info = {}
        if exif is not None:
            items = list(exif.items())
            for key, value in items:
                name = TAGS.get(key, key)
                info[name] = exif[key]

            if 'GPSInfo' in info:
                for key in list(info['GPSInfo'].keys()):
                    name = GPSTAGS.get(key,key)
                    info['GPSInfo'][name] = info['GPSInfo'][key]
        return info

    def getCoordinates(self, info):
        for key in ['Latitude', 'Longitude', 'Altitude']:
            if key == 'Altitude' and 'GPS'+key in info:
                info[key] = float(info['GPS'+key])
            elif 'GPS'+key in info and 'GPS'+key+'Ref' in info:
                deg, minutes, seconds = info['GPS'+key]
                direction = info['GPS'+key+'Ref']
                info[key] = self.gms2degrees(deg, minutes, seconds, direction)
        if 'Latitude' in info and 'Longitude' in info and 'Altitude' in info:
            return [info['Longitude'], info['Latitude'],  info['Altitude']]

    def gms2degrees(self, deg, minutes, seconds, direction):
        return (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)
            
    def loadImagesDataset(self, imagesFolderPath):
        imagesDF = pd.DataFrame(columns=['faixa','numero','nome','time','long','lat','ele'])
        for idx, filename in enumerate(os.listdir(imagesFolderPath)):
            if not('.jpg' in filename):
                continue
            exif = self.getExif(os.path.join(imagesFolderPath, filename))
            lon, lat, ele = self.getCoordinates(exif['GPSInfo'])
            year, month, day = exif['GPSInfo']['GPSDateStamp'].split(':')
            hour, minute, second = exif['GPSInfo']['GPSTimeStamp']
            imagesDF.loc[idx] = [
                int(filename.split('.')[0].split('_')[-2]),
                int(filename.split('.')[0].split('_')[-1]),
                filename.split('.')[0],
                datetime(int(year), int(month), int(day), int(hour), int(minute), int(second)).timestamp(),
                lon,
                lat,
                ele
            ]
        imagesDF["time"] = imagesDF["time"].apply(int)
        return imagesDF

    def removeDuplicatePoints(self, points):
        if points.empty:
            print('empty')
        grouped = points.groupby(['long_img','lat_img'])
        if grouped.ngroups == 0:
            print('ngroups')
        print(points)
        tamanho_points = points.shape[0]
        points_cleaned  = points.drop_duplicates(subset=['long_img', 'lat_img'], keep='first')
        print('----------------------')
        print(points_cleaned )
        tamanho_points_cleaned = points_cleaned.shape[0]

        print(tamanho_points, tamanho_points_cleaned)
        return points_cleaned 

    def removeDuplicateLinesV2(self, dataset):
        points = []
        deleteImages = {}
        groupSorted = dataset.sort_values(['faixa_img', 'numero_img'])
        
        for idxA, rowA in groupSorted.iterrows():
            if rowA['faixa_img'] in deleteImages and rowA['numero_img'] in deleteImages[rowA['faixa_img']]:
                continue
            points.append(rowA.to_list())
            buffer = QgsGeometry.fromPointXY( QgsPointXY(rowA['long_img'], rowA['lat_img']) ).buffer(0.00010, 5)
            for idxB, rowB in groupSorted.iterrows():
                if idxB <= idxA:
                    continue
                geomB = QgsGeometry.fromPointXY( QgsPointXY(rowB['long_img'], rowB['lat_img']) )
                if not(buffer.intersects(geomB) and abs(rowA["time_img"] - rowB["time_img"]) > 5):
                    continue
                if not(rowB['faixa_img'] in deleteImages):
                    deleteImages[rowB['faixa_img']] = []
                deleteImages[rowB['faixa_img']].append(rowB['numero_img'])
        return pd.DataFrame(points, columns=[name for name in dataset.columns.to_list()])

    def removeDuplicateLines(self, dataset):
        deleteImages = {}
        groupSorted = dataset.sort_values(['faixa_img', 'numero_img'])
        for idxA, rowA in groupSorted.iterrows():
            buffer = QgsGeometry.fromPointXY( QgsPointXY(rowA['long_img'], rowA['lat_img']) ).buffer(0.00010, 5)
            for idxB, rowB in groupSorted.iterrows():
                if idxB <= idxA:
                    continue
                geomB = QgsGeometry.fromPointXY( QgsPointXY(rowB['long_img'], rowB['lat_img']) )
                if not(buffer.intersects(geomB) and abs(rowA["time_img"] - rowB["time_img"]) > 5):
                    continue
                if not(rowB['faixa_img'] in deleteImages):
                    deleteImages[rowB['faixa_img']] = []
                deleteImages[rowB['faixa_img']].append(rowB['numero_img'])
        points = []
        for idxA, rowA in groupSorted.iterrows():
            if rowA['faixa_img'] in deleteImages and rowA['numero_img'] in deleteImages[rowA['faixa_img']]:
                continue
            points.append(rowA.to_list())
        return pd.DataFrame(points, columns=[name for name in dataset.columns.to_list()])

    def distance(self, point1, point2):
        distance = QgsDistanceArea()
        distance.setEllipsoid('WGS84')
        return distance.measureLine(point1, point2)

    def createLines(self, dataset):
        lineIdx = 0
        datasetSorted = dataset.sort_values(['time_img'])
        datasetSorted = datasetSorted.reset_index()
        for currentRow, nextRow in zip(datasetSorted.iterrows(), datasetSorted.iloc[1:].iterrows()):
            currentGeom = QgsGeometry.fromPointXY( QgsPointXY(currentRow[1]['long_img'], currentRow[1]['lat_img']) )
            datasetSorted.loc[datasetSorted['nome_img'] == currentRow[1]['nome_img'], 'faixa_img'] = lineIdx
            nextGeom = QgsGeometry.fromPointXY( QgsPointXY(nextRow[1]['long_img'], nextRow[1]['lat_img']) )
            if not(self.distance(currentGeom.asPoint(), nextGeom.asPoint()) > 40):
                continue
            lineIdx += 1
        byRange = datasetSorted.groupby('faixa_img').aggregate(np.count_nonzero)
        ranges = byRange[byRange['numero_img'] >= 2].index
        return datasetSorted[datasetSorted['faixa_img'].isin(ranges)]

    def removeNearPoints(self, dataset, groupSorted):
        lines2 = []
        for currentLine in dataset:
            line = []
            lastIdx = 0
            for i in range(0, len(currentLine)):
                if i < lastIdx:
                    continue
                geomA = currentLine[i]   
                if i == 0:
                    line.append(geomA)    
                for j in range(i, len(currentLine)): 
                    if j <= i:
                        continue
                    geomB = currentLine[j]
                    if self.distance(geomA.asPoint(), geomB.asPoint())  <= 5:
                        continue
                    line.append(geomB)
                    lastIdx = j
                    break
            lines2.append(line)
        photosFinal = []
        for idx, line in enumerate(lines2):
            for p in line:
                found = groupSorted[
                    (groupSorted['long_img']==p.asPoint().x() )
                    &
                    (groupSorted['lat_img']==p.asPoint().y() )
                ]
                found['faixa_img'] = idx
                photosFinal.append(found.iloc[0].to_list())
        return pd.DataFrame(photosFinal, columns=[name for name in groupSorted.columns.to_list()])


    def getStructPath(self):
        return os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 
            '..',
            'tmp',
            'STRUCT.csv'
        )

    def buildFillStyle(self, count):
        fills = []
        for _ in range(count):
            layer_style = {}
            layer_style['color'] = '%d, %d, %d' % (random.randrange(0, 256), random.randrange(0, 256), random.randrange(0, 256))
            layer_style['outline'] = '#000000'
            fills.append( QgsSimpleFillSymbolLayer.create(layer_style) )
        return fills

    def loadCSVLayer(self):
        uri = "file:///{}?type='csv&maxFields=10000&detectTypes=yes&xField=long_img&yField=lat_img&crs=EPSG:4326&spatialIndex=no&subsetIndex=no&watchFile=no'".format(
            self.getStructPath()
        )
        layer = QgsVectorLayer(uri, 'estrutura', 'delimitedtext')
        QgsProject().instance().addMapLayer(layer)
        fni = layer.dataProvider().fieldNameIndex('faixa_img')
        uniqueValues = layer.uniqueValues(fni)
        fills = self.buildFillStyle( len(uniqueValues) )
        categories = []
        for idx, uniqueValue in enumerate(uniqueValues):
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            symbolLayer = fills[idx]
            if symbolLayer is not None:
                symbol.changeSymbolLayer(0, symbolLayer)
            category = QgsRendererCategory(uniqueValue, symbol, str(uniqueValue))
            categories.append(category)
        renderer = QgsCategorizedSymbolRenderer('faixa_img', categories)
        if renderer is not None:
            layer.setRenderer(renderer)
        layer.triggerRepaint()

    def removeNearPoints(self, dataset):
        points = []
        deleteImages = {}
        groupSorted = dataset.sort_values(['faixa_img', 'numero_img'])
        
        for idxA, rowA in groupSorted.iterrows():
            if rowA['faixa_img'] in deleteImages and rowA['numero_img'] in deleteImages[rowA['faixa_img']]:
                continue
            points.append(rowA.to_list())
            buffer = QgsGeometry.fromPointXY( QgsPointXY(rowA['long_img'], rowA['lat_img']) ).buffer(0.00010, 5)
            for idxB, rowB in groupSorted.iterrows():
                if idxB <= idxA:
                    continue
                geomB = QgsGeometry.fromPointXY( QgsPointXY(rowB['long_img'], rowB['lat_img']) )
                if not(buffer.intersects(geomB)):
                    continue
                if not(rowB['faixa_img'] in deleteImages):
                    deleteImages[rowB['faixa_img']] = []
                deleteImages[rowB['faixa_img']].append(rowB['numero_img'])
        return pd.DataFrame(points, columns=[name for name in dataset.columns.to_list()])
    
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
    
    def styleLineLayer(self, layer:QgsVectorLayer, fieldName="faixa_img", width=1.0):
        if not layer:
            return
        else:
            
            # Obter os valores únicos do atributo
            fni = layer.dataProvider().fieldNameIndex(fieldName)
            unique_values = layer.uniqueValues(fni)
            lineStyle = self.buildLineStyle( len(unique_values) )
            
            # Criar as categorias
            categories = []
            symbolLine = QgsSymbol.defaultSymbol(layer.geometryType())
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
                layer.setRenderer(renderer)
            
            # Atualizar a exibição da camada
            layer.triggerRepaint()

    def buildLineGeometries(self)->QgsVectorLayer:
        layer = processing.run(
            'native:pointstopath', 
             { 
                    'CLOSE_PATH' : False, 
                    'GROUP_EXPRESSION' : '"faixa_img"', 
                    'INPUT' : 'delimitedtext://file:///{}?type=csv&maxFields=10000&detectTypes=yes&xField=long_img&yField=lat_img&crs=EPSG:4326&spatialIndex=no&subsetIndex=no&watchFile=no'.format(self.getStructPath()), 
                    'NATURAL_SORT' : False, 
                    'ORDER_EXPRESSION' : '"time_img"', 
                    'OUTPUT' : 'TEMPORARY_OUTPUT' 
            }
        )['OUTPUT']
        layer.startEditing()
        layer.setName('conexao')
        layer.commitChanges()

        QgsProject.instance().addMapLayer(layer)
        self.styleLineLayer(layer, fieldName='faixa_img', width=1)
    
    def build(self, imagesFolderPath):
        images = self.loadImagesDataset(imagesFolderPath)
        images.columns = ['{}_img'.format(name) for name in images.columns]
        result = self.removeDuplicatePoints(images)
        result = self.removeDuplicateLinesV2(result) #otimizar
        struct = self.createLines(result)
        struct = self.removeNearPoints(struct)
        struct.to_csv(self.getStructPath(), index=False)
        self.loadCSVLayer()
        self.buildLineGeometries()  
        