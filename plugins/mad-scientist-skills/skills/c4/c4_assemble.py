#!/usr/bin/env python3
"""C4 Architecture HTML Assembler.

Cleans rendered SVGs and assembles them into a self-contained architecture.html
with tabbed navigation, embedded SVGs, and a Structurizr DSL source panel.

Usage:
    python c4_assemble.py <project-dir> [--svg-dir <dir>] [--views <view-spec>...]

Arguments:
    project-dir     Path to the project root
    --dsl-path      Path to architecture.dsl (default: <project-dir>/architecture.dsl,
                    falls back to <project-dir>/docs/c4/architecture.dsl)
    --output        Path to write architecture.html (default: same dir as DSL file)
    --svg-dir       Directory containing rendered SVGs (default: system temp dir)
    --views         View specifications as key:label:filename triples (default: auto-detect)

Examples:
    # Auto-detect DSL location and views from SVG filenames in temp dir
    python c4_assemble.py /path/to/project

    # Specify SVG directory explicitly
    python c4_assemble.py /path/to/project --svg-dir /tmp/c4-render

    # Specify DSL path for projects with non-standard layout
    python c4_assemble.py /path/to/project --dsl-path /path/to/project/docs/c4/architecture.dsl

    # Specify views explicitly
    python c4_assemble.py /path/to/project --views \
        "system-context:System Context:structurizr-SystemContext.svg" \
        "containers:Containers:structurizr-Containers.svg"

SVG Cleaning (per C4 skill spec):
    1. Strips <?plantuml ...?> processing instructions
    2. Strips <?plantuml-src ...?> processing instructions
    3. Strips <title>...</title> elements
    4. Strips <g class="title"[^>]*>...</g> groups (handles extra attributes)
    5. Verifies each SVG is clean before embedding (mandatory check)

Output:
    Writes architecture.html in the same directory as the DSL file.
"""

from __future__ import annotations

import argparse
import html as html_mod
import os
import re
import sys
import tempfile
from pathlib import Path

# Well-known Structurizr view names: maps SVG filename patterns to (tab-key, tab-label).
# The fallback detection (below) handles any structurizr-*.svg file not listed here.
KNOWN_VIEWS = [
    ("structurizr-SystemContext.svg", "system-context", "System Context"),
    ("structurizr-Containers.svg", "containers", "Containers"),
    ("structurizr-Components.svg", "components", "Components"),
    ("structurizr-Dynamic.svg", "dynamic", "Dynamic"),
    ("structurizr-Deployment.svg", "deployment", "Deployment"),
]


def clean_svg(content: str) -> str:
    """Strip processing instructions, title elements, and title groups from SVG.

    This is the critical cleaning step. PlantUML generates SVGs with:
    - <?plantuml ...?> processing instructions at the top
    - <title>...</title> elements inside the SVG
    - <g class="title" data-source-line="1">...</g> groups with rendered title text

    The <g> tag has EXTRA ATTRIBUTES beyond just class="title", so the regex
    must use [^>]* to match them. A regex like <g class="title">...</g>
    without the attribute wildcard will SILENTLY FAIL to match.
    """
    # 1. Remove <?plantuml ...?> processing instructions
    content = re.sub(r"<\?plantuml[\s\S]*?\?>", "", content)
    # 2. Remove <?plantuml-src ...?> processing instructions (can be multiline)
    content = re.sub(r"<\?plantuml-src[\s\S]*?\?>", "", content)
    # 3. Remove <title>...</title> element
    content = re.sub(r"<title>.*?</title>", "", content, flags=re.DOTALL)
    # 4. Remove <g class="title" ...>...</g> group — [^>]* matches extra attributes
    content = re.sub(r'<g class="title"[^>]*>.*?</g>', "", content, flags=re.DOTALL)
    return content.strip()


def verify_clean(name: str, content: str) -> None:
    """Verify all title-related content has been removed. Abort if not."""
    checks = [
        (r"<\?plantuml", "processing instruction (<?plantuml)"),
        (r"<title>", "title element (<title>)"),
        (r'class="title"', 'title group (class="title")'),
    ]
    for pattern, desc in checks:
        if re.search(pattern, content):
            print(f"  FAIL: {name} still contains {desc} after cleaning!", file=sys.stderr)
            sys.exit(1)
    print(f"  VERIFIED: {name}")


def detect_views(svg_dir: Path) -> list[tuple[str, str, str]]:
    """Auto-detect views from SVG files present in the directory.

    First matches well-known Structurizr view names (SystemContext, Containers, etc.)
    in a stable order, then appends any remaining structurizr-*.svg files found in
    the directory (sorted alphabetically). This handles both standard and
    project-specific view names without hardcoding.

    Returns list of (filename, tab-key, tab-label) tuples.
    """
    found = []
    seen_filenames: set[str] = set()

    # 1. Match well-known views in stable order
    for filename, key, label in KNOWN_VIEWS:
        if (svg_dir / filename).exists():
            found.append((filename, key, label))
            seen_filenames.add(filename)

    # 2. Append any remaining structurizr-*.svg files not already matched
    for svg_file in sorted(svg_dir.glob("structurizr-*.svg")):
        if svg_file.name in seen_filenames:
            continue
        name = svg_file.stem.replace("structurizr-", "")
        key = name.lower().replace("_", "-")
        # Convert camelCase to "Camel Case" for labels
        label = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
        found.append((svg_file.name, key, label))

    return found


