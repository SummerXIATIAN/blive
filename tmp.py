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