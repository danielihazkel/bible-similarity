# Genealogy: progress and hand-off

This is the hand-off file for the family tree of the Hebrew Bible (series F, M88–M91, DESIGN §16.63, D101). Read it first in a new session, continue at **Next step**, and update it at the end of every step: tick the status table, add a log entry, move **Next step** on.

## How to resume
1. Read this file, then DESIGN §16.63 (the design) and the F milestones in `docs/TASKS.md`.
2. Do the step under **Next step**. For a review block (M90):
   1. `uv run bsim genealogy-review <block>`, which writes `artifacts/genealogy/review/<block>.md`: every link touching the block with its candidate verses, and the cue verses that have no link yet;
   2. read the Hebrew of the block's genealogy passages against the sheet;
   3. write `curation/genealogy/<NN-block>.yaml` (format below);
   4. `uv run bsim genealogy && uv run bsim build-db`, and look at the block's people at `/genealogy`;
   5. `uv run ruff check . && uv run pytest`;
   6. update this file (status, log, conflicts, open questions) and commit.
3. Keep each session to one step. If a block is too big for one session, split it here first, then continue.

## Decisions (user, 2026-10-21)
- **Conflicts marked:**
  - Bible vs Bible, where two passages give different parents or names;
  - "בן = descendant", where a link skips generations.
  - Rabbinic identifications are **deferred**: use only the Bible this round.
- **The tree holds:** father and mother; spouses and concubines (children grouped by mother); nations and clans (Gen 10, the tribes, founders); unnamed people needed as links.
- **Data:** TIPNR's family columns are the backbone, with proof verses found automatically, then a review block by block. The reviews go in `curation/genealogy/*.yaml`, which is committed: person keys and references only, never scripture text.
- **View:** a collapsible tree from Adam down, plus a side panel for the person: parents, spouses, children, proof verses in Hebrew, conflicts.
- **Fragments** that don't reach Adam attach to their tribe or nation by an edge marked "link not stated". Those with no known tribe go under "Unattached".
- **Names** are shown in Hebrew only. TIPNR's English unique names (`Isaac@Gen.17.19-Jas`) are internal keys.
- **References** in the curated files are Sefaria-style, in Hebrew numbering (`I Chronicles 5:27`).

## Curated file format
One file per block, `curation/genealogy/NN-<block>.yaml`; the block's verse range is in `genealogy.blocks` (`configs/default.yaml`). Keys are TIPNR's unique names exactly as the review sheet prints them.
```yaml
block: b13-ezra-nehemiah
status: reviewed          # draft | reviewed
people:                   # added people (anon:…) or corrections to TIPNR (he, sex)
  - {key: "anon:wife-of-hezron-2", he: "אשת חצרון", sex: f, kind: anon}
links:
  # the short form: confirmed, with the automatic proof verses (copy the sheet's line)
  - "Zerubbabel@1Ch.3.19-Mat <- Pedaiah@1Ch.3.18-"
  # the long form. status: confirmed | fixed | added | rejected
  # role: father | mother | spouse; kind: son | descendant | adopted | levirate | founder | unstated
  # proof: its own verses, which replace the automatic ones
  - {child: "…", parent: "…", role: father, kind: son, status: fixed, proof: [Ezra 3:2, Haggai 1:1]}
conflicts:
  - kind: bible           # bible | descendant
    child: "Zerubbabel@…"
    readings:             # the first reading is the one the tree draws
      - {parent: "Shealtiel@…", proof: [Ezra 3:2]}
      - {parent: "Pedaiah@…", proof: [I Chronicles 3:19]}
    note: {en: "…", he: "…"}   # optional; both languages or none
missed:                   # cue verses of the sheet that are no link, each with a reason
  - {ref: Genesis 4:25, reason: "Cain named as Abel's killer"}
```
Rules the build enforces, stopping on any error:
- `confirmed` and `fixed` need a TIPNR link, and `added` must not have one.
- Every key and reference must resolve, and the tree must not get a cycle.

A person counts as reviewed when every parent link of theirs is checked.

## Status

| Step | What | Status |
|---|---|---|
| F0 | Hand-off file, DESIGN §16.63 / D101, TASKS milestones | done |
| M88 (F1) | Data: TIPNR family columns, `bsim genealogy`, automatic proofs, curated loader, `genealogy-review`, DB tables | done |
| M89 (F2) | Viewer: API, `/genealogy` tree, collapsing, panel, search, legend, EN/HE, responsive | todo |
| M90 (F3) | Review block by block (below) | todo |
| M91 (F4) | Cross-book pass, tribe attachments, jump box, dossier entry | todo |

Review blocks (M90), in Jewish canon order:

| # | Block | Range | Status | Links checked | Conflicts |
|---|---|---|---|---|---|
| 01 | b01-gen-1-11 | Gen 1–11 | todo | | |
| 02 | b02-gen-12-25 | Gen 12–25:18 | todo | | |
| 03 | b03-gen-25-36 | Gen 25:19–36 | todo | | |
| 04 | b04-gen-37-50 | Gen 37–50 | todo | | |
| 05 | b05-exod-lev | Exodus–Leviticus | todo | | |
| 06 | b06-num-deut | Numbers–Deuteronomy | todo | | |
| 07 | b07-josh-judg | Joshua–Judges | todo | | |
| 08 | b08-samuel | 1–2 Samuel | todo | | |
| 09 | b09-kings | 1–2 Kings | todo | | |
| 10 | b10-latter-prophets | Isaiah–Malachi | todo | | |
| 11 | b11-ps-to-eccl | Psalms, Proverbs, Job, Song, Ruth, Lamentations, Ecclesiastes | todo | | |
| 12 | b12-esth-dan | Esther, Daniel | todo | | |
| 13 | b13-ezra-nehemiah | Ezra–Nehemiah | todo | | |
| 14 | b14-1chr-1 | 1 Chr 1 | todo | | |
| 15 | b15-1chr-2-4 | 1 Chr 2–4 | todo | | |
| 16 | b16-1chr-5-6 | 1 Chr 5–6 | todo | | |
| 17 | b17-1chr-7-9 | 1 Chr 7–9 | todo | | |
| 18 | b18-1chr-10-29 | 1 Chr 10–29 | todo | | |
| 19 | b19-2chr | 2 Chronicles | todo | | |

## Next step
**M89 (F2), viewer.** This step does:
- **API:** `src/bsim/api/{routes,queries,models}/genealogy.py`:
  - `GET /api/genealogy/skeleton`: every drawn node, compact (`person_id`, `he`, parent, `sex`, `kind`, `placement`, `book_id`, flags, `seq`) plus each node's spouses (`placement = spouse` people beside it);
  - `GET /api/genealogy/person/{id}`: parents, spouses, children by mother, siblings, proof verses as `{verse, tokens}`, conflicts;
  - `GET /api/genealogy/lookup?q=`: Hebrew name search, with a "son of X" subtitle.
- **Fixture rows** in `src/bsim/fixture.py`, and `npm run gen:api`.
- **Page:** `web/src/pages/GenealogyPage.tsx` at `/genealogy?p=`:
  - add `d3-hierarchy@3.1.2`;
  - nodes are HTML buttons over an SVG edge layer, laid out only over the expanded part;
  - collapse and expand;
  - mother headers when a father has several wives;
  - cross-links;
  - markers and a legend;
  - side panel, which becomes a bottom sheet at ≤ 860px;
  - `usePanZoom` shared with `GeoMap.tsx`.
- **Wiring:** `i18n/pages/genealogy.ts` (en + he), the nav line (Overview), the route.
- **Tests:** vitest, e2e (smoke, axe, fixture).

What the data gives the viewer (tables `genealogy_*` in `results.sqlite`):
- `genealogy_links.drawn = 1` is the tree.
- `placement`:
  - `root` is Adam;
  - `spouse` people are not nodes: draw them beside their spouse;
  - `virtual` nodes are "unattached" and one per book under it, labelled from the catalogs and the book's name. Their `he` is empty.
- A node is unreviewed when `genealogy_persons.reviewed = 0`, which gives the faint marker.
- Conflicts are `genealogy_conflicts`, whose readings are link ids, the first one drawn.
- Link `kind` `descendant` gives the violet dashed edge, and `role` `unstated` the grey dotted one.

## Conflicts found
None yet. Each entry: the child, the readings with their verses, the block that found it.

## Open questions
- `bsim places` drops TIPNR's references marked by their occurrence (`Exo.7.10a`, 15% of all) and doesn't map English numbering (`data/kjv.py`). Fixing both might improve the gazetteer, but it is outside this series: raise it with the user, don't just do it.
- 1,055 people are "unattached", mostly people with no family in the text. Most become reachable through search; the reviews may attach some.

## Log
- 2026-10-21, F0: plan approved; hand-off file, DESIGN §16.63 (design) / D101, TASKS milestones M88–M91 and review block F.
- 2026-10-21, M88: the data.
  - **Reader:** `read_tipnr()` reads the family columns (`TipnrFamily`) and every reference as written (`eng_refs`).
  - **Numbering:** `data/kjv.py` maps English to Hebrew numbering: 39 rules, and 98.3% of references then hit the name.
  - **Stage:** `bsim genealogy` and `bsim genealogy-review`, the `genealogy` config section, `paths.curation`, and DB tables `genealogy_{persons,links,proofs,conflicts,blocks}`.
  - **Real data:** 2,845 people; 1,818 parent links, 1,463 proved by a verse naming both, 218 with a nearby hint, 137 with nothing.
  - **Placement:** root 1, tree 1,553, tribe 169, spouse 67, unattached 1,055.
  - **Pipeline:** the stages flagged stale but unchanged were adopted (the encoders, places, place-lists, place-arc, place-links, gematria-links).
