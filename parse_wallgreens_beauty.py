from bs4 import BeautifulSoup
import os
import urllib2
from selenium import webdriver
from selenium.webdriver.support.ui import Select
import time
import pandas as pd


class Walgreen_Parser(object):
    def __init__(self):
        self.category_links = [['cosmetics', 'https://www.walgreens.com/store/c/cosmetics/ID=360337-tier2general'],
                               ['hair-care',
                                'https://www.walgreens.com/store/c/hair-care-products/ID=360339-tier2general'],
                               ['skin-care',
                                'https://www.walgreens.com/store/c/skin-care-products/ID=360323-tier2general'],
                               ['bath-and-body',
                                'https://www.walgreens.com/store/c/bath-and-body-products/ID=360341-tier2general'],
                               ['beauty-gift-sets',
                                'https://www.walgreens.com/store/c/beauty-gift-sets/ID=360329-tier2general'],
                               ['fragrance', 'https://www.walgreens.com/store/c/fragrance/ID=360335-tier2general']]

        self.browser = None
        self.restart_web_driver()
        self.cur_catecory = ''
        self.cur_brand = ''
        self.columns = ['Site', 'Brand', 'Category', 'SKU Description', 'Image URL', 'S3 Path']
        self.df = pd.DataFrame(columns=self.columns)
        self.failed_urls = []
        self.domain_url = 'https://www.walgreens.com'

    def restart_web_driver(self):
        if self.browser:
            self.browser.close()
        self.browser_options = webdriver.ChromeOptions()
        self.browser_options.add_argument('headless')
        self.browser_options.add_argument('disable-gpu')
        self.browser = webdriver.Chrome(chrome_options=self.browser_options)

    def get_sub_category(self):
        self.scroll_up_down_page()
        soup = BeautifulSoup(self.browser.page_source, 'html.parser')
        sub_category_soup = soup.find_all('div',
                                          'col-lg-2 col-sm-3 col-md-2 col-xs-4 wag-tier1-shopby-cat category_global_shopbycategory_dtm wag-tier2-shop-category-list')
        sub_category_list = []
        for sub_category in sub_category_soup:
            cat_info = sub_category.find('figure', 'wag-tier1-centerimg')
            tmp = cat_info.find('a', href=True)
            sub_category_list.append([tmp['title'],
                                      self.domain_url + tmp['href']])
        return sub_category_list[:-2]

    def get_brands_in_sub_category(self):
        view_more = self.browser.find_element_by_xpath('//*[@id="collapse1"]/section/aside/aside/a')
        view_more.click()
        time.sleep(0.2)

    def scroll_up_down_page(self):
        last_height = self.browser.execute_script("return document.body.scrollHeight")
        while True:
            # Scroll down to bottom
            self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait to load page
            time.sleep(0.5)

            # Calculate new scroll height and compare with last scroll height
            new_height = self.browser.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        """ Scroll up """
        while True:
            # Scroll down to bottom
            self.browser.execute_script("window.scrollTo(0, 0);")

            # Wait to load page
            time.sleep(0.5)

            # Calculate new scroll height and compare with last scroll height
            new_height = self.browser.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def select_list(self, list_id, name):
        select = None
        while select is None:
            try:
                select = Select(self.browser.find_element_by_xpath("//select[@id='ref']"))
            except:
                self.browser.refresh()
                time.sleep(2.0)
        select.select_by_visible_text(name)

    def find_next_page(self):
        has_next_page = False
        while True:
            time.sleep(0.2)
            try:
                next_page = self.browser.find_element_by_id('omni-next-click')
                next_page.click()
                has_next_page = True
                break
            except Exception as e:
                if 'no such element' in str(e):
                    has_next_page = False
                    break
                else:
                    self.browser.refresh()
        return has_next_page

    def parse_category_page(self, category_link):
        cur_catecory = category_link[0]
        self.browser.get(category_link[1])
        self.scroll_up_down_page()

        """ Parse brands """
        soup = BeautifulSoup(self.browser.page_source, 'html.parser')
        brands_list = soup.find_all('section', 'wag-field-vertical')[0].find_all('option', 'ng-binding ng-scope')
        brands_list = [brand.string for brand in brands_list]

        cnt = 0
        for brand in brands_list:
            brand = brand.string
            cur_brand = brand
            if not os.path.exists('Walgreens/{}'.format(cur_brand)):
                os.makedirs('Walgreens/{}'.format(cur_brand))
            print('Parsing category [{}] with brand [{}]'.format(cur_catecory, cur_brand))
            self.select_list('ref', brand)
            self.parse_brand_page()
            self.browser.get(category_link[1])

            cnt += 1
            if cnt % 20 == 0:
                self.df.to_csv('output.csv', sep='\t', encoding='utf-8')

    def parse_current_page_product(self, product_info):

        cur_page_info_list = []
        for i in product_info:
            try:
                img_url = i.find('img')['src']
            except:
                continue

            split_list = img_url.split('/')
            img_url = 'http:' + '/'.join(split_list[:-1] + ['500.jpg'])
            img_name = split_list[-2]
            print('Query image at [{}]'.format(img_url))
            try:
                img_data = urllib2.urlopen(img_url).read()
                file_name = 'Walgreens/{}/{}.jpg'.format(self.cur_brand, img_name)
                with open(file_name, 'wb') as f:
                    f.write(img_data)

                cur_page_info_list.append(
                    ['Walgreens', str(self.cur_brand), str(self.cur_catecory), str(i.find('img')['data-alt-tag']),
                     str(img_url), str(file_name)])
            except:
                print('no img')
                self.failed_urls.append(img_url)
        tmp = pd.DataFrame(cur_page_info_list, columns=self.columns)
        self.df = pd.concat([self.df, tmp], axis=0, ignore_index=True)

    def parse_brand_page(self):
        self.scroll_up_down_page()

        """ Parse products """
        soup = BeautifulSoup(self.browser.page_source, 'html.parser')
        product_info = soup.find_all('article',
                                     'col-lg-3 col-md-4 col-sm-4 col-xs-12 wag-product-card-width_b ng-scope')
        self.parse_current_page_product(product_info)

        # parse next page if exists
        has_next_page = self.find_next_page()
        while has_next_page:
            self.scroll_up_down_page()
            soup = BeautifulSoup(self.browser.page_source, 'html.parser')
            product_info = soup.find_all('article',
                                         'col-lg-3 col-md-4 col-sm-4 col-xs-12 wag-product-card-width_b ng-scope')
            self.parse_current_page_product(product_info)
            has_next_page = self.find_next_page()
        print('')


