# BMAD Module PULSE v1.0 — Plano de Implementacao

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extrair o modulo PULSE do projeto SIP e publica-lo como modulo standalone no BMAD Marketplace (`bmad-module-pulse`).

**Architecture:** Copy + adapt dos 3 skills existentes (track-start, track-done, dashboard) + criacao do skill pulse-setup com scripts Python do padrao BMB. Agente Levi extraido do agent-manifest.csv para formato standalone .agent.yaml. 25 variaveis de configuracao no module.yaml com single-select e defaults opinativos.

**Tech Stack:** BMAD 6.3.0, Python 3.9+ (scripts de setup), YAML/Markdown (skills), pytest (testes dos scripts)

---

## Contexto

### Repo
- **Repo:** `nidelson/bmad-module-pulse` (ja criado, branch `develop`)
- **Local:** `/Users/nidelson/Projects/nidelson/bmad-module-pulse`
- **Template base:** `bmad-code-org/bmad-module-template` (ja clonado)

### Origem dos arquivos (SIP)
- `sip/.claude/skills/bmad-pulse-track-start/` — SKILL.md + workflow.md
- `sip/.claude/skills/bmad-pulse-track-done/` — SKILL.md + workflow.md
- `sip/.claude/skills/bmad-pulse-dashboard/` — SKILL.md + workflow.md
- `sip/_bmad/_config/agent-manifest.csv` — linha do agente Levi (canonicalId: `bmad-pulse-efficiency-analyst`)
- `sip/.claude/skills/bmad-bmb-setup/scripts/` — merge-config.py, merge-help-csv.py, cleanup-legacy.py (padrao de referencia)

### Estrutura Alvo

```
bmad-module-pulse/
├── .claude-plugin/
│   └── marketplace.json
├── skills/
│   ├── pulse-setup/
│   │   ├── SKILL.md
│   │   ├── assets/
│   │   │   ├── module.yaml
│   │   │   └── module-help.csv
│   │   └── scripts/
│   │       ├── merge-config.py
│   │       ├── merge-help-csv.py
│   │       └── cleanup-legacy.py
│   ├── pulse-track-start/
│   │   ├── SKILL.md
│   │   └── workflow.md
│   ├── pulse-track-done/
│   │   ├── SKILL.md
│   │   └── workflow.md
│   └── pulse-dashboard/
│       ├── SKILL.md
│       └── workflow.md
├── agents/
│   └── levi.agent.yaml
├── docs/
│   └── index.md
├── LICENSE
└── README.md
```

### Transformacoes Necessarias nos Skills

Toda referencia hardcoded do SIP deve ser substituida por tokens de config:

| Hardcoded (SIP) | Token (modulo) |
|---|---|
| `{project-root}/_bmad/pulse/config.yaml` | Ler secao `pulse` de `{project-root}/_bmad/config.yaml` |
| `estimated_hours` | `{pulse_field_estimated_hours}` |
| `actual_hours` | `{pulse_field_actual_hours}` |
| `dev_count` | `{pulse_field_dev_count}` |
| `review_cycles` | `{pulse_field_review_cycles}` |
| `category` | `{pulse_field_category}` |
| Categorias `backend/web/mobile/fullstack` | `{pulse_dev_categories}` |
| Threshold `4` (excepcional) | `{pulse_leverage_threshold_exceptional}` |
| Threshold `2` (solido) | `{pulse_leverage_threshold_solid}` |
| `sprint-status.yaml` | `{pulse_sprint_status_filename}` |
| Path do dashboard output | `{pulse_dashboard_folder}` |

---

## Checkpoint 1: Scaffolding + Metadados

### Task 1: Limpar template e configurar repo

**Files:**
- Modify: `LICENSE`
- Modify: `.gitignore`
- Delete: `skills/.gitkeep`

- [ ] **Step 1: Atualizar LICENSE**

```
MIT License

Copyright (c) 2026 Nidelson Gimenez

Permission is hereby granted, free of charge, to any person obtaining a copy
...
```

Substituir `TODO: YEAR YOUR-NAME` por `2026 Nidelson Gimenez`.

- [ ] **Step 2: Verificar .gitignore**

O `.gitignore` do template ja esta adequado. Verificar que contem:

```
_bmad/
_bmad-output/
.*/skills
.env
.DS_Store
```

- [ ] **Step 3: Remover placeholder**

```bash
rm skills/.gitkeep
```

- [ ] **Step 4: Commit**

```bash
git add LICENSE skills/.gitkeep
git commit -m "chore: configurar repo — license e limpeza de placeholders"
```

---

### Task 2: Criar module.yaml com 25 variaveis de configuracao

**Files:**
- Create: `skills/pulse-setup/assets/module.yaml`

- [ ] **Step 1: Criar diretorio**

```bash
mkdir -p skills/pulse-setup/assets
```

- [ ] **Step 2: Escrever module.yaml**

