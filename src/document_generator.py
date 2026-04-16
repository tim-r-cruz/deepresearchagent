"""Generates a self-contained HTML research document with Notion-inspired styling."""

from __future__ import annotations

import html
import pathlib
import re
from datetime import date
from typing import List, Optional

from .topic_research import TopicResearchBrief


_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI",
               Helvetica, Arial, sans-serif;
  background: #ffffff;
  color: #37352f;
  line-height: 1.65;
  font-size: 15px;
}

.page {
  max-width: 820px;
  margin: 0 auto;
  padding: 4rem 2.5rem 6rem;
}

/* ── Header ── */
.doc-header { margin-bottom: 2.5rem; }

.doc-title {
  font-size: 2.6rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.2;
  margin-bottom: 0.75rem;
}

.doc-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
  font-size: 0.825rem;
  color: #787774;
  margin-bottom: 1rem;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background: #f1f1ef;
  border-radius: 4px;
  padding: 0.2rem 0.55rem;
  font-size: 0.78rem;
  color: #37352f;
  font-weight: 500;
}

.badge.high   { background: #d3f5e9; color: #0f7b6c; }
.badge.medium { background: #fdecc8; color: #9f6b1a; }
.badge.low    { background: #ffe2dd; color: #9c2a1f; }

/* ── Table of contents ── */
.toc {
  background: #f7f7f5;
  border-radius: 8px;
  padding: 1.1rem 1.4rem;
  margin-bottom: 3rem;
}

.toc-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #787774;
  margin-bottom: 0.6rem;
}

.toc-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 0.6rem;
  list-style: none;
  padding: 0;
}

.toc-links a {
  color: #2383e2;
  text-decoration: none;
  font-size: 0.84rem;
  font-weight: 500;
}

.toc-links a:hover { text-decoration: underline; }

.toc-sep {
  color: #ccc;
  font-size: 0.84rem;
}

/* ── Sections ── */
.section {
  margin-bottom: 2.75rem;
  padding-top: 2.75rem;
  border-top: 1px solid #e9e9e7;
}

.section:first-of-type { border-top: none; padding-top: 0; }

.section-heading {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #37352f;
  margin-bottom: 1rem;
}

.section-body {
  font-size: 0.95rem;
  color: #37352f;
}

/* ── Prose ── */
.prose p { margin-bottom: 1rem; }
.prose p:last-child { margin-bottom: 0; }

/* ── Key takeaways box ── */
.key-takeaways {
  background: rgba(35, 131, 226, 0.05);
  border-left: 3px solid #2383e2;
  border-radius: 0 6px 6px 0;
  padding: 0.85rem 1.1rem;
  margin: 0.6rem 0 1.25rem;
}

.key-takeaways-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #2383e2;
  margin-bottom: 0.5rem;
}

.key-takeaways ul {
  padding-left: 1.2rem;
  margin: 0;
}

.key-takeaways li {
  font-size: 0.9rem;
  line-height: 1.55;
  margin-bottom: 0.3rem;
  color: #37352f;
}

.key-takeaways li:last-child { margin-bottom: 0; }

/* ── Q&A blocks ── */
.qa-block {
  margin-bottom: 2.25rem;
  padding-bottom: 2.25rem;
  border-bottom: 1px solid #f1f1ef;
}

.qa-block:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.qa-question {
  font-size: 1.05rem;
  font-weight: 700;
  color: #37352f;
  margin-bottom: 0.65rem;
  line-height: 1.4;
}

.qa-response-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #787774;
  margin-bottom: 0.5rem;
  margin-top: 0.25rem;
}

.qa-response {
  font-size: 0.95rem;
  color: #37352f;
  line-height: 1.75;
}

.qa-response p { margin-bottom: 0.85rem; }
.qa-response p:last-child { margin-bottom: 0; }

/* ── Bullet lists ── */
.bullet-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.bullet-list li {
  padding: 0.45rem 0 0.45rem 1.4rem;
  border-bottom: 1px solid #f7f7f5;
  position: relative;
  font-size: 0.95rem;
  line-height: 1.6;
}