def parse_view_spec(spec: str) -> tuple[str, str, str]:
    """Parse a view spec like 'system-context:System Context:structurizr-SystemContext.svg'."""
    parts = spec.split(":")
    if len(parts) != 3:
        print(f"Invalid view spec '{spec}'. Expected key:label:filename", file=sys.stderr)
        sys.exit(1)
    return parts[2], parts[0], parts[1]  # filename, key, label


def build_html(
    views: list[tuple[str, str, str]],
    svgs: dict[str, str],
    dsl_escaped: str,
    system_name: str,
) -> str:
    """Build the complete HTML file from cleaned SVGs and DSL source."""
    # Build tab buttons
    tabs_html = ""
    for i, (_, key, label) in enumerate(views):
        active = " active" if i == 0 else ""
        tabs_html += f'    <button class="tab{active}" data-tab="{key}">{label}</button>\n'
    tabs_html += '    <button class="tab" data-tab="dsl">Structurizr DSL</button>\n'

    # Build diagram panels
    panels_html = ""
    for i, (_, key, _) in enumerate(views):
        active = " active" if i == 0 else ""
        panels_html += f'  <div id="{key}" class="tab-content{active}">\n'
        panels_html += '    <div class="svg-container">\n'
        panels_html += f"      {svgs[key]}\n"
        panels_html += "    </div>\n"
        panels_html += "  </div>\n\n"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{system_name} &mdash; C4 Architecture</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}

    body {{
      background: #1a1a2e;
      color: #e0e0e0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      margin: 0;
      padding: 24px 32px;
      line-height: 1.6;
    }}

    h1 {{
      font-size: 1.8rem;
      font-weight: 700;
      margin: 0 0 8px 0;
      color: #ffffff;
    }}

    p {{
      margin: 0 0 24px 0;
      color: #a0a0b8;
      font-size: 0.95rem;
    }}

    code {{
      background: #16213e;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
      font-size: 0.9em;
      color: #7ec8e3;
    }}

    .tabs {{
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }}

    .tab {{
      background: #16213e;
      color: #a0a0b8;
      border: 1px solid #2a2a4a;
      border-radius: 24px;
      padding: 8px 20px;
      font-size: 0.9rem;
      font-family: inherit;
      cursor: pointer;
      transition: all 0.2s ease;
      outline: none;
    }}

    .tab:hover {{
      background: #1f2b4d;
      color: #e0e0e0;
      border-color: #3a3a5a;
    }}

    .tab.active {{
      background: #438DD5;
      color: #ffffff;
      border-color: #438DD5;
    }}

    .tab-content {{
      display: none;
    }}

    .tab-content.active {{
      display: block;
    }}

    .svg-container {{
      background: #ffffff;
      border-radius: 8px;
      padding: 16px;
      overflow-x: auto;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
      border: 1px solid #2a2a4a;
    }}

    .svg-container svg {{
      display: block;
      margin: 0 auto;
      height: auto;
    }}

    .dsl-panel {{
      position: relative;
      background: #16213e;
      border-radius: 8px;
      border: 1px solid #2a2a4a;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
      overflow: hidden;
    }}

    .dsl-panel pre {{
      margin: 0;
      padding: 20px;
      overflow-x: auto;
      font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
      font-size: 0.85rem;
      line-height: 1.6;
      color: #c8d0e0;
      tab-size: 4;
    }}

    .dsl-panel code {{
      background: none;
      padding: 0;
      border-radius: 0;
      color: inherit;
      font-size: inherit;
    }}

    .copy-btn {{
      position: absolute;
      top: 12px;
      right: 12px;
      background: #2a2a4a;
      color: #a0a0b8;
      border: 1px solid #3a3a5a;
      border-radius: 6px;
      padding: 6px 14px;
      font-size: 0.8rem;
      font-family: inherit;
      cursor: pointer;
      transition: all 0.2s ease;
      z-index: 10;
    }}

    .copy-btn:hover {{
      background: #3a3a5a;
      color: #e0e0e0;
    }}

    .copy-btn.copied {{
      background: #2e7d32;
      color: #ffffff;
      border-color: #2e7d32;
    }}

    @media (max-width: 600px) {{
      body {{ padding: 16px; }}
      h1 {{ font-size: 1.4rem; }}
      .tab {{ padding: 6px 14px; font-size: 0.8rem; }}
    }}
  </style>
</head>
<body>
  <h1>{system_name} &mdash; C4 Architecture</h1>
  <p>Generated from <code>architecture.dsl</code> using the Structurizr &rarr; PlantUML rendering pipeline.</p>

  <div class="tabs">
{tabs_html}  </div>

