import scrapy
from PIL import Image
from io import BytesIO


class BidInfoSpider(scrapy.Spider):
    name = "bid"

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.f_bid = config[0]
        self.url = config[1]
        self.cookie = config[2]

    def start_requests(self):
        yield scrapy.Request(self.url, callback=self.check, meta={"cookiejar": self.cookie})

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
                                     callback=self.pass_valid, headers=header)
            request.meta['view_state'] = view_state
            request.meta['event_validation'] = event_validation
            request.meta['last_url'] = response.url
            yield request
        else:
            self.parse(response)

    def pass_valid(self, response):
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
        yield scrapy.FormRequest(response.meta['last_url'], meta={"cookiejar": response.meta["cookiejar"]},
                                 formdata=data, callback=self.parse, dont_filter=True)

    def parse(self, response):
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
            print("===== 中标信息: %s 已获取 =====" % bid_name)
