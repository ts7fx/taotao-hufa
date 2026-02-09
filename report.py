"""HTML 报告生成（Jinja2 模板，内联 CSS，单文件输出）"""

from jinja2 import Template
from models import AnalysisReport, Severity

TEMPLATE = Template('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>桃桃护法 - {{ report.target_url }} 分析报告</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #f0f2f5;
    color: #333;
    line-height: 1.6;
}
.container { max-width: 1100px; margin: 0 auto; padding: 20px; }

/* 头部 */
.header {
    text-align: center;
    padding: 40px 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 16px;
    margin-bottom: 30px;
}
.header h1 { font-size: 2em; margin-bottom: 8px; }
.header .subtitle { opacity: 0.9; font-size: 1.1em; }
.header .meta { margin-top: 12px; font-size: 0.9em; opacity: 0.8; }

/* 综合评分 */
.overall-score {
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 30px 0;
}
.score-circle {
    width: 160px; height: 160px;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    color: white;
    box-shadow: 0 8px 32px rgba(0,0,0,0.15);
}
.score-circle .number { font-size: 3em; line-height: 1; }
.score-circle .grade { font-size: 1.2em; margin-top: 4px; opacity: 0.9; }

.grade-A { background: linear-gradient(135deg, #43a047, #66bb6a); }
.grade-B { background: linear-gradient(135deg, #7cb342, #9ccc65); }
.grade-C { background: linear-gradient(135deg, #ffa726, #ffb74d); }
.grade-D { background: linear-gradient(135deg, #ef5350, #e57373); }
.grade-F { background: linear-gradient(135deg, #c62828, #e53935); }

/* 四维评分卡片 */
.score-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin-bottom: 30px;
}
.score-card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    transition: transform 0.2s;
}
.score-card:hover { transform: translateY(-2px); }
.score-card .cat-name { font-size: 1em; color: #666; margin-bottom: 8px; }
.score-card .cat-score { font-size: 2.5em; font-weight: bold; }
.score-card .cat-grade {
    display: inline-block;
    padding: 2px 12px;
    border-radius: 12px;
    font-weight: bold;
    font-size: 0.85em;
    margin-top: 4px;
}
.score-card .cat-counts { margin-top: 10px; font-size: 0.85em; color: #888; }

.text-A { color: #43a047; }
.text-B { color: #7cb342; }
.text-C { color: #ffa726; }
.text-D { color: #ef5350; }
.text-F { color: #c62828; }

.badge-A { background: #e8f5e9; color: #2e7d32; }
.badge-B { background: #f1f8e9; color: #558b2f; }
.badge-C { background: #fff8e1; color: #f57f17; }
.badge-D { background: #fbe9e7; color: #bf360c; }
.badge-F { background: #ffebee; color: #b71c1c; }

/* 分析详情 */
.section {
    background: white;
    border-radius: 12px;
    margin-bottom: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    overflow: hidden;
}
.section-header {
    padding: 20px 24px;
    background: #fafbfc;
    border-bottom: 1px solid #eee;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.section-header h2 { font-size: 1.3em; }
.section-badge {
    padding: 4px 16px;
    border-radius: 20px;
    font-weight: bold;
    font-size: 0.9em;
}

/* 发现列表 */
.finding {
    padding: 16px 24px;
    border-bottom: 1px solid #f0f0f0;
    display: flex;
    gap: 16px;
    align-items: flex-start;
}
.finding:last-child { border-bottom: none; }
.finding-icon {
    flex-shrink: 0;
    width: 28px; height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    margin-top: 2px;
}
.icon-good { background: #e8f5e9; color: #43a047; }
.icon-info { background: #e3f2fd; color: #1976d2; }
.icon-warning { background: #fff8e1; color: #f9a825; }
.icon-error { background: #ffebee; color: #e53935; }

.finding-body { flex: 1; }
.finding-title { font-weight: 600; margin-bottom: 4px; }
.finding-desc { color: #666; font-size: 0.9em; white-space: pre-line; }
.finding-rec {
    margin-top: 6px;
    padding: 6px 10px;
    background: #f8f9fa;
    border-left: 3px solid #667eea;
    font-size: 0.85em;
    color: #555;
    border-radius: 0 4px 4px 0;
}
.finding-url { font-size: 0.8em; color: #999; margin-top: 4px; word-break: break-all; }

/* 页脚 */
.footer {
    text-align: center;
    padding: 30px;
    color: #999;
    font-size: 0.85em;
}

/* 响应式 */
@media (max-width: 600px) {
    .score-cards { grid-template-columns: repeat(2, 1fr); }
    .header h1 { font-size: 1.5em; }
    .score-circle { width: 120px; height: 120px; }
    .score-circle .number { font-size: 2.2em; }
}
</style>
</head>
<body>
<div class="container">

<div class="header">
    <h1>🍑 桃桃护法</h1>
    <div class="subtitle">网站分析报告 — {{ report.target_url }}</div>
    <div class="meta">
        爬取 {{ report.total_pages }} 个页面 · 耗时 {{ duration }} · {{ report.generated_at }}
    </div>
</div>

<div class="overall-score">
    <div class="score-circle grade-{{ report.overall_grade }}">
        <span class="number">{{ report.overall_score }}</span>
        <span class="grade">{{ report.overall_grade }} 级</span>
    </div>
</div>

<div class="score-cards">
{% for cat in report.categories %}
    <div class="score-card">
        <div class="cat-name">{{ cat.category.value }}</div>
        <div class="cat-score text-{{ cat.grade }}">{{ cat.score }}</div>
        <div class="cat-grade badge-{{ cat.grade }}">{{ cat.grade }} 级</div>
        <div class="cat-counts">
            ✅ {{ cat.good_count }}　⚠️ {{ cat.warning_count }}　❌ {{ cat.error_count }}
        </div>
    </div>
{% endfor %}
</div>

{% for cat in report.categories %}
<div class="section">
    <div class="section-header">
        <h2>{{ cat.category.value }} 分析</h2>
        <span class="section-badge badge-{{ cat.grade }}">{{ cat.score }} 分 · {{ cat.grade }} 级</span>
    </div>
    {% for f in cat.findings %}
    <div class="finding">
        <div class="finding-icon icon-{{ f.severity.value }}">
            {% if f.severity.value == "good" %}✓{% elif f.severity.value == "info" %}i{% elif f.severity.value == "warning" %}!{% else %}✕{% endif %}
        </div>
        <div class="finding-body">
            <div class="finding-title">{{ f.title }}</div>
            <div class="finding-desc">{{ f.description }}</div>
            {% if f.recommendation %}
            <div class="finding-rec">💡 {{ f.recommendation }}</div>
            {% endif %}
            {% if f.url %}
            <div class="finding-url">📎 {{ f.url }}</div>
            {% endif %}
        </div>
    </div>
    {% endfor %}
</div>
{% endfor %}

<div class="footer">
    🍑 桃桃护法 v1.0 — tenmomo.com 的守护工具<br>
    报告生成于 {{ report.generated_at }}
</div>

</div>
</body>
</html>''')


def generate_report(report: AnalysisReport, output_path: str):
    """生成 HTML 报告"""
    from utils import format_duration
    html = TEMPLATE.render(
        report=report,
        duration=format_duration(report.crawl_duration),
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📄 报告已生成: {output_path}")
