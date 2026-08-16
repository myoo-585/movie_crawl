import scrapy
from lxml import etree
import logging
from movie_project.items import MysqlPipeline
import re
from movie_project.utils.sign import MaoyanSigner


class ExampleSpider(scrapy.Spider):
    name = "example"
    allowed_domains = ["www.maoyan.com"]
    start_urls = ["https://www.maoyan.com/"]

    logger = logging.getLogger(__name__)

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
        # 评分(star)

        # 票房(box_office)
        yield item






        



