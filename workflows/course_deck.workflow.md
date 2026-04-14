# Course Deck Workflow

This workflow describes the agentic process for generating a college course slide deck.

## Workflow steps

1. `Collect Source Content`
   - Inspect `content/` for Markdown and text files.
2. `Summarize Content`
   - Extract titles and key sentences from source files.
3. `Ask Topic Selection`
   - Prompt the user to choose course topics for the 3-hour deck.
4. `Research Topics Online`
   - Aggregate references from multiple web sources per selected topic.
   - Score each citation and calculate per-topic citation confidence.
5. `Generate Slide Deck`
   - Build a PowerPoint deck with deep-dive slides, discussion prompts, and confidence-labeled references.
6. `Send Email`
   - If requested, email the generated file using SMTP settings.

## Expected directories

- `content/`: source content input
- `output/`: generated slide decks
- `src/`: processing and agent runtime code
- `prompts/`: agent instructions and prompt templates
