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
| 04 | b04-gen-37-50 | Gen 37–50 | reviewed | 81 | 0 |
| 05 | b05-exod-lev | Exodus–Leviticus | reviewed | 49 | 0 |
| 06 | b06-num-deut | Numbers–Deuteronomy | reviewed | 67 | 2 |
| 07 | b07-josh-judg | Joshua–Judges | reviewed | 37 | 1 |
| 08 | b08-samuel | 1–2 Samuel | reviewed | 163 | 3 |
| 09 | b09-kings | 1–2 Kings | reviewed | 169 | 4 |
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
**M90, block 10: `b10-latter-prophets` (Isaiah–Malachi).** Follow **How to resume** step 2. Few genealogies, but the range is long; check the sheet's size first.

Things to look at in this block:
- **Write the review file from the sheet as it is before the block has a file** (save a copy first; block 03).
- **Reminder:** the API reads `results.sqlite`, so run `bsim build-db` before checking people at `/genealogy` or through the API.
- **The prophets' headings:** Isaiah son of Amoz, Jeremiah son of Hilkiah, Ezekiel son of Buzi, Hosea son of Beeri, Joel son of Pethuel, Jonah son of Amittai.
  - Zephaniah's line runs back four generations to "חזקיה" (Zeph 1:1). Whether this is King Hezekiah is not stated.
  - Zechariah is "בן ברכיה בן עדו" (Zech 1:1, 7) but "בן עדוא" in Ezra 5:1 and 6:14, a `descendant` conflict.
- **Families:**
  - Isaiah's sons: Shear-jashub (Isa 7:3), and Maher-shalal-hash-baz by "הנביאה" (8:3), who is unnamed.
  - Hosea's wife Gomer daughter of Diblaim and her three children (Hos 1).
  - Jeremiah's cousin Hanamel son of Shallum, his "דוד" (Jer 32:7).
  - Baruch son of Neriah son of Mahseiah, and Seraiah his brother (32:12, 51:59).
- **The house of Shaphan:** Ahikam, Gemariah, Elasah, Micaiah son of Gemariah (Jer 26, 29, 36). The sons of Kareah, Ishmael son of Nethaniah son of Elishama (Jer 40–41). Most are TIPNR links still open from block 09's people.
- **The last kings in Jeremiah:**
  - Shallum son of Josiah (Jer 22:11) is Jehoahaz, as against I Chr 3:15.
  - Coniah son of Jehoiakim (22:24).
  - Zedekiah son of Josiah (37:1). In 2 Kgs 24:17 he is "דדו", which agrees; 2 Chr 36:10 has "אחיו" (block 19).

