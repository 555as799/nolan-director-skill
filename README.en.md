# Nolan Director Skill

[简体中文](README.md) · **4.1.3 release candidate** · CineMatrix

An installable filmmaking conversation skill with a first-person creative persona, a portable research library, and workflows for discussing scripts, performance, camera placement, editing, and sound. It draws on relevant public accounts of Christopher Nolan's work and returns to the author's specific creative problem.

This is an **AI portrayal based on public sources**, not Christopher Nolan or an authorized product. It includes text instructions and research materials, not a cloned voice or specially trained model weights. The host application's model runs the conversation.

## Use in WorkBuddy

Download the [WorkBuddy package](https://github.com/555as799/nolan-director-skill/raw/refs/heads/main/downloads/nolan-director-4.1.3-workbuddy.zip) and import it through the Skills page: **Add Skill → Upload Skill**. Local builds write this archive to `dist/`. Confirm that the skill is enabled, start a new conversation, and explicitly request it:

> Use the Nolan Director skill for this ongoing creative conversation. I am making a two-minute short about someone drifting at sea, feeling free and happy. I have one performer and one small boat. Let's discuss the opening first, without producing a complete shot list.

Continue with ordinary questions and revisions. Select or invoke the skill again in a new conversation. These instructions follow the [official WorkBuddy Skills documentation](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market). Customer responses rejected both 4.1.0 and 4.1.2. A matching local 4.1.2 trace shows successful skill/core loading but no experience-card or voice-example read. Version 4.1.3 fixes that preparation path; its customer-host dialogue remains unverified.

Ordinary use does not require Python, a GPU, a separate database service, or another API key. Host model and browsing usage follow the customer's account. See the [installation guide in Chinese](给客户的安装说明.txt).

For another host supporting local Skills, use the complete `nolan-director` folder in the [portable package](https://github.com/555as799/nolan-director-skill/raw/refs/heads/main/downloads/nolan-director-4.1.3-portable.zip), following that host's installation procedure. Copying only `SKILL.md` leaves out the library. Install the package appropriate to your host.

## Design

- Load a compact session core once, then continue the author's project and accepted choices. Do not force grief, suspense, nonlinear structure, or a countdown onto every story.
- Keep public Nolan self-reports, collaborators' accounts, editorial analysis, and original examples distinct. First-person historical paraphrases require an identified Nolan source; collaborators retain attribution.
- Retrieve material for the current creative difficulty rather than reciting familiar film titles. Reuse context already read.
- Make suggestions concrete: a character action, audience expectation, camera position, sound relationship, cut, or resource tradeoff.
- Save project continuity only when requested, outside the shared skill. Separate confirmed facts, adopted decisions, and unaccepted proposals.

Hosts can read the text index and individual cards directly. Where Python is already available, an optional local JSON / SQLite script combines lexical retrieval with authored situation navigation. It is not a vector search service and makes no external model calls.

## Corpus and evidence

The 4.1.3 inventory contains **204 cards, 73 source entries, and 13 film entry points**: 46 Nolan experience cards, 12 collaborator cards, 89 craft/research cards, and 57 original examples. Relevant source passages for 39 cards were checked in this development round. Other inherited material retains its per-card review status.

Verify counts in the [build summary](validation/build-summary.json) and [canonical library](skills/nolan-director/assets/library.json). Cards can overlap in facts; source entries include engineering documentation. These counts are not counts of unique experiences or interviews, and do not imply every source was reread in full.

New material includes adaptation and period performance in *The Prestige*, production choices in *Tenet*, reflection on *Following*, science selection and performance preparation in *Interstellar*, and documented literary and film influences. Cards carry concise paraphrases, context, source locations, and limits. Complete books, films, paid interviews, and private conversations are not included.

Documented reading accounts now include *Waterland*, *A Tale of Two Cities*, *American Prometheus*, and a collection of Oppenheimer's postwar speeches whose exact title and edition were not specified. These accounts establish particular influences; they do not mean this project contains or has analyzed the full books.

## Release status

This is a **release candidate** with an installable package and reproducible source. Engineering tests, retrieval regression cases, and small independent AI conversation trials support specific findings. They do not establish human-equivalent directing ability or overall persona fidelity.

Version 4.1.3 embeds four concise sourced experiences in the entrypoint, loads voice examples at session start, and checks relevant experience for new substantive creative tasks. Six conflicting examples are repaired, subjective memory/time retrieval is added, and two existing source passages are rechecked. No cards or model weights are added. See the [current release record](validation/release-4.1.3.json) for the eight-turn-per-configuration proxy comparison with 4.1.2 and its limits. Raw customer prompts, images, traces and same-scene retests remain local. Proxy results do not establish customer-host acceptance or equivalence to a real director.

See the [readiness audit](validation/product-readiness.json), [validation report](validation/验收报告.md), [conversation trials](evals/independent-trials/), and [behavior cases](evals/behavior-cases.json). Once a case informs a fix, it is a regression case, not an untouched evaluation sample.

No new parameter training was performed for this release. Earlier experiments recorded in the project did not pass their quality checks; those weights are not used here. Retrieval and instruction improvements are separate from parameter training. Host model quality, file access, and context capacity still affect results.

## Build and verify

The source tree is self-contained. It does not require an enclosing workspace, the original archive, private training history, or developer-specific paths.

Use **Python 3.10+**. Core build and validation use the standard library; building the SQLite index requires SQLite with FTS5 enabled. End users taking the text-reading path do not need Python.

From the repository root:

```sh
python build.py
python tests/run_all.py
python audit_readiness.py
python export_source.py
python tests/verify_source.py
```

Packages are generated in `dist/`, with archive hashes in `dist/SHA256.json`. The final step checks the exported source's ability to rebuild in an isolated directory; consult its report for the exact scope. Regenerate evidence for the current revision before publishing.

Optional local retrieval:

```sh
python skills/nolan-director/scripts/recall.py --query "How can I preserve spontaneity while rehearsing?" --mode experience --limit 3
python skills/nolan-director/scripts/recall.py --query "limited budget, convincing space" --mode craft --backend json
```

`--budget` counts serialized Unicode characters, not tokens. If a result has `truncated: true`, read its full `card_file` before relying on factual content.

| Path | Purpose |
|---|---|
| `skills/nolan-director/SKILL.md` | Standalone skill entry point |
| `skills/nolan-director/references/session-core.md` | Session core and navigation |
| `skills/nolan-director/references/library-index.md` | Script-free library index |
| `skills/nolan-director/scripts/recall.py` | Local read-only retrieval |
| `data/` | Build inputs and migration provenance |
| `research/` | Source reviews and design adoption records |
| `evals/` | Behavior cases and actual trial records |
| `tests/`, `validation/` | Checks and supporting evidence |
| `release-files.json` | Explicit source-release allowlist |

Rebuild after changing source material instead of editing only the generated database. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Open-source approach and license

The project independently implements mechanisms informed by public persona-skill projects: layered role instructions, on-demand references, attribution, continuity, and evaluation. External persona implementations are not vendored. Adoption decisions are recorded in [research notes](research/方案与采用记录.md) and the [runtime review](research/runtime-adoption-review.md).

Original project code, instructions, and editorial material use the [MIT License](LICENSE). It does not grant rights in third-party films, books, interview originals, identities, or other protected material. See [NOTICE.md](NOTICE.md) and [SECURITY.md](SECURITY.md).

Fixed-version research covers [five persona/director frameworks](research/upstream-review-20261008.md) and [RoleLLM / Character-LLM training approaches](research/distillation-decision-20261008.md). Selected mechanisms are independently implemented; upstream weights, synthetic memories, and training systems are not bundled or claimed as reproduced.
