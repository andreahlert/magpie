<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [RFC-MAG-0002: Model C structural impact](#rfc-mag-0002-model-c-structural-impact)
- [Modelo C: o que muda na estrutura do Magpie](#modelo-c-o-que-muda-na-estrutura-do-magpie)
  - [Sumário do que precisa existir](#sum%C3%A1rio-do-que-precisa-existir)
  - [Estrutura nova do repositório Magpie (fonte)](#estrutura-nova-do-reposit%C3%B3rio-magpie-fonte)
    - [Mudanças destacadas](#mudan%C3%A7as-destacadas)
  - [Estrutura nova do repositório adopter](#estrutura-nova-do-reposit%C3%B3rio-adopter)
    - [Diferenças do estado atual](#diferen%C3%A7as-do-estado-atual)
  - [Schema dos arquivos novos](#schema-dos-arquivos-novos)
    - [Skill manifest (em cada skill)](#skill-manifest-em-cada-skill)
    - [Capability taxonomy](#capability-taxonomy)
    - [Adopter intent](#adopter-intent)
    - [Adopter lock](#adopter-lock)
  - [O que o reconciler faz, passo a passo](#o-que-o-reconciler-faz-passo-a-passo)
  - [Mudanças nas skills existentes](#mudan%C3%A7as-nas-skills-existentes)
  - [Mudanças nos templates por adopter](#mudan%C3%A7as-nos-templates-por-adopter)
  - [Mudanças nos docs](#mudan%C3%A7as-nos-docs)
  - [Sequência de migração proposta](#sequ%C3%AAncia-de-migra%C3%A7%C3%A3o-proposta)
  - [Riscos e mitigações](#riscos-e-mitiga%C3%A7%C3%B5es)
  - [O que **não** muda](#o-que-n%C3%A3o-muda)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

<!-- SPDX-License-Identifier: Apache-2.0 -->

# RFC-MAG-0002: Model C structural impact

| Field | Value |
|---|---|
| Status | Accepted |
| Authors | André Ahlert, Apache Magpie working group |
| Tracking issue | [#1](https://github.com/andreahlert/magpie/issues/1) |
| Depends on | [RFC-MAG-0001](RFC-MAG-0001-adoption-models.md) |

# Modelo C: o que muda na estrutura do Magpie

Detalha o impacto estrutural e organizacional de adotar o **Modelo C (intent + lock)** descrito em [RFC-MAG-0001](RFC-MAG-0001-adoption-models.md). Cobre o repositório fonte do Magpie e o repositório do adopter.

Leitura linear assume familiaridade com o RFC anterior.

## Sumário do que precisa existir

Lista das peças novas que o Modelo C exige. Detalhadas nas seções seguintes.

1. **Skill manifest** machine-readable em cada skill, com tags estruturadas.
2. **Capability taxonomy** versionada e canônica (domínios, audiences, risk tiers, integrações).
3. **Reconciler** que cruza `intent.yaml` com taxonomia e manifests, emitindo lock.
4. **Schema** formal dos arquivos `intent.yaml` e `lock`.
5. **Plan/apply CLI** que opera o ciclo declarativo.
6. **Override system** estruturado, com tipos definidos (exclude, force-include, pin, param-override).
7. **Migration registry** que documenta renomeação, split e merge de skills entre versões.
8. **Templates parametrizáveis** em vez de arquivos estáticos.
9. **Skill registry index** agregado, gerado a partir dos manifests.

## Estrutura nova do repositório Magpie (fonte)

Comparação direta com o layout atual.

```text
magpie/
├── README.md
├── LICENSE NOTICE .asf.yaml pyproject.toml uv.lock
│
├── agent/
│   ├── mission.md
│   ├── contract.md
│   ├── policies/
│   │   ├── security-model.md
│   │   ├── privacy.md
│   │   └── scope.md
│   ├── prompts/
│   └── taxonomy/                           # NOVO
│       ├── domains.yaml
│       ├── audiences.yaml
│       ├── risk-tiers.yaml
│       └── integrations.yaml
│
├── skills/                                 # ex .claude/skills
│   ├── security-issue-import/
│   │   ├── manifest.yaml                   # NOVO, machine-readable
│   │   ├── SKILL.md                        # prose, como hoje
│   │   ├── templates/                      # arquivos parametrizáveis
│   │   │   └── canned-replies.md.j2
│   │   └── params.schema.json              # NOVO, params aceitos
│   ├── pr-management-triage/
│   │   └── ...
│   └── ...
│
├── runtime/                                # ex tools/* serviços
│   ├── github/ jira/ gmail/ ponymail/
│   └── ...
│
├── workflows/                              # ex tools/* orquestradores
│   ├── pr-management/ issue-management/
│   └── ...
│
├── reconciler/                             # NOVO
│   ├── resolve.py                          # intent + taxonomy + manifests -> lock
│   ├── plan.py                             # diff entre lock atual e novo
│   ├── apply.py                            # materializa workspace adopter
│   ├── migrations/                         # renomeações, splits
│   │   ├── 2026-04-01-split-pr-triage.yaml
│   │   └── 2026-05-15-rename-security-import.yaml
│   └── schemas/
│       ├── intent.schema.json
│       └── lock.schema.json
│
├── registry/                               # NOVO, gerado
│   ├── skills-index.json                   # build artifact, agregado de manifests
│   └── capabilities-matrix.md              # gerado, human-readable
│
├── evals/
├── data-sources/
│
├── projects/                               # exemplos canônicos
│   └── _example-airflow/
│       ├── .apache-steward.intent.yaml
│       └── .apache-steward.lock
│
└── docs/
    ├── architecture/
    ├── governance/
    ├── rfcs/
    ├── setup/
    ├── adoption/                           # NOVO, guia adopter
    │   ├── intent-cookbook.md
    │   ├── override-guide.md
    │   ├── plan-apply-cycle.md
    │   └── migration-when-skill-renames.md
    └── contributing.md
```

### Mudanças destacadas

- `projects/_template/` desaparece como pasta de 20 .md estáticos. Vira `projects/_example-airflow/` com intent + lock reais. Templates de fato ficam dentro de cada skill em `skills/<n>/templates/`.
- `.claude/skills/` vira `skills/` no topo. Skill deixa de ser detalhe de empacotamento Claude e vira cidadão de primeira classe do framework.
- `reconciler/` é a engine. Sem ela o modelo não existe.
- `registry/` é build artifact (commitado ou regerado em CI, escolha de processo).
- `agent/taxonomy/` é o vocabulário canônico. Qualquer skill que invente tag fora dele falha o validador.

## Estrutura nova do repositório adopter

Hoje o adopter ganha symlinks dentro de `.claude/skills/`, um lock parcial (só install pin), e um diretório de overrides solto. Com Modelo C:

```text
<adopter-repo>/
├── .apache-steward.intent.yaml             # SOURCE OF TRUTH, committed
├── .apache-steward.lock                    # gerado por `magpie apply`, committed
├── .apache-steward.local.lock              # gitignored, "what fetched"
├── .apache-steward/                        # gitignored, snapshot framework
├── .apache-steward-overrides/              # estruturado, committed
│   ├── canned-replies/
│   │   └── pr-management-triage.md         # override pontual de template
│   └── params/
│       └── security-issue-import.yaml      # override de params declarados
└── .claude/skills/                         # symlinks gerados pelo apply
    └── ...
```

### Diferenças do estado atual

- Lock vira contrato completo de capacidade, não só pin de install.
- Override deixa de ser pasta livre, ganha sub-pastas tipadas. Override de template vai em `canned-replies/`, override de parâmetro em `params/`. Permite o reconciler validar.
- Symlinks são output do `apply`, não escolha manual durante onboarding.

## Schema dos arquivos novos

### Skill manifest (em cada skill)

```yaml
# skills/security-issue-import/manifest.yaml
id: security-issue-import
version: 1.4.2
domains: [security]
audiences: [maintainer-inbound]
risk-tier: suggest-only
integrations: [github, ponymail, vulnogram]
requires: [setup-isolated-setup-install]
templates:
  - canned-replies.md.j2
params:
  schema: params.schema.json
  defaults: params.defaults.yaml
status: stable
```

### Capability taxonomy

```yaml
# agent/taxonomy/risk-tiers.yaml
tiers:
  - id: suggest-only
    order: 1
    description: "Agent reads and proposes. Human acts."
  - id: draft-pr
    order: 2
    description: "Agent writes PR. Human reviews and merges."
  - id: write-comment
    order: 3
  - id: write-merge
    order: 4
    description: "Auto-merge narrow scope."
```

```yaml
# agent/taxonomy/domains.yaml
domains:
  - id: security
    description: "Security report flow, CVE, embargo."
  - id: pr-queue
  - id: issue-queue
  - id: contributor-lifecycle
  - id: dev-cycle
```

### Adopter intent

```yaml
# .apache-steward.intent.yaml
framework:
  install: { method: git-branch, ref: main }
capabilities:
  domains: [security, pr-queue]
  audiences: [maintainer-inbound]
  risk-tier-max: draft-pr
  integrations: [github, jira, ponymail, vulnogram]
overrides:
  exclude: [pr-management-code-review]
  force-include: [contributor-nomination]
  pin:
    security-issue-import: "1.4.2"
  params:
    security-issue-import:
      cve-allocator-email: security@adopter.org
```

### Adopter lock

```yaml
# .apache-steward.lock
generated-from: .apache-steward.intent.yaml
generated-at: 2026-05-28T14:00:00Z
framework-version: 1.4.0
skills:
  security-issue-import:
    version: 1.4.2
    source: intent.domains
    integrations-resolved: [github, ponymail, vulnogram]
  security-issue-deduplicate:
    version: 1.6.0
    source: intent.domains
  contributor-nomination:
    version: 0.3.1
    source: intent.overrides.force-include
exclusions:
  pr-management-code-review:
    reason: intent.overrides.exclude
checksum: sha256:abc123...
```

## O que o reconciler faz, passo a passo

1. **Carrega taxonomia canônica** da versão do framework declarada.
2. **Valida intent** contra schema. Erros: domínio inexistente, risk-tier inexistente, override apontando pra skill inexistente.
3. **Filtra skill registry** pelos critérios do intent:
   - Skills cujo `domains` intersecta `intent.capabilities.domains`.
   - Risk tier da skill é menor ou igual a `intent.capabilities.risk-tier-max`.
   - Audiences interseccionam.
   - Integrações da skill são subset das declaradas.
4. **Aplica overrides**:
   - Remove skills em `exclude`.
   - Adiciona skills em `force-include` (mesmo fora dos critérios; emite warning se viola risk-tier).
   - Resolve `pin` versus última versão disponível.
5. **Resolve dependências**: `requires` de cada skill puxa skills auxiliares (ex: setup).
6. **Emite lock candidato**.
7. **Plan**: compara lock candidato com lock corrente. Emite diff legível.
8. **Apply**: escreve lock, materializa symlinks, escreve templates resolvidos no workspace adopter, dispara hook post-checkout.

## Mudanças nas skills existentes

Cada skill ganha:

- `manifest.yaml` com tags estruturadas.
- `params.schema.json` se aceita parâmetros do adopter.
- `templates/` se gera arquivos no workspace adopter (templates Jinja2 ou similar).
- `params.defaults.yaml` com defaults seguros.

SKILL.md continua existindo, é a prose pro humano e pro agente. Manifest é o contrato pra máquina.

Custo: cada skill hoje (~17) precisa ser auditada e ganhar manifest. Estimativa grossa: 30 minutos por skill com manifest simples, 2 horas para as que têm templates não triviais.

## Mudanças nos templates por adopter

Hoje `projects/_template/` tem 20+ arquivos `.md` estáticos. Esses arquivos passam a viver dentro das skills que de fato os consomem, como Jinja2 templates parametrizáveis:

```text
skills/pr-management-triage/templates/
├── triage-ci-check-map.md.j2
├── triage-comment-templates.md.j2
└── canned-responses.md.j2
```

Adopter parametriza via `intent.overrides.params` ou substitui template inteiro via `.apache-steward-overrides/canned-replies/pr-management-triage.md`.

`projects/_template/` no repo Magpie vira `projects/_example-airflow/`: intent + lock reais que servem como exemplo navegável, não como pasta de copy-paste.

## Mudanças nos docs

Documentação ganha pasta nova `docs/adoption/` com:

- **`intent-cookbook.md`**: exemplos de intent.yaml por perfil de projeto (projeto pequeno só com triage, projeto ASF com fluxo security completo, projeto não-ASF, etc.).
- **`override-guide.md`**: quando usar exclude vs force-include vs pin. Anti-patterns.
- **`plan-apply-cycle.md`**: como rodar `magpie plan`, ler diff, aplicar.
- **`migration-when-skill-renames.md`**: como o reconciler avisa que uma skill mudou, e o que editar no intent.

Docs existentes que precisam atualizar:

- `docs/setup/README.md`: fluxo de adoção muda. Setup install permanece, takeover muda pra "edita intent, roda plan, roda apply".
- `docs/modes.md`: passa a explicar modes como **projeção do intent**, não como organização interna. Continua útil como narrativa externa.
- `README.md` topo: substituir "skill families" pela linguagem de capabilities.

## Sequência de migração proposta

Não dá pra trocar tudo num PR. Sequência:

1. **PR 1**: introduzir `agent/taxonomy/` + schemas. Sem mudar comportamento.
2. **PR 2**: introduzir `manifest.yaml` em uma skill piloto (security-issue-import). Sem reconciler ainda.
3. **PR 3**: backfill manifests no resto das skills, em ondas (uma família por PR).
4. **PR 4**: build do `registry/skills-index.json` em CI. Validador de manifest contra taxonomia.
5. **PR 5**: reconciler em modo `plan` only, sem apply. Adopter pode rodar pra ver o que aconteceria.
6. **PR 6**: `apply` em modo opt-in, atrás de flag. Apoiadores piloto experimentam.
7. **PR 7**: templates Jinja2 em uma skill piloto.
8. **PR 8 em diante**: migrar templates dos `projects/_template/` pra dentro das skills, deprecar `_template/` em favor de `_example-airflow/`.
9. **PR final**: flip do default. Setup-steward passa a operar em Modelo C.

Cada PR é reversível. Adopter atual não quebra enquanto a sequência roda.

## Riscos e mitigações

| Risco | Mitigação |
|-------|-----------|
| Reconciler vira god-component | Manter regras explícitas em YAML/data, código só executa regras. Sem heurística secreta. |
| Adopter abusa de override e perde regime intent | Linter no `plan`: se >5 overrides, sugere repensar capabilities. Warning, não erro. |
| Manifest fica desatualizado vs SKILL.md | CI valida: campos comuns (status, domínios) batem. PR review checklist exige update sincronizado. |
| Schema do lock muda quebrando adopters antigos | Schema versionado. Reconciler suporta N-2 versões. Migration tool oferece upgrade. |
| Renomeação de skill quebra lock | Migration registry mapeia old-id → new-id. Reconciler aplica auto-rename no `plan`, adopter aprova. |
| Curva de aprendizado pesada pro PMC | `intent-cookbook.md` com exemplos prontos. Onboarding via `magpie init` interativo que gera intent.yaml inicial. |

## O que **não** muda

- Os modos (Triage, Mentoring, Drafting, Pairing, Auto-merge) sobrevivem como narrativa externa em MISSION.md e como projeção derivada do intent. Não viram unidade de configuração técnica.
- Mecanismo de install (svn-zip, git-tag, git-branch) permanece. O lock continua pinando install method.
- Sandbox, secure-agent setup, permission rules: ortogonais ao modelo de adoção. Não tocam.
- Symlinks no `.claude/skills/` do adopter continuam sendo a forma de o Claude Code enxergar as skills. Mudou só quem decide quais symlinks existem.
