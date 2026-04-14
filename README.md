# Deep Research Assistant

An intelligent tool that researches any topic and generates comprehensive, evidence-based undergraduate course slide decks (30-40 slides).

## Features

- **CLI-driven**: Pass any topic as a command-line argument
- **Multi-source research**: Aggregates Wikipedia, educational sources, and local materials
- **Comprehensive structure**: 30-40 slides covering foundations, applications, ethics, and pitfalls
- **Citation confidence**: Shows reliability scores for all referenced material
- **Local enrichment**: Optionally augment with your own course materials

## Quick Start

```bash
python -m src.agent "Advanced Machine Learning"
```

## Usage Examples

```bash
# Basic topic research
python -m src.agent "Predictive Analytics"

# With local materials for enrichment
python -m src.agent "Neural Networks" --content-dir ./my_notes

# Custom output location and course title
python -m src.agent "Deep Learning" \
  --output-dir ./decks \
  --course-title "Applied ML for Undergraduates" \
  --author "Prof. Smith"
```

## Arguments

- `topic` (required): The subject to research and build a course on
- `--content-dir`: Optional directory with local course materials for enrichment
- `--output-dir`: Where to save the slide deck (default: `./output`)
- `--course-title`: Title for the generated course (default: "Undergraduate Course")
- `--author`: Instructor name (default: "Research Assistant")

## Generated Decks

Output decks contain approximately 30-40 slides organized in five parts:

1. **Foundations** (8-10 slides): Core concepts, definitions, history, and theoretical frameworks
2. **Applications** (8-10 slides): Real-world use cases and three detailed case studies
3. **Ethics & Implications** (6-8 slides): Social implications, fairness, accountability, and responsibility
4. **Pitfalls & Misconceptions** (6-8 slides): Common misconceptions, failure modes, and robust system design
5. **Discussion & Wrap-up** (4-6 slides): Key takeaways, reflection, and next steps
6. **References**: Scored sources with confidence metrics

Each deck is specifically designed for undergraduate learners with emphasis on practical understanding and ethical reasoning.

## Source Materials

The agent accepts optional local supplementary materials in:

- `.txt` - plain text files
- `.md`, `.markdown` - Markdown files
- `.docx` - Word documents
- `.pdf` - PDF files

Place these in a directory and pass `--content-dir ./your_directory` to enrich the research output.

## Research Process

When you run the agent:

1. Conducts multi-source research using Wikipedia and educational APIs
2. Scores sources by reliability and relevance
3. Extracts local course content if provided
4. Generates 30-40 slides with structured learning progression
5. Includes discussion prompts for classroom engagement
6. Provides citation confidence metrics

If online sources are temporarily unavailable, the tool falls back to local material to ensure quality output.
