# Progress Report — AI Personal Assistant

🌐 **English** · [Español](REPORTE_PROGRESO.md)

Updated November 16, 2026 · Hugo Maldonado Caballero

## Summary

The class chatbot grew into a **private personal assistant** that runs as a Telegram bot: it delivers personalized news and actively exploited vulnerabilities (CISA KEV), reads the user's Google Calendar, and creates reminders only after the user confirms them. It has **95 automated tests**, runs on Python 3.13, and every push goes through tests, Bandit and pip-audit.

- **Class goal:** fork the `automatizaci-n_simple` repository and build a chatbot from it (Phase 1, submitted).
- **Personal goal:** a daily assistant for news, agenda and job openings matched to a professional profile.
- **Status as of November 16, 2026:** Phases 1 to 4 done. Phase 5 (job openings) is being prepared: a dedicated mailbox now receives LinkedIn and Indeed job alerts.

| Phase | What it added | Tests |
| --- | --- | --- |
| 4 — Calendar | Google Calendar agenda (up to one year) and reminders with human confirmation | 95 |
| 3 — Telegram | Private bot with chat-ID allowlist and a morning briefing prompt | 66 |
| 2 — News | RSS news by topic, CISA KEV, personalization, prompt-injection defenses | 44 |
| 1 — LLM | Tool use, 4 providers, weather, stocks, time; class bugs fixed | 22 |

The sections below document Phase 1 (the class project) in detail, followed by Phases 2 to 4.

## Code origin

