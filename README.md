## gulangyu

#### data 文件夹里面有建立数据库的sql语句和鼓浪屿的各个景点的poiid和resourceid等值，还有配置文件可以根据自己本地的设置更改

#### ctrip_all.py 是爬取携程的评论数据 

#### mafengwo_all.py 是爬取蚂蜂窝的数据

---
#### 更新

先运行get_ctrip_poiid.py 获取poiid以后再运行 ctrip_all.py 
如果不需要存入mongo 可以自行删除 相关数据库操作代码
