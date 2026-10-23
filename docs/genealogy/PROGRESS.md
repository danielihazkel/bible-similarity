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

## Decisions (user, 2026-10-22, for M91)
- **One person under two TIPNR keys** is recorded in a `same:` list, with proof verses and a status:
  - `merged`: the keys become one node. Where the keys had different parents, the merged person gets a Bible-vs-Bible conflict.
  - `possible`: both nodes stay, and the panel shows "may be the same as …" with the proofs.
- **Adoption** (Jacob and Ephraim and Manasseh, Gen 48:5) is an `adopted` link from Jacob, shown in the panel as a cross-link. The tree keeps drawing them under Joseph.

## Curated file format
One file per block, `curation/genealogy/NN-<block>.yaml`; the block's verse range is in `genealogy.blocks` (`configs/default.yaml`). Keys are TIPNR's unique names exactly as the review sheet prints them.
```yaml
block: b13-ezra-nehemiah
status: reviewed          # draft | reviewed
people:                   # added people (anon:…) or corrections to TIPNR (he, sex, tribe)
  - {key: "Seir@Gen.36.20-1Ch", tribe: ""}   # tribe "": hung on no tribe's eponym (M91)
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
same:                     # one person under several TIPNR keys (M91); the first key is kept
  - {keys: ["Asriel@Num.26.31-Jos", "Asriel@1Ch.7.14"], status: merged, proof: [Numbers 26:31, I Chronicles 7:14]}
  - {keys: ["Elihu@1Ch.27.18", "Eliab@1Sa.16.6-2Ch"], status: possible, proof: [I Chronicles 27:18], note: {en: "…", he: "…"}}
missed:                   # cue verses of the sheet that are no link, each with a reason
  - {ref: Genesis 4:25, reason: "Cain named as Abel's killer"}
```
Rules the build enforces, stopping on any error:
- `confirmed` and `fixed` need a TIPNR link, and `added` must not have one.
- A link is decided once: listing it under `links` again, in the same file or a later one, or after an earlier file's conflict reading, is an error. A conflict's reading may still name a link decided elsewhere.
- Every key and reference must resolve, and the tree must not get a cycle.
- `same:` (M91): `merged` folds the other keys into the first before any link is decided, and the merged keys still name the person in every file. A link that two files decided under the two pairs of keys must have the same status there. A merged person with two fathers (or mothers) needs a conflict listing them as readings. `possible` keeps both persons; it cannot name two keys already merged. Both need proof verses.
- The cross-book steps' files are `curation/genealogy/xNN-<topic>.yaml`, with `block` one of `genealogy.cross_blocks` (`x03-edom` … `x09-unattached`). They have no verse range and no review sheet.
- A `people:` correction `tribe: ""` takes a person without a parent off TIPNR's tribe or nation: it goes under "unattached", by its book (M91 step 3).
- An adoptive father is a link of kind `adopted` (`role: father`); it is never the one the tree draws while the child has another father.

A person counts as reviewed when every parent link of theirs is checked.

## Status

| Step | What | Status |
|---|---|---|
| F0 | Hand-off file, DESIGN §16.63 / D101, TASKS milestones | done |
| M88 (F1) | Data: TIPNR family columns, `bsim genealogy`, automatic proofs, curated loader, `genealogy-review`, DB tables | done |
| M89 (F2) | Viewer: API, `/genealogy` tree, collapsing, panel, search, legend, EN/HE, responsive | done |
| M90 (F3) | Review block by block (below) | done |
| M91 (F4) | Cross-book pass, tribe attachments, jump box, dossier entry (below) | done |

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
| 10 | b10-latter-prophets | Isaiah–Malachi | reviewed | 68 | 2 |
| 11 | b11-ps-to-eccl | Psalms, Proverbs, Job, Song, Ruth, Lamentations, Ecclesiastes | reviewed | 25 | 0 |
| 12 | b12-esth-dan | Esther, Daniel | reviewed | 35 | 0 |
| 13 | b13-ezra-nehemiah | Ezra–Nehemiah | reviewed | 142 | 5 |
| 14 | b14-1chr-1 | 1 Chr 1 | reviewed | 0 | 0 |
| 15 | b15-1chr-2 | 1 Chr 2 | reviewed | 134 | 0 |
| 15b | b15b-1chr-3-4 | 1 Chr 3–4 | reviewed | 166 | 0 |
| 16 | b16-1chr-5-6 | 1 Chr 5–6 | reviewed | 71 | 2 |
| 17 | b17-1chr-7 | 1 Chr 7 | reviewed | 114 | 0 |
| 17b | b17b-1chr-8-9 | 1 Chr 8–9 | reviewed | 147 | 4 |
| 18 | b18-1chr-10-29 | 1 Chr 10–29 | reviewed | 130 | 2 |
| 19 | b19-2chr | 2 Chronicles | reviewed | 63 | 0 |

Cross-book steps (M91), planned in step 1:

