# Contributing to PULSE

Thanks for considering a contribution. PULSE is a BMAD-native observability module — improvements that sharpen the leverage signal, the dashboard, or the integration with BMAD workflows are especially welcome.

## Getting started

### Prerequisites

- Python 3.12+
- `git`
- A working clone of [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) is helpful for end-to-end testing, but not required for unit tests.

### Setup

```bash
git clone https://github.com/nidelson/bmad-module-pulse.git
cd bmad-module-pulse
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

### Run tests

```bash
python -m pytest tests/ -v
```

The test suite includes both unit tests and integration tests (marked with `@pytest.mark.integration`) that spin up fake consumer projects to validate end-to-end skill behavior.

## How to contribute

### Open an issue first for non-trivial changes

For bug fixes, small docs tweaks, or clearly-scoped improvements — go straight to a PR.

For anything larger (new skills, schema changes, new metrics, dashboard restructuring) — open an issue first so we can align before you invest the time. The PULSE roadmap is opinionated; let's make sure the work fits.

### Pick an existing issue

Issues labeled `good first issue` or `help wanted` are explicitly open for contributors. Comment on the issue to claim it before starting work.

## Development workflow

### Branch naming

Use prefixes that match the change type — these align with our Conventional Commit categories:

- `feat/<short-description>` — new feature
- `fix/<short-description>` — bug fix
- `chore/<short-description>` — tooling, deps, repo hygiene
- `docs/<short-description>` — documentation only
- `refactor/<short-description>` — internal restructure, no behavior change

### Conventional Commits are required

PULSE uses [release-please](https://github.com/googleapis/release-please) to automate releases. Commit prefixes drive the version bump and CHANGELOG. Use one of:

- `feat:` — new feature (minor bump pre-1.0, minor post-1.0)
- `fix:` — bug fix (patch bump)
- `chore:`, `docs:`, `refactor:`, `perf:`, `ci:`, `build:`, `test:`, `style:` — no version bump
- `feat!:` or `BREAKING CHANGE:` in the body — major bump

Bad commit messages (no prefix, vague) will be rejected at review.

### Branch protection

`main` requires:

- A pull request (no direct push)
- Passing `pytest` check
- Branch must be up to date with `main` before merge

There is no required reviewer (solo maintainer for now), but the maintainer may request changes before merging.

### Running tests before pushing

Always run the full suite locally before pushing — CI is fast, but failed runs slow everyone down:

```bash
python -m pytest tests/ -v
```

### Pull request flow

1. Push your branch.
2. Open a PR against `main`. Include a clear summary, the issue it resolves (if any), and a test plan.
3. Wait for `pytest` to pass.
4. Maintainer reviews. Address feedback in additional commits (don't force-push during review — squash happens at merge time).
5. Squash merge once approved.

## Code style

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/).
- Type hints are encouraged but not yet enforced.
- Keep functions focused; prefer small, testable units.
- Tests are required for new features and bug fixes.

### BMAD skill format

Skills follow BMAD conventions. When adding or modifying a skill:

- Frontmatter (`name`, `description`, etc.) is mandatory.
- Workflow files (`workflow.md`) describe the skill execution flow.
- Stay terse — skill files are loaded into LLM context every time the skill runs. Verbose docs cost tokens.

When in doubt, mirror the structure of an existing skill in `skills/`.

### Documentation

User-facing docs (README, MIGRATION, examples) are in **English**. Brazilian Portuguese mirrors live in `*.pt-BR.md` files.

Internal notes, ADRs, and design discussions can be in either language — match the existing file's language.

## Reporting issues

### Bugs

Open an issue with:

- PULSE version (`grep '"version"' skills/bmad-pulse-setup/SKILL.md` or check `CHANGELOG.md`)
- BMAD version
- Reproduction steps
- Expected vs. actual behavior
- Logs/output if relevant

### Security issues

**Do not open a public issue for security vulnerabilities.** See [SECURITY.md](SECURITY.md) for the private disclosure process.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold it.

## Recognition

Contributors are listed on the GitHub contributor graph automatically. Significant contributions may be highlighted in CHANGELOG entries.

## Questions?

- General discussion — open a GitHub Discussion (or Issue if Discussions are not yet enabled)
- Direct contact — `nidelson@gmail.com`

Thanks again for helping make PULSE better.
