# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class TFCReportItem(scrapy.Item):
    content_url = scrapy.Field()
    source = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()  # 原始內容
    processed_content = scrapy.Field()  # 處理後的內容
    check_result = scrapy.Field()
    publish_date = scrapy.Field()
    update_date = scrapy.Field()
    categories = scrapy.Field()
    report_number = scrapy.Field()
    reporter = scrapy.Field()
    editor = scrapy.Field()
