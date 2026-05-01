# Security Policy

## Supported Versions

PULSE is in active pre-1.0 development. Security fixes are applied to the latest minor version only.

| Version    | Supported          |
| ---------- | ------------------ |
| `0.4.x`    | ✅                 |
| `< 0.4.0`  | ❌ — please upgrade |

Once `1.0.0` ships, this table will be updated to cover the most recent two minor versions.

## Reporting a Vulnerability

**Do not file a public GitHub issue for security vulnerabilities.**

Please report security issues via one of the following private channels:

1. **Preferred — GitHub Security Advisories**
   - Open a private advisory at: <https://github.com/nidelson/bmad-module-pulse/security/advisories/new>
   - This keeps the report private until a fix is released and lets us coordinate a CVE if warranted.

2. **Alternative — Email**
   - `nidelson@gmail.com`
   - Subject: `[SECURITY] PULSE — <short summary>`
   - Include reproduction steps, affected version(s), and any relevant logs or POC.

### What to include in your report

- Affected PULSE version(s)
- Affected BMAD version (if relevant)
- Steps to reproduce
- Impact assessment (what data, files, or systems are exposed)
- Any suggested mitigation
- Whether you've already disclosed this elsewhere

## Response Timeline

PULSE is currently maintained by a single person, so response times are best-effort:

- **Initial acknowledgement** — within 72 hours
- **Triage and severity assessment** — within 7 days
- **Fix or mitigation** — depends on severity (see below)
- **Public disclosure** — coordinated with the reporter, typically within 30 days of fix release

### Severity guide

| Severity   | Description                                                                 | Target fix window |
| ---------- | --------------------------------------------------------------------------- | ----------------- |
| Critical   | Remote code execution, secret exfiltration, arbitrary file write            | 72 hours          |
| High       | Privilege escalation, sensitive data exposure, supply-chain risk            | 7 days            |
| Moderate   | Information disclosure, denial of service                                   | 30 days           |
| Low        | Hardening opportunities, defense-in-depth gaps                              | next release      |

## Scope

### In scope

- The PULSE skills (`skills/bmad-pulse-*`)
- Dashboard generation logic
- Configuration and template handling (`customize.toml`, golden templates)
- Any file or path manipulation performed by PULSE
- Dependencies declared in `requirements-dev.txt` and `pyproject.toml`

### Out of scope

- BMAD core itself — please report those at <https://github.com/bmad-code-org/BMAD-METHOD/security>
- The consumer project's own files (PULSE reads but does not modify project files outside its `_bmad-output` paths)
- Third-party LLM providers (Claude, GPT, etc.) — those are upstream of PULSE
- Issues in projects that fork or vendor PULSE without keeping current

## Acknowledgements

Reporters who follow this policy and act in good faith will be acknowledged in the release notes of the fixing version (unless they prefer to remain anonymous).

## Questions

For non-security questions, see [CONTRIBUTING.md](CONTRIBUTING.md) or open a regular GitHub issue.
