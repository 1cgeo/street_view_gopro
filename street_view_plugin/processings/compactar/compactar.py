
"""
/***************************************************************************
 Compacta Imagens
                                 A QGIS plugin
 Conjunto de ferramentas do Streetview do 1° CGEO.
                              -------------------
        begin                : 2025-04-20
        copyright            : (C) 2025 by Brazilian Army Cartographic
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
__date__ = '2025-04-20'
__copyright__ = '(C) 2025 by Brazilian Army Cartographic Streetview Tools'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import subprocess
import concurrent.futures
from PIL import Image
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
    QgsProcessingParameterBoolean,
    QgsProcessingException
)

class ComprimirImagensExifTool(QgsProcessingAlgorithm):
    INPUT_FOLDER = 'INPUT_FOLDER'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    QUALIDADE = 'QUALIDADE'
    USAR_THREADS = 'USAR_THREADS'
    NUMERO_THREADS = 'NUMERO_THREADS'
    TAMANHO_LOTE = 'TAMANHO_LOTE'

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_FOLDER,
                'Pasta com imagens JPG',
                behavior=QgsProcessingParameterFile.Folder
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                self.OUTPUT_FOLDER,
                'Pasta de saída',
                behavior=QgsProcessingParameterFile.Folder
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.QUALIDADE,
                'Qualidade JPEG (1-100)',
                type=QgsProcessingParameterNumber.Integer,
                minValue=1,
                maxValue=100,
                defaultValue=80
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.USAR_THREADS,
                'Usar processamento multithreaded',
                defaultValue=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NUMERO_THREADS,
                'Número de threads (0 = automático)',
                type=QgsProcessingParameterNumber.Integer,
                minValue=0,
                defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TAMANHO_LOTE,
                'Tamanho do lote para processamento em sequência',
                type=QgsProcessingParameterNumber.Integer,
                minValue=1,
                defaultValue=10
            )
        )

    def _processar_imagem(self, arquivo, pasta_entrada, pasta_saida, qualidade, exiftool_path):
        """Processa uma única imagem"""
        caminho_entrada = os.path.join(pasta_entrada, arquivo)
        caminho_saida = os.path.join(pasta_saida, arquivo)
        
        try:
            # Usar PIL para compactar a imagem
            with Image.open(caminho_entrada) as img:
                img.save(caminho_saida, 'JPEG', quality=qualidade, optimize=True)
            
            # Restaurar metadados com exiftool
            comando_exif = [
                exiftool_path,
                "-overwrite_original",
                "-tagsFromFile", caminho_entrada,
                caminho_saida
            ]
            
            resultado_exif = subprocess.run(comando_exif, capture_output=True, text=True)
            
            if resultado_exif.returncode != 0:
                return (arquivo, False, f"Erro ExifTool: {resultado_exif.stderr}")
            return (arquivo, True, "OK")
            
        except Exception as e:
            return (arquivo, False, str(e))

    def _processar_em_lote(self, arquivos, pasta_entrada, pasta_saida, qualidade, exiftool_path, feedback):
        """Processa um lote de imagens usando ExifTool em modo lote"""
        # Primeiro comprime todas as imagens com PIL
        for arquivo in arquivos:
            caminho_entrada = os.path.join(pasta_entrada, arquivo)
            caminho_saida = os.path.join(pasta_saida, arquivo)
            
            try:
                with Image.open(caminho_entrada) as img:
                    img.save(caminho_saida, 'JPEG', quality=qualidade, optimize=True)
            except Exception as e:
                feedback.reportError(f"❌ Erro ao compactar {arquivo} com PIL: {str(e)}")
        
        # Agora copia os metadados em lote
        comando_lote = [exiftool_path, "-overwrite_original"]
        
        # Cria pares de argumentos para o ExifTool: -tagsFromFile ORIGEM DESTINO
        for arquivo in arquivos:
            caminho_entrada = os.path.join(pasta_entrada, arquivo)
            caminho_saida = os.path.join(pasta_saida, arquivo)
            comando_lote.extend(["-tagsFromFile", caminho_entrada, caminho_saida])
        
        resultado = subprocess.run(comando_lote, capture_output=True, text=True)
        if resultado.returncode != 0:
            feedback.reportError(f"⚠️ Erro ao processar lote com ExifTool: {resultado.stderr}")
        
        return len(arquivos)

    def processAlgorithm(self, parameters, context, feedback):
        pasta_entrada = self.parameterAsString(parameters, self.INPUT_FOLDER, context)
        pasta_saida = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)
        qualidade = self.parameterAsInt(parameters, self.QUALIDADE, context)
        usar_threads = self.parameterAsBool(parameters, self.USAR_THREADS, context)
        num_threads = self.parameterAsInt(parameters, self.NUMERO_THREADS, context)
        tamanho_lote = self.parameterAsInt(parameters, self.TAMANHO_LOTE, context)
        
        # Se for 0, usa um número razoável de threads (mas não exageramos)
        if num_threads == 0:
            import os
            num_threads = os.cpu_count()
            if num_threads > 12:  # Limitar para não sobrecarregar
                num_threads = 12
        
        # Caminho para o exiftool
        script_path = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_path)
        exiftool_path = os.path.join(parent_dir, "recuperar", "auxiliar", 
                                     "exiftool-13.27_64", "exiftool.exe")
        
        feedback.pushInfo(f"Caminho do ExifTool: {exiftool_path}")
        feedback.pushInfo(f"Modo de processamento: {'Threads' if usar_threads else 'Sequencial'}")
        
        if not os.path.exists(exiftool_path):
            feedback.reportError(f"❌ ExifTool não encontrado em: {exiftool_path}")
            return {self.OUTPUT_FOLDER: pasta_saida}

        if not os.path.exists(pasta_entrada):
            raise QgsProcessingException("A pasta de entrada não existe.")
        os.makedirs(pasta_saida, exist_ok=True)

        # Listar apenas arquivos JPG/JPEG
        arquivos = [f for f in os.listdir(pasta_entrada) if f.lower().endswith((".jpg", ".jpeg"))]
        total = len(arquivos)
        
        feedback.pushInfo(f"Encontradas {total} imagens para processar.")
        
        contador = 0
        
        # Opção 1: Usar ThreadPoolExecutor (não cria novos processos do QGIS)
        if usar_threads and total > 1:
            feedback.pushInfo(f"Iniciando processamento com {num_threads} threads...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                # Submete os trabalhos para o executor
                futures = {}
                for arquivo in arquivos:
                    future = executor.submit(
                        self._processar_imagem, 
                        arquivo, 
                        pasta_entrada, 
                        pasta_saida, 
                        qualidade, 
                        exiftool_path
                    )
                    futures[future] = arquivo
                
                # Processa os resultados conforme concluídos
                for future in concurrent.futures.as_completed(futures):
                    arquivo = futures[future]
                    try:
                        resultado = future.result()
                        _, sucesso, mensagem = resultado
                        
                        contador += 1
                        if sucesso:
                            feedback.pushInfo(f"✔ {contador}/{total} - {arquivo} processado com sucesso.")
                        else:
                            feedback.reportError(f"❌ {contador}/{total} - Erro ao processar {arquivo}: {mensagem}")
                            
                        feedback.setProgress(int(contador * 100 / total))
                        
                    except Exception as exc:
                        feedback.reportError(f"❌ Erro ao processar {arquivo}: {str(exc)}")
                        contador += 1
                        feedback.setProgress(int(contador * 100 / total))
                    
                    # Verifica se o usuário cancelou
                    if feedback.isCanceled():
                        break
        
        # Opção 2: Processamento sequencial em lote
        else:
            feedback.pushInfo("Iniciando processamento em lote sequencial...")
            
            # Otimização: Usar processamento em lote maior com ExifTool
            # Dividimos em duas etapas: compressão e restauração de metadados
            
            # Primeiro comprime todas as imagens com PIL
            for i, arquivo in enumerate(arquivos):
                if feedback.isCanceled():
                    break
                    
                caminho_entrada = os.path.join(pasta_entrada, arquivo)
                caminho_saida = os.path.join(pasta_saida, arquivo)
                
                try:
                    with Image.open(caminho_entrada) as img:
                        img.save(caminho_saida, 'JPEG', quality=qualidade, optimize=True)
                    feedback.pushInfo(f"✔ {i+1}/{total} - {arquivo} comprimido.")
                except Exception as e:
                    feedback.reportError(f"❌ {i+1}/{total} - Erro ao comprimir {arquivo}: {str(e)}")
                
                feedback.setProgress(int((i + 1) * 50 / total))  # Primeiros 50% do progresso
            
            # Agora restaura os metadados em lotes para evitar sobrecarga do ExifTool
            if not feedback.isCanceled():
                feedback.pushInfo("Restaurando metadados em lotes...")
                
                for i in range(0, len(arquivos), tamanho_lote):
                    if feedback.isCanceled():
                        break
                        
                    lote_atual = arquivos[i:i + tamanho_lote]
                    feedback.pushInfo(f"Processando metadados do lote {i//tamanho_lote + 1} com {len(lote_atual)} imagens...")
                    
                    # Cria o comando ExifTool para o lote
                    comando_lote = [exiftool_path, "-overwrite_original"]
                    for arquivo in lote_atual:
                        caminho_entrada = os.path.join(pasta_entrada, arquivo)
                        caminho_saida = os.path.join(pasta_saida, arquivo)
                        comando_lote.extend(["-tagsFromFile", caminho_entrada, caminho_saida])
                    
                    # Executa o comando ExifTool
                    resultado = subprocess.run(comando_lote, capture_output=True, text=True)
                    if resultado.returncode != 0:
                        feedback.reportError(f"⚠️ Erro ao processar lote com ExifTool: {resultado.stderr}")
                    else:
                        feedback.pushInfo(f"✔ Metadados restaurados para {len(lote_atual)} imagens.")
                    
                    # Atualiza o progresso (50% a 100%)
                    progresso_atual = 50 + int((i + len(lote_atual)) * 50 / total)
                    feedback.setProgress(min(progresso_atual, 100))

        feedback.pushInfo(f"Processamento concluído.")
        return {self.OUTPUT_FOLDER: pasta_saida}

    def name(self):
        return 'comprimir_imagens_otimizado'

    def displayName(self):
        return '1. Comprimir imagens JPG (Otimizado)'

    def group(self):
        return 'Compactar'

    def groupId(self):
        return 'compactar'

    def shortHelpString(self):
        return (
            'Este algoritmo comprime imagens JPG usando PIL (Pillow) '
            'e restaura os metadados originais com exiftool, '
            'otimizado para alto desempenho com processamento multithread.'
        )
    
    def createInstance(self):
        return ComprimirImagensExifTool()