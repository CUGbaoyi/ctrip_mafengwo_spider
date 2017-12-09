#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by Baoyi on 2017/12/3

# 携程的数据是使用post请求加载

import base64
import configparser
import hashlib
import json
import logging
import re
import random
import time
from io import BytesIO

import exifread
import pymysql
import requests
import pandas as pd
from bs4 import BeautifulSoup

# 配置logging
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='weibo.log',
                    filemode='a')
cf = configparser.ConfigParser()
cf.read("./data/ConfigParser.conf")

# 读取配置mysql
db_host = cf.get("mysql", "db_host")
db_port = cf.getint("mysql", "db_port")
db_user = cf.get("mysql", "db_user")
db_pass = cf.get("mysql", "db_pass")
db = cf.get("mysql", "db")

# 创建insert_sql
insert_blog_sql = (
    "INSERT IGNORE INTO gulangyu.ctrip_blog(user_name, create_time, blog, star, scenery_star, interest_star, performance_star, travel_time, scenery) VALUES('{user_name}', '{create_time}','{blog}','{star}','{scenery_star}', '{interest_star}', '{performance_star}', '{travel_time}', '{scenery}')"
)

insert_pic_sql = (
    "INSERT IGNORE INTO gulangyu.ctrip_pics(pic_url, pic_bin, md5, exif) VALUES ('{pic_url}','{pic_bin}','{md5}','{exif}')"
)

insert_relationship_sql = (
    "INSERT IGNORE INTO gulangyu.ctrip_relationship(user_name, md5, scenery) VALUES ('{user_name}','{md5}', '{scenery}')"
)

url = 'http://you.ctrip.com/destinationsite/TTDSecond/SharedView/AsynCommentView'
user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36'
cookie = 'ASP.NET_SessionSvc=MTAuOC4xODkuNTZ8OTA5MHxqaW5xaWFvfGRlZmF1bHR8MTUwMDU0MDAxMTY4Mg; ASP.NET_SessionId=llp1osc0ejrpnx514beculek; _abtest_userid=6ba3a6e7-b467-43c7-a7a5-f9df2b6539f4; _bfi=p1%3D100003%26p2%3D0%26v1%3D1%26v2%3D0; bdshare_firstime=1511921790715; _ga=GA1.2.1170534963.1511921792; _gid=GA1.2.1773672486.1511921792; MKT_Pagesource=PC; appFloatCnt=1; manualclose=1; _bfa=1.1511852470959.vij5.1.1511921789102.1511966978022.3.3; _bfs=1.1; page_time=1511852472334%2C1511921790642%2C1511966980133; _RF1=119.36.214.6; _RSG=HYKTjJ9ngFFxfmOUr9OoA9; _RDG=289caa714119b022b402ce802a4784c45c; _RGUID=f3eac494-ed75-4891-92b2-609d5e630a7b; Session=smartlinkcode=U135371&smartlinklanguage=zh&SmartLinkKeyWord=&SmartLinkQuary=&SmartLinkHost=; Union=AllianceID=4899&SID=135371&OUID=&Expires=1512571780659; Mkt_UnionRecord=%5B%7B%22aid%22%3A%224899%22%2C%22timestamp%22%3A1511966980680%7D%5D; _jzqco=%7C%7C%7C%7C%7C1.1134122519.1511921791839.1511921791840.1511966980795.1511921791840.1511966980795.0.0.0.2.2; __zpspc=9.2.1511966980.1511966980.1%233%7Cwww.google.com%7C%7C%7C%7C%23'
Content_Type = 'application/x-www-form-urlencoded'
Accept_Encoding = 'gzip, deflate'
headers = {
    'User-Agent': user_agent,
    'Cookie': cookie,
    'Content-Type': Content_Type,
    'Accept-Encoding': Accept_Encoding
}


# 处理图片数据
def handle_pic(pic_url):
    large_bin = requests.get(pic_url)
    return large_bin.content


