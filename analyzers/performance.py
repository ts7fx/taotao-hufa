"""性能分析器"""

from models import PageData, Finding, Category, Severity
from utils import format_bytes


class PerformanceAnalyzer:
    def __init__(self, pages: dict[str, PageData], base_url: str):
        self.pages = pages
        self.base_url = base_url

    def analyze(self) -> list[Finding]:
        findings = []
        findings.extend(self._check_response_times())
        findings.extend(self._check_page_sizes())
        findings.extend(self._check_resource_counts())
        findings.extend(self._check_image_formats())
        findings.extend(self._check_compression())
        findings.extend(self._check_http2())
        return findings

    def _check_response_times(self) -> list[Finding]:
        findings = []
        slow_pages = []
        very_slow_pages = []

        for url, page in self.pages.items():
            if page.status_code != 200:
                continue
            if page.response_time > 3.0:
                very_slow_pages.append((url, page.response_time))
            elif page.response_time > 1.0:
                slow_pages.append((url, page.response_time))

        if very_slow_pages:
            desc_lines = [f"  - {url} ({t:.1f}s)" for url, t in very_slow_pages[:5]]
            findings.append(Finding(
                category=Category.PERFORMANCE, severity=Severity.ERROR,
                title=f"{len(very_slow_pages)} 个页面响应极慢（>3s）",
                description="\n".join(desc_lines),
                recommendation="检查服务器性能、启用缓存、优化数据库查询",
            ))

        if slow_pages:
            desc_lines = [f"  - {url} ({t:.1f}s)" for url, t in slow_pages[:5]]
            findings.append(Finding(
                category=Category.PERFORMANCE, severity=Severity.WARNING,
                title=f"{len(slow_pages)} 个页面响应较慢（1-3s）",
                description="\n".join(desc_lines),
                recommendation="考虑使用 CDN、页面缓存或优化服务端渲染",
            ))

        fast_count = sum(
            1 for p in self.pages.values()
            if p.status_code == 200 and p.response_time <= 1.0
        )
        if fast_count > 0:
            findings.append(Finding(
                category=Category.PERFORMANCE, severity=Severity.GOOD,
                title=f"{fast_count} 个页面响应良好（<1s）",
                description="这些页面的响应时间在可接受范围内",
            ))

        return findings

    def _check_page_sizes(self) -> list[Finding]:
        findings = []
        large_pages = []

        for url, page in self.pages.items():
            if page.status_code != 200:
                continue
            if page.content_length > 100 * 1024:
                large_pages.append((url, page.content_length))

        if large_pages:
            large_pages.sort(key=lambda x: x[1], reverse=True)
            desc_lines = [f"  - {url} ({format_bytes(size)})" for url, size in large_pages[:5]]
            severity = Severity.ERROR if large_pages[0][1] > 500 * 1024 else Severity.WARNING
            findings.append(Finding(
                category=Category.PERFORMANCE, severity=severity,
                title=f"{len(large_pages)} 个页面 HTML 过大（>100KB）",
                description="\n".join(desc_lines),
                recommendation="压缩 HTML、移除内联 CSS/JS、启用服务端压缩",
            ))
        else:
            findings.append(Finding(
                category=Category.PERFORMANCE, severity=Severity.GOOD,
                title="页面大小合理",
                description="所有页面 HTML 大小均在 100KB 以内",
            ))

        return findings

    def _check_resource_counts(self) -> list[Finding]:
        findings = []
        for url, page in self.pages.items():
            if page.status_code != 200:
                continue
            total = len(page.scripts) + len(page.stylesheets) + len(page.images)
            if total > 50:
                findings.append(Finding(
                    category=Category.PERFORMANCE, severity=Severity.WARNING,
                    title="资源请求过多",
                    description=f"JS: {len(page.scripts)}, CSS: {len(page.stylesheets)}, 图片: {len(page.images)}（共 {total} 个）",
                    recommendation="合并 CSS/JS 文件，使用雪碧图或 SVG，启用懒加载",
                    url=url,
                ))
        return findings

    def _check_image_formats(self) -> list[Finding]:
        png_count = 0
        jpg_count = 0
        webp_count = 0

        for page in self.pages.values():
            if page.status_code != 200:
                continue
            for img in page.images:
                src = img.get("src", "").lower()
                if src.endswith(".png"):
                    png_count += 1
                elif src.endswith((".jpg", ".jpeg")):
                    jpg_count += 1
                elif src.endswith(".webp"):
                    webp_count += 1

        findings = []
        if png_count + jpg_count > 0 and webp_count == 0:
            findings.append(Finding(
                category=Category.PERFORMANCE, severity=Severity.WARNING,
                title="未使用 WebP 图片格式",
                description=f"发现 {png_count} 个 PNG、{jpg_count} 个 JPG，但没有 WebP",
                recommendation="将图片转换为 WebP 格式可减少 25-35% 文件大小",
            ))
        elif webp_count > 0:
            findings.append(Finding(
                category=Category.PERFORMANCE, severity=Severity.GOOD,
                title="使用了 WebP 图片格式",
                description=f"WebP: {webp_count}, PNG: {png_count}, JPG: {jpg_count}",
            ))

        return findings

    def _check_compression(self) -> list[Finding]:
        # 检查首页的压缩
        home = self.pages.get(self.base_url)
        if not home or home.status_code != 200:
            return []

        encoding = home.headers.get("Content-Encoding", "").lower()
        if "br" in encoding:
            return [Finding(
                category=Category.PERFORMANCE, severity=Severity.GOOD,
                title="启用了 Brotli 压缩",
                description="服务器使用 Brotli 压缩（最优）",
            )]
        elif "gzip" in encoding:
            return [Finding(
                category=Category.PERFORMANCE, severity=Severity.GOOD,
                title="启用了 Gzip 压缩",
                description="服务器使用 Gzip 压缩",
                recommendation="考虑升级到 Brotli 以获得更好的压缩率",
            )]
        else:
            return [Finding(
                category=Category.PERFORMANCE, severity=Severity.ERROR,
                title="未启用响应压缩",
                description="服务器未返回 Content-Encoding 头",
                recommendation="启用 Gzip 或 Brotli 压缩，可减少 60-80% 传输大小",
            )]

    def _check_http2(self) -> list[Finding]:
        # 注意：requests 库默认使用 HTTP/1.1，无法直接检测 HTTP/2
        # 这里通过 alt-svc 头或其他线索判断
        home = self.pages.get(self.base_url)
        if not home or home.status_code != 200:
            return []

        alt_svc = home.headers.get("alt-svc", "")
        if "h2" in alt_svc or "h3" in alt_svc:
            return [Finding(
                category=Category.PERFORMANCE, severity=Severity.GOOD,
                title="支持 HTTP/2 或 HTTP/3",
                description=f"Alt-Svc: {alt_svc[:100]}",
            )]

        return [Finding(
            category=Category.PERFORMANCE, severity=Severity.INFO,
            title="HTTP/2 支持未确认",
            description="无法通过 HTTP/1.1 请求确认 HTTP/2 支持",
            recommendation="确保服务器或 CDN 支持 HTTP/2 以提升并发加载速度",
        )]
