"""工具函数"""

from urllib.parse import urlparse, urljoin, urldefrag
from models import Severity
from datetime import datetime


def normalize_url(url: str, base_url: str = "") -> str:
    """标准化 URL：去掉 fragment，确保绝对路径"""
    if base_url:
        url = urljoin(base_url, url)
    url, _ = urldefrag(url)
    # 去掉尾部斜杠（首页除外）
    parsed = urlparse(url)
    if parsed.path and parsed.path != "/" and parsed.path.endswith("/"):
        url = url.rstrip("/")
    return url


def is_same_domain(url: str, base_url: str) -> bool:
    """判断 URL 是否属于同一域名"""
    try:
        return urlparse(url).netloc == urlparse(base_url).netloc
    except Exception:
        return False


def is_crawlable_url(url: str) -> bool:
    """判断 URL 是否可爬取（排除非 HTML 资源）"""
    skip_extensions = {
        '.pdf', '.zip', '.rar', '.gz', '.tar',
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv',
        '.css', '.js', '.woff', '.woff2', '.ttf', '.eot',
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    }
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    return not any(path_lower.endswith(ext) for ext in skip_extensions)


def calculate_score(findings: list) -> int:
    """根据 findings 计算分数（满分 100）"""
    score = 100
    for f in findings:
        if f.severity == Severity.ERROR:
            score -= 15
        elif f.severity == Severity.WARNING:
            score -= 5
    return max(0, score)


def score_to_grade(score: int) -> str:
    """分数转等级"""
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


def format_bytes(size: int) -> str:
    """字节数格式化"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


def format_duration(seconds: float) -> str:
    """秒数格式化"""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"


def now_str() -> str:
    """当前时间字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
