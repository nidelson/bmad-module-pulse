# Changelog

## [0.4.2](https://github.com/nidelson/bmad-module-pulse/compare/v0.4.1...v0.4.2) (2026-05-01)


### Documentation

* **readme:** clarify v1.0 roadmap as a pitch to BMAD core ([#22](https://github.com/nidelson/bmad-module-pulse/issues/22)) ([b576b58](https://github.com/nidelson/bmad-module-pulse/commit/b576b5824ae7de624ec3c8b0c85f69ca91a9cf8d))
* **readme:** replace static image with inline dashboard snippet + examples folder ([85389e7](https://github.com/nidelson/bmad-module-pulse/commit/85389e739153ce3b9867c9755734319beeb742d5))


### Miscellaneous

* add CONTRIBUTING.md and SECURITY.md (community standards) ([#24](https://github.com/nidelson/bmad-module-pulse/issues/24)) ([aabba1a](https://github.com/nidelson/bmad-module-pulse/commit/aabba1abf3ca5b539d71235b4ff750668c1558ec))
* add Contributor Covenant 2.1 Code of Conduct ([#23](https://github.com/nidelson/bmad-module-pulse/issues/23)) ([31678cf](https://github.com/nidelson/bmad-module-pulse/commit/31678cfd84d1598bb37558296b0fffcfd4220aec))
* add GitHub issue and pull request templates ([#25](https://github.com/nidelson/bmad-module-pulse/issues/25)) ([03a4f53](https://github.com/nidelson/bmad-module-pulse/commit/03a4f53ebc7aec7c8d05a3abb020ca26f736e9e2))

## [0.4.1](https://github.com/nidelson/bmad-module-pulse/compare/v0.4.0...v0.4.1) (2026-04-30)


### Bug Fixes

* **pulse-setup:** drop redundant {project-root} prefix from path result templates ([#16](https://github.com/nidelson/bmad-module-pulse/issues/16)) ([b9ddbca](https://github.com/nidelson/bmad-module-pulse/commit/b9ddbcae75322ec4315542b26bc68ad56eaf2799)), closes [#15](https://github.com/nidelson/bmad-module-pulse/issues/15)

## [0.4.0](https://github.com/nidelson/bmad-module-pulse/compare/v0.3.2...v0.4.0) (2026-04-27)


### ⚠ BREAKING CHANGES

* drops BMAD <6.4.0 support; auto-tracking now via _bmad/custom/*.toml.
* skill folders and slash commands renamed pulse-* → bmad-pulse-*.

### Features

* migrate to BMAD 6.4.0 customize.toml and rename skills to bmad-pulse-* ([#12](https://github.com/nidelson/bmad-module-pulse/issues/12)) ([fcd8ba0](https://github.com/nidelson/bmad-module-pulse/commit/fcd8ba0e76e6dc766a3c160d7cd5928f1e541a38))

## [0.3.2](https://github.com/nidelson/bmad-module-pulse/compare/v0.3.1...v0.3.2) (2026-04-16)


### Bug Fixes

* **ci:** configure release-please jsonpath for marketplace.json and module.yaml ([3fc83a5](https://github.com/nidelson/bmad-module-pulse/commit/3fc83a5483cb70bfd3a60398fe8ba2abd3ce2020))

## [0.3.1](https://github.com/nidelson/bmad-module-pulse/compare/v0.3.0...v0.3.1) (2026-04-16)


### Bug Fixes

* **ci:** bump patch for fix commits in pre-major releases ([#9](https://github.com/nidelson/bmad-module-pulse/issues/9)) ([959de34](https://github.com/nidelson/bmad-module-pulse/commit/959de3465da6b3acab697d3ee6642cfb70d9f3ce))
* **pulse-setup:** detect workflow format and inject XML or Markdown ([a36e514](https://github.com/nidelson/bmad-module-pulse/commit/a36e514dae472e3aba7c40e2d5a195042662e34f))

## [0.3.0](https://github.com/nidelson/bmad-module-pulse/compare/v0.2.0...v0.3.0) (2026-04-12)


### Features

* **agent:** auto-register Levi via bmad-skill-manifest ([fa68967](https://github.com/nidelson/bmad-module-pulse/commit/fa68967f1b2b83bb714f29d7a5ffb5a51ccefcd5))
* **agent:** register Levi via bmad-skill-manifest.yaml for auto-discovery ([ae2fbfd](https://github.com/nidelson/bmad-module-pulse/commit/ae2fbfd2e69b3ecda36e72c43615a21fbcb8c8f4))
* PULSE module v0.1.0 — initial release ([af57dd1](https://github.com/nidelson/bmad-module-pulse/commit/af57dd1198997a3f2212d57d4799bf5470c588f4))
* PULSE module v1.0.0 — AI Leverage metrics for BMAD ([59e27a0](https://github.com/nidelson/bmad-module-pulse/commit/59e27a06a4384348bf12201f743f5b5f9115e492))
* **setup:** add auto-integration with bmad-dev-story for transparent tracking ([b389a8b](https://github.com/nidelson/bmad-module-pulse/commit/b389a8b572ae2ae543925741a4ddc2150f6b1c57))


### Bug Fixes

* **ci:** release-please configuration for v0.1.0 ([c685f79](https://github.com/nidelson/bmad-module-pulse/commit/c685f79d19e4e06742b622925c1f8e6005ace5e2))
* **ci:** set release-please manifest to 0.0.0 for correct initial release ([9a3a08b](https://github.com/nidelson/bmad-module-pulse/commit/9a3a08bbadb17291a8519f99fba4480a92c912f6))
* **ci:** set target-branch to main for release-please ([c6fe5ba](https://github.com/nidelson/bmad-module-pulse/commit/c6fe5ba61a3cf2c85ccd208dba471dd7aea2f974))
* **setup:** register Levi in agent-manifest.csv for Party Mode ([7ed422c](https://github.com/nidelson/bmad-module-pulse/commit/7ed422cee78018c6f97262f7563e8dd58b68b941))
* **skills:** align SKILL.md name with directory for 2 skills ([6148438](https://github.com/nidelson/bmad-module-pulse/commit/6148438cc1faa01f472cd1b051e61bc70abe84b5))
* **skills:** align SKILL.md name with directory for pulse-dashboard and pulse-track-start ([6f6cf9b](https://github.com/nidelson/bmad-module-pulse/commit/6f6cf9b4be2dee4682372ac48a6b23cd32e35e20))


### Continuous Integration

* add release-please for automated changelog and releases ([70bad80](https://github.com/nidelson/bmad-module-pulse/commit/70bad800614839b5275cc312a5afc8f977419190))


### Miscellaneous

* add GitHub Sponsors funding configuration ([98ec673](https://github.com/nidelson/bmad-module-pulse/commit/98ec673f8c17b61bf3df2c556929a678a7a2a0eb))
* **main:** release 0.1.0 ([6c2f1b6](https://github.com/nidelson/bmad-module-pulse/commit/6c2f1b63775fcc5e5ff2e67f6fe843fee3eb41b3))
* **main:** release 0.2.0 ([37b77f5](https://github.com/nidelson/bmad-module-pulse/commit/37b77f57b825f5e2a0757b2fd05c4838e61315ac))
* **main:** release 0.2.0 ([585ab32](https://github.com/nidelson/bmad-module-pulse/commit/585ab32db435c715e59dde49c54cd617de977200))
* **main:** release 1.0.0 ([69028f5](https://github.com/nidelson/bmad-module-pulse/commit/69028f557a229ff519d2aa5a0b02588bafb26d5c))
* remove internal implementation plan from repo ([dc8eb2d](https://github.com/nidelson/bmad-module-pulse/commit/dc8eb2d5bf0e76bec8e8a7266e366b6c5e4b0e9a))
* set initial version to 0.1.0 ([cfa6d78](https://github.com/nidelson/bmad-module-pulse/commit/cfa6d7838de20bb2431a7e279c41f3b64dc57593))

## [0.2.0](https://github.com/nidelson/bmad-module-pulse/compare/v0.1.0...v0.2.0) (2026-04-11)


### Features

* **agent:** register Levi via bmad-skill-manifest.yaml for auto-discovery ([ae2fbfd](https://github.com/nidelson/bmad-module-pulse/commit/ae2fbfd2e69b3ecda36e72c43615a21fbcb8c8f4))


### Bug Fixes

* **setup:** register Levi in agent-manifest.csv for Party Mode ([7ed422c](https://github.com/nidelson/bmad-module-pulse/commit/7ed422cee78018c6f97262f7563e8dd58b68b941))

## 0.1.0 (2026-04-11)


### Features

* PULSE module v0.1.0 — initial release ([af57dd1](https://github.com/nidelson/bmad-module-pulse/commit/af57dd1198997a3f2212d57d4799bf5470c588f4))
* PULSE module v1.0.0 — AI Leverage metrics for BMAD ([59e27a0](https://github.com/nidelson/bmad-module-pulse/commit/59e27a06a4384348bf12201f743f5b5f9115e492))
* **setup:** add auto-integration with bmad-dev-story for transparent tracking ([b389a8b](https://github.com/nidelson/bmad-module-pulse/commit/b389a8b572ae2ae543925741a4ddc2150f6b1c57))


### Bug Fixes

* **ci:** release-please configuration for v0.1.0 ([c685f79](https://github.com/nidelson/bmad-module-pulse/commit/c685f79d19e4e06742b622925c1f8e6005ace5e2))
* **ci:** set release-please manifest to 0.0.0 for correct initial release ([9a3a08b](https://github.com/nidelson/bmad-module-pulse/commit/9a3a08bbadb17291a8519f99fba4480a92c912f6))
* **ci:** set target-branch to main for release-please ([c6fe5ba](https://github.com/nidelson/bmad-module-pulse/commit/c6fe5ba61a3cf2c85ccd208dba471dd7aea2f974))
* **setup:** register Levi in agent-manifest.csv for Party Mode ([7ed422c](https://github.com/nidelson/bmad-module-pulse/commit/7ed422cee78018c6f97262f7563e8dd58b68b941))


### Continuous Integration

* add release-please for automated changelog and releases ([70bad80](https://github.com/nidelson/bmad-module-pulse/commit/70bad800614839b5275cc312a5afc8f977419190))


### Miscellaneous

* add GitHub Sponsors funding configuration ([98ec673](https://github.com/nidelson/bmad-module-pulse/commit/98ec673f8c17b61bf3df2c556929a678a7a2a0eb))
* remove internal implementation plan from repo ([dc8eb2d](https://github.com/nidelson/bmad-module-pulse/commit/dc8eb2d5bf0e76bec8e8a7266e366b6c5e4b0e9a))
* set initial version to 0.1.0 ([cfa6d78](https://github.com/nidelson/bmad-module-pulse/commit/cfa6d7838de20bb2431a7e279c41f3b64dc57593))
