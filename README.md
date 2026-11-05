# AI Personal Assistant

🌐 **English** · [Español](README.es.md)

A Python console assistant that uses an LLM with *tool use* to answer with real-time data. The goal is a daily assistant that delivers **relevant news** (technology, cybersecurity, AI, geopolitics) and **job openings** matched to a professional profile, without searching by hand.

> Work in progress. It started from a chatbot class exercise
> ([automatizaci-n_simple](https://github.com/krma12/automatizaci-n_simple)) and continues here as an independent project.

![Tool use flow](docs/flujo_tool_use.png)

## How it works

1. The user asks a question in natural language.
2. The model decides whether it needs a tool (weather, stocks, date and time, and soon news and job openings).
3. Python runs the tool and sends the result back to the model.
4. The model writes the final answer in Spanish without making up data.

## Swappable AI providers

Pick the model with one line in `.env`, no code changes:

| `LLM_PROVIDER` | Cost | Notes |
| --- | --- | --- |
| `gemini` | Free with limits | Key from Google AI Studio |
| `groq` | Free with limits | Open models, very fast |
| `ollama` | Free, local | Data never leaves your computer |
| `claude` | Paid | Anthropic API |

`proveedores.py` has two adapters: one for Anthropic's native API and one for OpenAI-compatible APIs (Gemini, Groq, Ollama).

## Roadmap

- [x] **Phase 1:** LLM with *tool use*, multi-provider, weather, stock, and time tools, `pytest` tests
- [ ] **Phase 2:** news tool from RSS feeds, filtered by interests
- [ ] **Phase 3:** job openings read from email job alerts and scored against a local profile (Ibero-America, including Brazil)
- [ ] **Phase 4:** automatic daily briefing

Full details on bugs found, fixes, and decisions: [Progress report](docs/PROGRESS_REPORT.md).

## Design and security decisions

- **No LinkedIn or Indeed scraping:** their terms of use prohibit it. Job openings will come from the job alerts those platforms email to the user.
- **Personal data stays out of the repository:** the real profile (`perfil.yaml`), API keys (`.env`) and generated output are in `.gitignore`. The repo only ships templates with fictional data.
- **Privacy per provider:** Ollama (local) is recommended for analyzing the personal profile, because some APIs' free tiers may use submitted data to improve their products.
- **Real-world provider compatibility:** Gemini 3 requires a reasoning signature to be sent back with every tool call. The adapter keeps every field of the response instead of rebuilding messages by hand.

## Setup (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # choose LLM_PROVIDER and add its key
copy perfil.example.yaml perfil.yaml   # (for Phase 3) your real data
python main.py
```

## Tests

```powershell
python -m pytest -v
```

Tests use mocks: no internet connection or API credits needed.

## Structure

```
asistente-personal/
├── main.py                 # Console conversation
├── proveedores.py          # LLM adapters + provider selection via .env
├── herramientas.py         # Tool registry (JSON Schema definitions)
├── funciones_agente/       # One skill per file
│   ├── obtener_clima.py
│   ├── obtener_precio_accion.py
│   └── obtener_hora.py
├── test_asistente.py
├── .env.example            # API key template (no real data)
├── perfil.example.yaml     # Profile template (fictional data)
├── README.es.md            # Spanish version
└── docs/
    ├── PROGRESS_REPORT.md  # Progress report (English)
    ├── REPORTE_PROGRESO.md # Progress report (Spanish)
    └── flujo_tool_use.png
```

## Credits

This project is based on [automatizaci-n_simple](https://github.com/mendiolaleonel2002-debug/automatizaci-n_simple) by mendiolaleonel2002-debug, the starter repository for an AI class exercise. It was first forked to [krma12/automatizaci-n_simple](https://github.com/krma12/automatizaci-n_simple), where v2.0 was built and submitted.

- **Kept from the original:** the one-skill-per-file structure in `funciones_agente/`, and the use of wttr.in and yfinance.
- **Rewritten:** the weather and stock functions, `main.py`, and the tests.
- **New:** `proveedores.py`, `herramientas.py`, multi-provider support, and `.env` configuration.
