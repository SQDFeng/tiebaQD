import os
import json
import time
import random
import requests
import re
import urllib.parse
from datetime import datetime


COOKIE_ENV_NAME = "TIEBA_COOKIES"


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://tieba.baidu.com",
    "Origin": "https://tieba.baidu.com"
}


def decode_kw(kw):
    try:
        return urllib.parse.unquote_to_bytes(kw).decode("gbk")
    except:
        return urllib.parse.unquote(kw)


def get_cookies():
    cookies_json = os.environ.get(COOKIE_ENV_NAME)

    if not cookies_json:
        print("❌ 未找到 Cookie 环境变量")
        return None

    cookies_list = json.loads(cookies_json)

    cookie_dict = {}

    for item in cookies_list:

        if isinstance(item, dict):

            cookie_dict[item["name"]] = item["value"]

    return cookie_dict


def get_tieba_list(cookie_dict):

    base_url = "https://tieba.baidu.com/f/like/mylike"

    page = 1

    all_tiebas = []

    print("🔄 获取贴吧列表")

    while True:

        resp = requests.get(
            base_url,
            headers=HEADERS,
            cookies=cookie_dict,
            params={"pn": page},
            timeout=15
        )

        resp.encoding = "gbk"

        html = resp.text

        matches = re.findall(r'/f\?kw=([^"&]+)', html)

        page_list = []

        for kw in matches:

            name = decode_kw(kw)

            if name not in page_list:

                page_list.append(name)

        if not page_list:

            break

        for tb in page_list:

            if tb not in all_tiebas:

                all_tiebas.append(tb)

        print(f"📄 第 {page} 页 {len(page_list)} 个贴吧")

        if page == 1:

            print("示例:", page_list[:5])

        page += 1

        time.sleep(random.uniform(1.5, 3))

    print(f"✅ 共 {len(all_tiebas)} 个贴吧")

    return all_tiebas


def get_tbs(cookie_dict):

    url = "https://tieba.baidu.com/dc/common/tbs"

    r = requests.get(url, headers=HEADERS, cookies=cookie_dict)

    data = r.json()

    if data["is_login"] == 1:

        return data["tbs"]

    return ""


def verify_vcode(cookie_dict, vcode_str):

    url = "https://tieba.baidu.com/sign/checkVcode"

    random_code = ''.join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(4))

    data = {
        "captcha_vcode_str": vcode_str,
        "captcha_input_str": random_code
    }

    r = requests.post(url, headers=HEADERS, cookies=cookie_dict, data=data)

    try:

        res = r.json()

        if res.get("anti_valve_err_no") == 0:

            return random_code

    except:

        pass

    return None


def sign_tieba(name, cookie_dict):

    url = "https://tieba.baidu.com/sign/add"

    tbs = get_tbs(cookie_dict)

    retry = 0

    captcha_vcode = None
    captcha_input = None

    while retry < 3:

        data = {
            "ie": "gbk",
            "kw": name,
            "tbs": tbs
        }

        if captcha_vcode:

            data["captcha_vcode_str"] = captcha_vcode
            data["captcha_input_str"] = captcha_input

        r = requests.post(url, headers=HEADERS, cookies=cookie_dict, data=data)

        try:

            j = r.json()

        except:

            return False, "返回异常"

        code = j.get("no")

        if code == 0:

            return True, "签到成功"

        if code == 160002:

            return True, "今日已签"

        if code == 1102:

            print("⚠️ 签到太快，1秒后重试")

            time.sleep(1)

            retry += 1

            continue

        if code == 2150040:

            print("⚠️ 触发验证码")

            vcode_str = j["data"]["captcha_vcode_str"]

            captcha_input = verify_vcode(cookie_dict, vcode_str)

            if captcha_input:

                captcha_vcode = vcode_str

                print("✔ 验证通过，重新签到")

                continue

            return False, "验证码验证失败"

        return False, j.get("error_msg", str(code))

    return False, "重试失败"


def main():

    print("="*40)

    print("贴吧签到启动", datetime.now())

    print("="*40)

    cookie = get_cookies()

    if not cookie:

        return

    tieba_list = get_tieba_list(cookie)

    if not tieba_list:

        return

    success = 0

    for i, tb in enumerate(tieba_list, 1):

        print(f"[{i}/{len(tieba_list)}] {tb}", end=" ")

        time.sleep(random.uniform(1, 2))

        ok, msg = sign_tieba(tb, cookie)

        if ok:

            success += 1

            print("✅", msg)

        else:

            print("❌", msg)

    print("\n完成")

    print("成功:", success, "/", len(tieba_list))


if __name__ == "__main__":

    main()
