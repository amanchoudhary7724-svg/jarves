# Jarves

A modular Python voice assistant built for practical, extensible desktop automation.

Jarves combines speech input, wake-word detection, language-model tools, text-to-speech, screen reading, and a lightweight web interface in one evolving assistant platform.

## What it includes

- Speech-to-text and text-to-speech building blocks
- Wake-word detection for hands-free interaction
- LLM integration and tool-oriented agent logic
- Screen reading and desktop context support
- Optional browser-based control surface
- JSON and environment-based configuration
- Tests and utility modules for continued experimentation

## Project structure

| Area | Key files |
| --- | --- |
| Assistant runtime | agent.py, main.py, run_jarvis.py |
| Language model layer | llm.py |
| Voice pipeline | stt.py, tts.py, wakeword_detector.py |
| Screen awareness | screen_reader.py |
| Web interface | index.html, web_server.py |
| Configuration | config.json, config_loader.py, .env.example |

## Getting started

1. Review SETUP.md for environment and dependency instructions.
2. Copy .env.example to .env and add your local values.
3. Follow the run command documented in SETUP.md for your chosen assistant mode.
4. Read HANDOVER.md for current verification notes and known limitations.

> Available voice, model, and desktop features depend on your operating system, installed dependencies, and configured providers. Never commit secrets or API keys.

## Development notes

Jarves is an active engineering project. The code is intentionally modular so individual voice, model, screen, and interface components can be tested or replaced independently.

## License

No license has been declared yet. Until a license is added, all rights remain with the repository owner.

---

Built by [Badshah](https://github.com/amanchoudhary7724-svg) as part of a practical AI-assistant portfolio.
