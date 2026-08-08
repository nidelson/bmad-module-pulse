# Attribution

## Business Complexity Points (BCP) framework — MIT

**Business Complexity Points (BCP)** is a software complexity normalization
framework created by **CI&T** (www.ciandt.com) in **2015**, adopted by **Itaú
Unibanco** in 2018 and evolved as a partnership between the two.

In **May 2026**, CI&T and Itaú published the framework as open source under the
**MIT License**:

- Official repository: https://github.com/flow-ciandt/bcp-agent
- License: MIT — `Copyright (c) 2025 CI&T HyperX`
- Institutional page: https://ciandt.com/us/en-us/complexitypoints
- Canonical ruler (image): https://dmwnh9nwzeoaa.cloudfront.net/2020-12/bcp-ruler.png

The normative ruler — complexity perspectives, per-size definitions, Fibonacci
points and examples — is materialized in the official repository at
`src/bcp/prompts/step0…step6.jinja2`, under the same MIT License.

### What MIT requires

Preserving the copyright notice and the license text in copies and in
substantial portions of the software. This file serves that purpose for the
ruler embedded in `skills/bmad-bcp-rule-card/assets/bcp-rule.yaml`.

### What changed relative to the previous publication

Until May 2026 BCP circulated under **CC BY-NC-ND 4.0**, and this module was
built on that premise. Three restrictions of that license **do not apply to the
MIT publication**:

| Previous term          | Effect on the module                    | Status under MIT                          |
| ---------------------- | --------------------------------------- | ----------------------------------------- |
| **ND** (NoDerivatives) | Embedded ruler was legally immutable    | Modification permitted                    |
| **NC** (NonCommercial) | Commercial use forbidden                | Commercial use permitted                  |
| **BY** (Attribution)   | Notice and link required                | Copyright and license remain required     |

### The ruler stays immutable — now by project decision

The immutability of `bcp-rule.yaml` **is no longer a legal constraint** and
becomes a **design decision of this module**, kept for the same practical reason
as always: a BCP score is only comparable across teams if the ruler is the same.
Editing elements, definitions or points produces numbers that look like BCP and
are not.

Anyone wanting to diverge from the canonical ruler now **may**, legally. But
they must do so by changing `rule_version` and accepting that the resulting
scores are not comparable with those of another installation.

The editorial `hints` blocks remain mutable by nature — they are authored by
this module, not part of CI&T's framework.

## Module code — MIT

The BCP scoring code (skills, scripts, schemas) is licensed under the MIT
License (see `LICENSE`). It shipped as the standalone `bmad-module-bcp` until
2026-08, and now lives inside PULSE as the optional feature behind
`pulse_estimation_method = "bcp"` — see [issue #84](https://github.com/nidelson/bmad-module-pulse/issues/84).
The move changes where the code lives, not its licence or its attribution
obligations: the copyright notice below must survive every relocation.

**With the republication of the framework, module and ruler now share the same
license (MIT).** The license split that used to be load-bearing in the design no
longer exists.

---

_License change verified on 2026-07-25 against the `LICENSE` of the
`flow-ciandt/bcp-agent` repository and the public announcement of May 2026. This
is a legal-posture assessment — human review is advisable before relying on it
for a commercial decision._
