#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by Baoyi on 09/01/2018

import requests
from bs4 import BeautifulSoup
import pandas as pd
from pymongo import *

# 配置pymongo
mongo_client = MongoClient('localhost', 27017)
spider = mongo_client['ctrip']
profile = spider['ma']

base_url = 'http://you.ctrip.com/sightlist/malaysia100022/s0-p{}.html'
second_url = 'http://you.ctrip.com'

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36'
cookie = 'ASP.NET_SessionId=llp1osc0ejrpnx514beculek; _abtest_userid=6ba3a6e7-b467-43c7-a7a5-f9df2b6539f4; bdshare_firstime=1511921790715; cticket=BEA660BF6397F5CC57C00F872D633109C50950CA7803949D01A4D193F6332FE2; DUID=u=A1DFAAE99DB5F27AE3EB345BCA5F2159&v=0; IsNonUser=F; ticket_ctrip=uoeOwviAJ6VQEgTNwLuTqSV9j/bS+aOP3Riia1P+kyQbgkQZsD2gidJzD+FCHrgXcbJj2UyTW9FYtAqWFVUwTrBzHB4HyhFko9JIGHG0BW+LX5x0/56nlWHtd21cnKfrQ8o/1sDw03xS/wTYhG4su1QTznnqgybpyTUIIjuVV8X59LNJPKGEee0ydN9nRR5gOsQQsg9hdLsgOCcxd35T8OgJyUtg02lI2qCgadZ0F8nXPweCsI7Y6sHdTHqtkw5nnssLF1qFDPjTWpo/kpC6vr+8It2xsX2SYyV6+K8xX6ucEW9vjkahmoAuY50uTgvq; corpid=; corpname=; CtripUserInfo=VipGrade=0&UserName=&NoReadMessageCount=0&U=DECAB38A802B9A472A7D632CCBD1F8A7; AHeadUserInfo=VipGrade=0&UserName=&NoReadMessageCount=0&U=DECAB38A802B9A472A7D632CCBD1F8A7; LoginStatus=1%7c; __utma=1.1170534963.1511921792.1512012024.1512012024.1; __utmc=1; __utmz=1.1512012024.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); ASP.NET_SessionSvc=MTAuOC4xODkuNTZ8OTA5MHxqaW5xaWFvfGRlZmF1bHR8MTUxMjA5MzU2NjE2OA; _RSG=HYKTjJ9ngFFxfmOUr9OoA9; _RDG=289caa714119b022b402ce802a4784c45c; _RGUID=f3eac494-ed75-4891-92b2-609d5e630a7b; _ga=GA1.2.1170534963.1511921792; _RF1=67.205.145.3; Session=smartlinkcode=U135371&smartlinklanguage=zh&SmartLinkKeyWord=&SmartLinkQuary=&SmartLinkHost=; Union=AllianceID=4899&SID=135371&OUID=&Expires=1515846592889; Customer=HAL=ctrip_gb; TraceSession=1776497254; MKT_Pagesource=PC; appFloatCnt=12; _gid=GA1.2.1237150113.1515374741; manualclose=1; _bfa=1.1511852470959.vij5.1.1515374737818.1515460493681.16.200; _bfs=1.6; Mkt_UnionRecord=%5B%7B%22aid%22%3A%224899%22%2C%22timestamp%22%3A1515460558196%7D%5D; __zpspc=9.15.1515460495.1515460558.7%233%7Cwww.google.com%7C%7C%7C%7C%23; _jzqco=%7C%7C%7C%7C%7C1.1134122519.1511921791839.1515460542837.1515460558278.1515460542837.1515460558278.0.0.0.186.186; _bfi=p1%3D290510%26p2%3D290510%26v1%3D200%26v2%3D199'
Content_Type = 'application/x-www-form-urlencoded'
Accept_Encoding = 'gzip, deflate'
headers = {
    'User-Agent': user_agent,
    'Cookie': cookie,
    'Content-Type': Content_Type,
    'Accept-Encoding': Accept_Encoding
}

final_data = []

for i in range(1, 64):
    try:

        req = requests.get(base_url.format(i), headers=headers)
        soup = BeautifulSoup(req.content.decode('utf-8'), 'lxml')

        rdetailbox = soup.find_all('div', {'class': 'rdetailbox'})

        for u in rdetailbox:
            url = second_url + u.dl.dt.a['href']
            get_poiid = requests.get(url, headers=headers)
            poiid_soup = BeautifulSoup(get_poiid.content.decode('utf-8'), 'lxml')

            comment_entrance = poiid_soup.find('div', {'class': 'comment_entrance'})
            poiid = comment_entrance.span.a['data-id']
            data = {
                'Name': u.dl.dt.a['title'],
                'resourceId': url.split('/')[-1][:-5],
                'poiID': poiid
            }
            print(data)
            profile.insert(data)
            final_data.append(data)
    except Exception as e:
        print(e)
        pass

df = pd.DataFrame(final_data, columns=['Name', 'poiID', 'resourceId'], index=False)
df.to_csv('./data/ctrip_ma.csv', encoding='utf-8')
