
"""
/***************************************************************************
 Remove pontos de parada
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

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterDefinition
from qgis.core import QgsExpression
import processing


class RemovePontosDeParada(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('camadadepontosimagens', 'Camada de pontos (imagens)', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterField('campoidentificador', 'Campo com o nome das imagens', type=QgsProcessingParameterField.Any, parentLayerParameterName='camadadepontosimagens', allowMultiple=False, defaultValue=None))
        param = QgsProcessingParameterNumber('tempoconsideradodetrocadebateriaemsegundos', 'Tempo considerado de troca de bateria (em segundos)', type=QgsProcessingParameterNumber.Integer, minValue=0, defaultValue=150)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        self.addParameter(QgsProcessingParameterFeatureSink('CamadaSemImagensDeParada', 'Camada sem imagens de parada', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(13, model_feedback)
        results = {}
        outputs = {}

        # Extrair pontos de inicio
        alg_params = {
            'EXPRESSION': 'left(right("filename",10),6) < @tempoconsideradodetrocadebateriaemsegundos',
            'INPUT': parameters['camadadepontosimagens'],
            'FAIL_OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtrairPontosDeInicio'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Extrair pontos de fim
        alg_params = {
            'EXPRESSION': 'left(right("filename",10),6) > (maximum(left(right("filename",10),6),left(right("filename",15),4))- @tempoconsideradodetrocadebateriaemsegundos)',
            'INPUT': outputs['ExtrairPontosDeInicio']['FAIL_OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtrairPontosDeFim'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Buffer Inicio
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': 5e-05,
            'END_CAP_STYLE': 0,  # Round
            'INPUT': outputs['ExtrairPontosDeInicio']['OUTPUT'],
            'JOIN_STYLE': 0,  # Round
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['BufferInicio'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Buffer Fim
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': 5e-05,
            'END_CAP_STYLE': 0,  # Round
            'INPUT': outputs['ExtrairPontosDeFim']['OUTPUT'],
            'JOIN_STYLE': 0,  # Round
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['BufferFim'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Pontos por poligono - Inicio
        alg_params = {
            'CLASSFIELD': '',
            'FIELD': 'qtd_pontos',
            'POINTS': outputs['ExtrairPontosDeInicio']['OUTPUT'],
            'POLYGONS': outputs['BufferInicio']['OUTPUT'],
            'WEIGHT': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PontosPorPoligonoInicio'] = processing.run('native:countpointsinpolygon', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Pontos por poligono - Fim
        alg_params = {
            'CLASSFIELD': '',
            'FIELD': 'qtd_pontos',
            'POINTS': outputs['ExtrairPontosDeFim']['OUTPUT'],
            'POLYGONS': outputs['BufferFim']['OUTPUT'],
            'WEIGHT': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PontosPorPoligonoFim'] = processing.run('native:countpointsinpolygon', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Unir atributos pelo valor do campo - Inicio
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': parameters['campoidentificador'],
            'FIELDS_TO_COPY': ['qtd_pontos'],
            'FIELD_2': QgsExpression(' @campoidentificador ').evaluate(),
            'INPUT': parameters['camadadepontosimagens'],
            'INPUT_2': outputs['PontosPorPoligonoInicio']['OUTPUT'],
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['UnirAtributosPeloValorDoCampoInicio'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Unir atributos pelo valor do campo - Fim
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': parameters['campoidentificador'],
            'FIELDS_TO_COPY': ['qtd_pontos'],
            'FIELD_2': QgsExpression(' @campoidentificador ').evaluate(),
            'INPUT': outputs['UnirAtributosPeloValorDoCampoInicio']['OUTPUT'],
            'INPUT_2': outputs['PontosPorPoligonoFim']['OUTPUT'],
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['UnirAtributosPeloValorDoCampoFim'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Ajusta qtd pontos
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'qtd_pontos',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,  # Integer (32 bit)
            'FORMULA': 'if("qtd_pontos_2" is not null,"qtd_pontos_2","qtd_pontos")',
            'INPUT': outputs['UnirAtributosPeloValorDoCampoFim']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AjustaQtdPontos'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Descartar qtd_pontos_2
        alg_params = {
            'COLUMN': ['qtd_pontos_2'],
            'INPUT': outputs['AjustaQtdPontos']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DescartarQtd_pontos_2'] = processing.run('native:deletecolumn', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Ajusta qtd pontos - Null
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'qtd_pontos',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,  # Integer (32 bit)
            'FORMULA': 'if("qtd_pontos" is null,0,"qtd_pontos")',
            'INPUT': outputs['DescartarQtd_pontos_2']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AjustaQtdPontosNull'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}

        # Pontos para remover - Fim
        alg_params = {
            'EXPRESSION': '"qtd_pontos"<6',
            'INPUT': outputs['AjustaQtdPontosNull']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PontosParaRemoverFim'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}

        # Remove vertices duplicados
        alg_params = {
            'INPUT': outputs['PontosParaRemoverFim']['OUTPUT'],
            'OUTPUT': parameters['CamadaSemImagensDeParada']
        }
        outputs['RemoveVerticesDuplicados'] = processing.run('native:deleteduplicategeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['CamadaSemImagensDeParada'] = outputs['RemoveVerticesDuplicados']['OUTPUT']
        return results

    def name(self):
        return 'remove_pontos_parada'

    def displayName(self):
        return '2. Remover pontos de parada'

    def group(self):
        return 'Pré-processamento'

    def groupId(self):
        return 'pre_processamento'

    def createInstance(self):
        return RemovePontosDeParada()
