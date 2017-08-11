import requests

f = open('proxies.txt', 'r')
fw = open('p2.txt', 'w')
lines = f.readlines()
for line in lines:
    protocol = 'https' if 'https' in line else 'http'
    proxies = {protocol: line}
    try:
        if requests.get('https://www.baidu.com', proxies=proxies, timeout=9).status_code == 200:
            print('success %s' % line)
            fw.write(line + '\n')
    except:
        print('fail %s' % line)
f.close()
fw.close()