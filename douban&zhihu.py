# encoding: utf-8

import socket
import ssl
import requests
from lxml import html
from utils import log


class Model(object):
    def __repr__(self):
        class_name = self.__class__.__name__
        properties = (u'{} = ({})'.format(k, v) for k, v in self.__dict__.items())
        r = u'\n<{}:\n  {}\n>'.format(class_name, u'\n  '.join(properties))
        return r


class Movie(Model):
    def __init__(self):
        self.ranking = 0
        self.cover_url = ''
        self.name = ''
        self.staff = ''
        self.publish_info = ''
        self.rating = 0
        self.quote = ''
        self.number_of_comments = 0


class Answer(Model):
    def __init__(self):
        self.author = ''
        self.content = ''
        self.link = ''


def parsed_url(url):
    """
    解析 url 返回 (protocol host port path)
    """
    # 检查协议
    protocol = 'http'
    if url[:7] == 'http://':
        u = url.split('://')[1]
    elif url[:8] == 'https://':
        protocol = 'https'
        u = url.split('://')[1]
    else:
        u = url

    # 检查默认 path
    i = u.find('/')
    if i == -1:
        host = u
        path = '/'
    else:
        host = u[:i]
        path = u[i:]

    # 检查端口
    port_dict = {
        'http': 80,
        'https': 443,
    }
    # 默认端口
    port = port_dict[protocol]
    if host.find(':') != -1:
        h = host.split(':')
        host = h[0]
        port = int(h[1])

    return protocol, host, port, path


def socket_by_protocol(protocol):
    """
    根据协议返回一个 socket 实例
    """
    if protocol == 'http':
        s = socket.socket()
    else:
        s = ssl.wrap_socket(socket.socket())
    return s


def response_by_socket(s):
    """
    参数是一个 socket 实例
    返回这个 socket 读取的所有数据
    """
    response = b''
    buffer_size = 1024
    while True:
        r = s.recv(buffer_size)
        if len(r) == 0:
            break
        response += r
    return response


def parsed_response(r):
    """
    把 response 解析出 状态码 headers body 返回
    状态码是 int
    headers 是 dict
    body 是 str
    """
    header, body = r.split('\r\n\r\n', 1)
    h = header.split('\r\n')
    status_code = h[0].split()[1]
    status_code = int(status_code)

    headers = {}
    for line in h[1:]:
        k, v = line.split(': ')
        headers[k] = v
    return status_code, headers, body


def get(url):
    """
    用 GET 请求 url 并返回响应
    """
    protocol, host, port, path = parsed_url(url)

    s = socket_by_protocol(protocol)
    s.connect((host, port))

    request = 'GET {} HTTP/1.1\r\nhost: {}\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36\r\nConnection: close\r\n\r\n'.format(path, host)
    encoding = 'utf-8'
    s.send(request.encode(encoding))

    response = response_by_socket(s)
    log('response', response)
    r = response.decode(encoding)

    status_code, headers, body = parsed_response(r)
    if status_code == 301:
        url = headers['Location']
        return get(url)
    return status_code, headers, body


def movie_from_div(div):
    movie = Movie()
    movie.ranking = div.xpath('.//div[@class="pic"]/em')[0].text
    movie.cover_url = div.xpath('.//div[@class="pic"]/a/img/@src')
    names = div.xpath('.//span[@class="title"]/text()')
    movie.name = ''.join(names)
    movie.rating = div.xpath('.//span[@class="rating_num"]')[0].text
    movie.quote = div.xpath('.//span[@class="inq"]')[0].text
    infos = div.xpath('.//div[@class="bd"]/p/text()')
    movie.staff, movie.publish_info = [i.strip() for i in infos[:2]]
    movie.number_of_comments = div.xpath('.//div[@class="star"]/span')[-1].text[:-3]
    return movie


def movies_from_url(url):
    _, _, page = get(url)
    root = html.fromstring(page)
    movie_divs = root.xpath('//div[@class="item"]')
    movies = [movie_from_div(div) for div in movie_divs]
    return movies


def download_covers(movies):
    for m in movies:
        image_url = m.cover_url[0]
        r = requests.get(image_url)
        path = 'covers/' + m.name.split('/')[0] + '.jpg'
        with open(path, 'wb') as f:
            f.write(r.content)


def answer_from_div(div):
    a = Answer()
    a.author = div.xpath('.//a[@class="author-link"]')[0].text
    log('author,', a)
    content = div.xpath('.//div[@class="zm-editable-content clearfix"]/text()')
    a.content = '\n'.join(content)
    return a


def answers_from_url(url):
    # r = requests.get(url)
    # page = r.content
    _, _, page = get(url)
    root = html.fromstring(page)
    # log('page', page)
    divs = root.xpath('//div[@class="zm-item-answer  zm-item-expanded"]')
    log('divs', len(divs))
    log('divs', divs[0])
    items = [answer_from_div(div) for div in divs]
    return items


def main():
    # 豆瓣电影 top250
    # url = 'http://movie.douban.com/top250'
    # movies = movies_from_url(url)
    # log('movies', movies[0])
    # download_covers(movies)
    #
    # 知乎答案
    url = 'https://www.zhihu.com/question/31515263'
    answers = answers_from_url(url)
    log(answers)

if __name__ == '__main__':
    # test()
    main()


def test_parsed_url():
    """
    parsed_url 函数很容易出错,检测是否正确运行
    """
    http = 'http'
    https = 'https'
    host = 'g.cn'
    path = '/'
    test_items = [
        ('http://g.cn', (http, host, 80, path)),
        ('http://g.cn', (http, host, 80, path)),
        ('http://g.cn/', (http, host, 80, path)),
        ('http://g.cn:90', (http, host, 90, path)),
        ('http://g.cn:90/', (http, host, 90, path)),
        #
        ('https://g.cn', (https, host, 443, path)),
        ('https://g.cn:233/', (https, host, 233, path)),
    ]
    for t in test_items:
        url, expected = t
        u = parsed_url(url)
        e = "parsed_url ERROR, ({}) ({}) ({})".format(url, u, expected)
        assert u == expected, e


def test_parsed_response():
    """
    测试是否能正确解析响应
    """
    response = 'HTTP/1.1 301 Moved Permanently\r\n' \
               'Content-Type: text/html\r\n' \
               'Location: https://movie.douban.com/top250\r\n' \
               'Content-Length: 178\r\n\r\n' \
               'test body'
    status_code, header, body = parsed_response(response)
    assert status_code == 301
    assert len(list(header.keys())) == 3
    assert body == 'test body'


def test_get():
    """
    测试是否能正确处理 HTTP 和 HTTPS
    """
    urls = [
        'http://movie.douban.com/top250',
        'https://movie.douban.com/top250',
    ]
    for u in urls:
        get(u)


def test():
    """
    用于测试的主函数
    """
    test_parsed_url()
    test_get()
    test_parsed_response()

