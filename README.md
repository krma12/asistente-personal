# AI Personal Assistant

[![CI](https://github.com/krma12/asistente-personal/actions/workflows/ci.yml/badge.svg)](https://github.com/krma12/asistente-personal/actions/workflows/ci.yml)

🌐 **English** · [Español](README.es.md)

A Python console assistant that uses an LLM with *tool use* to answer with real-time data. It already delivers **personalized news** (cybersecurity, AI, technology, geopolitics) and **actively exploited vulnerabilities** (CISA KEV). The goal is a daily assistant reachable from Telegram, with calendar reminders and **job openings** matched to a professional profile.

> Work in progress. It started from a chatbot class exercise
> ([automatizaci-n_simple](https://github.com/krma12/automatizaci-n_simple)) and continues here as an independent project.

![Tool use flow](docs/flujo_tool_use.png)

## How it works

1. The user asks a question in natural language.
2. The model decides whether it needs a tool: weather, stocks, date and time, news by topic, or exploited vulnerabilities.
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
- [x] **Phase 2:** news from RSS feeds by topic, personalized with the local profile, plus CISA KEV vulnerabilities, with prompt-injection defenses
- [ ] **Phase 3:** Telegram bot: chat from the phone and a morning prompt for the daily news
- [ ] **Phase 4:** Google Calendar reminders, days in advance, and reminders created by message
- [ ] **Phase 5:** job openings read from email job alerts and scored against the local profile (Ibero-America, including Brazil)

Full details on bugs found, fixes, and decisions: [Progress report](docs/PROGRESS_REPORT.md).

## Design and security decisions

- **Prompt-injection defenses (OWASP LLM01):** news and CVE text is treated as untrusted data. It is stripped of HTML and control characters, truncated, wrapped in delimiters that external text cannot forge, and scanned for typical injection phrases, which are flagged to the user. Tests simulate real attacks.
- **Least privilege:** every tool is read-only, and the model only picks a topic from a fixed list, never a URL (prevents SSRF). Any parameter not declared in a tool's schema is rejected.
- **Safe downloads:** time and size limits on every request; one broken source never breaks the others.
- **Data minimization:** only interests and career goal from `perfil.yaml` are sent to the model, loaded with `yaml.safe_load`.
- **No LinkedIn or Indeed scraping:** their terms of use prohibit it. Job openings will come from the job alerts those platforms email to the user.
- **Personal data stays out of the repository:** the real profile (`perfil.yaml`), API keys (`.env`) and generated output are in `.gitignore`. The repo only ships templates with fictional data.
- **Privacy per provider:** Ollama (local) is recommended for analyzing the personal profile, because some APIs' free tiers may use submitted data to improve their products.
- **Continuous integration with security checks:** every push runs the tests on Python 3.12 and 3.13, a static security scan with Bandit, and a dependency vulnerability check with pip-audit. Dependabot proposes weekly updates for libraries and GitHub Actions.
- **Real-world provider compatibility:** Gemini 3 requires a reasoning signature to be sent back with every tool call. The adapter keeps every field of the response instead of rebuilding messages by hand.

## Setup (Windows / PowerShell)

```powershell
python -m venv .bot
.\.bot\Scripts\Activate.ps1
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
│   ├── obtener_hora.py
│   ├── obtener_noticias.py          # RSS by topic (fixed allowlist)
│   ├── obtener_vulnerabilidades.py  # CISA KEV
│   └── contenido_externo.py         # Safe handling of untrusted content
├── perfil.py               # Reads interests from perfil.yaml
├── test_asistente.py
├── test_noticias.py        # Includes simulated injection attacks
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
