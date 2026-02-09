"""DataForSEO API 集成模块

DataForSEO 提供专业的 SEO 数据分析：
- OnPage API: 页面级 SEO 审计、Core Web Vitals、技术 SEO 检查
- Backlinks API: 反向链接分析、引用域名、锚文本
- SERP API: 关键词排名追踪

认证方式: HTTP Basic Auth
Base URL: https://api.dataforseo.com/v3/
文档: https://docs.dataforseo.com/v3/
定价: 按量付费（Pay-As-You-Go），Sandbox 免费

使用方式:
    python main.py https://tenmomo.com --dataforseo-login YOUR_LOGIN --dataforseo-password YOUR_PASSWORD

环境变量:
    DATAFORSEO_LOGIN=your_login
    DATAFORSEO_PASSWORD=your_password
"""

import json
import requests
from models import Finding, Category, Severity


class DataForSEOClient:
    """DataForSEO API 客户端"""

    BASE_URL = "https://api.dataforseo.com/v3"

    def __init__(self, login: str, password: str, sandbox: bool = False):
        self.auth = (login, password)
        if sandbox:
            self.BASE_URL = "https://sandbox.dataforseo.com/v3"
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            "Content-Type": "application/json",
        })

    def _post(self, endpoint: str, data: list[dict]) -> dict:
        """发送 POST 请求"""
        url = f"{self.BASE_URL}{endpoint}"
        resp = self.session.post(url, json=data, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def _get(self, endpoint: str) -> dict:
        """发送 GET 请求"""
        url = f"{self.BASE_URL}{endpoint}"
        resp = self.session.get(url, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def instant_pages(self, url: str) -> dict | None:
        """实时单页分析 - 返回 onpage_score、Core Web Vitals、SEO 检查项

        文档: https://docs.dataforseo.com/v3/on_page-instant_pages/
        费用: 按爬取页面数 + 参数附加费
        速率限制: 2000 请求/分钟，30 并发

        返回结构: result[0].items[0] 包含页面级数据
        """
        data = [{
            "url": url,
            "enable_javascript": True,
            "load_resources": True,
            "check_spell": True,
            "validate_micromarkup": True,
        }]
        try:
            resp = self._post("/on_page/instant_pages", data)
            if resp.get("status_code") == 20000 and resp.get("tasks"):
                task = resp["tasks"][0]
                if task.get("status_code") == 20000 and task.get("result"):
                    result = task["result"][0]
                    # 实际页面数据在 items 数组中
                    items = result.get("items", [])
                    if items:
                        return items[0]
                    return result
        except Exception as e:
            print(f"  ⚠️ DataForSEO instant_pages 失败: {e}")
        return None

    def backlinks_summary(self, target: str) -> dict | None:
        """反向链接概况

        文档: https://docs.dataforseo.com/v3/backlinks-overview/
        费用: $0.02/请求 + $0.00003/每行数据
        注意: Backlinks API 有 $100/月最低消费（Make.com/n8n 除外）
        """
        data = [{
            "target": target,
            "exclude_internal_backlinks": True,
        }]
        try:
            resp = self._post("/backlinks/summary/live", data)
            if resp.get("status_code") == 20000 and resp.get("tasks"):
                task = resp["tasks"][0]
                if task.get("status_code") == 20000 and task.get("result"):
                    return task["result"][0] if isinstance(task["result"], list) else task["result"]
                elif task.get("status_code") == 40204:
                    print(f"  ⚠️ Backlinks API 未开通（需要订阅）")
                    return None
        except Exception as e:
            print(f"  ⚠️ DataForSEO backlinks_summary 失败: {e}")
        return None


class DataForSEOAnalyzer:
    """利用 DataForSEO API 进行深度分析"""

    def __init__(self, client: DataForSEOClient, target_url: str):
        self.client = client
        self.target_url = target_url
        # 从 URL 提取域名
        from urllib.parse import urlparse
        self.domain = urlparse(target_url).netloc

    def analyze(self) -> list[Finding]:
        findings = []

        # 1. 页面级分析
        print("  📡 DataForSEO: 分析首页...")
        page_data = self.client.instant_pages(self.target_url)
        if page_data:
            findings.extend(self._parse_instant_pages(page_data))
        else:
            findings.append(Finding(
                category=Category.SEO, severity=Severity.INFO,
                title="DataForSEO 页面分析不可用",
                description="无法通过 DataForSEO API 获取页面数据",
            ))

        # 2. 反链分析
        print("  📡 DataForSEO: 分析反向链接...")
        backlinks = self.client.backlinks_summary(self.domain)
        if backlinks:
            findings.extend(self._parse_backlinks(backlinks))

        return findings

    def _parse_instant_pages(self, data: dict) -> list[Finding]:
        findings = []

        # OnPage 评分
        onpage_score = data.get("onpage_score")
        if onpage_score is not None:
            if onpage_score >= 80:
                severity = Severity.GOOD
            elif onpage_score >= 60:
                severity = Severity.WARNING
            else:
                severity = Severity.ERROR
            findings.append(Finding(
                category=Category.SEO, severity=severity,
                title=f"[DataForSEO] OnPage 评分: {onpage_score:.1f}/100",
                description="基于 DataForSEO 专业评估的页面优化得分",
                url=self.target_url,
            ))

        # 检查项（true = 问题存在）
        checks = data.get("checks", {})
        # 这些 check 的 true 表示有问题
        problem_checks = {
            "no_title": ("缺少 title 标签", Severity.ERROR, Category.SEO),
            "no_description": ("缺少 meta description", Severity.WARNING, Category.SEO),
            "no_h1_tag": ("缺少 H1 标签", Severity.ERROR, Category.SEO),
            "has_meta_refresh_redirect": ("使用了 meta refresh 重定向", Severity.WARNING, Category.SEO),
            "is_broken": ("页面已损坏", Severity.ERROR, Category.CONTENT),
            "no_image_alt": ("图片缺少 alt 属性", Severity.WARNING, Category.SEO),
            "no_image_title": ("图片缺少 title 属性", Severity.INFO, Category.SEO),
            "no_favicon": ("缺少 favicon", Severity.WARNING, Category.SEO),
            "no_content_encoding": ("未启用内容压缩", Severity.WARNING, Category.PERFORMANCE),
            "high_loading_time": ("页面加载时间过长", Severity.ERROR, Category.PERFORMANCE),
            "is_http": ("使用 HTTP 而非 HTTPS", Severity.ERROR, Category.SECURITY),
            "low_content_rate": ("内容占比过低（纯文本占比低）", Severity.WARNING, Category.CONTENT),
            "high_waiting_time": ("服务器等待时间过长", Severity.WARNING, Category.PERFORMANCE),
            "no_doctype": ("缺少 DOCTYPE 声明", Severity.WARNING, Category.SEO),
            "title_too_short": ("title 标签过短", Severity.WARNING, Category.SEO),
            "title_too_long": ("title 标签过长", Severity.WARNING, Category.SEO),
            "has_render_blocking_resources": ("存在渲染阻塞资源", Severity.WARNING, Category.PERFORMANCE),
            "https_to_http_links": ("HTTPS 页面包含 HTTP 链接", Severity.ERROR, Category.SECURITY),
            "size_greater_than_3mb": ("页面大于 3MB", Severity.ERROR, Category.PERFORMANCE),
            "duplicate_title_tag": ("重复的 title 标签", Severity.WARNING, Category.SEO),
            "duplicate_meta_tags": ("重复的 meta 标签", Severity.WARNING, Category.SEO),
            "deprecated_html_tags": ("使用了已废弃的 HTML 标签", Severity.WARNING, Category.SEO),
        }

        for check_name, is_flagged in checks.items():
            if is_flagged and check_name in problem_checks:
                desc, sev, cat = problem_checks[check_name]
                findings.append(Finding(
                    category=cat, severity=sev,
                    title=f"[DataForSEO] {desc}",
                    description=f"DataForSEO 检测到: {check_name}",
                    url=self.target_url,
                ))

        # 页面元数据摘要
        meta = data.get("meta", {})
        if meta:
            title = meta.get("title", "")
            desc_len = meta.get("description_length", 0)
            content_info = meta.get("content", {})
            details = []
            if title:
                details.append(f"title: '{title}' ({meta.get('title_length', 0)} 字符)")
            details.append(f"meta description: {desc_len} 字符")
            if content_info:
                details.append(f"纯文本: {content_info.get('plain_text_word_count', 0)} 词")
                details.append(f"可读性 (Flesch): {content_info.get('flesch_kincaid_readability_index', 0):.1f}")
                details.append(f"内容占比: {content_info.get('plain_text_rate', 0) * 100:.1f}%")
            social = meta.get("social_media_tags", {})
            if social:
                details.append(f"OG 标签: {len(social)} 个")
            findings.append(Finding(
                category=Category.SEO, severity=Severity.INFO,
                title="[DataForSEO] 页面元数据摘要",
                description="\n".join(f"  {d}" for d in details),
                url=self.target_url,
            ))

        # Core Web Vitals / 页面性能
        page_timing = data.get("page_timing", {})
        if page_timing:
            time_to_interactive = page_timing.get("time_to_interactive")
            if time_to_interactive:
                tti_sec = time_to_interactive / 1000
                if tti_sec > 5:
                    severity = Severity.ERROR
                elif tti_sec > 3:
                    severity = Severity.WARNING
                else:
                    severity = Severity.GOOD
                findings.append(Finding(
                    category=Category.PERFORMANCE, severity=severity,
                    title=f"[DataForSEO] Time to Interactive: {tti_sec:.2f}s",
                    description="页面可交互所需时间（<3s 良好，>5s 需优化）",
                    url=self.target_url,
                ))

            dom_complete = page_timing.get("dom_complete")
            if dom_complete:
                dom_sec = dom_complete / 1000
                if dom_sec > 5:
                    severity = Severity.ERROR
                elif dom_sec > 3:
                    severity = Severity.WARNING
                else:
                    severity = Severity.GOOD
                findings.append(Finding(
                    category=Category.PERFORMANCE, severity=severity,
                    title=f"[DataForSEO] DOM Complete: {dom_sec:.2f}s",
                    description="DOM 加载完成时间",
                    url=self.target_url,
                ))

            # 页面总大小
            total_size = data.get("total_dom_size", 0)
            encoded_size = data.get("encoded_size", 0)
            if total_size:
                findings.append(Finding(
                    category=Category.PERFORMANCE, severity=Severity.INFO,
                    title=f"[DataForSEO] 页面大小: {total_size / 1024:.1f}KB (压缩后 {encoded_size / 1024:.1f}KB)",
                    description=f"压缩编码: {data.get('content_encoding', 'none')}",
                    url=self.target_url,
                ))

        return findings

    def _parse_backlinks(self, data: dict) -> list[Finding]:
        findings = []

        total_backlinks = data.get("backlinks", 0)
        referring_domains = data.get("referring_domains", 0)
        rank = data.get("rank", 0)
        broken_backlinks = data.get("broken_backlinks", 0)

        # 总反链数
        if total_backlinks > 100:
            severity = Severity.GOOD
        elif total_backlinks > 10:
            severity = Severity.WARNING
        else:
            severity = Severity.ERROR
        findings.append(Finding(
            category=Category.SEO, severity=severity,
            title=f"[DataForSEO] 总反向链接数: {total_backlinks}",
            description=f"引用域名: {referring_domains}, Domain Rank: {rank}",
            recommendation="通过优质内容营销和外链建设增加高质量反链" if total_backlinks < 100 else "",
        ))

        # 坏链
        if broken_backlinks > 0:
            findings.append(Finding(
                category=Category.CONTENT, severity=Severity.WARNING,
                title=f"[DataForSEO] 发现 {broken_backlinks} 个失效反向链接",
                description="部分指向本站的外部链接已失效",
                recommendation="联系链接来源更新 URL 或设置 301 重定向",
            ))

        return findings
