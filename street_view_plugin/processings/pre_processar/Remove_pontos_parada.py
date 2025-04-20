
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

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterDefinition
)
import processing


class RemovePontosDeParada(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(
            'camadadepontosimagens',
            'Camada de pontos (imagens)',
            types=[QgsProcessing.TypeVectorPoint]
        ))

        self.addParameter(QgsProcessingParameterField(
            'campoidentificador',
            'Campo com o nome das imagens',
            type=QgsProcessingParameterField.Any,
            parentLayerParameterName='camadadepontosimagens',
            allowMultiple=False
        ))

        param = QgsProcessingParameterNumber(
            'tempotrocabateria',
            'Tempo considerado de troca de bateria (em segundos)',
            type=QgsProcessingParameterNumber.Integer,
            minValue=0,
            defaultValue=150
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

        self.addParameter(QgsProcessingParameterFeatureSink(
            'CamadaSemImagensDeParada',
            'Camada sem imagens de parada',
            type=QgsProcessing.TypeVectorAnyGeometry,
            createByDefault=True
        ))

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(13, model_feedback)
        results = {}
        outputs = {}

        # Obtem valores dos parâmetros
        tempo_troca_bateria = self.parameterAsInt(parameters, 'tempotrocabateria', context)
        campo_identificador = self.parameterAsString(parameters, 'campoidentificador', context)

        # Extrair pontos de inicio
        alg_params = {
            'EXPRESSION': f'left(right("filename",10),6) < {tempo_troca_bateria}',
            'INPUT': parameters['camadadepontosimagens'],
            'FAIL_OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtrairPontosDeInicio'] = processing.run(
            'native:extractbyexpression',
            alg_params, context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Extrair pontos de fim
        alg_params = {
            'EXPRESSION': f'left(right("filename",10),6) > (maximum(left(right("filename",10),6),left(right("filename",15),4)) - {tempo_troca_bateria})',
            'INPUT': outputs['ExtrairPontosDeInicio']['FAIL_OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtrairPontosDeFim'] = processing.run(
            'native:extractbyexpression',
            alg_params, context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Buffer Inicio
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': 5e-05,
            'END_CAP_STYLE': 0,
            'INPUT': outputs['ExtrairPontosDeInicio']['OUTPUT'],
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['BufferInicio'] = processing.run(
            'native:buffer',
            alg_params, context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Buffer Fim
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': 5e-05,
            'END_CAP_STYLE': 0,
            'INPUT': outputs['ExtrairPontosDeFim']['OUTPUT'],
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['BufferFim'] = processing.run(
            'native:buffer',
            alg_params, context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Pontos por polígono - Inicio
        alg_params = {
            'CLASSFIELD': '',
            'FIELD': 'qtd_pontos',
            'POINTS': outputs['ExtrairPontosDeInicio']['OUTPUT'],
            'POLYGONS': outputs['BufferInicio']['OUTPUT'],
            'WEIGHT': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PontosPorPoligonoInicio'] = processing.run(
            'native:countpointsinpolygon',
            alg_params, context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Pontos por polígono - Fim
        alg_params = {
            'CLASSFIELD': '',
            'FIELD': 'qtd_pontos',
            'POINTS': outputs['ExtrairPontosDeFim']['OUTPUT'],
            'POLYGONS': outputs['BufferFim']['OUTPUT'],
            'WEIGHT': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PontosPorPoligonoFim'] = processing.run(
            'native:countpointsinpolygon',
            alg_params, context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Unir atributos pelo valor do campo - Inicio
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': campo_identificador,
            'FIELDS_TO_COPY': ['qtd_pontos'],
            'FIELD_2': campo_identificador,
            'INPUT': parameters['camadadepontosimagens'],
            'INPUT_2': outputs['PontosPorPoligonoInicio']['OUTPUT'],
            'METHOD': 1,
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['UnirAtributosPeloValorDoCampoInicio'] = processing.run(
            'native:joinattributestable',
            alg_params, context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Unir atributos pelo valor do campo - Fim
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': campo_identificador,
            'FIELDS_TO_COPY': ['qtd_pontos'],
            'FIELD_2': campo_identificador,
            'INPUT': outputs['UnirAtributosPeloValorDoCampoInicio']['OUTPUT'],
            'INPUT_2': outputs['PontosPorPoligonoFim']['OUTPUT'],
            'METHOD': 1,
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['UnirAtributosPeloValorDoCampoFim'] = processing.run(
            'native:joinattributestable',
            alg_params, context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Ajusta qtd_pontos
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'qtd_pontos',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': 'if("qtd_pontos_2" is not null,"qtd_pontos_2","qtd_pontos")',
            'INPUT': outputs['UnirAtributosPeloValorDoCampoFim']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AjustaQtdPontos'] = processing.run(
            'native:fieldcalculator',
            alg_params, context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Descartar qtd_pontos_2
        alg_params = {
            'COLUMN': ['qtd_pontos_2'],
            'INPUT': outputs['AjustaQtdPontos']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DescartarQtd_pontos_2'] = processing.run(
            'native:deletecolumn',
            alg_params, context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Ajusta qtd pontos - Null
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'qtd_pontos',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': 'if("qtd_pontos" is null,0,"qtd_pontos")',
            'INPUT': outputs['DescartarQtd_pontos_2']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AjustaQtdPontosNull'] = processing.run(
            'native:fieldcalculator',
            alg_params, context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}

        # Pontos para remover - Fim
        alg_params = {
            'EXPRESSION': '"qtd_pontos"<6',
            'INPUT': outputs['AjustaQtdPontosNull']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PontosParaRemoverFim'] = processing.run(
            'native:extractbyexpression',
            alg_params, context=context, feedback=feedback, is_child_algorithm=True
        )

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}

        # Remove vértices duplicados
        alg_params = {
            'INPUT': outputs['PontosParaRemoverFim']['OUTPUT'],
            'OUTPUT': parameters['CamadaSemImagensDeParada']
        }
        outputs['RemoveVerticesDuplicados'] = processing.run(
            'native:deleteduplicategeometries',
            alg_params, context=context, feedback=feedback, is_child_algorithm=True
        )

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