```yaml
code: pulse
name: "PULSE — AI Leverage Monitor"
header: "PULSE: Process Utilization & Leverage Statistics Engine"
subheader: "Mede eficiencia de desenvolvimento assistido por IA com AI Leverage Ratio e Process Health"
description: "Modulo de metricas que calcula AI Leverage Ratio, taxa de first-pass e saude do processo por story. Gera dashboards acumulativos com tendencias e forecasts de capacidade."
module_version: 1.0.0
default_selected: false
module_greeting: >
  PULSE instalado com sucesso! Contra fatos nao ha argumentos.

  Use /pulse-track-start ao iniciar uma story e /pulse-track-done ao concluir.
  Use /pulse-dashboard para ver metricas acumuladas.

  Para duvidas e sugestoes: https://github.com/nidelson/bmad-module-pulse

# Variaveis de Core Config inseridas automaticamente pelo installer:
## user_name
## communication_language
## document_output_language
## output_folder

# ─── SECAO 1: Metodologia de Estimativa ───

pulse_estimation_method:
  prompt: "Qual metodologia de estimativa seu time utiliza?"
  default: "hours"
  result: "{value}"
  single-select:
    - value: "hours"
      label: "Horas (Recomendado — maior precisao)"
    - value: "story_points"
      label: "Story Points (requer fator de calibracao)"
    - value: "tshirt"
      label: "T-Shirt Sizes (S/M/L/XL — normalizado automaticamente)"

pulse_story_point_hours_factor:
  prompt: "Quantas horas em media equivalem a 1 story point no seu time?"
  default: "4.0"
  result: "{value}"
  single-select:
    - value: "2.0"
      label: "2h/ponto — sprints rapidos"
    - value: "4.0"
      label: "4h/ponto — media do mercado (Recomendado)"
    - value: "6.0"
      label: "6h/ponto — dominio complexo"
    - value: "8.0"
      label: "8h/ponto — trabalho de pesquisa"

# ─── SECAO 2: Mapeamento de Campos ───

pulse_field_estimated_hours:
  prompt: "Nome do campo de horas/pontos estimados nos arquivos de story?"
  default: "estimated_hours"
  result: "{value}"

pulse_field_actual_hours:
  prompt: "Nome do campo de horas reais gastas?"
  default: "actual_hours"
  result: "{value}"

pulse_field_dev_count:
  prompt: "Nome do campo de quantidade de devs na story?"
  default: "dev_count"
  result: "{value}"

pulse_field_review_cycles:
  prompt: "Nome do campo de ciclos de revisao?"
  default: "review_cycles"
  result: "{value}"

pulse_field_category:
  prompt: "Nome do campo de categoria na story?"
  default: "category"
  result: "{value}"

# ─── SECAO 3: Categorias de Trabalho ───

pulse_dev_categories:
  prompt: "Quais categorias de trabalho seu projeto utiliza?"
  default: "standard_4"
  result: "{value}"
  single-select:
    - value: "standard_4"
      label: "Standard 4: backend / web / mobile / fullstack (Recomendado)"
    - value: "standard_2"
      label: "Standard 2: backend / frontend"
    - value: "standard_3"
      label: "Standard 3: backend / frontend / mobile"
    - value: "data_heavy"
      label: "Data Heavy: backend / data-eng / ml / frontend"
    - value: "custom"
      label: "Custom (especificar lista separada por virgula)"

pulse_default_category:
  prompt: "Categoria padrao quando uma story nao especifica?"
  default: "fullstack"
  result: "{value}"

# ─── SECAO 4: Thresholds de AI Leverage ───

pulse_leverage_threshold_exceptional:
  prompt: "A partir de qual ratio o AI Leverage e considerado EXCEPCIONAL?"
  default: "3.0"
  result: "{value}"
  single-select:
    - value: "2.5"
      label: "2.5x — Acessivel (times iniciando com IA)"
    - value: "3.0"
      label: "3.0x — Padrao (Recomendado)"
    - value: "4.0"
      label: "4.0x — Exigente (workflows maduros)"
    - value: "5.0"
      label: "5.0x — Elite (workflows de pesquisa)"

pulse_leverage_threshold_solid:
  prompt: "A partir de qual ratio o AI Leverage e considerado SOLIDO?"
  default: "1.8"
  result: "{value}"
  single-select:
    - value: "1.5"
      label: "1.5x — Generoso"
    - value: "1.8"
      label: "1.8x — Padrao (Recomendado)"
    - value: "2.0"
      label: "2.0x — Rigoroso"

pulse_leverage_warning_threshold:
  prompt: "Abaixo de qual ratio emitir alerta de leverage insuficiente?"
  default: "1.2"
  result: "{value}"

# ─── SECAO 5: Armazenamento de Dados ───

pulse_data_strategy:
  prompt: "Como o PULSE deve armazenar os dados de metricas?"
  default: "embedded"
  result: "{value}"
  single-select:
    - value: "embedded"
      label: "Embutido no sprint-status.yaml (Recomendado — zero dependencias)"
    - value: "dedicated"
      label: "Arquivo dedicado pulse-data.yaml por sprint"
    - value: "central"
      label: "Arquivo central pulse-history.yaml acumulativo"

pulse_sprint_status_filename:
  prompt: "Nome do arquivo de sprint status?"
  default: "sprint-status.yaml"
  result: "{value}"

pulse_data_folder:
  prompt: "Pasta onde ficam os arquivos de sprint status?"
  default: "{output_folder}/implementation-artifacts"
  result: "{project-root}/{value}"

# ─── SECAO 6: Dashboard ───

pulse_dashboard_folder:
  prompt: "Onde salvar os dashboards gerados?"
  default: "{output_folder}/implementation-artifacts/pulse-dashboards"
  result: "{project-root}/{value}"

pulse_dashboard_format:
  prompt: "Formato do dashboard?"
  default: "markdown"
  result: "{value}"
  single-select:
    - value: "markdown"
      label: "Markdown — compativel com GitHub, Obsidian, Notion (Recomendado)"
    - value: "yaml"
      label: "YAML estruturado — para consumo programatico"
    - value: "both"
      label: "Ambos — markdown legivel + YAML para automacao"

pulse_include_trend_chart:
  prompt: "Incluir grafico de tendencia no dashboard?"
  default: "yes"
  result: "{value}"
  single-select:
    - value: "yes"
      label: "Sim (Recomendado)"
    - value: "no"
      label: "Nao"

pulse_include_capacity_forecast:
  prompt: "Incluir forecast de capacidade no dashboard?"
  default: "yes"
  result: "{value}"
  single-select:
    - value: "yes"
      label: "Sim (Recomendado)"
    - value: "no"
      label: "Nao"

pulse_min_stories_for_trend:
  prompt: "Minimo de stories para ativar analise de tendencia?"
  default: "3"
  result: "{value}"

# ─── SECAO 7: Agente Levi ───

pulse_levi_verbosity:
  prompt: "Nivel de detalhe nas respostas do Levi?"
  default: "standard"
  result: "{value}"
  single-select:
    - value: "concise"
      label: "Conciso — resumo executivo"
    - value: "standard"
      label: "Padrao — metricas + insights + recomendacoes (Recomendado)"
    - value: "verbose"
      label: "Detalhado — analise completa com contexto educativo"

pulse_levi_coaching_mode:
  prompt: "Levi deve sugerir melhorias de processo proativamente?"
  default: "yes"
  result: "{value}"
  single-select:
    - value: "yes"
      label: "Sim — coaching ativo (Recomendado)"
    - value: "metrics-only"
      label: "Apenas metricas"

# ─── SECAO 8: Process Health ───

pulse_process_health_checks:
  prompt: "Quais checks de saude do processo monitorar?"
  default: "standard"
  result: "{value}"
  single-select:
    - value: "standard"
      label: "Padrao: stories sem ACs, PRs sem review, stories paradas (Recomendado)"
    - value: "strict"
      label: "Rigoroso: padrao + estimativas ausentes, sem TDD, sem story linkage"
    - value: "minimal"
      label: "Minimo: apenas deteccao de blockers"

pulse_alert_on_halt:
  prompt: "Alertar quando a story tiver HALTs registrados?"
  default: "yes"
  result: "{value}"
  single-select:
    - value: "yes"
      label: "Sim — registrar e alertar (Recomendado)"
    - value: "warn"
      label: "Aviso apenas — sem bloqueio"
    - value: "no"
      label: "Nao"

pulse_alert_unused_skills:
  prompt: "Alertar quando skills disponiveis nao forem utilizadas?"
  default: "yes"
  result: "{value}"
  single-select:
    - value: "yes"
      label: "Sim (Recomendado)"
    - value: "no"
      label: "Nao"

# Diretorios a criar durante instalacao
directories:
  - "{pulse_dashboard_folder}"
```

