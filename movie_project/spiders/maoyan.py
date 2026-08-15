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
        lastest_country_time = response.xpath("string(//ul/li/a[@href='/films']/parent::li/following-sibling::li[1]/text())").get()
        # if lastest_country:
        #     last_country = re.match("^(.*)/", lastest_country.strip())
        #     country = last_country.group(1) if last_country else "未找到国家名"
        # chaos_country = lastest_country_time.split('\n')[0].split('/')
        # 获得时长
        # if chaos_country:
        #     country = chaos_country[0].strip()
            
        match = re.search(r'^(.*?)\s*/\s(.*?)分钟', lastest_country_time)

        if match:
            country = match.group(1)  # 提取第一个括号：国家
            item['country'] = country
            time = match.group(2) # 提取第二个括号：数字
            item['time'] = time
        else:
            country, duration = '未知', '0'
        
        # chaos_time = lastest_country_time.split('\n')[1].split('/')
        # if chaos_time:
        #     time = chaos_time[1].strip().replace("分钟", '')

        # 
        # last_time = re.match('/\s(.*?)$', lastest_country)
        # if last_time:
        #     time = last_time.group(1)
            
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






        



