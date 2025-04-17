# -*- coding: utf-8 -*-

"""
/***************************************************************************
 ExecutaLAIemLote
                                 A QGIS plugin
 Conjunto de ferramentas da mapoteca do 1° CGEO.
                              -------------------
        begin                : 2024-11-26
        copyright            : (C) 2024 by Brazilian Army Cartographic
        email                : raulmagno.neves@eb.mil.br
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

__author__ = '1° Ten Raul Magno / 1° CGEO'
__date__ = '2025-04-16'
__copyright__ = '(C) 2024 by Brazilian Army Cartographic Mapoteca Tools'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFile
)

import os
import subprocess
import shutil

class AdicionaCoordenadasExiftool(QgsProcessingAlgorithm):
    LAYER = 'LAYER'
    NAME_FIELD = 'NAME_FIELD'
    ALT_FIELD = 'ALT_FIELD'
    FOLDER_IMG = 'FOLDER_IMG'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.LAYER,
                'Camada de pontos',
                [QgsProcessing.TypeVectorPoint]
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.NAME_FIELD,
                'Campo com o nome do arquivo da imagem',
                parentLayerParameterName=self.LAYER
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.ALT_FIELD,
                'Campo com a altitude',
                parentLayerParameterName=self.LAYER,
                type=QgsProcessingParameterField.Numeric
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.FOLDER_IMG,
                'Pasta com imagens',
                behavior=QgsProcessingParameterFile.Folder
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.OUTPUT_FOLDER,
                'Pasta de destino',
                behavior=QgsProcessingParameterFile.Folder
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsSource(parameters, self.LAYER, context)
        name_field = self.parameterAsString(parameters, self.NAME_FIELD, context)
        alt_field = self.parameterAsString(parameters, self.ALT_FIELD, context)
        folder_img = self.parameterAsString(parameters, self.FOLDER_IMG, context)
        output_folder = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)

        # Caminho fixo relativo ao script/plugin
        script_dir = os.path.dirname(__file__)
        exiftool_path = os.path.join(script_dir,'auxiliar' ,'exiftool-13.27_64', 'exiftool.exe')

        if not os.path.exists(exiftool_path):
            raise Exception(f'Exiftool não encontrado no caminho esperado: {exiftool_path}')

        for feature in layer.getFeatures():
            name = str(feature[name_field])
            geom = feature.geometry()
            if not geom or not geom.isMultipart():
                pt = geom.asPoint()
                lat, lon = pt.y(), pt.x()
            else:
                feedback.pushWarning(f'Geometria múltipla ignorada: {name}')
                continue

            try:
                altitude = float(feature[alt_field])
            except Exception:
                altitude = None

            if altitude is None:
                feedback.pushWarning(f'Altitude inválida para: {name}')
                continue

            lat_ref = 'N' if lat >= 0 else 'S'
            lon_ref = 'E' if lon >= 0 else 'W'
            lat = abs(lat)
            lon = abs(lon)

            image_path = os.path.join(folder_img, name)
            if not os.path.exists(image_path):
                feedback.pushWarning(f'Imagem não encontrada: {image_path}')
                continue

            output_path = os.path.join(output_folder, name)

            try:
                shutil.copy(image_path, output_path)
            except Exception as e:
                feedback.reportError(f'Erro ao copiar a imagem: {str(e)}')
                continue

            cmd = [
                exiftool_path,
                f"-GPSLatitude={lat}",
                f"-GPSLatitudeRef={lat_ref}",
                f"-GPSLongitude={lon}",
                f"-GPSLongitudeRef={lon_ref}",
                f"-GPSAltitude={altitude}",
                "-overwrite_original",
                output_path
            ]

            feedback.pushDebugInfo("Comando exiftool: " + " ".join(cmd))

            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    feedback.reportError(f"Erro ao rodar exiftool: {result.stderr}")
                else:
                    feedback.pushInfo(f'Coordenadas e altitude adicionadas: {output_path}')
            except Exception as e:
                feedback.reportError(f'Erro ao executar exiftool: {str(e)}')

        return {}

    def name(self):
        return 'adicionar_coordenadas'

    def displayName(self):
        return '2. Adicionar metadados de coordenadas GPS às imagens'

    def group(self):
        return 'Recuperar Imagens'

    def groupId(self):
        return 'recuperar'

    def createInstance(self):
        return AdicionaCoordenadasExiftool()
