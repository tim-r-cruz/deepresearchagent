from __future__ import annotations

import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import re
from urllib.parse import quote
from urllib.parse import urlparse

import requests

from src.llm_enrichment import enrich_with_llm

WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
WIKIPEDIA_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
DUCKDUCKGO_INSTANT_ANSWER_URL = "https://api.duckduckgo.com/"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"
REQUEST_TIMEOUT_SECONDS = 8
TAVILY_TIMEOUT_SECONDS = 20  # advanced search takes longer
REQUEST_HEADERS = {
    "User-Agent": "CourseDeckAgent/1.0 (educational workflow)",
    "Accept": "application/json",
}


@dataclass
class Citation:
    title: str
    url: str
    snippet: str
    source: str
    reliability_score: float
    relevance_score: float
    citation_confidence: str

    @property
    def weighted_score(self) -> float:
        return round((self.reliability_score * 0.6) + (self.relevance_score * 0.4), 2)


@dataclass
class TopicResearchBrief:
    topic: str
    summary: str
    talking_points: List[str]
    discussion_questions: List[str]
    learning_objectives: List[str] = field(default_factory=list)
    prerequisite_topics: List[str] = field(default_factory=list)
    curriculum_modules: Dict[str, List[str]] = field(default_factory=dict)
    case_studies: List[str] = field(default_factory=list)
    lab_exercises: List[str] = field(default_factory=list)
    misconceptions: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    source_score: float = 0.0
    citation_confidence: str = "Low"
    guiding_questions: List[str] = field(default_factory=list)
    guiding_question_responses: List[Dict] = field(default_factory=list)
    llm_enriched: bool = False


def research_topics(
    topics: List[str],
    course_content: Optional[List[Dict]] = None,
    guiding_questions: Optional[List[str]] = None,
    on_status=None,
) -> List[TopicResearchBrief]:
    briefs: List[TopicResearchBrief] = []
    for topic in topics:
        briefs.append(_research_single_topic(
            topic,
            course_content=course_content,
            guiding_questions=guiding_questions,
            on_status=on_status,
        ))
    return briefs


