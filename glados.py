import requests, json, os

# -------------------------------------------------------------------------------------------
# github workflows: GLaDOS Checkin (2026 Updated Domain)
# -------------------------------------------------------------------------------------------
if __name__ == '__main__':
    # pushplus秘钥 申请地址 http://www.pushplus.plus
    sckey = os.environ.get("PUSHPLUS_TOKEN", "")
    
    # 推送内容
    sendContent = ''
    
    # glados账号cookie
    # 兼容处理：如果 secrets 里没有配置，避免 split 报错
    cookie_str = os.environ.get("GLADOS_COOKIE", "")
    if not cookie_str:
        print('未获取到 COOKIE 变量，请检查 GitHub Secrets')
        exit(0)
        
    cookies = cookie_str.split("&")
    
    # ------------------------------------------------------
    # 🔄 核心修改：域名从 glados.rocks 更新为 glados.cloud
    # ------------------------------------------------------
    base_url = "https://glados.cloud"
    url = f"{base_url}/api/user/checkin"
    url2 = f"{base_url}/api/user/status"
    referer = f"{base_url}/console/checkin"
    origin = base_url
    
    useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    # Token 通常跟随域名更新，使用通用的 glados.network
    payload = {
        'token': 'glados.network'
    }

    for cookie in cookies:
        if not cookie.strip():
            continue
            
        try:
            # 1. 执行签到
            checkin = requests.post(url, headers={
                'cookie': cookie,
                'referer': referer,
                'origin': origin,
                'user-agent': useragent,
                'content-type': 'application/json;charset=UTF-8'
            }, data=json.dumps(payload))
            
            # 2. 获取状态 (查分)
            state = requests.get(url2, headers={
                'cookie': cookie,
                'referer': referer,
                'origin': origin,
                'user-agent': useragent
            })
            
            # 解析数据
            if state.status_code == 200 and 'data' in state.json():
                data = state.json()['data']
                left_days = data['leftDays'].split('.')[0]
                points = data.get('points', 0) # ✨ 新增：获取积分
                email = data['email']
                
                # 获取签到返回的消息
                mess = checkin.json().get('message', 'Checkin OK')
                
                # --- 日志格式优化 ---
                log_msg = f"{email} | 结果: {mess} | 剩余: {left_days}天 | 💰积分: {points}"
                print(log_msg)
                
                sendContent += log_msg + '\n'
                
                # 简单的积分兑换提醒
                if int(points) >= 200:
                    sendContent += "⚠️ 提示：积分已达标，请去官网兑换 30 天！\n"
            else:
                print('cookie已失效或网络错误')
                requests.get('http://www.pushplus.plus/send?token=' + sckey + '&content=GLaDOS_Cookie已失效')
                
        except Exception as e:
            print(f"账号处理出错: {e}")

    # 推送消息
    if sckey != "" and sendContent != "":
        requests.get('http://www.pushplus.plus/send?token=' + sckey + '&title=GLaDOS签到通知&content=' + sendContent)