- [ ] **Step 3: Commit**

```bash
git add skills/pulse-setup/assets/module.yaml
git commit -m "feat(setup): criar module.yaml com 25 variaveis de configuracao"
```

---

### Task 3: Criar module-help.csv

**Files:**
- Create: `skills/pulse-setup/assets/module-help.csv`

- [ ] **Step 1: Escrever CSV**

```csv
module,skill,display-name,menu-code,description,action,args,phase,after,before,required,output-location,outputs
PULSE,pulse-track-start,Track Start,TS,"Registrar inicio de implementacao de story",track-start,"[story_id]",anytime,,,false,pulse_data_folder,"pulse_metrics entry"
PULSE,pulse-track-done,Track Done,TD,"Registrar conclusao e calcular metricas",track-done,"[story_id]",anytime,pulse-track-start:track-start,,false,pulse_data_folder,"leverage_ratio first_pass process_health"
PULSE,pulse-dashboard,Dashboard,PD,"Gerar dashboard acumulativo de eficiencia",dashboard,"",anytime,pulse-track-done:track-done,,false,pulse_dashboard_folder,"dashboard markdown"
```

- [ ] **Step 2: Commit**

```bash
git add skills/pulse-setup/assets/module-help.csv
git commit -m "feat(setup): criar module-help.csv com registro de 3 skills"
```

---

### Task 4: Criar agente Levi standalone

**Files:**
- Create: `agents/levi.agent.yaml`

