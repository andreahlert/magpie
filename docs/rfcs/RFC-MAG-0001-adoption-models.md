<!-- SPDX-License-Identifier: Apache-2.0 -->

# RFC-MAG-0001: Adoption models (intent vs skill vs hybrid)

| Field | Value |
|---|---|
| Status | Accepted (Model C selected) |
| Authors | André Ahlert, Apache Magpie working group |
| Tracking issue | [#1](https://github.com/andreahlert/magpie/issues/1) |
| Related RFC | [RFC-MAG-0002](RFC-MAG-0002-model-c-structural-impact.md) |

# Dois modelos pra configurar Magpie num projeto adopter

Documento exploratório. Explica três formas possíveis de um projeto open-source dizer pro Magpie o que quer que ele faça. Linguagem acessível para dev que nunca usou Terraform nem Ansible.

## O problema

Magpie é uma plataforma de skills (capacidades de agente). Tem coisa pra triagem de issue, pra revisar PR, pra cuidar de fluxo de security, pra mentorar contributor novo, etc. Total: dezenas de skills.

Um projeto que quer adotar Magpie (por exemplo, Apache Airflow) não quer ligar tudo. Quer escolher. A pergunta é: **como o adopter escolhe?**

Existem dois jeitos clássicos de modelar essa escolha. Os nomes vêm de ferramentas de infra (Terraform e Ansible), mas o conceito vale pra qualquer sistema que precisa de configuração.

## Modelo A: Intent-based (estilo Terraform)

### A ideia

O adopter descreve **o que quer**, não **como fazer**. O sistema descobre quais skills ligar a partir disso.

### Como o adopter declara

```yaml
# .apache-steward.lock
capabilities:
  domains: [security, pr-queue]          # áreas que me interessam
  audience: [maintainer-inbound]         # quem é meu público
  risk-tier-max: draft-pr                # até onde aceito ir
  integrations: [github, jira, ponymail] # ferramentas que uso
```

### O que o Magpie faz

Um componente chamado **reconciler** lê esse arquivo e pensa:

- "Esse projeto cuida de security e PR queue."
- "Risco máximo é draft-pr (agente escreve, humano merge). Skills de auto-merge ficam fora."
- "Audience é maintainer inbound. Skills de dev-side pairing ficam fora."
- "Usa GitHub, Jira, Ponymail. Skills que dependem de Gmail ficam fora."

A partir desse cruzamento, o reconciler **gera** a lista de skills habilitadas e materializa os arquivos no projeto.

### Analogia leiga

Você diz pro Uber: "quero ir do aeroporto pra casa, prefiro carro, até R$50". O app escolhe motorista e rota. Você nunca pediu "Honda Civic placa ABC1234 pela Marginal".

### Vantagens

- Adopter raciocina em **conceitos do domínio dele** (domínios, risco, audience), não em nomes de skills.
- Quando Magpie adiciona uma skill nova de PR queue, ela aparece automaticamente em projetos que disseram `domains: [pr-queue]`. Sem precisar editar config manual.
- Linguagem do lock file é estável. Skills internas mudam de nome sem quebrar nada.
- Conversa com PMC fica clara: "quanto risco aceitamos?" é decisão humana, não trivia técnica.

### Desvantagens

- Reconciler precisa existir. Alguém escreve e mantém. Tem lógica não trivial.
- Cada skill precisa de **metadata machine-readable** declarando seus tags: `domain`, `audience`, `risk-tier`, `integrations`. Hoje skill é prose em SKILL.md. Precisa estruturar.
- Adopter perde controle granular. Se quer ligar exatamente skill X mas não Y do mesmo domínio, fica desconfortável. Precisa de mecanismo de override fino.
- Surpresa quando Magpie atualiza: skill nova entra sozinha. Bom pra adoção rápida, ruim pra projeto conservador.

## Modelo B: Skill-based (estilo Ansible)

### A ideia

O adopter **lista as skills que quer** uma por uma. Não há inferência. As tags `(domain, audience, risk)` existem só pra ajudar a navegar e filtrar na documentação.

### Como o adopter declara

```yaml
# .apache-steward.lock
skills:
  - security-issue-import
  - security-issue-deduplicate
  - security-cve-allocate
  - pr-management-triage
  - pr-management-code-review
  # auto-merge, mentoring, pairing: não listados, ficam fora
```

### O que o Magpie faz

Lê a lista. Habilita exatamente o que está ali. Fim.

### Analogia leiga

Você vai num restaurante e pede pelo cardápio: "salada Caesar, pizza margherita, suco de laranja". Garçom traz exatamente esses três itens. Não interpreta "tô com fome moderada e gosto de italiano" pra escolher por você.

### Vantagens

- Simples de implementar. Sem reconciler, sem schema de capabilities, sem inferência.
- Adopter tem controle total e previsível. Ligou skill X, recebe skill X.
- Update do Magpie nunca habilita coisa nova sem o adopter pedir. Skills novas ficam dormentes até alguém editar o lock.
- Skill metadata pode continuar em prose. Tags são só pra documentação.

### Desvantagens

- Adopter precisa conhecer o catálogo de skills. Onboarding mais alto.
- Discussão com PMC vira granular demais. "Liga security-issue-deduplicate?" é pergunta técnica, não estratégica.
- Skills relacionadas precisam ser ligadas em conjunto manualmente. Esquecer uma quebra fluxo.
- Quando Magpie renomeia ou divide uma skill, **todo adopter quebra**. Lock file referencia identificador interno.
- Sem semântica de "risco máximo". Adopter pode ligar auto-merge por engano se não conhecer a taxonomia.

## Modelo C: Intent com lock de skills (híbrido)

### A ideia

Adopter declara intent (capabilities). Reconciler resolve a lista de skills. Mas o resultado dessa resolução fica **escrito num lock file**, e o adopter pode anotar nele exceções cirúrgicas: pinar uma skill numa versão, excluir uma skill que o reconciler ligou, forçar uma skill que o reconciler não pegou.

É o casamento dos dois mundos anteriores. A intent guia o caso comum, o lock cobre o caso especial.

### Como o adopter declara

Dois arquivos, papéis distintos. Um é desejo, outro é resolução congelada.

```yaml
# .apache-steward.intent.yaml (committed, editado a mão)
capabilities:
  domains: [security, pr-queue]
  audience: [maintainer-inbound]
  risk-tier-max: draft-pr
  integrations: [github, jira, ponymail]

overrides:
  exclude:
    - pr-management-code-review     # não queremos esta, mesmo entrando no domínio
  force-include:
    - contributor-nomination        # queremos esta, fora do domínio declarado
  pin:
    security-issue-import: "1.4.2"  # travado nessa versão até validarmos a próxima
```

```yaml
# .apache-steward.lock (committed, gerado pelo reconciler)
generated-from: .apache-steward.intent.yaml
generated-at: 2026-05-28T14:00:00Z
skills:
  security-issue-import: { version: "1.4.2", source: intent.domains }
  security-issue-deduplicate: { version: "1.6.0", source: intent.domains }
  pr-management-triage: { version: "2.1.0", source: intent.domains }
  contributor-nomination: { version: "0.3.1", source: intent.overrides.force-include }
  # pr-management-code-review: ausente, source: intent.overrides.exclude
```

### Como o ciclo funciona

1. Adopter edita `intent.yaml`. Roda `magpie plan`.
2. Plan mostra diff: "vai adicionar X, remover Y, manter Z na versão pinada".
3. Adopter roda `magpie apply`. Reconciler escreve `lock` novo e materializa workspace.
4. Commit dos dois arquivos. Reviewer vê tanto o **desejo** quanto o **resultado**.

### Analogia leiga

`package.json` versus `package-lock.json` no Node. Você escreve `"react": "^18.0.0"` (intent: aceito qualquer 18.x). O npm resolve pra `18.2.0` exato e congela no lock. Se quiser pinar exatamente uma versão diferente, edita o lock ou troca a faixa no `package.json`. Os dois arquivos vão pro git.

### Vantagens

- Caso comum (90% das adoções) usa só intent, sem mexer em skill individual.
- Casos especiais cabem sem virar exceção quebrada. Override é parte do modelo, não hack.
- Lock dá **reproducibilidade exata**. Dois clones do repo adopter em máquinas diferentes resolvem pra mesma lista.
- Update do Magpie roda `magpie plan` antes de tocar nada. PMC vê o diff e decide. Não tem surpresa.
- Reviewer de PR no repo adopter vê **intent + lock + diff materializado** num único commit. Auditável.
- Skills renomeadas geram erro de reconciliação claro: "skill X (referenciada em overrides.pin) não existe mais, migrada pra Y". Adopter atualiza intent, não código.

### Desvantagens

- Mais arquivos. Mais conceitos a explicar (intent vs lock, plan vs apply).
- Reconciler tem que existir e ser sólido. Mesmo custo do Modelo A.
- Override demais e o adopter sai do regime intent na prática. Vira skill-based com decoração. Precisa de disciplina e linting ("se você tem >5 overrides, repensa o intent").
- Conflito de merge em `lock` pode ser feio quando dois PRs alteram intent ao mesmo tempo. Solução conhecida (regerar), mas demanda doc.

### Quando faz sentido

Faz sentido quando você espera adopters de perfis muito diferentes: alguns querem só ligar e usar (intent puro basta), outros vão precisar de exceção pontual sem virar o jogo todo. Apache funciona assim. Airflow opera diferente de Kafka, ambos diferentes de algum projeto não-ASF.

Pelo desenho do Magpie (mission fala em "project autonomy" como starting point estrutural), o Modelo C é o que melhor preserva essa autonomia sem cair na sobrecarga cognitiva do skill-based puro.

## Comparação lado a lado

| Critério | A. Intent puro | B. Skill puro | C. Intent + lock |
|----------|----------------|---------------|------------------|
| Unidade de escolha | Capability | Skill individual | Capability, com override por skill |
| Quem decide set final | Reconciler | Adopter | Reconciler + overrides do adopter |
| Onboarding | Responde 4 perguntas | Lê catálogo, escolhe N | Responde 4 perguntas, override depois se precisar |
| Update do Magpie | Skill nova entra sozinha | Skill nova dorme | `plan` mostra diff, adopter decide |
| Quebra em renomeação | Não | Sim, quebra lock | Erro de reconciliação claro, migração guiada |
| Controle granular | Precisa hack | Nativo | Nativo via overrides |
| Discussão com PMC | Estratégica | Técnica | Estratégica no comum, técnica no especial |
| Reproducibilidade entre máquinas | Boa | Exata | Exata |
| Custo de implementar | Reconciler + metadata | Catálogo documentado | Reconciler + metadata + plan/apply |
| Risco principal | Surpresa em update | Onboarding pesado, drift | Adopter abusa de override e perde o regime |

## Onde Magpie está hoje

Híbrido inclinado pro skill-based, mas grosseiro. O setup atual pergunta **skill families** (`security`, `pr-management`), que é meio caminho:

- Mais coarse que skill individual.
- Mais coarse que capability.
- Sem metadata machine-readable.
- Sem reconciler.

O lock file hoje guarda só **install pin** (de onde veio o framework, qual versão). Não guarda capability config nem skill enable list. As escolhas vivem nos symlinks criados durante o takeover, que é estado opaco.

## A pergunta de design

Três opções, não duas. O default define a cara da plataforma.

- **A. Intent puro:** "diga o que precisa, eu monto". Adoção em escala, mas surpresa em update e override fica fora do modelo.
- **B. Skill puro:** "catálogo aberto, monte seu kit". Controle máximo, mas onboarding pesado e quebra em renomeação.
- **C. Intent + lock (híbrido):** intent como conversa principal, lock como contrato, override como exceção legítima. Mais conceitos, melhor preserva project autonomy.

C é o mais alinhado com o que MISSION.md declara sobre autonomia de projeto. Custa mais pra implementar (reconciler + plan/apply + metadata estruturada de skill), e exige disciplina contra abuso de override.

A escolha não é só técnica. Determina o tipo de conversa que adopter tem com Magpie no momento da adoção, e o tipo de update que recebe ao longo do tempo.
