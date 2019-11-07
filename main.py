from instagramspider import CookieReader, InstagramSpider
from spiderutil.connector import MongoDB
from spiderutil.log import Log

if __name__ == '__main__':
    # Get cookie from instagram.com after you logged in
    cookies = CookieReader.from_local_file('./cookie.txt')
    # Use MongoDB to save links
    db = MongoDB('instagram', primary_search_key='link')
    db.check_connection()
    # Declare the spider, you need to specify:
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
    # Get links from saved, will stop if met duplicate link in the database
    links = spider.get_saved_list('<Your Username>')
    logger.info('Total: {}'.format(len(links)))
    # Download the link
    for link in links:
        logger.info(link)
        count = spider.download(link)
        logger.info(count)