- [ ] **Step 1: Criar diretorio**

```bash
mkdir -p agents
```

- [ ] **Step 2: Extrair e adaptar agente Levi**

Converter a linha do `agent-manifest.csv` (canonicalId: `bmad-pulse-efficiency-analyst`) para formato standalone `.agent.yaml`:

```yaml
agent:
  metadata:
    id: "pulse/agents/levi.agent.yaml"
    name: Levi
    title: Hyper-Efficiency Analyst & SDLC Optimizer
    icon: "\u26A1"
    module: pulse
    hasSidecar: false

  persona:
    role: Hyper-Efficiency Analyst + SDLC Optimizer
    identity: >-
      Analista de performance obcecado por dados de eficiencia. Background em
      engenharia de producao e analytics. Transforma numeros em narrativas de
      melhoria. Especialista em metricas de AI-assisted development e
      otimizacao continua do SDLC.
    communication_style: >-
      Fala com dados mas traduz em insights acionaveis. Celebra conquistas com
      entusiasmo contido. Alerta com pragmatismo. Competitividade saudavel —
      faz o time querer bater o proprio recorde.
    principles:
      - O que se mede com dados reais, se melhora com acoes reais
      - Leverage nao e sobre velocidade — e sobre alavancagem de capacidade
      - Metricas sem acao sao decoracao de dashboard
      - Process Health e tao importante quanto Efficiency

  critical_actions:
    - "Ler configuracao do modulo PULSE em {project-root}/_bmad/config.yaml secao 'pulse'"
    - "Usar thresholds configurados para classificar leverage (exceptional/solid/warning)"
    - "Comunicar no idioma configurado em communication_language"

  menu:
    - trigger: "MH or fuzzy match on menu-help"
      description: "[MH] Redisplay Menu Help"
      action: display_help

    - trigger: "CH or fuzzy match on chat"
      description: "[CH] Chat com Levi sobre eficiencia, metricas e processo"
      action: chat_mode

    - trigger: "TS or fuzzy match on track-start"
      skill: "pulse-track-start"
      description: "[TS] Track Start: Registrar inicio de story"

    - trigger: "TD or fuzzy match on track-done"
      skill: "pulse-track-done"
      description: "[TD] Track Done: Registrar conclusao e calcular metricas"

    - trigger: "PD or fuzzy match on pulse-dashboard"
      skill: "pulse-dashboard"
      description: "[PD] Dashboard: Gerar dashboard acumulativo"

    - trigger: "DA or fuzzy match on dismiss-agent"
      description: "[DA] Dismiss Agent"
      action: exit
```

- [ ] **Step 3: Commit**

```bash
git add agents/levi.agent.yaml
git commit -m "feat(agent): criar agente Levi standalone para modulo PULSE"
```

---

## REVIEW CHECKPOINT 1

**Revisar antes de continuar:**
- [ ] `module.yaml` tem todas as 25 variaveis com prompts, defaults e single-selects
- [ ] `module-help.csv` tem 3 entradas (track-start, track-done, dashboard) com headers corretos
- [ ] `levi.agent.yaml` segue o schema BMAD Core (metadata, persona, critical_actions, menu)
- [ ] Nenhuma referencia ao SIP nos arquivos criados
- [ ] Todos os commits estao na branch `develop`

---

## Checkpoint 2: Skills Operacionais (Parallelizable)

### Task 5: Adaptar skill pulse-track-start

**Files:**
- Create: `skills/pulse-track-start/SKILL.md`
- Create: `skills/pulse-track-start/workflow.md`

**Source:** `sip/.claude/skills/bmad-pulse-track-start/`

- [ ] **Step 1: Criar diretorio**

```bash
mkdir -p skills/pulse-track-start
```

- [ ] **Step 2: Copiar SKILL.md do SIP e adaptar**

Copiar `sip/.claude/skills/bmad-pulse-track-start/SKILL.md` e fazer estas substituicoes:

Original:
```yaml
main_config: '{project-root}/_bmad/pulse/config.yaml'
```

Novo:
```yaml
main_config: '{project-root}/_bmad/config.yaml'
config_section: 'pulse'
```

- [ ] **Step 3: Copiar workflow.md do SIP e adaptar**

Copiar `sip/.claude/skills/bmad-pulse-track-start/workflow.md` e aplicar substituicoes:

1. Na secao INICIALIZACAO — trocar:
   - `Carregar config de {main_config}` → `Carregar secao pulse de {main_config}`
   - Adicionar: `Resolver variaveis de campo: {pulse_field_estimated_hours}, {pulse_field_dev_count}, {pulse_field_category}`

2. No Passo 2 (Extrair Dados da Story) — trocar:
   - `estimated_hours` literal → `o campo configurado em pulse_field_estimated_hours`
   - `dev_count` literal → `o campo configurado em pulse_field_dev_count`
   - `task_count` → manter (campo interno do PULSE, nao configuravel)
   - `category` literal → `o campo configurado em pulse_field_category`
   - Categorias hardcoded `backend/web/mobile/fullstack` → `as categorias configuradas em pulse_dev_categories`