.bullet-list li:last-child { border-bottom: none; }

.bullet-list li::before {
  content: "→";
  position: absolute;
  left: 0;
  color: #2383e2;
  font-weight: 600;
}

/* ── Numbered lists ── */
ol.numbered { padding-left: 1.5rem; }
ol.numbered li {
  margin-bottom: 0.55rem;
  font-size: 0.95rem;
  line-height: 1.6;
}
ol.numbered li::marker { color: #2383e2; font-weight: 600; }

/* ── Callout cards ── */
.callout-card {
  background: #f7f7f5;
  border-radius: 6px;
  padding: 0.9rem 1.1rem;
  margin-bottom: 0.6rem;
  font-size: 0.92rem;
  line-height: 1.6;
}

.callout-card:last-child { margin-bottom: 0; }

.callout-card .card-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #787774;
  margin-bottom: 0.3rem;
}

.callout-card.misconception {
  border-left: 3px solid #e03e3e;
  background: rgba(224, 62, 62, 0.04);
}

.callout-card.case-study {
  border-left: 3px solid #0f7b6c;
  background: rgba(15, 123, 108, 0.04);
}

/* ── Module grid ── */
.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.module-card {
  background: #f7f7f5;
  border-radius: 6px;
  padding: 0.9rem 1rem;
}

.module-card .module-name {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #787774;
  margin-bottom: 0.45rem;
}

.module-card ul {
  padding-left: 1.1rem;
  font-size: 0.86rem;
}

.module-card li { margin-bottom: 0.3rem; }

/* ── Sources ── */
.source-item {
  font-size: 0.83rem;
  color: #37352f;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f1f1ef;
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
}

.source-item:last-child { border-bottom: none; }

.source-score {
  font-size: 0.72rem;
  color: #787774;
  flex-shrink: 0;
}

.source-url {
  color: #2383e2;
  word-break: break-all;
  font-size: 0.78rem;
}

