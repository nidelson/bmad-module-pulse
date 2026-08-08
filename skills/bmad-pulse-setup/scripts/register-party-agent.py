#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["tomlkit"]
# ///
"""Registra o agente PULSE (Maxine) na tabela [agents] de _bmad/custom/config.toml.

Party-mode (bmad-party-mode) monta o roster lendo a tabela [agents] via
resolve_config.py, que faz deep-merge de _bmad/config.toml (base) com
_bmad/custom/config.toml (team). Os modulos OFICIAIS tem suas entradas
[agents.*] escritas no config.toml base pelo installer do BMAD core; um modulo
CUSTOM (como o PULSE) nao e escrito ali, entao seu agente nunca aparece no
party-mode. Este script grava a entrada no layer custom (team, committed), que
sobrevive a re-install. Idempotente: preserva comentarios e demais secoes
(tomlkit round-trip).

O custom/config.toml e um arquivo human-authored — o time comenta e edita as
entradas ali. Por isso um re-run NAO reescreve o bloco inteiro: a entrada e
atualizada in-place (mantendo sua posicao e os comentarios que a precedem) e so
os campos estruturais (STRUCTURAL_FIELDS) sao regravados. Campos editoriais ja
presentes (name/title/icon/description) sao preservados — use `--force` para
restaura-los a partir do fragment.

Excecao: um valor editorial identico ao que uma versao ANTERIOR deste script
gravou nao e uma edicao do time — e a nossa propria escrita antiga. Preserva-lo
seria carregar para sempre um nome que a skill nao usa mais. Ver
LEGACY_FRAGMENT_VALUES.
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

# Campos que o fragment e dono: identificam o registro e podem ser regravados a
# cada run sem perda. Os demais (name/title/icon/description) sao editoriais —
# o time os ajusta direto no config.toml, e um re-run nao deve achata-los.
STRUCTURAL_FIELDS = ("module", "team")

# Valores editoriais que versoes anteriores deste script gravaram. Se o campo no
# config do time ainda casa EXATAMENTE com um destes, ninguem o editou: e a
# nossa escrita antiga, e sobrescrever restaura a verdade em vez de destruir uma
# customizacao. Qualquer outro valor e do time e continua preservado.
#
# Sem isso a troca Levi -> Maxine (v0.9) nao chegaria a projetos ja instalados:
# `name` e editorial, logo o re-run o preservaria, e o party-mode listaria Levi
# para sempre enquanto a skill se apresenta como Maxine.
LEGACY_FRAGMENT_VALUES = {
    "name": ("Levi",),
    "title": ("Hyper-Efficiency Analyst & SDLC Optimizer",),
    "icon": ("⚡",),
    "description": (
        "Performance analyst obsessed with efficiency data. Background in "
        "production engineering and analytics. Transforms numbers into "
        "improvement narratives. Specialist in AI-assisted development metrics "
        "and continuous SDLC optimization.",
    ),
}


def is_stale_default(field: str, value) -> bool:
    """True quando o valor presente foi escrito por uma versao antiga daqui."""
    return str(value).strip() in LEGACY_FRAGMENT_VALUES.get(field, ())


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
        "name": (row.get("displayName") or "Maxine").strip(),
        "title": (row.get("title") or "").strip(),
        "icon": (row.get("icon") or "").strip(),
        "description": (row.get("identity") or row.get("role") or "").strip(),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Register the PULSE agent in _bmad/custom/config.toml [agents].")
    ap.add_argument("--project-root", required=True, help="Consumer project root")
    ap.add_argument("--fragment", required=True, help="Path to agent-manifest-fragment.csv")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Tambem sobrescreve os campos editoriais (name/title/icon/description) "
             "com os valores do fragment. Sem a flag, campos ja presentes sao preservados.",
    )
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

    existing = agents.get(key)
    if existing is None:
        tbl = tomlkit.table()
        for k, v in entry.items():
            tbl[k] = v
        agents[key] = tbl
        action = "created"
        written = dict(entry)
        migrated = []
    else:
        # Atualiza in-place. Recriar a entrada (del + reatribuicao) a moveria
        # para o fim de [agents], desgarrando os comentarios que a precedem no
        # arquivo do time.
        migrated = []
        for k, v in entry.items():
            stale = k in existing and is_stale_default(k, existing[k])
            if args.force or k in STRUCTURAL_FIELDS or k not in existing or stale:
                existing[k] = v
                if stale and not args.force:
                    migrated.append(k)
        action = "forced" if args.force else ("migrated" if migrated else "updated")
        written = {k: existing[k] for k in entry}

    custom.write_text(tomlkit.dumps(doc), encoding="utf-8")
    print(json.dumps(
        {
            "status": "success",
            "action": action,
            "agent_key": key,
            "custom_config_path": str(custom),
            # Campos que estavam com o valor default antigo e foram atualizados
            # sem --force. Sai no payload para que o setup consiga dizer ao
            # usuario o que mudou no arquivo do time dele.
            "migrated_fields": migrated,
            "entry": written,
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
