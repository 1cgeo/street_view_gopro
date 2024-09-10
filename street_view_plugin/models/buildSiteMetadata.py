from qgis.core import (
    QgsPointXY,
    QgsGeometry,
    QgsProcessingException,
    QgsPoint,
    QgsDistanceArea,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsVectorLayer,
    QgsVectorFileWriter,
)
from qgis.PyQt.QtCore import *
from qgis.PyQt.Qt import QVariant

import os
import json
import glob
import csv
import math

from street_view_plugin.models import graphHandler

class BuildSiteMetadata:

    def build(self, imageLayer: QgsVectorLayer, connectionLayer: QgsVectorLayer, metadataFolderPath):
        imageDict = {image['index']: image for image in imageLayer.getFeatures()} 
        try:
            import networkx as nx
        except ImportError:
            raise QgsProcessingException(
                self.tr(
                    "Esse algoritmo requer a biblioteca Python networkx. Por favor, instale esta biblioteca e tente novamente."
                )
            )
        # images = self.getImages(imageLayer)
        G = graphHandler.build_graph_with_photo_ids(nx, connectionLayer, imageLayer, 'index')
        neighboursDict  ={}
        for i in imageDict:
            neighbours = [imageDict[n] for n in graphHandler.get_neighbors(G, i)]
            neighboursDict[imageDict[i]] = neighbours
        metadata = self.buildMetadata(neighboursDict)
        self.saveMetadata(metadata, metadataFolderPath)
        fotosPath = os.path.join(metadataFolderPath, 'fotos')
        self.saveGeojson(imageLayer, fotosPath)
        fotos_linhasPath = os.path.join(metadataFolderPath, 'fotos_linhas')
        self.saveGeojson(connectionLayer, fotos_linhasPath)

    def getImages(self, imageLayer):
        images = {}
        for feat in imageLayer.getFeatures():
            if not(int(feat['faixa_img']) in images):
                images[int(feat['faixa_img'])] = {
                    'images': {}
                }
            images[int(feat['faixa_img'])]['images'][int(feat['numero_img'])] = {
                'feature': feat
            }
        return images

    def createGeometries(self, images):
        for photoRange in sorted(list(images)):
            images[photoRange]['pointFeatures'] = []
            for photoNumber in sorted(list(images[photoRange]['images'])):
                feat = images[photoRange]['images'][photoNumber]['feature']
                name = feat['nome_img']
                x = float(feat['long_img'])
                y = float(feat['lat_img'])

                images[photoRange]['pointFeatures'].append(
                    self.getPointFeature(
                        x, y, photoRange, photoNumber, name
                    )
                )
                images[photoRange]['images'][photoNumber]['neighbors'] = []
        for photoRange in images:
            images[photoRange]['pointFeatures'] = sorted(images[photoRange]['pointFeatures'], key=lambda f: f['pointId'], reverse=True) 
            images[photoRange]['line'] = QgsGeometry.fromPolyline([ QgsPoint(f.geometry().asPoint().x(), f.geometry().asPoint().y()) for f in images[photoRange]['pointFeatures'] ])
        return images

    def hasPoint(self, line, projected):
        closest, _, _, _, _ = line.closestVertex(
            QgsPointXY(projected.x(), projected.y())
        )
        return QgsGeometry.fromPointXY(closest).equals(QgsGeometry.fromPointXY(QgsPointXY(projected.x(), projected.y())))

    def distanceMeters(self, point1, point2):
        distance = QgsDistanceArea()
        distance.setEllipsoid('WGS84')
        return distance.measureLine(point1, point2)
    
    def getPreviousNextNeighbours(self, currentPoint, allneighbours):
        previousPoint = None
        nextPoint = None
        neighbours = []
        for neighbour in allneighbours:
            if neighbour['faixa_img'] != currentPoint['faixa_img']:
                neighbours.append(neighbour)
            elif neighbour['numero_img'] > currentPoint['numero_img']:
                nextPoint = neighbour
            else:
                previousPoint = neighbour
        return previousPoint, nextPoint, neighbours


    def buildMetadata(self, neighboursDict):
        metadata = []
        for currentPoint in neighboursDict:
            allneighbours = neighboursDict[currentPoint]
            previousPoint, nextPoint, neighbours = self.getPreviousNextNeighbours(currentPoint, allneighbours)

            links = []
            cpLatLong = (currentPoint['lat_img'], currentPoint['long_img'])
            ppLatLong = (previousPoint['lat_img'], previousPoint['long_img']) if previousPoint else None
            npLatLong = (nextPoint['lat_img'], nextPoint['long_img']) if nextPoint else None


            # heading = math.degrees(math.radians(float(currentPoint['heading_camera_gps'])) + 3.14159) % 360
            heading = self.get_azimuth(cpLatLong, ppLatLong, npLatLong)
            
                

            if nextPoint:
                links.append({
                    "id": nextPoint['nome_img'],
                    "img": nextPoint['nome_img'],
                    "lon": nextPoint['long_img'],
                    "lat": nextPoint['lat_img'],
                    "ele": nextPoint['ele_img'],
                    "icon": 'next',
                    "next": True
                })

            if previousPoint:
                links.append({
                    "id": previousPoint['nome_img'],
                    "img": previousPoint['nome_img'],
                    "lon": previousPoint['long_img'],
                    "lat": previousPoint['lat_img'],
                    "ele": previousPoint['ele_img'],
                    "icon": 'next'
                })

            # quando a funcao abaixo esta habilitada, os pontos nas extremidades sao conectados
            for neighbour in neighbours:
                links.append({
                    "id": neighbour['nome_img'],
                    "img": neighbour['nome_img'],
                    "lon": neighbour['long_img'],
                    "lat": neighbour['lat_img'],
                    "ele": neighbour['ele_img'],
                    "icon": 'next'
                })

            meta = {
                "camera": {
                    "id":  currentPoint['nome_img'],
                    "img": currentPoint['nome_img'],
                    "lon": currentPoint['long_img'],
                    "lat": currentPoint['lat_img'],
                    "ele": currentPoint['ele_img'],
                    "heading": heading
                },
                "targets": links
            }

            metadata.append(meta)
            """ if count == 3:
                break
            count +=1 """
        return metadata

    def saveMetadata(self, metadata, metadataFolderPath):
        files = glob.glob('{}/*'.format(metadataFolderPath))
        for f in files:
            os.remove(f)

        for meta in metadata:
            with open(os.path.join(metadataFolderPath, '{}.json'.format(meta['camera']['img'])), 'w') as outfile:
                json.dump(
                    meta, 
                    outfile,
                    indent=4
                )
    
    def calculate_azimuth(self, point1, point2):
        """
        Calcula o azimute entre dois pontos.
        :param point1: (latitude1, longitude1)
        :param point2: (latitude2, longitude2)
        :return: Azimute em graus
        """
        lat1, lon1 = math.radians(point1[0]), math.radians(point1[1])
        lat2, lon2 = math.radians(point2[0]), math.radians(point2[1])
        
        delta_lon = lon2 - lon1
        x = math.sin(delta_lon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
        
        initial_bearing = math.atan2(x, y)
        initial_bearing = math.degrees(initial_bearing)
        
        # Normalizar o azimute para estar entre 0 e 360 graus
        azimuth = (initial_bearing + 360) % 360
        return azimuth

    # Função para calcular o azimute de currentPoint
    def get_azimuth(self, currentPoint, previousPoint=None, nextPoint=None):
        """
        Calcula o azimute de currentPoint com base em previousPoint ou nextPoint.
        Se ambos estiverem disponíveis, calcula a média dos dois azimutes.
        :param currentPoint: (latitude, longitude) do ponto atual
        :param previousPoint: (latitude, longitude) do ponto anterior, opcional
        :param nextPoint: (latitude, longitude) do ponto seguinte, opcional
        :return: Azimute médio em graus
        """
        if previousPoint and nextPoint:
            azimuth1 = self.calculate_azimuth(previousPoint, currentPoint)
            azimuth2 = self.calculate_azimuth(currentPoint, nextPoint)
            
            # Calcula a média levando em conta que azimutes são circulares (0 a 360 graus)
            azimuth_mean = (azimuth1 + azimuth2) / 2
            
            # Verifica se a diferença entre os azimutes é maior que 180 para evitar erros na média circular
            if abs(azimuth1 - azimuth2) > 180:
                azimuth_mean = (azimuth_mean + 180) % 360
            
            return azimuth_mean
        elif previousPoint:
            return self.calculate_azimuth(previousPoint, currentPoint)
        elif nextPoint:
            return self.calculate_azimuth(currentPoint, nextPoint)
        else:
            return 0

    def getPointFeature(self, x, y, trackId, pointId, image):
        point = QgsFeature()
        point.setFields(self.getPointFields())
        point['trackId'] = trackId
        point['pointId'] = pointId
        point['image'] = image
        point.setGeometry( QgsGeometry.fromPointXY( QgsPointXY(x, y) ) )
        return point

    def getPointFields(self):
        fields = QgsFields()
        fields.append(QgsField('trackId', QVariant.Int))
        fields.append(QgsField('pointId', QVariant.Int))
        fields.append(QgsField('image', QVariant.String))
        fields.append(QgsField('ele', QVariant.String))
        return fields

    def saveCSV(self, images, filePath):
        hasHeader = False
        with open(filePath, 'w') as outfile:
            #w = csv.DictWriter(outfile)
            for photoRange in sorted(list(images)):
                images[photoRange]['images']
                for photoNumber in sorted(list(images[photoRange]['images'])):
                        if not hasHeader:
                            hasHeader = True
                            w = csv.DictWriter(outfile, images[photoRange]['images'][photoNumber].keys())
                            w.writeheader()
                        w.writerow(images[photoRange]['images'][photoNumber])

    def saveGeojson(self, layer, outputPath):
        

        # Salvar a camada como GeoJSON
        error = QgsVectorFileWriter.writeAsVectorFormat(
            layer,
            outputPath,
            "utf-8",  # codificação
            layer.crs(),  # sistema de referência de coordenadas
            "GeoJSON",
        )