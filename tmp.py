import requests

url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/guard/Honor?target_id=0&gid=241&area_id=0&page=1&page_size=100"

payload = {}
headers = {
    "Content-Type": "application/json; charset=utf-8",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Cookie": 'LIVE_BUVID=AUTO2716990584154319'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)


# [streamer]
# mini_guardNum = 20
# mini_guardNum_vtb = 20
# mini_guardNum_top = 20
# mini_follower_vtb = 10000
# max_page_top100 = 3

# [fans_group]
# WORKERS_NUM = 8

# [cal_common]
# fans_type = fans

# [clustering]
# threshold_follower = 400
# threshold_count = 20
# threshold_percentage = 0.04
# threshold_percentage_reverse = 0.04
# profile_num = 20