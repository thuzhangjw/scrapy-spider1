import scrapy
from PIL import Image
from io import BytesIO
from crawler.crawler.spiders.cache import *


def load_urls(file):
    urls = []
    f = open('./config/' + file, 'r')
    lines = f.readlines()
    for line in lines:
        urls.append(line.strip())
    f.close()
    return urls


class LoginSpider(scrapy.Spider):
    name = "login"

    cookie = ''

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.header = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Connection": "keep-alive",
            "Host": "user.cbi360.net"
        }
        self.parsed_urls = load_parsed_urls(config[9], 'login_parsed_urls.info')
        self.f_cache = open('./config/login_parsed_urls.info', 'a')

        self.f_zz = open('./info/' + config[0], "a")
        self.zz_url_list = load_urls('companies_zz_url')

        f_bid = open('./info/' + config[1], "a")
        f_bid.close()
        f_bid_flag = False
        f_bid = open('./info/' + config[1], "r")
        if len(f_bid.readlines()) == 0:
            f_bid_flag = True
        f_bid.close()
        self.f_bid = open('./info/' + config[1], "a")
        if f_bid_flag:
            self.f_bid.write("公司名称;中标工程项目;中标金额;中标时间;信息来源\n")
        self.bid_url_list = load_urls('companies_bidInfo_url')

    def start_requests(self):
        print("===== 开始登陆 =====")
        yield scrapy.Request(url="http://user.cbi360.net/Login", headers=self.header, callback=self.getvalidcode,
                             meta={"cookiejar": 1})

    def getvalidcode(self, response):
        validcode_path = response.xpath("//img[@id='imgValidCode']/@src").extract_first()
        validcode_url = "http://user.cbi360.net" + str(validcode_path).replace(" ", "%20")
        yield scrapy.Request(url=validcode_url, meta={"cookiejar": response.meta["cookiejar"]}, callback=self.login)

    def login(self, response):
        i = Image.open(BytesIO(response.body))
        i.save("validcode.png")
        validcode_value = input("查看validcode.png,输入验证码：")
        data = {
            "UserAccount": "*******",
            "UserPwd": "******",
            "ValidCode": validcode_value
        }
        yield scrapy.FormRequest("http://user.cbi360.net/Login/SubmitLogin?Length=4",
                                 meta={"cookiejar": response.meta["cookiejar"]},
                                 formdata=data, callback=self.parse)

    def parse(self, response):
        has_login = response.xpath('//input[@id="btnLogin"]')
        if len(has_login) == 0:
            print("===== 登陆成功 =====")
            for zz_url in self.zz_url_list:
                if zz_url in self.parsed_urls:
                    print("##资质 %s 已经获取过, 跳过##" % zz_url)
                    continue
                request = scrapy.Request(zz_url, meta={"cookiejar": response.meta["cookiejar"]}, callback=self.check)
                request.meta['type'] = 'zz'
                yield request

            for bid_url in self.bid_url_list:
                if bid_url in self.parsed_urls:
                    print("##中标 %s 已经获取过, 跳过##" % bid_url)
                    continue
                request = scrapy.Request(bid_url, meta={"cookiejar": response.meta["cookiejar"]}, callback=self.check)
                request.meta['type'] = 'bid'
                yield request
        else:
            print("!!!!! 登陆失败,重新登陆 !!!!!")
            yield scrapy.Request(url="http://user.cbi360.net/Login", headers=self.header, callback=self.getvalidcode,
                                 meta={"cookiejar": 1})

    def check(self, response):
        print("########  checking #############")
        warning = response.xpath('//div[@class="rightContent"]/h1[contains(text(), "系统检测到你的账号操作频繁")]/text()').extract_first()
        if warning is not None:
            print("### 系统检测到你的账号操作频繁, 开始自动验证 ###")
            validcode_path = response.xpath('//img[@id="img_validCode"]/@src').extract_first()
            validcode_url = "http://hhb.cbi360.net/" + validcode_path
            header = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "zh-CN,zh;q=0.8",
                "Host": "hhb.cbi360.net",
                "Refer": response.url
            }
            view_state = response.xpath('//input[@id="__VIEWSTATE"]/@value').extract_first()
            event_validation = response.xpath('//input[@id="__EVENTVALIDATION"]/@value').extract_first()
            request = scrapy.Request(url=validcode_url, meta={"cookiejar": response.meta["cookiejar"]},
                                     callback=self.pass_valid, headers=header, priority=100, dont_filter=True)
            request.meta['view_state'] = view_state
            request.meta['event_validation'] = event_validation
            request.meta['last_url'] = response.url
            request.meta['type'] = response.meta['type']
            yield request
        else:
            if response.meta['type'] == 'zz':
                self.parse_zz(response)
            else:
                self.parse_bid(response)

    def pass_valid(self, response):
        print("下载验证码")
        i = Image.open(BytesIO(response.body))
        i.save("yz.png")
        validcode_value = input("查看 yz.png,输入验证码：")

        data = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": response.meta['view_state'],
            "__EVENTVALIDATION": response.meta['event_validation'],
            "txt_ValidCode": validcode_value,
            "btnSubmit": "提 交"
        }
        func = self.parse_zz if response.meta['type'] == 'zz' else self.parse_bid
        yield scrapy.FormRequest(response.meta['last_url'], meta={"cookiejar": response.meta["cookiejar"]},
                                 formdata=data, callback=func, dont_filter=True)

    def parse_zz(self, response):
        warning = response.xpath('//div[@class="rightContent"]/h1[contains(text(), "系统检测到你的账号操作频繁")]/text()').extract_first()
        if warning is None:
            print("### 验证通过 ###")
            company_name = response.xpath('//div[@class="company_name"]/h1/a/text()').extract_first()
            credentials = map(lambda s: s.strip(),
                              response.xpath('//div[@class="d01link"]//span[@class="span01"]/text()').extract())
            credential_level = response.xpath('//div[@class="d01link"]//span[@class="span01"]/font/text()').extract()
            credential_name = []
            for name in credentials:
                if name != "":
                    credential_name.append(name)

            self.f_zz.write(company_name)
            for idx, val in enumerate(credential_name):
                item = ";%s%s" % (val, credential_level[idx])
                self.f_zz.write(item)
            if len(credential_name) == 0:
                self.f_zz.write(";无资质信息")
            self.f_zz.write("\n")
            self.f_zz.flush()
            self.f_cache.write(response.url + "\n")
            self.f_cache.flush()
            print("===== %s 资质等级已获取 =====" % company_name)
        else:
            print("！！！！验证不通过！！！！")

    def parse_bid(self, response):
        warning = response.xpath('//div[@class="rightContent"]/h1[contains(text(), "系统检测到你的账号操作频繁")]/text()').extract_first()
        if warning is None:
            print("### 验证通过 ###")
            company_name = response.xpath('//div[@class="company_name"]/h1/a/text()').extract_first()
            bid_info = response.xpath('//div[@class="company_zbname"]')
            bid_name = bid_info.xpath('./h1/text()').extract_first().strip()
            bid_money = bid_info.xpath('.//tr[contains(td, "中标金额")]/td[@colspan="3"]/text()').extract_first().strip()
            bid_time = bid_info.xpath('.//tr[contains(td, "中标时间")]/td[@colspan="3"]/text()').extract_first().strip()
            bid_info_source = bid_info.xpath('.//tr[contains(td, "信息来源")]//a/@href').extract()
            line = "%s;%s;%s;%s;%s\n" % (company_name, bid_name, bid_money, bid_time, str(bid_info_source))
            self.f_bid.write(line)
            self.f_bid.flush()
            self.f_cache.write(response.url + "\n")
            self.f_cache.flush()
            print("===== 中标信息: %s 已获取 =====" % bid_name)
        else:
            print("！！！！验证不通过！！！！")
