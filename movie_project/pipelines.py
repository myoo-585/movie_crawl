# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
# pipelines.py
from twisted.enterprise import adbapi # 异步操作
from itemadapter.adapter import ItemAdapter # 用来实例化
import pymysql


class MysqlPipeline:
    def __init__(self, dbpool):
        self.dbpool = dbpool

    @classmethod
    def from_settings(cls, settings):
        """从settings读取数据库配置"""
        dbparams = dict(
            host=settings['MYSQL_HOST'],
            port=settings['MYSQL_PORT'],
            db=settings['MYSQL_DB'],
            user=settings['MYSQL_USER'],
            passwd=settings['MYSQL_PASSWORD'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor, # 字典游标
            use_unicode=True,
        )
        dbpool = adbapi.ConnectionPool('pymysql', **dbparams)
        instance = cls(dbpool)
        instance.dbpool.runInteraction(instance.create_table).addErrback(
            lambda f: print(f"建表失败: {f}")
        )
        return instance

    def process_item(self, item, spider):
        """异步插入"""
        query = self.dbpool.runInteraction(self.do_insert, item)
        query.addErrback(self.handle_error, item, spider)
        return item

    def create_table(self, cursor):
        """建表(mysql)"""
        sql = """ CREATE TABLE IF NOT EXISTS maoyan_movie(
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            type VARCHAR(100),
            director VARCHAR(50),
            actor VARCHAR(255),
            country VARCHAR(50),
            synopsis TEXT,
            rel_schedule VARCHAR(20),
            time INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) 
        """
        cursor.execute(sql)

        alter_sqls = [
            "ALTER TABLE maoyan_movie ADD COLUMN star VARCHAR(50) COMMENT 'star'",
            "ALTER TABLE maoyan_movie ADD COLUMN box_office VARCHAR(50) COMMENT 'box_office'",
        ]

        for sql in alter_sqls:
            try:
                cursor.execute(sql)
            except Exception as e:
                if "Duplicate column name" not in str(e):
                    raise e

    def do_insert(self, cursor, item):
        adapter = ItemAdapter(item)
        cursor.execute("""
            INSERT INTO maoyan_movie (title, type, star, box_office, director, actor, country, synopsis, rel_schedule, time) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            adapter.get('title'),
            adapter.get('type'),            
            adapter.get('star'),            
            adapter.get('box_office'),
            adapter.get('director'),
            adapter.get('actor'),
            adapter.get('country'),
            adapter.get('synopsis'),
            adapter.get('rel_schedule'),
            adapter.get('time'),

        ))

    def handle_error(self, failure, item, spider):
        spider.logger.error(f"数据库插入失败: {failure}")
