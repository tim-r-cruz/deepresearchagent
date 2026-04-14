import pathlib
import tempfile

from src.agent import build_research_deck


def test_build_research_deck_cli_interface(tmp_path):
    """Test the CLI interface with a topic argument."""
    output_dir = tmp_path / "output"
    
    deck_path = build_research_deck(
        topic="Machine Learning",
        output_dir=output_dir,
        course_title="Advanced Topics",
        author="Dr. Test",
        content_dir=None,
    )
    
    assert deck_path.exists()
    assert deck_path.name == "Machine_Learning.pptx"
    assert output_dir.exists()


def test_build_research_deck_with_local_enrichment(tmp_path):
    """Test research with local content enrichment."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    
    # Create a sample content file
    sample_file = content_dir / "notes.txt"
    sample_file.write_text("Machine learning enables computers to learn patterns from data without explicit programming.")
    
    output_dir = tmp_path / "output"
    
    deck_path = build_research_deck(
        topic="Machine Learning",
        output_dir=output_dir,
        course_title="Applied ML",
        author="Prof. Smith",
        content_dir=content_dir,
    )
    
    assert deck_path.exists()
    assert len(deck_path.name) > 0
