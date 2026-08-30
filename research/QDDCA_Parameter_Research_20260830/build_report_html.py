"""Assemble the deep-research Markdown into the provided report template."""

import importlib.util
import re
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
MARKDOWN = DIRECTORY / "research_report_20260830_qddca_parameter_optimization.md"
OUTPUT = DIRECTORY / "research_report_20260830_qddca_parameter_optimization.html"
SKILL = Path(r"C:\Users\nhatdevzizi-desktop\.codex\skills\deep-research")
CONVERTER_PATH = SKILL / "scripts" / "md_to_html.py"
TEMPLATE_PATH = SKILL / "templates" / "mckinsey_report_template.html"


def load_converter():
    spec = importlib.util.spec_from_file_location("deep_research_md_to_html", CONVERTER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.convert_markdown_to_html


def main():
    convert = load_converter()
    markdown = MARKDOWN.read_text(encoding="utf-8")
    before_bibliography, remainder = markdown.split("## Bibliography", 1)
    bibliography_body, after_bibliography = remainder.split("## Appendix: Methodology", 1)
    converter_input = (
        before_bibliography
        + "## Appendix: Methodology"
        + after_bibliography
        + "\n## Bibliography\n"
        + bibliography_body
    )
    content, bibliography = convert(converter_input)
    bibliography = re.sub(
        r"(?m)^\[(\d+)\]\s*(.+)$",
        r'<div class="bib-entry"><span class="bib-number">[\1]</span> \2</div>',
        bibliography,
    )
    bibliography = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", bibliography)
    bibliography = re.sub(
        r"(https?://[^\s<]+)",
        r'<a href="\1" target="_blank">\1</a>',
        bibliography,
    )
    content = re.sub(
        r"<p>!\[Full QDDCA parameter grid\]\(full_grid_tradeoffs\.png\)\s*</p>",
        '<figure><img src="full_grid_tradeoffs.png" alt="Full QDDCA parameter grid"><figcaption>Figure 1. Full new-QDDCA EDR, drop, and CV parameter surface.</figcaption></figure>',
        content,
    )
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    metrics = """
    <div class="metrics-dashboard">
      <div class="metric"><span class="metric-number">w=2</span><span class="metric-label">Exact window</span></div>
      <div class="metric"><span class="metric-number">M=3</span><span class="metric-label">Minimum retry plateau</span></div>
      <div class="metric"><span class="metric-number">194.87</span><span class="metric-label">EDR pairs/s</span></div>
      <div class="metric"><span class="metric-number">0.001909</span><span class="metric-label">Request CV</span></div>
    </div>
    """
    html = (
        template.replace("{{TITLE}}", "QDDCA Retry and Sending-Window Optimization")
        .replace("{{DATE}}", "2026-08-30")
        .replace("{{SOURCE_COUNT}}", "16")
        .replace("{{METRICS_DASHBOARD}}", metrics)
        .replace("{{CONTENT}}", content)
        .replace("{{BIBLIOGRAPHY}}", bibliography)
    )
    print_css = """
    <style>
      figure { margin: 18px 0; page-break-inside: avoid; }
      figure img { width: 100%; height: auto; display: block; }
      figcaption { font-size: 9pt; color: #4a5568; margin-top: 6pt; }
      table, .executive-summary, .key-insight, figure { page-break-inside: avoid; }
      h2, h3, h4 { page-break-after: avoid; }
      p { orphans: 3; widows: 3; }
      @page { size: A4; margin: 18mm 16mm 18mm 16mm;
        @bottom-center { content: counter(page); font-size: 8pt; color: #666; }
      }
      @media print {
        body { font-size: 10pt; line-height: 1.5; }
        .header h1 { font-size: 22pt; }
        .section-title { font-size: 14pt; }
        .subsection-title { font-size: 11pt; }
        .metrics-dashboard { display: table; width: 100%; }
        .metric { display: table-cell; width: 25%; padding: 8pt; }
        .metric-number { font-size: 18pt; }
        .content { padding: 18pt 22pt; }
        .bib-entry, .bibliography-content { font-size: 8pt; }
      }
    </style>
    """
    html = html.replace("</head>", print_css + "\n</head>")
    OUTPUT.write_text(html, encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
