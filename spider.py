from twisted.internet import reactor, defer
from scrapy.crawler import CrawlerRunner
from crawler.crawler.spiders.CompanyLinkSpider import CompanyLinkSpider
from crawler.crawler.spiders.LoginSpider import LoginSpider
import os


def load_config():
    configs = []
    f = open('./config/lastSettings.cnf', 'r')
    lines = f.readlines()
    for line in lines:
        configs.append(line.strip())
    f.close()
    return configs

if not os.path.exists('./config'):
    os.mkdir('./config')


flag = True
flag2 = False
config = []
if os.path.exists('./config/lastSettings.cnf'):
    load = input("是否导入上次设置？(y/N): ")
    if load.lower() == "y":
        flag = False
        config = load_config()

if flag:
    file_zz = input("请输入资质信息要保存的文件名，包含后缀: ")
    config.append(file_zz)
    file_bid = input("请输入中标项目信息要保存的文件名, 包含后缀: ")
    config.append(file_bid)
    file_award = input("请输入荣誉信息要保存的文件名， 包含后缀: ")
    config.append(file_award)

    stop_time = input("请输入每次请求的间隔时间，以秒为单位, 默认为6，实际间隔为该值的0.5到1.5倍之间的随机值: ")
    if stop_time == '':
        stop_time = '6'
    config.append(stop_time)

    awards_str = input("请输入荣誉奖项名称，多个奖项以逗号分隔，默认值为:鲁班奖,詹天佑奖,国家优质工程金质奖: ")
    if awards_str == '':
        awards_str = "鲁班奖,詹天佑奖,国家优质工程金质奖"
    config.append(awards_str)

    print("请输入筛选公司时的中标项目的时间段，时间格式xxxx-xx-xx")
    date_start_str = input("开始时间(包含): ")
    config.append(date_start_str)
    date_end_str = input("结束时间(包含): ")
    config.append(date_end_str)

    print("请输入筛选公司时的项目金额区间，以万为单位")
    money_low = input("资金区间左值: ")
    config.append(money_low)
    money_high = input("资金区间右值: ")
    config.append(money_high)

    flag2 = input("是否清空以前的URL缓存(y/N): ")
    if flag2.lower() == "y":
        flag2 = True
    else:
        flag2 = False

print("===============设置信息如下===============")
print("资质信息保存文件名: ", config[0])
print("中标项目信息保存文件名: ", config[1])
print("荣誉信息保存文件名: ", config[2])
print("每次请求间隔时间: %s秒" % config[3])
print("荣誉奖项名称: ", config[4])
print("中标项目时间段: %s--%s" % (config[5], config[6]))
print("筛选公司时的项目金额区间: %s万--%s万" % (config[7], config[8]))
print("清空以前的URL缓存: ", ("是" if flag2 else "否"))

yn = input("确认(Y/n): ")
if yn.lower() == "n":
    exit(0)

if not os.path.exists('./info'):
    os.mkdir('./info')

f_last_set = open('./config/lastSettings.cnf', 'w')
for s in config:
    f_last_set.write(s + "\n")
f_last_set.close()

config.append(flag2)

runner = CrawlerRunner({
    'BOT_NAME': 'crawler',
    'ROBOTSTXT_OBEY': False,
    'DOWNLOADER_MIDDLEWARES': {
        'scrapy.downloadermiddleware.useragent.UserAgentMiddleware': None,
        'crawler.crawler.middlewares.RandomUserAgentMiddleware': 400
    },
    'LOG_LEVEL': 'ERROR',
    'RANDOMIZE_DOWNLOAD_DELAY': True,
    'DOWNLOAD_DELAY': int(config[3]),
    'CONCURRENT_REQUESTS': 1,
    'DEPTH_PRIORITY': -1,
    'CONCURRENT_REQUESTS_PER_IP': 1
})


try:
    @defer.inlineCallbacks
    def crawl():
        print("===== 开始无登录状态获取信息 =====")
        yield runner.crawl(CompanyLinkSpider, config)
        CompanyLinkSpider.summary_awards(config[2])
        print("===== ！！无登录状态信息全部获取完毕！！ =====")
        print("===== 开始登录状态获取信息 =====")
        yield runner.crawl(LoginSpider, config)
        print("===== ！！信息全部获取完毕！！ =====")
        reactor.stop()
    crawl()
    reactor.run()
except Exception as error:
    print("=======Exception=======")
