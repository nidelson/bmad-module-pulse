# PULSE

[![BMAD Module](https://img.shields.io/badge/BMAD-Module-blue)](https://docs.bmad-method.org/)
[![BMAD Version](https://img.shields.io/badge/BMAD-%3E%3D6.4.0-blue)](https://docs.bmad-method.org/)
[![Tests](https://github.com/nidelson/bmad-module-pulse/actions/workflows/test.yaml/badge.svg)](https://github.com/nidelson/bmad-module-pulse/actions/workflows/test.yaml)
[![GitHub release](https://img.shields.io/github/v/release/nidelson/bmad-module-pulse)](https://github.com/nidelson/bmad-module-pulse/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/nidelson/bmad-module-pulse?style=social)](https://github.com/nidelson/bmad-module-pulse/stargazers)

> **PULSE — Sinais de alavancagem de IA para times BMAD.**

**Prove que sua IA está mesmo entregando mais rápido — ou descubra onde ela trava.**

🌐 [English 🇺🇸](README.md)

> *Saída exemplo de `/bmad-pulse-dashboard` — baseado em projeto BMAD real:*

### 🏆 Estatísticas Gerais

| Métrica                | Valor     |
| ---------------------- | --------- |
| Stories medidas        | 12        |
| Alavancagem AI média   | **6.9x**  |
| Horas estimadas humano | 152h      |
| Horas reais AI         | 22h       |
| Horas economizadas     | **130h**  |
| Taxa de first-pass     | 83%       |

### 📈 Tendência de Alavancagem por Epic

```text
Epic  1: ████████░░░░░░░░░░░░  4.2x (3 stories)
Epic  4: ██████████░░░░░░░░░░  5.1x (2 stories)
Epic  5: ████████████████░░░░  7.8x (3 stories)
Epic 14: ██████████████░░░░░░  6.9x (3 stories)
Epic 15: ████████████████████  8.4x (1 story)
```

📊 **[Ver dashboard completo →](examples/dashboards/mature-bmad-team.md)** *(quebra por categoria, previsão de capacidade, insights do Levi, breakdown story-a-story)*

Veja [mais cenários de dashboard](examples/dashboards/) para diferentes tamanhos de time e estágios de adoção.

---

## O Problema

Em algum momento, todo desenvolvedor que trabalha com IA já viveu este instante: olhou para o relógio, percebeu que fez em duas horas o que estimou em dois dias, e não soube muito bem o que fazer com aquela sensação.

PULSE foi construído para esse momento. Para transformar essa sensação em número. Esse número em história. E essa história em evidência.

Você adotou BMAD. Plugou Claude Code ou Cursor. Seu time *parece* mais rápido — mas quando a liderança pergunta **"quão mais rápido?"**, você está chutando.

Toda ferramenta de produtividade de IA mede **linhas de código**, **commits** ou **gasto de tokens**. Nenhuma responde a pergunta que seu CTO está realmente fazendo: *estamos entregando mais valor visível ao usuário por hora de engenharia?*

Existem dois tipos de time em 2026: **o time que usa IA, e o time que tem IA usando IA.** A diferença não aparece em linhas de código. Aparece em stories entregues por hora estimada.

PULSE mede isso!

---

## O que você ganha

- **Um número defensável de ROI da IA no seu SDLC** — razão de alavancagem, calculada sprint a sprint, pronta para o seu deck de stakeholders.
- **Aviso antecipado de trabalho travado** — previsões de capacidade e alertas de halt antes da sprint escorregar.
- **Um coach, não só um dashboard** — Levi (o agente do PULSE) lê seus sinais e te diz *onde* a alavancagem está vazando.

---

## Por que PULSE

**O mercado mede linhas. PULSE mede stories.**

É a diferença entre **peso na balança e percentual de gordura corporal**. LOC te diz que algo está se mexendo. Alavancagem te diz se é músculo ou inchaço.

Uma story é a menor unidade de valor que seu usuário sente. Acompanhar alavancagem de IA no nível da story — horas estimadas vs. horas reais, do planning ao done — te dá a única métrica que sobrevive a uma reunião de board.

PULSE também é o **primeiro plugin de observabilidade BMAD-native** do marketplace. Não existe incumbente. Não existe segundo lugar ainda. Se você roda BMAD e quer analytics de SDLC que falem o vocabulário BMAD (epics, stories, agentes, workflows), essa é a ferramenta.

> Stories, não linhas.
> Outcomes, não output.
> Alavancagem, não atividade.

---

## O que PULSE mede

| Métrica | O que é | Por que importa |
|---------|---------|-----------------|
| **AI Leverage Ratio** | `horas_estimadas / horas_reais` | Quanto a IA multiplicou sua capacidade |
| **First-Pass Rate** | % de stories aprovadas sem revisão | Qualidade do processo de desenvolvimento |
| **Process Health** | Aderência ao workflow BMAD | Halts, skills subutilizadas, drift |

---

## Quick start

```bash
npx bmad-method install --custom-source https://github.com/nidelson/bmad-module-pulse
```

Depois, no seu projeto BMAD:

```bash
/bmad-pulse-setup            # Configure uma vez
/bmad-pulse-track-start      # Quando começar uma story
/bmad-pulse-track-done       # Quando terminar — alavancagem é calculada
/bmad-pulse-dashboard        # Veja a tendência cumulativa
```

PULSE se conecta aos seus arquivos de story BMAD existentes — sem migrations, sem banco separado.

---

## Skills inclusas

> ⚠ **Atualizando da v0.3.x?** Os slash commands foram renomeados de `pulse-*` para `bmad-pulse-*` na v0.4.0. Leia **[MIGRATION.md](docs/MIGRATION.md)** antes de atualizar — v0.4.0 tem BREAKING CHANGES.

| Skill | Comando | Função |
|---|---|---|
| `bmad-pulse-setup` | `/bmad-pulse-setup` | Configura o módulo no seu projeto |
| `bmad-pulse-track-start` | `/bmad-pulse-track-start [story_id]` | Registra início da story |
| `bmad-pulse-track-done` | `/bmad-pulse-track-done [story_id]` | Registra conclusão + calcula métricas |
| `bmad-pulse-dashboard` | `/bmad-pulse-dashboard` | Gera dashboard cumulativo |

---

## Levi — seu agente coach

**Levi** é o Analista de Hyper-Efficiency do PULSE. Ele lê suas métricas e te diz, em linguagem clara, onde o squad está perdendo tempo: drift de estimativa, etapas BMAD sendo puladas, agentes mal utilizados. Comemora vitórias reais, aponta desvios e sugere correções no processo.

Ele não moraliza. Ele aponta.

---

## Como funciona

PULSE instrumenta três pontos no ciclo de vida da story BMAD:

1. **Story start** — captura horas estimadas do arquivo da story.
2. **Story done** — captura horas reais e calcula a razão de alavancagem.
3. **Sprint rollup** — agrega alavancagem na sprint ativa e projeta capacidade.

### Limiares de alavancagem

| Razão | Sinal | O que significa |
|-------|--------|---------------|
| **≥ 3.0x** | Excepcional | IA está comprimindo materialmente seu SDLC. Documente o padrão, replique. |
| **1.8x – 2.9x** | Sólido | Alavancagem saudável. A norma para times BMAD maduros. |
| **1.2x – 1.7x** | Atenção | Ganho marginal. Investigue onde a IA está desacelerando. |
| **< 1.2x** | Alerta | IA não está puxando o peso dela. Levi vai apontar a causa provável. |

### Capacidades

- **Track** — horas estimadas vs. reais por story, timestamps de início/fim, atribuição por agente.
- **Aggregate** — dashboard cumulativo com tendências semanais e por sprint.
- **Forecast** — projeção de capacidade baseada em alavancagem rolante e velocidade do time.
- **Audit** — checagens de saúde de processo: stories sem estimativa, trabalho parado, artefatos faltando.
- **Alert** — detecção de halt quando uma story trava além da estimativa.
- **Coach** — Levi lê as métricas e aponta gargalos em linguagem clara.

---

## Configuração

PULSE oferece 25 variáveis configuráveis com defaults opinionated. Durante o setup (`/bmad-pulse-setup`), você customiza:

- **Metodologia de estimativa** — horas, story points ou t-shirt sizes
- **Mapeamento de campos** — adapta nomes de campos do seu projeto
- **Categorias de trabalho** — backend/web/mobile/fullstack ou customizado
- **Limiares de alavancagem** — quando considerar excepcional, sólido ou alerta
- **Dashboard** — formato, seções e previsões
- **Process Health** — nível de checagens e alertas

---

## Alavancagem comprovada

Alavancagem sustentada de **6.9x** medida em um projeto BMAD em produção (SIP — plataforma de pesquisa local-first, monorepo com apps mobile, web, backend e worker). O número reflete stories entregues com horas estimadas e reais capturadas pelo próprio PULSE ao longo de múltiplas sprints.

PULSE usa o próprio remédio.

Esse número não é o teto. É um ponto de dado. PULSE existe para que seu time encontre o dele.

---

## Roadmap

- **v0.5** — Dashboard navegável por período (visões semana / sprint / trimestre, comparação lado a lado)
- **v0.6** — Quebras de alavancagem por desenvolvedor e por agente, com guards de privacidade ativos por padrão
- **v0.7** — Digests no Slack e Linear para sinais chegarem à liderança sem reunião
- **v1.0** — Adoção nativa no BMAD core, em discussão com mantenedores

---

## Requisitos

- **BMAD Method** >= 6.4.0 (veja [MIGRATION.md](docs/MIGRATION.md) se atualizando da v0.3.x)
- **Python** >= 3.9 (para scripts de setup)
- **Assistente de IA** agnóstico — Claude Code, Cursor, Copilot ou qualquer outro. PULSE mede o squad, não a IDE.

---

## Comunidade

- [Discord](https://discord.gg/gk8jAdXWmj) — Comunidade BMad Method
- [Issues](https://github.com/nidelson/bmad-module-pulse/issues) — Reports de bugs e pedidos de features

## Histórico de stars

[Ver histórico em star-history.com](https://star-history.com/#nidelson/bmad-module-pulse)

## Licença

MIT — veja [LICENSE](LICENSE).

---

_PULSE — Contra fatos, não há argumentos._
