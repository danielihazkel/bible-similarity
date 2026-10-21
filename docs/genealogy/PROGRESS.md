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
| M89 (F2) | Viewer: API, `/genealogy` tree, collapsing, panel, search, legend, EN/HE, responsive | done |
| M90 (F3) | Review block by block (below) | in progress |
| M91 (F4) | Cross-book pass, tribe attachments, jump box, dossier entry | todo |

Review blocks (M90), in Jewish canon order:

| # | Block | Range | Status | Links checked | Conflicts |
|---|---|---|---|---|---|
| 01 | b01-gen-1-11 | Gen 1–11 | reviewed | 116 | 5 |
| 02 | b02-gen-12-25 | Gen 12–25:18 | reviewed | 84 | 0 |
| 03 | b03-gen-25-36 | Gen 25:19–36 | reviewed | 108 | 3 |
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
**M90, block 04: `b04-gen-37-50` (Gen 37–50).** Follow **How to resume** step 2.

Things to look at in this block:
- **Write the review file from the sheet as it is before the block has a file.** Once a file proves links with this block's verses, the regenerated sheet lists them too, and a generator run on it doubles them (block 03 hit this).
- The block's people's links on later sheets (1 Chronicles, Numbers 26): check them here as before.
- Gen 38: Judah, Bath-shua (an unnamed `anon` in TIPNR? check), Er, Onan, Shelah, Tamar, Perez and Zerah.
- Gen 41:45–52: Asenath daughter of Potiphera; Manasseh and Ephraim.
- Gen 46:8–27, the seventy: the grandsons of Jacob, and where Numbers 26 and 1 Chronicles 4–8 name them differently (Jemuel / Nemuel, Ohad, Jachin / Jarib, Zohar / Zerah; Benjamin's ten sons against Num 26:38–40 and 1 Chr 7:6, 8:1–2) — `bible` conflicts or one person with several names. Hezron and Hamul, Perez's sons, born in Canaan's reckoning.
- Simeon's Canaanite wife (46:10) and Joseph's Egyptian line.

## Conflicts found
Each entry: the child, the readings with their verses, the block that found it.
- **Uz, Hul, Gether, Mash** (b01): sons of Aram (Gen 10:23), or listed with the sons of Shem (I Chr 1:17, which writes Mash as משך). Aram drawn.
- **The Philistines** (b01): out of the Casluhim as Gen 10:14 runs, or from Caphtor (Amos 9:7, Jer 47:4). Casluhim drawn, both as `descendant`.
- **Laban** (b03, `descendant`): Bethuel's son (Gen 24:29, 28:5), "בן נחור" (29:5). Bethuel drawn.
- **Timna** (b03): daughter of Seir, Lotan's sister (Gen 36:20, 22), or among Eliphaz's sons (I Chr 1:36). Seir drawn.
- **Anah** (b03): son of Zibeon (Gen 36:2, 24) or of Seir (36:20, 29); perhaps two men, one TIPNR record. Zibeon drawn.

## Open questions
- **Tribe attachments that the text does not support** (for M91): TIPNR's tribe "Edom" hangs Seir the Horite and the kings of Edom's fathers (Beor, Zerah of Bozrah, Bedad, Achbor, Mezahab) on Esau by a link not stated. The Horites were in Seir before Esau (Deut 2:12, 22); the kings are not said to descend from him.
- **Esau's wives** follow TIPNR's identifications: Basemath daughter of Elon (Gen 26:34) is Adah (36:2), Mahalath (28:9) is Basemath daughter of Ishmael (36:3). The fathers agree, the names differ; no conflict recorded, only noted in the review file.
- The skeleton is ~650 KB of JSON (gzipped in transit), fetched once per visit. Fine now; if M91 adds fields, consider a compact array form.
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
- 2026-10-21, M89: the viewer.
  - **API:** `/api/genealogy/skeleton` (2,816 nodes, 64 spouses beside them, 113 cross-links), `/api/genealogy/person/{id}`, `/api/genealogy/lookup?q=`; fixture rows (a made-up tree from Adam to Lamech's wives, with a conflict, a descendant link, a tribe and a book group).
  - **Page:** Overview → Family tree (`/genealogy?p=`), `d3-hierarchy` 3.1.2. Children hang from mother headers when they have more than one mother, the attached apart; the unnamed are named by what they are to their parent or spouse ("בת לוט"). It opens on Adam's first three generations; nodes off screen are not drawn.
  - **Pan and zoom:** `lib/panZoom.ts` (drag, pinch, Ctrl + wheel), shared with `GeoMap`, which gains pinch and Ctrl + wheel.
  - **Panel:** parents, spouses, children by mother, siblings, the people attached, each link's verses with both names marked, a conflict's readings; it can open or close everything below. On a phone it is a bottom sheet, and the search sits above it.
  - **Checked** on the real data in both languages, light and dark, desktop and phone: Jacob's sons under Leah, Bilhah, Zilpah and Rachel, with verses.
- 2026-10-21, M90 block 01 (Gen 1–11): `curation/genealogy/01-b01-gen-1-11.yaml`, reviewed.
  - 116 links checked: 104 confirmed (proofs chosen by hand where the sentence runs on: Gen 4:19–22, 10:13–18, 10:26–29), 7 fixed, 1 added, 4 rejected; 5 conflicts; 2 cue verses dismissed. No cue verse is left unhandled.
  - **Added:** Shelah ← Arpachshad (Gen 10:24, 11:12–13); TIPNR had Shelah with no parent, under "unattached".
  - **Rejected:** Naamah as Noah's wife and the mother of Shem, Ham and Japheth (TIPNR's `(?)`): Genesis Rabbah 23:3, not the text. Rabbinic identifications are deferred.
  - **Fixed:** seven peoples of Gen 10 TIPNR marks as descended groups (Dodanim, Anamim, Casluhim, Caphtorim, Amorites, Arkites, Arvadites) are sons in the text (בני, ילד).
  - **Kept, on one verse:** Sarah ← Terah rests on Abraham's "בת אבי היא" (Gen 20:12) alone; Gen 11:31 calls her Terah's כלה.
  - **Names:** Dedan was רדן in TIPNR (now דדן); Dodanim had the Chronicles spelling (now דדנים).
  - Cain's and Seth's lines keep their two Lamechs and two Enochs apart (separate TIPNR keys).
- 2026-10-21, M90 block 02 (Gen 12–25:18): `curation/genealogy/02-b02-gen-12-25.yaml`, reviewed.
  - 84 links checked: 81 confirmed, 1 fixed, 2 rejected; 21 cue verses dismissed (בן as an age, "the sons of Heth", the promise of a son, Isaac called בנו again). No cue verse is left unhandled.
  - **Picked up from later sheets:** 24 links of the block's people whose best verse was in 1 Chronicles, now proved on Genesis: Isaac <- Abraham (21:2–5), Rebekah <- Bethuel (22:23), Isaac and Rebekah (24:67), Laban <- Bethuel (24:29, 28:5), Abraham and Keturah and her six sons (25:1–4), Jokshan's two (25:3), Ishmael's five younger sons (25:13–16).
  - **Rejected:** Lot's daughters as his spouses (TIPNR): they bore his sons (19:31–36), the text tells of no marriage. Moab and Ben-ammi stay under Lot, their mothers named.
  - **Kept:** TIPNR's unnamed father of Mamre, Eshcol and Aner, who are brothers (14:13).
  - **Fixed:** Asshurim, a son of Dedan in the text (25:3), not a descended group.
  - Left for block 03: Hori <- Lotan (Gen 36).
- 2026-10-21, M90 block 03 (Gen 25:19–36): `curation/genealogy/03-b03-gen-25-36.yaml`, reviewed.
  - 108 links checked: 106 confirmed, 2 rejected; 3 conflicts; 15 cue verses dismissed. No cue verse is left unhandled.
  - **Picked up from later sheets:** Esau and Jacob <- Isaac (25:26, 35:29), Leah <- Laban (29:16, 23–24), Rachel as Jacob's wife (29:28), Jacob's twelve sons and Dinah by their births (29:31–30:24, 35:16–18) and 35:22–26, Esau's sons by Oholibamah (36:5, 14), Seir's sons (36:20–21).
  - **Rejected:** TIPNR's husband of Matred, and Mehetabel <- him: "מהיטבאל בת מטרד" names a mother only.
  - **Names:** Jacob now reads יעקב (TIPNR's record is "Israel"; search finds him as יעקב). Hadad of Gen 36:39 reads הדר, as Genesis writes it.
  - Kept: TIPNR's unnamed wife of Eliphaz, the mother of his sons other than Amalek (Timna was his concubine, 36:12).

