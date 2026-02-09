"""爬虫核心：BFS 爬取、链接发现、速率控制"""

import time
import re
from collections import deque
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from models import PageData
from utils import normalize_url, is_same_domain, is_crawlable_url


class Crawler:
    USER_AGENT = "TaoTaoHuFa/1.0"

    def __init__(self, base_url: str, max_pages: int = 50, delay: float = 1.0):
        self.base_url = base_url.rstrip("/")
        self.max_pages = max_pages
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
        })
        self.visited: set[str] = set()
        self.pages: dict[str, PageData] = {}
        self.robots_parser = self._load_robots()

    def _load_robots(self) -> RobotFileParser:
        """加载 robots.txt"""
        rp = RobotFileParser()
        robots_url = f"{self.base_url}/robots.txt"
        try:
            rp.set_url(robots_url)
            rp.read()
            print(f"  ✓ robots.txt 已加载")
        except Exception:
            print(f"  ✗ robots.txt 加载失败，将爬取所有页面")
        return rp

    def _can_fetch(self, url: str) -> bool:
        """检查 robots.txt 是否允许爬取"""
        try:
            return self.robots_parser.can_fetch(self.USER_AGENT, url)
        except Exception:
            return True

    def _fetch_page(self, url: str) -> PageData:
        """抓取单个页面"""
        page = PageData(url=url)
        try:
            start = time.time()
            resp = self.session.get(url, timeout=15, allow_redirects=True)
            page.response_time = time.time() - start
            page.status_code = resp.status_code
            page.content_type = resp.headers.get("Content-Type", "")
            page.headers = dict(resp.headers)
            page.content_length = len(resp.content)

            if "text/html" not in page.content_type:
                return page

            page.html = resp.text
            self._parse_html(page)

        except requests.RequestException as e:
            page.error = str(e)
            page.status_code = 0

        return page

    def _parse_html(self, page: PageData):
        """解析 HTML，提取结构化数据"""
        soup = BeautifulSoup(page.html, "html.parser")

        # title
        title_tag = soup.find("title")
        page.title = title_tag.get_text(strip=True) if title_tag else ""

        # meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            page.meta_description = meta_desc.get("content", "")

        # H 标签
        page.h1_tags = [h.get_text(strip=True) for h in soup.find_all("h1")]
        page.h2_tags = [h.get_text(strip=True) for h in soup.find_all("h2")]
        page.h3_tags = [h.get_text(strip=True) for h in soup.find_all("h3")]

        # 图片（识别 <picture> + <source type="image/webp"> 的标准写法）
        for img in soup.find_all("img"):
            has_webp_source = False
            parent = img.parent
            if parent and parent.name == "picture":
                for source in parent.find_all("source"):
                    stype = (source.get("type") or "").lower()
                    srcset = (source.get("srcset") or "").lower()
                    if "webp" in stype or srcset.endswith(".webp"):
                        has_webp_source = True
                        break
            page.images.append({
                "src": img.get("src", ""),
                "alt": img.get("alt", ""),
                "has_webp_source": has_webp_source,
            })

        # 链接
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            full_url = normalize_url(href, page.url)
            if is_same_domain(full_url, self.base_url):
                page.internal_links.append(full_url)
            else:
                page.external_links.append(full_url)

        # canonical
        canonical = soup.find("link", rel="canonical")
        if canonical:
            page.canonical_url = canonical.get("href", "")

        # Open Graph
        for og in soup.find_all("meta", property=re.compile(r"^og:")):
            page.og_tags[og["property"]] = og.get("content", "")

        # JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    page.json_ld.extend(data)
                else:
                    page.json_ld.append(data)
            except (json.JSONDecodeError, TypeError):
                pass

        # 资源统计
        page.scripts = [s.get("src", "") for s in soup.find_all("script", src=True)]
        page.stylesheets = [
            l.get("href", "") for l in soup.find_all("link", rel="stylesheet")
        ]

        # 字数（纯文本内容）
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # 中文按字符算，英文按单词算
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        page.word_count = chinese_chars + english_words

    def crawl(self) -> dict[str, PageData]:
        """BFS 广度优先爬取"""
        print(f"\n🕷️ 桃桃护法 - 开始爬取 {self.base_url}")
        print(f"  最大页面数: {self.max_pages}, 请求间隔: {self.delay}s\n")

        queue = deque([self.base_url])
        self.visited.add(self.base_url)

        while queue and len(self.pages) < self.max_pages:
            url = queue.popleft()

            if not self._can_fetch(url):
                print(f"  [跳过] robots.txt 禁止: {url}")
                continue

            print(f"  [{len(self.pages) + 1}/{self.max_pages}] {url}", end=" ")
            page = self._fetch_page(url)
            self.pages[url] = page

            if page.error:
                print(f"❌ 错误: {page.error}")
            elif page.status_code != 200:
                print(f"⚠️ {page.status_code}")
            else:
                print(f"✅ {page.response_time:.1f}s {page.word_count}字")

            # 发现新链接加入队列
            for link in page.internal_links:
                if (link not in self.visited
                        and is_crawlable_url(link)
                        and len(self.visited) < self.max_pages * 2):
                    self.visited.add(link)
                    queue.append(link)

            if queue and len(self.pages) < self.max_pages:
                time.sleep(self.delay)

        print(f"\n✅ 爬取完成，共 {len(self.pages)} 个页面\n")
        return self.pages
