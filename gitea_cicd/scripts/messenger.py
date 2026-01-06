# 通知库

import os
import requests


# DEFAULT_TOPIC ="169"
# DEFAULT_NTFY_URL=f"http://192.168.0.169:8125/{DEFAULT_TOPIC}"

def send_ntfy(message, title="CI/CD Notification", tags="rocket", priority="default"):
    """
    通用通知函数，支持 ntfy
    """
    ntfy_url = os.getenv("NTFY_URL")+"/"+os.getenv("NTFY_TOPIC")
    if not ntfy_url:
        print("未配置 NTFY_URL，跳过通知。")
        return

    try:
        response=requests.post(
            ntfy_url,
            data=message.encode('utf-8'),
            headers={
                "Title": title.encode('utf-8'),
                "Priority": priority,
                "Tags": tags
            },
            timeout=10
        )
        # 这一行确保了如果服务器返回 404 或 500，也会打印出来
        response.raise_for_status() 
    except Exception as e:
        print(f"发送通知失败: {e}")
