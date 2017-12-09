#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by Baoyi on 2017/12/8

# 蚂蜂窝使用的是异步加载，但是加载的数据不是json...而是一个嵌套了另外一个网页的非常异形的json，感觉有点奇葩

import base64
import configparser
import hashlib
import json
import logging
import re
import time
import random
from io import BytesIO

import exifread
import pymysql
import requests
from bs4 import BeautifulSoup

# 配置logging
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='weibo.log',
                    filemode='a')
cf = configparser.ConfigParser()
cf.read("/Users/baoyi/PycharmProjects/Some/gulangyu/get_more_data/data/ConfigParser.conf")

# 读取配置mysql
db_host = cf.get("mysql", "db_host")
db_port = cf.getint("mysql", "db_port")
db_user = cf.get("mysql", "db_user")
db_pass = cf.get("mysql", "db_pass")
db = cf.get("mysql", "db")

# 创建连接
conn = pymysql.connect(host=db_host, user=db_user, passwd=db_pass, db=db, port=db_port, charset='utf8')
# 获取游标
cursor = conn.cursor()

# 创建insert_sql
insert_blog_sql = (
    "INSERT IGNORE INTO gulangyu.mafengwo_blog(user_name, create_time, blog, star, comment_id, scenery) VALUES('{user_name}', '{create_time}','{blog}','{star}','{comment_id}', '{scenery}')"
)

insert_pic_sql = (
    "INSERT IGNORE INTO gulangyu.mafengwo_pics(pic_url, pic_bin, md5, exif, scenery) VALUES ('{pic_url}','{pic_bin}','{md5}','{exif}', '{scenery}')"
)

insert_relationship_sql = (
    "INSERT IGNORE INTO gulangyu.mafengwo_relationship(id, md5, scenery) VALUES ('{id}','{md5}', '{scenery}')"
)

url = 'http://pagelet.mafengwo.cn/poi/pagelet/poiCommentListApi?callback=jQuery18105332634542482972_1511924148475&params=%7B%22poi_id%22%3A%22{href}%22%2C%22page%22%3A{num}%2C%22just_comment%22%3A1%7D'
user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36'
Connection = 'keep-alive'
cookie = 'PHPSESSID=uhcp0js2nkrfm2ergc630drpr6; mfw_uuid=5a1d497e-106d-9f3a-dfb1-a701fa6d7002; _r=google; _rp=a%3A2%3A%7Bs%3A1%3A%22p%22%3Bs%3A15%3A%22www.google.com%2F%22%3Bs%3A1%3A%22t%22%3Bi%3A1511868798%3B%7D; oad_n=a%3A5%3A%7Bs%3A5%3A%22refer%22%3Bs%3A22%3A%22https%3A%2F%2Fwww.google.com%22%3Bs%3A2%3A%22hp%22%3Bs%3A14%3A%22www.google.com%22%3Bs%3A3%3A%22oid%22%3Bi%3A1075%3Bs%3A2%3A%22dm%22%3Bs%3A15%3A%22www.mafengwo.cn%22%3Bs%3A2%3A%22ft%22%3Bs%3A19%3A%222017-11-28+19%3A33%3A18%22%3B%7D; uva=s%3A150%3A%22a%3A4%3A%7Bs%3A13%3A%22host_pre_time%22%3Bs%3A10%3A%222017-11-28%22%3Bs%3A2%3A%22lt%22%3Bi%3A1511868799%3Bs%3A10%3A%22last_refer%22%3Bs%3A23%3A%22https%3A%2F%2Fwww.google.com%2F%22%3Bs%3A5%3A%22rhost%22%3Bs%3A14%3A%22www.google.com%22%3B%7D%22%3B; __mfwurd=a%3A3%3A%7Bs%3A6%3A%22f_time%22%3Bi%3A1511868799%3Bs%3A9%3A%22f_rdomain%22%3Bs%3A14%3A%22www.google.com%22%3Bs%3A6%3A%22f_host%22%3Bs%3A3%3A%22www%22%3B%7D; __mfwuuid=5a1d497e-106d-9f3a-dfb1-a701fa6d7002; UM_distinctid=16002671cf7bc4-0a489059b51dc4-17386d57-13c680-16002671cf8aa4; __mfwlv=1512004316; __mfwvn=4; __mfwlt=1512008540'
headers = {
    'User-Agent': user_agent,
    'Cookie': cookie,
    'Connection': Connection
}


# 处理图片数据
def handle_pic(pic_url):
    try:
        large_bin = requests.get(pic_url, timeout=(10, 10))
        return large_bin.content
    except:
        logging.warning('img not get')
        print('img not get')
        return None


