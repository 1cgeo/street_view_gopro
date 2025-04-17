import os
import subprocess
from PIL import Image
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
    QgsProcessingException
)

class ComprimirImagensExifTool(QgsProcessingAlgorithm):
    INPUT_FOLDER = 'INPUT_FOLDER'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    QUALIDADE = 'QUALIDADE'

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

    def processAlgorithm(self, parameters, context, feedback):
        pasta_entrada = self.parameterAsString(parameters, self.INPUT_FOLDER, context)
        pasta_saida = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)
        qualidade = self.parameterAsInt(parameters, self.QUALIDADE, context)

        # Caminho para o exiftool baseado na estrutura de pasta fornecida
        # Caminho do script atual
        script_path = os.path.dirname(os.path.abspath(__file__))
        # Diretório pai do script
        parent_dir = os.path.dirname(script_path)
        # Caminho para exiftool
        exiftool_path = os.path.join(parent_dir, "recuperar", "auxiliar", 
                                     "exiftool-13.27_64", "exiftool.exe")
        
        feedback.pushInfo(f"Caminho do ExifTool: {exiftool_path}")
        
        if not os.path.exists(exiftool_path):
            feedback.reportError(f"❌ ExifTool não encontrado em: {exiftool_path}")
            return {self.OUTPUT_FOLDER: pasta_saida}

        if not os.path.exists(pasta_entrada):
            raise QgsProcessingException("A pasta de entrada não existe.")
        os.makedirs(pasta_saida, exist_ok=True)

        arquivos = [f for f in os.listdir(pasta_entrada) if f.lower().endswith((".jpg", ".jpeg"))]
        total = len(arquivos)
        contador = 0

        for arquivo in arquivos:
            contador += 1
            feedback.setProgress(int(contador * 100 / total))

            caminho_entrada = os.path.join(pasta_entrada, arquivo)
            caminho_saida = os.path.join(pasta_saida, arquivo)

            try:
                feedback.pushInfo(f"Processando {arquivo}...")
                
                # Usar PIL para compactar a imagem
                try:
                    # Abrir e compactar a imagem com PIL
                    img = Image.open(caminho_entrada)
                    img.save(caminho_saida, 'JPEG', quality=qualidade, optimize=True)
                    feedback.pushInfo(f"✔ Imagem {arquivo} compactada com PIL.")
                except Exception as e:
                    feedback.reportError(f"❌ Erro ao compactar com PIL: {str(e)}")
                    continue

                # Restaurar metadados da imagem original com exiftool
                comando_exif = [
                    exiftool_path,
                    "-overwrite_original",
                    "-tagsFromFile", caminho_entrada,
                    caminho_saida
                ]
                
                feedback.pushInfo(f"Executando comando ExifTool: {' '.join(comando_exif)}")
                resultado_exif = subprocess.run(comando_exif, capture_output=True, text=True)

                if resultado_exif.returncode != 0:
                    feedback.reportError(f"⚠️ Erro ao copiar metadados: {resultado_exif.stderr}")
                else:
                    feedback.pushInfo(f"✔ {arquivo} comprimida com metadados restaurados.")

            except Exception as e:
                feedback.reportError(f"❌ Erro ao processar {arquivo}: {str(e)}")
                import traceback
                feedback.reportError(traceback.format_exc())

        return {self.OUTPUT_FOLDER: pasta_saida}

    def name(self):
        return 'comprimir_imagens'

    def displayName(self):
        return '1. Comprimir imagens JPG (PIL + ExifTool)'

    def group(self):
        return 'Compactar'

    def groupId(self):
        return 'compactar'

    def shortHelpString(self):
        return (
            'Este algoritmo comprime imagens JPG usando PIL (Pillow) '
            'e restaura os metadados originais com exiftool.'
        )
    
    def createInstance(self):
        return ComprimirImagensExifTool()