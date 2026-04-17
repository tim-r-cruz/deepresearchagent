"""Generates a Markdown research document."""

from __future__ import annotations

import pathlib
import re
from datetime import date
from typing import List, Optional

from .topic_research import TopicResearchBrief


class DocumentGenerator:
    def __init__(self, output_path: pathlib.Path):
        self.output_path = output_path

    def build(self, topic: str, brief: TopicResearchBrief, author: str = ""):
        md = self._render(topic, brief, author)
        self.output_path.write_text(md, encoding="utf-8")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _prose_to_bullets(text: str, max_bullets: int = 6) -> List[str]:
        bullets: List[str] = []
        for para in text.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            for s in re.split(r"(?<=[.!?])\s+", para):
                s = s.strip()
                if s:
                    bullets.append(s)
                if len(bullets) >= max_bullets:
                    return bullets
        return bullets

    @staticmethod
    def _slug(text: str) -> str:
        return re.sub(r"[^\w\- ]", "", text.lower()).strip().replace(" ", "-")

    # ── Render ────────────────────────────────────────────────────────────────

    def _render(self, topic: str, brief: TopicResearchBrief, author: str) -> str:
        today = date.today().strftime("%B %d, %Y")
        author_display = author or "Research Studio"
        lines: List[str] = []

        def h(level: int, text: str) -> str:
            return f"{'#' * level} {text}"

        def section(heading: str, body: List[str]):
            lines.append(h(2, heading))
            lines.append("")
            lines.extend(body)
            lines.append("")

        # ── Header ────────────────────────────────────────────────────────────
        lines.append(h(1, topic))
        lines.append("")
        lines.append(f"**Author:** {author_display}  ")
        lines.append(f"**Generated:** {today}  ")
        lines.append(f"**Confidence:** {brief.citation_confidence} (score: {brief.source_score:.2f})")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ── Table of contents ─────────────────────────────────────────────────
        toc_entries: List[tuple[str, str]] = [("Summary", "summary")]
        gqr = getattr(brief, "guiding_question_responses", None) or []
        if gqr or brief.guiding_questions:
            toc_entries.append(("Research Findings", "research-findings"))
        if brief.talking_points:
            toc_entries.append(("Key Concepts", "key-concepts"))
        if brief.learning_objectives:
            toc_entries.append(("Learning Objectives", "learning-objectives"))
        if brief.prerequisite_topics:
            toc_entries.append(("Prerequisites", "prerequisites"))
        if brief.curriculum_modules:
            toc_entries.append(("Curriculum Modules", "curriculum-modules"))
        if brief.case_studies:
            toc_entries.append(("Case Studies", "case-studies"))
        if brief.lab_exercises:
            toc_entries.append(("Lab Exercises", "lab-exercises"))
        if brief.misconceptions:
            toc_entries.append(("Common Misconceptions", "common-misconceptions"))
        if brief.discussion_questions:
            toc_entries.append(("Discussion Questions", "discussion-questions"))
        toc_entries.append(("Research Sources", "research-sources"))

        lines.append("**Contents**")
        lines.append("")
        for label, anchor in toc_entries:
            lines.append(f"- [{label}](#{anchor})")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ── Summary ───────────────────────────────────────────────────────────
        lines.append(h(2, "Summary"))
        lines.append("")
        for para in brief.summary.split("\n\n"):
            para = para.strip()
            if para:
                lines.append(para)
                lines.append("")

        # ── Research Findings ─────────────────────────────────────────────────
        if gqr:
            lines.append(h(2, "Research Findings"))
            lines.append("")
            for item in gqr:
                question = item.get("question", "").strip()
                response = item.get("response", "").strip()
                bullets  = item.get("bullets") or self._prose_to_bullets(response)

                lines.append(h(3, question))
                lines.append("")

                if bullets:
                    lines.append("> **Key Takeaways**")
                    lines.append(">")
                    for b in bullets:
                        lines.append(f"> - {b}")
                    lines.append("")

                lines.append("**Full Response**")
                lines.append("")
                for para in response.split("\n\n"):
                    para = para.strip()
                    if para:
                        lines.append(para)
                        lines.append("")

        elif brief.guiding_questions:
            body = [f"{i}. {q}" for i, q in enumerate(brief.guiding_questions, 1)]
            section("Guiding Questions", body)

        # ── Key Concepts ──────────────────────────────────────────────────────
        if brief.talking_points:
            lines.append(h(2, "Key Concepts"))
            lines.append("")
            for pt in brief.talking_points:
                lines.append(f"- {pt}")
            lines.append("")

        # ── Learning Objectives ───────────────────────────────────────────────
        if brief.learning_objectives:
            lines.append(h(2, "Learning Objectives"))
            lines.append("")
            for i, obj in enumerate(brief.learning_objectives, 1):
                lines.append(f"{i}. {obj}")
            lines.append("")

        # ── Prerequisites ─────────────────────────────────────────────────────
        if brief.prerequisite_topics:
            lines.append(h(2, "Prerequisites"))
            lines.append("")
            for p in brief.prerequisite_topics:
                lines.append(f"- {p}")
            lines.append("")

        # ── Curriculum Modules ────────────────────────────────────────────────
        if brief.curriculum_modules:
            lines.append(h(2, "Curriculum Modules"))
            lines.append("")
            for mod_name, mod_items in brief.curriculum_modules.items():
                if not mod_items:
                    continue
                lines.append(h(3, mod_name.replace("_", " ").capitalize()))
                lines.append("")
                for item in mod_items:
                    lines.append(f"- {item}")
                lines.append("")

        # ── Case Studies ──────────────────────────────────────────────────────
        if brief.case_studies:
            lines.append(h(2, "Case Studies"))
            lines.append("")
            for i, c in enumerate(brief.case_studies, 1):
                lines.append(f"**Case {i}:** {c}")
                lines.append("")

        # ── Lab Exercises ─────────────────────────────────────────────────────
        if brief.lab_exercises:
            lines.append(h(2, "Lab Exercises"))
            lines.append("")
            for i, lab in enumerate(brief.lab_exercises, 1):
                lines.append(f"{i}. {lab}")
            lines.append("")

        # ── Common Misconceptions ─────────────────────────────────────────────
        if brief.misconceptions:
            lines.append(h(2, "Common Misconceptions"))
            lines.append("")
            for m in brief.misconceptions:
                lines.append(f"> ⚠️ {m}")
                lines.append("")

        # ── Discussion Questions ───────────────────────────────────────────────
        if brief.discussion_questions:
            lines.append(h(2, "Discussion Questions"))
            lines.append("")
            for i, q in enumerate(brief.discussion_questions, 1):
                lines.append(f"{i}. {q}")
            lines.append("")

        # ── Research Sources ──────────────────────────────────────────────────
        lines.append(h(2, "Research Sources"))
        lines.append("")
        if brief.citations:
            for c in brief.citations[:8]:
                lines.append(f"- **{c.title}** [{c.citation_confidence} {c.weighted_score:.2f}]  ")
                lines.append(f"  {c.url}")
        elif brief.sources:
            for s in brief.sources[:8]:
                lines.append(f"- {s}")
        else:
            lines.append("_No external sources collected._")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"_Generated by Research Studio · {today}_")

        return "\n".join(lines)
