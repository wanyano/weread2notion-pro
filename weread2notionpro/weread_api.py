import hashlib
import json
import os
import re

import requests
from requests.utils import cookiejar_from_dict
from retrying import retry
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()
WEREAD_URL = "https://weread.qq.com/"
WEREAD_NOTEBOOKS_URL = "https://i.weread.qq.com/user/notebooks"
WEREAD_BOOKMARKLIST_URL = "https://i.weread.qq.com/book/bookmarklist"
WEREAD_CHAPTER_INFO = "https://i.weread.qq.com/book/chapterInfos"
WEREAD_READ_INFO_URL = "https://i.weread.qq.com/book/readinfo"
WEREAD_REVIEW_LIST_URL = "https://i.weread.qq.com/review/list"
WEREAD_BOOK_INFO = "https://i.weread.qq.com/book/info"
WEREAD_READDATA_DETAIL = "https://i.weread.qq.com/readdata/detail"
WEREAD_HISTORY_URL = "https://i.weread.qq.com/readdata/summary?synckey=0"


class WeReadApi:
    def __init__(self):
        self.api_key = (os.getenv("WEREAD_API_KEY") or "").strip()
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
        else:
            self.cookie = self.get_cookie()
            self.session.cookies = self.parse_cookie_string()

    def gateway(self, api_name, **kwargs):
        """WeRead skill v1.0.5 gateway. Never log credentials or response bodies."""
        response = self.session.post(
            "https://i.weread.qq.com/api/agent/gateway",
            json={"api_name": api_name, "skill_version": "1.0.5", **kwargs},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("upgrade_info"):
            raise RuntimeError(f"WeRead gateway skill upgrade required: {data['upgrade_info']}")
        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"WeRead gateway request failed: {api_name}, code={data.get('errcode')}")
        return data

    def try_get_cloud_cookie(self, url, id, password):
        if url.endswith("/"):
            url = url[:-1]
        req_url = f"{url}/get/{id}"
        data = {"password": password}
        result = None
        response = requests.post(req_url, data=data)
        if response.status_code == 200:
            data = response.json()
            cookie_data = data.get("cookie_data")
            if cookie_data and "weread.qq.com" in cookie_data:
                cookies = cookie_data["weread.qq.com"]
                cookie_str = "; ".join(
                    [f"{cookie['name']}={cookie['value']}" for cookie in cookies]
                )
                result = cookie_str
        return result

    def get_cookie(self):
        url = os.getenv("CC_URL")
        if not url:
            url = "https://cookiecloud.malinkang.com/"
        id = os.getenv("CC_ID")
        password = os.getenv("CC_PASSWORD")
        cookie = os.getenv("WEREAD_COOKIE")
        if url and id and password:
            cookie = self.try_get_cloud_cookie(url, id, password)
        if not cookie or not cookie.strip():
            raise Exception("没有找到cookie，请按照文档填写cookie")
        return cookie

    def parse_cookie_string(self):
        cookies_dict = {}
        
        # 使用正则表达式解析 cookie 字符串
        pattern = re.compile(r'([^=]+)=([^;]+);?\s*')
        matches = pattern.findall(self.cookie)
        
        for key, value in matches:
            cookies_dict[key] = value.encode('unicode_escape').decode('ascii')
        # 直接使用 cookies_dict 创建 cookiejar
        cookiejar = cookiejar_from_dict(cookies_dict)
        
        return cookiejar

    def get_bookshelf(self):
        if self.api_key:
            raise NotImplementedError("Gateway has no compatible bookshelf endpoint; use notebook-only book sync")
        self.session.get(WEREAD_URL)
        r = self.session.get(
            "https://i.weread.qq.com/shelf/sync?synckey=0&teenmode=0&album=1&onlyBookid=0"
        )
        if r.ok:
            return r.json()
        else:
            errcode = r.json().get("errcode",0)
            self.handle_errcode(errcode)
            raise Exception(f"Could not get bookshelf {r.text}")
        
    def handle_errcode(self,errcode):
        if( errcode== -2012 or errcode==-2010):
            print(f"::error::微信读书Cookie过期了，请参考文档重新设置。https://mp.weixin.qq.com/s/B_mqLUZv7M1rmXRsMlBf7A")

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def get_notebooklist(self):
        """获取笔记本列表"""
        if self.api_key:
            books, last_sort, seen = [], None, set()
            for _ in range(1000):
                params = {"count": 100}
                if last_sort is not None:
                    params["lastSort"] = last_sort
                data = self.gateway("/user/notebooks", **params)
                batch = data.get("books") or []
                books.extend(batch)
                if not data.get("hasMore"):
                    break
                if not batch:
                    raise RuntimeError("WeRead notebook pagination returned an empty batch")
                last_sort = batch[-1].get("sort")
                if last_sort in seen:
                    raise RuntimeError("WeRead notebook pagination did not advance")
                seen.add(last_sort)
            else:
                raise RuntimeError("WeRead notebook pagination exceeded limit")
            return sorted(books, key=lambda b: b.get("sort") or 0)
        self.session.get(WEREAD_URL)
        r = self.session.get(WEREAD_NOTEBOOKS_URL)
        if r.ok:
            data = r.json()
            books = data.get("books")
            books.sort(key=lambda x: x["sort"])
            return books
        else:
            errcode = r.json().get("errcode",0)
            self.handle_errcode(errcode)
            raise Exception(f"Could not get notebook list {r.text}")

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def get_bookinfo(self, bookId):
        """获取书的详情"""
        if self.api_key:
            return self.gateway("/book/info", bookId=bookId)
        self.session.get(WEREAD_URL)
        params = dict(bookId=bookId)
        r = self.session.get(WEREAD_BOOK_INFO, params=params)
        if r.ok:
            return r.json()
        else:
            errcode = r.json().get("errcode",0)
            self.handle_errcode(errcode)
            print(f"Could not get book info {r.text}")


    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def get_bookmark_list(self, bookId):
        if self.api_key:
            return self.gateway("/book/bookmarklist", bookId=bookId).get("updated") or []
        self.session.get(WEREAD_URL)
        params = dict(bookId=bookId)
        r = self.session.get(WEREAD_BOOKMARKLIST_URL, params=params)
        if r.ok:
            with open("bookmark.json","w") as f:
                f.write(json.dumps(r.json(),indent=4,ensure_ascii=False))
            bookmarks = r.json().get("updated")
            return bookmarks
        else:
            errcode = r.json().get("errcode",0)
            self.handle_errcode(errcode)
            raise Exception(f"Could not get {bookId} bookmark list")

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def get_read_info(self, bookId):
        if self.api_key:
            data = self.gateway("/book/getprogress", bookId=bookId)
            book = data.get("book") or {}
            progress = float(book.get("progress") or 0)
            if progress <= 1:
                progress *= 100
            progress = max(0, min(progress, 100))
            finished = book.get("finishTime") or 0
            marked_status = 4 if finished or progress >= 100 else (2 if progress > 0 or book.get("updateTime") else 1)
            return {
                "markedStatus": marked_status, "readingTime": book.get("recordReadingTime") or 0,
                "readingProgress": progress, "finishedDate": finished,
                "readDetail": {}, "bookInfo": {},
            }
        self.session.get(WEREAD_URL)
        params = dict(
            noteCount=1,
            readingDetail=1,
            finishedBookIndex=1,
            readingBookCount=1,
            readingBookIndex=1,
            finishedBookCount=1,
            bookId=bookId,
            finishedDate=1,
        )
        headers = {
            "baseapi":"32",
            "appver":"8.2.5.10163885",
            "basever":"8.2.5.10163885",
            "osver":"12",
            "User-Agent": "WeRead/8.2.5 WRBrand/xiaomi Dalvik/2.1.0 (Linux; U; Android 12; Redmi Note 7 Pro Build/SQ3A.220705.004)",
        }
        r = self.session.get(WEREAD_READ_INFO_URL,headers=headers, params=params)
        if r.ok:
            return r.json()
        else:
            errcode = r.json().get("errcode",0)
            self.handle_errcode(errcode)
            raise Exception(f"get {bookId} read info failed {r.text}")

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def get_review_list(self, bookId):
        if self.api_key:
            reviews, synckey, seen = [], 0, set()
            for _ in range(1000):
                data = self.gateway("/review/list/mine", bookid=bookId, synckey=synckey, count=100)
                batch = data.get("reviews") or []
                for wrapper in batch:
                    note = dict(wrapper.get("review") or {})
                    if not note or note.get("type") not in (1, 4):
                        continue
                    if note.get("type") == 4:
                        note["chapterUid"] = 1000000
                    reviews.append(note)
                if not data.get("hasMore"):
                    break
                new_key = data.get("synckey")
                if not batch or new_key is None or new_key in seen:
                    raise RuntimeError("WeRead review pagination did not advance")
                seen.add(new_key)
                synckey = new_key
            else:
                raise RuntimeError("WeRead review pagination exceeded limit")
            return reviews
        self.session.get(WEREAD_URL)
        params = dict(bookId=bookId, listType=11, mine=1, syncKey=0)
        r = self.session.get(WEREAD_REVIEW_LIST_URL, params=params)
        if r.ok:
            reviews = r.json().get("reviews")
            reviews = list(map(lambda x: x.get("review"), reviews))
            reviews = [
                {"chapterUid": 1000000, **x} if x.get("type") == 4 else x
                for x in reviews
            ]
            return reviews
        else:
            errcode = r.json().get("errcode",0)
            self.handle_errcode(errcode)
            raise Exception(f"get {bookId} review list failed {r.text}")



    
    def get_api_data(self):
        if self.api_key:
            raise NotImplementedError("Reading-time API not verified for gateway mode; disabled to protect existing records")
        self.session.get(WEREAD_URL)
        r = self.session.get(WEREAD_HISTORY_URL)
        if r.ok:
            return r.json()
        else:
            errcode = r.json().get("errcode",0)
            self.handle_errcode(errcode)
            raise Exception(f"get history data failed {r.text}")

    

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def get_chapter_info(self, bookId):
        if self.api_key:
            data = self.gateway("/book/chapterinfo", bookId=bookId)
            chapter = {item["chapterUid"]: item for item in (data.get("chapters") or []) if "chapterUid" in item}
            chapter[1000000] = {"chapterUid": 1000000, "chapterIdx": 1000000, "title": "点评", "level": 1}
            return chapter
        self.session.get(WEREAD_URL)
        body = {"bookIds": [bookId], "synckeys": [0], "teenmode": 0}
        r = self.session.post(WEREAD_CHAPTER_INFO, json=body)
        if (
            r.ok
            and "data" in r.json()
            and len(r.json()["data"]) == 1
            and "updated" in r.json()["data"][0]
        ):
            update = r.json()["data"][0]["updated"]
            update.append(
                {
                    "chapterUid": 1000000,
                    "chapterIdx": 1000000,
                    "updateTime": 1683825006,
                    "readAhead": 0,
                    "title": "点评",
                    "level": 1,
                }
            )
            return {item["chapterUid"]: item for item in update}
        else:
            raise Exception(f"get {bookId} chapter info failed {r.text}")

    def transform_id(self, book_id):
        id_length = len(book_id)
        if re.match("^\\d*$", book_id):
            ary = []
            for i in range(0, id_length, 9):
                ary.append(format(int(book_id[i : min(i + 9, id_length)]), "x"))
            return "3", ary

        result = ""
        for i in range(id_length):
            result += format(ord(book_id[i]), "x")
        return "4", [result]

    def calculate_book_str_id(self, book_id):
        md5 = hashlib.md5()
        md5.update(book_id.encode("utf-8"))
        digest = md5.hexdigest()
        result = digest[0:3]
        code, transformed_ids = self.transform_id(book_id)
        result += code + "2" + digest[-2:]

        for i in range(len(transformed_ids)):
            hex_length_str = format(len(transformed_ids[i]), "x")
            if len(hex_length_str) == 1:
                hex_length_str = "0" + hex_length_str

            result += hex_length_str + transformed_ids[i]

            if i < len(transformed_ids) - 1:
                result += "g"

        if len(result) < 20:
            result += digest[0 : 20 - len(result)]

        md5 = hashlib.md5()
        md5.update(result.encode("utf-8"))
        result += md5.hexdigest()[0:3]
        return result

    def get_url(self, book_id):
        return f"https://weread.qq.com/web/reader/{self.calculate_book_str_id(book_id)}"