3. No Passo 3 (Registrar no sprint-status.yaml) — trocar:
   - `sprint-status.yaml` → `o arquivo configurado em pulse_sprint_status_filename`

4. Na secao RESTRICOES — adicionar:
   - `Comunicar no idioma configurado em communication_language`

- [ ] **Step 4: Verificar que nao ha referencias ao SIP**

```bash
grep -ri "sip" skills/pulse-track-start/ || echo "OK: nenhuma referencia ao SIP"
```

- [ ] **Step 5: Commit**

```bash
git add skills/pulse-track-start/
git commit -m "feat(track-start): adaptar skill de registro de inicio para modulo standalone"
```

---

### Task 6: Adaptar skill pulse-track-done

**Files:**
- Create: `skills/pulse-track-done/SKILL.md`
- Create: `skills/pulse-track-done/workflow.md`

**Source:** `sip/.claude/skills/bmad-pulse-track-done/`

- [ ] **Step 1: Criar diretorio**

```bash
mkdir -p skills/pulse-track-done
```

- [ ] **Step 2: Copiar SKILL.md do SIP e adaptar**

Mesma transformacao do Task 5 Step 2:
- `main_config` → `{project-root}/_bmad/config.yaml` com `config_section: 'pulse'`

- [ ] **Step 3: Copiar workflow.md do SIP e adaptar**

Copiar `sip/.claude/skills/bmad-pulse-track-done/workflow.md` e aplicar:

1. INICIALIZACAO — mesmas mudancas do Task 5 Step 3 item 1

2. Passo 2 (Registrar Conclusao) — sem mudancas (campos internos do PULSE)

3. Passo 3 (Calcular Metricas) — sem mudancas na formula (fixa por design):
   ```
   leverage_ratio = estimated_hours / actual_hours
   ```
   Mas se `pulse_estimation_method` for `story_points`, adicionar conversao:
   ```
   estimated_hours = story_points * pulse_story_point_hours_factor
   ```

4. Passo 4 (Efficiency Pulse + Process Health) — trocar thresholds:
   - `leverage_ratio >= 4` → `leverage_ratio >= {pulse_leverage_threshold_exceptional}`
   - `leverage_ratio >= 2` → `leverage_ratio >= {pulse_leverage_threshold_solid}`
   - Adicionar: `leverage_ratio < {pulse_leverage_warning_threshold}` → emitir alerta

5. Process Health — parametrizar:
   - Verificacao de HALTs: respeitar `pulse_alert_on_halt` (yes/warn/no)
   - Skills subutilizadas: respeitar `pulse_alert_unused_skills` (yes/no)
   - Nivel de checks: respeitar `pulse_process_health_checks` (standard/strict/minimal)

6. Passo 5 e 6 — mesmas mudancas de campo do Task 5

7. RESTRICOES — adicionar:
   - `Comunicar no idioma configurado em communication_language`
   - `Respeitar pulse_levi_verbosity para nivel de detalhe`
   - `Respeitar pulse_levi_coaching_mode para sugestoes de processo`

- [ ] **Step 4: Verificar que nao ha referencias ao SIP**

```bash
grep -ri "sip" skills/pulse-track-done/ || echo "OK: nenhuma referencia ao SIP"
```

- [ ] **Step 5: Commit**

```bash
git add skills/pulse-track-done/
git commit -m "feat(track-done): adaptar skill de conclusao e metricas para modulo standalone"
```

---

### Task 7: Adaptar skill pulse-dashboard

**Files:**
- Create: `skills/pulse-dashboard/SKILL.md`
- Create: `skills/pulse-dashboard/workflow.md`

**Source:** `sip/.claude/skills/bmad-pulse-dashboard/`

- [ ] **Step 1: Criar diretorio**

```bash
mkdir -p skills/pulse-dashboard
```

- [ ] **Step 2: Copiar SKILL.md do SIP e adaptar**

Mesma transformacao dos Tasks anteriores para `main_config` e `config_section`.

- [ ] **Step 3: Copiar workflow.md do SIP e adaptar**

Copiar `sip/.claude/skills/bmad-pulse-dashboard/workflow.md` e aplicar:

1. INICIALIZACAO — mesmas mudancas de config

2. Caminhos — trocar:
   - `dashboard_file` → usar `{pulse_dashboard_folder}/dashboard.md`

3. Passo 1 (Coletar Dados) — trocar:
   - `sprint_status_file` → usar `{pulse_data_folder}/{pulse_sprint_status_filename}`

4. Passo 2 (Gerar Dashboard) — parametrizar:
   - Secao de tendencia: condicional em `pulse_include_trend_chart`
   - Secao de forecast: condicional em `pulse_include_capacity_forecast`
   - Formato: respeitar `pulse_dashboard_format` (markdown/yaml/both)
   - Categorias na tabela: usar `{pulse_dev_categories}` em vez de hardcoded

5. Template do dashboard — trocar:
   - `> Projeto: {project_name}` → manter mas ler de config
   - `> Criado por: Nidelson Gimenez` → REMOVER (era SIP-specific)
   - Manter tagline: `_PULSE — Contra fatos nao ha argumentos._`

