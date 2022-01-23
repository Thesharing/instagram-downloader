import atexit
import json
import re
from typing import Union

import requestium
from bs4 import BeautifulSoup as Soup
from spiderutil.connector import Database, MongoDB
from spiderutil.log import Log
from spiderutil.path import PathGenerator, StoreByUserName
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
            'prefix': re.compile(r'<script type="text/javascript">window.__additionalDataLoaded\('),
            'start': re.compile(r'{"items":'),
            'suffix': re.compile(r'\);</script><script type="text/javascript">')
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
            page = str(soup.find('body'))

            # Extract json content from the page
            prefix_match = self.pattern['prefix'].search(page)
            stripped_str = page[prefix_match.end():]
            start_match = self.pattern['start'].search(stripped_str)
            suffix_match = self.pattern['suffix'].search(stripped_str)
            content = stripped_str[start_match.start():suffix_match.start()]

            total_count = 0

            for data in json.loads(content)['items']:

                # Get username
                contents = []
                user_name = data['user']['username']
                media_type = data['media_type']

                if media_type == 8:
                    if 'carousel_media' in data:
                        count = 0
                        for item in data['carousel_media']:
                            count += 1
                            if 'video_versions' in item:
                                # Here we assume that the first one is the original one
                                contents.append((item['video_versions'][0]['url'], MediaType.video))
                            elif 'image_versions2' in item:
                                contents.append((item['image_versions2']['candidates'][0]['url'], MediaType.image))
                            else:
                                raise ValueError('No available content found in carousel media.')
                        if 'carousel_media_count' not in data or data['carousel_media_count'] != count:
                            raise ValueError('The count of media is not equal, expected: {}, actual: {}'.format(
                                data['carousel_media_count'], count))
                    else:
                        raise ValueError('No available content found in carousel media.')
                elif media_type == 2:
                    if 'video_versions' in data:
                        contents.append((data['video_versions'][0]['url'], MediaType.video))
                    else:
                        raise ValueError('No available video found in media type 2.')
                elif media_type == 1:
                    if 'image_versions2' in data:
                        contents.append((data['image_versions2']['candidates'][0]['url'], MediaType.image))
                    else:
                        raise ValueError('No available image found in media type 1.')
                else:
                    raise ValueError('Unknown media type: {}'.format(media_type))

                for content in contents:
                    self._download_content(content[0], user_name, content[1])

                total_count += len(contents)

            self.db.insert({'link': link})
            return total_count
        except IndexError as e:
            self.logger.error(e)

    def _download_content(self, url, user_name, media_type):
        while True:
            try:
                r = self.session.get(url)
                break
            except Exception as e:
                self.logger.error(e)
        with open(self.path.generate(user_name=user_name, media_type=media_type), 'wb') as f:
            f.write(r.content)

    def quit(self):
        self.session.driver.quit()

    def __del__(self):
        self.quit()
