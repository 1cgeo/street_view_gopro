from qgis.core import *
from PyQt5.QtCore import *

import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import re
import numpy as np
from datetime import datetime
import copy
import json
import glob
import csv
import math

class BuildSiteMetadata:

    def build(self, imageLayer, connectionLayer, metadataFolderPath):
        images = self.getImages(imageLayer)
        images = self.createGeometries(images)
        connection = connectionLayer
        for link in connection.getFeatures():
            neighbors = []
            for photoRange in sorted(list(images)):
                line = images[photoRange]['line']
                if not link.geometry().buffer(0.00001, 5).intersects(line):
                    continue
                linkPoints = list(link.geometry().vertices())
                linkPointA = QgsPointXY(linkPoints[0].x(), linkPoints[0].y())
                linkPointB = QgsPointXY(linkPoints[-1].x(), linkPoints[-1].y())

                for pointFeature in images[photoRange]['pointFeatures']:
                    if not(
                            pointFeature.geometry().buffer(0.00001, 5).intersects(QgsGeometry.fromPointXY(linkPointA)) or 
                            pointFeature.geometry().buffer(0.00001, 5).intersects(QgsGeometry.fromPointXY(linkPointB))
                        ):
                        continue
                    neighbors.append(
                        {
                            'faixa': photoRange,
                            'numero': pointFeature['pointId']
                        }
                    )
            if not neighbors:
                continue
            images[ neighbors[0]['faixa'] ]['images'][ neighbors[0]['numero'] ]['neighbors'].append(
                images[ neighbors[-1]['faixa'] ]['images'][ neighbors[-1]['numero'] ]
            )

            images[ neighbors[-1]['faixa'] ]['images'][ neighbors[-1]['numero'] ]['neighbors'].append(
                images[ neighbors[0]['faixa'] ]['images'][ neighbors[0]['numero'] ]
            )
        metadata = self.buildMetadata(images)
        self.saveMetadata(metadata, metadataFolderPath)

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
        tracks = {}
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


    def buildMetadata(self, tracks):
        metadata = []
        count = 0
        for trackId in sorted(list(tracks.keys())):
            imageIds = sorted(list(tracks[trackId]['images']))
            
            for idx, imageId in enumerate(imageIds):

                currentPoint = tracks[trackId]['images'][imageId]
                previousPoint = tracks[trackId]['images'][ imageIds[idx - 1] ] if (idx - 1) >= 0 else None
                nextPoint = tracks[trackId]['images'][ imageIds[idx + 1] ] if (idx + 1) < len(imageIds) else None

                links = []


                heading = math.degrees(math.radians(float(currentPoint['feature']['heading_camera_gps'])) + 3.14159) % 360
                
                    

                if nextPoint:
                    links.append({
                        "id": nextPoint['feature']['nome_img'],
                        "img": nextPoint['feature']['nome_img'],
                        "lon": nextPoint['feature']['long_img'],
                        "lat": nextPoint['feature']['lat_img'],
                        "ele": nextPoint['feature']['ele_img'],
                        "icon": 'next',
                        "next": True
                    })

                if previousPoint:
                    links.append({
                        "id": previousPoint['feature']['nome_img'],
                        "img": previousPoint['feature']['nome_img'],
                        "lon": previousPoint['feature']['long_img'],
                        "lat": previousPoint['feature']['lat_img'],
                        "ele": previousPoint['feature']['ele_img'],
                        "icon": 'next'
                    })

                for neighbor in currentPoint['neighbors']:
                    links.append({
                        "id": neighbor['feature']['nome_img'],
                        "img": neighbor['feature']['nome_img'],
                        "lon": neighbor['feature']['long_img'],
                        "lat": neighbor['feature']['lat_img'],
                        "ele": neighbor['feature']['ele_img'],
                        "icon": 'next'
                    })

                meta = {
                    "camera": {
                        "id":  currentPoint['feature']['nome_img'],
                        "img": currentPoint['feature']['nome_img'],
                        "lon": currentPoint['feature']['long_img'],
                        "lat": currentPoint['feature']['lat_img'],
                        "ele": currentPoint['feature']['ele_img'],
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