6. RESTRICOES — adicionar idioma e verbosidade

- [ ] **Step 4: Verificar que nao ha referencias ao SIP**

```bash
grep -ri "sip\|nidelson\|coremax" skills/pulse-dashboard/ || echo "OK: nenhuma referencia ao SIP"
```

- [ ] **Step 5: Commit**

```bash
git add skills/pulse-dashboard/
git commit -m "feat(dashboard): adaptar skill de dashboard para modulo standalone"
```

---

## REVIEW CHECKPOINT 2

**Revisar antes de continuar:**
- [ ] Os 3 skills existem em `skills/` com SKILL.md + workflow.md cada
- [ ] Nenhum skill referencia `_bmad/pulse/config.yaml` — todos leem secao `pulse` de `_bmad/config.yaml`
- [ ] Nenhuma referencia hardcoded a SIP, Nidelson, CoreMAX
- [ ] Campos de story usam tokens de config (`pulse_field_*`)
- [ ] Categorias usam `pulse_dev_categories`
- [ ] Thresholds usam `pulse_leverage_threshold_*`
- [ ] Todos os commits estao na branch `develop`

---

## Checkpoint 3: Setup Skill + Scripts Python

### Task 8: Copiar e adaptar scripts Python do padrao BMB

**Files:**
- Create: `skills/pulse-setup/scripts/merge-config.py`
- Create: `skills/pulse-setup/scripts/merge-help-csv.py`
- Create: `skills/pulse-setup/scripts/cleanup-legacy.py`

**Source:** `sip/.claude/skills/bmad-bmb-setup/scripts/`

- [ ] **Step 1: Criar diretorio**

```bash
mkdir -p skills/pulse-setup/scripts
```

- [ ] **Step 2: Copiar merge-config.py**

Copiar `sip/.claude/skills/bmad-bmb-setup/scripts/merge-config.py` sem alteracoes.

Este script e generico — le `module.yaml` e `answers.json`, faz merge na `config.yaml` do projeto alvo. Nao tem nenhuma referencia ao BMB hardcoded. O `module_code` vem do `module.yaml` (que define `code: pulse`).

Verificar:
```bash
grep -i "bmb\|bmad-builder" skills/pulse-setup/scripts/merge-config.py || echo "OK: generico"
```

- [ ] **Step 3: Copiar merge-help-csv.py**

Copiar `sip/.claude/skills/bmad-bmb-setup/scripts/merge-help-csv.py` sem alteracoes.

Mesmo raciocinio — script generico que le source CSV e faz merge no target.

- [ ] **Step 4: Copiar cleanup-legacy.py**

Copiar `sip/.claude/skills/bmad-bmb-setup/scripts/cleanup-legacy.py` sem alteracoes.

- [ ] **Step 5: Tornar executaveis**

```bash
chmod +x skills/pulse-setup/scripts/*.py
```

- [ ] **Step 6: Commit**

```bash
git add skills/pulse-setup/scripts/
git commit -m "feat(setup): copiar scripts Python do padrao BMB (merge-config, merge-help-csv, cleanup-legacy)"
```

---

### Task 9: Criar SKILL.md do pulse-setup

**Files:**
- Create: `skills/pulse-setup/SKILL.md`

**Referencia:** `sip/.claude/skills/bmad-bmb-setup/SKILL.md` (padrao a seguir)

- [ ] **Step 1: Escrever SKILL.md**

Seguir exatamente o padrao do `bmad-bmb-setup/SKILL.md`, adaptando para o modulo PULSE:

