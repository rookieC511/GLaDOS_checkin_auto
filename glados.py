import requests
import json
import os

# -------------------------------------------------------------------------------------------
# GLaDOS Checkin Script (iOS/Mobile Simulation Mode)
# -------------------------------------------------------------------------------------------

def glados_checkin():
    # 1. 获取 Cookie
    cookie_str = os.environ.get("GLADOS_COOKIE", "")
    if not cookie_str:
        print("❌ 错误: 未找到 GLADOS_COOKIE 环境变量")
        return

    # 清理 Cookie 格式 (移除 curl 命令中可能的干扰字符)
    # 兼容用户直接粘贴 curl 命令里的 cookie 格式
    if 'koa:sess=' not in cookie_str:
        print("⚠️ 警告: Cookie 格式看起来不太对，请确保包含 koa:sess")

    # 2. PushPlus 配置
    sckey = os.environ.get("PUSHPLUS_TOKEN", "")
    send_content = ""

    # 3. 核心配置 (伪装成 iPhone)
    base_url = "https://glados.cloud"
    checkin_url = f"{base_url}/api/user/checkin"
    status_url = f"{base_url}/api/user/status"
    
    # ⚠️ 关键修改：使用你 cURL 里的 iPhone User-Agent
    mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"

    headers = {
        "cookie": cookie_str, # 直接使用完整字符串，不再分割
        "referer": f"{base_url}/console/checkin",
        "origin": base_url,
        "user-agent": mobile_ua,
        "content-type": "application/json;charset=UTF-8",
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        # 补充 cURL 里的一些头信息
        "priority": "u=1, i",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin"
    }
    
    payload = {"token": "glados.network"}

    print(f"📱 正在以 iPhone 身份连接: {base_url}")

    try:
        # --- 动作 A: 签到 ---
        print(f"正在签到...")
        resp = requests.post(checkin_url, headers=headers, json=payload)
        
        # 调试输出
        if resp.status_code != 200:
            print(f"❌ HTTP错误: {resp.status_code}")
            print(resp.text)
        
        res_json = resp.json()
        message = res_json.get("message", "")
        print(f"签到响应: {message}")

        # --- 动作 B: 查状态 ---
        print(f"正在获取状态...")
        status_resp = requests.get(status_url, headers=headers)
        
        if status_resp.status_code == 200 and 'data' in status_resp.json():
            data = status_resp.json()['data']
            email = data.get('email', 'Unknown')
            points = data.get('points', 0)
            left_days = data.get('leftDays', '?').split('.')[0]
            
            log_msg = f"✅ 用户: {email} | 结果: {message} | 📅 剩余: {left_days}天 | 💰 积分: {points}"
            print(log_msg)
            send_content += log_msg + "\n"
            
            if int(points) >= 200:
                send_content += "👉 提示: 积分已超 200，请及时兑换！\n"
        else:
            print(f"⚠️ 状态获取失败: {status_resp.text}")
            send_content += f"签到响应: {message}，但无法获取积分详情。\n"

    except Exception as e:
        print(f"❌ 运行异常: {e}")
        send_content += f"脚本运行出错: {str(e)}\n"

    # 推送消息
    if sckey and send_content:
        requests.post("http://www.pushplus.plus/send", json={
            "token": sckey,
            "title": "GLaDOS签到汇报",
            "content": send_content,
            "template": "txt"
        })

if __name__ == '__main__':
    glados_checkin()