{panels_html}  <div id="dsl" class="tab-content">
    <div class="dsl-panel">
      <button class="copy-btn" id="copyBtn" onclick="copyDSL()">Copy</button>
      <pre><code id="dsl-source">{dsl_escaped}</code></pre>
    </div>
  </div>

  <script>
    document.querySelectorAll('.tab').forEach(function(tab) {{
      tab.addEventListener('click', function() {{
        document.querySelectorAll('.tab').forEach(function(t) {{ t.classList.remove('active'); }});
        document.querySelectorAll('.tab-content').forEach(function(c) {{ c.classList.remove('active'); }});
        tab.classList.add('active');
        document.getElementById(tab.getAttribute('data-tab')).classList.add('active');
      }});
    }});

    function copyDSL() {{
      var dslText = document.getElementById('dsl-source').textContent;
      var btn = document.getElementById('copyBtn');
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(dslText).then(function() {{
          btn.textContent = 'Copied!';
          btn.classList.add('copied');
          setTimeout(function() {{
            btn.textContent = 'Copy';
            btn.classList.remove('copied');
          }}, 2000);
        }});
      }} else {{
        var textarea = document.createElement('textarea');
        textarea.value = dslText;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        btn.textContent = 'Copied!';
        btn.classList.add('copied');
        setTimeout(function() {{
          btn.textContent = 'Copy';
          btn.classList.remove('copied');
        }}, 2000);
      }}
    }}
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble C4 architecture.html from rendered SVGs")
    parser.add_argument("project_dir", help="Project root directory")
    parser.add_argument("--dsl-path", help="Path to architecture.dsl (default: auto-detect)")
    parser.add_argument("--output", help="Path to write architecture.html (default: same dir as DSL)")
    parser.add_argument("--svg-dir", help="Directory containing rendered SVGs (default: auto-detect temp dir)")
    parser.add_argument("--views", nargs="*", help="View specs as key:label:filename (default: auto-detect)")
    parser.add_argument("--system-name", help="System name for HTML title (default: extracted from DSL)")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)

    # Auto-detect DSL path: try root first, then docs/c4/
    if args.dsl_path:
        dsl_path = Path(args.dsl_path)
    elif (project_dir / "architecture.dsl").exists():
        dsl_path = project_dir / "architecture.dsl"
    elif (project_dir / "docs" / "c4" / "architecture.dsl").exists():
        dsl_path = project_dir / "docs" / "c4" / "architecture.dsl"
    else:
        print("DSL file not found. Searched:", file=sys.stderr)
        print(f"  {project_dir / 'architecture.dsl'}", file=sys.stderr)
        print(f"  {project_dir / 'docs' / 'c4' / 'architecture.dsl'}", file=sys.stderr)
        print("Use --dsl-path to specify the location.", file=sys.stderr)
        sys.exit(1)

    # Determine SVG directory
    if args.svg_dir:
        svg_dir = Path(args.svg_dir)
    else:
        svg_dir = Path(tempfile.gettempdir()) / "c4-render"

    if not svg_dir.exists():
        print(f"SVG directory not found: {svg_dir}", file=sys.stderr)
        sys.exit(1)

    # Read DSL and extract system name
    dsl_source = dsl_path.read_text(encoding="utf-8")
    if args.system_name:
        system_name = args.system_name
    else:
        match = re.search(r'workspace\s+"([^"]+)"', dsl_source)
        system_name = match.group(1) if match else "System"

    # Determine views
    if args.views:
        views = [parse_view_spec(v) for v in args.views]
    else:
        views = detect_views(svg_dir)

    if not views:
        print(f"No SVG files found in {svg_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"System: {system_name}")
    print(f"SVG dir: {svg_dir}")
    print(f"Views: {len(views)}")
    print()

    # Read, clean, and verify SVGs
    print("Cleaning SVGs:")
    svgs: dict[str, str] = {}
    for filename, key, label in views:
        svg_path = svg_dir / filename
        if not svg_path.exists():
            print(f"  SKIP: {filename} (not found)", file=sys.stderr)
            continue
        raw = svg_path.read_text(encoding="utf-8")
        cleaned = clean_svg(raw)
        verify_clean(f"{key} ({filename})", cleaned)
        svgs[key] = cleaned

    # Filter views to only those with SVGs
    views = [(f, k, l) for f, k, l in views if k in svgs]

    if not views:
        print("No valid SVGs to embed!", file=sys.stderr)
        sys.exit(1)

    # Build and write HTML
    dsl_escaped = html_mod.escape(dsl_source)
    page = build_html(views, svgs, dsl_escaped, system_name)

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = dsl_path.parent / "architecture.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")

    print(f"\nWritten {len(page):,} chars to {out_path}")

    # Final verification on the output
    print("\nFinal HTML verification:")
    for pattern, desc in [('class="title"', "title group"), ("<?plantuml", "processing instruction")]:
        if pattern in page:
            # Check if it's only in the DSL panel (escaped)
            escaped = html_mod.escape(pattern)
            outside_dsl = page.count(pattern) - page.count(escaped)
            if outside_dsl > 0:
                print(f"  FAIL: {outside_dsl} unescaped {desc} found in output!", file=sys.stderr)
                sys.exit(1)
        print(f"  OK: {desc}")

    print("\nDone.")


if __name__ == "__main__":
    main()
