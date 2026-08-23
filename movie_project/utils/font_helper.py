import logging
from io import BytesIO
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
import ddddocr
import io

logger = logging.getLogger(__name__)


class FontHelper:
    """字体反爬处理工具类"""
    def __init__(self):
        """字体反爬处理工具类"""
        # 初始化OCR引擎
        self.ocr = ddddocr.DdddOcr()
        logger.info(f"FontHelper类初始化完成")


    def build_font_mappping(self, font_data):
        """建立映射表"""

        font = TTFont(font_data)
        cmap = font.getBestCmap()
        # 字体加载
        ttf_data = BytesIO()
        font.flavor = None
        font.save(ttf_data)
        ttf_data.seek(0)
        pil_font = ImageFont.truetype(ttf_data, 40)

        mapping = {}

        for k, v in cmap.items():
            # 绘画
            img = Image.new("L", (60, 60), "white")
            draw = ImageDraw.Draw(img)
            draw.text((10, 5), chr(k), font=pil_font, fill="black")
            # 缓存到字节流
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            # 识别
            result = self.ocr.classification(img_bytes.getvalue())
            img_bytes.close()

            if result.isdigit():
                mapping[hex(k)] = result
        logger.info(f"字体映射构建成功，这是映射表mapping的结果-->{mapping}")
        return mapping


    def method(self, text, mapping):
        """通用方法"""
        result = []

        for i in text:
            if i == '.':
                result.append('.')
                continue

            real_value = mapping.get(hex(ord(i)), i)
            result.append(real_value)
        return ''.join(result)


    def decrypt_number(self, data_type, mapping, unit_box_office, finally_result):
        """解开评分和票房的加密"""

        if len(data_type) == 3:

            star = self.method(data_type[0], mapping)
            box_office = self.method(data_type[2], mapping)

            if box_office and star:
                logger.info(f"票房：{box_office}， 评分：{star}")

            else:
                logger.info(f"票房， 评分并未获取到")

            return star, f"{box_office}{unit_box_office}"

        elif len(data_type) == 2: # 想看数 + box_office

            box_office = self.method(data_type[1], mapping)
            return "暂无评分", f"{box_office}{unit_box_office}"

        elif len(data_type) == 1: # 想看数 / 票房
            if finally_result == "暂无":
                box_office = self.method(data_type[0], mapping)
                return "暂无评分", f"{box_office}{unit_box_office}"
                
            else:
                return "暂无评分", "暂无票房"
