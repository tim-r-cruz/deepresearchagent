from __future__ import annotations

import pathlib
import re
from typing import List, Optional

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from .topic_research import TopicResearchBrief

# ── Colour palette (Notion-inspired) ────────────────────────────────────────
C_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
C_SURFACE = RGBColor(0xF7, 0xF7, 0xF5)
C_TEXT    = RGBColor(0x37, 0x35, 0x2F)
C_SUBTLE  = RGBColor(0x78, 0x77, 0x74)
C_ACCENT  = RGBColor(0x23, 0x83, 0xE2)
C_DIVIDER = RGBColor(0xE9, 0xE9, 0xE7)
C_GREEN   = RGBColor(0x0F, 0x7B, 0x6C)

# ── Typography ───────────────────────────────────────────────────────────────
FONT_HEADING = "Calibri Light"
FONT_BODY    = "Calibri"

# ── Layout constants (13.33 × 7.5 in, standard widescreen) ──────────────────
W         = Inches(13.33)
H         = Inches(7.5)
MARGIN_L  = Inches(0.9)
MARGIN_R  = Inches(0.9)
MARGIN_T  = Inches(0.6)
CONTENT_W = W - MARGIN_L - MARGIN_R   # ≈ 11.53 in


class SlideDeckGenerator:
    def __init__(self, output_path: pathlib.Path):
        self.output_path = output_path
        self.presentation = Presentation()
        self.presentation.slide_width  = W
        self.presentation.slide_height = H
        self._blank = self._find_blank_layout()
        self._slide_num = 0

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _find_blank_layout(self):
        for layout in self.presentation.slide_layouts:
            if layout.name.lower() == "blank":
                return layout
        return self.presentation.slide_layouts[6]

    def _new_slide(self):
        slide = self.presentation.slides.add_slide(self._blank)
        # Remove any placeholder shapes that the blank layout might carry
        for ph in list(slide.placeholders):
            ph._element.getparent().remove(ph._element)
        bg = slide.background
        bg.fill.solid()
        bg.fill.fore_color.rgb = C_WHITE
        self._slide_num += 1
        return slide

    def _set_bg(self, slide, color: RGBColor):
        bg = slide.background
        bg.fill.solid()
        bg.fill.fore_color.rgb = color

    def _txb(self, slide, left, top, width, height):
        """Add a textbox and return its text_frame with word-wrap on."""
        shape = slide.shapes.add_textbox(left, top, width, height)
        tf = shape.text_frame
        tf.word_wrap = True
        return tf

    def _rect(self, slide, left, top, width, height, color: RGBColor):
        """Add a solid filled, borderless rectangle."""
        shp = slide.shapes.add_shape(1, left, top, width, height)  # 1 = rectangle
        shp.fill.solid()
        shp.fill.fore_color.rgb = color
        shp.line.fill.background()
        return shp

    def _set_para(self, p, text: str, font: str, size: float, color: RGBColor,
                  bold: bool = False, italic: bool = False,
                  align: PP_ALIGN = PP_ALIGN.LEFT,
                  space_before: float = 0, space_after: float = 0):
        p.text = text
        p.alignment = align
        if space_before:
            p.space_before = Pt(space_before)
        if space_after:
            p.space_after = Pt(space_after)
        for run in p.runs:
            run.font.name   = font
            run.font.size   = Pt(size)
            run.font.color.rgb = color
            run.font.bold   = bold
            run.font.italic = italic

    def _add_para(self, tf, text: str, font: str, size: float, color: RGBColor,
                  bold: bool = False, space_before: float = 0,
                  align: PP_ALIGN = PP_ALIGN.LEFT):
        p = tf.add_paragraph()
        self._set_para(p, text, font, size, color, bold=bold,
                       space_before=space_before, align=align)
        return p

    def _attach_notes(self, slide, notes_text: str):
        slide.notes_slide.notes_text_frame.text = notes_text

    # ── Public slide builders ────────────────────────────────────────────────

    def add_title_slide(self, course_title: str, author: str = "Course Agent"):
        slide = self._new_slide()

        # Thin accent strip at top
        self._rect(slide, Inches(0), Inches(0), W, Inches(0.05), C_ACCENT)

        # Topic title — large, left-aligned
        tf = self._txb(slide, MARGIN_L, Inches(2.2), CONTENT_W, Inches(2.0))
        self._set_para(tf.paragraphs[0], course_title,
                       FONT_HEADING, 38, C_TEXT, bold=False)

        # Author / subtitle
        tf2 = self._txb(slide, MARGIN_L, Inches(4.4), CONTENT_W, Inches(0.7))
        self._set_para(tf2.paragraphs[0], f"Prepared by {author}",
                       FONT_BODY, 16, C_SUBTLE)

        # Bottom bar
        self._rect(slide, Inches(0), H - Inches(0.48), W, Inches(0.48), C_SURFACE)
        tf3 = self._txb(slide, MARGIN_L, H - Inches(0.44), CONTENT_W, Inches(0.38))
        self._set_para(tf3.paragraphs[0], "Research Studio",
                       FONT_BODY, 10, C_SUBTLE)

        notes = self._build_speaker_notes(
            title=course_title,
            bullets=[f"Instructor: {author}",
                     "Introduce learning outcomes and expected participation.",
                     "Set context for the module progression and timing."],
            slide_type="title",
        )
        self._attach_notes(slide, notes)

    def add_section_slide(self, title: str, bullets: List[str]):
        """Add a content slide. Section-header titles get a distinctive look."""
        clean = [b.strip() for b in bullets if b and b.strip()]
        slide_type = self._infer_slide_type(title)

        if slide_type in ("section-divider",) or re.match(r"^Part \d+", title):
            self._build_section_divider(title, clean)
        else:
            self._build_content_slide(title, clean, slide_type)

    def _build_section_divider(self, title: str, bullets: List[str]):
        slide = self._new_slide()
        self._set_bg(slide, C_SURFACE)

        # Short accent bar
        self._rect(slide, MARGIN_L, Inches(3.1), Inches(0.45), Pt(3), C_ACCENT)

        # Section title — large, left-aligned
        tf = self._txb(slide, MARGIN_L, Inches(3.2), CONTENT_W, Inches(1.8))
        self._set_para(tf.paragraphs[0], title, FONT_HEADING, 32, C_TEXT)

        # Optional first bullet as a brief descriptor
        if bullets:
            tf2 = self._txb(slide, MARGIN_L, Inches(4.9), CONTENT_W, Inches(0.8))
            self._set_para(tf2.paragraphs[0], bullets[0], FONT_BODY, 16, C_SUBTLE)

        notes = self._build_speaker_notes(title, bullets, "generic")
        self._attach_notes(slide, notes)

    def _build_content_slide(self, title: str, bullets: List[str], slide_type: str):
        slide = self._new_slide()

        # Title
        tf = self._txb(slide, MARGIN_L, MARGIN_T, CONTENT_W, Inches(0.85))
        self._set_para(tf.paragraphs[0], title, FONT_HEADING, 24, C_TEXT)

        # Thin divider under title
        self._rect(slide, MARGIN_L, Inches(1.42), CONTENT_W, Pt(1), C_DIVIDER)

        # Body
        if bullets:
            BODY_T = Inches(1.6)
            BODY_H = H - BODY_T - Inches(0.55)
            tf2 = self._txb(slide, MARGIN_L, BODY_T, CONTENT_W, BODY_H)
            self._set_para(tf2.paragraphs[0], bullets[0], FONT_BODY, 17, C_TEXT)
            for bullet in bullets[1:]:
                self._add_para(tf2, bullet, FONT_BODY, 17, C_TEXT,
                               space_before=9)

        # Subtle bottom bar
        self._rect(slide, Inches(0), H - Inches(0.38), W, Inches(0.38), C_SURFACE)
        tf3 = self._txb(slide, MARGIN_L, H - Inches(0.35), CONTENT_W, Inches(0.3))
        self._set_para(tf3.paragraphs[0], "Research Studio",
                       FONT_BODY, 9, C_SUBTLE)

        notes = self._build_speaker_notes(title, bullets, slide_type)
        self._attach_notes(slide, notes)

    # ── Slide type inference ─────────────────────────────────────────────────

    def _infer_slide_type(self, title: str) -> str:
        lowered = title.lower()
        if re.match(r"^part \d+", lowered):
            return "section-divider"
        if "overview" in lowered or "roadmap" in lowered:
            return "overview"
        if "objective" in lowered or "prerequisite" in lowered:
            return "course-setup"
        if "foundation" in lowered or "core concept" in lowered or "historical" in lowered:
            return "foundations"
        if "method" in lowered or "model" in lowered or "evaluation" in lowered:
            return "methods"
        if "application" in lowered or "domain" in lowered:
            return "applications"
        if "case study" in lowered:
            return "case-study"
        if "deployment" in lowered or "monitor" in lowered:
            return "deployment"
        if "ethical" in lowered or "accountability" in lowered:
            return "ethics"
        if "pitfall" in lowered or "misconception" in lowered or "failure" in lowered:
            return "pitfalls"
        if "lab" in lowered or "exercise" in lowered:
            return "lab"
        if "discussion" in lowered or "capstone" in lowered:
            return "discussion"
        if "reference" in lowered:
            return "references"
        return "generic"

    # ── Speaker notes ────────────────────────────────────────────────────────

    def _build_speaker_notes(self, title: str, bullets: List[str], slide_type: str = "generic") -> str:
        key_points = bullets[:4] if bullets else ["Introduce the key theme of this slide."]
        while len(key_points) < 4:
            key_points.append("Connect this point to the previous and next concepts in the lesson flow.")

        templates = {
            "title": [
                ("Session launch", f"Welcome learners and frame the session goal around '{title}'. Set expectations for participation, evidence-based reasoning, and applied thinking. Clarify how the lecture, discussion breaks, and exercises will be paced."),
                ("Learner contract", "Define what students should do during class: ask clarifying questions, challenge assumptions respectfully, and justify claims with data or references."),
                ("Relevance framing", "Connect the topic to career pathways, interdisciplinary transfer, and problem-solving utility. Give one real community or industry example where this content improves decisions."),
                ("Roadmap preview", "Walk through module flow from foundations to governance and capstone critique. Explain why the order matters and where students should expect conceptual difficulty."),
                ("Timing note", "Keep this segment to about five minutes, including one quick poll or hands-up prompt to assess prior familiarity."),
            ],
            "overview": [
                ("Context", f"Introduce '{title}' as the map for the whole session. Explain how each section builds from definitions to high-stakes decision-making."),
                ("Path through content", f"Describe the arc using '{key_points[0]}' and '{key_points[1]}'. Emphasize that understanding process quality is as important as model performance."),
                ("Where students struggle", "Flag common confusion early: mixing metrics with outcomes, over-trusting complex models, and ignoring implementation constraints."),
                ("Engagement prompt", f"Ask students which part they expect to be most challenging: '{key_points[2]}' or '{key_points[3]}'."),
                ("Timing note", "Use approximately five minutes here to orient, motivate, and set participation norms."),
            ],
            "foundations": [
                ("Concept clarity", f"Use '{title}' to build precise definitions before jumping into techniques. Distinguish terms that are often conflated in introductory materials."),
                ("Deep explanation", f"Unpack '{key_points[0]}' and '{key_points[1]}' with mechanism-level explanation. Show how assumptions influence what conclusions are valid."),
                ("Theory-to-practice", f"Use '{key_points[2]}' to bridge abstraction and practical interpretation. Ask students to identify what evidence would confirm or contradict the claim."),
                ("Misconception check", "Surface one foundational misconception and correct it with a counterexample."),
                ("Timing note", "This foundation block should support roughly five minutes of explanation plus a brief comprehension check."),
            ],
            "methods": [
                ("Method purpose", f"Frame '{title}' around decision quality, not tool preference. Clarify when each method class is appropriate and where it fails."),
                ("Workflow coaching", f"Walk through '{key_points[0]}' and '{key_points[1]}' as a reproducible workflow."),
                ("Trade-off analysis", f"Use '{key_points[2]}' to discuss bias-variance, interpretability-performance, and robustness-cost trade-offs."),
                ("Quality control", "Describe validation traps and leakage patterns that invalidate results."),
                ("Timing note", "Spend about five minutes here with one mini walk-through of a method choice."),
            ],
            "applications": [
                ("Use-case framing", f"Present '{title}' as decision support in realistic organizational settings."),
                ("Operational constraints", f"Discuss '{key_points[0]}' and '{key_points[1]}' with concrete constraints: data availability, latency, policy, and stakeholder trust."),
                ("Impact and outcomes", f"Use '{key_points[2]}' to compare technical performance versus real outcome improvement."),
                ("Transferability", "Invite learners to adapt the example to a different domain and identify what changes in assumptions, risk tolerance, and governance."),
                ("Timing note", "Allocate approximately five minutes and keep examples concrete and evidence-backed."),
            ],
            "case-study": [
                ("Case setup", f"Introduce the case objective for '{title}' and define stakeholders, constraints, and success criteria."),
                ("Decision chronology", "Reconstruct decisions in sequence: framing, data choice, model strategy, evaluation, and deployment."),
                ("Failure and recovery", f"Use '{key_points[2]}' to discuss what almost went wrong and how teams mitigated risk."),
                ("Class critique", "Run a short critique: what would students do differently with the same context and evidence?"),
                ("Timing note", "Target around five minutes with one minute reserved for learner critique."),
            ],
            "deployment": [
                ("Production mindset", f"Frame '{title}' around reliability over novelty."),
                ("Monitoring essentials", f"Walk through '{key_points[0]}' and '{key_points[1]}' with concrete monitoring signals and retraining triggers."),
                ("Incident response", f"Use '{key_points[2]}' to describe rollback criteria, owner responsibilities, and communication protocol."),
                ("Governance tie-in", "Connect technical monitoring to governance: approvals, audit evidence, and stakeholder reporting."),
                ("Timing note", "Spend approximately five minutes and anchor every point in operational accountability."),
            ],
            "ethics": [
                ("Ethical lens", f"Position '{title}' as a design requirement, not an afterthought."),
                ("Fairness analysis", f"Use '{key_points[0]}' and '{key_points[1]}' to discuss representational harms and measurement bias."),
                ("Accountability practice", f"Use '{key_points[2]}' to define who is responsible for audits, appeals, and remediation."),
                ("Deliberation prompt", "Invite structured disagreement: what is the most defensible compromise between utility and equity?"),
                ("Timing note", "Use roughly five minutes with emphasis on reasoning quality and stakeholder impact."),
            ],
            "pitfalls": [
                ("Failure orientation", f"Frame '{title}' as prevention through anticipatory thinking."),
                ("Common traps", f"Analyze '{key_points[0]}' and '{key_points[1]}' with concrete warning signs."),
                ("Diagnostic questions", f"Use '{key_points[2]}' to teach diagnostic prompts: what assumptions break, what data shifts."),
                ("Mitigation playbook", "Provide mitigation sequence: detect, isolate, communicate, remediate, verify."),
                ("Timing note", "Keep this to approximately five minutes and emphasize actionable diagnostics."),
            ],
            "lab": [
                ("Exercise objective", f"Set up '{title}' with clear deliverable, constraints, and evidence standards."),
                ("Work plan", f"Break down '{key_points[0]}' and '{key_points[1]}' into phases with expected outputs."),
                ("Coaching cues", f"Use '{key_points[2]}' to coach teams on where to focus effort."),
                ("Debrief design", "Explain how groups will present findings and respond to peer critique."),
                ("Timing note", "Reserve about five minutes for instruction before teams begin active work."),
            ],
            "discussion": [
                ("Prompt setup", f"Use '{title}' to launch an analytic discussion, not opinion exchange."),
                ("Argument structure", f"Anchor discussion around '{key_points[0]}' and '{key_points[1]}'."),
                ("Counter-position", f"Use '{key_points[2]}' to invite a counter-position and test which argument survives stronger scrutiny."),
                ("Synthesis", "Conclude with a structured synthesis: strongest claim, key uncertainty, and practical next action."),
                ("Timing note", "This segment should run about five minutes with high student participation."),
            ],
            "references": [
                ("Evidence audit", f"Introduce '{title}' as an evidence-quality checkpoint."),
                ("Source interpretation", f"Walk through '{key_points[0]}' and '{key_points[1]}' and describe how each source informed course claims."),
                ("Confidence calibration", f"Use '{key_points[2]}' to model confidence calibration: what is known, what is uncertain."),
                ("Scholarly practice", "Remind students to separate citation count from evidentiary strength."),
                ("Timing note", "Use roughly five minutes to reinforce reproducible, evidence-based reasoning habits."),
            ],
            "course-setup": [
                ("Setup framing", f"Use '{title}' to set the academic baseline for this cohort."),
                ("Readiness check", f"Work through '{key_points[0]}' and '{key_points[1]}' as readiness indicators."),
                ("Bridging strategy", f"Use '{key_points[2]}' to explain how weaker prerequisite areas will be reinforced."),
                ("Support plan", "Point to office hours, peer collaboration expectations, and rubric criteria."),
                ("Timing note", "Allocate approximately five minutes to calibrate the room and align expectations."),
            ],
            "generic": [
                ("Opening framing", f"Start by naming the purpose of '{title}' and why it matters in the course arc."),
                ("Guided walkthrough", f"Walk through '{key_points[0]}' and '{key_points[1]}' with mechanism-level explanation."),
                ("Applied example", f"Use '{key_points[2]}' to anchor an applied scenario and ask students to identify risk and trade-offs."),
                ("Critical discussion", f"Use '{key_points[3]}' to invite critique of assumptions and argument quality."),
                ("Timing note", "This pacing should provide approximately five minutes of instructor talking material."),
            ],
        }

        sections = templates.get(slide_type, templates["generic"])
        lines = []
        for section_title, section_text in sections:
            lines.append(f"{section_title}:")
            lines.append(section_text)
            lines.append("")
        return "\n".join(lines).strip()

    # ── Research-specific slides ─────────────────────────────────────────────

    def add_topic_research_slides(self, idx: int, brief: TopicResearchBrief):
        deep_dive_bullets = [
            f"Summary: {brief.summary[:220]}",
            f"Source score: {brief.source_score:.2f} | Citation confidence: {brief.citation_confidence}",
            f"Talking point 1: {brief.talking_points[0]}",
            f"Talking point 2: {brief.talking_points[1]}",
            f"Talking point 3: {brief.talking_points[2]}",
        ]
        self.add_section_slide(f"Module {idx} Deep Dive: {brief.topic}", deep_dive_bullets)

        discussion_bullets = [
            f"Prompt 1: {brief.discussion_questions[0]}",
            f"Prompt 2: {brief.discussion_questions[1]}",
            f"Prompt 3: {brief.discussion_questions[2]}",
            "Ask students to support their claims with evidence from the source readings.",
        ]
        self.add_section_slide(f"Module {idx} Discussion Lab", discussion_bullets)

    def add_guiding_question_slide(self, question: str, response: str):
        """One slide per guiding question with a full prose answer."""
        slide = self._new_slide()

        # Question as title
        tf = self._txb(slide, MARGIN_L, MARGIN_T, CONTENT_W, Inches(1.1))
        p = tf.paragraphs[0]
        self._set_para(p, question, FONT_HEADING, 20, C_TEXT)

        # Thin accent divider
        self._rect(slide, MARGIN_L, Inches(1.58), CONTENT_W, Pt(2), C_ACCENT)

        # Response as body — split into paragraphs and show as wrapped text
        BODY_T = Inches(1.72)
        BODY_H = H - BODY_T - Inches(0.55)
        tf2 = self._txb(slide, MARGIN_L, BODY_T, CONTENT_W, BODY_H)

        paragraphs = [p.strip() for p in response.split("\n\n") if p.strip()]
        if paragraphs:
            self._set_para(tf2.paragraphs[0], paragraphs[0], FONT_BODY, 14, C_TEXT)
            for para in paragraphs[1:4]:  # fit up to 4 paragraphs
                self._add_para(tf2, para, FONT_BODY, 14, C_TEXT, space_before=10)
        else:
            self._set_para(tf2.paragraphs[0], response[:600], FONT_BODY, 14, C_TEXT)

        # Bottom bar
        self._rect(slide, Inches(0), H - Inches(0.38), W, Inches(0.38), C_SURFACE)
        tf3 = self._txb(slide, MARGIN_L, H - Inches(0.35), CONTENT_W, Inches(0.3))
        self._set_para(tf3.paragraphs[0], "Research Studio", FONT_BODY, 9, C_SUBTLE)

        self._attach_notes(slide, f"Question: {question}\n\nFull response:\n{response}")

    def add_references_slide(self, research_brief: TopicResearchBrief):
        source_lines: List[str] = []
        if research_brief.citations:
            for citation in research_brief.citations[:6]:
                source_lines.append(
                    f"{citation.source} [{citation.citation_confidence} {citation.weighted_score:.2f}]: {citation.url}"
                )
        else:
            for source in research_brief.sources:
                source_lines.append(f"Reference: {source}")

        self.add_section_slide("Research References", source_lines or ["No external references collected."])

    def save(self):
        self.presentation.save(self.output_path)

    # ── Full deck builders ───────────────────────────────────────────────────

    def build_research_deck(self, topic: str, research_brief: TopicResearchBrief, course_title: str, author: str):
        """Generate a research-based course deck with evidence-driven structure."""
        modules      = research_brief.curriculum_modules or {}
        foundations  = modules.get("foundations", [])
        methods      = modules.get("methods", [])
        applications = modules.get("applications", [])
        evaluation   = modules.get("evaluation", [])
        deployment   = modules.get("deployment", [])
        ethics       = modules.get("ethics", [])
        pitfalls     = modules.get("pitfalls", [])

        objectives     = research_brief.learning_objectives or [
            f"Explain advanced concepts in {topic}.",
            f"Apply {topic} methods to real problems.",
            f"Evaluate risks and ethics in {topic} systems.",
        ]
        prerequisites  = research_brief.prerequisite_topics or ["Statistics", "Programming", "Data literacy"]
        case_studies   = research_brief.case_studies or [f"Case: {topic} in high-stakes decision support."]
        labs           = research_brief.lab_exercises or [f"Lab: build and critique a {topic} workflow."]
        misconceptions = research_brief.misconceptions or [f"{topic} is a universal solution for every context."]

        self.add_title_slide(f"{course_title}: {topic}", author)

        self.add_section_slide("Overview", [
            f"Deep dive into {topic}",
            "Foundations, methods, applications, deployment, and ethics",
            f"Evidence quality: {research_brief.citation_confidence} confidence (score {research_brief.source_score:.2f})",
            "Designed for undergraduate instruction with discussion and labs",
        ])

        # Guiding question responses — one slide per question
        gqr = getattr(research_brief, "guiding_question_responses", [])
        if gqr:
            self._build_section_divider("Research Findings", [
                f"Answers to {len(gqr)} guiding question{'s' if len(gqr) != 1 else ''}",
            ])
            for item in gqr:
                self.add_guiding_question_slide(
                    question=item.get("question", ""),
                    response=item.get("response", ""),
                )

        self.add_section_slide("Learning Objectives", objectives[:5])
        self.add_section_slide("Prerequisites", prerequisites[:5])
        self.add_section_slide("Course Roadmap", [
            "Module 1: Foundations and conceptual framing",
            "Module 2: Methods, modeling, and evaluation",
            "Module 3: Deployment, risk, ethics, and governance",
            "Capstone: discussion lab and case analysis",
        ])

        # Foundations
        self.add_section_slide("Part 1: Foundations", foundations or [f"Foundational framing for {topic}"])
        tp = research_brief.talking_points
        self.add_section_slide("Core Concepts & Definitions", [
            tp[0] if len(tp) > 0 else f"What is {topic}?",
            tp[1] if len(tp) > 1 else "Scope, assumptions, and boundary conditions",
        ])
        self.add_section_slide("Key Insights", [
            tp[2] if len(tp) > 2 else f"Mechanisms and methods in {topic}",
            tp[3] if len(tp) > 3 else "Evidence from research and practice",
        ])
        self.add_section_slide("Historical & Theoretical Foundations", [
            tp[4] if len(tp) > 4 else f"Historical development of {topic}",
            tp[5] if len(tp) > 5 else "Key milestones and paradigm shifts",
            "Competing schools of thought and trade-offs",
        ])

        # Methods and evaluation
        self.add_section_slide("Part 2: Methods and Modeling", methods or ["Method selection and modeling strategy"])
        self.add_section_slide("Model Development Workflow", [
            "Problem framing and target definition",
            "Data preparation and feature engineering",
            "Model training, tuning, and validation",
            "Error analysis and iterative refinement",
        ])
        self.add_section_slide("Evaluation Strategy", evaluation or [
            "Metric selection based on decision context",
            "Validation design and uncertainty quantification",
            "Robustness checks under shift and noise",
        ])

        # Applications
        self.add_section_slide("Part 3: Practical Applications", applications or [
            f"Applied use cases for {topic}",
            "Operational constraints and implementation choices",
            "Outcome measurement and business alignment",
        ])
        self.add_section_slide("Application Domains", [
            f"{topic} in industry and business",
            f"{topic} in public-sector and social-impact contexts",
            f"{topic} in research and academia",
            "Emerging cross-domain applications",
        ])

        for idx, case in enumerate(case_studies[:3], start=1):
            self.add_section_slide(f"Case Study {idx}", [
                case,
                "Problem context and success criteria",
                "Approach, trade-offs, and implementation details",
                "Outcomes, limitations, and transferable lessons",
            ])

        self.add_section_slide("Scaling & Implementation Considerations", [
            "Moving from prototype to production safely",
            "Infrastructure, latency, and reliability targets",
            "Cost-performance trade-offs and service levels",
            "Organizational adoption and workflow change",
        ])

        # Deployment and operations
        self.add_section_slide("Part 4: Deployment and Monitoring", deployment or [
            "Monitoring, drift detection, and retraining policy",
            "Incident response and rollback strategy",
            "Documentation and model lifecycle governance",
        ])
        self.add_section_slide("Monitoring Playbook", [
            "Data quality checks and schema contracts",
            "Performance dashboards and alert thresholds",
            "Fairness and calibration audits",
            "Change management and sign-off workflow",
        ])

        # Ethics
        self.add_section_slide("Part 5: Ethical & Social Implications", [
            f"Responsibility in deploying {topic}",
            *(ethics[:3] if ethics else ["Fairness and accountability", "Stakeholder impact assessment", "Governance controls"]),
        ])
        self.add_section_slide("Ethical Considerations", [
            research_brief.discussion_questions[0],
            "Who benefits and who bears the risks?",
            "Bias, fairness, and representation impacts",
            "Regulatory obligations and policy alignment",
        ])
        self.add_section_slide("Accountability & Transparency", [
            "Explainability and interpretability requirements by stakeholder",
            "Audit trails and reproducibility",
            "Communicating uncertainty and limitations",
            "Human oversight and intervention policy",
        ])

        # Pitfalls
        self.add_section_slide("Part 6: Common Pitfalls & Misconceptions", [
            f"What goes wrong when applying {topic}",
            *(pitfalls[:3] if pitfalls else ["Misconceptions and unrealistic expectations", "Failure modes", "Resilience strategies"]),
        ])
        self.add_section_slide("Common Misconceptions", misconceptions[:4])
        self.add_section_slide("Failure Modes & Pitfalls", [
            "Technical pitfalls (performance, scalability, etc.)",
            "Data quality and representation issues",
            "Integration challenges and system complexity",
            "Human factors and adoption barriers",
        ])
        self.add_section_slide("Building Robust Systems", [
            "Testing and validation strategies",
            "Monitoring and adaptation frameworks",
            "Contingency planning and fallback mechanisms",
            "Learning from failures and continuous improvement",
        ])

        # Lab and discussion
        self.add_section_slide("Discussion Lab Setup", [
            "Split class into critique teams: model, data, and governance",
            "Assign one case scenario and one risk register template",
            "Require evidence-backed recommendations with trade-offs",
            "Debrief with rubric: accuracy, ethics, and operational feasibility",
        ])
        self.add_section_slide("Hands-on Exercises", labs[:4])

        # Wrap-up
        self.add_section_slide("Key Takeaways", [
            f"The landscape of {topic} continues to evolve rapidly",
            "Effective practitioners combine foundations with ethical awareness",
            "Learning from successes and failures accelerates expertise",
            "The importance of interdisciplinary collaboration",
        ])
        self.add_section_slide("Discussion & Reflection", [
            research_brief.discussion_questions[1],
            "What challenges might you face applying this material?",
            "How would you approach teaching this to stakeholders?",
            "Where do you want to deepen your knowledge?",
        ])
        self.add_section_slide("Capstone Prompt", [
            research_brief.discussion_questions[2],
            "Design a deployment plan with metrics, governance, and rollback criteria.",
            "Defend trade-offs across performance, interpretability, and equity.",
            "Present assumptions and uncertainty clearly to non-technical stakeholders.",
        ])
        self.add_section_slide("Recommended Next Steps", [
            "Further reading and academic resources",
            "Hands-on practice opportunities",
            "Community engagement and networking",
            "Staying current with developments in the field",
        ])

        self.add_references_slide(research_brief)

    def build_deck(self, course_title: str, topics: List[str], source_summaries: List[str],
                   research_briefs: Optional[List[TopicResearchBrief]] = None):
        """Legacy method for backward compatibility."""
        self.add_title_slide(course_title)
        self.add_section_slide("Course Overview", [
            "3-hour session split into modules",
            f"Core topics: {', '.join(topics)}",
            "Interactive lecture with researched talking points and discussion prompts",
        ])

        brief_by_topic = {brief.topic: brief for brief in (research_briefs or [])}

        for idx, topic in enumerate(topics, start=1):
            bullets = [
                f"What is {topic}?",
                f"Key concepts for {topic} from course materials",
                "Applied examples and practice problems",
                "Transition into evidence-based discussion prompts",
            ]
            self.add_section_slide(f"Module {idx}: {topic}", bullets)

            brief = brief_by_topic.get(topic)
            if brief:
                self.add_topic_research_slides(idx, brief)

        self.add_section_slide("Source Content Summary", source_summaries[:6] or ["No source content identified."])

        if research_briefs:
            self.add_references_slide(research_briefs[0])