def get_comment(num, poiID, resourceId, scenery_name):
    # 创建连接
    conn = pymysql.connect(host=db_host, user=db_user, passwd=db_pass, db=db, port=db_port, charset='utf8')
    # 获取游标
    cursor = conn.cursor()

    form_data = {
        'poiID': poiID,
        'districtId': 120058,
        'districtEName': 'Gulangyu',
        'pagenow': num,
        'order': 3.0,
        'star': 0,
        'tourist': 0.0,
        'resourceId': resourceId,
        'resourcetype': 2,
    }

    req = requests.post(url=url, data=form_data).content.decode('utf-8')
    soup = BeautifulSoup(req, 'lxml')

    blog_all = soup.find_all('span', {'class': 'heightbox'})
    description = soup.find_all('li', {'itemprop': 'description'})
    star_all = soup.find_all('li', {'class': 'title cf'})
    travel_time_all = soup.find_all('span', {'class': 'youcate'})
    user_all = soup.find_all('a', {'itemprop': 'author'})
    create_time_all = soup.find_all('em', {'itemprop': 'datePublished'})

    for i in range(len(blog_all)):
        blog = blog_all[i].text.replace('\'', '\'\'')
        try:
            scenery_star = re.findall(re.compile(r'景色：\d'),
                                      star_all[i].find('span', {'class': 'sblockline'}).text)[0].strip('景色：')
            interest_star = re.findall(re.compile(r'趣味：\d'),
                                       star_all[i].find('span', {'class': 'sblockline'}).text)[0].strip('趣味：')
            performance_star = re.findall(re.compile(r'性价比：\d'),
                                          star_all[i].find('span', {'class': 'sblockline'}).text)[0].strip('性价比：')
        except Exception as e:
            scenery_star = None
            interest_star = None
            performance_star = None
        try:
            travel_time = re.findall(re.compile(r'\d{4}-\d'), travel_time_all[i].text)[0]
        except Exception as e:
            travel_time = None

        user_name = user_all[i].text
        create_time = create_time_all[i].text
        total_star = int(star_all[i].span.span.span['style'].split(':')[-1].replace('%;', '')) / 20
        print(total_star)

        print(insert_blog_sql.format(user_name=user_name, create_time=create_time, blog=blog, star=total_star,
                                     scenery_star=scenery_star, interest_star=interest_star,
                                     performance_star=performance_star, travel_time=travel_time, scenery=scenery_name))
        cursor.execute(insert_blog_sql.format(user_name=user_name, create_time=create_time, blog=blog, star=total_star,
                                              scenery_star=scenery_star, interest_star=interest_star,
                                              performance_star=performance_star, travel_time=travel_time,
                                              scenery=scenery_name))
        conn.commit()

    # 获取含图片标签的id
    have_img_uid = [img.parent.previous_sibling.previous_sibling.span.a.text for img in description if
                    img.find_next_sibling('li').get('class')[0] == 'comment_piclist']

    # 获取图片列表
    include_img = [img.find_next_sibling('li') for img in description if
                   img.find_next_sibling('li').get('class')[0] == 'comment_piclist']

    for index in range(len(have_img_uid)):
        pic_urls = [i['href'] for i in include_img[index].find_all('a')]
        user = have_img_uid[index]
        # 处理图片
        for pic_url in pic_urls:
            # 获取原图片二进制数据'
            pic_bin = handle_pic(pic_url)
            # 读取exif 数据
            pic_file = BytesIO(pic_bin)  # 将二进制数据转化成文件对象便于读取exif数据信息和生成MD5

            try:

                tag1 = exifread.process_file(pic_file, details=False, strict=True)
                tag = {}
                for key, value in tag1.items():
                    if key not in (
                            'JPEGThumbnail', 'TIFFThumbnail', 'Filename',
                            'EXIF MakerNote'):  # 去除四个不必要的exif属性，简化信息量
                        tag[key] = str(value)
                tags = json.dumps(tag).replace('\'', '\'\'')  # dumps为json类型 此tag即为exif的json数据
                # 生成MD5

            except:
                tags = None
            MD5 = hashlib.md5(pic_file.read()).hexdigest()
            # 首先把二进制图片用base64 转成字符串之后再存
            # 判断是否已经存在图片
            judge_pics = (
                "SELECT md5 FROM gulangyu.ctrip_pics WHERE md5 = '{md5}' LIMIT 1"
            )

            cursor.execute(judge_pics.format(md5=MD5))
            pic_md5 = cursor.fetchone()

            # 如果不存在就插入图片，否则就pass
            if pic_md5 is None:
                cursor.execute(
                    insert_pic_sql.format(
                        pic_url=pic_url,
                        pic_bin=str(base64.b64encode(pic_bin))[2:-1], md5=MD5,
                        exif=tags))
            else:
                logging.warning("Duplicate  " + pic_md5[0])

            cursor.execute(insert_relationship_sql.format(user_name=user, md5=MD5, scenery=scenery_name))
            conn.commit()
            # conn.close()


if __name__ == '__main__':
    df = pd.read_csv('./data/gulangyu.csv', encoding='utf-8')
    for p in df.iterrows():
        scenery_name = p[1]['Name']
        poiID = p[1]['poiID']
        resourceId = p[1]['resourceId']
        print(scenery_name)
        for page in range(1, 101):
            time.sleep(random.choice(range(1, 10)))
            get_comment(num=page, poiID=poiID, resourceId=resourceId, scenery_name=scenery_name)
