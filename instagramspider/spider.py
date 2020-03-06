import atexit
import json
import re
from typing import Union

import requestium
from bs4 import BeautifulSoup as Soup

from spiderutil.connector import Database, MongoDB
from spiderutil.path import PathGenerator, StoreByUserName
from spiderutil.log import Log
from spiderutil.typing import MediaType


class InstagramSpider:

    def __init__(self, driver_path,
                 cookies: dict,
                 db: Database = None,
                 path: Union[PathGenerator, str] = None,
                 proxies: dict = None,
                 timeout: int = 15,
                 no_window: bool = False,
                 logger=None):

        options = {
            'arguments': [
                '--headless',
                '--window-size=1920,1080'
            ]
        } if no_window else {
            'arguments': [
                '--start-maximized'
            ]
        }

        # https://chromedriver.chromium.org/downloads
        self.session = requestium.Session(webdriver_path=driver_path,
                                          browser='chrome',
                                          default_timeout=timeout,
                                          webdriver_options=options)

        for key, value in cookies.items():
            self.session.driver.ensure_add_cookie({
                'name': key,
                'value': value,
                'domain': '.instagram.com'
            })
        self.session.transfer_driver_cookies_to_session()
        self.session.proxies = proxies
        self.session.headers = {
            'user-agent': self.session.driver.execute_script("return navigator.userAgent;")
        }
        self.session.default_timeout = timeout

        self.db = MongoDB('instagram', primary_key='link') if db is None else db

        if path is None:
            self.path = StoreByUserName('./download')
        elif path is str:
            self.path = StoreByUserName(path)
        else:
            self.path = path

        self.pattern = {
            'content': re.compile(r'("display_url"|"display_src"|"video_url"):"(.+?)"'),
            'owner': re.compile(r'"owner":({.+?})'),
            'username': re.compile(r'"username":"(.+?)"')
        }

        self.logger = Log.create_logger('InstagramSpider', './instagram.log') if logger is None else logger

        atexit.register(self.quit)

    @property
    def driver(self):
        return self.session.driver

    def get_saved_list(self, user):
        url = 'https://www.instagram.com/{}/saved/'.format(user)
        links = []
        end = False
        self.session.driver.get(url)

        def extract_list():
            self.session.driver.ensure_element_by_xpath(
                '//*[@id="react-root"]/section/main/div/div[3]/article/div[1]/div/div[last()]')
            article = self.session.driver.find_element_by_tag_name('article')
            photos = article.find_elements_by_tag_name('a')
            for photo in photos:
                link = photo.get_property('href')
                if link in self.db:
                    nonlocal end
                    end = True
                    break
                if link not in links:
                    links.append(link)

        extract_list()
        while not end:
            self.session.driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            extract_list()

        links.reverse()
        return links

    def download(self, link: str):
        while True:
            try:
                r = self.session.get(link)
                break
            except Exception as e:
                self.logger.error(e)
        soup = Soup(r.text, 'lxml')
        try:
            page = soup.find('body').text
            res = self.pattern['content'].findall(page)
            contents = []
            for item in res:
                img_link = item[1].replace('\\u0026', '&').replace('\\', '')
                if img_link not in contents:
                    contents.append(img_link)
            owner_str = self.pattern['owner'].findall(page)[-1]
            username = self.pattern['username'].findall(owner_str)[-1]
            for content in contents:
                while True:
                    try:
                        r = self.session.get(content)
                        break
                    except Exception as e:
                        self.logger.error(e)
                media_type = MediaType.video if 'video' in r.headers['Content-Type'] else MediaType.image
                with open(self.path.generate(user_name=username, media_type=media_type), 'wb') as f:
                    f.write(r.content)
            self.db.insert({'link': link})
            return len(contents)
        except IndexError as e:
            self.logger.error(e)

    def quit(self):
        self.session.driver.quit()

    def __del__(self):
        self.quit()
