import scrapy
from PIL import Image
from io import BytesIO


class ZZSpider(scrapy.Spider):
    name = "zz"

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.f_zz = config[0]
        self.url = config[1]
        self.cookie = config[2]

    def start_requests(self):
        print("start")
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
            print("===== %s 资质等级已获取 =====" % company_name)
        else:
            print("！！！！验证不通过！！！！")


