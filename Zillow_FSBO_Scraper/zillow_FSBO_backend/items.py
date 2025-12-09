# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ZillowScraperItem(scrapy.Item):
    Detail_URL = scrapy.Field()
    Address = scrapy.Field()
    Bedrooms = scrapy.Field()
    Bathrooms = scrapy.Field()
    Price = scrapy.Field()
    Home_Type = scrapy.Field()
    Year_Build = scrapy.Field()
    HOA = scrapy.Field()
    Days_On_Zillow = scrapy.Field()
    Page_View_Count = scrapy.Field()
    Favorite_Count = scrapy.Field()
    Phone_Number = scrapy.Field()
