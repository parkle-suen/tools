# 通知库

import os
import requests


DEFAULT_TOPIC ="169"
DEFAULT_NTFY_URL=f"http://192.168.0.169:8125/{DEFAULT_TOPIC}"

def send_ntfy(message: str, title: str = None, priority: str = None, tags: str = None):
    base_url = os.getenv("NTFY_BASE_URL") or DEFAULT_NTFY_URL
    topic = os.getenv("NTFY_TOPIC") or DEFAULT_TOPIC
    
    if not base_url or not topic:
        print(f"⚠️ ntfy 通知跳过：缺少 NTFY_BASE_URL 或 NTFY_TOPIC 环境变量")
        print(f"通知内容: {title or ''} - {message}")
        return
    
    url = f"{base_url.rstrip('/')}/{topic}"
    headers = {"Title": title or "", "Priority": priority or "", "Tags": tags or ""}
    try:
        requests.post(url, data=message.encode('utf-8'), headers=headers)
    except Exception as e:
        print(f"❌ ntfy 发送失败: {e}")