## Conflicts found
Each entry: the child, the readings with their verses, the block that found it.
- **Uz, Hul, Gether, Mash** (b01): sons of Aram (Gen 10:23), or listed with the sons of Shem (I Chr 1:17, which writes Mash as משך). Aram drawn.
- **The Philistines** (b01): out of the Casluhim as Gen 10:14 runs, or from Caphtor (Amos 9:7, Jer 47:4). Casluhim drawn, both as `descendant`.
- **Laban** (b03, `descendant`): Bethuel's son (Gen 24:29, 28:5), "בן נחור" (29:5). Bethuel drawn.
- **Timna** (b03): daughter of Seir, Lotan's sister (Gen 36:20, 22), or among Eliphaz's sons (I Chr 1:36). Seir drawn.
- **Anah** (b03): son of Zibeon (Gen 36:2, 24) or of Seir (36:20, 29); perhaps two men, one TIPNR record. Zibeon drawn.
- **Eliab** (b06, `descendant`): Pallu's son (Num 26:5, 8), "אליאב בן ראובן" (Deut 11:6). Pallu drawn.
- **Achan** (b07, `descendant`): "עכן בן כרמי בן זבדי בן זרח" (Josh 7:1, 18), "עכן בן זרח" (7:24, 22:20). Carmi drawn.
- **Jair** (b06, `descendant`): Segub's son, whose mother was Machir's daughter (I Chr 2:21–22); "יאיר בן מנשה" (Num 32:41, Deut 3:14). Segub drawn; the link Jair <- Segub is confirmed early, on block 15's verses.
- **Kish** (b08): "קיש בן אביאל" (I Sam 9:1, 14:51); "ונר הוליד את קיש" (I Chr 8:33, 9:39). Abiel drawn. TIPNR takes Abiel for Jeiel of Gibeon (I Chr 9:35), whose sons include a Kish and a Ner (8:30, 9:36).
- **Abigail, Zeruiah's sister** (b08): "אביגל בת נחש" (II Sam 17:25); a sister of Jesse's sons (I Chr 2:16). Jesse drawn. Her husband is "יתרא הישראלי" in Samuel and "יתר הישמעאלי" in I Chr 2:17.
- **Mephibosheth** (b08, `descendant`): Jonathan's son (II Sam 4:4, 9:6); "מפבשת בן שאול" (19:25), and Saul "אביך" (9:7). Jonathan drawn.
- **Maacah, Abijam's mother** (b09): "מעכה בת אבישלום" (I Kgs 15:2), "בת אבשלום" (II Chr 11:20–21); "מיכיהו בת אוריאל מן גבעה" (II Chr 13:2). Absalom drawn. TIPNR's mother for her, Absalom's daughter Tamar, is rejected.
- **Athaliah** (b09, `descendant`): "בת אחאב" (II Kgs 8:18, II Chr 21:6); "עתליהו בת עמרי" (II Kgs 8:26, II Chr 22:2). Ahab drawn.
- **Jehu** (b09, `descendant`): "יהוא בן יהושפט בן נמשי" (II Kgs 9:2, 14); "יהוא בן נמשי" (I Kgs 19:16, II Kgs 9:20). Jehoshaphat drawn.
- **Azariah the priest** (b09, `descendant`): "עזריהו בן צדוק הכהן" (I Kgs 4:2); "ואחימעץ הוליד את עזריה" (I Chr 5:35), as TIPNR identifies him. Ahimaaz drawn; that link is confirmed early, on block 16's verse.

## Open questions
- **Tribe attachments that the text does not support** (for M91): TIPNR's tribe "Edom" hangs Seir the Horite and the kings of Edom's fathers (Beor, Zerah of Bozrah, Bedad, Achbor, Mezahab) on Esau by a link not stated. The Horites were in Seir before Esau (Deut 2:12, 22); the kings are not said to descend from him.
- **More tribe attachments of TIPNR's** (for M91), found in block 06:
  - Zurishaddai is filed under Benjamin, but his son Shelumiel is Simeon's chieftain (Num 1:6, 2:12).
  - Og is filed under Ben-ammi (tribe "Ammon"), but he is king of Bashan "מיתר הרפאים" (Deut 3:11).
  - Zippor is filed under Moab: his son Balak is king of Moab (Num 22:4), and his descent is not stated.
- **More TIPNR people filed under a tribe or unattached** (for M91), found in block 07:
  - Micah of Judg 17 is filed under Levi, but he is "מהר אפרים" (17:1); the Levite is the young man of Bethlehem (17:7).
  - Jephunneh has no tribe, so Caleb, Kenaz and Othniel sit under "Unattached". Caleb is of Judah (Num 13:6, 34:19). 1 Chr 2:9, 18, 42 and 4:15 have Calebs of Hezron's line; block 15 decides how they relate.
  - Joash, Gideon's father, is "אבי העזרי" (Judg 6:11, 24), of Abiezer, Gilead's son (Num 26:30, Josh 17:2), but he has no tribe.