This project starts from the repository [mendiolaleonel2002-debug/automatizaci-n_simple](https://github.com/mendiolaleonel2002-debug/automatizaci-n_simple), provided as an exercise in the AI class. It was forked to [krma12/automatizaci-n_simple](https://github.com/krma12/automatizaci-n_simple), where v2.0 was developed and submitted. The working code was then copied to this repository to keep growing as a personal project.

- **Kept from the original:** the one-skill-per-file idea in `funciones_agente/`, and the use of wttr.in (weather) and yfinance (stocks).
- **Rewritten:** both functions, `main.py`, and the tests.
- **New:** `proveedores.py`, `herramientas.py`, multi-provider support, and `.env` configuration.

## Original project (v1.0)

The instructor's repository is a Python console chatbot of about 550 lines with two skills: checking the weather and stock prices. It did not use AI: it detected intent by searching for keywords.

| Component | Role in v1.0 |
| --- | --- |
| `main.py` | Console chatbot; detects intent with regular expressions (regex) |
| `agente_selenium.py` | Second version that opens headless Chrome with Selenium and detects keywords |
| `funciones_agente/obtener_clima.py` | Gets the temperature from the free wttr.in API |
| `funciones_agente/obtener_precio_accion.py` | Gets the price with the yfinance library; has a dictionary of 11 company names to tickers |
| `utils/sanitizar.py` | Strips prefixes like "precio de" or "la" to isolate the company name |
| `test_chatbot.py` | Prints Microsoft's price; does not check any result |
| `prueba_selenium.py` | Opens Google, Hybridge, and OpenAI in Chrome as a demo |

**What was already well done and was kept:**

- **Modularity:** each skill lives in its own file inside `funciones_agente/`.
- **Interface separation:** the same function can be called from the console or from Selenium.
- **Error handling:** `try/except` in the main loop and in API calls, with a clean exit on Ctrl+C.
- **Documentation:** README with a Mermaid architecture diagram and a list of suggested improvements. The first suggestion was precisely to replace the regex with an LLM.

## Bugs found in the original code

When the text cleanup was tested with real questions, none of the 4 sample questions reached the API correctly. The two most serious bugs broke even the example the bot itself shows at startup.

| Test question | Text sent to the API | Cause |
| --- | --- | --- |
| clima en Denver | `dver` | `obtener_clima` deleted "en" and "de" anywhere inside a word, not only as standalone words |
| temperatura en Benito Juárez | `bito juárez` | The same `.replace("en", "")` |
| ¿cuál es la temperatura actual en la Ciudad de México? | `¿cuál es la  actual  la ciudad  méxico?` | Only keywords were removed; the rest of the sentence was sent as is |
| ¿cuál es el precio de una acción de Microsoft? | the whole sentence as the ticker | `main.py` did not clean the text, and `sanitizar` only strips leading prefixes |

**Other issues:**

1. **Unused Selenium:** `agente_selenium.py` opened Chrome and passed the browser to the functions, but none of them used it. It only slowed down startup.
2. **Junk files in the repository:** `__pycache__` folders were committed even though `.gitignore` excluded them.
3. **Tests without assertions:** `test_chatbot.py` only printed a result; it never checked whether it was correct.
4. **Empty price on weekends:** requesting 1 day of history from yfinance may return no data when the market is closed.

## Improvements and optimizations (v2.0)

The core change was replacing the regex with a language model using *tool use*: the model understands the question, decides which tool to use, extracts the clean parameter, and writes the answer. The weather and stock functions were kept and turned into tools.

| Area | v1.0 | v2.0 |
| --- | --- | --- |
| Understanding | Regex and keywords | LLM with *tool use* |
| AI providers | None | Gemini, Groq, Ollama, and Claude, selected with `LLM_PROVIDER` in `.env` |
| Conversation memory | No | Yes, trimmed to the 20 most recent messages |
| Weather | Temperature only; city names mangled | Condition, temperature, feels-like, and humidity in Spanish; city kept intact and URL-encoded |
| Stocks | 1-day price; 11 names in the dictionary | 5-day history, with currency and closing date; the model converts any company to its ticker |
| Tests | 1 script with no assertions | 18 `pytest` tests with mocks, no internet or cost |
| Security | No key handling | Keys in `.env` excluded from Git, `.env.example` template |
| Errors | Generic message | Shows the server's detail and rolls the failed question back out of the history |

**New or rewritten files:**

- **`herramientas.py` (new):** central tool registry. Each tool has a definition (name, description, and JSON Schema parameters) and its Python function. Adding a skill means adding a definition.
- **`proveedores.py` (new):** two adapters, one for Anthropic's native API and one for OpenAI-compatible APIs (Gemini, Groq, Ollama), plus a function that picks the provider from `.env`.
- **`main.py` (rewritten):** only handles the conversation; it does not depend on which model is behind it.
- **`agente_selenium.py` (adjusted):** still works with the new function signatures, in case it is used later in the class.
- **`README.md` (updated):** v2.0 changes section, provider table, and usage instructions.

## Problems during implementation

Four problems came up while installing and testing on Windows; all 4 were resolved and no key reached GitHub.

| Problem | Cause | Solution |
| --- | --- | --- |
| Gemini 400 error when using a tool | Gemini 3 sends a hidden "reasoning signature" with each tool call and requires it back; the code rebuilt the message and dropped it | Store the model's response exactly as received (`model_dump`), with a test confirming the signature is kept |
| API key shared in a chat | The key was pasted into a conversation | Treated as exposed: deleted in Google AI Studio and a new one generated |
| Key inside `.env.example` | The key was pasted into the template, which does get pushed to GitHub | Detected by the file size (728 to 769 bytes) and the template was restored before the first commit |
| `.Bot` virtual environment not excluded | `.gitignore` only covered names like `.venv` and `venv` | Added `.bot/` to `.gitignore`, along with the `cheetsheet` notes file |

**Main lesson:** even though Gemini, Groq, and Ollama claim to be "OpenAI-compatible", each provider has its own details. An adapter that keeps fields it does not recognize is more robust than one that rebuilds messages by hand.

## Current features and v2.0 structure

v2.0 answers in Spanish, remembers the conversation, uses tools only when the question requires it, and never makes up temperatures or prices.

![Tool use flow: the model decides whether it needs a tool before answering](flujo_tool_use.png)

If the model requests a tool, Python runs it and returns the result; the loop repeats up to 5 times before answering.

**File structure (class fork):**

```
automatizaci-n_simple/
├── main.py               # Console conversation
├── proveedores.py        # LLM adapters + selection via .env  (new)
├── herramientas.py       # Tool definitions and registry       (new)
├── funciones_agente/
│   ├── obtener_clima.py
│   └── obtener_precio_accion.py
├── utils/sanitizar.py    # No longer used by main.py; used by agente_selenium.py
├── agente_selenium.py
├── test_chatbot.py       # 18 pytest tests
├── REPORTE_PROGRESO.md   # This report
├── docs/flujo_tool_use.png  # Flow diagram
├── .env.example          # Public template (no keys)
├── .env                  # Real keys (excluded from Git)
└── requirements.txt
```

**Available providers:**

| Provider | Cost | Default model | Recommended use |
| --- | --- | --- | --- |
| Gemini | Free with limits | `gemini-3.5-flash` | Daily testing (active today) |
| Groq | Free with limits | `openai/gpt-oss-20b` | Fast alternative |
| Ollama | Free, local | `qwen3:4b` | Personal data (Phase 3), for privacy |
| Claude | Paid | `claude-haiku-5-5` | Production |

**Environment:** Windows, VS Code, project on an external SSD (`D:\Proyectos`), `.Bot` virtual environment.

## Phases 2 to 4 (asistente-personal)

### Phase 2 — News and threat intelligence
- **News by topic** from a fixed list of RSS sources: cybersecurity, AI, technology and geopolitics (sources from several regions for balance).
- **CISA KEV:** vulnerabilities with confirmed real-world exploitation, with an NVD link and a ransomware flag.
- **Personalization:** only the interests and career goal from the local `perfil.yaml` are sent to the model.
- **Prompt-injection defenses:** external text is cleaned, truncated, wrapped in unforgeable delimiters and scanned for injection phrases; the model only chooses topics, never URLs.

### Phase 3 — Private Telegram bot
- Only answers the configured chat ID; strangers are ignored and only their ID is logged.
- Daily question at 08:00 with a button for the briefing; `/noticias` and `/reiniciar` commands.
- The bot token is never printed (HTTP client logging is silenced because Telegram URLs contain it).

### Phase 4 — Google Calendar
- Reads the agenda (a specific day or up to one year, up to 300 events, paginated).
- **Reminders with human confirmation:** the model can only propose; the event is created when the user taps **Create**. Notifications can be set days in advance.
- Minimal Google scope (`calendar.events`); credentials in `secretos/`, excluded from Git.

### Quality and security work
- Python 3.13 (3.10 reached end of life), pinned dependencies, Dependabot.
- CI in GitHub Actions: tests on 3.12 and 3.13, Bandit and pip-audit.
- [Security policy](../SECURITY.md) and [threat model](THREAT_MODEL.md) mapped to the OWASP Top 10 for LLM applications.

### Problems solved along the way

| Problem | Cause | Solution |
| --- | --- | --- |
| Gemini returned **429 Too Many Requests** | A year-long agenda was resent in every message through the conversation history | Old tool results are trimmed in the history; compact agenda format; clear rate-limit message in Telegram |
| Events after a certain date "did not exist" | The calendar query was capped at 25 events | Pagination up to 300 events, queries by specific date, warning when the list is truncated |
| Google publishing blocked | The new Google Auth Platform asks for a home page and privacy policy to publish | Stay in Testing mode (authorization renewed every 7 days) |
| Old virtual environment could not be deleted | Windows kept `python.exe` locked | New `.venv` with Python 3.13; delete the old one after a reboot |
| Files reverted to old versions | VS Code saved open tabs over updated files | Close tabs and disable Auto Save before external edits |
| CI in red after Phase 2 | Bandit flagged `assert` in the new test files | Exclude `test_*.py` from Bandit |

## Next steps

- [x] Phases 1 to 4
- [x] Security policy and threat model
- [ ] **Phase 5, job openings:** read the dedicated job-alert mailbox (LinkedIn and Indeed alerts redirected from Outlook) and score openings against the local profile; Ibero-America, including Brazil
- [ ] Move the bot to a dedicated home server (Lenovo ThinkCentre M920q) and harden it
- [ ] Optional: publish the Google OAuth app with a privacy page on GitHub Pages
