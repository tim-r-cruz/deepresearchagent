"""Generates a self-contained HTML research document with Notion-inspired styling."""

from __future__ import annotations

import html
import pathlib
from datetime import date
from typing import Optional

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
  max-width: 780px;
  margin: 0 auto;
  padding: 4rem 2.5rem 6rem;
}

/* ── Header ── */
.doc-header { margin-bottom: 3rem; }

.doc-title {
  font-size: 2.4rem;
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
  margin-bottom: 1.25rem;
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

/* ── Sections ── */
.section {
  margin-bottom: 2.5rem;
  padding-top: 2.5rem;
  border-top: 1px solid #e9e9e7;
}

.section:first-of-type { border-top: none; padding-top: 0; }

.section-title {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #787774;
  margin-bottom: 0.85rem;
}

.section-body {
  font-size: 0.95rem;
  color: #37352f;
}

/* ── Lists ── */
ol, ul { padding-left: 1.5rem; }
li { margin-bottom: 0.45rem; }
li::marker { color: #787774; }

/* ── Module grid ── */
.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.module-card {
  background: #f7f7f5;
  border-radius: 6px;
  padding: 0.9rem 1rem;
}

.module-card .module-name {
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #787774;
  margin-bottom: 0.45rem;
}

.module-card ul {
  padding-left: 1.1rem;
  font-size: 0.85rem;
}

/* ── Prose paragraphs ── */
.prose p { margin-bottom: 1rem; }
.prose p:last-child { margin-bottom: 0; }

/* ── Q&A blocks ── */
.qa-block {
  margin-bottom: 2rem;
}
.qa-block:last-child { margin-bottom: 0; }

.qa-question {
  font-size: 1rem;
  font-weight: 600;
  color: #37352f;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #2383e2;
}

.qa-response {
  font-size: 0.95rem;
  color: #37352f;
  line-height: 1.75;
}

.qa-response p { margin-bottom: 0.85rem; }
.qa-response p:last-child { margin-bottom: 0; }

/* ── Callout blocks ── */
.callout {
  background: #f7f7f5;
  border-radius: 6px;
  padding: 1rem 1.25rem;
  margin-bottom: 0.6rem;
  font-size: 0.9rem;
}

.callout.accent {
  border-left: 3px solid #2383e2;
  background: rgba(35, 131, 226, 0.05);
}

/* ── Sources ── */
.source-item {
  font-size: 0.82rem;
  color: #37352f;
  padding: 0.4rem 0;
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

    def _render(self, topic: str, brief: TopicResearchBrief, author: str) -> str:
        e = html.escape
        today = date.today().strftime("%B %d, %Y")
        confidence = brief.citation_confidence.lower()
        score = f"{brief.source_score:.2f}"

        # Guiding questions — show full Q&A if available, fallback to plain list
        guiding_html = ""
        if getattr(brief, "guiding_question_responses", None):
            blocks = ""
            for item in brief.guiding_question_responses:
                q_text = e(item.get("question", ""))
                response_paragraphs = item.get("response", "")
                paras = "".join(
                    f"<p>{e(para.strip())}</p>"
                    for para in response_paragraphs.split("\n\n")
                    if para.strip()
                )
                blocks += f"""
            <div class="qa-block">
              <div class="qa-question">{q_text}</div>
              <div class="qa-response">{paras}</div>
            </div>"""
            guiding_html = f"""
        <div class="section">
          <div class="section-title">Research Findings</div>
          <div class="section-body">{blocks}</div>
        </div>"""
        elif brief.guiding_questions:
            items = "".join(f"<li>{e(q)}</li>" for q in brief.guiding_questions)
            guiding_html = f"""
        <div class="section">
          <div class="section-title">Guiding Questions</div>
          <div class="section-body"><ol>{items}</ol></div>
        </div>"""

        # Curriculum modules grid
        module_cards = ""
        for mod_name, mod_items in (brief.curriculum_modules or {}).items():
            items_html = "".join(f"<li>{e(item)}</li>" for item in mod_items)
            module_cards += f"""
            <div class="module-card">
              <div class="module-name">{e(mod_name.capitalize())}</div>
              <ul>{items_html}</ul>
            </div>"""

        modules_html = ""
        if module_cards:
            modules_html = f"""
        <div class="section">
          <div class="section-title">Curriculum Modules</div>
          <div class="module-grid">{module_cards}</div>
        </div>"""

        # Learning objectives
        objectives_html = "".join(
            f"<li>{e(obj)}</li>" for obj in (brief.learning_objectives or [])
        )

        # Talking points
        talking_html = "".join(
            f'<div class="callout accent">{e(pt)}</div>'
            for pt in (brief.talking_points or [])
        )

        # Discussion questions
        discussion_html = "".join(
            f"<li>{e(q)}</li>" for q in (brief.discussion_questions or [])
        )

        # Case studies
        cases_html = "".join(
            f'<div class="callout">{e(c)}</div>'
            for c in (brief.case_studies or [])
        )

        # Lab exercises
        labs_html = "".join(
            f"<li>{e(lab)}</li>" for lab in (brief.lab_exercises or [])
        )

        # Misconceptions
        misconceptions_html = "".join(
            f'<div class="callout">{e(m)}</div>'
            for m in (brief.misconceptions or [])
        )

        # Prerequisites
        prereqs_html = "".join(
            f"<li>{e(p)}</li>" for p in (brief.prerequisite_topics or [])
        )

        # Sources
        sources_html = ""
        if brief.citations:
            for c in brief.citations[:8]:
                url_display = c.url if len(c.url) < 80 else c.url[:77] + "…"
                sources_html += f"""
              <div class="source-item">
                <span class="source-score">[{e(c.citation_confidence)} {c.weighted_score:.2f}]</span>
                <span>
                  <strong>{e(c.title)}</strong>
                  <a class="source-url" href="{e(c.url)}" target="_blank">{e(url_display)}</a>
                </span>
              </div>"""
        elif brief.sources:
            for s in brief.sources[:8]:
                sources_html += f'<div class="source-item"><span class="source-url">{e(s)}</span></div>'
        else:
            sources_html = '<p style="color:#787774;font-size:0.85rem">No external sources collected.</p>'

        # Summary — render as paragraphs
        summary_html = "".join(
            f"<p>{e(para.strip())}</p>"
            for para in brief.summary.split("\n\n")
            if para.strip()
        ) or f"<p>{e(brief.summary)}</p>"

        author_display = e(author) if author else "Research Studio"

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

    <div class="section">
      <div class="section-title">Summary</div>
      <div class="section-body prose">{summary_html}</div>
    </div>

    {guiding_html}

    <div class="section">
      <div class="section-title">Learning Objectives</div>
      <div class="section-body"><ol>{objectives_html}</ol></div>
    </div>

    <div class="section">
      <div class="section-title">Prerequisites</div>
      <div class="section-body"><ul>{prereqs_html}</ul></div>
    </div>

    <div class="section">
      <div class="section-title">Key Concepts</div>
      <div class="section-body">{talking_html}</div>
    </div>

    {modules_html}

    <div class="section">
      <div class="section-title">Discussion Questions</div>
      <div class="section-body"><ol>{discussion_html}</ol></div>
    </div>

    <div class="section">
      <div class="section-title">Case Studies</div>
      <div class="section-body">{cases_html}</div>
    </div>

    <div class="section">
      <div class="section-title">Lab Exercises</div>
      <div class="section-body"><ol>{labs_html}</ol></div>
    </div>

    <div class="section">
      <div class="section-title">Common Misconceptions</div>
      <div class="section-body">{misconceptions_html}</div>
    </div>

    <div class="section">
      <div class="section-title">Research Sources</div>
      <div class="section-body">{sources_html}</div>
    </div>

    <footer class="doc-footer">
      Generated by Research Studio · {today}
    </footer>

  </div>
</body>
</html>"""
