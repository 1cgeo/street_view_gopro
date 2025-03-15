from qgis.core import (QgsProcessing, QgsProcessingParameterFile, QgsProcessingAlgorithm, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsProcessingException)
from PyQt5.QtCore import QVariant
import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import re

class ImageToGeometry(QgsProcessingAlgorithm):
    PASTA = 'PASTA'

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.PASTA,
                'Pasta contendo as imagens',
                behavior=QgsProcessingParameterFile.Folder,
                defaultValue=None
            )
        )
    
    def processAlgorithm(self, parameters, context, feedback):
        pasta = self.parameterAsFile(parameters, self.PASTA, context)
        
        if not os.path.isdir(pasta):
            raise QgsProcessingException(f"A pasta especificada não existe: {pasta}")
        
        dataset = self.loadImagesDataset(pasta)
        self.createGeometry(dataset)
        
        return {}
    
    def loadImagesDataset(self, imagesFolderPath):
        dataset = []
        for filename in os.listdir(imagesFolderPath):
            if not self.check_image_extension(filename):
                continue
            exif = self.getExif(os.path.join(imagesFolderPath, filename))
            lon, lat, ele = self.getCoordinates(exif.get('GPSInfo', {}))
            if lon is not None and lat is not None and ele is not None:
                dataset.append((filename, lon, lat, ele))
        return dataset
    
    def check_image_extension(self, filename):
        return bool(re.search(r"\.(jpg)$", filename, re.IGNORECASE))
    
    def getExif(self, filename):
        exif = Image.open(filename)._getexif()
        info = {}
        if exif is not None:
            for key, value in exif.items():
                name = TAGS.get(key, key)
                info[name] = value

            if 'GPSInfo' in info:
                gps_info = {}
                for key, value in info['GPSInfo'].items():
                    name = GPSTAGS.get(key, key)
                    gps_info[name] = value
                info['GPSInfo'] = gps_info
        return info
    
    def getCoordinates(self, info):
        try:
            for key in ['Latitude', 'Longitude', 'Altitude']:
                if key == 'Altitude' and f'GPS{key}' in info:
                    info[key] = float(info[f'GPS{key}'])
                elif f'GPS{key}' in info and f'GPS{key}Ref' in info:
                    deg, minutes, seconds = info[f'GPS{key}']
                    direction = info[f'GPS{key}Ref']
                    info[key] = self.gms2degrees(deg, minutes, seconds, direction)
            return info.get('Longitude'), info.get('Latitude'), info.get('Altitude')
        except:
            return None, None, None
    
    def gms2degrees(self, deg, minutes, seconds, direction):
        return (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)
    
    def createGeometry(self, dataset):
        layer = QgsVectorLayer("Point?crs=EPSG:4326", "imagens", "memory")
        provider = layer.dataProvider()

        provider.addAttributes([
            QgsField("filename", QVariant.String),
            QgsField("lon", QVariant.Double),
            QgsField("lat", QVariant.Double),
            QgsField("ele", QVariant.Double)
        ])
        layer.updateFields()

        features = []
        for filename, lon, lat, ele in dataset:
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat))) 
            feat.setAttributes([filename, lon, lat, ele]) 
            features.append(feat)

        provider.addFeatures(features)
        layer.updateExtents()
        QgsProject.instance().addMapLayer(layer)

    def name(self):
        return 'image2geom'

    def displayName(self):
        return 'Exibir posição das imagens'

    def group(self):
        return 'Processamento Personalizado'

    def groupId(self):
        return 'processamento_personalizado'

    def createInstance(self):
        return ImageToGeometry()
