import re
import logging
from lxml import etree
logger = logging.getLogger(__name__)


class MovieInfoParser:
    """电影信息解析类"""
    def __init__(self, response):
        self.response = response

    
    def extract_title(self):
        """获得电影名"""
        title = self.response.xpath("//h1/text()").get()
        return title if title else "未获取到电影名"


    def extract_type(self):
        """获得电影分类"""
        types_list = self.response.xpath("//h1/following-sibling::ul/li[@class='ellipsis']/a/text()")
        movie_type = "".join(t.get() for t in types_list)
        return movie_type if movie_type else "未获得类别"


    def extract_country_time(self):
        """获取国家和电影时长"""
        lastest_country_time = self.response.xpath("string(//ul/li/a[@href='/films']/parent::li/following-sibling::li[1]/text())").get()
        if not lastest_country_time:
            return "未获取到国家信息", "未获取到时长"
        
        new_lastest_country_time = lastest_country_time.strip().replace(" ", "")
        parts = new_lastest_country_time.split("\n")
        
        country = parts[0].strip()
        duration = "未获取到时长"

        if len(parts) > 1 and parts[1]:
            last_time = re.match("/(\d+)分钟", parts[1])
            duration = last_time.group(1) if last_time else "没正确匹配到时长信息"

        return country, duration 


    def extract_rel_schedule(self):
        """上映时间"""
        last_rel_schedule = self.response.xpath("string(//ul/li/a[@href='/films']/parent::li/following-sibling::li[2]/text())").get()
        if not last_rel_schedule:
            return "上映时间未获取"
        rel_schedule = re.match('^(.*?)[\u4e00-\u9fa5]+', last_rel_schedule)
        return rel_schedule.group(1) if rel_schedule else "未获得上映时间"


    def extract_synopsis(self):
        """简介"""
        synopsis = self.response.xpath("//div[@class='mod-content']/span[@class='dra']/text()").get()
        return synopsis if synopsis else "未获得简介"


    def extract_director_actor(self):
        """导演和主演（共计5个）"""
        director_actor = self.response.xpath("//div[@class='module']//div[@class='name']/text()")
        if not director_actor:
            return "导演和主演的正则出了问题", "导演和主演的正则出了问题"
        
        director = director_actor.get()
        actor_result = "".join(a.get() for a in director_actor[1:5])
        return director, actor_result