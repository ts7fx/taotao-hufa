"""桃桃护法 - 网站分析爬虫 CLI 入口"""

import argparse
import os
import sys
import time
from datetime import datetime
from urllib.parse import urlparse

from crawler import Crawler
from analyzers import SEOAnalyzer, PerformanceAnalyzer, ContentAnalyzer, SecurityAnalyzer
from models import AnalysisReport, CategoryReport, Category
from report import generate_report
from utils import calculate_score, score_to_grade, now_str


def run_analysis(url: str, max_pages: int = 50, delay: float = 1.0,
                 output: str = "report.html",
                 dataforseo_login: str = "", dataforseo_password: str = ""):
    """执行完整分析流程"""
    print("🍑 桃桃护法 v1.0 — tenmomo.com 的守护工具")
    print("=" * 50)

    # 1. 爬取
    start_time = time.time()
    crawler = Crawler(url, max_pages=max_pages, delay=delay)
    pages = crawler.crawl()

    if not pages:
        print("❌ 未爬取到任何页面，请检查 URL")
        sys.exit(1)

    crawl_duration = time.time() - start_time

    # 2. 四维分析
    print("🔍 开始分析...")
    analyzers = [
        (Category.SEO, SEOAnalyzer(pages, url)),
        (Category.PERFORMANCE, PerformanceAnalyzer(pages, url)),
        (Category.CONTENT, ContentAnalyzer(pages, url)),
        (Category.SECURITY, SecurityAnalyzer(pages, url)),
    ]

    # DataForSEO 增强分析（可选）
    dataforseo_findings = []
    if dataforseo_login and dataforseo_password:
        print("\n📡 DataForSEO API 增强分析...")
        try:
            from analyzers.dataforseo import DataForSEOClient, DataForSEOAnalyzer
            client = DataForSEOClient(dataforseo_login, dataforseo_password)
            dfs_analyzer = DataForSEOAnalyzer(client, url)
            dataforseo_findings = dfs_analyzer.analyze()
            print(f"  获得 {len(dataforseo_findings)} 条专业分析结果")
        except Exception as e:
            print(f"  ⚠️ DataForSEO 分析失败: {e}")
    else:
        print("\n💡 提示: 配置 DataForSEO API 可获得更专业的分析")
        print("   --dataforseo-login LOGIN --dataforseo-password PASSWORD")
        print("   或设置环境变量 DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD")
        print("   文档: https://docs.dataforseo.com/v3/\n")

    categories = []
    for category, analyzer in analyzers:
        findings = analyzer.analyze()
        # 合并 DataForSEO 同类别的发现
        for df in dataforseo_findings:
            if df.category == category:
                findings.append(df)
        score = calculate_score(findings)
        grade = score_to_grade(score)
        cat_report = CategoryReport(
            category=category,
            score=score,
            grade=grade,
            findings=findings,
        )
        categories.append(cat_report)
        print(f"  {category.value}: {score} 分 ({grade})")

    # 3. 综合评分
    overall_score = sum(c.score for c in categories) // len(categories)
    overall_grade = score_to_grade(overall_score)

    report = AnalysisReport(
        target_url=url,
        total_pages=len(pages),
        crawl_duration=crawl_duration,
        categories=categories,
        overall_score=overall_score,
        overall_grade=overall_grade,
        generated_at=now_str(),
        pages=pages,
    )

    # 4. 生成报告
    print()
    generate_report(report, output)
    print(f"\n🍑 综合评分: {overall_score} ({overall_grade})")
    print(f"📊 浏览器打开 {output} 查看详细报告")


def main():
    parser = argparse.ArgumentParser(
        description="🍑 桃桃护法 - 网站分析爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python main.py https://tenmomo.com
  python main.py https://tenmomo.com --max-pages 100 --delay 0.5 -o report.html
  python main.py https://tenmomo.com --dataforseo-login YOUR_LOGIN --dataforseo-password YOUR_PASSWORD

DataForSEO API:
  注册: https://app.dataforseo.com/register
  文档: https://docs.dataforseo.com/v3/
  定价: 按量付费，注册送 $1 试用额度，Sandbox 免费"""
    )
    parser.add_argument("url", help="目标网站 URL")
    parser.add_argument("--max-pages", type=int, default=50, help="最大爬取页面数（默认 50）")
    parser.add_argument("--delay", type=float, default=1.0, help="请求间隔秒数（默认 1.0）")
    parser.add_argument("-o", "--output", default="", help="报告输出路径（默认 reports/时间戳_tenmomo.html）")
    parser.add_argument("--dataforseo-login", default="",
                        help="DataForSEO API 登录名（或设置 DATAFORSEO_LOGIN 环境变量）")
    parser.add_argument("--dataforseo-password", default="",
                        help="DataForSEO API 密码（或设置 DATAFORSEO_PASSWORD 环境变量）")

    args = parser.parse_args()

    if not args.url.startswith(("http://", "https://")):
        args.url = "https://" + args.url

    # 环境变量兜底
    dfs_login = args.dataforseo_login or os.environ.get("DATAFORSEO_LOGIN", "")
    dfs_password = args.dataforseo_password or os.environ.get("DATAFORSEO_PASSWORD", "")

    # 默认输出到 reports/ 目录，时间戳命名
    output = args.output
    if not output:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        reports_dir = os.path.join(script_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        domain = urlparse(args.url).netloc.replace(".", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = os.path.join(reports_dir, f"{timestamp}_{domain}.html")

    run_analysis(args.url, args.max_pages, args.delay, output, dfs_login, dfs_password)


if __name__ == "__main__":
    main()
