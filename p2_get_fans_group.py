from multiprocessing import Pool
import requests
import pandas as pd
import time
import requests
import json
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

WORKERS_NUM = int(config['fans_group']['WORKERS_NUM'])

def get_fans(ruid,page=1,page_size=100):
    '''get members (active viewers) in fans group
        - ruid: mid of the user
        - page: start from page #
        - page_size: number of members per page (max 30 actually))

    return: pandas dataframe'''
    payload={}
    headers = {
      'Cookie': 'LIVE_BUVID=AUTO1616700756065396'
    }
    url = f"https://api.live.bilibili.com/xlive/general-interface/v1/rank/getFansMembersRank?ruid={ruid}&page={page}&page_size={page_size}"
    
    response = requests.request("GET", url, headers=headers, data=payload)
    rf = json.loads(response.text)
    
    ### Get total number of this type of streamers
    fan_attr = ['user_rank','uid','name','score','medal_name','level','guard_level']
    f_num = rf['data']['num']
    f_page = int(f_num/30) + 1
    # print(f"Fans Num: {f_num}, Total page num: {f_page}")
    
    
    ### Get data from each page
    result = []
    for p in range(page, f_page+1):
        # if p%10 == 0:
            # print(f"Processing Page {p}...")
        url = f"https://api.live.bilibili.com/xlive/general-interface/v1/rank/getFansMembersRank?ruid={ruid}&page={p}&page_size={page_size}"
        response = requests.request("GET", url, headers=headers, data=payload)
        rf = json.loads(response.text)
        userList = [{k: v for k, v in u.items() if k in fan_attr} for u in rf['data']['item']]
        result += userList
    
    df_f = pd.DataFrame.from_dict(result)
    return df_f

def main(args):
    mid, uname = args
    '''Main function to get fans data'''

    try:
        df = get_fans(mid)
        if len(df) > 0:
            df.to_csv(f"data/fans/{uname}_fans.csv", index=False)
            print(f"Done! {uname}, with {len(df)} fans")
        else:
            print(f"Streamer {uname} has {len(df)} fans")
    except Exception as e:
        print(f"Error on Streamer {uname}, {e}.")

if __name__ == '__main__':
    df = pd.read_csv("data/streamer_info.csv")
    args = list(zip(df.mid, df.uname))
    # args = args[300:308]
    print(f"Total {len(args)} streamers")

    start_time = time.time()

    ## Single-process
    # for arg in args:
        # main(*arg)

    ## Multi-process
    with Pool(WORKERS_NUM) as p:
        p.map(main, args)
    print(f'TimeUsed: {time.time() - start_time:.1f} s')