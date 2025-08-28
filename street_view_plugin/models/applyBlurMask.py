import os
from PIL import Image, ImageFilter
import numpy as np

class ApplyBlurMask:
    
    def __init__(self, blur_strength=80):
        """
        Inicializa a classe com duas máscaras separadas
        
        Args:
            blur_strength: Intensidade do blur (recomendado valores entre 10-30)
        """
        self.blur_strength = blur_strength

    def apply_selective_blur_with_separate_masks(self, base_image, blur_mask, coat_mask):
        """
        Aplica blur seletivo usando duas máscaras separadas:
        - blur_mask: define onde aplicar o blur (fundo branco)
        - coat_mask: brasões com fundo transparente para sobrepor no final
        """
        # Converter blur_mask para escala de cinza se necessário
        if blur_mask.mode != 'L':
            blur_mask_gray = blur_mask.convert('L')
        else:
            blur_mask_gray = blur_mask
        
        # Converter para arrays numpy
        base_array = np.array(base_image)
        blur_mask_array = np.array(blur_mask_gray).astype(np.float32) / 255.0
        
        # Aplicar blur gaussiano na imagem base
        blurred_pil = base_image.filter(ImageFilter.GaussianBlur(radius=self.blur_strength//3))
        blurred_array = np.array(blurred_pil)
        
        # Misturar imagem original com blur usando a máscara
        result_array = base_array.astype(np.float32)
        blurred_array = blurred_array.astype(np.float32)
        
        for channel in range(3):  # RGB
            result_array[:, :, channel] = (
                blur_mask_array * blurred_array[:, :, channel] +  # Blur onde máscara é branca
                (1 - blur_mask_array) * base_array[:, :, channel]  # Original onde máscara é preta
            )
        
        # Converter de volta para PIL
        result_image = Image.fromarray(np.clip(result_array, 0, 255).astype(np.uint8))
        
        # Sobrepor os brasões por cima do resultado
        if coat_mask.mode == 'RGBA':
            # Redimensionar máscara dos brasões se necessário
            if coat_mask.size != result_image.size:
                coat_mask_resized = coat_mask.resize(result_image.size, Image.LANCZOS)
            else:
                coat_mask_resized = coat_mask
            
            # Converter resultado para RGBA para composição
            result_rgba = result_image.convert('RGBA')
            
            # Compor brasões sobre a imagem com blur
            final_result = Image.alpha_composite(result_rgba, coat_mask_resized)
            
            # Converter de volta para RGB
            return final_result.convert('RGB')
        else:
            return result_image

    def apply(self, inputFolder, outputFolder, maskPath, imageLayer):
        """
        Método principal com duas máscaras separadas:
        - maskPath: máscara com fundo branco para definir área de blur
        - coat_mask: brasões com fundo transparente (endereço fixo no plugin)
        """
        imagens = os.listdir(inputFolder)
        
        # Carregar máscara de blur
        blur_mask = Image.open(maskPath)  # Máscara de blur (fundo branco)
        
        # Carregar máscara dos brasões do endereço fixo
        # Obter o diretório do arquivo atual e subir até encontrar street_view_plugin
        current_file = os.path.abspath(__file__)
        current_dir = os.path.dirname(current_file)
        
        # Subir diretórios até encontrar street_view_plugin
        while not os.path.basename(current_dir) == "street_view_plugin" and current_dir != "/":
            current_dir = os.path.dirname(current_dir)
            
        coat_mask_path = os.path.join(current_dir, "resources", "masks", "coat_mask.png")
        
        if not os.path.exists(coat_mask_path):
            raise FileNotFoundError(f"Arquivo de máscara dos brasões não encontrado: {coat_mask_path}")
            
        coat_mask = Image.open(coat_mask_path).convert("RGBA")  # Brasões com transparência
        
        names = [feat['nome_img'] for feat in imageLayer.getFeatures()]
        
        for filename in sorted(imagens):
            if filename[:-4] not in names:
                continue
                
            if filename.endswith(".jpg") or filename.endswith(".jpeg"):
                jpg_path = os.path.join(inputFolder, filename)
                
                try:
                    # Carregar a imagem JPG
                    base_image = Image.open(jpg_path).convert("RGB")
                    
                    # Redimensionar máscaras para o tamanho da imagem base
                    blur_mask_resized = blur_mask.resize(base_image.size, Image.LANCZOS)
                    coat_mask_resized = coat_mask.resize(base_image.size, Image.LANCZOS)
                    
                    # Aplicar blur seletivo e sobrepor brasões
                    result_image = self.apply_selective_blur_with_separate_masks(
                        base_image, 
                        blur_mask_resized, 
                        coat_mask_resized
                    )
                    
                    # Salvar resultado
                    output_path = os.path.join(outputFolder, filename)
                    result_image.save(output_path, quality=95)
                    
                    print(f"Processado: {filename}")
                    
                except Exception as e:
                    print(f"Erro ao processar {filename}: {str(e)}")