- **Kenaz <- Jephunneh** (b07) is kept as `unstated`. It rests only on reading "עתניאל בן קנז אחי כלב (הקטן ממנו)" (Josh 15:17, Judg 1:13, 3:9) as Kenaz being Caleb's brother. "כלב בן יפנה הקנזי" (Num 32:12, Josh 14:6, 14) makes Caleb a Kenizzite instead.
- **Hobab** (b07): Num 10:29 has "חבב בן רעואל המדיני חתן משה", Judg 4:11 "חבב חתן משה". If חתן there means father-in-law, Hobab is Zipporah's father, against Exod 2:18–21 (Reuel). No conflict is recorded, since the word can mean any in-law; the tree follows Num 10:29.
- **Jonathan son of Gershom** (Judg 18:30) writes "בן מנשה" with a suspended nun; without it, it reads משה. TIPNR's Gershom is Moses' son (marked doubtful), and the link is kept.
- **Absalom's sons** (b08): "ויולדו לאבשלום שלושה בנים ובת אחת" (II Sam 14:27) against "אין לי בן" (18:18). The sons are not named and have no key, so no conflict can be recorded; only Tamar is in the tree.
- **Adriel's wife** (b08): Merab is given to Adriel (I Sam 18:19), but II Sam 21:8 has "חמשת בני מיכל בת שאול אשר ילדה לעדריאל", and Michal had no child (6:23). The five sons are not named, so nothing can be recorded. The tree keeps Merab as Adriel's wife and no Michal–Adriel link.
- **Nahash of II Sam 17:25** is made a man (`sex: m`): "אביגל בת נחש" names a parent, and the text does not say Nahash was Jesse's wife, as TIPNR has it. Her mother links to all of Jesse's children are rejected, including the ones in I Chr 2:14–15 and 27:18 (blocks 15, 18).
- **Mothers not stated** (b08), kept as `unstated`:
  - Ahinoam daughter of Ahimaaz for Saul's children: her name follows the list of 14:49, but the text does not say she bore them. Ish-bosheth, not on the list, is rejected.
  - Maacah for Tamar: "אחות אבשלם" (13:4) marks a full sister.
- **TIPNR identifications kept** (b08), one key for two names:
  - Ahijah son of Ahitub (I Sam 14:3, 18) is Ahimelech son of Ahitub.
  - Ishvi (14:49) is Abinadab.
  - Jonathan son of Shimea (II Sam 21:21, I Chr 20:7) is Jonadab (II Sam 13:3).
  - Abiel (I Sam 9:1) is Jeiel of Gibeon.
  - Merib-baal and Eshbaal (I Chr 8:33–34) are Mephibosheth and Ish-bosheth.
- **Name variants on one key** (b08):
  - Eliam / Ammiel and Bathsheba / Bath-shua (II Sam 11:3 / I Chr 3:5);
  - Chileab / Daniel (II Sam 3:3 / I Chr 3:1);
  - Maoch / Maacah, Achish's father (I Sam 27:2 / I Kgs 2:39);
  - Jaare-oregim / Jair, Elhanan's father (II Sam 21:19 / I Chr 20:5), where Samuel has Goliath and Chronicles "לחמי אחי גלית";
  - Palti / Paltiel, Toi / Tou, Joram / Hadoram, Sharar / Sachar.
