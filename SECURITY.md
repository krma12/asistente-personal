# Security Policy

🌐 **English** · [Español](docs/SEGURIDAD.md)

This is a personal portfolio project, but security is treated as a first-class requirement: the assistant reads untrusted content from the internet, has access to a personal calendar, and talks to the outside world through Telegram.

## Supported versions

Only the latest commit on `main` is supported. Dependencies are pinned in `requirements.txt` and kept up to date by Dependabot; every push runs the test suite, Bandit (static analysis) and pip-audit (known-vulnerability check) in GitHub Actions.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Use GitHub's private vulnerability reporting: go to the **Security** tab of this repository and click **Report a vulnerability**. Include:

- what you found and where (file, function or behavior),
- steps to reproduce it,
- the impact you think it has.

You can expect an acknowledgment within 7 days. Fixes are released on `main`, and reporters are credited in the commit message unless they prefer to stay anonymous.

## Scope

In scope:

- Prompt injection that makes the assistant act against the user (for example, creating calendar events without confirmation or leaking the profile).
- Bypassing the Telegram allowlist.
- Leaking secrets (API keys, Telegram token, Google OAuth tokens) through code, logs or error messages.
- Server-side request forgery or downloads outside the fixed source list.
- Vulnerable dependencies not yet caught by pip-audit.

Out of scope:

- Rate limits or availability of third-party services (Gemini, Telegram, Google, RSS sources).
- Attacks that require prior access to the user's computer or accounts.
- The accuracy of news content or of the language model's answers.

## Design

The threat model, trust boundaries, mitigations and known residual risks are documented in [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).
