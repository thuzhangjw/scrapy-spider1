import scrapy
import datetime
import time
from .cache import *
import threading


class CompanyLinkSpider(scrapy.Spider):
    name = "companyLink"

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)

        self.parsed_url_list = load_parsed_urls(config[9], 'nologin_parsed_urls.info')
        self.f_cache = open('./config/nologin_parsed_urls.info', 'a')

        f = open('./info/' + config[2], 'a')
        f.close()

        f_flag = False
        f = open('./info/' + config[2], "r")
        if len(f.readlines()) == 0:
            f_flag = True
        f.close()

        self.f_award = open('./info/' + config[2], 'a')
        if f_flag:
            self.f_award.write("公司名称;荣誉奖项;企业荣誉项目;荣誉公布时间\n")

        self.awards = config[4].split(',')
        self.date_start = datetime.datetime.strptime(config[5], "%Y-%m-%d").date()
        self.date_end = datetime.datetime.strptime(config[6], "%Y-%m-%d").date()
        self.money_low = config[7]
        self.money_high = config[8]
        self.companies = {}
        self.prefix = "http://hhb.cbi360.net"
        self.f_bid_url = open('./config/companies_bidInfo_url', 'w' if config[9] else 'a')
        self.saved_zz_urls = load_parsed_urls(config[9], 'companies_zz_url')
        self.f_zz_url = open('./config/companies_zz_url', 'w' if config[9] else 'a')
        self.zz_count = 0
        self.mutex = threading.Lock()
        self.pending_urls = []

    def start_requests(self):
        print("===== 开始获取公司列表 =====")
        start_url = self.prefix + "/tenderbangsoso.aspx?money=" + self.money_low + "-" + self.money_high + "&isall=1"
        yield scrapy.Request(url=start_url, callback=self.parse_company_name_list)

    def parse_company_name_list(self, response):
        project_divs = response.xpath('//div[@class="d01link"]')
        for div in project_divs:
            date_str = div.xpath('.//dd[@class="d04"]/text()').extract_first()
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            if self.date_start <= date <= self.date_end:
                company_info = div.xpath('.//dd[@class="d02"]/a')
                company_name = company_info.xpath('./text()').extract_first()
                company_href = company_info.xpath('@href').extract_first()
                if self.companies.get(company_name) is None:
                    self.companies[company_name] = company_href

        print("===== crawled a page =====")
        next_page = response.xpath('//a[contains(span, "下一页")]/@href').extract_first()
        if next_page is not None:
            yield scrapy.Request(self.prefix + next_page, callback=self.parse_company_name_list)
            time.sleep(1)
        else:
            print("===== 公司名称列表获取完毕, %d家公司 =====" % len(self.companies))
            print("===== 开始获取URL信息 =====")
            for name, href in self.companies.items():
                url = self.prefix + "/" + href
                if url in self.parsed_url_list:
                    print('### 公司链接: %s已经获取过，跳过 ###' % url)
                    continue

                self.mutex.acquire()
                index = len(self.pending_urls)
                pending_url = UrlInfo(-1, 0, url, index)
                self.pending_urls.append(pending_url)
                self.mutex.release()

                request = scrapy.Request(url, callback=self.parse)
                request.meta['index'] = index
                yield request
                time.sleep(1)

    def parse(self, response):
        zz_url = response.xpath('//a[contains(text(), "资质等级")]/@href').extract_first()
        if zz_url not in self.saved_zz_urls:
            self.f_zz_url.write(zz_url + "\n")
            self.f_zz_url.flush()
        self.zz_count += 1
        print("===== 已获取%d个公司资质信息链接 ======" % self.zz_count)

        tmp = response.xpath('//a[contains(@title, "企业简介")]/@href').extract_first().split("=")
        if len(tmp) == 2:
            flink_pos = response.meta['index']

            bid_url = self.prefix + "/CompanyTenderList.aspx?cid=" + tmp[1] + "&money=" + self.money_low + "-" + self.money_high
            if bid_url not in self.parsed_url_list:
                index = self.pending(flink_pos, bid_url)
                request = scrapy.Request(bid_url, callback=self.parse_last_page)
                request.meta['type'] = 'bid'
                request.meta['index'] = index
                yield request
                time.sleep(1)
            else:
                print('### 中标链接: %s已经获取过，跳过 ###' % bid_url)

            award_url = self.prefix + "/CRedMoreList.aspx?cid=" + tmp[1]
            if award_url not in self.parsed_url_list:
                index = self.pending(flink_pos, award_url)
                request = scrapy.Request(award_url, callback=self.parse_last_page)
                request.meta['type'] = 'award'
                request.meta['index'] = index
                yield request
                time.sleep(1)
            else:
                print('### 荣誉链接: %s已经获取过，跳过 ###' % bid_url)
        else:
            print("warning: cid解析出错")
            raise Exception

    def parse_last_page(self, response):
        last_page = response.xpath('//a[contains(span, "末页")]/@href').extract_first()
        if last_page is None:
            if response.meta['type'] == 'award':
                print("===== 获取荣誉信息，仅一页 =====")
                self.parse_awards(response)
            else:
                print("===== 获取中标链接，仅一页 =====")
                self.parse_href(response)
        else:
            flink_pos = response.meta['index']
            last_page = last_page.split('page=')[1]
            for i in range(int(last_page) + 1):
                url = response.url + "&page=" + str(i)
                if url in self.parsed_url_list:
                    print('### %s 链接第%d页: %s已经获取过，跳过 ###' % (response.meta['type'], i + 1, url))
                    continue

                index = self.pending(flink_pos, url)
                if response.meta['type'] == 'award':
                    request = scrapy.Request(url, callback=self.parse_awards)
                else:
                    request = scrapy.Request(url, callback=self.parse_href)
                request.meta['index'] = index
                yield request
                time.sleep(1)

    def parse_awards(self, response):
        awards = response.xpath('//div[@class="d01link"]')
        award_names = awards.xpath('.//dd[@class="d01"]/span[@class="span1"]/a/@title').extract()
        award_times = awards.xpath('.//dd[@class="d02"]/text()').extract()
        company_name = response.xpath('//div[@class="company_name"]/h1/a/text()').extract_first()
        has = False
        for idx, award in enumerate(award_names):
            flag = False
            award_type = ''
            for keyword in self.awards:
                if keyword in award:
                    flag = True
                    award_type = keyword
                    break
            if flag:
                has = True
                line = "%s;%s;%s;%s\n" % (company_name, award_type, award, award_times[idx])
                self.f_award.write(line)
        if not has:
            self.f_award.write("%s\n" % company_name)
        self.f_award.flush()
        self.write_cache(response.meta['index'])
        print("=====", company_name, ": 荣誉信息获取一页 =====")

    def parse_href(self, response):
        divs = response.xpath('//div[@class="d01link"]')
        for div in divs:
            bid_href = div.xpath('.//dd[@class="d01"]//a/@href').extract_first()
            url = self.prefix + "/" + bid_href
            self.f_bid_url.write(url + "\n")
        self.f_bid_url.flush()
        self.write_cache(response.meta['index'])
        print("===== 爬取一页中标链接 =====")

    def pending(self, flink_pos, url):
        self.mutex.acquire()
        index = len(self.pending_urls)
        pending_url = UrlInfo(flink_pos, 0, url, index)
        self.pending_urls.append(pending_url)
        self.pending_urls[flink_pos].clinks_num += 1
        self.mutex.release()
        return index

    def write_cache(self, index):
        self.mutex.acquire()
        url_info = self.pending_urls[index]
        while url_info.clinks_num == 0:
            self.f_cache.write(url_info.url + '\n')
            if url_info.flink_pos == -1:
                break
            url_info = self.pending_urls[url_info.flink_pos]
            url_info.clinks_num -= 1
        self.mutex.release()

    @classmethod
    def summary_awards(cls, file_name):
        f = open('./info/' + file_name, 'r')
        awards_map = {}
        awards_list = []
        lines = f.readlines()
        for line in lines:
            info = line.strip().split(';')
            if len(info) < 3:
                if awards_map.get(info[0]) is None:
                    awards_map[info[0]] = False
            else:
                awards_list.append(line)
                if awards_map.get(info[0]) is None:
                    awards_map[info[0]] = True
                else:
                    awards_map[info[0]] = True
        f.close()
        f = open('./info/' + file_name, 'w')
        for line in awards_list:
            f.write(line)
        for name, flag in awards_map.items():
            if not flag:
                s = name + ';无相关荣誉\n'
                f.write(s)
        f.close()
