# ⚡ PULSE — O Pulso de Entrega do Time

> Sinais de previsibilidade e alavancagem de entrega para times BMAD<br>
> Gerado em: 2026-06-27 22:46 | Projeto: SIP

---

## 🏆 Estatísticas Gerais

| Métrica                                   | Valor                                |
| ----------------------------------------- | ------------------------------------ |
| Stories medidas                           | 12                                   |
| **Previsibilidade**                       | **88% (mediana) ↑ convergindo** — margem de erro 12% |
| Horas reais (IA)                          | 24h                                  |
| Taxa de first-pass                        | 83%                                  |
| **Alavancagem (vs REFERÊNCIA)**           | **6.9x — o número que vende (vs cotação de mercado, não colapsa)** |
| Horas vs benchmark de referência (152h)   | **128h economizadas**                |

> **Previsibilidade é o número-herói** — acurácia, **maior = melhor, meta 100%** (`↑` = subindo). **Três conceitos fixos:** *Previsibilidade* (88%, meta 100%) e *Margem de erro* (12%, meta 0% quando calibrado) são duas faces da acurácia; *Alavancagem* (6.9x vs REFERÊNCIA) é o multiplicador ortogonal que vende. A razão `estimated_hours / actual_hours` (vs PLANO) colapsou pra ~1.0x ao calibrar — **é a previsibilidade, não é mostrada como alavancagem**. A Alavancagem usa um denominador **frozen** (cotação de mercado, governado pelo `bmad-module-bcp`), que **não colapsa**.

> **Invariante anti-Goodhart — leverage não é meta.** `leverage = estimated_hours / actual_hours`. Quando a base de estimativa calibra, a razão vs-PLANO colapsa para **~1.0x por construção** — então um multiplicador vs-plano *alto* sinaliza base inflada, **não** velocidade. O sinal durável é a **previsibilidade** (drift de h/BCP convergindo a zero). A alavancagem vs REFERÊNCIA frozen é reportada como **ROI honesto vs um benchmark fixo** (cadência de board), nunca "vs humano" e nunca como meta.

## 📈 Tendência de Alavancagem (vs REFERÊNCIA frozen) por Epic

Sparkline: cada █ = 0.5x de alavancagem vs referência frozen, máximo 20 caracteres.

```text
Epic  1: ████████░░░░░░░░░░░░  4.2x (3 stories)
Epic  4: ██████████░░░░░░░░░░  5.1x (2 stories)
Epic  5: ████████████████░░░░  7.8x (3 stories)
Epic 14: ██████████████░░░░░░  6.9x (3 stories)
Epic 15: ████████████████████  8.4x (1 story)
```

> Estável por construção: o denominador (referência frozen) não muda quando o time calibra. A alavancagem vs PLANO destes mesmos epics já colapsou para ~1.0–1.2x (veja o detalhamento) — é a previsibilidade.

## 📊 Alavancagem por Categoria (vs REFERÊNCIA frozen)

| Categoria  | Leverage médio (vs REF) | Leverage médio (vs PLANO) | Stories | Melhor (vs REF) |
| ---------- | ----------------------- | ------------------------- | ------- | --------------- |
| backend    | 7.2x                    | 1.1x                      | 4       | 8.4x            |
| web        | 6.5x                    | 1.0x                      | 3       | 7.8x            |
| mobile     | 5.8x                    | 0.9x                      | 2       | 6.9x            |
| fullstack  | **7.8x**                | 1.2x                      | 3       | 9.1x            |

## 📊 Produtividade BCP

