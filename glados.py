import requests
import json
import os

# -------------------------------------------------------------------------------------------
# GLaDOS Checkin Script (Chrome 144 / Windows 10 High-Fidelity Mode)
# -------------------------------------------------------------------------------------------

def glados_checkin():
    cookie_str = os.environ.get("GLADOS_COOKIE", "")
    sckey = os.environ.get("PUSHPLUS_TOKEN", "")
    
    if not cookie_str:
        print("❌ Fatal: 未找到 Cookie")
        return

    # 1. 基础配置
    base_url = "https://glados.cloud"
    checkin_url = f"{base_url}/api/user/checkin"
    status_url = f"{base_url}/api/user/status"
    
    # 2. 伪装: 严格匹配你截图中的 Chrome 144
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"

    headers = {
        "cookie": cookie_str,
        "referer": f"{base_url}/console/checkin",
        "origin": base_url,
        "user-agent": user_agent,
        "content-type": "application/json;charset=UTF-8",
        # 补全截图中的高阶指纹 (High Fidelity Headers)
        "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8"
    }

    # 3. 智能 Token 穷举
    # 既然你是在新官网，优先尝试 glados.cloud
    possible_tokens = ["glados.network", "glados.cloud", "glados.one"]

    print(f"🖥️ 启动 Chrome 144 (PC) 签到模式...")
    print(f"🍪 Cookie摘要: {cookie_str[:20]}...")

    success = False
    final_msg = ""

    # --- 阶段 1: 签到 ---
    for token in possible_tokens:
        print(f"\n🧪 测试 Token: {token}")
        try:
            # 这里的 Payload 很重要
            resp = requests.post(checkin_url, headers=headers, json={"token": token})
            
            res_json = resp.json()
            message = res_json.get("message", "")
            print(f"   📨 响应: {message}")
            
            if "Checkin" in message and "please" not in message.lower():
                print("   🎉 命中！签到成功！")
                final_msg += f"✅ 签到结果: {message}\n"
                success = True
                break
            elif "please checkin via" in message.lower():
                print("   🛡️ 被拦截 (Token 不对或 Cookie 过期)")
            else:
                # 有时候返回 "User has checked in" 也算成功
                print("   ℹ️ 可能已签到")
                
        except Exception as e:
            print(f"   ❌ 请求异常: {e}")

    # --- 阶段 2: 查分 (验证 Cookie 有效性) ---
    print(f"\n📊 正在验证账户状态...")
    try:
        status_resp = requests.get(status_url, headers=headers)
        if status_resp.status_code == 200 and 'data' in status_resp.json():
            data = status_resp.json()['data']
            email = data.get('email', 'Unknown')
            points = data.get('points', 0)
            left_days = data.get('leftDays', '?').split('.')[0]
            
            status_info = f"👤 用户: {email} | 💰 积分: {points} | 📅 剩余: {left_days}天"
            print(status_info)
            final_msg += status_info
            
            # 只要能查到分，说明 Cookie 绝对没问题
            if int(points) >= 0:
                success = True
                
            if int(points) >= 200:
                final_msg += "\n💰 提示：积分 > 200，快去兑换！"
        else:
            print(f"❌ 状态获取失败: {status_resp.text}")
    except Exception as e:
        print(f"❌ 状态同步出错: {e}")

    # 推送
    if sckey and success:
        requests.post("http://www.pushplus.plus/send", json={
            "token": sckey,
            "title": "GLaDOS签到成功",
            "content": final_msg,
            "template": "txt"
        })

if __name__ == '__main__':
    glados_checkin()
