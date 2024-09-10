import os
from PIL import Image

class ApplyMask:


    def apply(self, inputFolder, outputFolder, maskPath, imageLayer):
        imagens = os.listdir(inputFolder)
        overlay = Image.open(maskPath).convert("RGBA")
        names = [feat['nome_img'] for feat in imageLayer.getFeatures()]
        for filename in sorted(imagens):
            if filename[:-4] not in names:
                continue
            if filename.endswith(".jpg") or filename.endswith(".jpeg"):
                jpg_path = os.path.join(inputFolder, filename)
                # Carregar a imagem JPG
                base_image = Image.open(jpg_path).convert("RGBA")
                # Redimensionar a imagem de sobreposição para o tamanho da imagem base
                overlay_resized = overlay.resize(base_image.size)
                # Sobrepor as imagens
                combined = Image.alpha_composite(base_image, overlay_resized)
                # Converter a imagem combinada de volta para o modo RGB e salvar
                combined = combined.convert("RGB")
                output_path = os.path.join(outputFolder, filename)
                combined.save(output_path)