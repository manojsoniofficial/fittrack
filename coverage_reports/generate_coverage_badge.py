"""Generate a simple SVG coverage badge from a coverage.py XML report."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET


def badge_color(percent: float) -> str:
    if percent >= 90:
        return "#16a34a"  # green
    if percent >= 80:
        return "#65a30d"  # lime
    if percent >= 70:
        return "#ca8a04"  # yellow
    if percent >= 60:
        return "#ea580c"  # orange
    return "#dc2626"      # red


def estimate_text_width(text: str) -> int:
    # Approximate monospace-like width for badge sizing.
    return max(24, len(text) * 7 + 10)


def render_svg(label: str, value: str, color: str) -> str:
    left_w = estimate_text_width(label)
    right_w = estimate_text_width(value)
    total_w = left_w + right_w

    left_mid = left_w // 2
    right_mid = left_w + (right_w // 2)

    return f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{total_w}\" height=\"20\" role=\"img\" aria-label=\"{label}: {value}\">
  <title>{label}: {value}</title>
  <linearGradient id=\"s\" x2=\"0\" y2=\"100%\">
    <stop offset=\"0\" stop-color=\"#fff\" stop-opacity=\".15\"/>
    <stop offset=\"1\" stop-opacity=\".15\"/>
  </linearGradient>
  <clipPath id=\"r\">
    <rect width=\"{total_w}\" height=\"20\" rx=\"3\" fill=\"#fff\"/>
  </clipPath>
  <g clip-path=\"url(#r)\">
    <rect width=\"{left_w}\" height=\"20\" fill=\"#334155\"/>
    <rect x=\"{left_w}\" width=\"{right_w}\" height=\"20\" fill=\"{color}\"/>
    <rect width=\"{total_w}\" height=\"20\" fill=\"url(#s)\"/>
  </g>
  <g fill=\"#fff\" text-anchor=\"middle\" font-family=\"Segoe UI,Arial,sans-serif\" font-size=\"11\">
    <text x=\"{left_mid}\" y=\"15\" fill=\"#010101\" fill-opacity=\".35\">{label}</text>
    <text x=\"{left_mid}\" y=\"14\">{label}</text>
    <text x=\"{right_mid}\" y=\"15\" fill=\"#010101\" fill-opacity=\".35\">{value}</text>
    <text x=\"{right_mid}\" y=\"14\">{value}</text>
  </g>
</svg>
"""


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python coverage_reports/generate_coverage_badge.py <coverage.xml> <output.svg>")
        return 1

    xml_path = sys.argv[1]
    output_path = sys.argv[2]

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        line_rate = float(root.attrib.get("line-rate", "0"))
    except Exception as exc:  # pragma: no cover - utility script
        print(f"Failed to read coverage XML: {exc}")
        return 1

    percent = round(line_rate * 100, 1)
    if percent.is_integer():
        value = f"{int(percent)}%"
    else:
        value = f"{percent}%"

    svg = render_svg("coverage", value, badge_color(percent))

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg)
    except Exception as exc:  # pragma: no cover - utility script
        print(f"Failed to write badge SVG: {exc}")
        return 1

    print(f"Coverage badge generated: {output_path} ({value})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