| Step | What | Status |
|---|---|---|
| 1 | The plan; the format for identifications and adoption, asked | done |
| 2 | Build `same:` (`merged` / `possible`) and `adopted` cross-links: loader, tree, API, panel, DESIGN §16.63, tests | done |
| 3 | Gen 36 / I Chr 1: Edom's chiefs and kings, the Horites | done |
| 4 | Gen 46 / Num 26 / I Chr 2–4: Judah and Simeon, Caleb and Achsah, Salma, Hur, Zerah's sons and the Ezrahite sages | done |
| 5 | Gen 46 / Num 26 / I Chr 5–8: Reuben, Levi (Korah's line, the two lines from Kohath to Samuel), Benjamin, Manasseh, Ephraim, Asher | done |
| 6 | Ezra 7 / I Chr 5:27–41, Neh 11–12 / I Chr 9: the priests, the Levites, the gatekeepers and the singers | done |
| 7 | Samuel–Kings / Chronicles: David's brothers, the kings' sons, Josiah's sons and Zedekiah, the Levites of David's lists | done |
| 8 | Tribe attachments: TIPNR's that the text does not support (blocks 01–13) | done |
| 9 | "Unattached": people whose tribe or family the text states | done |
| 10 | A People group in the jump box, and a dossier entry for the people of a unit (D99 / D100) | done |

## Next step
**Series F is done (M88–M91).** Nothing is scheduled. F5, rabbinic identifications as a third kind of conflict with their sources from Sefaria, waits until the user asks for it (deferred, 2026-10-21; `docs/TASKS.md`).

If the user asks for more on the tree before then, the material is here:
- The **Open questions** below. The items marked "(M91)" all carry a **Step N:** note saying how they were settled or why they were left.
- The `possible` identities (20), which a later pass may merge or drop.
- The 908 people still under "unattached", mostly people with no family in the text.

New curated files follow the same format (above). A cross-book file needs its block added to `genealogy.cross_blocks`.

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
- **Zerubbabel** (b10): "זרבבל בן שאלתיאל" (Hag 1:1, 12, 14, 2:2, 23, Ezra 3:2, Neh 12:1); "ובני פדיה זרבבל ושמעי" (I Chr 3:19), where Pedaiah is listed with Shealtiel among Jeconiah's sons (3:17–18). Shealtiel drawn; the link Zerubbabel <- Pedaiah is confirmed early, on block 15's verse.
- **Zechariah the prophet** (b10, `descendant`): "זכריה בן ברכיה בן עדו" (Zech 1:1, 7); "זכריה בר עדוא" (Ezra 5:1, 6:14). Berechiah drawn.
- **Ezra** (b13, `descendant`, one reading): "עזרא בן שריה" (Ezra 7:1). Seraiah the chief priest was put to death at Riblah (II Kgs 25:18–21) and his son Jehozadak went into exile (I Chr 5:40–41); Ezra went up in Artaxerxes' seventh year (Ezra 7:7–8). Seraiah drawn as a `descendant`.
- **Azariah son of Johanan** (b13, `descendant`): "ויוחנן הוליד את עזריה" (I Chr 5:36); "בן עזריה בן מריות" (Ezra 7:3), which leaves out the six names from Amariah to Johanan of I Chr 5:33–36. Johanan drawn; that link is confirmed early, on block 16's verse.
- **Mahli** (b13, `descendant`): Merari's son (Ex 6:19, Num 3:20, I Chr 6:4); "מחלי בן לוי בן ישראל" (Ezra 8:18). Merari drawn.
- **Johanan the high priest** (b13, `descendant`): between Joiada and Jaddua, "ויוידע הוליד את יונתן" (Neh 12:11) and "אלישיב יוידע ויוחנן וידוע" (12:22); "יוחנן בן אלישיב" (12:23). Joiada drawn.
- **Jeroham** (b13, `descendant`): "ירחם בן פלליה בן אמצי בן זכריה בן פשחור" (Neh 11:12); "ירחם בן פשחור" (I Chr 9:12). Pelaliah drawn.
- **Zimmah** (b16, `descendant`): "זמה בן שמעי בן יחת בן גרשם" (I Chr 6:27–28); "לבני בנו יחת בנו זמה בנו" (6:5), with no Shimei between. Shimei drawn. TIPNR's key for Jahath is Jehiel son of Ladan (23:8), so that reading shows the name יחיאל; block 18 checks that identification.
- **Ahimoth** (b16): "אלקנה בן מחת בן עמשי" (I Chr 6:20), where TIPNR takes Mahath for Ahimoth; "ובני אלקנה עמשי ואחימות" (6:10), where Ahimoth is Amasai's brother. Amasai drawn.
- **Gera, Muppim and Huppim** (b17b): Benjamin's sons (Gen 46:21; Shephupham and Hupham in Num 26:39); among Bela's sons, "ויהיו בנים לבלע אדר וגרא ... וגרא ושפופן וחורם" (I Chr 8:3–5), where TIPNR takes the second Gera, Shephuphan and Huram for Benjamin's sons. Benjamin drawn.
- **Zadok, Shallum's father** (b17b): "ואחיטוב הוליד את צדוק וצדוק הוליד את שלום" (I Chr 5:38), "בן שלום בן צדוק בן אחיטוב" (Ezra 7:2); "בן משלם בן צדוק בן מריות בן אחיטוב" (I Chr 9:11, Neh 11:11). Ahitub drawn. TIPNR's key for that Meraioth is Zerahiah's son (5:32), so the second reading shows him.
- **Zetham and Joel** (b18): "בני לעדן הראש יחיאל וזתם ויואל שלשה" (I Chr 23:8), Jehiel's brothers; "בני יחיאלי זתם ויואל אחיו" (26:22), Jehieli's sons, unless יחיאלי names the clan. Ladan (TIPNR's Libni) drawn.
- **Achsah** (x04): daughter of Caleb son of Jephunneh (Josh 15:16–17, Judg 1:12–13) and of Caleb son of Hezron (I Chr 2:49), one person since the merge. Caleb son of Jephunneh drawn.
- **Ethan, Heman, Calcol and Dara** (x04): "ובני זרח זמרי ואיתן והימן וכלכל ודרע" (I Chr 2:6); "איתן האזרחי והימן וכלכל ודרדע בני מחול" (I Kgs 5:11). Zerah drawn; if "בני זרח" means descendants, Mahol stands between.
- **Ard and Naaman** (x05): Benjamin's sons (Gen 46:21); Bela's (Num 26:40, I Chr 8:3–4, Addar for Ard), one person each since the merge. Benjamin drawn, as for Gera, Muppim and Huppim.
- **Asriel** (x05): Gilead's son (Num 26:30–31); Manasseh's, born of the Aramean concubine (I Chr 7:14). Gilead drawn.
- **Abiezer** (x05): Gilead's son, as Iezer (Num 26:30, Josh 17:2); the son of Hammolecheth, Gilead's sister, and her husband (I Chr 7:18). Gilead drawn.
- **Shechem** (x05): Gilead's son, Shemida's brother (Num 26:31–32); "ויהיו בני שמידע אחין ושכם" (I Chr 7:19). Gilead drawn.
- **Elkanah and Ebiasaph** (x05): Korah's sons (Ex 6:24; I Chr 6:22 for Ebiasaph), or a chain, "קרח בנו אסיר בנו אלקנה בנו ואביסף בנו" (I Chr 6:7–8). Korah drawn.
- **Meshullam, Sallu's father** (x06): "בן יועד בן פדיה" (Neh 11:7) or "בן הודויה בן הסנאה" (I Chr 9:7), one person since the merge. Joed drawn.
- **Mica, Mattaniah's father** (x06): son of Zichri (I Chr 9:15; Zabdi in Neh 11:17) or of Zaccur (Neh 12:35), each a son of Asaph. Zichri drawn.
## Open questions
- **Edom** (M91 step 3, settled): Seir the Horite, the kings of Edom and their fathers, Elon and Beeri the Hittites, and TIPNR's husband of Matred are taken off TIPNR's tribe "Edom" (`tribe: ""` in `x03-edom.yaml`) and sit under "unattached". The chiefs of Gen 36:40–43 ("אלופי עשו") and Hadad "האדמי" (I Kgs 11:14) stay under Esau.
- **Edom, left as TIPNR has it** (M91 step 3):
  - TIPNR's Hori son of Lotan (Gen 36:22) is also the Horites of Gen 14:6 and Deut 2:12, 22, and "החרי" of 36:20–30, so the people is filed under Seir's grandson, while Seir himself is "החרי". There is no way to split a key.
  - The chiefs Timna and Oholibamah (Gen 36:40–41, I Chr 1:51–52) are on the keys of Seir's daughter and Esau's wife; Teman also holds "התימני" (36:34, Job).
  - Amalek of I Chr 1:36 is on no key (TIPNR's Amalek has only Gen 36:12, 16).
  - Not recorded as identities: Judith daughter of Beeri the Hittite (26:34) and Oholibamah daughter of Anah the Hivite (36:2), the wife each list has left after the two TIPNR matches by father (other father, other people); Zerah of Bozrah (36:33) and Zerah son of Reuel (36:13); Hadad son of Bedad (36:35) and Hadad the Edomite (I Kgs 11:14). The names alone are the link.
  - Korah of Gen 36:16, a chief of Eliphaz's line, is recorded as `possible` with Korah son of Oholibamah (36:5, 18): Eliphaz's sons (36:11–12, I Chr 1:36) have no Korah.
- **More tribe attachments of TIPNR's** (for M91), found in block 06:
  - Zurishaddai is filed under Benjamin, but his son Shelumiel is Simeon's chieftain (Num 1:6, 2:12). **Step 8:** moved to Simeon.
  - Og is filed under Ben-ammi (tribe "Ammon"), but he is king of Bashan "מיתר הרפאים" (Deut 3:11). **Step 8:** off Ammon, unattached.
  - Zippor is filed under Moab: his son Balak is king of Moab (Num 22:4), and his descent is not stated. **Step 8:** kept: he carries Balak, "מלך למואב".
- **More TIPNR people filed under a tribe or unattached** (for M91), found in block 07:
  - Micah of Judg 17 is filed under Levi, but he is "מהר אפרים" (17:1); the Levite is the young man of Bethlehem (17:7). **Step 8:** off Levi, unattached.
  - Jephunneh has no tribe, so Caleb, Kenaz and Othniel sit under "Unattached". Caleb is of Judah (Num 13:6, 34:19). 1 Chr 2:9, 18, 42 and 4:15 have Calebs of Hezron's line; block 15 decides how they relate. **Step 4:** Jephunneh is filed under Judah (`tribe` correction); the two Calebs are a `possible`.
  - Joash, Gideon's father, is "אבי העזרי" (Judg 6:11, 24), of Abiezer, Gilead's son (Num 26:30, Josh 17:2), but he has no tribe. **Step 8:** added Joash <- Abiezer, a `descendant` (Judg 6:11, 24, 8:32).
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
- **Ahimelech and Abiathar** (b08): "אחימלך בן אביתר" (II Sam 8:17, I Chr 18:16, 24:6) against "אביתר בן אחימלך" (I Sam 22:20, 23:6). TIPNR has two Ahimelechs, so the tree keeps both links as written. **Step 7:** the two Ahimelechs are a `possible` (II Sam 20:25 has "צדוק ואביתר"); both links stay as written.
- **Jesse's sons:** eight (I Sam 17:12), seven named in I Chr 2:13–15. For block 15. **Step 7:** no key to add; Elihu (I Chr 27:18) and Eliab are a `possible`.
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
  - Ethan and Heman as sons of Mahol: "מאיתן האזרחי והימן וכלכל ודרדע בני מחול" (5:11). **Step 4:** merged with Zerah's sons; Zerah and Mahol are a conflict.
  - Mahol as Zerah's descendant, which rests on "האזרחי" alone.
  - I Chr 2:6 lists Ethan, Heman, Calcol and Dara as sons of Zerah. TIPNR uses other keys there (block 15). **Step 4:** merged with the sages of 5:11.
- **TIPNR identifications kept** (b09):
  - Shisha (I Kgs 4:3) is Seraiah, David's scribe.
  - Nathan, father of Azariah and Zabud (4:5), is Nathan the prophet.
  - Hushai, Baana's father (4:16), is David's friend.
  - Shimei son of Ela (4:18) is the Shimei of 1:8.
  - Abishalom (15:2, 10) is Absalom.
  - The Pharaoh of Hadad and Tahpenes (11:19) is Solomon's father-in-law (one key).
- **Dropped TIPNR placeholders** (b09): the unnamed wife who is the mother of Solomon's daughters Taphath and Basemath. She stays as one of his wives (I Kgs 11:3). The unnamed husband of Shimeath, Jozacar's mother, is dropped.
- **For later blocks** (b09): Shomer, Jehozabad's father (II Kgs 12:22), is "שמרית המואבית" in II Chr 24:26, a woman (block 19). Hiram the craftsman has a mother "ממטה נפתלי" (I Kgs 7:14) or "מן בנות דן" (II Chr 2:13). No parent is named, so nothing is recorded. **Step 7:** Shomer / Shimrith stays one key, a man, as in Kings.
- **Shallum son of Josiah** (b10): "שלם בן יאשיהו מלך יהודה המלך תחת יאשיהו אביו" (Jer 22:11) is the king after Josiah, Jehoahaz in II Kgs 23:30. TIPNR files the verse under Jehoiachin, marked doubtful, and keeps Shallum of I Chr 3:15 as another son of Josiah, beside Johanan, whom it takes for Jehoahaz. No link is recorded, since merging TIPNR keys is not supported. For block 15 (I Chr 3:15) and M91. **Step 4:** recorded as a `possible` with Jehoahaz.
- **Hammelech** (b10): TIPNR's one man "המלך" is the father of Jerahmeel (Jer 36:26, under Jehoiakim) and of Malchiah (38:6, under Zedekiah). "בן המלך" can be "the king's son", and the kings differ. Kept as TIPNR has it.
  - TIPNR's family column gives Hammelech's son as Malchijah of I Chr 9:12, but its own references put 38:6 under Malchiah, Pashhur's father (Jer 21:1). That link is rejected, and Malchiah <- Hammelech is added.
- **Pashhur son of Immer** (b10): "פשחור בן אמר הכהן" (Jer 20:1) is added as a `descendant`. TIPNR's Immer is the head of the sixteenth course (I Chr 24:14); block 18 may revisit.
- **Hosea's children** (b10): only Jezreel is "ותלד לו בן" (1:3). Lo-ruhamah and Lo-ammi are Gomer's (1:6, 8), and Hosea's links to them are `unstated`; the children are "ילדי זנונים" (1:2). The woman of 3:1–3 is not named, and nothing is recorded.
- **Isaiah's prophetess** (b10): "ואקרב אל הנביאה ותהר ותלד בן" (8:3). She is added as Maher-shalal-hash-baz's mother only, `anon:prophetess-of-isaiah`, since the text does not call her his wife (as with Lot's daughters). Shear-jashub's mother is not named.
- **Hanamel** (b10): "חנמאל בן שלם דדך" (Jer 32:7) and "חנמאל בן דדי" (32:8–9), but "לעיני חנמאל דדי" (32:12). The tree follows 32:7–9: Shallum is the brother of Jeremiah's father, through TIPNR's unnamed father of Hilkiah.
- **TIPNR identifications kept** (b10):
  - Gemariah son of Hilkiah (Jer 29:3) is the son of Hilkiah the high priest.
  - Elasah (29:3) and Gemariah (36:10) are sons of Shaphan the scribe.
  - Azariah son of Hoshaiah (43:2) is Jezaniah (42:1). "יזניהו בן המעכתי" (40:8, II Kgs 25:23) is a gentilic, so no conflict.
  - Hen (Zech 6:14) is Josiah son of Zephaniah (6:10).
  - Malchiah son of Hammelech (Jer 38:6) is Pashhur's father (21:1, 38:1).
- **Not identified** (b10): Zephaniah's forefather "חזקיה" (Zeph 1:1) has his own key, not King Hezekiah's; the text does not say. Zechariah son of Jeberechiah (Isa 8:2) is not the prophet.
- **For M91** (b10):
  - TIPNR keys Immanuel (Isa 7:14) as Jesus and attaches him to Judah by a link not stated. Under the Bible-only rule, the child of "העלמה" has no stated tribe. **Step 8:** off Judah, unattached.
  - The Rechabites (Jer 35) hang from Habazziniah with no link to Jonadab son of Rechab, "אבינו" (35:6). I Chr 2:55 makes them Kenites (block 15).
- **Zedekiah** (b10): "צדקיהו בן יאשיהו" (Jer 1:3, 37:1) agrees with "דדו" (II Kgs 24:17), Jehoiachin's uncle; II Chr 36:10 has "אחיו" (block 19).
- **Zerubbabel's conflict** (b10): TIPNR's Pedaiah <- Shealtiel (block 15) would make Shealtiel his grandfather, a `descendant` reading. Block 15 decides how to read I Chr 3:17–19.
- **Ruth** (b11):
  - TIPNR's Salma "אבי בית לחם" (I Chr 2:51) as Elimelech's father, marked doubtful: rejected, no verse. Elimelech now sits under his tribe.
  - TIPNR's Ephrathah as Ram's mother: rejected, no verse. TIPNR makes her Hezron's wife (I Chr 2:24), Caleb's wife and Hur's mother; for block 15.
  - Orpah is Chilion's wife only by elimination: 1:4 does not pair them, and Ruth is "אשת מחלון" (4:10).
  - Obed: "ילד בן לנעמי" (4:17), but Ruth bore him (4:13); Boaz takes her "להקים שם המת על נחלתו" (4:10). Boaz stays his father (4:21); no `levirate` link to Mahlon is recorded.
  - Salmon is "שלמה" (4:20), "שלמון" (4:21) and "שלמא" (I Chr 2:11), one key.
- **Added** (b11): Job's wife (2:9, 19:17) as a spouse only, since the mother of his children is not named; Lemuel's mother, "אשר יסרתו אמו" (Prov 31:1). Job's seven sons are not named.
- **For M91** (b11): Cush "בן ימיני" (Ps 7:1) is of Benjamin, but is attached only to the book. TIPNR's Buzites <- Ram (Job 32:2, "הבוזי ממשפחת רם") is kept as a `descendant`; Buz son of Nahor (Gen 22:21) is not linked. "קהלת בן דוד" (Eccl 1:1) has no key. **Step 8:** Cush is filed under Benjamin.
- **Esther and Daniel** (b12):
  - Esther is "בת אביחיל דד מרדכי" (2:15) and "בת דדו" (2:7): Abihail is Mordecai's uncle, but no link from Abihail to Shimei or Kish is recorded, as "דוד" does not say on which side.
  - Mordecai's forefather Kish (2:5) is TIPNR's own key, not Saul's father; the text does not say. **Step 9:** filed under Benjamin ("איש ימיני").
  - Haman "האגגי" (3:1): whether Agag of I Sam 15 is meant is not stated, and nothing is linked.
  - Belshazzar is kept as Nebuchadnezzar's son: "נבוכדנצר אבוהי" (Dan 5:2, 11, 18), "ואנת ברה" (5:22). No other father is named, so no conflict.
  - "דריוש בן אחשורוש מזרע מדי" (Dan 9:1) is kept on TIPNR's one Ahasuerus, who is also Esther's king; an identification of TIPNR's.
  - Daniel and his companions are "מבני יהודה" (Dan 1:6) but attached only to the book (M91). **Step 8:** filed under Judah.
- **Ezra–Nehemiah** (b13):
  - **Family lists:** "בני פחת מואב לבני ישוע יואב" and "בני אטר ליחזקיה" (Ezra 2:6, 16; Neh 7:11, 21) group families and name no father. TIPNR's Jeshua and Joab <- Pahath-moab and Hezekiah <- Ater are rejected, like the other "בני X" of the lists.
  - **Family names after "בן"** in Neh 3 are kept as fathers, as written, though several are also family names in Ezra 2: Pahath-moab and Harim (3:11), Hakkoz (3:4), Bani (3:17), Henadad (3:18, 24), Parosh (3:25), Immer (3:29). Only "בן השלני" (Neh 11:5) is made a `descendant`, of the Shelanite family (Num 26:20). "יהודה בן הסנואה" (11:9) and "זבדיאל בן הגדולים" (11:14) are kept as TIPNR names them.
  - **Jeshua son of Jozadak** (Ezra 10:18) is the high priest of Ezra 3:2 and 5:2. TIPNR files the verse under the course Jeshua of David's time (I Chr 24:11; also Ezra 2:36, Neh 7:39) with a Jozadak of its own; that link is rejected. The high priest's link is confirmed in block 10.
  - **The high priest Eliashib** is three TIPNR keys: Neh 3:1, 20–21 ("אלישיב הכהן הגדול"); Neh 12:10, 22–23 and 13:28; Neh 13:4, 7 (over the chambers, "קרוב לטוביה"). "יהוחנן בן אלישיב" (Ezra 10:6) is another pair of keys, perhaps the Johanan of Neh 12:23 (M91). **Step 6:** Neh 3:1's key is merged with Neh 12:10's; Neh 13:4's and Ezra 10:6's Eliashib, and Jehohanan with Johanan of Neh 12:22–23, are each a `possible`.
  - **Hanani** is Hacaliah's son by "חנני אחי" (Neh 7:2; "אחד מאחי", 1:2); אח can also mean a kinsman.
  - **Tobiah** (Neh 6:18): his wife, Shecaniah's daughter, is not said to be Jehohanan's mother, so that mother link is rejected.
  - **Neh 12:36:** "ואחיו שמעיה ועזראל ..." are Zechariah's fellow musicians. TIPNR's eight sons of Jonathan are rejected.
  - **Added:** Shecaniah <- Jahaziel, "מבני שכניה בן יחזיאל" (Ezra 8:5), read like "ומבני שלומית בן יוספיה" (8:10), which TIPNR links; Micaiah <- Zaccur (Neh 12:35). TIPNR's Zaccur there is Asaph's son of David's time (I Chr 25:2), so the line Asaph, Zaccur, Micaiah, Mattaniah, Shemaiah, Jonathan, Zechariah spans David to Nehemiah in six generations and skips where the text does not show.
  - **Neh 11:11 / I Chr 9:11** put a Meraioth between Zadok and Ahitub ("צדוק בן מריות בן אחיטוב"), against "ואחיטוב הוליד את צדוק" (I Chr 5:38, Ezra 7:2). TIPNR merges that Meraioth with Zerahiah's son and has no Meraioth <- Ahitub link (blocks 16–17). **Step 6:** the conflict on Zadok (block 17b) stands.
  - **Neh 11:13 / I Chr 9:12:** "עמשסי בן עזראל בן אחזי בן משלמות בן אמר" against "מעשי בן עדיאל בן יחזרה בן משלם בן משלמית בן אמר". TIPNR takes Ahzai for Meshullam, though the name is nearer Jahzerah; Meshullam <- Meshillemith is proved on I Chr 9:12 alone (block 17).
  - **Neh 11:10** "ידעיה בן יויריב יכין" against I Chr 9:10 "ידעיה ויהויריב ויכין", three priests; TIPNR's link is kept (block 17). **Neh 12:24** "וישוע בן קדמיאל" against "ישוע בנוי קדמיאל" (12:8, 10:10); kept as written.
  - Ezra 7:2–5's "אחיטוב בן אמריה" and "בקי בן אבישוע" run across verse ends, so Ahitub <- Amariah and Bukki <- Abishua are left to block 16 (I Chr 5:31, 37).
  - The priest who took a wife of the daughters of Barzillai the Gileadite (Ezra 2:61, Neh 7:63) is not named; nothing is added.
  - **For M91:**
    - TIPNR keeps one man under two keys: Mattaniah son of Mica of Neh 11:17 (= I Chr 9:15), and of 11:22 and 12:35. If they are one man, Mica's father is Zabdi / Zichri (Neh 11:17, I Chr 9:15) or Zaccur (Neh 12:35). Likewise Asaph@1Ch.9.15-Neh stands beside Asaph@1Ch.6.39-Psa. **Step 6:** Mattaniah, Mica and Asaph are merged; Mica's father is a conflict (Zichri drawn, Zaccur the other reading), and Zichri and Zaccur are a `possible`.
    - The heads of Ezra 8:2 ("מבני פינחס גרשם מבני איתמר דניאל מבני דויד חטוש") and Pethahiah "מבני זרח בן יהודה" (Neh 11:24) are attached only by tribe or book. **Step 6:** Gershom <- Phinehas and Daniel <- Ithamar are added as `descendant`s; Pethahiah is left to step 9. **Step 9:** Meshezabel, Pethahiah's father, is a `descendant` of Zerah.
    - TIPNR's Shilonites ("People from Shelah(?)") have no link to Shelah.
    - TIPNR makes the father of Shemaiah, keeper of the East Gate (Neh 3:29), the same man as Shecaniah son of Jehiel (Ezra 10:2); the text does not say so.
- **I Chronicles 1** (b14): Keturah is "פילגש אברהם" here (1:32) and "אשה" in Gen 25:1; Gen 25:6 speaks of Abraham's "פילגשים". The tree keeps her as a spouse, as it has no separate role for a concubine.
- **I Chronicles 2** (b15):
  - **Jesse's sons:** seven here, with David the seventh (2:13–15); eight in I Sam 16:10–11 and 17:12, with David the youngest. TIPNR's Elihu "מאחי דויד" (27:18) is left to block 18.
  - **Zerah's sons** Zimri, Ethan, Heman, Calcol and Dara (2:6): TIPNR keeps them apart from the Ezrahite sages "איתן האזרחי והימן וכלכל ודרדע בני מחול" (I Kgs 5:11; block 09's open question). If they are the same men, Zerah's "sons" are his descendants through Mahol (M91). Zimri (2:6) is the Zabdi of Josh 7:1, as TIPNR has it. **Step 4:** merged, with a conflict each (Zerah drawn, Mahol the other reading).
  - **Hezron's wives:** TIPNR's unnamed wife as mother of Jerahmeel and Caleb (2:9) is rejected: no mother is named there. Hezron's wives are Machir's daughter (2:21) and Abiah, who bore Ashhur after his death (2:24); TIPNR's Ephrathah as his wife is rejected too ("ואחר מות חצרון בכלב אפרתה", 2:24, names where he died, or Caleb's wife).
  - **Jerahmeel's first wife:** "ותהי אשה אחרת לירחמאל ושמה עטרה היא אם אונם" (2:26) implies a first wife, the mother of the sons of 2:25; TIPNR's unnamed wife is kept. The list of 2:25 ends with "אחיה", which TIPNR takes for a son.
  - **Caleb's wives:** "וכלב בן חצרון הוליד את עזובה אשה ואת יריעות ואלה בניה" (2:18): whose sons Jesher, Shobab and Ardon are, Azubah's or Jerioth's, is not clear; TIPNR's Azubah is kept. TIPNR's Jerioth as the mother of Mesha (2:42) is rejected.
  - **Jahdai** (2:47) comes between Caleb's concubines Ephah and Maacah (2:46, 48), but the text does not say who Jahdai is to Caleb. TIPNR's spouse link is rejected, Jahdai's six sons are kept, and their link to Caleb is `unstated`.
  - **Sheshan:** "ובני ששן אחלי" (2:31), but "ולא היה לששן בנים כי אם בנות" (2:34). TIPNR takes Ahlai for the daughter given to Jarha (2:35). Their marriage is kept on 2:31, 34–35, and Ahlai as Attai's mother is `unstated`.
  - **Mareshah** (2:42) is among Caleb's sons but is not said to be Mesha's son; the link is `unstated`.
  - **Founders:** Hebron (2:42), Jorkeam (2:44), Madmannah, Machbenah and Gibea (2:49) are towns of Judah (Josh 15), linked as `founder`. Maon (2:45) is "בן", so a son.
  - **Hammath** "אבי בית רכב" (2:55) is the forefather of the Rechabites, so Rechab <- Hammath is a `descendant`. Hammath is a Kenite, though TIPNR attaches him to Judah (M91). **Step 9:** kept on Judah, in whose list Chronicles puts the Kenites.
  - **The families of Kiriath-jearim** (2:53): the Mishraites, Puthites, Shumathites and Zorathites stand under Shobal "אבי קרית יערים" (2:52), but are attached only to the book (M91). **Step 9:** the Ithrites, Puthites, Shumathites, Mishraites and Zorathites are `descendant`s of Shobal.
  - **For M91:**
    - **Achsah:** "ובת כלב עכסה" (2:49) is the daughter of Caleb son of Hezron. In Josh 15:16–17 and Judg 1:12–13, Achsah is the daughter of Caleb son of Jephunneh. TIPNR keeps two Achsahs and two Calebs. If each pair is one person, this is a Bible vs Bible conflict. **Step 4:** the Achsahs are merged, with a conflict (Caleb son of Jephunneh drawn); the Calebs are a `possible` (Hur, Uri and Bezalel make Caleb son of Hezron three generations older).
    - **Salma** "אבי בית לחם", son of Hur (2:51), and Salma father of Boaz (2:11), who lived in Bethlehem, are two TIPNR keys. **Step 4:** a `possible`.
    - **Hur** grandfather of Bezalel (2:19–20) is merged with the Hur of Ex 17:10 and 24:14, as TIPNR has it.
  - Ashhur "אבי תקוע" (2:24), Mesha "אבי זיף" (2:42), Maon "אבי בית צור" (2:45), Shobal "אבי קרית יערים" (2:50), Salma "אבי בית לחם" and Hareph "אבי בית גדר" (2:51): TIPNR does not make these towns persons, so no link is needed.
- **I Chronicles 3–4** (b15b):
  - **Jeconiah's sons:** "ובני יכניה אסר שאלתיאל בנו ומלכירם ופדיה ושנאצר יקמיה הושמע ונדביה" (3:17–18). The list goes on with Jeconiah's sons, so the six of 3:18 are added as his sons. TIPNR's six links to Shealtiel are rejected, as block 10's note on Zerubbabel already read the verse. Pedaiah is then Shealtiel's brother, and Zerubbabel's conflict stays Bible vs Bible: Haggai's Shealtiel, or Shealtiel's brother Pedaiah. TIPNR reads "אסר" as "the captive", not as a son.
  - **Zedekiah** (3:16): "ובני יהויקים יכניה בנו צדקיה בנו" is kept as TIPNR has it, Jeconiah's son, after the pattern "X בנו" of 3:10–14. In II Chr 36:10 King Zedekiah is Jehoiachin's "אחיו", and in II Kgs 24:17 his "דדו". If this is the king, that is a conflict (M91). **Step 4:** a `possible` with the king.
  - **Josiah's sons** (3:15): TIPNR takes Johanan the firstborn for Jehoahaz and keeps Shallum apart. But Jehoahaz was 23 at his accession and Jehoiakim 25 three months later (II Kgs 23:31, 36), so Jehoahaz was not the firstborn; Jer 22:11 makes Shallum the king after Josiah (block 10's open question; M91). TIPNR's unnamed wife as Shallum's mother is rejected. **Step 4:** Shallum and Jehoahaz are a `possible`; Johanan stays on Jehoahaz's key.
  - **David's sons** (3:1–9): Daniel (3:1) is Chileab of II Sam 3:3 on one TIPNR key. "בת שוע בת עמיאל" (3:5) is Bathsheba daughter of Eliam (II Sam 11:3), also on one key. Elpelet and Nogah (3:6–7), absent from II Sam 5:14–16, are linked to the wives taken in Jerusalem on I Chr 14:3–6. Elpelet's father link has its best verse in I Chr 14:5 (block 18).
  - **Hananiah's line** (3:21): "בני רפיה בני ארנן בני עבדיה בני שכניה" are families named after Hananiah's sons Pelatiah and Jeshaiah. The text does not say whose sons they are, so their links to Hananiah are `unstated`. Shecaniah's line (3:22–24) follows; "ששה" (3:22) counts six where five sons are named.
  - **Hur's sons** (4:3–4): "ואלה אבי עיטם יזרעאל וישמא וידבש" are the sons of "the father of Etam". "אלה בני חור" (4:4) may take them in, so their links to Hur are `unstated`, and Penuel and Ezer are confirmed. Ezer "אבי חושה" is a `founder`, and so are Heber "אבי שוכו" (4:18), Er "אבי לכה" and Laadah "אבי מרשה" (4:21).
  - **Names linked only by their place in the list:**
    - Koz (4:8) may be a fourth son of Helah, after "צרת וצחר ואתנן"; his links to Ashhur and Helah are `unstated`, and so is Harum <- Koz.
    - Meonothai (4:14) may be a second son of Othniel; that link is `unstated`. Achsah is not said to be the mother of Hathath or Meonothai.
    - Jabez (4:9–10) and Jehallelel (4:16) begin passages of their own; TIPNR's links to Koz and Elah are rejected.
  - **Mered's wives** (4:17–18): "ותהר את מרים ואת שמי ואת ישבח" names no parent. TIPNR takes the three for the sons of Bithiah "אשר לקח מרד", so those links are `unstated`. "ואשתו היהדיה" follows Mered, so she is kept as his wife and the mother of Jered, Heber and Jekuthiel. "ואלה בני בתיה" comes right after those three, so whose sons Bithiah's are is not clear.
  - **Hodiah** (4:19): "ובני אשת הודיה אחות נחם" reads "the sons of Hodiah's wife, Naham's sister". Hodiah is a man's name elsewhere (Neh 8:7, 10:11, 14, 19). TIPNR makes Hodiah the woman, Naham's sister and Ishbah's wife. Hodiah is made male and the father of the Garmite; the marriage to Ishbah, the Garmite <- Ishbah, and TIPNR's unnamed father of Hodiah and Naham are rejected.
  - **Simeon** (4:24): "נמואל וימין יריב זרח שאול" against "ימואל וימין ואהד ויכין וצחר ושאול" (Gen 46:10, Ex 6:15) and Num 26:12–13. Nemuel, Jarib and Zerah here have no TIPNR keys of their own: Jemuel and Zerah are on the Genesis keys, and Jarib is not linked. Shallum son of Shaul (4:25) begins the line down to Shimei. Its Mibsam and Mishma are also the names of Ishmael's sons (Gen 25:13–14). **Step 4:** TIPNR's Jachin key holds 4:24, so Jarib is read as Jachin; nothing to merge.
  - **For M91:** Chelub "אחי שוחה" (4:11) and Caleb; Hattush son of Shemaiah (3:22) and Hattush "מבני דויד" (Ezra 8:2); Caleb son of Jephunneh's sons Iru, Elah and Naam (4:15) beside block 15's Calebs; and the Simeonite princes of 4:34–37, 42, attached to Simeon by tribe only. **Step 4:** Hattush merged; Chelub left apart (nothing but the name). **Step 9:** the Simeonite princes stay on Simeon.
- **I Chronicles 5–6** (b16):
  - **Reuben** (5:1–10): "בני יואל" (5:4) follows Reuben's sons (5:3), but the text does not say whose son Joel is; his line down to Beerah is confirmed. Joel father of Shema (5:8) is a second TIPNR key, likely the same man (M91). Jeiel and Zechariah "ואחיו" (5:7) would be Beerah's brothers; they stay on the tribe. **Step 5:** the two Joels are merged; Shema and Shemaiah are a `possible`.
  - **Gad** (5:11–17): the four heads of 5:12 have no father. "אלה בני אביחיל" (5:14) is read, as TIPNR reads it, as the seven of 5:13, not the four.
  - **The high priests** (5:27–41, 6:35–38) are confirmed; Bukki <- Abishua and Ahitub <- Amariah close block 13's gaps. The note "הוא אשר כהן בבית אשר בנה שלמה" (5:36) is on the second Azariah, as TIPNR has it. Meraioth between Zadok and Ahitub (Neh 11:11, I Chr 9:11) is not in 5:38; block 17b decides.
  - **Gershon** is spelled "גרשם" in 6:1, 2, 5, 28 and "גרשום" in 6:47, 56; TIPNR keys them all to Levi's son, not to Moses' son Gershom.
  - **Korah's line** (6:7–9): TIPNR takes Amminadab (6:7) for Izhar (6:23, Ex 6:18, 21). "אסיר בנו / אלקנה בנו ואביסף בנו ואסיר בנו" (6:7–8) reads as a chain, but Ex 6:24 makes Assir, Elkanah and Abiasaph Korah's sons, and 6:22 has "אסיר בן אביסף בן קרח". TIPNR keeps Exodus's three brothers and a second Assir, son of Ebiasaph; no conflict is recorded (M91). **Step 5:** the chain reading is a conflict on Elkanah (Assir the other reading) and on Ebiasaph (Elkanah); Korah drawn.
  - **The two lines from Kohath to Samuel** (6:7–13 and 6:18–23) run parallel, and TIPNR makes one person of each pair: Shaul / Joel, Uzziah / Azariah, Uriel / Zephaniah, Ahimoth / Mahath, Zophai / Zuph, Nahath / Toah / Tohu, Eliab / Eliel / Elihu. Samuel is missing in 6:12–13 ("אלקנה בנו / ובני שמואל"). Samuel is a Levite here, while Elkanah is "אפרתי" in I Sam 1:1 (M91). **Step 5:** left as TIPNR has it. "אפרתי" names where Elkanah lived ("מהר אפרים", I Sam 1:1), not a father.
  - **Samuel's sons** (6:13): "הבכר ושני ואביה"; TIPNR reads "ושני" as "and the second" and keys it to Joel (6:18, I Sam 8:2), so there is no Vashni.
  - **Heman** son of Joel son of Samuel (6:18) is confirmed early, on this block's verse (its best verse is I Chr 15:17).
  - **Asaph's line** (6:24–28) against Gershon's line (6:5–6): TIPNR makes Ethni Jeatherai, Adaiah Iddo and Ethan Joah. "בן יחת בן גרשם" (6:28) leaves out Libni (6:5). Jahath <- Libni has its best verse in 23:8 (block 18), where TIPNR makes Jahath Ladan's son Jehiel, and Shimei son of Jahath (6:27–28) the Shimei of 23:9.
  - **Ethan** (6:29) is TIPNR's Jeduthun; "איתן בן קישי" is "איתן בן קושיהו" in 15:17. His line runs to a second Mahli, son of Mushi (6:32); Merari's line of 6:14–15 runs through Mahli son of Merari and a second Libni.
- **I Chronicles 7** (b17):
  - **Benjamin's sons:** "בלע ובכר וידיעאל שלשה" (7:6), against ten in Gen 46:21, five in Num 26:38–39 and five in I Chr 8:1–2. Jediael is not named elsewhere. Bela's five sons (7:7) are not those of Num 26:40 or I Chr 8:3–5. TIPNR keeps all the lists apart, so there is no key with two parents (M91). **Step 5:** Ard (with Addar, 8:3) and Naaman are merged, Benjamin drawn and Bela the other reading, as for Gera; Jediael and Bela's sons of 7:7 are left.
  - **"ושפם וחפם בני עיר חשם בני אחר"** (7:12): TIPNR keeps Ir apart from Iri son of Bela (7:7), and Shuppim and Huppim apart from Muppim and Huppim, Benjamin's sons (Gen 46:21, Num 26:39). "חשם בני אחר" may be Dan's son Hushim (Gen 46:23), "בני אחר" standing for Dan, the tribe otherwise missing here; Naphtali's list that follows ends "בני בלהה" (7:13), and Bilhah is Dan's mother too; TIPNR reads a man Aher, and that link is confirmed as written (M91). **Step 5:** Ir / Iri, Shuppim / Muppim, Huppim / Huppim and Hushim / Dan's Hushim are each a `possible`.
  - **Maacah** (7:15–16) is Machir's wife. TIPNR makes her Ir's daughter, as Huppim's and Shuppim's sister ("ושם אחתו מעכה"); the link is `unstated`. Her mother links to Gilead and Hammolecheth are rejected: neither is said to be her child.
  - **Hammolecheth** "ואחתו" (7:18) is the sister of Gilead (7:17) or of Machir; her link to Machir is `unstated`. Her husband is TIPNR's unnamed one, kept as the father of Ishhod, Abiezer and Mahlah.
  - **Manasseh's sons and grandsons, two keys each** (M91): Asriel is Manasseh's son here (7:14), Gilead's in Num 26:31; Abiezer is Hammolecheth's son here (7:18), Gilead's (as Iezer) in Num 26:30 and Josh 17:2; Shechem is Shemida's son here (7:19), Gilead's in Num 26:31. TIPNR keeps the I Chr keys apart. **Step 5:** all three merged, Gilead drawn; the other readings are Manasseh, Hammolecheth's husband and Shemida.
  - **The Aramean concubine** (7:14) is kept as Manasseh's concubine and the mother of Asriel and Machir, as TIPNR reads "אשר ילדה פילגשו הארמיה ילדה את מכיר".
  - **Ephraim** (7:20–27): the chain from Shuthelah to a second Shuthelah, then "ועזר ואלעד" killed by the men of Gath, whom Ephraim mourned as "אביהם" (7:22). Ezer and Elead are confirmed as Ephraim's sons, on 7:21–22. Beriah is born to Ephraim's wife (7:23).
  - **Sheerah, Rephah and Resheph** (7:24–25): "ובתו", "ורפח בנו" may be Ephraim's or the newborn Beriah's; TIPNR's links to Beriah are `unstated`. The line then runs to Joshua son of Nun (7:27).
  - **Elishama son of Ammihud** (7:26) is TIPNR's Ephraimite chieftain of Num 1:10, 2:18, 7:48, 10:22. That makes him Joshua's grandfather and his contemporary as chieftain (M91). Tahan (7:25) and Bered (7:20) are kept apart from Tahan and Becher, Ephraim's sons in Num 26:35. **Step 5:** left: father and tribe agree. Tahan son of Telah stands eight generations below Ephraim, and Bered is Shuthelah's son.
  - **Asher** (7:30–40): Birzaith "הוא אבי ברזית" is a town, so a `founder`. TIPNR takes Helem "אחיו" (7:35) for Hotham, Shomer's brother (7:32), and Jether (7:38) for Ithran (7:37); both are confirmed. It also takes Ulla (7:39) for Shual (7:36), which nothing in the text supports; the three sons' links to Shual are `unstated`. **Step 5:** TIPNR's keys already hold Gen 46:17 and Num 26:44–45; nothing to merge.
- **I Chronicles 8–9** (b17b):
  - **Benjamin's sons** (8:1–2): "בלע בכרו אשבל השני ואחרח השלישי נוחה הרביעי ורפא החמישי". TIPNR takes Aharah for Ahiram (Num 26:38), and keys Nohah and Rapha to Naaman and Rosh of Gen 46:21; the father agrees, so no conflict. Bela's sons (8:3–5) bring the conflicts on Gera, Muppim and Huppim; Naaman (8:4) is the Naaman of Num 26:40, Bela's son there too.
  - **Ehud** "ואלה בני אחוד" (8:6) is TIPNR's judge Ehud son of Gera (Judg 3:15), though spelled אחוד. "וגרא הוא הגלם והוליד את עזא ואת אחיחד" (8:7): Gera may be the father of Uzza and Ahihud, so their links to Ehud are `unstated`.
  - **Shaharaim** (8:8–11) has no father; his wives Hushim, Baara and Hodesh, and their sons, are confirmed. Hushim the woman is apart from Hushim son of Dan or of Aher (Gen 46:23, I Chr 7:12).
  - **Elpaal's sons** are in two lists (8:12–13, 17–18), and Shimei and Jeroham (8:21, 27) have no fathers; they may be Shema and Jeremoth (8:13–14). TIPNR reads "ואחיו" (8:14) as a man, Ahio, among Beriah's sons; LXX reads "his brothers".
  - **Jeiel of Gibeon** (8:29, 9:35) is TIPNR's Abiel, Kish's father (I Sam 9:1), as in block 08's conflict on Kish. His wife Maacah is confirmed; "ובנו הבכור עבדון..." are his sons, and her mother links to them are `unstated`.
  - **The chain of 8:37** (and 9:43): "בנעא רפה בנו אלעשה בנו אצל בנו" runs Binea, Raphah, Eleasah, Azel. TIPNR makes all three Binea's sons; Eleasah <- Binea and Azel <- Binea are rejected and the chain added. "ובני עשק אחיו" (8:39): Eshek is Azel's brother, added as `anon:eshek-1ch-8-39` (TIPNR's key there is Eleasah's), with his sons Ulam, Jeush and Eliphelet.
  - **The returnees** (9:3–34): Uthai's line (9:4) against Neh 11:4, which has Athaiah son of Uzziah; Sallu's line (9:7) against Neh 11:7 (M91). The priests and Levites of 9:10–16 were decided on Neh 11 (block 13). Neh 11:13 has Ahzai between Azarel and Meshillemoth, I Chr 9:12 Jahzerah and Meshullam between Adiel and Meshillemith. **Step 6:** Uthai and Athaiah are a `possible`; Sallu and his father Meshullam are merged, with a conflict on Meshullam's father (Joed drawn, Hodaviah the other reading).
  - **The gatekeepers:** Shallum son of Kore (9:19) is added; his firstborn Mattithiah (9:31) is confirmed. TIPNR keeps Meshelemiah (9:21; son of Kore in 26:1) apart from Shallum, and Shelemiah (26:14) too (M91). **Step 6:** Shallum and Meshelemiah are a `possible`; TIPNR's Meshelemiah key already holds Shelemiah (26:14).
- **I Chronicles 10–29** (b18):
  - **David's heroes** (11:26–47): TIPNR takes Shage, Jonathan's father (11:34), for Shammah the Hararite (II Sam 23:33), and Nathan, Joel's brother (11:38), for Nathan of Zobah, Igal's father (II Sam 23:36). "מבחר בן הגרי" (11:38) is the Hagrite; his link to TIPNR's Hagri, the Hagrites' eponym, is `descendant`. Jashobeam "בן חכמוני" (11:11) is the Hachmonite (II Sam 23:8, TIPNR's group key); his father is Zabdiel (27:2), as TIPNR has it. **Step 7:** TIPNR keys both lists as one; Eliphal son of Ur (11:35) and Eliphelet son of Ahasbai (II Sam 23:34) are a `possible`.
  - **Obed-edom** son of Jeduthun (16:38) is TIPNR's one key for Obed-edom the Gittite (II Sam 6:10), the gatekeeper with his sons (26:4–8) and the singer (15:18, 21) (M91). Jeduthun is the singer, Ethan (block 16). **Step 6:** left as one key; a key is not split.
  - **Ladan** (23:7–9, 26:21) is TIPNR's Libni (Ex 6:17), in "לעדן ושמעי" against "לבני ושמעי"; TIPNR marks it doubtful. Jehiel son of Ladan (23:8) is also TIPNR's Jahath son of Libni (6:5, 28); Shimei son of Jahath (6:27–28) is the Shimei of 23:9, whose sons are "ראשי האבות ללעדן". The two keys stay merged (M91), so Zimmah's second reading (block 16) shows Jehiel. **Step 6:** left as TIPNR has it.
  - **Shimei son of Gershon** (23:10) has a son Jahath, apart from Jahath son of Libni.
  - **Merari's sons** (24:26–27): "בני יעזיהו בנו" reads as "the sons of Jaaziah his son", but "ליעזיהו בנו ושהם וזכור ועברי" lists Beno as a fourth son; TIPNR's Beno is confirmed.
  - **Hebron's sons** "ובני יריהו אמריהו השני" (24:23) are those of 23:19, with Jeriah the first of them; the cue is dismissed.
  - **Jeduthun's six sons** (25:3) name five; Shimei (25:17) would be the sixth.
  - **Meshelemiah son of Kore** (26:1) is added; "מן בני אסף" is Ebiasaph, as in 9:19.
  - **Elihu "מאחי דויד"** (27:18) is confirmed as Jesse's son, the eighth of I Sam 16:10, 17:12, as against the seven of I Chr 2:13–15; he may be Eliab (I Sam 16:6) (M91). **Step 7:** Elihu and Eliab are a `possible`.
  - **Jaasiel son of Abner** (27:21) is TIPNR's Abner son of Ner. Jehoiada son of Benaiah (27:34) is kept apart from Jehoiada, Benaiah's father.
- **II Chronicles** (b19):
  - **Rehoboam's wives** (11:18–21): "את מחלת בת ירימות בן דויד אביהיל בת אליאב בן ישי" names one wife, "ותלד לו" (11:19) and "ואחריה" (11:20), so Abihail is Mahalath's mother and Jerimoth's wife, as TIPNR also has her. Her second TIPNR link, as Rehoboam's wife, is rejected. Jerimoth son of David is in no list of David's sons; his mother link to the Jerusalem wives is rejected (I Chr 3:9 has the concubines' sons, unnamed).
  - **Maaseiah "בן המלך"** (28:7) is TIPNR's son of Ahaz, who was twenty when he began to reign (28:1); like "יואש בן המלך" (I Kgs 22:26, block 09) it may be a title, so the link is `unstated`. His mother link to Abi, Hezekiah's mother, is rejected.
  - **Zechariah son of Jehoiada** (24:20): Jehosheba is Jehoiada's wife (22:11) but not said to be Zechariah's mother; the link is `unstated`.
  - **The singers in Hezekiah's day** (29:13–14): "ומן בני הימן יחיאל ושמעי ומן בני ידותון שמעיה ועזיאל" are descendants, as "ומן בני אליצפן ... ומן בני אסף" in 29:13; the four links are `descendant`.
  - **The Levites of 29:12**: "מחת בן עמשי ויואל בן עזריהו" repeats the pairs of Heman's line (I Chr 6:20–21), and "יואח בן זמה" those of Gershon's (6:6); TIPNR keeps them apart, as men of Hezekiah's day. "ועדן בן יואח" has its own Joah in TIPNR (M91). **Step 6:** the two Joahs of 29:12 are a `possible`; the others are left, as Hezekiah's men.
  - **Huram-abi** (2:13) is the son of "אשה מן בנות דן"; I Kgs 7:14 has "בן אשה אלמנה הוא ממטה נפתלי". Neither parent is named.
  - **Jehozabad son of Shimrith the Moabitess** (24:26) is the son of Shomer in II Kgs 12:22, where block 09 confirmed the father; Chronicles makes the name a woman's (M91). **Step 7:** left: one key, a man.
- **Moses' Cushite wife** (Num 12:1) is added as her own person, `anon:cushite-wife-of-moses`. The text does not say whether she is Zipporah, a Midianite.
- **Name variants, Gen 46 against Num 26** (the parent agrees, so no conflict): Jemuel / Nemuel, Zohar / Zerah, Ezbon / Ozni, Iob / Jashub, Hushim / Shuham, Ehi / Ahiram, Muppim / Shephupham, Huppim / Hupham. Num 26 has no Ohad, Ishvah, Gera or Rosh. Also Deuel / Reuel (Num 1:14 / 2:14) and Abiezer / Iezer (Josh 17:2 / Num 26:30). TIPNR keeps each pair as one key; the Genesis form is the one shown.
- **Two Zurs of Midian**: TIPNR has two keys, Cozbi's father "ראש אמות בית אב במדין" (Num 25:15) and one of the five kings (31:8). They are perhaps one man.
- **Esau's wives** follow TIPNR's identifications: Basemath daughter of Elon (Gen 26:34) is Adah (36:2), Mahalath (28:9) is Basemath daughter of Ishmael (36:3). The fathers agree, the names differ; no conflict recorded, only noted in the review file.
- **One person in one list, two in another** (no conflict recordable): Gen 46:21 gives Naaman and Ard as Benjamin's sons, Num 26:40 as Bela's sons, and TIPNR has two people each (`Naaman@Gen.46.21-1Ch` / `Naaman@Num.26.40-1Ch`). A conflict needs one key with two parents; merging TIPNR keys is not supported. Revisit in M91, with Benjamin's sons in Num 26:38–40 and 1 Chr 7:6, 8:1–5. **Step 5:** merged, with a conflict each (Benjamin drawn, Bela the other reading).
- **Adoption** (settled in M91 step 2): Jacob takes Ephraim and Manasseh as his own (Gen 48:5), an `adopted` cross-link; Joseph stays the drawn father.
- The skeleton is ~650 KB of JSON (gzipped in transit), fetched once per visit. Fine now; if M91 adds fields, consider a compact array form.
- `bsim places` drops TIPNR's references marked by their occurrence (`Exo.7.10a`, 15% of all) and doesn't map English numbering (`data/kjv.py`). Fixing both might improve the gazetteer, but it is outside this series: raise it with the user, don't just do it.
- 1,055 people are "unattached", mostly people with no family in the text. Most become reachable through search; the reviews may attach some. **Step 9:** 908 after the M91 sweeps.

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
- 2026-10-21, M90 block 10 (Isaiah–Malachi): `curation/genealogy/10-b10-latter-prophets.yaml`, reviewed.
  - **Counts:** 68 links checked (62 confirmed, 2 fixed, 1 rejected, 3 added), 2 conflicts, 171 cue verses dismissed. Most cues are "בת ציון" and the other cities, "בני ישראל", "בני עמון", "גיא בן הנם", and Jeremiah's "X בן Y" for links proved in block 09 (Gedaliah, Ishmael, Johanan, Jehoiakim, Jeconiah). No cue verse is left unhandled. The block fits one session; no split was needed.
  - **Confirmed:**
    - The prophets' fathers: Jeremiah, Ezekiel, Hosea, Joel; Zephaniah's line to "חזקיה" (Zeph 1:1); Zechariah's to Iddo; Joshua son of Jehozadak.
    - Isaiah's sons: Shear-jashub (7:3), Maher-shalal-hash-baz (8:3, 18). Hosea and Gomer, Jezreel (1:3–4). Ezekiel's wife (24:16, 18).
    - Jeremiah's people: Hanamel son of Shallum and Shallum as the brother of Jeremiah's father (32:7–9); Baruch and Seraiah sons of Neriah son of Mahseiah; the house of Shaphan; the princes of Jer 36–38; Jonathan son of Kareah; the Rechabites of 35:3; Zedekiah son of Josiah (1:3, 37:1).
  - **Fixed:** Lo-ruhamah and Lo-ammi <- Hosea are `unstated`.
  - **Rejected:** Malchijah of I Chr 9:12 <- Hammelech (no verse).
  - **Added:** Isaiah's prophetess as Maher-shalal-hash-baz's mother; Pashhur <- Immer (`descendant`); Malchiah <- Hammelech (Jer 38:6).
- 2026-10-21, M90 block 11 (Psalms, Proverbs, Job, Song, Ruth, Lamentations, Ecclesiastes): `curation/genealogy/11-b11-ps-to-eccl.yaml`, reviewed.
  - **Counts:** 25 links checked (21 confirmed, 2 rejected, 2 added), no conflicts, 27 cue verses dismissed ("בת ציון", "בנות ירושלם", "בני אלים", "בני ישראל"). No cue verse is left unhandled.
  - **Confirmed:** Ruth's family: Elimelech and Naomi, Mahlon and Chilion, Ruth and Orpah, Boaz and Ruth, Obed <- Ruth (4:13, 17); the line from Perez to David (4:18–22), with Ram <- Hezron picked up from block 15's sheet (4:19, I Chr 2:9). Job's daughters (42:13–15); Elihu <- Barachel; Agur <- Jakeh.
  - **Rejected:** Elimelech <- Salma, Ram <- Ephrathah (TIPNR, no verse).
  - **Added:** Job's wife, Lemuel's mother.
  - The two Rahab links on the sheet stay rejected, as block 07 decided.
- 2026-10-21, M90 block 12 (Esther, Daniel): `curation/genealogy/12-b12-esth-dan.yaml`, reviewed.
  - **Counts:** 35 links checked (19 confirmed, 14 rejected, 2 added), no conflicts, 7 cue verses dismissed. No cue verse is left unhandled.
  - **Confirmed:** Mordecai's line to Kish (Est 2:5); Esther <- Abihail; Ahasuerus and Vashti (1:9, 19); Haman <- Hammedatha, Zeresh his wife, his ten sons (9:7–10); Belshazzar <- Nebuchadnezzar (Dan 5); Darius <- Ahasuerus (Dan 9:1).
  - **Rejected** (TIPNR, no verse): Zeresh as the mother of Haman's ten sons (marked doubtful); Vashti as the mother of Darius the Mede and of Artaxerxes; Ahasuerus <- Darius and Artaxerxes <- Ahasuerus (Ezra 4:5–7 is a succession of kings).
  - **Added:** Esther as Ahasuerus's wife (2:16–17), and Esther <- Mordecai, `adopted` ("לקחה מרדכי לו לבת", 2:7, 15); Abihail stays her drawn father.
- 2026-10-21, M90 block 13 (Ezra–Nehemiah): `curation/genealogy/13-b13-ezra-nehemiah.yaml`, reviewed. The sheet had 148 links beside 483 book attachments (M91), so the block was not split.
  - **Counts:** 142 links checked (126 confirmed, 1 fixed, 13 rejected, 2 added), 5 conflicts, 83 cue verses dismissed; the other 3 cue verses are proofs of a conflict or an added link. No cue verse is left unhandled.
  - **Confirmed:** Ezra's line to Aaron (Ezra 7:1–5); the leaders and builders "X בן Y" of Ezra 8, 10 and Neh 3, 6, 10–13; Nehemiah and Hanani <- Hacaliah; the high priests Jeshua, Joiakim, Eliashib, Joiada, Jaddua (Neh 12:10–11, 26); Tobiah's marriage to Shecaniah's daughter and Jehohanan's to Meshullam's (Neh 6:18); Joiada's son, Sanballat's son-in-law (13:28); the lines of Neh 11:4–17, 22 and 12:35.
  - **Fixed:** Zechariah <- the Shelanites (Neh 11:5), as a `descendant`.
  - **Rejected:** Jeshua and Joab <- Pahath-moab, Hezekiah <- Ater (family lists); TIPNR's Jeshua <- Jozadak of Ezra 10:18 (the high priest, filed under the course of I Chr 24:11); Shecaniah's daughter as Jehohanan's mother; the eight "brothers" of Neh 12:36 as Jonathan's sons.
  - **Conflicts:** Ezra <- Seraiah, Azariah <- Meraioth (Ezra 7:3), Mahli <- Levi (Ezra 8:18), Johanan <- Eliashib (Neh 12:23), Jeroham <- Pashhur (I Chr 9:12), all `descendant`.
  - **Added:** Shecaniah <- Jahaziel (Ezra 8:5); Micaiah <- Zaccur (Neh 12:35).
- 2026-10-21, M90 block 14 (I Chr 1): `curation/genealogy/14-b14-1chr-1.yaml`, reviewed, with no links of its own.
  - **Counts:** no new links and no new conflicts; 6 cue verses are dismissed (1:18, 28, 31, 32, 34, 38), all proved in Genesis.
  - **Why so small:** I Chr 1 repeats Genesis 5, 10, 11:10–26, 25 and 36. Its 93 links with a proof here were all proved first in Genesis and are decided in blocks 01–03 (92 confirmed, Dodanim fixed). The 5 lines of the sheet are readings of the conflicts on Uz, Hul, Gether, Mash (1:17) and Timna (1:36). No person's TIPNR key starts in I Chr 1.
  - **Spellings:** the names spelled differently from Genesis (דיפת / ריפת, רודנים / דדנים, משך / מש, עלין / עלון, שפי / שפו, חמרן / חמדן, הדד / הדר, פעי / פעו) are on the Genesis keys, so none adds a link. Hadad / Hadar (1:50) was given "הדר" in block 03.
- 2026-10-22, M90 block 15 (I Chr 2): `curation/genealogy/15-b15-1chr-2.yaml`, reviewed.
  - **The split:** block 15 (I Chr 2–4, 301 links) was split at I Chr 3:1 into `b15-1chr-2` and `b15b-1chr-3-4`, in `configs/default.yaml`, the table above and `docs/TASKS.md`.
  - **Counts:** 134 links checked (112 confirmed, 15 fixed, 7 rejected), no conflicts. 7 cue verses are dismissed: 2:1, 3, 4, 7 and 20 are proved in blocks 03, 04, 05 and 07, and 2:23 and 2:54 name no person. 2:34 is a proof of the Ahlai links. 6 links of the sheet were decided earlier: Zeruiah and Abigail <- Jesse, Jesse's three sons not by Nahash (block 08), and Jair <- Segub (block 06).
  - **Confirmed:**
    - Zerah's sons (2:6); Hezron's sons Jerahmeel and Caleb (2:9; Caleb on 2:9 and 2:18, since the automatic proof 2:24, "בכלב אפרתה", is a place);
    - Jesse's sons Nethanel, Raddai and Ozem (2:13–15);
    - Caleb's wives, concubines and sons (2:18–19, 46, 48–49), Hur and his sons Shobal, Salma and Hareph (2:50–51), and Achsah (2:49);
    - Segub, son of Hezron and Machir's daughter (2:21);
    - Abiah, Hezron's wife, and Ashhur (2:24);
    - Jerahmeel's line (2:25–33) and its continuation through Jarha (2:35–41);
    - Hebron's sons, Shema's and Rekem's lines, and Maon (2:43–45);
    - the Menuhoth (half of the Manahathites) under Shobal (2:52).
  - **Fixed:**
    - Appaim is Nadab's son (2:30), not his descendant.
    - `founder`: Hebron, Jorkeam, Madmannah, Machbenah and Gibea.
    - `unstated`:
      - Mareshah <- Mesha;
      - Attai <- Ahlai;
      - Jahdai's six sons <- Caleb.
    - Rechab <- Hammath is a `descendant`.
  - **Rejected:** TIPNR's unnamed wife of Hezron (2:9: her two mother links and the marriage); Ephrathah as Hezron's wife; Maacah as the mother of Machir's daughter; Jerioth as Mesha's mother; Jahdai as Caleb's wife.
- 2026-10-22, the build: a link is now decided once. Listing it under `links` again, in the same file or a later one, or after an earlier file's conflict reading, stops the build (`apply_curation`, with a test). The existing review files pass.
- 2026-10-22, M90 block 15b (I Chr 3–4): `curation/genealogy/15b-b15b-1chr-3-4.yaml`, reviewed. Its sheet had 162 links besides 21 book attachments, so it was not split again.
  - **Counts:** 166 links checked (121 confirmed, 23 fixed, 16 rejected, 6 added), no conflicts, 5 cue verses dismissed (3:4, 11, 14 and 4:1 are proved earlier; 4:27 names no one). Zerubbabel <- Pedaiah was decided in block 10.
  - **Confirmed:**
    - Bathsheba's four sons (3:5);
    - Nogah, son of David and of the wives taken in Jerusalem, and Elpelet's mother (3:6–7, 14:3–6);
    - Shallum son of Josiah (3:15), and Zedekiah and Shealtiel sons of Jeconiah (3:16–17);
    - Zerubbabel's line (3:19–24);
    - Haroeh <- Shobal and his line (2:52, 4:2), Hur's sons Penuel and Ezer (4:4);
    - Ashhur's wives and sons (4:5–7), Koz's sons, Chelub's line (4:11–12), Kenaz's and Othniel's sons (4:13–14), Caleb son of Jephunneh's sons (4:15), Jehallelel's (4:16), Ezrah's (4:17);
    - Mered's wives Bithiah, daughter of Pharaoh, and the Judahite, and the Judahite's sons (4:17–18);
    - the sons of Shimon and Ishi (4:20), Shelah's line (4:21–22), Simeon's line from Shaul to Shimei (4:25–26), and the Simeonite chains of 4:34–37, 42.
  - **Fixed:**
    - `founder`: Hushah, Soco, Lecah and Mareshah.
    - `unstated`:
      - Hananiah's four families (3:21);
      - Hur's sons of 4:3;
      - Koz and Harum;
      - Meonothai;
      - Mered and Bithiah's three.
    - The Garmite <- Hodiah, as father; Hodiah is made male.
  - **Rejected:**
    - TIPNR's six sons of Shealtiel (3:18), and its unnamed wife of Josiah;
    - Jabez <- Koz and Jehallelel <- Elah;
    - Achsah as the mother of Hathath and Meonothai;
    - the marriage of Ishbah and Hodiah, the Garmite <- Ishbah, and the unnamed father of Hodiah and Naham.
  - **Added:** Malchiram, Pedaiah, Shenazzar, Jekamiah, Hoshama and Nedabiah <- Jeconiah (3:17–18).
- 2026-10-22, M90 block 16 (I Chr 5–6): `curation/genealogy/16-b16-1chr-5-6.yaml`, reviewed. The sheet had 72 links besides 17 tribe attachments, so the block was not split.
  - **Counts:** 71 links checked (all confirmed: 68 of the sheet, Heman <- Joel early, and the two TIPNR links that are the first readings of the conflicts), 2 conflicts, which add 2 readings, and 22 cue verses dismissed: Levi's and Amram's sons proved earlier, Samuel's sons (6:13), "בן יחת בן גרשם" (6:28), and the tribes and towns of the Levites' cities. 2 links of the sheet were decided earlier (Azariah <- Ahimaaz, Azariah <- Johanan).
  - **Confirmed:**
    - Reuben: Joel's line down to Beerah (5:4–6), and Bela's (5:8);
    - Gad: the seven sons of Abihail (5:13–14), Abihail's line up to Buz (5:14), Ahi son of Abdiel (5:15);
    - the high priests: Bukki <- Abishua, Amariah <- Meraioth and Ahitub <- Amariah (5:31–33, 6:37), Johanan <- Azariah (5:35), the second Amariah's Ahitub (5:37), Jehozadak <- Seraiah (5:40);
    - Gershon's line through Libni to Jeatherai (6:5–6) and Asaph's line (6:24–28);
    - Korah's line to Samuel (6:7–12, 6:20–22);
    - Merari's line through Mahli and Libni (6:14–15), and Ethan's line (6:29–32);
    - Heman <- Joel (6:18), early.
  - **Own proofs** for the lists whose "בן" or "בנו" runs into the next verse: 5:4–6, 5:13–14, 6:5–6, 6:14–15, 6:24–26, 6:29–32.
  - **Conflicts:** Zimmah (`descendant`, 6:5 against 6:27–28) and Ahimoth (6:10 against 6:20).
  - Checked in the API: Abihail's seven sons, Zimmah's and Ahimoth's conflicts with both readings, Heman's father.
- 2026-10-22, M90 block 17 (I Chr 7): `curation/genealogy/17-b17-1chr-7.yaml`, reviewed.
  - **The split:** block 17 (I Chr 7–9, about 250 links) was split at I Chr 8:1 into `b17-1chr-7` and `b17b-1chr-8-9`, in `configs/default.yaml`, the table above and `docs/TASKS.md`.
  - **Counts:** 114 links checked (103 confirmed, 9 fixed, 2 rejected), no conflicts, 2 cue verses dismissed (7:28–29, towns).
  - **Confirmed:**
    - Issachar: Tola's sons and Uzzi's line (7:2–3);
    - Benjamin: Jediael (7:6), Bela's and Becher's sons (7:7–8), Jediael's line through Bilhan (7:10), and 7:12 as written;
    - Manasseh: the Aramean concubine with Asriel and Machir (7:14), Machir's wife Maacah and her sons Peresh and Sheresh, Sheresh's sons, Bedan (7:15–17), Hammolecheth's children (7:18), Shemida's sons (7:19);
    - Ephraim: Shuthelah's chain to the second Shuthelah (7:20–21), Ezer, Elead and Beriah as Ephraim's sons (7:21–23), and the line from Telah to Nun (7:25–27);
    - Asher: Heber's children, Japhlet's, Shomer's, Helem's, Zophah's and Jether's sons (7:32–38).
  - **Own proofs** for links whose "בנו" runs on into the next verse or whose father is named in the next verse: 7:20–21, 7:21–23, 7:25–27, 7:36–37.
  - **Fixed:**
    - `unstated`: Maacah <- Ir; Hammolecheth <- Machir; Sheerah, Rephah and Resheph <- Beriah; Ulla's three sons <- Shual.
    - `founder`: Birzaith <- Malchiel.
  - **Rejected:** Maacah as the mother of Gilead and of Hammolecheth.
- 2026-10-22, M90 block 17b (I Chr 8–9): `curation/genealogy/17b-b17b-1chr-8-9.yaml`, reviewed.
  - **Counts:** 147 links checked (123 confirmed, 12 fixed, 5 rejected, 7 added), 4 conflicts, 5 cue verses dismissed (8:40, 9:3, 9:6, 9:20, 9:40); 8:6 is a proof of Ehud's sons. 3 links of the sheet were decided earlier (Kish <- Ner, Jeroham <- Pashhur, Meshullam <- Meshillemith).
  - **Confirmed:**
    - Bela's sons (8:3–4), Ehud's (8:6–7), Shaharaim's wives and sons (8:8–11);
    - Elpaal's, Beriah's, Shimei's, Shashak's and Jeroham's sons (8:12–27);
    - Jeiel of Gibeon's wife and sons, Shimeah <- Mikloth (8:29–32, 9:35–38);
    - Saul's descendants through Micah to Azel's six sons (8:35–38, 9:41–44);
    - the returnees' lines (9:4, 7–8, 12, 16), Kore <- Ebiasaph (9:19), Zechariah <- Meshelemiah (9:21), Mattithiah <- Shallum (9:31).
  - **Own proofs** for the many lists that end "בני X" a verse or more later (8:3–4, 6–7, 8–11, 12–27, 29–31, 9:35–37).
  - **Fixed** (`unstated`): Uzza and Ahihud <- Ehud; Maacah of Gibeon as the mother of Jeiel's eleven sons.
  - **Rejected:** Eleasah and Azel <- Binea; Ulam, Jeush and Eliphelet <- Eleasah.
  - **Added:** the chain Eleasah <- Raphah and Azel <- Eleasah (8:37); Eshek (a new person), Azel's brother, and his three sons (8:39); Shallum <- Kore (9:19).
  - **Conflicts:** Gera, Muppim and Huppim (Gen 46:21 against I Chr 8:3–5), and Zadok son of Ahitub or of Meraioth (I Chr 5:38 against 9:11, Neh 11:11).
- 2026-10-22, M90 block 18 (I Chr 10–29): `curation/genealogy/18-b18-1chr-10-29.yaml`, reviewed. The sheet had 278 lines, 145 of them tribe attachments, so the block was not split.
  - **Counts:** 130 links checked (126 confirmed, 1 fixed, 1 added, and the 2 TIPNR links that are the first readings of the conflicts), 2 conflicts, 75 cue verses dismissed (links proved earlier, the clans' chiefs of 15:5–10, unnamed sons, the nations); 14:4, 26:6 and 26:22 are proofs. 4 links of the sheet were decided earlier.
  - **Confirmed:**
    - David's heroes (11:34–47, 12:3, 8), with Nathan and Joel "אחי" through an unnamed father (11:38);
    - Elpelet son of David (14:3–5), Obed-edom son of Jeduthun (16:38);
    - Levi's families (23:8–23): Ladan's, Shimei's, Eliezer's, Izhar's, Hebron's, Uzziel's, Mahli's and Mushi's sons;
    - the courses (24): Shemaiah son of Nethanel, Jehdeiah, Isshiah, Jahath, Shamir, Zechariah, Jaaziah's sons, Jerahmeel son of Kish;
    - the singers' sons (25:2–4): Asaph's, Jeduthun's and Heman's;
    - the gatekeepers (26): Meshelemiah's, Obed-edom's, Shemaiah's and Hosah's sons; Shebuel son of Gershom (26:24), the chain of 26:25;
    - the officers (27): Jashobeam son of Zabdiel, Ammizabad son of Benaiah, Zebadiah son of Asahel, the tribal chiefs, Elihu son of Jesse (27:18), and the king's stewards and counsellors.
  - **Own proofs** for the lists that run on into the next verse (26:2–3, 4–5, 4 and 6, 10–11, 24:26–27), for Shimei son of Jahath (6:27–28) and for Elihu (27:18, I Sam 17:12).
  - **Fixed** (`descendant`): Mibhar <- Hagri (11:38).
  - **Added:** Meshelemiah <- Kore (26:1).
  - **Conflicts:** Zetham and Joel, sons of Ladan (23:8) or of Jehieli (26:22).
- 2026-10-22, M90 block 19 (II Chronicles): `curation/genealogy/19-b19-2chr.yaml`, reviewed. **M90 is done**: 21 blocks, 1,969 links checked, 33 conflicts.
  - **Counts:** 63 links checked (54 confirmed, 6 fixed, 3 rejected), no conflicts, 92 cue verses dismissed (the kings' successions and other links proved in Kings, the people, the nations, the clans' Levites of 29:13 and 34:12); 11:22 and 28:7 are proofs. 2 links of the sheet were decided earlier (Maacah <- Uriel, Uriel's wife).
  - **Confirmed:**
    - Rehoboam's wives Mahalath and Maacah and their sons (11:18–21), Mahalath's parents Jerimoth and Abihail, Abihail daughter of Eliab;
    - the prophets and officers: Azariah son of Oded (15:1), Amasiah (17:16), Zebadiah son of Ishmael (19:11), Jahaziel's line to Mattaniah (20:14), Eliezer son of Dodavahu (20:37);
    - Jehoshaphat's six sons (21:2), Jehosheba wife of Jehoiada (22:11), the captains of 23:1, Zechariah son of Jehoiada (24:20);
    - the chiefs of Ephraim (28:12), the Levites of 29:12, Conaniah and his brother Shimei through an unnamed father (31:12), Kore son of Imnah (31:14), Joah son of Joahaz (34:8).
  - **Own proofs** for Rehoboam's sons (11:18–19) and his marriage to Maacah (11:20–22).
  - **Fixed:** `unstated`: Zechariah <- Jehosheba, Maaseiah <- Ahaz; `descendant`: Jehuel and Shimei <- Heman, Shemaiah and Uzziel <- Jeduthun (29:14).
  - **Rejected:** Abihail as Rehoboam's wife; Jerimoth <- the Jerusalem wives; Maaseiah <- Abi.
- 2026-10-22, M91 step 1: the plan.
  - **Asked the user:** one person under two keys becomes a `same:` list, `merged` (one node, with a conflict where the parents differ) or `possible` (a cross-link in the panel). Adoption is an `adopted` cross-link from Jacob, and the tree keeps Joseph.
  - **Planned:** M91 split into 10 steps (table above). The "(M91)" items of **Open questions** fall under steps 3–9.
  - The build has no `same:` yet; step 2 adds it.
- 2026-10-22, M91 step 2: identities and adoption built.
  - **The loader** (`apply_curation`): the files' people come first, then `same:`. `merged` folds keys into the first (`merge_person`: verses, names, places founded, links; two links that become one fold, a link between the two is dropped), and every later key resolves through the merge. A link decided under both pairs of keys must agree. A merged person with two fathers or mothers needs a conflict. `possible` keeps both. `genealogy.cross_blocks` lists the cross-book steps' blocks, which have no verse range. A merged key in `genealogy.root` or `genealogy.tribes` names the merged person.
  - **Adoption:** `choose_primary` ranks an `adopted` father after every other, and it adds no "married in" partner. Added Jacob -> Ephraim and Manasseh (Gen 48:5) to block 04's file, as `added`, kind `adopted`: a cross-link, and Joseph stays the drawn father.
  - **Output:** `identities.parquet`, with each identity's verses and the names' tokens, goes to the DB table `genealogy_identities` and `meta.identities`. The review sheet lists the identities of the people first named in its block.
  - **API and viewer:** `PersonDetail.identities` (merged: how many entries; possible: the other person), with the proofs. The panel's section is "One person or two?" ("Read as one person, though STEPBible lists 2 entries"; "Perhaps the same person as …"), and an adopted link is tagged "by adoption". The panel's siblings leave out an adoptive father's children. English and Hebrew.
  - **Tests:** pytest covers a merge (verses, places, the marriages folded, a link named by both keys, adoption not drawn, identities, the sheet), the errors (two fathers without a conflict, a possible on merged keys, too few keys, no proof, a link decided two ways) and the API on the fixture. vitest covers the panel's section and the adoption tag in both languages. DESIGN §16.63 is updated.
- 2026-10-22, M91 step 3: Edom, Gen 36 against I Chr 1 (`x03-edom.yaml`, reviewed).
  - **One person, two keys:** none to merge. TIPNR keys all 77 people of Gen 36 and I Chr 1:35–54 so that each person named in both lists is one key, with the variants (Zepho / Zephi, Alvan / Alian, Shepho / Shephi, Hemam / Homam, Hemdan / Hamran, Akan / Jaakan, Hadar / Hadad, Alvah / Aliah). Amalek of I Chr 1:36 is on no key. One `possible`: Korah of 36:16 with Korah son of Oholibamah.
  - **Off Esau:** the loader now takes `tribe` in a `people:` correction; `tribe: ""` hangs a person on no eponym (a test covers it). Seir, Beor, Zerah of Bozrah, Husham, Bedad, Samlah, Shaul, Achbor, Hadar, Mezahab, the husband of Matred, Elon and Beeri are taken off "Edom": 12 more people under "unattached" (Hadar stays beside Mehetabel). The chiefs of 36:40–43 and Hadad the Edomite stay under Esau.
  - The variants of blocks 03 and 14 needed nothing; the conflicts on Timna and Anah (block 03) stand.
- 2026-10-22, M91 step 4: Judah and Simeon against I Chr 2–4 (`x04-judah-simeon.yaml`, reviewed).
  - **Probes:** every person of I Chr 2:1–4:43 against the keys of the same name in Gen 38, 46, Ex 6, Num 13, 26, 34, Josh 7, 14–15, Judg 1, Ruth 4, II Kgs 23–25, Jer 22 and Ezra 8. Most pairs share only a name (Korah son of Hebron and Korah the Levite, Nepheg, Heber); the rest are below.
  - **Merged (6):**
    - Achsah, with a conflict on her father: Caleb son of Jephunneh (drawn) or Caleb son of Hezron (2:49).
    - Hattush (3:22; Ezra 8:2–3, "מבני דויד חטוש מבני שכניה").
    - Zerah's sons Ethan, Heman, Calcol and Dara with the sages of I Kgs 5:11 (Darda), each with a conflict: Zerah drawn, Mahol the other reading.
  - **Possible (4):** the two Calebs; Salma son of Hur and Salma son of Nahshon; Shallum son of Josiah and Jehoahaz (Jer 22:11); Zedekiah of 3:16 and the king (II Chr 36:10).
  - **Left:** Simeon's sons need nothing (TIPNR's Genesis keys hold 4:24). Chelub "אחי שוחה" (4:11) is not tied to a Caleb. Jephunneh is filed under Judah ("למטה יהודה", Num 13:6), so Caleb son of Jephunneh, Kenaz and Othniel leave "Unattached".
  - 6 fewer people (2,849), 38 conflicts, identities: 6 merged, 5 possible.
- 2026-10-22, M91 step 5: Reuben, Levi, Benjamin, Manasseh, Ephraim and Asher against I Chr 5–8 (`x05-1chr-5-8.yaml`, reviewed).
  - **Probes:** every person of I Chr 5:1–8:40 against the keys of the same name in Gen 46, Ex 6, Num 1–4, 26, Josh 17 and I Sam 1, 8. Most pairs share only a name (Becher of Ephraim and Bocheru, Zichri of Izhar and Benjamin's Zichris, Mahlah of Hammolecheth and of Zelophehad).
  - **Merged (6):**
    - Joel of Reuben (5:4, 8).
    - Ard (with Addar, 8:3) and Naaman, Benjamin's sons (Gen 46:21) and Bela's (Num 26:40, I Chr 8:3–4), each with a conflict: Benjamin drawn, Bela the other reading, as block 17b has Gera, Muppim and Huppim.
    - Manasseh's Asriel, Abiezer and Shechem (Num 26:30–31, Josh 17:2; I Chr 7:14, 18–19), each with a conflict: Gilead drawn; Manasseh, Hammolecheth's husband and Shemida the other readings.
  - **Possible (5):** Shema and Shemaiah, Joel's sons (5:4, 8); Ir and Iri (7:7, 12); Shuppim and Huppim, Ir's sons (7:12), and Muppim and Huppim (Gen 46:21); Hushim "בני אחר" (7:12) and Dan's Hushim (Gen 46:23).
  - **Conflicts:** Korah's line read as a chain (6:7–8) gives Elkanah the father Assir and Ebiasaph the father Elkanah, against Ex 6:24 and 6:22; Korah drawn.
  - **Left:** the two lines from Kohath to Samuel (one key per pair already; Elkanah "אפרתי" is where he lived); Jediael and Bela's sons of 7:7; Elishama son of Ammihud (one key), Tahan son of Telah and Bered (Ephraim); Asher, whose keys already hold Gen 46:17 and Num 26:44–45.
  - **Mother headers:** a mother who is the wife of the child's other father, a reading not drawn, heads no group under the drawn one (`genealogy_mothers`, a test, DESIGN §16.63). Without it, Asriel and Abiezer would have stood under Gilead beneath the Aramean concubine and Hammolecheth.
  - 7 fewer people (2,842), 45 conflicts, identities: 12 merged, 10 possible.
- 2026-10-22, M91 step 6: the priests, the Levites, the gatekeepers and the singers (`x06-priests-levites.yaml`, reviewed).
  - **Probes:** every person of I Chr 5:27–6:66, 9:1–34 and 23–26 against the keys of the same name in Ezra 2, 7–8, 10, Neh 3, 7, 10–13, Samuel and Kings (exact names; the loose match is swamped by the lists of Ezra 10 and Neh 10–12). The high priests, the lines of 6:18–32 and most returnees of I Chr 9 / Neh 11 are one key each already.
  - **Merged (6):**
    - Eliashib "הכהן הגדול" (Neh 3:1) with Eliashib son of Joiakim (Neh 12:10, 13:28).
    - Sallu son of Meshullam and his father (Neh 11:7, I Chr 9:7), with a conflict on Meshullam's father: Joed drawn, Hodaviah the other reading.
    - Mattaniah son of Mica (Neh 11:17, 22, 12:35, I Chr 9:15), his father Mica and Asaph the singer, with a conflict on Mica's father: Zichri drawn, Zaccur the other reading.
  - **Possible (7):** Eliashib of Neh 13:4 and of Ezra 10:6 with the high priest; Jehohanan son of Eliashib (Ezra 10:6) with Johanan (Neh 12:22–23); Uthai and Athaiah (I Chr 9:4, Neh 11:4); Zichri and Zaccur, Asaph's sons; Shallum and Meshelemiah, sons of Kore; the two Joahs of II Chr 29:12.
  - **Added:** Gershom <- Phinehas and Daniel <- Ithamar (Ezra 8:2), `descendant`s; both leave "Unattached".
  - **Left:** the Meraioth of Neh 11:11 (block 17b's conflict), Maasai / Amashsai (one key), Obed-edom and Ladan (one key each, not split), the Levites of II Chr 29:12.
  - 6 fewer people (2,836), 47 conflicts, identities: 18 merged, 17 possible.
- 2026-10-22, M91 step 7: Samuel–Kings against Chronicles (`x07-kings.yaml`, reviewed).
  - **Probes:** the people of I Chronicles 10–29 and II Chronicles against the keys of the same name in Samuel and Kings, and the parallel passages side by side (David's sons, heroes and officers, the Rapha's offspring, Abigail and Zeruiah, Jesse's sons, Jehoash's killers, Josiah's envoys and Huldah). TIPNR keys every person of the parallels once, with the variants (Achbor / Abdon, Harhas / Hasrah, Jozacar / Zabad, Ahaziah / Jehoahaz / Azariah, Seraiah / Shisha / Shavsha); the II Chronicles people tied to kings (Rehoboam's and Jehoshaphat's sons, Uriel) have no key elsewhere.
  - **Possible (3):** Elihu "מאחי דויד" (I Chr 27:18) and Eliab; Eliphal son of Ur (I Chr 11:35) and Eliphelet son of Ahasbai (II Sam 23:34); Ahimelech son of Abiathar (II Sam 8:17) and Ahimelech son of Ahitub.
  - **Left:** Shomer / Shimrith on one key, a man; Elpelet, Nogah and Jerimoth, Chronicles' own; Zechariah the gatekeeper on the singer's key; Josiah's sons (step 4).
  - Nothing merged: 2,836 people, 47 conflicts, identities: 18 merged, 20 possible.
- 2026-10-22, M91 step 8: TIPNR's tribe attachments, blocks 01–13 (`x08-tribes.yaml`, reviewed).
  - **The sweep:** the 105 people of Genesis–Nehemiah who hang on a tribe's or nation's eponym by a link not stated, each checked for a verse that gives the tribe or nation, or a son's that they carry. 91 are kept (the comments of the file list them by kind); 6 move and 8 come off.
  - **Moved (6, and Maoch from "unattached"):** Zurishaddai to Simeon (Num 1:6); Nebat to Ephraim ("אפרתי", I Kgs 11:26); Ahijah, Baasha's father, to Issachar (I Kgs 15:27); Abimelech of Gerar ("מלך פלשתים", Gen 26:1) and Maoch, Achish's father ("מלך גת"), to the Philistines; Ethbaal ("מלך צידנים") and Toi ("מלך חמת") to Canaan (Gen 10:15, 18).
  - **Off a tribe (8):** Og, Arba "אבי הענק", Melchizedek, the two Hirams (Tyre is not Aram), Osnappar, Micah of Judg 17 and Immanuel go under "unattached".
  - **Attached (5):** Cush "בן ימיני" to Benjamin; Daniel, Hananiah, Mishael and Azariah "מבני יהודה" to Judah. Joash, Gideon's father, is a `descendant` of Abiezer.
  - **Config:** `genealogy.tribes` gains `Philistia` -> the Philistines (Gen 10:14), so Achish's line now hangs on them too.
  - 2,836 people, 1,799 parent links, 47 conflicts; placed on a tribe 164, unattached 1,076.
- 2026-10-22, M91 step 9: "Unattached", people whose tribe or family the text states (`x09-unattached.yaml`, reviewed).
  - **The sweep:** the 1,076 unattached people, each name followed within four words by a gentilic, "מלך X", "מבני X", "הכהן" or "הלוי" (79 people), then the priests' and Levites' lists of Ezra 8, 10 and Neh 9–12 (107 people whose every verse is in them).
  - **On a nation (28):** the Hittites Zohar, Beeri, Elon and Ahimelech, Hamor the Hivite, Shua "הכנעני", Ornan the Jebusite, and Sihon and Og, "שני מלכי האמרי" (Deut 3:8), under Canaan; Beor (Balaam "מארם"), Cushan-rishathaim and Hezion under Aram; the five kings of Midian, Oreb and Zeeb, Zebah and Zalmunna under Midian; Doeg "האדמי" under Esau; Ittai "הגתי", Phicol and Ahuzzath under the Philistines; Sennacherib under Asshur; Ebed-melech and Zerah "הכושי" under Cush.
  - **On a tribe (131):** Dodo (Issachar), Manoah "ממשפחת הדני", Gera, Abiezer, Ribai, Kish and Zichri (Benjamin), Bani "הגדי", Shiza "הראובני"; the priests and Levites named so (Jehoiada, Uriah, Immer, Buzi, Kadmiel, Imnah, ...) and the 107 of the lists, under Levi.
  - **By descent (9):** Heber the Kenite <- Hobab ("מבני חבב", Judg 4:11); Meshezabel <- Zerah (Neh 11:24); Azariah "לבית צדוק" <- Zadok (II Chr 31:10); Jeshaiah "מבני מררי" <- Merari (Ezra 8:19); the families of Kiriath-jearim and the Zorathites <- Shobal (I Chr 2:52–53).
  - **Left:** gentilics of places (Gileadites, Carmelites, Anathothites), nations with no eponym (Babylon, Persia, the Kenites), Neh 8:4 and 8:7, the singers and gatekeepers of Ezra 10:24, Abihail, Jether, Hammath and the Simeonite princes (the file's comments).
  - 2,836 people, 1,808 parent links, 47 conflicts; placed on a tribe 323, unattached 908 (from 1,076).
- 2026-10-22, M91 step 10: the people in the jump box and in the unit dossier (D102). M91 done.
  - **Data:** `bsim genealogy` writes `mentions.parquet` (each named person's verses, merged keys folded), loaded as `genealogy_mentions` with an index by verse.
  - **API:** a `people` entry in `/dossier/{unit}`: the people its verses name, the most named first (ties: the most named in the whole text), `key` / `label` that person's id / name, "not computed" without the table.
  - **Viewer:** a People group in the jump box after the words and places, each with the parent (or tribe, or spouse) and the first verse that tell namesakes apart (`lib/people.ts`, shared with the tree's search), opening `/genealogy?p=`. Enter before the typing pause looks people up too. A dossier chip "N people in the family tree, most named X" links to the tree at X. English and Hebrew.
  - **Tests:** the mentions (pytest, `test_run_genealogy`); the entry on a verse, a chapter and "not computed" (`test_dossier.py`); the People group in both languages, the chip and its link (vitest).
  - DESIGN §16.63 ("From elsewhere"), the API table and D102; `docs/TASKS.md` M91 and F4 ticked.
- 2026-10-23, M92 (F6): the look of the tree (D103), asked for with a reference PDF of a printed tree (not committed).
  - **Size:** full width, the screen's height; the search, the zoom bar and the legend float over the tree; the person's card over its far side, the person brought into the part it leaves.
  - **Look:** round avatars (man, woman, nation, book) with the name under them; spouses beside as avatars joined by a dashed line, the first on the first-born's side; a mother's children hang from the line between her and the father, so her header is gone; the chosen person's line back to Adam lit in yellow.
  - **Zoom:** a plain wheel (the map keeps Ctrl + wheel), double-click, fit (down to 2%), 100%, full screen; names alone below 45%, dots below 22%.
  - Web only: `lib/familyTree.ts`, `lib/panZoom.ts`, `components/Avatar.tsx`, `pages/GenealogyPage.tsx`, the stylesheet, the strings in both languages.
- 2026-10-23, after M95: children by adoption in the person panel.
  - **Found by** the real-build smoke test: Jacob's panel listed Ephraim and Manasseh as "By אסנת", a group of their mother, Joseph's wife, under Jacob (the panel grouped every child by the child's other parent, the adoptive link of Gen 48:5 too).
  - **Fix:** `/genealogy/person/{id}` puts the children of `adopted` links in a group of their own, after the others (`ChildGroup.adopted`), headed "By adoption" / "באימוץ". The tree is unchanged: Joseph stays their drawn father.
  - **Tests:** `test_api_person_adopted` (pytest), the heading in both languages (vitest); the smoke test now expects the fifth group with Ephraim and Manasseh in it, Gen 25:26 as Jacob's first proof (chosen in the M91 review), יעקב as the node's name, and each mother drawn (a header or an avatar) at a zoom where cards are drawn (M92).