- **Ahimelech and Abiathar** (b08): "אחימלך בן אביתר" (II Sam 8:17, I Chr 18:16, 24:6) against "אביתר בן אחימלך" (I Sam 22:20, 23:6). TIPNR has two Ahimelechs, so the tree keeps both links as written.
- **Jesse's sons:** eight (I Sam 17:12), seven named in I Chr 2:13–15. For block 15.
- **The Rapha's offspring** (b08): Ishbi-benob, Saph, Goliath, the man of 21:20 and Lahmi are `descendant`s of הרפה ("בילידי הרפה", "ילדו להרפה", II Sam 21:16–22). With the article, it reads as the eponym of the Rephaim, not a father. Rapha is unattached.
- **Asa's mother** (b09): "ושם אמו מעכה בת אבישלום" (I Kgs 15:10, 13), who is Abijam's mother (15:2), and Asa is Abijam's son (15:8). The link Asa <- Maacah is added as a mother link of kind `descendant`. Abijam stays Asa's drawn parent.
- **Eli** (b09): TIPNR hangs Eli on Ithamar through four invented unnamed generations (`Unnamed#1–4@1Ki.2.27`). Those links are rejected, and Eli <- Ithamar is added as `unstated`: Abiathar, of Eli's house (I Kgs 2:27), is of Ithamar's sons through Ahimelech (I Chr 24:3). The four unnamed people are left with no link. Block 18 rechecks this with I Chr 24.
- **Kings' wives:** each queen mother named at a son's accession is taken as the king's wife, as TIPNR has it. Proof: the son's accession and the mother's name (b09).
- **Mothers not stated** (b09), kept as `unstated`:
  - Jezebel for Ahaziah: "בדרך אמו" (I Kgs 22:53).
  - Athaliah for Jehosheba: "בת המלך יורם אחות אחזיהו" (II Kgs 11:2).
  - Joash "בן המלך" (I Kgs 22:26) for Ahab, perhaps a title; his link to Jezebel is rejected.
- **Not stated** (b09):
  - Ben-geber (I Kgs 4:13) as the son of Geber son of Uri (4:19).
  - Ethan and Heman as sons of Mahol: "מאיתן האזרחי והימן וכלכל ודרדע בני מחול" (5:11).
  - Mahol as Zerah's descendant, which rests on "האזרחי" alone.
  - I Chr 2:6 lists Ethan, Heman, Calcol and Dara as sons of Zerah. TIPNR uses other keys there (block 15).
- **TIPNR identifications kept** (b09):
  - Shisha (I Kgs 4:3) is Seraiah, David's scribe.
  - Nathan, father of Azariah and Zabud (4:5), is Nathan the prophet.
  - Hushai, Baana's father (4:16), is David's friend.
  - Shimei son of Ela (4:18) is the Shimei of 1:8.
  - Abishalom (15:2, 10) is Absalom.
  - The Pharaoh of Hadad and Tahpenes (11:19) is Solomon's father-in-law (one key).
