import argparse
import pathlib
import sys
from typing import Optional

from src.course_parser import load_course_content
from src.slide_deck_generator import SlideDeckGenerator
from src.topic_research import research_topics
from src.config import DEFAULT_OUTPUT_DIR


def build_research_deck(topic: str, output_dir: pathlib.Path, course_title: str, author: str, content_dir: Optional[pathlib.Path] = None):
    """Conduct deep research on a topic and generate an undergraduate course slide deck."""
    print(f"Conducting deep research on: {topic}")
    
    course_content = []
    if content_dir and content_dir.exists():
        print(f"  Enriching with local materials from: {content_dir}")
        try:
            course_content = load_course_content(content_dir)
        except Exception as e:
            print(f"  Warning: could not load local content: {e}")
    
    print("  Researching foundations, applications, ethics, and pitfalls...")
    research_brief = research_topics([topic], course_content=course_content if course_content else None)[0]
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{topic.replace(' ', '_').replace('/', '_')}.pptx"
    
    generator = SlideDeckGenerator(output_path)
    generator.build_research_deck(topic, research_brief, course_title, author)
    generator.save()
    
    print(f"\nSlide deck generated: {output_path}")
    print(f"  Total slides: {len(generator.presentation.slides)}")
    print(f"  Citation confidence: {research_brief.citation_confidence}")
    print(f"  Source score: {research_brief.source_score:.2f}")
    return output_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Deep research assistant: research a topic and generate an undergraduate course slide deck.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.agent "Advanced Machine Learning"
  python -m src.agent "Predictive Analytics" --content-dir ./local_materials
  python -m src.agent "Neural Networks" --output-dir ./decks --course-title "CS 301"
        """
    )
    parser.add_argument("topic", help="Topic to research for the course (e.g., 'Advanced Machine Learning')")
    parser.add_argument("--content-dir", type=pathlib.Path, default=None, help="Optional directory with local course materials for enrichment")
    parser.add_argument("--output-dir", type=pathlib.Path, default=DEFAULT_OUTPUT_DIR, help="Directory where the slide deck will be saved")
    parser.add_argument("--course-title", type=str, default="Undergraduate Course", help="Title of the course")
    parser.add_argument("--author", type=str, default="Research Assistant", help="Instructor/author name")
    args = parser.parse_args(argv)
    
    try:
        build_research_deck(
            topic=args.topic,
            output_dir=args.output_dir,
            course_title=args.course_title,
            author=args.author,
            content_dir=args.content_dir,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