def get_param():
    # 获取所有景点的参数
    total = []
    router_url = 'http://www.mafengwo.cn/ajax/router.php'
    for num in range(1, 6):
        params = {
            'sAct': 'KMdd_StructWebAjax|GetPoisByTag',
            'iMddid': 12522,
            'iTagId': 0,
            'iPage': num
        }
        pos = requests.post(url=router_url, data=params, headers=headers).json()
        soup_pos = BeautifulSoup(pos['data']['list'], 'lxml')

        result = [{'scenery': p['title'], 'href': re.findall(re.compile(r'/poi/(\d+).html'), p['href'])[0]} for p in
                  soup_pos.find_all('a')]
        total.extend(result)

    return total


def get_comment(href, num, name):
    new_url = url.format(href=href, num=num)
    req = requests.get(new_url, headers=headers)
    print(req.status_code)
    back = req.content.decode('utf-8')
    # 正则匹配出所需要的html文档
    p = re.compile('\((.*?)}}\)')
    html = json.loads(p.findall(back)[0] + "}}")['data']['html']

    soup = BeautifulSoup(html, 'lxml')
    star_all = soup.find_all('span', {'class': re.compile(r's-star s-star\d')})
    blog_all = soup.find_all('p', {'class': 'rev-txt'})
    create_time_all = soup.find_all('span', {'class': 'time'})
    comment_id_all = soup.find_all('textarea')

    for i in range(len(star_all)):
        star = star_all[i]['class'][1][-1]
        blog = blog_all[i].text.replace('\'', '\'\'')
        create_time = create_time_all[i].text
        comment_id = comment_id_all[i]['data-comment_id']
        user_name = comment_id_all[i]['data-comment_username']

        print(insert_blog_sql.format(user_name=user_name, create_time=create_time, blog=blog, star=star,
                                     comment_id=comment_id, scenery=name))

        cursor.execute(insert_blog_sql.format(user_name=user_name, create_time=create_time, blog=blog, star=star,
                                              comment_id=comment_id, scenery=name))
        conn.commit()

    # 获取含图片的标签
    include_img = [img.next_sibling.next_sibling for img in blog_all if
                   img.find_next_sibling('div')['class'][0] == 'rev-img']
    # 获取含图片标签的id
    have_img_uid = [img.find_previous_siblings('a')[1]['data-id'] for img in blog_all if
                    img.find_next_sibling('div')['class'][0] == 'rev-img']

    for index in range(len(have_img_uid)):
        pic_urls = [i.img['src'] for i in include_img[index].find_all('a')]
        id = have_img_uid[index]
        # 处理图片
        for pic_url in pic_urls:
            # 获取原图片二进制数据'
            print(pic_url)
            pic_bin = handle_pic(pic_url)
            if pic_bin == None:
                pass
            else:
                # 读取exif 数据
                pic_file = BytesIO(pic_bin)  # 将二进制数据转化成文件对象便于读取exif数据信息和生成MD5
                tag1 = exifread.process_file(pic_file, details=False, strict=True)
                tag = {}
                for key, value in tag1.items():
                    if key not in (
                            'JPEGThumbnail', 'TIFFThumbnail', 'Filename',
                            'EXIF MakerNote'):  # 去除四个不必要的exif属性，简化信息量
                        tag[key] = str(value)
                tags = json.dumps(tag)  # dumps为json类型 此tag即为exif的json数据
                # 生成MD5
                MD5 = hashlib.md5(pic_file.read()).hexdigest()
                # 首先把二进制图片用base64 转成字符串之后再存

                # 判断是否已经存在图片
                judge_pics = (
                    "SELECT md5 FROM gulangyu.mafengwo_pics WHERE md5 = '{md5}' LIMIT 1"
                )

                cursor.execute(judge_pics.format(md5=MD5))
                pic_md5 = cursor.fetchone()

                # 如果不存在就插入图片，否则就pass
                if pic_md5 is None:
                    cursor.execute(
                        insert_pic_sql.format(
                            pic_url=pic_url,
                            pic_bin=str(base64.b64encode(pic_bin))[2:-1], md5=MD5,
                            exif=tags, scenery=name))
                else:
                    logging.warning("Duplicate  " + pic_md5[0])

                cursor.execute(insert_relationship_sql.format(id=id, md5=MD5, scenery=name))
                conn.commit()


if __name__ == '__main__':
    result = get_param()

    for data in result:
        href = data['href']
        name = data['scenery']
        for i in range(1, 340):
            time.sleep(random.choice(range(1, 5)))
            get_comment(href=href, name=name, num=i)
