import os
import json
import time
import random
import requests
import re
import urllib.parse
from datetime import datetime


# ================= 配置区域 =================
COOKIE_ENV_NAME = "TIEBA_COOKIES"
NOTIFY_KEY = os.environ.get("SendKey", "")


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://tieba.baidu.com",
    "Referer": "https://tieba.baidu.com/f/like/mylike",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive"
}


# ================= GBK解码修复 =================
def decode_kw(kw_encoded):
    """
    修复贴吧 kw 参数 GBK URL Encode
    """
    try:
        return urllib.parse.unquote_to_bytes(kw_encoded).decode("gbk")
    except:
        try:
            return urllib.parse.unquote(kw_encoded)
        except:
            return kw_encoded


def get_cookies():
    cookies_json = os.environ.get(COOKIE_ENV_NAME)
    if not cookies_json:
        print(f"❌ 未找到环境变量 [{COOKIE_ENV_NAME}]")
        return None
    try:
        cookies_list = json.loads(cookies_json)
        cookie_dict = {}
        bduss = ""
        for item in cookies_list:
            if isinstance(item, dict):
                name = item.get("name")
                value = item.get("value")
                if name and value:
                    cookie_dict[name] = value
                    if name == "BDUSS":
                        bduss = value
            elif isinstance(item, str) and "=" in item:
                n, v = item.split("=", 1)
                cookie_dict[n.strip()] = v.strip()
        if not bduss:
            print("⚠️ 警告：未找到 BDUSS，可能导致签到失败")
        return cookie_dict
    except Exception as e:
        print(f"❌ Cookie 解析失败: {e}")
        return None


def get_tieba_list(cookie_dict):
    base_url = "https://tieba.baidu.com/f/like/mylike"
    all_tiebas = []
    current_page = 1
    empty_count = 0
    
    print("🔄 开始获取贴吧列表...")


    while True:
        params = {"pn": current_page}
        try:
            resp = requests.get(base_url, headers=HEADERS, cookies=cookie_dict, params=params, timeout=15)

            # 强制GBK解析页面
            resp.encoding = "gbk"
            content = resp.text

            # 登录检测
            if "未登录" in content:
                print("❌ 检测到未登录，请检查 Cookie 是否过期。")
                return []

            pattern = r'/f\?kw=([^"&\']+)'
            matches = re.findall(pattern, content)

            page_tiebas = []

            for kw_encoded in matches:
                try:
                    real_name = decode_kw(kw_encoded)

                    clean_name = "".join(c for c in real_name if c.isprintable()).strip()

                    if clean_name and clean_name not in page_tiebas:
                        page_tiebas.append(clean_name)

                except:
                    continue

            if not page_tiebas:
                empty_count += 1
                if empty_count >= 1:
                    break
            else:
                empty_count = 0

                for tb in page_tiebas:
                    if tb not in all_tiebas:
                        all_tiebas.append(tb)

                print(f"📄 第 {current_page} 页：解析到 {len(page_tiebas)} 个贴吧 (总计: {len(all_tiebas)})")

                if current_page == 1:
                    print("🔎 示例:", page_tiebas[:5])

            current_page += 1

            time.sleep(random.uniform(1.5, 3.0))

        except Exception as e:
            print(f"❌ 第 {current_page} 页请求异常: {e}")
            break
            
    print(f"✅ 列表获取完成！共发现 {len(all_tiebas)} 个关注的贴吧。")
    return all_tiebas


def get_tbs(cookie_dict):
    url = "https://tieba.baidu.com/dc/common/tbs"
    try:
        resp = requests.get(url, headers=HEADERS, cookies=cookie_dict, timeout=10)
        data = resp.json()
        if data.get("is_login") == 1:
            return data.get("tbs")
        return ""
    except:
        return ""


def sign_tieba(tieba_name, cookie_dict):
    url = "https://tieba.baidu.com/sign/add"
    tbs = get_tbs(cookie_dict)

    if not tbs:
        return False, "tbs 获取失败"

    data = {
        "ie": "gbk",
        "kw": tieba_name,
        "tbs": tbs
    }

    try:
        resp = requests.post(url, headers=HEADERS, cookies=cookie_dict, data=data, timeout=10)
        res_json = resp.json()

        no_code = res_json.get("no")

        if no_code == 0:
            return True, "签到成功"
        elif no_code == 160002:
            return True, "今日已签"
        else:
            err_msg = res_json.get("error_msg", f"错误码:{no_code}")
            return False, err_msg

    except Exception as e:
        return False, str(e)


def send_notify(msg):
    if not NOTIFY_KEY:
        return

    try:
        requests.get(
            f"https://sctapi.ftqq.com/{NOTIFY_KEY}.send",
            params={"title": "贴吧签到结果", "desp": msg},
            timeout=5
        )
        print("📩 通知已发送。")

    except Exception as e:
        print(f"通知失败: {e}")


def main():
    print("="*40)
    print(f"🤖 贴吧签到启动：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*40)

    cookie_dict = get_cookies()

    if not cookie_dict:
        return

    tieba_list = get_tieba_list(cookie_dict)

    if not tieba_list:
        print("💤 未获取到贴吧列表，任务结束。")
        return

    print(f"🚀 开始全量签到，共 {len(tieba_list)} 个贴吧...")

    success_count = 0
    fail_count = 0
    result_log = []

    for i, tb in enumerate(tieba_list, 1):

        print(f"[{i}/{len(tieba_list)}] 正在签到：{tb} ...", end=" ")

        time.sleep(random.uniform(1, 2))

        status, msg = sign_tieba(tb, cookie_dict)

        if status:
            print(f"✅ {msg}")
            success_count += 1
            result_log.append(f"✅ {tb}: {msg}")
        else:
            print(f"❌ {msg}")
            fail_count += 1
            result_log.append(f"❌ {tb}: {msg}")

    summary = f"【签到总结】\n总数：{len(tieba_list)}\n成功：{success_count}\n失败/已签：{fail_count}"

    print("\n" + "="*40)
    print(summary)

    notify_content = summary + "\n\n最近日志:\n" + "\n".join(result_log[-10:])

    send_notify(notify_content)


if __name__ == "__main__":
    main()