def _research_single_topic(
    topic: str,
    course_content: Optional[List[Dict]] = None,
    guiding_questions: Optional[List[str]] = None,
    on_status=None,
) -> TopicResearchBrief:
    encoded_topic = quote(topic.replace(" ", "_"))
    wikipedia_url = WIKIPEDIA_SUMMARY_URL.format(topic=encoded_topic)
    citations: List[Citation] = []

    use_tavily = bool(os.environ.get("TAVILY_API_KEY"))

    if on_status:
        on_status("Searching the web…")

    if use_tavily:
        print(f"[topic_research] Using Tavily + Wikipedia for {topic!r}", file=sys.stderr, flush=True)
        with ThreadPoolExecutor(max_workers=2) as executor:
            tavily_future = executor.submit(_fetch_tavily_citations, topic)
            wiki_future   = executor.submit(_fetch_wikipedia_citation, topic)
            try:
                citations.extend(tavily_future.result())
            except Exception as exc:
                print(f"[topic_research] Tavily fetch failed: {exc}", file=sys.stderr, flush=True)
            try:
                result = wiki_future.result()
                if result:
                    citations.append(result)
            except Exception:
                pass
    else:
        print(f"[topic_research] TAVILY_API_KEY not set — using Wikipedia + DuckDuckGo for {topic!r}", file=sys.stderr, flush=True)
        with ThreadPoolExecutor(max_workers=2) as executor:
            wiki_future = executor.submit(_fetch_wikipedia_citation, topic)
            ddg_future  = executor.submit(_fetch_duckduckgo_citations, topic)
            try:
                result = wiki_future.result()
                if result:
                    citations.append(result)
            except Exception:
                pass
            try:
                citations.extend(ddg_future.result())
            except Exception:
                pass

    local_citations = _build_local_citations(topic=topic, course_content=course_content)
    citations.extend(local_citations)

    if not citations:
        # Still try the LLM even without web citations
        if on_status:
            on_status("Running LLM enrichment…")
        course_text = _extract_course_text(course_content)
        llm_data = enrich_with_llm(
            topic=topic,
            guiding_questions=guiding_questions or [],
            context_snippets=[],
            course_text=course_text,
        )
        if llm_data:
            return TopicResearchBrief(
                topic=topic,
                summary=llm_data["summary"],
                talking_points=llm_data["talking_points"],
                discussion_questions=llm_data["discussion_questions"],
                learning_objectives=llm_data["learning_objectives"],
                prerequisite_topics=llm_data["prerequisite_topics"],
                curriculum_modules=llm_data["curriculum_modules"],
                case_studies=llm_data["case_studies"],
                lab_exercises=llm_data["lab_exercises"],
                misconceptions=llm_data["misconceptions"],
                sources=[wikipedia_url, "local://instructional-framework"],
                citations=[],
                source_score=0.25,
                citation_confidence="Low",
                guiding_questions=guiding_questions or [],
                guiding_question_responses=llm_data.get("guiding_question_responses", []),
                llm_enriched=True,
            )

        # Final fallback — pure templates
        print(f"[topic_research] WARNING: LLM unavailable for {topic!r} — using templates", file=sys.stderr, flush=True)
        fallback_summary = (
            f"No external references were retrieved for {topic}. "
            f"Use this module to frame key definitions, methods, and applied examples for {topic}."
        )
        fallback_discussion = _build_discussion_questions(topic, fallback_summary, guiding_questions)
        return TopicResearchBrief(
            topic=topic,
            summary=fallback_summary,
            talking_points=[
                f"Define the conceptual boundaries and vocabulary of {topic}.",
                f"Compare at least two approaches or frameworks used in {topic}.",
                f"Evaluate one real scenario where applying {topic} changes outcomes.",
            ],
            discussion_questions=fallback_discussion,
            learning_objectives=[
                f"Explain foundational concepts in {topic}.",
                f"Apply core methods from {topic} to practical examples.",
                f"Critique real-world decisions involving {topic} using evidence.",
            ],
            prerequisite_topics=["Basic statistics", "Introductory programming", "Data literacy"],
            curriculum_modules={
                "foundations": [f"Core definitions of {topic}", f"Historical evolution of {topic}"],
                "methods": [f"Method families used in {topic}", "Model selection principles"],
                "applications": ["Industry use cases", "Operational constraints and trade-offs"],
                "evaluation": ["Performance metrics", "Validation and error analysis"],
                "deployment": ["Monitoring and drift", "Reliability in production"],
                "ethics": ["Fairness and accountability", "Transparency and governance"],
                "pitfalls": ["Overfitting and leakage", "Misaligned objectives"],
            },
            case_studies=[
                f"Case study: implementing {topic} for high-stakes decisions.",
                f"Case study: failure analysis in a {topic} deployment.",
            ],
            lab_exercises=[
                f"Lab: compare two {topic} approaches on the same dataset.",
                "Lab: diagnose model errors and propose remediations.",
            ],
            misconceptions=[
                f"Misconception: {topic} works equally well across all contexts.",
                "Misconception: higher complexity always means better performance.",
            ],
            sources=[wikipedia_url, "local://instructional-framework"],
            citations=[],
            source_score=0.25,
            citation_confidence="Low",
            guiding_questions=guiding_questions or [],
        )

    source_score = _calculate_source_score(citations)
    confidence = _confidence_bucket(source_score)

    # ── LLM enrichment ────────────────────────────────────────────────────────
    context_snippets = [c.snippet for c in citations if c.snippet]
    if on_status:
        on_status("Running LLM enrichment…")
    course_text = _extract_course_text(course_content)
    llm_data = enrich_with_llm(
        topic=topic,
        guiding_questions=guiding_questions or [],
        context_snippets=context_snippets,
        course_text=course_text,
    )

    if llm_data:
        return TopicResearchBrief(
            topic=topic,
            summary=llm_data["summary"],
            talking_points=llm_data["talking_points"],
            discussion_questions=llm_data["discussion_questions"],
            learning_objectives=llm_data["learning_objectives"],
            prerequisite_topics=llm_data["prerequisite_topics"],
            curriculum_modules=llm_data["curriculum_modules"],
            case_studies=llm_data["case_studies"],
            lab_exercises=llm_data["lab_exercises"],
            misconceptions=llm_data["misconceptions"],
            sources=[citation.url for citation in citations],
            citations=citations,
            source_score=source_score,
            citation_confidence=confidence,
            guiding_questions=guiding_questions or [],
            guiding_question_responses=llm_data.get("guiding_question_responses", []),
            llm_enriched=True,
        )

    # ── Fallback: template-based generation ───────────────────────────────────
    print(f"[topic_research] WARNING: LLM unavailable for {topic!r} — using templates", file=sys.stderr, flush=True)
    aggregate_summary = _build_aggregate_summary(topic, citations)
    talking_points = _build_talking_points(topic, aggregate_summary)
    discussion_questions = _build_discussion_questions(topic, aggregate_summary, guiding_questions)
    learning_objectives = _build_learning_objectives(topic, talking_points, citations)
    prerequisite_topics = _build_prerequisites(topic, citations)
    curriculum_modules = _build_curriculum_modules(topic, citations, aggregate_summary)
    case_studies = _build_case_studies(topic, citations)
    lab_exercises = _build_lab_exercises(topic, citations)
    misconceptions = _build_misconceptions(topic, citations)

    return TopicResearchBrief(
        topic=topic,
        summary=aggregate_summary,
        talking_points=talking_points,
        discussion_questions=discussion_questions,
        learning_objectives=learning_objectives,
        prerequisite_topics=prerequisite_topics,
        curriculum_modules=curriculum_modules,
        case_studies=case_studies,
        lab_exercises=lab_exercises,
        misconceptions=misconceptions,
        sources=[citation.url for citation in citations],
        citations=citations,
        source_score=source_score,
        citation_confidence=confidence,
        guiding_questions=guiding_questions or [],
    )


