# Course Slide Deck Agent Prompt

This agent inspects a directory of course content files, asks the user which topics to cover, then generates a polished 3-hour slide deck.

## Behavior

- Scan the provided `content/` directory for supported source files.
- Summarize each source file by its title and first line.
- Prompt the user interactively for the topics they want included.
- Perform multi-source online topic research to gather deeper supporting material.
- Score retrieved sources and assign citation confidence levels.
- Generate a `.pptx` slide deck in the `output/` directory with in-depth talking points, discussion questions, and confidence-labeled references.
- If email configuration is available and an email recipient is provided, send the deck as an attachment.

## Usage

- Create or drop course notes into `content/`.
- Run `python src/agent.py`.
- Provide topics when prompted.
- Review the generated slide deck in `output/`.
