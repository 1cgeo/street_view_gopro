# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Copia Imagens
                                 A QGIS plugin
 Conjunto de ferramentas do Streetview do 1° CGEO.
                              -------------------
        begin                : 2025-04-17
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
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class CopiaImagens(QgsProcessingAlgorithm):
    LAYER = 'LAYER'
    NAME_FIELD = 'NAME_FIELD'
    FOLDER_IMG = 'FOLDER_IMG'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    BATCH_SIZE = 20  # Reduzido para evitar sobrecarga
    MAX_WORKERS = 4  # Limitar número de threads concorrentes

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

        # Verificar se o usuário cancelou
        if feedback.isCanceled():
            return {}

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Cria uma lista de tarefas para o executor (baseado nos nomes das imagens)
        total_features = layer.featureCount()
        feedback.setProgress(0)
        
        processed_count = 0
        failed_count = 0
        
        # Coleta todas as tarefas antecipadamente
        tasks = []
        for feature in layer.getFeatures():
            # Verificar se o usuário cancelou
            if feedback.isCanceled():
                feedback.pushInfo('Processo cancelado pelo usuário')
                return {}
                
            name = feature[name_field]
            if not name:  # Verificar nomes vazios
                continue
                
            image_path = os.path.join(folder_img, name)
            if os.path.exists(image_path):
                output_path = os.path.join(output_folder, name)
                tasks.append((image_path, output_path))
            else:
                feedback.pushInfo(f'Imagem não encontrada: {name}')
        
        total_tasks = len(tasks)
        feedback.pushInfo(f'Total de imagens a serem copiadas: {total_tasks}')
        
        # Processamento em lotes para evitar sobrecarga de memória
        batch_start = 0
        while batch_start < len(tasks):
            # Verificar se o usuário cancelou
            if feedback.isCanceled():
                feedback.pushInfo('Processo cancelado pelo usuário')
                return {}
                
            batch_end = min(batch_start + self.BATCH_SIZE, len(tasks))
            batch = tasks[batch_start:batch_end]
            
            feedback.pushInfo(f'Processando lote {batch_start//self.BATCH_SIZE + 1} ({batch_start+1}-{batch_end} de {total_tasks})')
            
            # Executa a cópia das imagens do lote em paralelo com número limitado de workers
            with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                # Usar as_completed para processar os resultados à medida que terminam
                future_to_path = {
                    executor.submit(self.copy_image, task[0], task[1]): task[1] 
                    for task in batch
                }
                
                for future in as_completed(future_to_path):
                    # Verificar se o usuário cancelou
                    if feedback.isCanceled():
                        feedback.pushInfo('Processo cancelado pelo usuário')
                        executor.shutdown(wait=False)
                        return {}
                    
                    output_path = future_to_path[future]
                    try:
                        success = future.result()
                        processed_count += 1
                        if success:
                            # Limitar feedback para reduzir operações de UI
                            if processed_count % 10 == 0:
                                feedback.pushInfo(f'Progresso: {processed_count}/{total_tasks} imagens copiadas')
                        else:
                            failed_count += 1
                    except Exception as e:
                        failed_count += 1
                        feedback.reportError(f'Erro ao processar {output_path}: {str(e)}')
                    
                    # Atualizar o progresso
                    progress = int((processed_count + failed_count) / total_tasks * 100)
                    feedback.setProgress(progress)
                    
                    # Pequena pausa para permitir que a UI respire
                    time.sleep(0.001)
            
            batch_start += self.BATCH_SIZE  # Avança para o próximo lote
            
            # Pausa entre os lotes para liberar recursos
            time.sleep(0.1)
        
        feedback.pushInfo(f'Processo finalizado. {processed_count} imagens copiadas com sucesso. {failed_count} falhas.')
        
        return {}

    def copy_image(self, image_path, output_path):
        try:
            shutil.copy2(image_path, output_path)
            return True
        except Exception:
            return False

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