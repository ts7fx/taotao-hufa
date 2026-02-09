"""数据结构定义"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class Severity(Enum):
    GOOD = "good"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Category(Enum):
    SEO = "SEO"
    PERFORMANCE = "性能"
    CONTENT = "内容"
    SECURITY = "安全"


@dataclass
class PageData:
    """单个页面的爬取数据"""
    url: str
    status_code: int = 0
    content_type: str = ""
    html: str = ""
    headers: dict = field(default_factory=dict)
    response_time: float = 0.0  # 秒
    content_length: int = 0  # 字节
    title: str = ""
    meta_description: str = ""
    h1_tags: list[str] = field(default_factory=list)
    h2_tags: list[str] = field(default_factory=list)
    h3_tags: list[str] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)  # [{"src": ..., "alt": ...}]
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    scripts: list[str] = field(default_factory=list)
    stylesheets: list[str] = field(default_factory=list)
    canonical_url: str = ""
    og_tags: dict = field(default_factory=dict)
    json_ld: list[dict] = field(default_factory=list)
    word_count: int = 0
    crawled_at: float = field(default_factory=time.time)
    error: str = ""


@dataclass
class Finding:
    """单条分析发现"""
    category: Category
    severity: Severity
    title: str
    description: str
    recommendation: str = ""
    url: str = ""  # 相关页面 URL（可选）


@dataclass
class CategoryReport:
    """单个维度的分析报告"""
    category: Category
    score: int  # 0-100
    grade: str  # A/B/C/D/F
    findings: list[Finding] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def good_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.GOOD)


@dataclass
class AnalysisReport:
    """完整分析报告"""
    target_url: str
    total_pages: int
    crawl_duration: float  # 秒
    categories: list[CategoryReport] = field(default_factory=list)
    overall_score: int = 0
    overall_grade: str = "F"
    generated_at: str = ""
    pages: dict = field(default_factory=dict)  # url -> PageData
