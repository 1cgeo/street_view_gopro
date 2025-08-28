from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSlot
import os
from PIL import Image, ImageFilter
import numpy as np

class BlurTask(QRunnable):
    def __init__(self, filename, inputFolder, outputFolder, maskPath, coat_mask_path, blur_strength):
        super().__init__()
        self.filename = filename
        self.inputFolder = inputFolder
        self.outputFolder = outputFolder
        self.maskPath = maskPath
        self.coat_mask_path = coat_mask_path
        self.blur_strength = blur_strength

    @pyqtSlot()
    def run(self):
        try:
            blur_mask = Image.open(self.maskPath)
            coat_mask = Image.open(self.coat_mask_path).convert("RGBA")

            jpg_path = os.path.join(self.inputFolder, self.filename)
            base_image = Image.open(jpg_path).convert("RGB")

            blur_mask_resized = blur_mask.resize(base_image.size, Image.LANCZOS)
            coat_mask_resized = coat_mask.resize(base_image.size, Image.LANCZOS)

            # blur
            blurred = base_image.filter(ImageFilter.GaussianBlur(radius=self.blur_strength//3))
            base_array = np.array(base_image)
            blurred_array = np.array(blurred)
            mask_array = np.array(blur_mask_resized.convert("L")).astype(np.float32) / 255.0

            result = base_array.astype(np.float32)
            for c in range(3):
                result[:, :, c] = mask_array * blurred_array[:, :, c] + (1-mask_array) * base_array[:, :, c]
            result_img = Image.fromarray(np.clip(result, 0, 255).astype(np.uint8))

            # coat overlay
            result_img = Image.alpha_composite(result_img.convert("RGBA"), coat_mask_resized).convert("RGB")

            output_path = os.path.join(self.outputFolder, self.filename)
            result_img.save(output_path, quality=95)

            print(f"Processado: {self.filename}")
        except Exception as e:
            print(f"Erro {self.filename}: {e}")


class ApplyBlurMask:
    def __init__(self, blur_strength=80):
        self.blur_strength = blur_strength

    def apply(self, inputFolder, outputFolder, maskPath, imageLayer):
        imagens = os.listdir(inputFolder)
        names = [feat['nome_img'] for feat in imageLayer.getFeatures()]
        targets = [f for f in sorted(imagens) if f.endswith((".jpg", ".jpeg")) and f[:-4] in names]

        current_file = os.path.abspath(__file__)
        current_dir = os.path.dirname(current_file)
        while not os.path.basename(current_dir) == "street_view_plugin" and current_dir != "/":
            current_dir = os.path.dirname(current_dir)

        coat_mask_path = os.path.join(current_dir, "resources", "masks", "coat_mask.png")
        if not os.path.exists(coat_mask_path):
            raise FileNotFoundError(f"Arquivo coat_mask.png não encontrado: {coat_mask_path}")

        pool = QThreadPool.globalInstance()
        print(f"⚙️ Usando até {pool.maxThreadCount()} threads Qt")

        for filename in targets:
            task = BlurTask(filename, inputFolder, outputFolder, maskPath, coat_mask_path, self.blur_strength)
            pool.start(task)

        pool.waitForDone()  # esperar terminar tudo
        print("✅ Processamento finalizado")
