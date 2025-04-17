# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Copia Imagens
                                 A QGIS plugin
 Conjunto de ferramentas do Streetview do 1° CGEO.
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
__date__ = '2025-04-17'
__copyright__ = '(C) 2024 by Brazilian Army Cartographic Mapoteca Tools'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
    QgsFeature,
    QgsProcessingException
)
import os
import shutil

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
)
import os
import shutil
from concurrent.futures import ThreadPoolExecutor


class CopiaImagens(QgsProcessingAlgorithm):
    LAYER = 'LAYER'
    NAME_FIELD = 'NAME_FIELD'
    FOLDER_IMG = 'FOLDER_IMG'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    BATCH_SIZE = 50  # Número de arquivos a serem copiados por vez (em lotes)

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
        folder_img = self.parameterAsString(parameters, self.FOLDER_IMG, context)
        output_folder = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Cria uma lista de tarefas para o executor (baseado nos nomes das imagens)
        tasks = []
        for feature in layer.getFeatures():
            name = feature[name_field]
            image_path = os.path.join(folder_img, name)
            if os.path.exists(image_path):
                output_path = os.path.join(output_folder, name)
                tasks.append((image_path, output_path))

        # Processamento em lotes de 50 arquivos por vez
        batch_start = 0
        while batch_start < len(tasks):
            batch_end = min(batch_start + self.BATCH_SIZE, len(tasks))
            batch = tasks[batch_start:batch_end]
            
            # Executa a cópia das imagens do lote em paralelo
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(self.copy_image, task[0], task[1], feedback) for task in batch]
                for future in futures:
                    future.result()  # Aguarda a conclusão de todas as tarefas no lote

            batch_start += self.BATCH_SIZE  # Avança para o próximo lote

        return {}

    def copy_image(self, image_path, output_path, feedback):
        try:
            shutil.copy(image_path, output_path)
            feedback.pushInfo(f'Imagem copiada: {output_path}')
        except Exception as e:
            feedback.reportError(f'Erro ao copiar a imagem: {str(e)}')

    def name(self):
        return 'copiar_imagens'

    def displayName(self):
        return '3. Copiar Imagens'

    def group(self):
        return 'Pré-processamento'

    def groupId(self):
        return 'pre_processamento'

    def createInstance(self):
        return CopiaImagens()


