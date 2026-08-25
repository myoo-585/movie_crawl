import scrapy
import re
import logging
from io import BytesIO
from movie_project.items import MysqlPipeline
from movie_project.utils.sign import MaoyanSigner
from urllib.parse import urlencode
from urllib.parse import urljoin
from movie_project.utils.movie_parser import MovieInfoParser
from movie_project.utils.font_helper import FontHelper

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
        """入口:正在热映电影url"""
        now_url = response.urljoin('films?showType=1&offset=0')
        yield scrapy.Request(url=now_url, 
                             callback=self.next_url_parse)


    def next_url_parse(self, response):
        judge_con = response.xpath("//ul[@class='list-pager']/li/a/text()").getall()
        movie_page_count = len(judge_con) - 1
        self.logger.info(f"当前的url有：{movie_page_count}个页面")
        if movie_page_count <= 0:
            return self.logger.info("长度不够无法进行页面循环")
        # url_parts = response.url.split("offset=")
        # current_offset = int(url_parts[1].split("&")[0]) if len(url_parts) >= 2 else 0 
        for movie_num in range(1, movie_page_count+1):
            
            offset = (movie_num - 1) * 18
            if offset == 0:
                next_url = f"https://www.maoyan.com/films?showType=1"
        
            else:
                next_url = f"https://www.maoyan.com/films?showType=1&offset={offset}"
            yield scrapy.Request(url=next_url, callback=self.parse_detail_url)


    def parse_detail_url(self, response):
        """拼接访问具体电影url"""

        movie_list = response.xpath("//dd")
        if not movie_list:
            self.logger.warning(f"页面结构发生变化，请在网页查看并更改")
        self.logger.info(f"正在拼接各个电影具体的url...")
        
        try:
            for movie in movie_list:    
                detail_url = movie.xpath(".//div[@title]/a/@href").get()
                if detail_url:
                    detail_url = detail_url.lstrip('/')
                    chaos_movie_detail_url = urljoin('https://www.maoyan.com/ajax/', detail_url)
                    self.logger.info(f"拼接的url是：{chaos_movie_detail_url}")
                    movie_detail_url = MaoyanSigner.build_url(chaos_movie_detail_url, webdeiver='false', yodaReady='h5')
                    if movie == movie_list[-1]:
                        self.logger.info(f"电影详情页：{movie_detail_url}")
                    yield scrapy.Request(url=movie_detail_url, callback=self.parse_detail)
            self.logger.info(f"各个电影的详情页面爬取完毕,共计:{len(movie_list)}")


        except Exception as e:
            self.logger.error(f"解析电影条目失败：{e}")

        
    def parse_detail(self, response):
        
        try:
            self.logger.info(f"正在获取具体的信息...")
            item = MysqlPipeline()
            movie_parser = MovieInfoParser(response)
            # 获得电影名
            title = movie_parser.extract_title()
            item['title']=title
            # 获得类别
            type = movie_parser.extract_type()
            item['type']=type
            # 获取国家和时长
            country, time = movie_parser.extract_country_time()
            item['country']=country
            item['time']=time
            # 上映时间
            rel_schedule = movie_parser.extract_rel_schedule()
            item['rel_schedule']=rel_schedule
            # 简介
            synopsis = movie_parser.extract_synopsis()
            item['synopsis']=synopsis
            # 导演和主演
            director, actor = movie_parser.extract_director_actor()
            item['director']=director
            item['actor']=actor

            # 评分(star) 票房(box_office)
            self.logger.info(f"{item}")
            choas_font_url = response.xpath("//style[contains(text(), '@font-face')]/text()")

            chaos_text = response.xpath("//span[@class='stonefont']/text()").getall()

            self.logger.info(f"这是字体匹配的xpath结果-->{chaos_text}")
            if chaos_text:
                self.logger.info(f"成功匹配到字体匹配的xpath结果-->{chaos_text}")
                unit_box_office = response.xpath("//span[@class='unit']/text()").get()
                for choas_font in choas_font_url:
                    mat = re.search('\,url\("(.*\.woff)"', choas_font.get().strip())

                    if mat:
                        font_url = f"https:{mat.group(1)}"
                        self.logger.info(f"这是匹配并拼接好的woff_url结果-->{font_url}")
                        finally_result = response.xpath("//span[contains(@class, 'index-left no-info')]/text()").get()

                        self.logger.info(f"正在前往下一个函数进行评分和票房的获取...")
                        yield scrapy.Request(
                            url=font_url,
                            callback=self.font_crackANDstar_box_office,
                            cb_kwargs={'item': item, 
                                    'chaos_text':chaos_text,
                                    'finally_result':finally_result,
                                    'unit_box_office':unit_box_office
                                    },
                            dont_filter=True  # 强制不去重
                        )
                        break
                    else:
                        self.logger.info(f"匹配并拼接好的woff_url结果的font_url没有匹配到")
            else:
                self.logger.info(f"字体匹配的xpath的结果chaos_text没有匹配到")
        except Exception as e:
            self.logger.error(f"解析详情页出错：{e}")
            


    def font_crackANDstar_box_office(self, response, item, chaos_text, finally_result, unit_box_office):
        self.font_helper = FontHelper()
        self.logger.info(f"运行到评分位置")
        font_data = BytesIO(response.body)
        mapp = self.font_helper.build_font_mappping(font_data)
        star, box_office = self.font_helper.decrypt_number(chaos_text, mapp, unit_box_office, finally_result)
        item['star']=star
        item['box_office']=box_office if box_office else "暂无票房"

        self.logger.info(f"具体信息获取完毕！")
        yield item

