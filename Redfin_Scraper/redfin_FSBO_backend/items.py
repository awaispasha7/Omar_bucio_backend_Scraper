# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class RedfinScraperItem(scrapy.Item):
    Name = scrapy.Field()
    Beds_Baths = scrapy.Field()
    Phone_Number = scrapy.Field()
    Asking_Price = scrapy.Field()
    Days_On_Redfin = scrapy.Field()
    Address = scrapy.Field()
    YearBuilt = scrapy.Field()
    Agent_Name = scrapy.Field()
    Url = scrapy.Field()
    Owner_Name = scrapy.Field()
    Email = scrapy.Field()
    Mailing_Address = scrapy.Field()
    Square_Feet = scrapy.Field()
