#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["tomlkit"]
# ///
"""Registra o agente PULSE (Levi) na tabela [agents] de _bmad/custom/config.toml.

Party-mode (bmad-party-mode) monta o roster lendo a tabela [agents] via
resolve_config.py, que faz deep-merge de _bmad/config.toml (base) com
_bmad/custom/config.toml (team). Os modulos OFICIAIS tem suas entradas
[agents.*] escritas no config.toml base pelo installer do BMAD core; um modulo
CUSTOM (como o PULSE) nao e escrito ali, entao seu agente nunca aparece no
party-mode. Este script grava a entrada no layer custom (team, committed), que
sobrevive a re-install. Idempotente / anti-zombie: reescreve a propria entrada
a cada run e preserva comentarios e demais secoes (tomlkit round-trip).
"""
import argparse
import csv
import json
import sys
from pathlib import Path

try:
    import tomlkit
except ModuleNotFoundError:
    print("Error: tomlkit is required (PEP 723 dependency). Run via `uv run`.", file=sys.stderr)
    sys.exit(2)

DEFAULT_TEAM = "software-development"


def load_fragment(fragment_path: Path) -> dict | None:
    with fragment_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if (r.get("name") or "").strip() == "pulse":
            return r
    return rows[0] if rows else None


def agent_key(row: dict) -> str:
    # deriva a chave da tabela do path do SKILL: .claude/skills/<dir>/SKILL.md
    path = (row.get("path") or "").strip()
    if path:
        return Path(path).parent.name  # bmad-agent-pulse
    return "bmad-agent-pulse"


def build_entry(row: dict) -> dict:
    return {
        "module": (row.get("module") or "pulse").strip(),
        "team": DEFAULT_TEAM,
        "name": (row.get("displayName") or "Levi").strip(),
        "title": (row.get("title") or "").strip(),
        "icon": (row.get("icon") or "").strip(),
        "description": (row.get("identity") or row.get("role") or "").strip(),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Register the PULSE agent in _bmad/custom/config.toml [agents].")
    ap.add_argument("--project-root", required=True, help="Consumer project root")
    ap.add_argument("--fragment", required=True, help="Path to agent-manifest-fragment.csv")
    args = ap.parse_args()

    root = Path(args.project_root)
    fragment = Path(args.fragment)
    custom = root / "_bmad" / "custom" / "config.toml"

    if not fragment.exists():
        print(json.dumps({"status": "error", "reason": f"fragment not found: {fragment}"}))
        sys.exit(1)

    row = load_fragment(fragment)
    if row is None:
        print(json.dumps({"status": "error", "reason": "empty fragment"}))
        sys.exit(1)

    key = agent_key(row)
    entry = build_entry(row)

    if custom.exists():
        doc = tomlkit.parse(custom.read_text(encoding="utf-8"))
    else:
        custom.parent.mkdir(parents=True, exist_ok=True)
        doc = tomlkit.document()

    agents = doc.get("agents")
    if agents is None:
        agents = tomlkit.table(is_super_table=True)
        doc["agents"] = agents
    if key in agents:
        del agents[key]

    tbl = tomlkit.table()
    for k, v in entry.items():
        tbl[k] = v
    agents[key] = tbl

    custom.write_text(tomlkit.dumps(doc), encoding="utf-8")
    print(json.dumps(
        {"status": "success", "agent_key": key, "custom_config_path": str(custom), "entry": entry},
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
