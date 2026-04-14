import pathlib

from src.slide_deck_generator import SlideDeckGenerator
from src.topic_research import Citation, TopicResearchBrief


def test_build_research_deck(tmp_path):
    output_path = tmp_path / "course_deck.pptx"
    generator = SlideDeckGenerator(output_path)
    research_brief = TopicResearchBrief(
        topic="Machine Learning",
        summary="Machine learning is a subset of AI that learns patterns from data.",
        talking_points=[
            "Supervised learning uses labeled data for training",
            "Unsupervised learning discovers patterns in unlabeled data",
            "Reinforcement learning learns through interaction and rewards",
        ],
        discussion_questions=[
            "What are the ethical implications of predictive models?",
            "How do we detect and mitigate bias in ML systems?",
            "When should humans override automated decisions?",
        ],
        citations=[
            Citation(
                title="Machine Learning Overview",
                url="https://en.wikipedia.org/wiki/Machine_learning",
                snippet="Machine learning is the study of computer algorithms that learn from experience.",
                source="wikipedia",
                reliability_score=0.85,
                relevance_score=0.92,
                citation_confidence="High",
            )
        ],
        source_score=0.88,
        citation_confidence="High",
    )
    
    generator.build_research_deck(
        topic="Machine Learning",
        research_brief=research_brief,
        course_title="Advanced Topics",
        author="Dr. Smith"
    )
    generator.save()

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert len(generator.presentation.slides) >= 25
    first_slide_notes = generator.presentation.slides[0].notes_slide.notes_text_frame.text
    assert "Session launch:" in first_slide_notes
    assert "five minutes" in first_slide_notes


def test_legacy_build_deck_backwards_compat(tmp_path):
    output_path = tmp_path / "legacy_deck.pptx"
    generator = SlideDeckGenerator(output_path)
    research_briefs = [
        TopicResearchBrief(
            topic="Topic 1",
            summary="Topic 1 is explored in depth.",
            talking_points=["Point A", "Point B", "Point C"],
            discussion_questions=["Q1", "Q2", "Q3"],
            citations=[
                Citation(
                    title="Source 1",
                    url="https://example.org/1",
                    snippet="Example content.",
                    source="wikipedia",
                    reliability_score=0.85,
                    relevance_score=0.9,
                    citation_confidence="High",
                )
            ],
            source_score=0.88,
            citation_confidence="High",
        )
    ]
    
    generator.build_deck(
        course_title="Test Course",
        topics=["Topic 1"],
        source_summaries=["doc1: intro"],
        research_briefs=research_briefs,
    )
    generator.save()

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    legacy_notes = generator.presentation.slides[0].notes_slide.notes_text_frame.text
    assert "Session launch:" in legacy_notes
