"""
/***************************************************************************
 Imagens para pontos
                                 A QGIS plugin
 Conjunto de ferramentas do Streetview do 1° CGEO.
                              -------------------
        begin                : 2024-11-26
        copyright            : (C) 2024 by Brazilian Army Cartographic
        email                : raulmagno.neves@eb.mil.br
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   Este programa é um software livre; você pode redistribuí-lo e/ou     *
 *   modificá-lo sob os termos da Licença Pública Geral GNU conforme      *
 *   publicada pela Free Software Foundation; versão 2 ou posterior.      *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = '1° Ten Raul Magno / 1° CGEO'
__date__ = '2025-04-17'
__copyright__ = '(C) 2024 by Brazilian Army Cartographic Mapoteca Tools'

from qgis.core import (
    QgsProcessing,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingAlgorithm,
    QgsVectorLayer,
    QgsField,
    QgsFields,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsProcessingException,
    QgsVectorFileWriter,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem
)
from PyQt5.QtCore import QVariant
import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import re

class ImageToGeometry(QgsProcessingAlgorithm):
    PASTA = 'PASTA'
    SAIDA = 'SAIDA'

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.PASTA,
                'Pasta contendo as imagens',
                behavior=QgsProcessingParameterFile.Folder,
                defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.SAIDA,
                'Arquivo de saída (GeoPackage)',
                fileFilter='GeoPackage (*.gpkg)'
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        pasta = self.parameterAsFile(parameters, self.PASTA, context)
        saida = self.parameterAsFileOutput(parameters, self.SAIDA, context)

        if not os.path.isdir(pasta):
            raise QgsProcessingException(f"A pasta especificada não existe: {pasta}")

        dataset = self.loadImagesDataset(pasta)
        self.createGeometry(dataset, saida, context, feedback)

        return {'OUTPUT': saida}

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

    def createGeometry(self, dataset, saida, context, feedback):
        fields = [
            QgsField("filename", QVariant.String),
            QgsField("lon", QVariant.Double),
            QgsField("lat", QVariant.Double),
            QgsField("ele", QVariant.Double)
        ]

        qgs_fields = QgsFields()
        for field in fields:
            qgs_fields.append(field)

        writer = QgsVectorFileWriter(
            saida, 'UTF-8', qgs_fields,
            QgsWkbTypes.Point,
            QgsCoordinateReferenceSystem("EPSG:4326"),
            "GPKG"
        )

        if writer.hasError() != QgsVectorFileWriter.NoError:
            raise QgsProcessingException(f"Erro ao criar o GeoPackage: {writer.errorMessage()}")

        for filename, lon, lat, ele in dataset:
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
            feat.setAttributes([filename, lon, lat, ele])
            writer.addFeature(feat)

        del writer  # Finaliza a escrita

        camada = QgsVectorLayer(saida, "Imagens_GeoRef", "ogr")
        if camada.isValid():
            QgsProject.instance().addMapLayer(camada)
        else:
            feedback.pushWarning("A camada foi criada, mas não pôde ser carregada automaticamente.")

    def name(self):
        return 'image2geom'

    def displayName(self):
        return '1. Exibir posição das imagens'

    def group(self):
        return 'Pré-processamento'

    def groupId(self):
        return 'pre_processamento'

    def createInstance(self):
        return ImageToGeometry()