> Telemetria de Business Complexity Points. As horas foram derivadas upstream pelo
> [`bmad-module-bcp`](https://github.com/nidelson/bmad-module-bcp); PULSE só
> reporta produtividade observada e nunca é dono do baseline BCP.

| Métrica            | Valor |
| ------------------ | ----- |
| Stories com BCP    | 12    |
| Total BCP pontuado | 38    |

**h/BCP real por categoria e segmento de tamanho** (mediana de BCP `segment_split` = 3):

| Categoria | Segmento | n | h/BCP real (faixa típica) | h/BCP est. | Drift |
| --------- | -------- | - | ------------------------- | ---------- | ----- |
| backend   | all      | 4 | 0.64h [0.58–0.71]         | 0.62h      | +3%   |
| web       | all      | 3 | 0.58h [0.52–0.65]         | 0.60h      | −3%   |
| fullstack | all      | 3 | 0.61h [0.55–0.68]         | 0.60h      | +2%   |

**Convergência do baseline (h/BCP está estabilizando?):** **converging** — a mediana de |drift| foi de 19% (1ª metade) para 4% (2ª metade); a faixa de confiança estreitou no mesmo split. Estimativas se fechando na realidade.

> **Referência frozen vs plano recalibrado:** o `h/BCP` real (~0.6h) é o **fator vivo** (plano → previsibilidade). A **reference rate frozen** (`reference_h_per_bcp` = 4.0h, benchmark governado) é o que ancora a alavancagem vs REFERÊNCIA — não recalibra, então o ROI não colapsa.

## 🔮 Previsão de Projeto

> Horas pra concluir o backlog pontuado restante (14 BCP não-iniciado), por `BCP × h/BCP` calibrado, com IC de 90%. Pra times que faturam por hora.

**Total: 8.6h** — faixa [6.9–11.2]h (IC 90%)

| Categoria | BCP restante | Previsão (IC 90%)   | Confiança |
| --------- | ------------ | ------------------- | --------- |
| backend   | 8            | 5.1h [4.0–6.7]h     | ok        |
| web       | 6            | 3.5h [2.9–4.5]h     | ok        |

> Faixa conservadora: o IC do total soma os limites por categoria. O forecast é read-only — não muda estimativa nem baseline.

## 💡 Insights de Processo

💓 **Maxine:** A manchete é **previsibilidade**: 88% (mediana), convergindo (`↑`) — só 12% de margem de erro. As estimativas deste time casam com a realidade — é o sinal que sobrevive a uma reunião de board. Três leituras:

1. **Alavancagem vs PLANO já colapsou para ~1.1x.** Isso é o produto funcionando: base calibrada ⇒ multiplicador vs-plano → 1.0x por construção. Não persiga esse número.
2. **O ROI durável é a alavancagem vs REFERÊNCIA frozen (6.9x)** — vs um benchmark de 4.0h/BCP que não recalibra. É o que você leva pro board, honesto e estável.
3. **Convergência do baseline (19% → 4%)** confirma que a calibração está madura. A faixa de confiança do h/BCP estreitou junto.

⚠ **Atenção:** 2 stories mostram `pulse-track-start` invocado retroativamente. Conecte ao `/bmad-dev-story` pra capturar timestamps de início limpos automaticamente.

## 📋 Detalhamento por Story

> `Plano` = horas estimadas recalibradas (vivo); `vs PLANO` = plano/real (colapsa ao calibrar → previsibilidade); `vs REF` = referência frozen / real (ROI estável). Linhas ilustrativas.

| Story                                 | Plano | Real   | vs PLANO | vs REF   | Qualidade | Categoria  |
| ------------------------------------- | ----- | ------ | -------- | -------- | --------- | ---------- |
| 1.1 login-supabase-auth               | 2.3h  | 2.1h   | 1.1x     | 3.8x     | ✅ passou | backend    |
| 1.3 download-cache-usuarios           | 1.5h  | 1.4h   | 1.1x     | 4.3x     | ✅ passou | backend    |
| 4.4 coresync-pull-bidirectional       | 3.1h  | 2.8h   | 1.1x     | 5.0x     | ✅ passou | backend    |
| 4.6 coresync-ack-mobile               | 1.8h  | 1.9h   | 0.9x     | 5.3x     | 🔁 1x     | mobile     |
| 5.3 projetos-crud-list                | 2.0h  | 1.6h   | 1.3x     | 7.5x     | ✅ passou | fullstack  |
| 5.8-mvp publish-flag                  | 2.1h  | 1.92h  | 1.1x     | **7.8x** | ✅ passou | fullstack  |
| 5.9 importacao-questionarios          | 2.5h  | 2.4h   | 1.0x     | 7.5x     | ✅ passou | fullstack  |
| 14.1 role-impersonator-endpoint       | 2.4h  | 2.3h   | 1.0x     | 7.0x     | ✅ passou | backend    |
| 14.5 audit-log-completo-lgpd          | 1.9h  | 1.7h   | 1.1x     | 7.1x     | ✅ passou | backend    |
| 14.8 remocao-customer-select          | 1.4h  | 1.5h   | 0.9x     | 6.7x     | ✅ passou | web        |
| 15.2 migrar-crud-clientes-admin       | 2.0h  | 1.8h   | 1.1x     | 7.8x     | 🔁 1x     | web        |
| 15.4 dashboard-visao-geral-plataforma | 2.2h  | 2.0h   | 1.1x     | **8.4x** | ✅ passou | web        |

---

_PULSE — Contra fatos, não há argumentos._  
_Dashboard gerado automaticamente pelo módulo PULSE._
