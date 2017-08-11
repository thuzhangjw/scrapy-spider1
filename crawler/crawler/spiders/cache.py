import os


class UrlInfo(object):
    def __init__(self, flink_pos, clinks_num, url, index):
        self.flink_pos = flink_pos
        self.clinks_num = clinks_num
        self.url = url
        self.index = index


def load_parsed_urls(flag, file):
    if flag:
        f = open('./config/' + file, 'w')
        f.close()
        return []
    else:
        parsed_url_list = []
        if not os.path.exists('./config/' + file):
            f = open('./config/' + file, 'w')
            f.close()
        else:
            f = open('./config/' + file, 'r')
            urls = f.readlines()
            for url in urls:
                parsed_url_list.append(url.strip())
            f.close()
        return parsed_url_list
