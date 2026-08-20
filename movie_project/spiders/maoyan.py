import scrapy
from lxml import etree
import logging
from movie_project.items import MysqlPipeline
from movie_project.utils.sign import MaoyanSigner
import requests
from urllib.parse import urlencode
import re
from io import BytesIO
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
import ddddocr
import io
import logging
import sys
import os


class ExampleSpider(scrapy.Spider):
    name = "maoyan"
    allowed_domains = ["www.maoyan.com"]
    start_urls = ["https://www.maoyan.com/"]

    logger = logging.getLogger(__name__)     

    custom_settings = {
    'DEFAULT_REQUEST_HEADERS': {
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://www.maoyan.com/',
        'Cookie': '__mta=220494759.1786338823233.1786513147600.1786513155120.15; Hm_lvt_e0bacf12e04a7bd88ddbd9c74ef2b533=1764493856; _ga=GA1.1.1953755283.1764493857; _lxsdk_cuid=19ad40791efc8-075321309c9967-26061b51-1bcab9-19ad40791efc8; _ga_WN80P4PSY7=GS2.1.s1764493856$o1$g1$t1764493929$j48$l0$h0; uuid_n_v=v1; uuid=40E47130947A11F1B6518700194C1582AA114C77B4F3451CA7CF7E4FE73B7C20; _lx_utm=utm_source%3Dgoogle%26utm_medium%3Dorganic; _lxsdk=40E47130947A11F1B6518700194C1582AA114C77B4F3451CA7CF7E4FE73B7C20; WEBDFPID=71zzxxyx52y55zxx152vw90v26w6117v80zw592uyw197958w25u4498-1786518927726-1764493882526OCMGIUIfd79fef3d01d5e9aadc18ccd4d0c95071191; utm_source_rg=AM%2599bCzCx%25338%25olyyHHfHM4fMMyHHlM4DhGzD4ShSlloDZzyhMG4EfhlGoGMZh4MEddGZ; _csrf=f5fb2128b9c4e4fac6246495785e5178f52bae5807128131885dc3d91c806ef7; hotMovieIds=1525868,1462628,1490607,1545360,1521734,1375786,1500469,1525000,1587931,1528803,1591067,1531493,1524050,38270,1545588,1516982,1413650,1487857,1490532,1552828,1429933,488,1552593,1552202,641862,75313,953,1293,1642743,1522873; old-moviepage-ci=361; __mta=220494759.1786338823233.1786438825961.1786507656565.12; _lxsdk_s=19ff4ff027e-cf5-3f4-402%7C%7C1',

        }
    }

    def parse(self, response):
        """拼接url"""
        pin_url = 'films?showType=1'
        now_url = response.urljoin(pin_url)

        yield scrapy.Request(url=now_url, callback=self.parse_detail_url)

    def parse_detail_url(self, response):
        base_url = 'https://www.maoyan.com/'


        a_str = 'ajax'
        url = base_url + a_str
        movie_list = response.xpath("//dd")
        for movie in movie_list:
            detail_url = movie.xpath(".//div[@title]/a/@href").get()
            if detail_url:
                chaos_movie_detail_url = url  + detail_url
                movie_detail_url = MaoyanSigner.build_url(chaos_movie_detail_url, webdeiver='false', yodaReady='h5')

                yield scrapy.Request(url=movie_detail_url, callback=self.parse_detail)

        
    def parse_detail(self, response):
        item = MysqlPipeline()
        # 获得电影名
        title = response.xpath("//h1/text()").get()
        item['title'] = title if title else "未获取到电影名"
        # 获得类别
        movie_type = ''
        types_list = response.xpath("//h1/following-sibling::ul/li[@class='ellipsis']/a/text()")
        for types in types_list:
            movie_type = f'{movie_type} {types.get()}'
        item['type'] = movie_type if movie_type else "未获得类别"
        # 获取国家
        lastest_country = response.xpath("string(//ul/li/a[@href='/films']/parent::li/following-sibling::li[1]/text())").get()
        if lastest_country:
            new_lastest_country = lastest_country.strip().replace(" ", "")

            country = new_lastest_country.split("\n")[0]
            item['country'] = country.strip()
            # 获得时长
            time_ = new_lastest_country.split("\n")[1]
            if time_:
                last_time = re.match("/(.*?)分钟", time_)
                item['time'] = last_time.group(1) if last_time else "没正确匹配到时长信息"
            
        # 上映时间
        last_rel_schedule = response.xpath("string(//ul/li/a[@href='/films']/parent::li/following-sibling::li[2]/text())").get()
        rel_schedule = re.match('^(.*?)[\u4e00-\u9fa5]+', last_rel_schedule)
        item['rel_schedule'] = rel_schedule.group(1) if rel_schedule else "None"
        # 简介
        synopsis = response.xpath(("//div[@class='mod-content']/span[@class='dra']/text()")).get()
        item['synopsis'] = synopsis
        # 导演
        director_actor = response.xpath("//div[@class='module']//div[@class='name']/text()")
        director = director_actor.get()
        item['director'] = director
        # 前4个主演
        actor_result = ''
        for actor in director_actor[1:]:
            actor_result = f'{actor_result} {actor.get()}'
        item['actor'] = actor_result
        # 评分(star) 票房(box_office)
        choas_font_url = response.xpath("//style[contains(text(), '@font-face')]/text()")

        chaos_text = response.xpath("//span[@class='stonefont']/text()").getall()

        # self.logger.info(f"这是字体匹配的xpath结果-->{chaos_text}")
        if chaos_text:
            unit_box_office = response.xpath("//span[@class='unit']/text()").get()
            for choas_font in choas_font_url:
                mat = re.search('\,url\("(.*\.woff)"', choas_font.get().strip())

                if mat:
                    font_url = f"https:{mat.group(1)}"
                    # self.logger.info(f"这是匹配并拼接好的woff_url结果-->{font_url}")
                    finally_result = response.xpath("//span[contains(@class, 'index-left no-info')]/text()").get()
                    
                    
                else:
                    print("正则并没有匹配到")

        yield scrapy.Request(
            url=font_url,
            callback=self.woff_url,
            cb_kwargs={'item': item, 
                       'chaos_text':chaos_text,
                       'finally_result':finally_result,
                       'unit_box_office':unit_box_office
                       },
            dont_filter=True  # 强制不去重
        )


    def woff_url(self, response, item, chaos_text, finally_result, unit_box_office):
        pin = f"{item['title'][:5]}"
        woff_name = pin + '.woff'
        ttf_name = pin + '.ttf'
        
        woff_data = BytesIO(response.body)
        # .woff --> .ttf
        font = TTFont(woff_data)
        # 映射
        cmap = font.getBestCmap()
        # 字体加载
        ttf_data = BytesIO()
        font.flavor = None
        font.save(ttf_data)
        ttf_data.seek(0)
        pil_font = ImageFont.truetype(ttf_data, 40)
        # 
        ocr = ddddocr.DdddOcr()
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
            result = ocr.classification(img_bytes.getvalue())

            if result.isdigit():
                mapping[hex(k)] = result
                self.logger.info(f"这是映射表mapping的结果-->{mapping}")

        # 完整情况
        message_font = chaos_text
        self.logger.info(f"这是字体匹配的xpath结果-->{chaos_text}")

        if mapping:
            star_list = []
            people_list = [] # 评分人数
            box_offic_list = []

            if len(chaos_text) == 3:

                for j in range(len(message_font)):
                    if j == 0:
                        for i in message_font[j]:
                            if i == '.':
                                star_list.append('.')
                                continue

                            real_value = mapping.get(hex(ord(i)), i)
                            star_list.append(real_value) # 评分
                    # 评分人数
                    # elif j == 1:
                    #     for i in message_font[j]:

                    #         if i == '.':
                    #             people_list.append('.')
                    #             continue  
                    #         elif i == '万':
                    #             people_list.append('万')
                    #             continue

                    #         real_value = mapping.get(hex(ord(i)), i)
                    #         people_list.append(real_value)
                    elif j == 2:
                        for i in message_font[j]:

                            if i == '.':
                                box_offic_list.append('.')
                                continue  

                            real_value = mapping.get(hex(ord(i)), i)
                            box_offic_list.append(real_value)
                star = ''.join(star_list)
                item['star'] = star
                # people = ''.join(people_list) # 评分人数

                box_office = ''.join(box_offic_list)
                item['box_office'] = f"{box_office}{unit_box_office}"
                if box_office and star:
                    self.logger.info(f"票房：{box_office}， 评分：{star}")
                else:
                    self.logger.info(f"票房， 评分并未获取到")
                yield item
            elif len(chaos_text) == 2: # 想看数 + box_office
                for i in message_font[1]:

                    if i == '.':
                        box_offic_list.append('.')
                        continue  

                    real_value = mapping.get(hex(ord(i)), i)
                    box_offic_list.append(real_value)
                box_office = ''.join(box_offic_list)
                item['box_office'] = f"{box_office}{unit_box_office}"
                item['star'] = "暂无评分"
                yield item

            elif len(chaos_text) == 1: # 想看数 / 票房
                if finally_result == "暂无":
                    for i in message_font[0]:

                        if i == '.':
                            box_offic_list.append('.')
                            continue  

                        real_value = mapping.get(hex(ord(i)), i)
                        box_offic_list.append(real_value)
                    box_office = ''.join(box_offic_list)
                    item['box_office'] = f"{box_office}{unit_box_office}"
                    item['star'] = "暂无评分"
                    yield item
                    
                else:
                    item['star'] = '暂无评分'
                    item['box_office'] = '暂无票房'
                    yield item



