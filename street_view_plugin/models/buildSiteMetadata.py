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

CSV_IMAGENS = 'E:\\URUGUAIANA\\street_uruguaiana.csv'
METADATA_FOLDER = 'E:\\URUGUAIANA\\METADATA_CAMPO_FINAL'
MAX_DISTANCE = 0.0003
MIN_DISTANCE = 0.00005
START_POINT = ""


class BuildSiteMetadata:
    pass
    def getImages():
        images = {}
        with open(CSV_IMAGENS, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if not(int(row['faixa_img']) in images):
                    images[int(row['faixa_img'])] = {
                        'images': {}
                    }
                images[int(row['faixa_img'])]['images'][int(row['numero_img'])] = row
        return images

    def createGeometries(images):
        tracks = {}
        for photoRange in sorted(list(images)):
            images[photoRange]['pointFeatures'] = []
            for photoNumber in sorted(list(images[photoRange]['images'])):
                name = images[photoRange]['images'][photoNumber]['nome_img']
                x = float(images[photoRange]['images'][photoNumber]['long_img'])
                y = float(images[photoRange]['images'][photoNumber]['lat_img'])

                images[photoRange]['pointFeatures'].append(
                    getPointFeature(
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


                heading = math.degrees(math.radians(float(currentPoint['heading_camera_gps'])) + 3.14159) % 360
                
                    

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

                for neighbor in currentPoint['neighbors']:
                    links.append({
                        "id": neighbor['nome_img'],
                        "img": neighbor['nome_img'],
                        "lon": neighbor['long_img'],
                        "lat": neighbor['lat_img'],
                        "ele": neighbor['ele_img'],
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

    def saveMetadata(self, metadata):
        files = glob.glob('{}/*'.format(METADATA_FOLDER))
        for f in files:
            os.remove(f)

        for meta in metadata:
            with open(os.path.join(METADATA_FOLDER, '{}.json'.format(meta['camera']['img'])), 'w') as outfile:
                json.dump(
                    meta, 
                    outfile,
                    indent=4
                )

    def getPointFeature(self, x, y, trackId, pointId, image):
        point = QgsFeature()
        point.setFields(getPointFields())
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

    def addElevationAttributes(self, images, demLayer):
        for imgRange in images:
            for imgId in images[imgRange]['images']:
                img = images[imgRange]['images'][imgId]
                point = QgsPointXY(img['lonlat'][0], img['lonlat'][1])
                img['ele'] = list(demLayer.dataProvider().identify( point, QgsRaster.IdentifyFormatValue ).results().values())[0]

    def getLayer(self, layerName):
        layers = QgsProject.instance().mapLayers()
        for l in layers.values():
            if not(layerName == l.name()):
                continue
            return l
        return None

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


    def addPoint(self):
        #MULTICAPTURA_1530_000065
        pass

    def getVectorLayer(self, name):
        found = [l for l in [
            l
            for l in QgsProject.instance().mapLayers().values()
            if l.type() == QgsMapLayer.VectorLayer
        ] if l.name() == name]
        if len(found) != 1:
            raise Exception("{} não encontrado!".format(name))
        return found[0]
        
    def main(self):
        images = getImages()
        images = createGeometries(images)
        connection = getVectorLayer('conexoes')
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
        metadata = buildMetadata(images)
        saveMetadata(metadata)



    
#main()