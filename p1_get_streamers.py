import pandas as pd
import numpy as np
import requests
import json
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

mini_guardNum = int(config['streamer']['mini_guardNum'])
mini_guardNum_vtb = int(config['streamer']['mini_guardNum_vtb'])
mini_guardNum_top = int(config['streamer']['mini_guardNum_top'])
mini_follower_vtb = int(config['streamer']['mini_follower_vtb'])
max_page_top100 = int(config['streamer']['max_page_top100'])


### Get Vtuber List from Vtbs.moe
def get_vtuber():
    '''Request data from https://vtbs.moe, return a list of dict about vtuber'''

    url = "https://api.vtbs.moe/v1/info"

    payload = {}
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload)
    r = json.loads(response.text)

    ## Format data
    df = pd.DataFrame(r,columns=['uname','mid','roomid','follower','guardNum'])
    df = df.fillna(0)
    df = df.astype({"mid": int, "roomid": int, "follower": int, "guardNum": int})
    df = df.astype({"mid": str, "roomid": str})
    return df

## Get Top Streamers from Bilibili
def get_topStreamer(gid,page=1,page_size=100,max_page=3):
    '''Request data from bili航海名人堂,
        - gid: type of scale
            -  241: 10000+
            -  75: 1000+ 
            -  76: 100+
        - page: start from page #
        - page_size: amount of streamers in one page
        - max_page: page number limit
        
    return a dataframe of dict about top streamers'''

    payload = {}
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Cookie": 'LIVE_BUVID=AUTO2716990584154319'
    }
    url = f"https://api.live.bilibili.com/xlive/app-ucenter/v1/guard/Honor?target_id=0&gid={gid}&area_id=0&page={page}&page_size={page_size}"
    
    response = requests.request("GET", url, headers=headers, data=payload)
    r = json.loads(response.text)
    
    ### Get total number of this type of streamers
    attr = ['room_id','uid','name','guard_num','gid']
    t_num = r['data']['page']['total_count']
    t_page = int(t_num/page_size) + 1
    print(f"Streamer Type: {gid}, Total count: {t_num}, Total page num: {t_page}")
    
    ### Get data from each page
    if t_page > max_page:
        print(f"Limit page depth from {t_page} to {max_page}")
        t_page = max_page
        
    result = []
    for p in range(page, t_page+1):
        if p%20 == 0:
            print(f"Processing Page {p}...")
        url = f"https://api.live.bilibili.com/xlive/app-ucenter/v1/guard/Honor?target_id=0&gid={gid}&area_id=0&page={p}&page_size={page_size}"
        response = requests.request("GET", url, headers=headers, data=payload)
        r = json.loads(response.text)
        userList = [{k: v for k, v in u.items() if k in attr} for u in r['data']['list']]
        result += userList
    
    df_t = pd.DataFrame.from_dict(result)
    return df_t


## Get Vtuber List
df_v = get_vtuber()

## Vtuber Selection
df_v['coefficent'] = 63.4*np.log(df_v['follower']) + df_v['guardNum'] - 790
df_v = df_v[(df_v['guardNum']>mini_guardNum_vtb) & (df_v['follower']>mini_follower_vtb)]
df_vtb = df_v[df_v['coefficent'] > 0].sort_values(by='guardNum',ascending=False)

## Get Top Streamers
top10000 = get_topStreamer(gid=241)
top1000 = get_topStreamer(gid=75)
top100 = get_topStreamer(gid=76,max_page=max_page_top100)

## Top Streamers Selection
pdList = [top10000, top1000, top100]  # List of dataframes
df_top = pd.concat(pdList)
df_top = df_top[df_top['name'] != '账号已注销']
df_top = df_top[df_top['guard_num'] > mini_guardNum_top]
df_top = df_top[['name', 'uid', 'room_id', 'guard_num', 'gid']]
df_top.columns = ['uname', 'mid', 'roomid', 'guardNum', 'gid']
df_top = df_top.astype({"mid": str, "roomid": str})

## Merge top streamers and vtubers
df_all = pd.concat([df_vtb, df_top])
df_all = df_all.drop_duplicates(subset=['mid'])
df_all = df_all.sort_values(by='guardNum',ascending=False)
df_all

## Save data
df_result = df_all[df_all['guardNum']>mini_guardNum]
df_result.to_csv('data/streamer_info.csv',index=False)
print(f"Total Streamers: {len(df_result)}")