/* ── Footer ── */
.doc-footer {
  margin-top: 4rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e9e9e7;
  font-size: 0.78rem;
  color: #787774;
}
"""


class DocumentGenerator:
    def __init__(self, output_path: pathlib.Path):
        self.output_path = output_path

    def build(self, topic: str, brief: TopicResearchBrief, author: str = ""):
        html_content = self._render(topic, brief, author)
        self.output_path.write_text(html_content, encoding="utf-8")

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _prose_to_bullets(text: str, max_bullets: int = 6) -> List[str]:
        """Split \n\n-separated prose into individual sentences, up to max_bullets."""
        bullets: List[str] = []
        for para in text.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for s in sentences:
                s = s.strip()
                if s:
                    bullets.append(s)
                if len(bullets) >= max_bullets:
                    return bullets
        return bullets

    @staticmethod
    def _paragraphs(text: str) -> str:
        """Render \n\n-separated text as <p> tags."""
        e = html.escape
        return "".join(
            f"<p>{e(para.strip())}</p>"
            for para in text.split("\n\n")
            if para.strip()
        ) or f"<p>{e(text)}</p>"

    @staticmethod
    def _bullet_items(items: List[str]) -> str:
        e = html.escape
        return "".join(f"<li>{e(item)}</li>" for item in items)

    # ── Render ────────────────────────────────────────────────────────────────

    def _render(self, topic: str, brief: TopicResearchBrief, author: str) -> str:
        e = html.escape
        today = date.today().strftime("%B %d, %Y")
        confidence = brief.citation_confidence.lower()
        score = f"{brief.source_score:.2f}"
        author_display = e(author) if author else "Research Studio"

        # ── Summary ──────────────────────────────────────────────────────────
        summary_html = self._paragraphs(brief.summary)

        # ── Research Findings (Q&A with key takeaways) ───────────────────────
        guiding_html = ""
        gqr = getattr(brief, "guiding_question_responses", None) or []
        if gqr:
            blocks = ""
            for item in gqr:
                q_text   = e(item.get("question", ""))
                response = item.get("response", "")
                bullets  = item.get("bullets") or self._prose_to_bullets(response)

                takeaways_items = "".join(f"<li>{e(b)}</li>" for b in bullets)
                takeaways_html = f"""
              <div class="key-takeaways">
                <div class="key-takeaways-label">Key Takeaways</div>
                <ul>{takeaways_items}</ul>
              </div>""" if takeaways_items else ""

                response_paras = self._paragraphs(response)
                blocks += f"""
            <div class="qa-block">
              <div class="qa-question">{q_text}</div>
              {takeaways_html}
              <div class="qa-response-label">Full Response</div>
              <div class="qa-response">{response_paras}</div>
            </div>"""

            guiding_html = f"""
        <div class="section" id="findings">
          <div class="section-heading">Research Findings</div>
          <div class="section-body">{blocks}</div>
        </div>"""
        elif brief.guiding_questions:
            items = self._bullet_items(brief.guiding_questions)
            guiding_html = f"""
        <div class="section" id="findings">
          <div class="section-heading">Guiding Questions</div>
          <div class="section-body"><ol class="numbered">{items}</ol></div>
        </div>"""

        # ── Key Concepts (talking points as bullets) ──────────────────────────
        talking_items = self._bullet_items(brief.talking_points or [])
        talking_html = f"""
        <div class="section" id="concepts">
          <div class="section-heading">Key Concepts</div>
          <div class="section-body">
            <ul class="bullet-list">{talking_items}</ul>
          </div>
        </div>""" if talking_items else ""

        # ── Learning Objectives ───────────────────────────────────────────────
        objectives_items = self._bullet_items(brief.learning_objectives or [])
        objectives_html = f"""
        <div class="section" id="objectives">
          <div class="section-heading">Learning Objectives</div>
          <div class="section-body"><ol class="numbered">{objectives_items}</ol></div>
        </div>""" if objectives_items else ""

        # ── Prerequisites ─────────────────────────────────────────────────────
        prereqs_items = self._bullet_items(brief.prerequisite_topics or [])
        prereqs_html = f"""
        <div class="section" id="prerequisites">
          <div class="section-heading">Prerequisites</div>
          <div class="section-body"><ul class="bullet-list">{prereqs_items}</ul></div>
        </div>""" if prereqs_items else ""

        # ── Curriculum Modules ────────────────────────────────────────────────
        module_cards = ""
        for mod_name, mod_items in (brief.curriculum_modules or {}).items():
            items_html = "".join(f"<li>{e(item)}</li>" for item in mod_items)
            module_cards += f"""
            <div class="module-card">
              <div class="module-name">{e(mod_name.replace('_', ' ').capitalize())}</div>
              <ul>{items_html}</ul>
            </div>"""

        modules_html = f"""
        <div class="section" id="modules">
          <div class="section-heading">Curriculum Modules</div>
          <div class="module-grid">{module_cards}</div>
        </div>""" if module_cards else ""

        # ── Case Studies ──────────────────────────────────────────────────────
        case_cards = ""
        for i, c in enumerate(brief.case_studies or [], 1):
            case_cards += f"""
            <div class="callout-card case-study">
              <div class="card-label">Case {i}</div>
              {e(c)}
            </div>"""

        cases_html = f"""
        <div class="section" id="cases">
          <div class="section-heading">Case Studies</div>
          <div class="section-body">{case_cards}</div>
        </div>""" if case_cards else ""

        # ── Lab Exercises ─────────────────────────────────────────────────────
        labs_items = self._bullet_items(brief.lab_exercises or [])
        labs_html = f"""
        <div class="section" id="labs">
          <div class="section-heading">Lab Exercises</div>
          <div class="section-body"><ol class="numbered">{labs_items}</ol></div>
        </div>""" if labs_items else ""

        # ── Misconceptions ────────────────────────────────────────────────────
        misconception_cards = ""
        for m in (brief.misconceptions or []):
            misconception_cards += f"""
            <div class="callout-card misconception">
              <div class="card-label">Common Misconception</div>
              {e(m)}
            </div>"""

        misconceptions_html = f"""
        <div class="section" id="misconceptions">
          <div class="section-heading">Common Misconceptions</div>
          <div class="section-body">{misconception_cards}</div>
        </div>""" if misconception_cards else ""

        # ── Discussion Questions ───────────────────────────────────────────────
        discussion_items = self._bullet_items(brief.discussion_questions or [])
        discussion_html = f"""
        <div class="section" id="discussion">
          <div class="section-heading">Discussion Questions</div>
          <div class="section-body"><ol class="numbered">{discussion_items}</ol></div>
        </div>""" if discussion_items else ""

        # ── Sources ───────────────────────────────────────────────────────────
        sources_inner = ""
        if brief.citations:
            for c in brief.citations[:8]:
                url_display = c.url if len(c.url) < 80 else c.url[:77] + "…"
                sources_inner += f"""
              <div class="source-item">
                <span class="source-score">[{e(c.citation_confidence)} {c.weighted_score:.2f}]</span>
                <span>
                  <strong>{e(c.title)}</strong>&nbsp;
                  <a class="source-url" href="{e(c.url)}" target="_blank">{e(url_display)}</a>
                </span>
              </div>"""
        elif brief.sources:
            for s in brief.sources[:8]:
                sources_inner += f'<div class="source-item"><a class="source-url" href="{e(s)}" target="_blank">{e(s)}</a></div>'
        else:
            sources_inner = '<p style="color:#787774;font-size:0.85rem">No external sources collected.</p>'

        sources_html = f"""
        <div class="section" id="sources">
          <div class="section-heading">Research Sources</div>
          <div class="section-body">{sources_inner}</div>
        </div>"""

        # ── Table of contents ─────────────────────────────────────────────────
        toc_sections = [
            ("summary",       "Summary"),
        ]
        if gqr or brief.guiding_questions:
            toc_sections.append(("findings",      "Research Findings"))
        if talking_items:
            toc_sections.append(("concepts",      "Key Concepts"))
        if objectives_items:
            toc_sections.append(("objectives",    "Learning Objectives"))
        if prereqs_items:
            toc_sections.append(("prerequisites", "Prerequisites"))
        if module_cards:
            toc_sections.append(("modules",       "Curriculum Modules"))
        if case_cards:
            toc_sections.append(("cases",         "Case Studies"))
        if labs_items:
            toc_sections.append(("labs",          "Lab Exercises"))
        if misconception_cards:
            toc_sections.append(("misconceptions","Misconceptions"))
        if discussion_items:
            toc_sections.append(("discussion",    "Discussion Questions"))
        toc_sections.append(("sources", "Sources"))

        toc_links = ""
        for i, (anchor, label) in enumerate(toc_sections):
            if i > 0:
                toc_links += '<li class="toc-sep">·</li>'
            toc_links += f'<li><a href="#{anchor}">{e(label)}</a></li>'

        toc_html = f"""
      <nav class="toc">
        <div class="toc-label">Contents</div>
        <ul class="toc-links">{toc_links}</ul>
      </nav>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(topic)} — Research Document</title>
  <style>{_CSS}</style>
</head>
<body>
  <div class="page">

    <header class="doc-header">
      <h1 class="doc-title">{e(topic)}</h1>
      <div class="doc-meta">
        <span>Author: {author_display}</span>
        <span>Generated: {today}</span>
      </div>
      <div>
        <span class="badge {confidence}">
          {e(brief.citation_confidence)} confidence · score {score}
        </span>
      </div>
    </header>

    {toc_html}

    <div class="section" id="summary">
      <div class="section-heading">Summary</div>
      <div class="section-body prose">{summary_html}</div>
    </div>

    {guiding_html}

    {talking_html}

    {objectives_html}

    {prereqs_html}

    {modules_html}

    {cases_html}

    {labs_html}

    {misconceptions_html}

    {discussion_html}

    {sources_html}

    <footer class="doc-footer">
      Generated by Research Studio · {today}
    </footer>

  </div>
</body>
</html>"""
