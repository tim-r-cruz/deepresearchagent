"""LLM enrichment — calls Anthropic Claude to produce rich, substantive research content."""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

try:
    import anthropic as _anthropic_module
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 50000


def enrich_with_llm(
    topic: str,
    guiding_questions: List[str],
    context_snippets: List[str],
    course_text: Optional[str] = None,
) -> Optional[Dict]:
    """
    Call Anthropic Claude to generate an enriched research brief.

    Returns a dict whose keys map to ``TopicResearchBrief`` fields,
    or ``None`` when the SDK is unavailable or the API call fails after retries.
    """
    import sys

    if not _ANTHROPIC_AVAILABLE:
        print("[llm_enrichment] anthropic SDK not installed — skipping LLM", file=sys.stderr, flush=True)
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[llm_enrichment] ANTHROPIC_API_KEY not set — skipping LLM", file=sys.stderr, flush=True)
        return None

    client = _anthropic_module.Anthropic(api_key=api_key)
    prompt = _build_prompt(topic, guiding_questions, context_snippets, course_text)

    for attempt in range(1, 3):  # try up to twice
        print(f"[llm_enrichment] attempt {attempt}: calling {MODEL} topic={topic!r}", file=sys.stderr, flush=True)
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            print(f"[llm_enrichment] attempt {attempt}: stop_reason={message.stop_reason} tokens={message.usage.output_tokens}", file=sys.stderr, flush=True)

            raw = message.content[0].text.strip()
            json_str = _extract_json(raw)
            if not json_str:
                print(f"[llm_enrichment] attempt {attempt}: could not extract JSON — retrying", file=sys.stderr, flush=True)
                continue

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"[llm_enrichment] attempt {attempt}: JSON parse error at pos {e.pos}: {e.msg} — retrying", file=sys.stderr, flush=True)
                continue

            result = _validate_and_normalise(data)
            print(f"[llm_enrichment] attempt {attempt}: OK gqr={len(result.get('guiding_question_responses', []))}", file=sys.stderr, flush=True)
            return result

        except Exception as exc:
            import traceback
            print(f"[llm_enrichment] attempt {attempt}: ERROR {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)

    print("[llm_enrichment] all attempts failed — falling back to templates", file=sys.stderr, flush=True)
    return None


# ── Prompt construction ───────────────────────────────────────────────────────

def _build_prompt(
    topic: str,
    guiding_questions: List[str],
    context_snippets: List[str],
    course_text: Optional[str],
) -> str:
    lines: List[str] = [
        "You are a subject-matter expert and curriculum designer. "
        "Your task is to produce a comprehensive, substantive research brief on the topic below.",
        "",
        "## Topic",
        topic,
    ]

    if guiding_questions:
        lines += [
            "",
            "## Guiding Questions",
            "The research must directly address these questions:",
        ]
        for q in guiding_questions:
            lines.append(f"- {q.strip()}")

    if context_snippets:
        combined = "\n\n".join(s.strip() for s in context_snippets[:6] if s.strip())
        if combined:
            lines += [
                "",
                "## Reference Snippets (from web sources — use as grounding context)",
                combined,
            ]

    if course_text and course_text.strip():
        excerpt = course_text.strip()[:3000]
        lines += [
            "",
            "## Uploaded Context Material (treat as authoritative for this brief)",
            excerpt,
        ]

    has_questions = bool(guiding_questions)

    lines += [
        "",
        "## Output Format",
        "Return ONLY a valid JSON object. No markdown fences. No text before or after the JSON.",
        "The object must contain exactly these keys:",
        "",
        "summary (string)",
        "  A substantive overview of 4–6 paragraphs. Separate paragraphs with \\n\\n.",
        "  Cover: what the topic is, why it matters, current state of knowledge, and key challenges.",
        "",
    ]

    if has_questions:
        lines += [
            "guiding_question_responses (array of objects)",
            "  One object per guiding question listed above. Each object has two string keys:",
            '    "question": copy the guiding question verbatim',
            '    "response": write a thorough expert answer of 2–4 paragraphs (separated by \\n\\n).',
            "      Cite specific evidence, named studies, mechanisms, or data.",
            "      Do NOT restate or paraphrase the question — just answer it deeply.",
            "      This must be the most substantial field in the output.",
            "",
        ]
    else:
        lines += [
            "guiding_question_responses (array): empty array []",
            "",
        ]

    lines += [
        "talking_points (array of 6–8 strings)",
        "  Each is a complete, expert-level sentence with specific detail. Not headings.",
        "",
        "discussion_questions (array of 4–6 strings)",
        "  Thought-provoking questions beyond the guiding questions. Not yes/no answerable.",
        "",
        "learning_objectives (array of 5 strings)",
        "  Specific, measurable objectives using Bloom's action verbs: analyse, evaluate, design, etc.",
        "",
        "prerequisite_topics (array of 4–5 strings)",
        "  Specific prerequisite topics or skills needed.",
        "",
        "curriculum_modules (object)",
        '  Keys: "foundations", "methods", "applications", "evaluation", "advanced"',
        "  Each key maps to an array of 3–4 specific content items.",
        "",
        "case_studies (array of 3–4 strings)",
        "  Specific, named real-world cases with concrete outcomes.",
        "",
        "lab_exercises (array of 3–4 strings)",
        "  Hands-on exercises with clear deliverables.",
        "",
        "misconceptions (array of 3–4 strings)",
        "  Each item: state the flawed belief, then explain why it is wrong.",
        "",
        "Every field must contain real, substantive content.",
    ]

    return "\n".join(lines)


# ── JSON extraction and validation ────────────────────────────────────────────

def _extract_json(text: str) -> Optional[str]:
    """Pull the first complete JSON object out of the model's response."""
    # Strip markdown code fences if present
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        candidate = fenced.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            return None
        candidate = text[start : end + 1]

    return _repair_json(candidate)


def _repair_json(s: str) -> str:
    """Fix common LLM JSON issues — primarily literal newlines inside string values."""
    # Replace literal newlines/tabs inside JSON strings with their escape sequences.
    # Strategy: iterate character by character, tracking whether we're inside a string.
    result = []
    in_string = False
    i = 0
    while i < len(s):
        ch = s[i]
        if in_string:
            if ch == "\\":
                # Escape sequence — pass through both chars
                result.append(ch)
                i += 1
                if i < len(s):
                    result.append(s[i])
            elif ch == '"':
                in_string = False
                result.append(ch)
            elif ch == "\n":
                result.append("\\n")
            elif ch == "\r":
                result.append("\\r")
            elif ch == "\t":
                result.append("\\t")
            else:
                result.append(ch)
        else:
            if ch == '"':
                in_string = True
                result.append(ch)
            else:
                result.append(ch)
        i += 1
    return "".join(result)


def _validate_and_normalise(data: Dict) -> Dict:
    """Ensure all expected keys exist and have the right types."""
    def _ensure_list(val, fallback: List) -> List:
        if isinstance(val, list) and val:
            return [str(i) for i in val]
        return fallback

    def _ensure_str(val, fallback: str) -> str:
        if isinstance(val, str) and val.strip():
            return val.strip()
        return fallback

    def _ensure_modules(val) -> Dict[str, List[str]]:
        if isinstance(val, dict):
            return {k: _ensure_list(v, []) for k, v in val.items()}
        return {}

    topic_placeholder = data.get("_topic", "this topic")

    # Validate guiding_question_responses: must be list of dicts with question+response strings
    raw_gqr = data.get("guiding_question_responses") or []
    gqr: list = []
    if isinstance(raw_gqr, list):
        for item in raw_gqr:
            if isinstance(item, dict):
                q = str(item.get("question") or "").strip()
                r = str(item.get("response") or "").strip()
                if q and r:
                    gqr.append({"question": q, "response": r})

    return {
        "summary": _ensure_str(
            data.get("summary"),
            f"An in-depth overview of {topic_placeholder}.",
        ),
        "guiding_question_responses": gqr,
        "talking_points": _ensure_list(
            data.get("talking_points"),
            [f"Key insight about {topic_placeholder}."],
        ),
        "discussion_questions": _ensure_list(
            data.get("discussion_questions"),
            [f"What are the most important considerations in {topic_placeholder}?"],
        ),
        "learning_objectives": _ensure_list(
            data.get("learning_objectives"),
            [f"Explain core concepts of {topic_placeholder}."],
        ),
        "prerequisite_topics": _ensure_list(
            data.get("prerequisite_topics"),
            ["Foundational domain knowledge"],
        ),
        "curriculum_modules": _ensure_modules(data.get("curriculum_modules")),
        "case_studies": _ensure_list(
            data.get("case_studies"),
            [f"Case study: applying {topic_placeholder} in practice."],
        ),
        "lab_exercises": _ensure_list(
            data.get("lab_exercises"),
            [f"Lab: explore {topic_placeholder} hands-on."],
        ),
        "misconceptions": _ensure_list(
            data.get("misconceptions"),
            [f"Misconception: {topic_placeholder} is simpler than it appears."],
        ),
    }
