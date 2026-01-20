import requests
import json
import os

# -------------------------------------------------------------------------------------------
# GLaDOS Checkin Script (Target: glados.cloud)
# -------------------------------------------------------------------------------------------

def glados_checkin():
    # 1. 获取 Cookie
    cookie_str = os.environ.get("GLADOS_COOKIE", "")
    if not cookie_str:
        print("❌ 错误: 未找到 GLADOS_COOKIE 环境变量，请在 Settings -> Secrets 中配置。")
        return

    cookies = cookie_str.split("&")
    
    # 2. PushPlus 配置
    sckey = os.environ.get("PUSHPLUS_TOKEN", "")
    send_content = ""

    # 3. 核心配置 (针对 glados.cloud)
    # 网页地址: https://glados.cloud/console/checkin
    # 接口地址: https://glados.cloud/api/user/checkin
    base_url = "https://glados.cloud"
    checkin_url = f"{base_url}/api/user/checkin"
    status_url = f"{base_url}/api/user/status"
    
    # 伪装成真实的浏览器访问
    headers = {
        "cookie": "",  # 后面循环里填
        "referer": f"{base_url}/console/checkin",
        "origin": base_url,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "content-type": "application/json;charset=UTF-8",
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    
    payload = {"token": "glados.network"}

    print(f"🚀 正在尝试连接新域名: {base_url}")

    for idx, cookie in enumerate(cookies):
        if not cookie.strip(): continue
        
        # 移除可能误复制的 "cookie:" 前缀
        clean_cookie = cookie.replace("cookie:", "").replace("Cookie:", "").strip()
        headers["cookie"] = clean_cookie

        try:
            # --- 动作 A: 签到 ---
            print(f"[{idx+1}] 正在签到...")
            resp = requests.post(checkin_url, headers=headers, json=payload)
            
            # 调试：如果不是 200，打印出来看看到底报什么错
            if resp.status_code != 200:
                print(f"❌ 签到请求失败: HTTP {resp.status_code}")
                print(f"❌ 服务器返回: {resp.text}")
                continue
                
            res_json = resp.json()
            message = res_json.get("message", "")
            
            # --- 动作 B: 查状态 ---
            print(f"[{idx+1}] 正在获取状态...")
            status_resp = requests.get(status_url, headers=headers)
            
            if status_resp.status_code == 200 and 'data' in status_resp.json():
                data = status_resp.json()['data']
                email = data.get('email', 'Unknown User')
                points = data.get('points', 0)
                left_days = data.get('leftDays', '?').split('.')[0]
                
                log_msg = f"✅ 用户: {email} | 结果: {message} | 📅 剩余: {left_days}天 | 💰 积分: {points}"
                print(log_msg)
                send_content += log_msg + "\n"
                
                if int(points) >= 200:
                    send_content += "👉 提示: 积分已超 200，可去官网兑换 30 天！\n"
            else:
                print(f"⚠️ 状态获取失败: {status_resp.text}")
                send_content += f"用户{idx+1}: 签到成功但无法获取详情 (Cookie可能部分失效)\n"

        except Exception as e:
            print(f"❌ 运行异常: {e}")
            send_content += f"用户{idx+1}: 脚本运行出错\n"

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
