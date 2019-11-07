from instagramspider import CookieReader, InstagramSpider
from spiderutil.connector import MongoDB
from spiderutil.log import Log

if __name__ == '__main__':
    # 1. Get cookie from instagram.com after you logged in
    cookies = CookieReader.from_local_file('./cookie.txt')
    # 2. Use MongoDB to save links
    db = MongoDB('instagram', primary_search_key='link')
    db.check_connection()
    # 3. Declare the spider, you need to specify:
    # the location of chromedriver, the cookies, the proxies (if necessary),
    # the database, and the path generator
    spider = InstagramSpider(driver_path='./chromedriver.exe',
                             cookies=cookies,
                             proxies={
                                 'https': 'http://127.0.0.1:1080'
                             },
                             db=db)
    # Use logger to log
    logger = Log.create_logger(name='InstagramSpider', path='./instagram.log')
    # 4. Get links from saved, will stop if met duplicate link in the database
    links = spider.get_saved_list('<Your Username>')
    logger.info('Total: {}'.format(len(links)))
    # 5. Download the links
    for link in links:
        logger.info(link)
        count = spider.download(link)
        logger.info(count)
