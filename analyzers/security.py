"""安全分析器"""

import re
from urllib.parse import urlparse
from models import PageData, Finding, Category, Severity


class SecurityAnalyzer:
    def __init__(self, pages: dict[str, PageData], base_url: str):
        self.pages = pages
        self.base_url = base_url

    def analyze(self) -> list[Finding]:
        findings = []
        findings.extend(self._check_https())
        findings.extend(self._check_security_headers())
        findings.extend(self._check_mixed_content())
        findings.extend(self._check_cookies())
        findings.extend(self._check_info_leak())
        return findings

    def _check_https(self) -> list[Finding]:
        parsed = urlparse(self.base_url)
        if parsed.scheme == "https":
            return [Finding(
                category=Category.SECURITY, severity=Severity.GOOD,
                title="使用 HTTPS",
                description="网站通过 HTTPS 安全连接提供服务",
            )]
        return [Finding(
            category=Category.SECURITY, severity=Severity.ERROR,
            title="未使用 HTTPS",
            description="网站未启用 HTTPS 加密",
            recommendation="尽快迁移到 HTTPS，可使用 Let's Encrypt 免费证书",
        )]

    def _check_security_headers(self) -> list[Finding]:
        home = self.pages.get(self.base_url)
        if not home or home.status_code != 200:
            return []

        findings = []
        headers = {k.lower(): v for k, v in home.headers.items()}

        checks = [
            ("strict-transport-security", "HSTS",
             "启用 HSTS 强制浏览器使用 HTTPS",
             "添加 Strict-Transport-Security: max-age=31536000; includeSubDomains"),
            ("content-security-policy", "CSP（内容安全策略）",
             "CSP 可防止 XSS 和数据注入攻击",
             "配置 Content-Security-Policy 头限制资源加载来源"),
            ("x-frame-options", "X-Frame-Options",
             "防止页面被嵌入 iframe（点击劫持防护）",
             "添加 X-Frame-Options: DENY 或 SAMEORIGIN"),
            ("x-content-type-options", "X-Content-Type-Options",
             "防止浏览器 MIME 类型嗅探",
             "添加 X-Content-Type-Options: nosniff"),
            ("referrer-policy", "Referrer-Policy",
             "控制请求中的 Referer 信息泄露",
             "添加 Referrer-Policy: strict-origin-when-cross-origin"),
        ]

        for header, name, desc_present, recommendation in checks:
            if header in headers:
                findings.append(Finding(
                    category=Category.SECURITY, severity=Severity.GOOD,
                    title=f"已设置 {name}",
                    description=f"{name}: {headers[header][:100]}",
                ))
            else:
                findings.append(Finding(
                    category=Category.SECURITY, severity=Severity.ERROR,
                    title=f"缺少 {name}",
                    description=desc_present,
                    recommendation=recommendation,
                ))

        return findings

    def _check_mixed_content(self) -> list[Finding]:
        if not self.base_url.startswith("https://"):
            return []

        mixed_pages = []
        for url, page in self.pages.items():
            if page.status_code != 200 or not page.html:
                continue
            # 检查 HTML 中的 http:// 资源引用
            http_refs = re.findall(
                r'(?:src|href|action)\s*=\s*["\']http://[^"\']+["\']',
                page.html, re.IGNORECASE
            )
            if http_refs:
                mixed_pages.append((url, len(http_refs)))

        if mixed_pages:
            desc_lines = [f"  - {url} ({count} 处)" for url, count in mixed_pages[:5]]
            return [Finding(
                category=Category.SECURITY, severity=Severity.ERROR,
                title=f"{len(mixed_pages)} 个页面存在混合内容",
                description="HTTPS 页面中加载了 HTTP 资源:\n" + "\n".join(desc_lines),
                recommendation="将所有资源引用改为 HTTPS 或使用协议相对 URL",
            )]

        return [Finding(
            category=Category.SECURITY, severity=Severity.GOOD,
            title="无混合内容",
            description="所有 HTTPS 页面未加载 HTTP 资源",
        )]

    def _check_cookies(self) -> list[Finding]:
        home = self.pages.get(self.base_url)
        if not home or home.status_code != 200:
            return []

        set_cookie = home.headers.get("Set-Cookie", "")
        if not set_cookie:
            return [Finding(
                category=Category.SECURITY, severity=Severity.INFO,
                title="首页未设置 Cookie",
                description="首页响应中未发现 Set-Cookie 头",
            )]

        findings = []
        cookies_str = set_cookie.lower()

        if "secure" not in cookies_str:
            findings.append(Finding(
                category=Category.SECURITY, severity=Severity.ERROR,
                title="Cookie 缺少 Secure 属性",
                description="Cookie 未设置 Secure 标志，可能通过 HTTP 传输",
                recommendation="为所有 Cookie 添加 Secure 属性",
            ))

        if "httponly" not in cookies_str:
            findings.append(Finding(
                category=Category.SECURITY, severity=Severity.WARNING,
                title="Cookie 缺少 HttpOnly 属性",
                description="Cookie 未设置 HttpOnly，JavaScript 可以访问",
                recommendation="为敏感 Cookie 添加 HttpOnly 属性",
            ))

        if "samesite" not in cookies_str:
            findings.append(Finding(
                category=Category.SECURITY, severity=Severity.WARNING,
                title="Cookie 缺少 SameSite 属性",
                description="Cookie 未设置 SameSite，可能存在 CSRF 风险",
                recommendation="添加 SameSite=Lax 或 SameSite=Strict",
            ))

        if not findings:
            findings.append(Finding(
                category=Category.SECURITY, severity=Severity.GOOD,
                title="Cookie 安全属性完整",
                description="Cookie 设置了 Secure、HttpOnly、SameSite",
            ))

        return findings

    def _check_info_leak(self) -> list[Finding]:
        home = self.pages.get(self.base_url)
        if not home or home.status_code != 200:
            return []

        findings = []
        headers = home.headers

        # Server 头
        server = headers.get("Server", "")
        if server:
            # 检查是否包含版本号
            if re.search(r'\d+\.\d+', server):
                findings.append(Finding(
                    category=Category.SECURITY, severity=Severity.WARNING,
                    title="Server 头暴露版本号",
                    description=f"Server: {server}",
                    recommendation="配置服务器隐藏版本信息",
                ))
            else:
                findings.append(Finding(
                    category=Category.SECURITY, severity=Severity.INFO,
                    title="Server 头存在",
                    description=f"Server: {server}（未暴露版本号）",
                ))

        # X-Powered-By 头
        powered_by = headers.get("X-Powered-By", "")
        if powered_by:
            findings.append(Finding(
                category=Category.SECURITY, severity=Severity.WARNING,
                title="X-Powered-By 头暴露技术栈",
                description=f"X-Powered-By: {powered_by}",
                recommendation="移除 X-Powered-By 头，避免暴露服务端技术",
            ))

        # 检查 HTML 中的调试信息
        if home.html:
            debug_patterns = [
                (r'(?i)debug\s*[:=]\s*true', "调试模式可能开启"),
                (r'(?i)APP_DEBUG\s*[:=]\s*true', "Laravel DEBUG 模式开启"),
                (r'<!-- (?:debug|todo|fixme|hack)', "HTML 注释包含调试信息"),
            ]
            for pattern, desc in debug_patterns:
                if re.search(pattern, home.html):
                    findings.append(Finding(
                        category=Category.SECURITY, severity=Severity.ERROR,
                        title="检测到调试信息",
                        description=desc,
                        recommendation="生产环境务必关闭调试模式，清理调试注释",
                    ))

        return findings
