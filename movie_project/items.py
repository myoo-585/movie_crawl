# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class MysqlPipeline(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    title = scrapy.Field()
    # star = scrapy.Field()
    # box_office = scrapy.Field() # 票房
    type = scrapy.Field()    
    director = scrapy.Field()
    actor = scrapy.Field()
    country = scrapy.Field()
    synopsis = scrapy.Field() # 简介
    rel_schedule = scrapy.Field() # 上映时间 
    time = scrapy.Field()   
    pass
