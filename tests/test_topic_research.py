import requests

from src.topic_research import TopicResearchBrief, _build_discussion_questions, _build_talking_points, research_topics


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_research_topics_success(monkeypatch):
    wiki_payload = {
        "title": "Systems Thinking",
        "extract": "Topic summary sentence one. Topic summary sentence two. Topic summary sentence three.",
        "content_urls": {
            "desktop": {
                "page": "https://example.org/topic"
            }
        },
    }
    ddg_payload = {
        "AbstractText": "Systems thinking studies interdependent elements and feedback loops.",
        "AbstractURL": "https://www.britannica.com/topic/systems-theory",
        "Heading": "Systems Thinking",
        "RelatedTopics": [
            {
                "Text": "Feedback - Process where outputs loop back as inputs.",
                "FirstURL": "https://en.wikipedia.org/wiki/Feedback",
            }
        ],
    }

    def _fake_get(url, *args, **kwargs):
        if "wikipedia.org" in url:
            return _FakeResponse(wiki_payload)
        if "duckduckgo.com" in url:
            return _FakeResponse(ddg_payload)
        raise AssertionError("Unexpected URL")

    monkeypatch.setattr("src.topic_research.requests.get", _fake_get)
    briefs = research_topics(["Systems Thinking"])

    assert len(briefs) == 1
    assert isinstance(briefs[0], TopicResearchBrief)
    assert briefs[0].topic == "Systems Thinking"
    assert len(briefs[0].sources) >= 2
    assert len(briefs[0].citations) >= 2
    assert briefs[0].source_score > 0
    assert briefs[0].citation_confidence in {"Low", "Medium", "High"}
    assert len(briefs[0].talking_points) == 3
    assert len(briefs[0].discussion_questions) == 3
    assert briefs[0].sources[0] == "https://example.org/topic"


def test_research_topics_fallback_when_all_sources_fail(monkeypatch):
    def _raise_get(*args, **kwargs):
        raise requests.RequestException("network error")

    monkeypatch.setattr("src.topic_research.requests.get", _raise_get)
    content_items = [
        {
            "name": "ethics_notes",
            "body": "Data ethics examines fairness, accountability, transparency, and social impact in model design.",
        }
    ]
    brief = research_topics(["Data Ethics"], course_content=content_items)[0]

    assert brief.source_score >= 0.65
    assert brief.citation_confidence in {"Medium", "High"}
    assert len(brief.citations) >= 1
    assert "unavailable" not in brief.summary.lower()


def test_build_helpers_return_expected_lengths():
    summary = "First sentence. Second sentence. Third sentence."
    points = _build_talking_points("Critical Thinking", summary)
    questions = _build_discussion_questions("Critical Thinking", summary)

    assert len(points) == 3
    assert len(questions) == 3
