"""内容分析器"""

from models import PageData, Finding, Category, Severity


class ContentAnalyzer:
    def __init__(self, pages: dict[str, PageData], base_url: str):
        self.pages = pages
        self.base_url = base_url

    def analyze(self) -> list[Finding]:
        findings = []
        findings.extend(self._check_page_stats())
        findings.extend(self._check_dead_links())
        findings.extend(self._check_word_counts())
        findings.extend(self._check_link_graph())
        findings.extend(self._check_duplicate_titles())
        return findings

    def _check_page_stats(self) -> list[Finding]:
        total = len(self.pages)
        ok = sum(1 for p in self.pages.values() if p.status_code == 200)
        err = sum(1 for p in self.pages.values() if p.status_code >= 400)
        no_resp = sum(1 for p in self.pages.values() if p.status_code == 0)

        return [Finding(
            category=Category.CONTENT, severity=Severity.INFO,
            title="页面统计",
            description=f"共爬取 {total} 个页面：{ok} 个正常，{err} 个错误，{no_resp} 个无响应",
        )]

    def _check_dead_links(self) -> list[Finding]:
        findings = []
        dead_links = []

        for url, page in self.pages.items():
            if page.status_code == 404:
                dead_links.append(url)
            elif page.status_code >= 400:
                dead_links.append(f"{url} ({page.status_code})")

        if dead_links:
            desc_lines = [f"  - {link}" for link in dead_links[:10]]
            findings.append(Finding(
                category=Category.CONTENT, severity=Severity.ERROR,
                title=f"发现 {len(dead_links)} 个死链",
                description="\n".join(desc_lines),
                recommendation="修复或移除这些失效链接，设置 301 重定向",
            ))
        else:
            findings.append(Finding(
                category=Category.CONTENT, severity=Severity.GOOD,
                title="未发现死链",
                description="所有已爬取的内部链接都可正常访问",
            ))

        return findings

    def _check_word_counts(self) -> list[Finding]:
        findings = []
        thin_pages = []

        # 功能性页面路径，不需要大量文字内容
        functional_paths = (
            "/register", "/login", "/signup", "/signin",
            "/cart", "/checkout", "/account", "/profile",
            "/reset-password", "/forgot-password", "/verify",
            "/unsubscribe", "/settings", "/dashboard",
        )

        for url, page in self.pages.items():
            if page.status_code != 200:
                continue
            from urllib.parse import urlparse
            path = urlparse(url).path.rstrip("/").lower()
            if any(path == fp or path.endswith(fp) for fp in functional_paths):
                continue
            if page.word_count < 300 and page.word_count > 0:
                thin_pages.append((url, page.word_count))

        if thin_pages:
            thin_pages.sort(key=lambda x: x[1])
            desc_lines = [f"  - {url} ({count} 字)" for url, count in thin_pages[:10]]
            findings.append(Finding(
                category=Category.CONTENT, severity=Severity.WARNING,
                title=f"{len(thin_pages)} 个页面内容过少（<300 字）",
                description="\n".join(desc_lines),
                recommendation="丰富页面内容，确保为用户提供有价值的信息",
            ))

        # 统计平均字数
        word_counts = [p.word_count for p in self.pages.values() if p.status_code == 200 and p.word_count > 0]
        if word_counts:
            avg = sum(word_counts) / len(word_counts)
            findings.append(Finding(
                category=Category.CONTENT, severity=Severity.INFO,
                title="内容字数统计",
                description=f"平均 {avg:.0f} 字/页，最少 {min(word_counts)} 字，最多 {max(word_counts)} 字",
            ))

        return findings

    def _check_link_graph(self) -> list[Finding]:
        findings = []

        # 计算入链数
        inbound: dict[str, int] = {url: 0 for url in self.pages}
        for page in self.pages.values():
            if page.status_code != 200:
                continue
            for link in page.internal_links:
                if link in inbound:
                    inbound[link] += 1

        # 孤立页面（无入链，排除首页）
        orphans = [
            url for url, count in inbound.items()
            if count == 0 and url != self.base_url and self.pages[url].status_code == 200
        ]

        if orphans:
            desc_lines = [f"  - {url}" for url in orphans[:10]]
            findings.append(Finding(
                category=Category.CONTENT, severity=Severity.WARNING,
                title=f"{len(orphans)} 个孤立页面（无内部入链）",
                description="\n".join(desc_lines),
                recommendation="为这些页面添加内部链接，提升可发现性和 SEO",
            ))

        # 出链统计
        avg_internal = 0
        pages_200 = [p for p in self.pages.values() if p.status_code == 200]
        if pages_200:
            avg_internal = sum(len(p.internal_links) for p in pages_200) / len(pages_200)
            findings.append(Finding(
                category=Category.CONTENT, severity=Severity.INFO,
                title="内部链接统计",
                description=f"平均每页 {avg_internal:.0f} 个内部链接",
            ))

        return findings

    def _check_duplicate_titles(self) -> list[Finding]:
        title_pages: dict[str, list[str]] = {}
        for url, page in self.pages.items():
            if page.status_code == 200 and page.title:
                title_pages.setdefault(page.title, []).append(url)

        findings = []
        duplicates = {t: urls for t, urls in title_pages.items() if len(urls) > 1}
        if duplicates:
            desc_lines = []
            for title, urls in list(duplicates.items())[:5]:
                desc_lines.append(f"  '{title}' ({len(urls)} 个页面)")
            findings.append(Finding(
                category=Category.CONTENT, severity=Severity.WARNING,
                title=f"{len(duplicates)} 组重复标题",
                description="\n".join(desc_lines),
                recommendation="确保每个页面有唯一的标题",
            ))

        return findings