- **Dropped TIPNR placeholders** (b09): the unnamed wife who is the mother of Solomon's daughters Taphath and Basemath. She stays as one of his wives (I Kgs 11:3). The unnamed husband of Shimeath, Jozacar's mother, is dropped.
- **For later blocks** (b09): Shomer, Jehozabad's father (II Kgs 12:22), is "שמרית המואבית" in II Chr 24:26, a woman (block 19). Hiram the craftsman has a mother "ממטה נפתלי" (I Kgs 7:14) or "מן בנות דן" (II Chr 2:13). No parent is named, so nothing is recorded.
- **Moses' Cushite wife** (Num 12:1) is added as her own person, `anon:cushite-wife-of-moses`. The text does not say whether she is Zipporah, a Midianite.
- **Name variants, Gen 46 against Num 26** (the parent agrees, so no conflict): Jemuel / Nemuel, Zohar / Zerah, Ezbon / Ozni, Iob / Jashub, Hushim / Shuham, Ehi / Ahiram, Muppim / Shephupham, Huppim / Hupham. Num 26 has no Ohad, Ishvah, Gera or Rosh. Also Deuel / Reuel (Num 1:14 / 2:14) and Abiezer / Iezer (Josh 17:2 / Num 26:30). TIPNR keeps each pair as one key; the Genesis form is the one shown.
- **Two Zurs of Midian**: TIPNR has two keys, Cozbi's father "ראש אמות בית אב במדין" (Num 25:15) and one of the five kings (31:8). They are perhaps one man.
- **Esau's wives** follow TIPNR's identifications: Basemath daughter of Elon (Gen 26:34) is Adah (36:2), Mahalath (28:9) is Basemath daughter of Ishmael (36:3). The fathers agree, the names differ; no conflict recorded, only noted in the review file.
- **One person in one list, two in another** (no conflict recordable): Gen 46:21 gives Naaman and Ard as Benjamin's sons, Num 26:40 as Bela's sons, and TIPNR has two people each (`Naaman@Gen.46.21-1Ch` / `Naaman@Num.26.40-1Ch`). A conflict needs one key with two parents; merging TIPNR keys is not supported. Revisit in M91, with Benjamin's sons in Num 26:38–40 and 1 Chr 7:6, 8:1–5.
- **Adoption** (for M91): Jacob takes Ephraim and Manasseh as his own (Gen 48:5). An `adopted` father link beside Joseph would compete with him for the drawn parent; decide how adoption shows in the tree.
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
- 2026-10-21, M90 block 04 (Gen 37–50): `curation/genealogy/04-b04-gen-37-50.yaml`, reviewed.
  - 81 links checked: 79 confirmed, 1 added, 1 rejected; 22 cue verses dismissed (Jacob's sons together, the counts of the seventy, links checked in block 03). No cue verse is left unhandled.
  - **Picked up from later sheets:** Gen 38 (Bath-shua <- Shua, her three sons, Shelah <- Judah, Perez and Zerah <- Judah and Tamar), Manasseh and Ephraim <- Joseph (41:50–52, 46:20, 48:5), and the Gen 46 sons whose best verse was in Exodus, Numbers or 1 Chronicles (Carmi, Simeon's Jachin, Zohar and Shaul, Levi's three, Asher's Imnah and Serah).
  - **Rejected:** Tamar as Judah's wife: she bore his sons, but "ולא יסף עוד לדעתה" (38:26).
  - **Added:** Tamar and Onan, the levirate (38:8–9).
  - **Names:** Simeon's Zohar reads צחר (TIPNR had זרח from Numbers and Chronicles), Benjamin's Ehi אחי (TIPNR had אחירם from Numbers), Simeon's unnamed wife הכנענית.
  - Kept: TIPNR's unnamed wife of Simeon, the mother of his sons other than Shaul "בן הכנענית" (46:10).
  - Left open: Machir's mother, the Aramitess (I Chr 7:14), for block 17.
- 2026-10-21, M90 block 05 (Exodus–Leviticus): `curation/genealogy/05-b05-exod-lev.yaml`, reviewed.
  - 49 links checked: 48 confirmed, 1 added; 147 cue verses dismissed, nearly all "בני ישראל" (the people) or Aaron's unnamed sons (the priests). No cue verse is left unhandled.
  - **Picked up from later sheets:** Amram and Jochebed, Moses and Aaron <- Amram (Exod 6:20), Libni, Izhar, Mushi, Korah <- Izhar, Ebiasaph, Phinehas <- Eleazar (6:17–25), Gershom and Eliezer <- Moses (2:22, 18:3–5).
  - **Added:** Moses <- Pharaoh's daughter, `adopted` (2:10, "ויהי לה לבן"); his father Amram stays the drawn parent, Jochebed his mother.
  - Kept: TIPNR's Jethro as Zipporah's father, the man 2:18 calls רעואל.
  - Left open for later blocks: Jochebed, Miriam and Nahshon (Numbers); Amminadab <- Ram, Hur <- Caleb and Ephrathah, Nun <- Elishama (Ruth, 1 Chronicles; Nun's is only a `nearby` hint, I Chr 7:27).
- 2026-10-21, M90 block 06 (Numbers–Deuteronomy): `curation/genealogy/06-b06-num-deut.yaml`, reviewed.
  - **Counts:** 67 links checked (66 confirmed, 1 added), 2 conflicts, 228 cue verses dismissed. Nearly all the cues are "בני ישראל", the tribes, the chieftains named again, or links checked in blocks 04–05. No cue verse is left unhandled.
  - **Confirmed:** the chieftains of Num 1–2, 7, 10, 13 and 34 and the Levite heads of Num 3; Dathan, Abiram and Nemuel <- Eliab <- Pallu; On <- Peleth; Balak <- Zippor, Balaam <- Beor; Zimri <- Salu, Cozbi <- Zur; Hobab <- Jethro (Num 10:29, as TIPNR's one Jethro / Reuel); Jochebed <- Levi, Miriam <- Jochebed (26:59).
  - **The line of Manasseh:** Gilead <- Machir (26:29, "ומכיר הוליד את גלעד"), Gilead's six sons (26:30–32), Zelophehad <- Hepher and his five daughters. Ephraim's Shuthelah, Becher and Tahan, Eran <- Shuthelah; Bela's Ard and Naaman (26:40, the open question stands).
  - **Picked up from later sheets:** Shuthelah <- Ephraim (26:35), Shemida <- Gilead (26:30, 32), Miriam <- Amram (26:59).
  - **Added:** Moses' Cushite wife (12:1), as a spouse.
  - **Names:** Issachar's Jashub reads יוב and Puah פוה, as Genesis 46:13 writes them (block 04's rule for צחר).
  - **Left for block 07:** Kenaz <- Jephunneh (TIPNR), Anak's sons, Hobab as Moses' חתן.
  - Checked in the API: Moses with two wives, Gilead's six sons, Eliab's and Jair's conflicts with both readings.
- 2026-10-21, M90 block 07 (Joshua–Judges): `curation/genealogy/07-b07-josh-judg.yaml`, reviewed.
  - **Counts:** 37 links checked (25 confirmed, 2 fixed, 3 rejected, 7 added), 1 conflict, 223 cue verses dismissed. Nearly all the cues are "בני ישראל", the tribes, Ammon, or Joshua son of Nun. No cue verse is left unhandled.
  - **Confirmed:** Achan <- Carmi <- Zabdi <- Zerah (Josh 7:1, 18); Anak <- Arba ("ארבע אבי הענק", 15:13) and Anak's three sons, taking ענק as a man, as TIPNR does; Achsah <- Caleb and Othniel her husband; Othniel <- Kenaz; the judges' fathers (Shamgar, Barak, Gideon, Tola, Jephthah, Abdon, Samson); Deborah and Lappidoth, Jael and Heber; Gideon's sons Jether, Abimelech and Jotham; Gaal <- Ebed; Jonathan <- Gershom (Judg 18:30).
  - **Fixed:**
    - Ehud <- Gera is a `descendant`: TIPNR's Gera is Benjamin's son.
    - Kenaz <- Jephunneh is `unstated` (left open by block 06).
  - **Rejected:**
    - Delilah as Samson's wife: 16:4 tells of love, no marriage.
    - Rahab as Salmon's wife and Boaz's mother: that is Matthew 1:5.
  - **Added:**
    - Gideon's concubine in Shechem, Abimelech's mother (8:31, 9:18).
    - Manoah's wife, Samson's mother (13:2, 24).
    - Jephthah's mother (11:1–2).
    - Samson's Timnite wife (14:2, 20, 15:6).
    - Bohan <- Reuben as a `descendant` ("אבן בהן בן ראובן", Josh 15:6, 18:17).
  - **Checked in the API, after `bsim build-db`:** Gideon's children grouped by mother, Samson with his Timnite wife only, and the conflict on Achan.
- 2026-10-21, M90 block 08 (1–2 Samuel): `curation/genealogy/08-b08-samuel.yaml`, reviewed.
  - **Counts:** 163 links checked (138 confirmed, 12 fixed, 11 rejected, 2 added), 3 conflicts, 93 cue verses dismissed. Most cues are "בני ישראל", "בני עמון", or "בן ישי", "בן צרויה" and "יונתן בנו" repeated. No cue verse is left unhandled. The block fits one session; no split was needed.
  - **Confirmed:**
    - Elkanah's line to Zuph (I Sam 1:1); Hannah and Peninnah; Samuel <- Elkanah and Hannah; Joel and Abijah <- Samuel (8:1–2).
    - Eli's house: Hophni and Phinehas, Ichabod and Ahitub, Ahimelech son of Ahitub (proved on 22:9–20, not 14:3), Abiathar, Jonathan son of Abiathar.
    - Saul's line from Aphiah to Kish, and Ner <- Abiel (14:51). Saul's children, Rizpah's Armoni and Mephibosheth, and Michal's husbands David and Palti; Merab and Adriel; Mephibosheth and Micah.
    - David: Jesse's sons, Zeruiah and her three sons, whose father is not named but has a tomb in Bethlehem (II Sam 2:32). Amasa <- Jether and Abigail.
    - David's wives and the sons of Hebron and Jerusalem (3:2–5, 5:13–16); Solomon <- Bathsheba; Tamar; Jonadab <- Shimeah.
    - The officials and heroes with their fathers (8:16–18, 23:8–39).
  - **Fixed:**
    - Ahinoam's five children and Tamar <- Maacah are `unstated`.
    - Abigail <- Nahash is a father link.
    - The Rapha's five offspring are `descendant`s.
  - **Rejected:**
    - Ish-bosheth <- Ahinoam.
    - TIPNR's Nahash as Jesse's wife, with her nine mother links (five here, four on later sheets).
  - **Added:** Phinehas's wife, Ichabod's mother (4:19–21).
  - **Code:** a `fixed` link with a new parent `role` (mother to father) used to fail, because the lookup filtered by the new role. It now falls back to the pair's other parent link (`apply_curation`). New test: `test_fixed_changes_the_role`.
- 2026-10-21, M90 block 09 (1–2 Kings): `curation/genealogy/09-b09-kings.yaml`, reviewed.
  - **Counts:** 169 links checked (146 confirmed, 7 fixed, 14 rejected, 2 added), 4 conflicts, 105 cue verses dismissed. Most cues are "ירבעם בן נבט", "בני ישראל", "בניהו בן יהוידע", and "וימלך X בנו תחתיו" for links proved elsewhere. No cue verse is left unhandled.
  - **Confirmed:**
    - Both royal lines, with every queen mother and her father: Naamah, Azubah daughter of Shilhi, Athaliah, Zibiah, Jehoaddan, Jecoliah, Jerusha daughter of Zadok, Abi daughter of Zechariah, Hephzibah, Meshullemeth, Jedidah, Hamutal, Zebidah, Nehushta.
    - The kings of Israel and their fathers; Jezebel <- Ethbaal; Joram <- Jezebel (II Kgs 9:22).
    - Solomon's officials and his daughters Taphath and Basemath; Pharaoh's daughter; Tahpenes and Hadad's Genubath; Hiel's sons; Sennacherib's three sons.
    - The scribes and officers of Josiah and Gedaliah: Shaphan, Ahikam, Achbor, Huldah's husband Shallum.
  - **Picked up from later sheets:** the kings whose "בנו תחתיו" was not found as a proof: Rehoboam, Abijam, Asa, Manasseh, Amon, Josiah, Jehoiachin. Also the mothers of Abijam, Amaziah, Uzziah, Jotham and Hezekiah, and Jehoram's wife Athaliah.
  - **Fixed:** seven links `unstated` (see the open questions).
  - **Rejected:** Eli's four unnamed forefathers; mothers no verse names (Tahpenes, Tamar, Jezebel twice, Solomon's unnamed wife twice); Uriel as Tamar's husband; Shimeath's unnamed husband.
  - **Added:** Asa <- Maacah (`descendant`), Eli <- Ithamar (`unstated`).
