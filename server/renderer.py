from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import html
import re

from .models import BrainstormSession, ContentType


@dataclass
class RenderedContent:
    title: str
    html: str
    section_ids: list[str]


class ContentRenderer:
    def render(self, session: BrainstormSession) -> RenderedContent:
        title = session.content.title or session.content.prompt.strip() or "Brainstorm Session"
        if session.content.content_type == ContentType.mermaid:
            rendered_html = self._render_mermaid(session.content.body)
            section_ids = ["diagram-1"]
        elif session.content.content_type == ContentType.html:
            rendered_html = self._render_html(session.content.body)
            section_ids = self._extract_ids(rendered_html)
        elif session.content.content_type == ContentType.wireframe:
            rendered_html = self._render_wireframe(session.content.body)
            section_ids = self._extract_ids(rendered_html)
        else:
            rendered_html, section_ids = self._render_markdown(session.content.body)
        return RenderedContent(title=title, html=rendered_html, section_ids=section_ids)

    def _render_mermaid(self, source: str) -> str:
        escaped = html.escape(source)
        return (
            '<section id="diagram-1" class="content-card">'
            '<h2 class="section-title">Diagram</h2>'
            f'<pre class="mermaid">{escaped}</pre>'
            "</section>"
        )

    def _render_wireframe(self, source: str) -> str:
        sanitized = self._sanitize_inline(source)
        return (
            '<section id="wireframe-1" class="content-card wireframe-card">'
            '<div class="wireframe-stage">'
            f"{sanitized}"
            "</div>"
            "</section>"
        )

    _SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.IGNORECASE | re.DOTALL)
    _DANGEROUS_TAG_RE = re.compile(
        r"</?\s*(iframe|object|embed|link|meta|base)\b[^>]*>", re.IGNORECASE
    )
    _EVENT_ATTR_RE = re.compile(r"\son[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", re.IGNORECASE)
    _JS_URL_RE = re.compile(r"(href|src|xlink:href)\s*=\s*([\"'])\s*javascript:[^\"']*\2", re.IGNORECASE)

    def _sanitize_inline(self, source: str) -> str:
        cleaned = self._SCRIPT_RE.sub("", source)
        cleaned = self._DANGEROUS_TAG_RE.sub("", cleaned)
        cleaned = self._EVENT_ATTR_RE.sub("", cleaned)
        cleaned = self._JS_URL_RE.sub(r"\1=\2#\2", cleaned)
        return cleaned

    def _render_html(self, source: str) -> str:
        srcdoc = html.escape(source, quote=True)
        return (
            '<section id="html-1" class="content-card html-content">'
            '<h2 class="section-title">HTML Preview</h2>'
            '<iframe class="html-preview-frame" '
            'sandbox="" '
            'referrerpolicy="no-referrer" '
            f'srcdoc="{srcdoc}"></iframe>'
            "</section>"
        )

    def _render_markdown(self, source: str) -> tuple[str, list[str]]:
        lines = source.splitlines()
        output: list[str] = []
        section_ids: list[str] = []
        list_open = False
        paragraph: list[str] = []
        fence_mode: Optional[str] = None
        fence_lines: list[str] = []

        def close_paragraph() -> None:
            nonlocal paragraph
            if paragraph:
                text = html.escape(" ".join(line.strip() for line in paragraph))
                output.append(f"<p>{text}</p>")
                paragraph = []

        def close_list() -> None:
            nonlocal list_open
            if list_open:
                output.append("</ul>")
                list_open = False

        for raw_line in lines:
            line = raw_line.rstrip()
            if line.startswith("```"):
                if fence_mode is None:
                    close_paragraph()
                    close_list()
                    fence_mode = line.removeprefix("```").strip() or "code"
                    fence_lines = []
                else:
                    code = "\n".join(fence_lines)
                    if fence_mode == "mermaid":
                        section_id = f"section-{len(section_ids) + 1}"
                        section_ids.append(section_id)
                        output.append(
                            f'<section id="{section_id}" class="content-card">'
                            '<h2 class="section-title">Mermaid</h2>'
                            f'<pre class="mermaid">{html.escape(code)}</pre>'
                            "</section>"
                        )
                    else:
                        output.append(
                            f'<pre class="code-block"><code>{html.escape(code)}</code></pre>'
                        )
                    fence_mode = None
                    fence_lines = []
                continue

            if fence_mode is not None:
                fence_lines.append(raw_line)
                continue

            if not line.strip():
                close_paragraph()
                close_list()
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                close_paragraph()
                close_list()
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                section_id = self._slugify(heading_text, len(section_ids) + 1)
                section_ids.append(section_id)
                output.append(
                    f'<section id="{section_id}" class="content-card">'
                    f"<h{level}>{html.escape(heading_text)}</h{level}>"
                    "</section>"
                )
                continue

            if line.lstrip().startswith(("- ", "* ")):
                close_paragraph()
                if not list_open:
                    output.append('<ul class="content-list">')
                    list_open = True
                item = line.lstrip()[2:].strip()
                output.append(f"<li>{html.escape(item)}</li>")
                continue

            if "|" in line and line.startswith("|") and line.endswith("|"):
                close_paragraph()
                close_list()
                output.append(self._render_table_row(line))
                continue

            paragraph.append(line)

        close_paragraph()
        close_list()
        if fence_mode is not None and fence_lines:
            output.append(f'<pre class="code-block"><code>{html.escape(chr(10).join(fence_lines))}</code></pre>')
        if not section_ids:
            section_ids.append("section-1")
            output.insert(0, '<section id="section-1" class="content-card">')
            output.append("</section>")
        return "\n".join(output), section_ids

    def _render_table_row(self, line: str) -> str:
        cells = [html.escape(cell.strip()) for cell in line.strip("|").split("|")]
        row = "".join(f"<td>{cell}</td>" for cell in cells)
        return f'<table class="content-table"><tbody><tr>{row}</tr></tbody></table>'

    def _slugify(self, value: str, index: int) -> str:
        lowered = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
        return lowered or f"section-{index}"

    def _extract_ids(self, rendered_html: str) -> list[str]:
        return re.findall(r'id="([^"]+)"', rendered_html)