if __name__ == '__main__':
    write_cnt = 0
    wal_parser = Walgreen_Parser()

    # Parse root
    for root_category in wal_parser.category_links:
        wal_parser.browser.get(root_category[1])

        # Parse sub category
        sub_category_list = wal_parser.get_sub_category()
        for cat_idx, sub_category in enumerate(sub_category_list):
            wal_parser.cur_catecory = sub_category[0]
            wal_parser.browser.get(sub_category[1])

            # Parse brands in this sub category
            err_cnt = 0
            while True:
                time.sleep(2)
                try:
                    wal_parser.get_brands_in_sub_category()
                except Exception as e:
                    err_cnt += 1
                    if 'no such element' in str(e):
                        print(str(e))
                    wal_parser.browser.refresh()
                    if err_cnt > 10:
                        break
                else:
                    break

            wal_parser.scroll_up_down_page()
            soup = BeautifulSoup(wal_parser.browser.page_source, 'html.parser')
            brand_soup = soup.find('section',
                                   {'id': 'Brand'}) \
                .find_all('p',
                          'wag-mb0 ng-pristine ng-untouched ng-valid ng-scope ng-not-empty')
            print('Category [{}] ({}/{}) with [{}] brands'.format(wal_parser.cur_catecory,
                                                                  cat_idx + 1,
                                                                  len(sub_category_list),
                                                                  len(brand_soup)))

            brand_list = []
            for brand in brand_soup:
                tmp = brand.find('a', 'triggerForesee', href=True)
                brand_list.append([str(tmp.find('span', 'wag-text-grey ng-binding').text.split('(')[0]).strip(),
                                   str(wal_parser.domain_url + tmp['href'])])

            for brand_idx, brand in enumerate(brand_list):
                write_cnt += 1
                wal_parser.cur_brand = brand[0]
                if not os.path.exists('Walgreens/{}'.format(wal_parser.cur_brand)):
                    os.makedirs('Walgreens/{}'.format(wal_parser.cur_brand))
                wal_parser.browser.get(brand[1])

                print('Parsing category [{}] ({}/{}) with brand [{}] ({}/{})'.format(wal_parser.cur_catecory,
                                                                                     cat_idx + 1,
                                                                                     len(sub_category_list),
                                                                                     wal_parser.cur_brand,
                                                                                     brand_idx + 1,
                                                                                     len(brand_list)))
                wal_parser.parse_brand_page()

                if write_cnt % 5 == 0:
                    wal_parser.df.to_csv('walgreens_metadata_cosmetics&hair.csv', sep='\t', encoding='utf-8')
                    wal_parser.restart_web_driver()

    wal_parser.df.to_csv('walgreens_metadata_cosmetics&hair.csv', sep='\t', encoding='utf-8')
    print(wal_parser.failed_urls)