def _fetch_tavily_citations(topic: str) -> List[Citation]:
    """Call Tavily Search API for rich, AI-optimised web results."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return []

    try:
        response = requests.post(
            TAVILY_SEARCH_URL,
            json={
                "api_key": api_key,
                "query": topic,
                "search_depth": "advanced",
                "max_results": 5,
                "include_answer": True,
            },
            headers={"Content-Type": "application/json"},
            timeout=TAVILY_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print(f"[topic_research] Tavily request error: {exc}", file=sys.stderr, flush=True)
        return []

    citations: List[Citation] = []

    # Tavily's synthesised answer is a high-quality context snippet
    answer = (payload.get("answer") or "").strip()
    if answer:
        citations.append(_build_citation(
            topic=topic,
            title=f"Tavily synthesis: {topic}",
            url="https://tavily.com",
            snippet=answer,
            source="tavily-answer",
        ))

    for result in (payload.get("results") or []):
        title   = (result.get("title") or "").strip()
        url     = (result.get("url") or "").strip()
        content = (result.get("content") or "").strip()
        if not content or not url:
            continue
        citations.append(_build_citation(
            topic=topic,
            title=title or url,
            url=url,
            snippet=content,
            source="tavily",
        ))

    print(f"[topic_research] Tavily returned {len(citations)} citations for {topic!r}", file=sys.stderr, flush=True)
    return citations


def _fetch_wikipedia_citation(topic: str) -> Citation | None:
    candidate_titles = [topic, topic.replace("-", " ").strip()]

    search_response = _http_get(
        WIKIPEDIA_SEARCH_URL,
        params={
            "action": "query",
            "list": "search",
            "srsearch": topic,
            "format": "json",
            "utf8": "1",
        },
    )
    search_payload = search_response.json()
    search_hits = search_payload.get("query", {}).get("search", [])
    if search_hits:
        candidate_titles.append(search_hits[0].get("title", topic))

    for candidate in candidate_titles:
        if not candidate:
            continue
        encoded_topic = quote(candidate.replace(" ", "_"))
        source_url = WIKIPEDIA_SUMMARY_URL.format(topic=encoded_topic)
        try:
            response = _http_get(source_url)
            payload = response.json()
            summary = (payload.get("extract") or "").strip()
            canonical_url = payload.get("content_urls", {}).get("desktop", {}).get("page", source_url)
            if not summary:
                continue

            return _build_citation(
                topic=topic,
                title=payload.get("title") or candidate,
                url=canonical_url,
                snippet=summary,
                source="wikipedia",
            )
        except requests.RequestException:
            continue

    return None


def _fetch_duckduckgo_citations(topic: str) -> List[Citation]:
    params = {
        "q": topic,
        "format": "json",
        "no_redirect": "1",
        "no_html": "1",
    }
    response = _http_get(DUCKDUCKGO_INSTANT_ANSWER_URL, params=params)
    response.raise_for_status()
    payload = response.json()

    citations: List[Citation] = []
    abstract = (payload.get("AbstractText") or "").strip()
    abstract_url = (payload.get("AbstractURL") or "").strip()
    heading = (payload.get("Heading") or topic).strip()
    if abstract and abstract_url:
        citations.append(
            _build_citation(
                topic=topic,
                title=heading,
                url=abstract_url,
                snippet=abstract,
                source="duckduckgo-abstract",
            )
        )

    related_topics = payload.get("RelatedTopics") or []
    for entry in related_topics:
        if not isinstance(entry, dict):
            continue
        text = (entry.get("Text") or "").strip()
        url = (entry.get("FirstURL") or "").strip()
        if not text or not url:
            continue
        citations.append(
            _build_citation(
                topic=topic,
                title=text.split(" - ")[0][:100],
                url=url,
                snippet=text,
                source="duckduckgo-related",
            )
        )
        if len(citations) >= 4:
            break

    return citations


def _build_local_citations(topic: str, course_content: Optional[List[Dict]]) -> List[Citation]:
    if not course_content:
        return []

    topic_words = [word.lower() for word in topic.split() if word.strip()]
    citations: List[Citation] = []
    for item in course_content:
        name = str(item.get("name") or "course-content")
        body = str(item.get("body") or "")
        if not body.strip():
            continue

        matched_sentences: List[str] = []
        for sentence in _split_sentences(body):
            lowered = sentence.lower()
            if any(word in lowered for word in topic_words):
                matched_sentences.append(sentence)
            if len(matched_sentences) >= 2:
                break

        if not matched_sentences:
            fallback_sentence = _split_sentences(body[:450])
            if fallback_sentence:
                matched_sentences = [fallback_sentence[0]]

        for sentence in matched_sentences:
            citations.append(
                _build_citation(
                    topic=topic,
                    title=name,
                    url=f"local://{name}",
                    snippet=sentence,
                    source="local-course",
                )
            )

    citations.sort(key=lambda citation: citation.weighted_score, reverse=True)
    return citations[:4]


def _build_citation(topic: str, title: str, url: str, snippet: str, source: str) -> Citation:
    reliability = _score_reliability(url=url, source=source)
    relevance = _score_relevance(topic=topic, title=title, snippet=snippet)
    weighted = (reliability * 0.6) + (relevance * 0.4)
    return Citation(
        title=title,
        url=url,
        snippet=snippet,
        source=source,
        reliability_score=reliability,
        relevance_score=relevance,
        citation_confidence=_confidence_bucket(round(weighted, 2)),
    )


def _build_aggregate_summary(topic: str, citations: List[Citation]) -> str:
    sorted_citations = sorted(citations, key=lambda citation: citation.weighted_score, reverse=True)
    top_snippets = [citation.snippet for citation in sorted_citations[:3] if citation.snippet]

    if not top_snippets:
        return f"No high-quality snippets were retrieved for {topic}."

    merged = " ".join(top_snippets)
    return merged[:700]


def _build_learning_objectives(topic: str, talking_points: List[str], citations: List[Citation]) -> List[str]:
    top_titles = [citation.title for citation in _top_citations(citations, 2)]
    objectives = [
        f"Explain the core concepts and vocabulary of {topic} with precision.",
        f"Analyze real use cases of {topic} and justify method choices using evidence.",
        f"Evaluate trade-offs in {topic} across performance, interpretability, and risk.",
    ]
    if top_titles:
        objectives.append(f"Synthesize insights from: {', '.join(top_titles)}.")
    if talking_points:
        objectives.append(f"Connect theory to practice through: {talking_points[0][:90]}.")
    return objectives[:5]


def _build_prerequisites(topic: str, citations: List[Citation]) -> List[str]:
    keywords = _extract_keywords(" ".join(citation.snippet for citation in citations), 6)
    base = ["Probability and statistics", "Data preprocessing", "Python programming"]
    if keywords:
        base.append(f"Concept familiarity: {', '.join(keywords[:3])}")
    return base[:4]


def _build_curriculum_modules(topic: str, citations: List[Citation], summary: str) -> Dict[str, List[str]]:
    key_sentences = _split_sentences(summary)
    key_terms = _extract_keywords(summary + " " + " ".join(c.title for c in citations), 10)

    modules: Dict[str, List[str]] = {
        "foundations": [
            f"Define {topic} and its scope.",
            key_sentences[0] if key_sentences else f"Position {topic} in the broader analytics ecosystem.",
            f"Key terms: {', '.join(key_terms[:4])}" if key_terms else "Key terms and conceptual map.",
        ],
        "methods": [
            f"Method families commonly used in {topic}.",
            "Feature engineering, model selection, and hyperparameter tuning.",
            "Balancing bias-variance trade-offs in practice.",
        ],
        "applications": [
            f"High-value applications of {topic} in industry and public sector.",
            "Decision support workflows and operational constraints.",
            "Impact measurement and KPI alignment.",
        ],
        "evaluation": [
            "Metric selection for classification/regression and ranking tasks.",
            "Cross-validation, calibration, and error decomposition.",
            "Robustness testing under distribution shift.",
        ],
        "deployment": [
            "Serving architecture and model monitoring.",
            "Data drift detection and retraining policy.",
            "Reliability, latency, and cost trade-offs.",
        ],
        "ethics": [
            "Fairness assessment and stakeholder impact.",
            "Transparency, explainability, and accountability design.",
            "Governance, policy, and risk controls.",
        ],
        "pitfalls": [
            "Data leakage, spurious correlations, and shortcut learning.",
            "Overfitting and poor generalization to new cohorts.",
            "Misalignment between technical metrics and business outcomes.",
        ],
    }
    return modules


def _build_case_studies(topic: str, citations: List[Citation]) -> List[str]:
    studies: List[str] = []
    for citation in _top_citations(citations, 3):
        studies.append(f"{citation.title}: {citation.snippet[:140]}")
    if not studies:
        studies.append(f"Case: decision-making workflow improved using {topic}.")
    return studies


def _build_lab_exercises(topic: str, citations: List[Citation]) -> List[str]:
    terms = _extract_keywords(" ".join(c.snippet for c in citations), 5)
    term_text = ", ".join(terms[:3]) if terms else "model quality, risk, and interpretability"
    return [
        f"Lab 1: build a baseline {topic} pipeline and report metrics.",
        f"Lab 2: stress-test model behavior under data shift ({term_text}).",
        "Lab 3: present a model card with fairness and monitoring recommendations.",
    ]


def _build_misconceptions(topic: str, citations: List[Citation]) -> List[str]:
    examples = [
        f"{topic} automatically removes the need for domain expertise.",
        "A higher accuracy score always means better business outcomes.",
        "One model configuration will remain optimal as data evolves.",
    ]
    if citations:
        examples.append(f"Reliance on a single source such as '{citations[0].title}' is sufficient evidence.")
    return examples[:4]


def _top_citations(citations: List[Citation], limit: int) -> List[Citation]:
    return sorted(citations, key=lambda citation: citation.weighted_score, reverse=True)[:limit]


def _extract_keywords(text: str, limit: int) -> List[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", text.lower())
    stopwords = {
        "about", "after", "also", "analytics", "because", "being", "between", "could", "course",
        "data", "from", "have", "into", "learning", "local", "more", "most", "other", "predictive",
        "should", "than", "that", "their", "there", "these", "those", "topic", "under", "using",
        "with", "what", "when", "where", "which", "while", "would", "your", "machine",
    }
    words = [token for token in tokens if token not in stopwords]
    counts = Counter(words)
    return [word for word, _ in counts.most_common(limit)]


def _calculate_source_score(citations: List[Citation]) -> float:
    if not citations:
        return 0.0
    total = sum(citation.weighted_score for citation in citations)
    return round(total / len(citations), 2)


def _score_reliability(url: str, source: str) -> float:
    if source == "tavily-answer":
        return 0.90  # synthesised from multiple sources
    if source == "tavily":
        return 0.82
    if source == "wikipedia":
        return 0.85
    if source == "local-course":
        return 0.78

    hostname = urlparse(url).hostname or ""
    if hostname.endswith(".gov"):
        return 0.95
    if hostname.endswith(".edu"):
        return 0.92
    if hostname.endswith(".org"):
        return 0.82
    if hostname.endswith(".com"):
        return 0.72
    return 0.68


def _score_relevance(topic: str, title: str, snippet: str) -> float:
    content = f"{title} {snippet}".lower()
    words = [word for word in topic.lower().split() if word]
    if not words:
        return 0.5

    hits = sum(1 for word in words if word in content)
    coverage = hits / len(words)
    depth_bonus = 0.1 if len(snippet) > 120 else 0.0
    return round(min(1.0, 0.55 + (coverage * 0.35) + depth_bonus), 2)


def _confidence_bucket(score: float) -> str:
    if score >= 0.8:
        return "High"
    if score >= 0.65:
        return "Medium"
    return "Low"


def _http_get(url: str, params: Optional[Dict[str, str]] = None) -> requests.Response:
    response = requests.get(
        url,
        params=params,
        headers=REQUEST_HEADERS,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response


def _build_talking_points(topic: str, summary: str) -> List[str]:
    sentences = _split_sentences(summary)
    points = []
    for sentence in sentences[:3]:
        points.append(sentence)

    if len(points) < 3:
        points.extend([
            f"Historical development and major milestones in {topic}.",
            f"Common misconceptions students have about {topic}.",
            f"How {topic} appears in professional or community practice.",
        ])

    return points[:3]


def _build_discussion_questions(
    topic: str, summary: str, guiding_questions: Optional[List[str]] = None
) -> List[str]:
    if guiding_questions:
        clean = [q.strip() for q in guiding_questions if q.strip()]
        if clean:
            # Use the user's guiding questions directly, pad to 3 if needed
            result = clean[:3]
            if len(result) < 3:
                result.append(f"What is one ethical or social implication of decisions in {topic}?")
            if len(result) < 3:
                result.append(f"How would you teach {topic} differently for beginners versus advanced learners?")
            return result[:3]

    sentences = _split_sentences(summary)
    anchor = sentences[0] if sentences else f"the current framing of {topic}"
    return [
        f"Which part of '{anchor[:120]}' would you challenge, and why?",
        f"What is one ethical or social implication of decisions in {topic}?",
        f"How would you teach {topic} differently for beginners versus advanced learners?",
    ]


def _extract_course_text(course_content: Optional[List[Dict]]) -> Optional[str]:
    """Concatenate body text from all uploaded course files into one string."""
    if not course_content:
        return None
    parts = [str(item.get("body") or "").strip() for item in course_content]
    combined = "\n\n".join(p for p in parts if p)
    return combined if combined else None


def _split_sentences(text: str) -> List[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    parts = []
    current = []
    for char in cleaned:
        current.append(char)
        if char in ".!?":
            sentence = "".join(current).strip()
            if sentence:
                parts.append(sentence)
            current = []

    if current:
        trailing = "".join(current).strip()
        if trailing:
            parts.append(trailing)

    return parts