```markdown
---
name: pulse-setup
description: Instala e configura o modulo PULSE em um projeto BMAD. Use quando o usuario solicitar 'instalar PULSE', 'configurar PULSE', ou 'setup PULSE'.
---

# Module Setup

## Overview

Installs and configures a BMad module into a project. Module identity (name, code, version) comes from `./assets/module.yaml`. Collects user preferences and writes them to three files:

- **`{project-root}/_bmad/config.yaml`** — shared project config: core settings at root plus a section per module with metadata and module-specific values. User-only keys (`user_name`, `communication_language`) are **never** written here.
- **`{project-root}/_bmad/config.user.yaml`** — personal settings intended to be gitignored: `user_name`, `communication_language`, and any module variable marked `user_setting: true` in `./assets/module.yaml`.
- **`{project-root}/_bmad/module-help.csv`** — registers module capabilities for the help system.

Both config scripts use an anti-zombie pattern — existing entries for this module are removed before writing fresh ones, so stale values never persist.

`{project-root}` is a **literal token** in config values — never substitute it with an actual path.

## On Activation

1. Read `./assets/module.yaml` for module metadata and variable definitions (the `code` field is the module identifier)
2. Check if `{project-root}/_bmad/config.yaml` exists — if a section matching the module's code is already present, inform the user this is an update
3. Check for per-module configuration at `{project-root}/_bmad/pulse/config.yaml` and `{project-root}/_bmad/core/config.yaml`. If either file exists:
   - If `{project-root}/_bmad/config.yaml` does **not** yet have a section for this module: this is a **fresh install**
   - If `{project-root}/_bmad/config.yaml` **already** has a section for this module: this is a **legacy migration**
   - In both cases, per-module config files and directories will be cleaned up after setup

If the user provides arguments (e.g. `accept all defaults`, `--headless`, or inline values), map any provided values to config keys, use defaults for the rest, and skip interactive prompting. Still display the full confirmation summary at the end.

## Collect Configuration

Ask the user for values. Show defaults in brackets. Present all values together so the user can respond once with only the values they want to change. Never tell the user to "press enter" or "leave blank".

**Default priority** (highest wins): existing new config values > legacy config values > `./assets/module.yaml` defaults.

**Core config** (only if no core keys exist yet): `user_name`, `communication_language` and `document_output_language`, `output_folder`.

**Module config**: Read each variable in `./assets/module.yaml` that has a `prompt` field. Ask using that prompt with its default value.

**Validation rules:**
- Se `pulse_estimation_method` = `story_points` e `pulse_story_point_hours_factor` nao foi definido, alertar antes de continuar
- Se `pulse_dev_categories` = `custom`, pedir lista separada por virgula

## Write Files

Write a temp JSON file with the collected answers structured as `{"core": {...}, "module": {...}}`. Then run both scripts in parallel:

```bash
python3 ./scripts/merge-config.py --config-path "{project-root}/_bmad/config.yaml" --user-config-path "{project-root}/_bmad/config.user.yaml" --module-yaml ./assets/module.yaml --answers {temp-file} --legacy-dir "{project-root}/_bmad"
python3 ./scripts/merge-help-csv.py --target "{project-root}/_bmad/module-help.csv" --source ./assets/module-help.csv --legacy-dir "{project-root}/_bmad" --module-code pulse
```

## Create Output Directories

After writing config, create any output directories configured. Resolve `{project-root}` to actual project root and create each path-type value that does not yet exist. Use `mkdir -p`.

## Cleanup Legacy Directories

After both merge scripts complete successfully, remove legacy directories:

```bash
python3 ./scripts/cleanup-legacy.py --bmad-dir "{project-root}/_bmad" --module-code pulse --skills-dir "{project-root}/.claude/skills"
```

## Confirm

Display what was written — config values set, help entries added, fresh install vs update. Then display the `module_greeting`.

## Outcome

Once the user's `user_name` and `communication_language` are known, use them consistently for the remainder of the session.
```

- [ ] **Step 2: Commit**

```bash
git add skills/pulse-setup/SKILL.md
git commit -m "feat(setup): criar SKILL.md do pulse-setup seguindo padrao BMB"
```

---

## REVIEW CHECKPOINT 3

