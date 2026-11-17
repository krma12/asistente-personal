# Threat Model

🌐 **English** · [Español](MODELO_DE_AMENAZAS.md)

Last reviewed: November 2026 (through Phase 4: Telegram + Google Calendar).

The assistant's biggest risk is not a classic web attack. It is a **language model that reads untrusted text and can call tools**: anyone who controls a news article, an RSS feed or a calendar invitation can try to steer it. The design assumes the model *will* sometimes be fooled, and limits what a fooled model can do.

## Assets

| Asset | Where it lives | Why it matters |
| --- | --- | --- |
| LLM API keys (Gemini, Groq, Claude) | `.env` (git-ignored) | Billing and quota abuse |
| Telegram bot token | `.env` | Full control of the bot |
| Google OAuth token (`calendar.events`) | `secretos/` (git-ignored) | Read and write the user's calendar |
| Personal profile | `perfil.yaml` (git-ignored) | Career goals and interests |
| Calendar contents | Google Calendar | Daily life, places, people |
| The user's attention and trust | Telegram chat | A fooled assistant can mislead the user |

## Trust boundaries

1. **User ↔ assistant:** only the Telegram chat ID in `.env`, or the local console, is trusted to give instructions.
2. **Assistant ↔ language model provider:** prompts, profile interests and tool results leave the machine and reach the provider's servers.
3. **Assistant ↔ external content:** RSS feeds, the CISA KEV catalog and calendar events (including invitations from anyone) are **untrusted data**.
4. **Assistant ↔ Google Calendar:** the only place where the assistant can *write*.

## Threats and mitigations

| # | Threat | Mitigation | Where in the code |
| --- | --- | --- | --- |
| T1 | **Indirect prompt injection** in a news item or calendar invitation ("ignore your instructions and…") | Untrusted text is stripped of HTML and control characters, truncated, wrapped in delimiters it cannot forge, and scanned for typical injection phrases (flagged to the user). The system prompt tells the model to treat it as data. | `funciones_agente/contenido_externo.py`, `proveedores.py` |
| T2 | **Excessive agency:** a fooled model creates calendar events | The model can only *propose* a reminder. It is created only after the user taps **Create** (Telegram) or types `s` (console). There is deliberately no tool to confirm. All other tools are read-only. | `funciones_agente/calendario.py`, `herramientas.py`, `bot_telegram.py`, `main.py` |
| T3 | **Server-side request forgery:** the model is tricked into fetching internal or arbitrary URLs | The model picks a topic from a fixed list, never a URL. Any parameter not declared in a tool's schema is rejected before execution. | `funciones_agente/obtener_noticias.py`, `herramientas.py` |
| T4 | **Unauthorized bot use:** a stranger finds the bot and spends the user's quota or reads data | Telegram allowlist by chat ID; strangers are ignored, and only their ID is logged, never their message. Without a configured ID the bot answers no one except `/start`. | `bot_telegram.py` |
| T5 | **Secret leakage** in the repo or logs | `.env`, `perfil.yaml` and `secretos/` are git-ignored; templates contain fake values; GitHub Push Protection is enabled. HTTP client logging is silenced because Telegram API URLs contain the bot token. Error messages to the user never include internals. | `.gitignore`, `bot_telegram.py` |
| T6 | **Malicious or oversized responses** from a compromised source | Time and size limits on every download; one failing source never breaks the others; JSON and feeds are parsed defensively. | `funciones_agente/contenido_externo.py` |
| T7 | **Unsafe deserialization** of the profile file | `yaml.safe_load` only; a test confirms that a malicious YAML payload is rejected. | `perfil.py`, `test_noticias.py` |
| T8 | **Dangerous links** in news or events | Only `http(s)` links are kept; `javascript:` and `data:` links are dropped. Telegram messages are sent as plain text, never parsed as HTML or Markdown. | `funciones_agente/contenido_externo.py`, `bot_telegram.py` |
| T9 | **Supply-chain vulnerabilities** in dependencies | Pinned versions, Dependabot weekly updates, pip-audit and Bandit on every push. | `requirements.txt`, `.github/` |
| T10 | **Unbounded consumption:** huge tool results exhaust the API quota | Result size limits, compact calendar format above 40 events, and old tool results are trimmed from the conversation history. | `proveedores.py`, `funciones_agente/calendario.py` |
| T11 | **Excess data sent to the model provider** | Data minimization: only interests and career goal are taken from the profile; the rest never leaves the machine. | `perfil.py` |

## OWASP Top 10 for LLM Applications (2025) coverage

| OWASP item | Addressed by |
| --- | --- |
| LLM01 Prompt Injection | T1, T2, T3 |
| LLM02 Sensitive Information Disclosure | T5, T11 |
| LLM03 Supply Chain | T9 |
| LLM05 Improper Output Handling | T8 |
| LLM06 Excessive Agency | T2, T3 |
| LLM07 System Prompt Leakage | The system prompt contains no secrets, so leaking it has no impact |
| LLM10 Unbounded Consumption | T4, T10 |

## Residual risks (known and accepted)

- **Injection detection is heuristic.** A creative attacker can phrase an injection that is not flagged. The real protection is that tools are read-only and writes need human confirmation; the worst realistic outcome is a misleading answer.
- **Data sent to the model provider.** Calendar titles, news and profile interests reach the provider. Some free tiers may use submitted data to improve their products. For sensitive use, switch to Ollama (local) or a paid plan with business data terms.
- **Telegram bot chats are not end-to-end encrypted;** messages pass through Telegram's servers.
- **Secrets are stored as plain files** protected only by the operating system account. Recommended: full-disk encryption (BitLocker) on the computer and the external SSD.
- **The Google OAuth app is in Testing mode,** so the authorization expires every 7 days and must be renewed with `configurar_calendario.py`.
- **Dependencies are pinned by version, not by hash.**
- **Availability** depends on the user's laptop being on; there is no redundancy.

## Planned improvements

- Phase 5 (job alerts) will read a **dedicated mailbox** that only receives job-alert emails, so the assistant never has access to personal or work email.
- Move the bot to a dedicated home server and harden it (SSH keys only, firewall, automatic updates, unprivileged service user).
- Optional hash-pinned dependencies.
