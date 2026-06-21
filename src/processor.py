# 图片处理核心逻辑
import os
import io
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np

try:
    from rembg import remove, new_session
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False


class ImageProcessor:
    def __init__(self, model_name="u2net"):
        self.model_name = model_name
        self.session = None
        if HAS_REMBG:
            try:
                self.session = new_session(model_name)
            except Exception:
                self.session = None

    def remove_background(self, image):
        """AI 智能抠图"""
        if not HAS_REMBG or self.session is None:
            raise RuntimeError("rembg 模型未加载，请检查网络连接后重试")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        result_bytes = remove(img_bytes.getvalue(), session=self.session)
        return Image.open(io.BytesIO(result_bytes)).convert("RGBA")

    def fill_background(self, image, color=(255, 255, 255)):
        """填充背景色（白底）"""
        w, h = image.size
        bg = Image.new("RGBA", (w, h), color + (255,))
        bg.paste(image, (0, 0), image)
        return bg

    def resize_for_platform(self, image, target_size, fill_color=(255, 255, 255)):
        """适配平台尺寸 - 等比缩放并居中填充"""
        tw, th = target_size
        iw, ih = image.size
        ratio = min(tw / iw, th / ih)
        new_w, new_h = int(iw * ratio), int(ih * ratio)
        resized = image.resize((new_w, new_h), Image.LANCZOS)

        canvas = Image.new("RGBA", (tw, th), fill_color + (255,))
        x, y = (tw - new_w) // 2, (th - new_h) // 2
        canvas.paste(resized, (x, y), resized if resized.mode == "RGBA" else None)
        return canvas

    def add_watermark(self, image, text, position="br", opacity=128):
        """添加文字水印"""
        from PIL import ImageDraw, ImageFont
        img = image.convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        font_size = max(12, min(img.size) // 20)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        margin = 10

        positions = {
            "tl": (margin, margin),
            "tr": (img.width - tw - margin, margin),
            "bl": (margin, img.height - th - margin),
            "br": (img.width - tw - margin, img.height - th - margin),
            "center": ((img.width - tw) // 2, (img.height - th) // 2),
        }
        x, y = positions.get(position, positions["br"])

        draw.text((x, y), text, font=font, fill=(255, 255, 255, opacity))
        img = Image.alpha_composite(img, overlay)
        return img

    def auto_enhance(self, image):
        """自动色彩增强"""
        img = image.convert("RGB")
        enhancers = [
            ("Color", 1.1),
            ("Contrast", 1.05),
            ("Brightness", 1.05),
            ("Sharpness", 1.2),
        ]
        for name, factor in enhancers:
            enhancer = getattr(ImageEnhance, name)(img)
            img = enhancer.enhance(factor)
        return img

    def process(self, image, options):
        """完整处理流程"""
        results = {"steps": [], "image": image}

        # 1. 抠图
        if options.get("remove_bg"):
            results["image"] = self.remove_background(results["image"])
            results["steps"].append("抠图完成")

        # 2. 背景填充
        if options.get("fill_bg"):
            color = options.get("bg_color", (255, 255, 255))
            results["image"] = self.fill_background(results["image"], color)
            results["steps"].append("背景填充")

        # 3. 自动增强
        if options.get("auto_enhance"):
            results["image"] = self.auto_enhance(results["image"])
            results["steps"].append("自动增强")

        # 4. 尺寸适配
        if options.get("target_size"):
            results["image"] = self.resize_for_platform(
                results["image"],
                options["target_size"],
                options.get("fill_color", (255, 255, 255)),
            )
            results["steps"].append(f"适配尺寸 {options['target_size']}")

        # 5. 水印
        if options.get("watermark_text"):
            results["image"] = self.add_watermark(
                results["image"],
                options["watermark_text"],
                options.get("watermark_position", "br"),
                options.get("watermark_opacity", 128),
            )
            results["steps"].append("添加水印")

        return results
