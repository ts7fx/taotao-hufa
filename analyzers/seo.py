"""SEO 分析器"""

import requests
from models import PageData, Finding, Category, Severity


class SEOAnalyzer:
    def __init__(self, pages: dict[str, PageData], base_url: str):
        self.pages = pages
        self.base_url = base_url

    def analyze(self) -> list[Finding]:
        findings = []
        findings.extend(self._check_titles())
        findings.extend(self._check_meta_descriptions())
        findings.extend(self._check_h_tags())
        findings.extend(self._check_images_alt())
        findings.extend(self._check_canonical())
        findings.extend(self._check_og_tags())
        findings.extend(self._check_json_ld())
        findings.extend(self._check_robots_sitemap())
        findings.extend(self._check_duplicate_titles())
        return findings

    def _check_titles(self) -> list[Finding]:
        findings = []
        for url, page in self.pages.items():
            if page.status_code != 200:
                continue
            if not page.title:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.ERROR,
                    title="缺少 title 标签",
                    description=f"页面缺少 title 标签",
                    recommendation="每个页面都应有唯一、描述性的 title（10-60 字符）",
                    url=url,
                ))
            elif len(page.title) < 10:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.WARNING,
                    title="title 过短",
                    description=f"title 只有 {len(page.title)} 字符: '{page.title}'",
                    recommendation="建议 title 长度在 10-60 字符之间",
                    url=url,
                ))
            elif len(page.title) > 60:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.WARNING,
                    title="title 过长",
                    description=f"title 有 {len(page.title)} 字符，搜索结果中可能被截断",
                    recommendation="建议 title 长度在 10-60 字符之间",
                    url=url,
                ))
            else:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.GOOD,
                    title="title 长度合适",
                    description=f"'{page.title}' ({len(page.title)} 字符)",
                    url=url,
                ))
        return findings

    def _check_meta_descriptions(self) -> list[Finding]:
        findings = []
        for url, page in self.pages.items():
            if page.status_code != 200:
                continue
            if not page.meta_description:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.WARNING,
                    title="缺少 meta description",
                    description="页面没有 meta description",
                    recommendation="添加 50-160 字符的描述，包含关键词",
                    url=url,
                ))
            elif len(page.meta_description) < 50:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.WARNING,
                    title="meta description 过短",
                    description=f"只有 {len(page.meta_description)} 字符",
                    recommendation="建议 50-160 字符",
                    url=url,
                ))
            elif len(page.meta_description) > 160:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.WARNING,
                    title="meta description 过长",
                    description=f"{len(page.meta_description)} 字符，搜索结果中会被截断",
                    recommendation="建议 50-160 字符",
                    url=url,
                ))
        return findings

    def _check_h_tags(self) -> list[Finding]:
        findings = []
        for url, page in self.pages.items():
            if page.status_code != 200:
                continue
            if len(page.h1_tags) == 0:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.ERROR,
                    title="缺少 H1 标签",
                    description="页面没有 H1 标题",
                    recommendation="每个页面应有且仅有一个 H1",
                    url=url,
                ))
            elif len(page.h1_tags) > 1:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.WARNING,
                    title="多个 H1 标签",
                    description=f"页面有 {len(page.h1_tags)} 个 H1: {page.h1_tags}",
                    recommendation="每个页面只保留一个 H1",
                    url=url,
                ))
        return findings

    def _check_images_alt(self) -> list[Finding]:
        total_images = 0
        missing_alt = 0
        for page in self.pages.values():
            if page.status_code != 200:
                continue
            for img in page.images:
                total_images += 1
                if not img.get("alt", "").strip():
                    missing_alt += 1

        if total_images == 0:
            return []

        ratio = (total_images - missing_alt) / total_images * 100
        if missing_alt > 0:
            severity = Severity.ERROR if ratio < 50 else Severity.WARNING
            return [Finding(
                category=Category.SEO, severity=severity,
                title="图片缺少 alt 属性",
                description=f"{missing_alt}/{total_images} 张图片缺少 alt 属性（覆盖率 {ratio:.0f}%）",
                recommendation="为所有图片添加描述性的 alt 文本",
            )]
        return [Finding(
            category=Category.SEO, severity=Severity.GOOD,
            title="图片 alt 属性完整",
            description=f"所有 {total_images} 张图片都有 alt 属性",
        )]

    def _check_canonical(self) -> list[Finding]:
        findings = []
        for url, page in self.pages.items():
            if page.status_code != 200:
                continue
            if not page.canonical_url:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.WARNING,
                    title="缺少 canonical URL",
                    description="页面没有设置 canonical URL",
                    recommendation="设置 canonical URL 避免重复内容问题",
                    url=url,
                ))
        return findings

    def _check_og_tags(self) -> list[Finding]:
        findings = []
        # 只检查首页的 OG 标签
        home = self.pages.get(self.base_url)
        if not home or home.status_code != 200:
            return findings

        required_og = ["og:title", "og:description", "og:image", "og:url"]
        missing = [tag for tag in required_og if tag not in home.og_tags]
        if missing:
            findings.append(Finding(
                category=Category.SEO, severity=Severity.WARNING,
                title="Open Graph 标签不完整",
                description=f"首页缺少: {', '.join(missing)}",
                recommendation="添加完整的 OG 标签以优化社交媒体分享",
                url=self.base_url,
            ))
        else:
            findings.append(Finding(
                category=Category.SEO, severity=Severity.GOOD,
                title="Open Graph 标签完整",
                description="首页包含所有必要的 OG 标签",
                url=self.base_url,
            ))
        return findings

    def _check_json_ld(self) -> list[Finding]:
        has_json_ld = any(page.json_ld for page in self.pages.values() if page.status_code == 200)
        if has_json_ld:
            return [Finding(
                category=Category.SEO, severity=Severity.GOOD,
                title="使用了 JSON-LD 结构化数据",
                description="网站包含 JSON-LD 结构化数据，有助于富摘要展示",
            )]
        return [Finding(
            category=Category.SEO, severity=Severity.WARNING,
            title="缺少 JSON-LD 结构化数据",
            description="未发现 JSON-LD 数据",
            recommendation="添加 Article/Product/Organization 等 JSON-LD 标记",
        )]

    def _check_robots_sitemap(self) -> list[Finding]:
        findings = []
        # 检查 robots.txt
        try:
            resp = requests.get(f"{self.base_url}/robots.txt", timeout=10,
                                headers={"User-Agent": "TaoTaoHuFa/1.0"})
            if resp.status_code == 200:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.GOOD,
                    title="robots.txt 存在",
                    description="网站有 robots.txt 文件",
                ))
            else:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.WARNING,
                    title="robots.txt 缺失",
                    description=f"robots.txt 返回 {resp.status_code}",
                    recommendation="创建 robots.txt 文件指导搜索引擎爬取",
                ))
        except Exception:
            findings.append(Finding(
                category=Category.SEO, severity=Severity.WARNING,
                title="robots.txt 不可访问",
                description="无法获取 robots.txt",
            ))

        # 检查 sitemap.xml
        try:
            resp = requests.get(f"{self.base_url}/sitemap.xml", timeout=10,
                                headers={"User-Agent": "TaoTaoHuFa/1.0"})
            if resp.status_code == 200:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.GOOD,
                    title="sitemap.xml 存在",
                    description="网站有 sitemap.xml",
                ))
            else:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.ERROR,
                    title="sitemap.xml 缺失",
                    description=f"sitemap.xml 返回 {resp.status_code}",
                    recommendation="创建 sitemap.xml 帮助搜索引擎发现所有页面",
                ))
        except Exception:
            findings.append(Finding(
                category=Category.SEO, severity=Severity.ERROR,
                title="sitemap.xml 不可访问",
                description="无法获取 sitemap.xml",
                recommendation="创建并提交 sitemap.xml",
            ))

        return findings

    def _check_duplicate_titles(self) -> list[Finding]:
        title_pages: dict[str, list[str]] = {}
        for url, page in self.pages.items():
            if page.status_code == 200 and page.title:
                title_pages.setdefault(page.title, []).append(url)

        findings = []
        for title, urls in title_pages.items():
            if len(urls) > 1:
                findings.append(Finding(
                    category=Category.SEO, severity=Severity.ERROR,
                    title="重复标题",
                    description=f"'{title}' 在 {len(urls)} 个页面中重复使用",
                    recommendation="每个页面使用唯一的 title",
                ))
        return findings
