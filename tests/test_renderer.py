from __future__ import annotations

from server.models import BrainstormSession, SessionContent
from server.renderer import ContentRenderer


def test_render_markdown_with_heading() -> None:
    renderer = ContentRenderer()
    session = BrainstormSession(
        content=SessionContent(
            prompt="Prompt",
            body="# Title\n\n- one\n- two",
            content_type="markdown",
        )
    )

    rendered = renderer.render(session)

    assert "Title" in rendered.html
    assert "content-list" in rendered.html
    assert rendered.section_ids == ["title"]


def test_render_mermaid() -> None:
    renderer = ContentRenderer()
    session = BrainstormSession(
        content=SessionContent(
            prompt="Prompt",
            body="graph TD\nA-->B",
            content_type="mermaid",
        )
    )

    rendered = renderer.render(session)

    assert '<pre class="mermaid">' in rendered.html
    assert rendered.section_ids == ["diagram-1"]


def test_render_wireframe_inlines_and_strips_scripts() -> None:
    renderer = ContentRenderer()
    session = BrainstormSession(
        content=SessionContent(
            prompt="Prompt",
            body='<div id="hero" onclick="alert(1)"><script>evil()</script><h1>Hi</h1></div>',
            content_type="wireframe",
        )
    )

    rendered = renderer.render(session)

    assert "wireframe-stage" in rendered.html
    assert "<script>" not in rendered.html.lower()
    assert "onclick" not in rendered.html.lower()
    assert "<h1>Hi</h1>" in rendered.html
    assert "hero" in rendered.section_ids


def test_render_html_uses_sandboxed_iframe() -> None:
    renderer = ContentRenderer()
    session = BrainstormSession(
        content=SessionContent(
            prompt="Prompt",
            body='<script>alert(1)</script><h1>Safe?</h1>',
            content_type="html",
        )
    )

    rendered = renderer.render(session)

    assert "sandbox=\"\"" in rendered.html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered.html