**Revisar antes de continuar:**
- [ ] `pulse-setup/` tem: SKILL.md, assets/module.yaml, assets/module-help.csv, scripts/*.py
- [ ] Scripts Python sao executaveis (`chmod +x`)
- [ ] SKILL.md referencia `module-code pulse` (nao bmb)
- [ ] Validation rules para story_points + custom categories estao documentadas
- [ ] Scripts sao genericos — nenhuma referencia hardcoded a BMB ou SIP

---

## Checkpoint 4: Metadados e Publicacao

### Task 10: Preencher marketplace.json

**Files:**
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Atualizar marketplace.json**

```json
{
  "name": "bmad-module-pulse",
  "owner": { "name": "Nidelson Gimenez" },
  "license": "MIT",
  "homepage": "https://github.com/nidelson/bmad-module-pulse",
  "repository": "https://github.com/nidelson/bmad-module-pulse",
  "keywords": ["bmad", "metrics", "ai-leverage", "efficiency", "pulse", "process-health"],
  "plugins": [
    {
      "name": "bmad-module-pulse",
      "source": "./",
      "description": "Mede eficiencia de desenvolvimento assistido por IA com AI Leverage Ratio, first-pass rate e Process Health.",
      "version": "1.0.0",
      "author": { "name": "Nidelson Gimenez" },
      "skills": [
        "./skills/pulse-setup",
        "./skills/pulse-track-start",
        "./skills/pulse-track-done",
        "./skills/pulse-dashboard"
      ]
    }
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "feat: preencher marketplace.json com metadados do PULSE"
```

---

### Task 11: Escrever README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Substituir README do template**

```markdown
# PULSE — Process Utilization & Leverage Statistics Engine

> Prove the ROI of AI-Assisted Development

[![BMAD Module](https://img.shields.io/badge/BMAD-Module-blue)](https://docs.bmad-method.org/)
[![Python Version](https://img.shields.io/badge/python-%3E%3D3.9-blue?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Em algum momento, todo desenvolvedor que trabalha com IA viveu este momento: olhou para o relogio, percebeu que fez em duas horas o que estimou para dois dias, e nao soube ao certo o que fazer com aquela sensacao.

O PULSE foi construido para esse momento. Para transformar aquela sensacao em um numero. Aquele numero em uma historia. E aquela historia em evidencia.

## O que o PULSE mede

| Metrica | O que e | Por que importa |
|---|---|---|
| **AI Leverage Ratio** | `horas_estimadas / horas_reais` | Quanto a IA multiplicou sua capacidade |
| **First-Pass Rate** | % de stories aprovadas sem revisao | Qualidade do processo de desenvolvimento |
| **Process Health** | Aderencia ao workflow BMAD | Saude do processo (HALTs, skills subutilizadas) |

## Instalacao

```bash
npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse
```

## Skills Incluidas

| Skill | Comando | Funcao |
|---|---|---|
| `pulse-setup` | `/pulse-setup` | Configurar o modulo no seu projeto |
| `pulse-track-start` | `/pulse-track-start [story_id]` | Registrar inicio de story |
| `pulse-track-done` | `/pulse-track-done [story_id]` | Registrar conclusao + calcular metricas |
| `pulse-dashboard` | `/pulse-dashboard` | Gerar dashboard acumulativo |

## Agente

**Levi** — Hyper-Efficiency Analyst. Apresenta metricas com personalidade, celebra conquistas e sugere melhorias de processo.

## Configuracao

O PULSE oferece 25 variaveis configuraveis com defaults opinativos. Durante o setup (`/pulse-setup`), voce pode customizar:

- **Metodologia de estimativa** — horas, story points ou t-shirt sizes
- **Mapeamento de campos** — adapta nomes de campos do seu projeto
- **Categorias de trabalho** — backend/web/mobile/fullstack ou custom
- **Thresholds de leverage** — quando considerar excepcional, solido ou alerta
- **Dashboard** — formato, secoes e forecasts
- **Process Health** — nivel de checks e alertas

## Requisitos

- BMAD Method >= 6.3.0
- Python >= 3.9 (para scripts de setup)

## Licenca

MIT

---

_PULSE — Contra fatos nao ha argumentos._
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: escrever README com posicionamento e instrucoes de instalacao"
```

---

### Task 12: Atualizar docs/index.md

**Files:**
- Modify: `docs/index.md`

- [ ] **Step 1: Substituir conteudo placeholder**

```markdown
# PULSE — Documentacao

## Inicio Rapido

1. Instale o modulo: `npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse`
2. Configure: `/pulse-setup`
3. Ao iniciar uma story: `/pulse-track-start`
4. Ao concluir: `/pulse-track-done`
5. Para ver o dashboard: `/pulse-dashboard`

## Referencia de Metricas

### AI Leverage Ratio

```
leverage = estimated_hours / actual_hours
```

- >= 3.0x: Excepcional
- >= 1.8x: Solido
- < 1.2x: Alerta

### First-Pass Rate

Percentual de stories aprovadas com `review_cycles == 1`.

### Process Health

Score composto baseado em:
- Fluxo BMAD completo (create-story → dev-story → code-review → done)
- Contagem de HALTs
- Skills disponiveis mas nao utilizadas

## Configuracao Avancada

Consulte o [module.yaml](../skills/pulse-setup/assets/module.yaml) para a lista completa de variaveis configuraveis.
```

- [ ] **Step 2: Commit**

```bash
git add docs/index.md
git commit -m "docs: atualizar index.md com documentacao do PULSE"
```

---

## REVIEW CHECKPOINT 4 (Final)

**Validacao pre-publicacao:**
- [ ] `marketplace.json` — JSON valido, paths de skills corretos, versao 1.0.0
- [ ] `module.yaml` — 25 variaveis com prompts e defaults
- [ ] `module-help.csv` — 3 entradas, headers corretos, encoding UTF-8
- [ ] `levi.agent.yaml` — schema valido, sem referencias ao SIP
- [ ] 3 skills — SKILL.md + workflow.md cada, sem hardcodes
- [ ] `pulse-setup/SKILL.md` — segue padrao BMB
- [ ] Scripts Python — executaveis, genericos
- [ ] `README.md` — posicionamento claro, instrucoes de instalacao
- [ ] `LICENSE` — MIT com nome e ano corretos
- [ ] Zero referencias a SIP, CoreMAX, Nidelson (exceto LICENSE e README author)
- [ ] Todos os commits na branch `develop`

```bash
# Validacao final
grep -ri "sip\b" skills/ agents/ || echo "OK: zero referencias ao SIP nos skills/agents"
grep -ri "coremax" . --include="*.md" --include="*.yaml" --include="*.csv" --include="*.json" || echo "OK: zero referencias CoreMAX"
```

**Apos aprovacao do checkpoint:**

```bash
git push origin develop
```

---

## Proximo: Testes (pos-v1.0)

Apos o push da v1.0 no develop, os proximos passos sao:

1. **Testes Python** — pytest para merge-config.py, merge-help-csv.py, cleanup-legacy.py
2. **Validacao estrutural** — schema validation do module.yaml e marketplace.json
3. **Smoke test** — instalar em projeto BMAD vazio e executar os 3 skills
4. **Tag v1.0.0** — merge develop → main, tag, push
5. **Submeter ao marketplace** — PR para `bmad-plugins-marketplace`
