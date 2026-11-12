# Task List — bible-similarity

Build plan in milestones. Each milestone lists its tasks, dependencies and **acceptance criteria (✔)**. Section numbers (§) refer to [DESIGN.md](DESIGN.md).

Dependency graph:
```
M0 → M1 → M2 → M3 ─┐
            └→ M4 ─┼→ M5 → M6 → M7 → M8 → M9 → M10 → M11 → M12 → M13
```

---

Finished milestones (M0–M141, M144–M146, H1–H5) are in [TASKS_DONE.md](TASKS_DONE.md) (D146). This file keeps the open ones and the latest series, newest first. §16 of DESIGN is in [design/ANALYSES.md](design/ANALYSES.md).

---

## Series O (chosen 2026-11-11): a round of UI/UX work on the viewer; the order of work is M167 → M177, one milestone at a time

Chosen after an audit of the code and of the screen (30 desktop pages from `bsim fixture-serve`, English and Hebrew, light and dark). In scope: finding a page, the reading flow, fewer controls, one way to filter, tables and terms, look and theme, saving and feedback. Out of scope: phone and touch (phone layouts must not get worse). The owner's own use on a desktop comes first. Every milestone: strings in both catalogs, a page's rules in its own stylesheet (D150), view state in the URL and an old URL still read, no change to the pipeline or the DB; vitest, fixture e2e with axe, smoke on the real build, the changed pages looked at on the real build in both languages and both themes.

## M167: The faults the audit found (D156; proposed O1)
- [x] The eleven tables of class `data` (Laws, Mainline, Prophetic, Reception, Witnesses ×3, Theophoric ×2, Neighbourhood, the precision table) had no CSS rule: the shared `change-table` style (the audit counted the eight with that class alone; the e2e check found the others)
- [x] `PrecisionNote`'s `PAGES` and the catalog's `detectors`: `mainline` and `prophetic`, so their Findings rows are named and linked; `PrecisionTable` in a table wrapper
- [x] The error red as a token `--error` (`global.css`, `UnitPicker.css`): #b3261e on light (6.1:1), #f28b82 on dark (7.1:1; the light red was 2.8:1 there)
- [x] `/laws?unit=…` shows the `UnitFilter` strip with its way back to every pair
- [x] The Hebrew top bar: a menu's arrow stays on its label's line (`white-space: nowrap`)
- [x] `Segmented`: one tab stop, the arrow keys, Home and End move and choose, Left and Right by the group's direction
- [x] The phone menu closes on Escape (an open group inside it first), the focus back on its button
- [x] Found on the way: restyled, three tables (Mainline, Reception, the theophoric names) scroll sideways on a phone and their wrapper could not be reached from the keyboard (the smoke's accessibility sweep, `scrollable-region-focusable`). `TableWrap` (in `TableCsv.tsx`): a wrapper is a tab stop and a region named after the heading above it while its table is wider than it, and adds no tab stop otherwise; `TableCsv`, `PrecisionTable` and the ten wrappers written by hand use it; the fixture e2e checks it on every route (five routes failed it on the phone: `/lemma`, `/poetry?view=pairs`, `/poetry?view=meter` with and without its group, `/style`)
- [x] Found on the way: `npm test` collected `e2e-docker/docker.spec.ts` (a Playwright spec, M157) and reported a failed file; `e2e-docker/**` left out in `vite.config.ts`
- [x] Tests: vitest (475: the keys, the phone menu, the table's links and wrapper, the laws strip, `TableWrap`), fixture e2e with axe (1,500 passed: no bare table, the strip, the keys, the Hebrew bar, the phone menu, the error box in dark in both languages, every route's wrappers), smoke on the real build (344 passed, both accessibility sweeps), ruff and pytest (no Python changed; both pass); the changed pages looked at on the real build

✔ No table renders with the browser's defaults; axe passes on the error box in the dark theme.

## M168: The top bar, the Display menu and a theme switch (D157; proposed O2)
- [x] `components/DisplayMenu.tsx`: the text display, the language, the theme (auto / light / dark) and Copy link behind one button of the bar; it opens on a click, closes on Escape (the focus back on its button), a click outside it or a new page, and is slid inside the window as the nav menus are (`lib/menuFit.ts`, shared with them)
- [x] Theme: `lib/theme.ts` and `context/Theme.tsx`, stored as `bsim.theme`; `index.html` writes `data-theme` on `<html>` before the first paint and `main.tsx` before the first render; on auto the system is followed as it changes; the dark token blocks (`global.css` ×2, `PlacesPage.css`) under the one selector `:root[data-theme='dark']`, still inside `@media screen`; `lib/svgExport.ts` puts the theme back after an export (its test now starts from a dark screen); the structure heatmap, which reads its colours from the tokens, is drawn again when the theme changes
- [x] The bar in one row from 1280px in both languages: English needs 1,196px (it needed more than 1366px: 109px tall there), Hebrew 984px, measured on the personal server; the bar's gap 1.5 → 1rem and a nav entry's side padding 0.7 → 0.55rem
- [x] Found on the way: under that width and above the phone menu (half a wide screen) the bar wrapped as it fell, to three rows at 950px in English. There the pages now take a row of their own under the brand and the buttons (English under 1220px, Hebrew under 1010px), never a third row
- [x] Tests: vitest (485: the menu's opening and closing, the theme chosen, kept and following the system, the link copied, Hebrew), fixture e2e with axe (1,512 passed: the bar's rows at 1280, 1263, 1150, 1000 and 905px in both languages, the menu inside the window and through axe in both themes, the theme over a reload, auto following the system, paper light from a chosen dark theme), smoke on the real build (348 passed: the bar's rows, the theme over a reload, both accessibility sweeps), ruff and pytest pass; the bar, the menu and both themes looked at on the real build in both languages, and on a phone

✔ One row at 1280px in English and Hebrew; the theme survives a reload and follows the OS on auto.

## M169: Pinned pages, recent pages, the All pages index (D158; proposed O3)
- [x] `lib/recent.ts`: `bsim.pins` (nav paths, in the order pinned) and `bsim.recent` (the last 8 nav pages and the last 8 passages, a passage once, in the view it was opened in last, with its label in both languages), read through `usePins` / `useRecent`; written by `Layout` on a new path: a nav page by its path, a passage once its unit is known (the unit the page itself asks for), a verse sent on by the reader not at all
- [x] A pin button (`components/PinButton.tsx`, a star, a toggle button) in the bar for the nav page on screen; a Pinned menu, first in the nav, when there is a pin (the nav's own menu, with the pages' hints); the personal pages left out of both on a public server
- [x] `/pages` (`pages/PagesPage.tsx`): every page by menu and section with its hint, a filter box (`matchPages`, kept in the URL as `q`), a star on each row, the pinned pages first; linked at the foot of each menu
- [x] The jump box: before anything is typed, the pinned pages, the passages and pages opened last (not the one on screen, a pinned page not twice) and the index; a book by the start of its name in either language, a word of the English name or the OSIS code ("gen" → Genesis, "sam" → both Samuels), ahead of the pages, and ahead of the words too when the name is whole
- [x] Room in the bar: with the Pinned menu and the pin button English needs 1,323px, so the site's English name beside the Hebrew mark is shown from 1340px (without it 1,197px: one row from 1220px as before); Hebrew needs 1,120px, so its second row starts under 1140px (was 1010px); a phone's bar has no star (pages are pinned from `/pages` there), so it is as tall as it was
- [x] Found on the way: the grey of a nav entry on its hover background was 4.34:1 (axe, with the mouse left on an open menu's button); a hovered entry takes the text colour
- [x] Tests: vitest (`components/Pins.test.tsx`: the two lists, the star and the Pinned menu, the visits recorded, the jump box before typing and its books, `/pages`, a public server, Hebrew); the fixture e2e (`/pages` in every route's checks, the rows of the fullest bar in both languages, the Pinned menu with axe in both themes, the index's filter and star, the jump box in both languages, a public server's index); the smoke on the real build (the fullest bar on the real nav, a chapter read offered again, "gen" to Genesis); the bar, the Pinned menu, `/pages` and the jump box looked at on the real build in both languages and themes, and on a phone

✔ A page pinned once is one click away from anywhere; "gen" offers Genesis.

## M170: The start page (D159; proposed O4)
- [x] `/` (`pages/BooksPage.tsx`, its own rules in `styles/pages/BooksPage.css`): a jump field, Continue (the six passages opened last as cards, each in the view it was left in, and the six pages opened last as a row of links), the pinned pages (not again among the recent ones), the three notebook entries changed last with the first line of each note (a personal server with something kept), this week's parasha, the Findings and the All pages links, then the books under one heading, the canon's sections under it; the tours one line at the foot (`/tours`, the glossary); the Explore panel gone (`/pages` has it), its strings and rules removed
- [x] The jump field: `JumpField` (`components/JumpBox.tsx`), the box's own field and list, `inline` here: the list drops under the field while something is typed, Escape clears, Tab moves on, and nothing is listed before typing (the page lists the recent ones itself)
- [x] A first visit with nothing stored (no recent passage or page, no pin) shows the tours in Continue's place
- [x] The page's own parts are there before the books load, and stay when the books cannot be loaded
- [x] Found on the way: the notebook was asked for before `/meta` had said whether the server keeps one, so a public server's start page would have asked for it; `useNotebook` waits for `/meta`. In the jump box a book's Hebrew name is isolated (FSI … PDI), so the chapter count after it stays in its place in English
- [x] Tests: vitest (`pages/StartPage.test.tsx`: a first visit, Continue and the pinned row, the notebook's latest and a server without one, the jump field, the books failing, Hebrew); the fixture e2e (a first visit, a cold start after a passage read in both languages with axe in both themes, the jump field, the notebook's latest answered in the browser; a public server's start page asks for no notebook); the smoke on the real build (a psalm found from the field and one click away after a cold start); the page looked at on the real build on a first visit and with something to go back to, in both languages and themes, and on a phone

✔ From a cold start the last passage read is one click away; a public server shows no notebook.

## M171: The reading flow (proposed O5)
- [ ] The reader lands on the verse (`#v<verse_id>`, scrolled to and marked)
- [ ] A Read link on `HitCard`, Search results and Query hits
- [ ] `components/CopyButton.tsx`: the reference, and the verse in the text display in use
- [ ] Back keeps your place (scroll saved per history entry); a new page still starts at the top
- [ ] A page change in `PagedList` scrolls the list's top into view
- [ ] Search results get the row actions that fit a free-text query
- [ ] `UnitPicker`'s reference field suggests as you type
- [ ] Tests

✔ "Read with layers" from Genesis 22:2 opens chapter 22 at verse 2; Back from a hit returns to the same hit.

## M172: The unit page (proposed O6)
- [ ] `DossierBar`: the chips grouped under the nav's families (from the nav section of the page a chip links to), the rest behind "more"
- [ ] A sticky strip that jumps to the page's sections, the one in view marked
- [ ] The results controls in one row, a Reset link, the text options under one group
- [ ] Tests

✔ On a chapter page the similar passages are one click from the top; the chips read as groups.

## M173: The reader's layers (proposed O7)
- [ ] The 18 toggles grouped, with presets (default, poetry, narrative, none) and a reset
- [ ] The legends in one Key block that folds, kept in the URL
- [ ] What the layers say about a word listed in the `WordPanel` on a click
- [ ] Tests

✔ With eight layers on, the first verse is visible without scrolling at 1366×860.

## M174: One way to filter (proposed O8)
- [ ] `SignificanceFilter` and `KnownOnly` in `Controls.tsx`, used by every page with such a filter; the old parameter forms still read; the conventions in DESIGN §11
- [ ] A toolbar's rule (up to five short options a `Segmented`, more a `select`) applied to the 13 mixed toolbars; Gematria's chips a `Segmented`
- [ ] The hand-written empty states through `EmptyList`; the six hand-placed `Pager`s through `PagedList` where the response fits; Root's CSV
- [ ] The 19 paged lists without an export: the page export, and the all-rows export where the server's export table takes the list
- [ ] Tests

✔ The significance filter looks and behaves the same on every page that has one; every paged list can be exported.

## M175: Tables and terms (proposed O9)
- [ ] One table style; `.num` on every numeric column
- [ ] Sticky table headers on desktop
- [ ] p, q, G² and the glossary's other terms in table headings through `Term`
- [ ] Tests

✔ Every p / q heading opens its glossary entry; numbers line up on the right on every page.

## M176: A type and spacing scale; headings before data (proposed O10)
- [ ] Tokens: a type scale, a spacing scale, radii, shadows through `--shadow`; two breakpoints, written in §11
- [ ] The section and district palettes hard-coded in five page modules as tokens with dark values
- [ ] The 33 pages that show "Loading…" before their heading draw the heading and lede first; a quiet placeholder for lists
- [ ] Screenshots of every fixture route before and after, gone through by eye
- [ ] Tests

✔ No raw font size or radius left in `global.css`; a page's title is there before its data.

## M177: Saving and feedback (proposed O11)
- [ ] `components/Toaster.tsx`, `useToast`: one live region for saved, removed with Undo, and failures
- [ ] Labels: a note says saved or failed; clearing a label offers Undo
- [ ] Notebook: a note saves itself after a pause and on blur; a save in flight guarded on leaving; removing from a collection offers Undo; the text filter in the URL
- [ ] Tests

✔ No edit is lost silently: every save says so, every removal can be undone for a few seconds.

---

## Series N (chosen 2026-11-10): the order of work is M156 → M166, one milestone at a time

## M166: Law codes side by side (§16.93, D155; proposed N10)
- [x] `analysis/laws.py`, `bsim laws` (`laws` in `bsim all`): the codes as verse ranges in config (Covenant Code, Exod 34:10–26, Holiness Code, Deuteronomic Code, the other priestly law), laws cut at the MAM paragraphs (257), each law's form (107 casuistic, 109 apodictic, 41 other) and its address
- [x] The form rule tightened after the first run: a protasis needs a yiqtol within 3 words of its verse (the first run took every כי, and Exod 34:10's כי נורא הוא made the ritual decalogue casuistic); the matching untouched
- [x] Laws matched across codes over the fused verse list (links in each other's first 20, at least 2, the best match in the other code): 344 pairs; aligned word by word (`diffs.align_words`) over their linked verses, span to span
- [x] Known pairs fixed before the first run (slave release, asylum, festivals, sabbatical year, interest, the kid in its mother's milk), counted pair of passages by pair: 18 of 21, by the aligned verses themselves also 18; not found the sabbatical year Lev 25 / Deut 15 and Deut 14:21 against both Exodus verses
- [x] DB `laws`, `law_pairs`, `law_marks`, `law_codes`; API `/laws`, `/laws/list`, `/laws/pairs`, `/laws/pair/{id}`; Findings `laws`, the dossier `laws`, exports `laws` and `law-pairs`
- [x] Viewer: `/laws` (Parallels: the codes by form and address, the known pairs, the matched pairs, the laws by code and form, a pair side by side in two columns with its changes marked); English and Hebrew
- [x] Tests: a verb's person, a law's form (the protasis, apodictic forms, מות יומת), the links and the matching, the stage on a toy corpus, the API, the exports, the dossier, Findings and a public server (pytest); the page in both languages, the nav (vitest); fixture e2e with axe, smoke on the real build
- [x] The full checks: pytest, vitest (465), fixture e2e (1,490; the Hebrew psalms page failed once on the phone under load and passed on a rerun), smoke on the real build and its accessibility sweep

✔ The codes can be read side by side: 18 of the 21 pairs of passages the commentaries name are found among the laws the fused list matches across codes, and the forms fall as the scholarship describes them, the Covenant Code casuistic, the Holiness Code apodictic.

## M165: Prophetic forms (§16.92, D154; proposed N9)
- [x] `analysis/prophetic.py`, `bsim prophetic` (`prophetic` in `bsim all`): the messenger formula (801), woe sayings (38), oracles against the nations (70), covenant lawsuits (62), call narratives (12), by rule over the OSHB lemmas and morphology and the BHSA clauses; each form's words in config (`prophetic`), fixed before the first run
- [x] The call's speakers loosened after the first run (4 calls, Isa 6 and Ezek 1–3 missed: BHSA has no speaker in the prophets' own accounts): the commission and the reassurance not said by a man BHSA names; the known passages unchanged
- [x] Known answers as the plan wrote them (Isa 13–23, Jer 46–51, Ezek 25–32, Amos 1–2; Isa 1:2, Mic 6:1–2, Hos 4:1, Jer 2:9, Deut 32:1; Exod 3–4, Judg 6, Isa 6, Jer 1, Ezek 1–3; Isa 5:8–23, Hab 2:6–19), found by cover (nations, woe: half the verses) or overlap (call, lawsuit): 16 of 16; the spread by book
- [x] Precision by Claude's reading: `llm-audit --detectors prophetic --tag m165` (dry run first, $0.24; the messenger formula not judged): 0.53 [0.39, 0.66]; woe 9 / 11, nations 13 / 23, call 1 / 1, lawsuit 3 / 14 (any mountain a witness, any call to hear)
- [x] DB `prophetic_items`, `prophetic_books`, `prophetic_words`; API `/prophetic`, `/prophetic/items`, the reader's `prophetic`; Findings `prophetic`
- [x] Viewer: `/prophetic` (Patterns → Poetry and form: the forms and their rules, the passages named in advance, the forms by book, the findings with their marking words); the reader's Prophetic forms layer (the words boxed); English and Hebrew
- [x] Tests: the morph parts, the cover, the joining, every form on a toy corpus and the rules that hold back (mourning, a man's commission, a bare call to hear), the API, the reader, Findings and a public server (pytest); the audit's claims (pytest); the page in both languages, the reader layer, the nav (vitest); fixture e2e with axe, smoke on the real build
- [x] The full checks: pytest, vitest (461), fixture e2e (1,464; the citations page's accessibility check timed out once under load and passed on a rerun), smoke on the real build and its accessibility sweep; `test_reader_without_stages` empties the new table too

✔ Rules over the words find every passage the commentaries name for the four forms; about half of what they find is the form by Claude's reading, the woe sayings mostly, the lawsuits seldom.

## M164: The narrative main line (§16.91, D153; proposed N8)
- [x] `analysis/mainline.py`, `bsim mainline` (`mainline` in `bsim all`): the narrator's independent BHSA clauses outside quoted speech (27,167), wayyiqtol the main line (14,625), the rest background; per paragraph, per book
- [x] Pauses inside the chain: in the narrative books, background runs of 2 to 30 clauses with a wayyiqtol just before and after in the narrator's stream (1,250). Not as the first run had it: by paragraph, which listed Proverbs and Ecclesiastes and could not hold 1 Sam 3:1-3 (a paragraph break between every verse)
- [x] The claim, fixed before the first run and kept: background more common among a paragraph's first 3 narrator clauses: not borne out (−0.9 points against +2.9 by chance, p 1.0)
- [x] Known answers (Gen 3:1, Gen 29:16-17, 1 Sam 3:1-3, Ruth 1:1-2, Judg 3:20-22): 5 of 5 overlap a pause
- [x] Precision by Claude's reading: `llm-audit --detectors mainline --tag m164` (dry run first, $0.22; its own folder, `llm_audit.shown_runs`): 0.57 [0.43, 0.70]; the wrong ones lists, unmarked speech, law's closing formulas
- [x] DB `mainline_pericopes`, `mainline_pauses`, `mainline_books`, `mainline_clauses`; API `/mainline`, `/mainline/pauses`, the reader's `mainline`; Findings `mainline`
- [x] Viewer: `/mainline` (Patterns → Narrative): the claim and its note, the known pauses, the books, the pauses with their verses; the reader's Main line layer (background underlined); English and Hebrew
- [x] Tests: the narrator's clauses, the runs inside the chain, the opening share, the stage on a toy corpus, the API, the reader and a public server (pytest); a tagged audit run and the runs shown (pytest); the page in both languages, the nav (vitest); fixture e2e (the page and the reader layer), smoke on the real build
- [x] The full checks: pytest, vitest, fixture e2e (1,436; two Hebrew pages hit Windows' ERR_NO_BUFFER_SPACE under load and passed on a rerun), the smoke accessibility sweep; `test_reader_without_stages` empties the new table too

✔ Every story's chain of wayyiqtol and its 1,250 pauses can be read in the text; the scene is not set at the paragraph breaks more than elsewhere, and about four pauses in seven are pauses by Claude's reading.

## M163: Theophoric names over time (§16.90, D152; proposed N7)
- [x] `analysis/theophoric.py`, `bsim theophoric` (`theophoric` in `bsim all`): HebrewStrong's person names derived from יה / יהוה / אל and those called "a form of" one (300; ישראל left out), each occurrence's form from its consonants (‑יהו, ‑יה, יהו‑, יו‑, אל‑, ‑אל); 283 names in 3,150 occurrences; counts by name and book
- [x] The claim, fixed before the first run (the same names shuffled between early and late books): late 64 % short, early 26 %, p 0.053 against a shuffle that gives 0.35 of the 0.38 difference: not borne out, the gap mostly which names each side uses
- [x] Known answers as the plan wrote them before the run: Jeremiah, Kings long, Ezra, Nehemiah short hold; Chronicles short does not (44 %: 2 Chronicles keeps Kings' long spellings)
- [x] The dating feature `yah_short`, stored for every chapter; `dating.features` (the model's), measured by the rule fixed before: AUC 0.948 → 0.889, 0.895 → 0.852 without the lexemes, synoptic 24 → 22 of 24: not adopted; without it the model's numbers exactly as before; borrowing unchanged (28 of 30)
- [x] DB `theophoric_names`, `theophoric_books`; API `/theophoric` (its known answers with book ids), `theophoric` on `/entities/{lemma}`; Findings `theophoric`
- [x] Viewer: the Language page's section (the claim, the known answers, the forms by book, the most frequent names, why the feature is not in the model), a line on each such name's panel on Names; English and Hebrew
- [x] Tests: the names from a small lexicon, the forms, the occurrences and the within-name share, the stage on a toy corpus, the dating feature and the feature list, the API, Findings and a public server (pytest); the section in both languages (vitest); fixture e2e
- [x] The full checks: pytest, vitest, fixture e2e (1,412), smoke on the real build (the section's verdict and Jeremiah's line on Names, the accessibility sweep)
- [x] Fixed on the way: `test_api_queue_without_splits` deleted `splits.json` while the label queue's preload thread read it (Windows refuses to delete an open file; seen in the full run only); the test's app runs without the preload
- [x] Not run: `bsim all`. Its dry run shows `train-sup` as code changed (cause not traced) and the stages series N ran by hand as stale; run it with `--skip train-simcse --skip train-sup`

✔ The spelling of the divine name in names follows the history of the language in the books scholars cite (Jeremiah and Kings long, Ezra–Nehemiah short), but for the same names the late books' preference for ‑יה is not beyond what the names they use give, and it does not help the late-language profile.

## M162: A study page from the notebook (D151; proposed N6)
- [x] `lib/notebookPage.ts` `studyPage`: what the notebook shows (a collection with its description, or the filtered entries) as one standalone HTML file: the day, each passage linked back to the site, a verse in the text display chosen on screen, the note escaped as text (paragraphs and line breaks kept), the collections, the verses' source and licence; light, inline styles, no script; direction by the interface language
- [x] Notebook: *Download a study page* beside Markdown and CSV, and *Print* with a print stylesheet (each note as text; editors, collections and controls left out); English and Hebrew
- [x] Tests: the page, the escaping, the text display, Hebrew (vitest); fixture e2e: the file downloaded with a collection chosen (its name, title, note and link), print media (the note shown, the editors hidden)

✔ A notebook, or one collection of it, leaves the site as a page anyone can open or print: the verses as read, the notes, and the way back to each passage.

## M161: A verse's neighbourhood (D149; proposed N5)
- [x] `api/neighbourhood.py`, `GET /neighbourhood/{unit_id}?k=&hops=`: the stored fused list of each node followed (`serve.neighbourhood`: k 6, hops 2, max_nodes 40; a verse's neighbours left out), each edge with its kinds (the lists' lexical and semantic ranks, a shared phrase, a gold link; between the nodes found, significant sequences and allusions, resolved citations, chapter echoes and borrowing), a seeded spring layout with the unit in the middle; 422 past the limits, 404 for an unknown unit; about 0.25 s a graph on the real DB
- [x] `/neighbourhood/:unitId`: the graph (pan and zoom, zoom buttons, SVG export), each edge in the colour of its first kind (the project's tokens, dashes where kinds share one), every kind a toggle kept in the address (`?off=`), a click puts a passage in the middle with the same settings; a table of every passage with its link to the middle; English and Hebrew; its own stylesheet (D150)
- [x] Linked from the unit page and from Compare's two sides; a public server has it (stored lists only)
- [x] Tests: the walk, the kinds and their order, one step and the cap, the same layout twice, the limits, a public server (pytest); the page, the toggles through the address, the settings carried, Hebrew (vitest); fixture e2e (two routes in both languages with axe, a walk from a unit page, a passage with nothing of its own), public e2e, smoke on the real build (axe found the zoom buttons in the browser's grey in the dark theme, 4.2:1: given the page's surface)

✔ From any passage, its parallels and theirs are one click away as a picture, each link saying what joins the two, and any passage in it can be put in the middle.

## M160: The stylesheet split by page (D150; proposed N4)
- [x] Each selector moved to the stylesheet of the one `.tsx` module that writes one of its classes (as a word, or the template prefix that builds it); the rest stays in `global.css` (tokens, base, layout, shared components); order kept per file, `@media` blocks split per file; 99 modules import their own `styles/pages/` or `styles/components/` file
- [x] Screenshots of every fixture route (158), English and Hebrew, light and dark, desktop and phone (1,264) before and after, pixel-compared: the first split turned the reader's Leitwort keys (`.lw-0` … built as `lw-${k}`, left global, now before `.layer-key`); the template prefix found it, and the second split differs only on the brackets page caught mid-load in the first shots (settled height 1,872 with and without the split)
- [x] First-load CSS 88,249 → 31,238 bytes (18,765 → 7,950 gzipped); 83 stylesheets, all in the offline app's precache
- [x] Convention: a new page's rules go in its own file (DESIGN.md §11, D150)
- [x] Tests: vitest, fixture e2e with axe and smoke on the real build (with M161's runs)

✔ A first visit downloads 11 KB less CSS (gzipped), and a page's rules arrive with the page; every page looks as it did, in both languages and both themes.

## M159: The detectors' recurring wrong findings (D148; proposed N3b)
- [x] Each rule chosen from the wrong findings' Hebrew rationales and tried on the findings Claude had judged (M152, M158) before adoption; a config switch each, off for the first runs:
  - brackets `formula_reach` 40: a repetition whose tokens all stand in a third verse nearby is a formula (3404 → 1739); the page lists the known three by default (`?show=all` for every one)
  - ciphers: the page lists the swaps named in advance by default (`?known=0` for every one)
  - refrains `form_share` 0.5 and `names: false`: a refrain repeats its words; no man's title; not numbers alone (551 → 440 distinct)
  - forms `alone_steps` [[1, 2]]: in one … two both numbers stand alone (`counts_a_noun`; 91 → 70 sayings)
  - seams `snap` 2: each seam at the nearest paragraph start in reach, or left out (241 → 159)
  - etiologies `explained_only`: listed where the verse explains (כי, על כן, אמר; 111 → 65)
  - type scenes `etcbc_share` 0.5 and `skip_adjacent`: ETCBC's parallels mark a parallel text (Ps 70 / 40); pericopes side by side are not paired
  - acrostics `span_trim`: the span from the alphabet's start (Prov 31:10, Ps 119:1–176)
- [x] Known recall not lower for any detector (etiologies 16 / 16, refrains 8 / 9, sayings 18 / 19, acrostics 13 / 14, brackets 3 / 3); tried and not kept: refrains by form in every token, sayings on a parallel line or in two cola, the acrostic chain by the nearest line
- [x] `bsim build-db`; the `pages` audit again with its own seed (`llm_audit.pages.seed`, dry run first; $1.22): etiologies 0.59 → 0.85, seams 0.30 → 0.64, refrains 0.29 → 0.36, sayings 0.26 → 0.30, the unchanged ones within 0.18 of M158; RESULTS.md, two numbers in `test_docs_numbers.py`; M158's run kept as `llm_audit_pages_m158`
- [x] Tests: each rule (pytest), the brackets and ciphers defaults (vitest), the e2e tests that opened the old defaults
- [x] The full checks: pytest, vitest, smoke on the real build (two expectations moved: the etiologies listed 65, Exodus 6's p 0.007 over the new draws); fixture e2e 1,392 passed
- [x] Fixed on the way: 5 fixture e2e tests on /labels failed in the full run only. The queue test asked for the next pairs before the server had written the label the button already showed (it now waits for the write), and the page's axe check failed whenever another test's label was listed: its two unit links in a line of text were not underlined (`link-in-text-block`, a real fault an empty list hid; underlined, and the labels test now runs axe with a label in the list)

✔ A reader of the etiologies and the seams now sees right findings five times in six and two in three, the known answers all kept; resumptive repetition and the ciphers show what is known by default, since no rule here rescues the rest.

## M158: Detector precision on what the pages show (D147; proposed N3a)
- [x] `llm_audit.population: strongest | pages` (`bsim llm-audit --population pages`): 50 drawn uniformly from each page's default list (`llm_audit.pages.shown`: acrostics and type scenes q ≤ 0.05, allusions new pairs only; the rest list all) and from what a page marks as strong (`pages.marked`: brackets, etiologies); all of a shorter list; its own folder, M152's run kept
- [x] Found on the way: the plan assumed the pages hide their weak findings by default; only three do, so `shown` is mostly the whole list, sampled uniformly
- [x] Dry run: 743 requests, about $1.51 (budget $10); the run (2026-11-10, $1.37): calibration holds (places 46 / 50, known 87 / 91); RESULTS.md beside M152's table, two numbers in `test_docs_numbers.py`
- [x] Not done as the plan had it: a `detector_precision` DB table; the API reads the calibrated runs' meta files, cached by their times, as the notes are (D147)
- [x] API `/detector-precision` (personal only, 404 on a public server); `PrecisionNote` under the lede of the 14 audited pages' lists, `PrecisionTable` at the end of Findings; English and Hebrew (`i18n/pages/precision.ts`)
- [x] Tests: the condition, the draw, the output folder, a `pages` run, a failed calibration left out, the API and the public server (pytest); the note, the table, Hebrew, the public server (vitest); fixture e2e in both languages with axe, public too

✔ Of what the pages list, acrostics at q ≤ 0.05 are right three times in four (the strongest 200: 0.08), resumptive repetition and the ciphers almost never, marked strong or not; most full lists fall below their tops. Each page now says so.

## M157: The open runs (proposed N2)
- [x] M143: `self` and `self_ce` trained (2026-11-11), dev tables and the verdict: neither adopted (fused OpenBible +0.0009 and +0.0007, CIs reaching 0)
- [x] M147: the image built and run with the bundle, health and smoke checked (62 checks passed; publishing stays the user's decision)

✔ The model's own near misses as negatives move the fused list by no more than a reseed does; the public image runs with nothing personal in it. M142's `labels` variant still waits for 30 real train pairs.

## M156: The docs split (D146; proposed N1)
- [x] DESIGN.md §16 moved verbatim to `docs/design/ANALYSES.md`; a list of its titles left in its place; D146
- [x] Finished milestones (M0–M141, M144–M146, H1–H5) and the review lists moved verbatim to `docs/TASKS_DONE.md`; 933 task lines before and after
- [x] ARCHITECTURE, CLAUDE.md and README point to the new files
- [x] Tests: `test_llm_gold.py` (D54 and §11's rules still found), the full checks

✔ DESIGN.md 510 → 158 KB and TASKS.md 245 → 18 KB, every number where the code's citations expect it.

## M155: A review of the Hebrew interface (§16.89, D145; proposed L8)
- [x] `eval/llm_ui.py`, `bsim llm-ui-review [--dry-run]`: each of 54 catalog groups, English beside Hebrew, D54 and §11's rules, the Hebrew glossary; Claude Opus 5.5 at effort high; a checklist report, no catalog changed
- [x] Dry run: 54 requests, about $3.20 (budget $8)
- [x] Tests: the groups and rules found, the answer read, a run with a fake batch client and its report (pytest)
- [x] The run (2026-11-05, $2.41): 252 suggestions in 54 groups (wording 79, meaning 61, agreement 34, consistency 31, grammar 24, term 23); in RESULTS.md
- [x] The owner's choice (2026-11-05): all 252 applied to the Hebrew catalogs (243 by script where the current text was found, the 9 abbreviated ones by hand); one suggestion put code inside a template string (`sums.pairCount`) and was written with `countHe` instead
- [x] The same terms carried to the strings the review did not list: the cipher names (אתב״ש, אלב״ם) across ciphers, dossier and Findings; the Labels page as התוויות שלכם with the reader in the plural, the dossier's and notebook's תיוגים; divisions' למות; `inHe` (ב־ before a digit) where ב stood before a count
- [x] `docs/HEBREW_UI.md`: the agreed terms and conventions; pointed to from CLAUDE.md
- [x] Tests: the Hebrew assertions that quoted the old wording updated (10 vitest files), `inHe` (vitest); vitest, and fixture e2e in Hebrew on every page with axe, on phone and desktop

✔ The Hebrew interface uses one term for each thing, the glossary's, addresses the reader in the plural throughout, and its 252 reviewed strings read as Hebrew prose.

## M154: Claude's notes beside the strongest parallels (§16.88, D144; proposed L7)
- [x] `eval/llm_notes.py`: `read_notes` gathers every calibrated run with a Hebrew rationale (about 25,000 pairs); `bsim llm-notes [--dry-run]` reads the 5,000 strongest fused verse discoveries not yet read, its own calibration
- [x] API: `/pair-note` and `note` on verse discoveries (`api/notes.py`, cached by the runs' files); personal only (404 and no notes on a public server)
- [x] Viewer: `ClaudeNote` (the queue's suggestion, shared) on Compare's pair panel and the discovery cards; `usePairNote`; the types regenerated
- [x] Fixture: a made-up notes run on v:0 / v:3
- [x] Dry run: 5,100 requests, about $7.80 (budget $15)
- [x] Tests: the runs gathered and their order, calibration and language, the strongest pairs, the API and the public server (pytest); the card with and without a note (vitest); fixture e2e in both languages, phone and desktop, with axe
- [x] The run (2026-11-05, $9.23): calibration AUC 0.976; 4,469 of the 5,000 strongest called real; 29,117 pairs with a note in all

✔ The strongest parallels and every pair a series-L run read carry Claude's reading in Hebrew beside them, as a suggestion, on a personal server only.

## M153: Speaker and family-tree gold (§16.87, D143; proposed L6)
- [x] `eval/llm_speakers.py`, `bsim llm-speakers [--dry-run]`: 100 quotations of each source (454), the passage and the opening words; the answer mapped to a lemma; `bsim speaker-eval`, per source and on the dev books, the owner's sheet of 30
- [x] `eval/llm_genealogy.py`, `bsim llm-genealogy [--dry-run]`: 50 siblings no shared parent implies and 315 attachments to a named people or tribe, calibrated on 100 confirmed against 45 rejected parent links; a review sheet, never the curation files
- [x] Dry runs: 454 requests, about $0.95; 510 requests, about $0.91
- [x] Tests: letters and lemma matching, the draws, the passage, agreement; the candidates, the calibration, a run and its sheet (pytest)
- [x] The runs (2026-11-05, $0.87 and $0.78): speakers per source (explicit 83 / 94 … carried 55 / 89); the family tree's calibration AUC 0.952, 27 of 50 siblings and 23 of 315 attachments called wrong; in RESULTS.md
- [x] The owner marks the 30 speaker answers (`artifacts/llm_speakers/review.csv`); `bsim speaker-eval` again: 26 right, usable
- [x] `artifacts/llm_genealogy/review.md` gone through in the curation files (2026-11-05, at the owner's word): 44 sibling links rejected (25 called wrong, 19 the same reading carried through), the Meunites off Canaan; 22 attachments called wrong kept (priests are Levi's line), 2 siblings left open; `role: sibling` in the format

## M152: How often the detectors are right (§16.86, D142; proposed L5)
- [x] `eval/llm_audit.py`, `bsim llm-audit [--dry-run]`: 50 of the 200 strongest findings of 14 detectors and their known answers, each claim with the detector's definition and the pointed verses; type scenes without the parallel texts
- [x] Calibration fixed before the run: the owner's place sample (49 / 50) at least 85 % right, the known answers at least 80 %
- [x] Precision with a Wilson interval; `artifacts/eval/llm_audit.md` with the wrong findings
- [x] Dry run: 805 requests, about $1.70 (budget $10)
- [x] Tests: the claims, known answers, the draw, the interval, the gate, a run with a fake batch client (pytest)
- [x] The run (2026-11-05, $1.53): calibration holds (places 45 / 50, known 127 / 138); the table in RESULTS.md: wordplay 0.87 … ciphers 0.02, the low ones beyond their significant findings

✔ Each detector's precision is measured, not only its recall: the found-as-read detectors are right four times in five, and the ones past their significant few are noise, as their tests said.

## M151: The reranker taught by Claude (§16.85, D141; proposed L4)
- [x] `eval/llm_rerank.py`, `bsim llm-rerank [--dry-run]`: 5,000 of the cross-encoder's 37,457 training negatives (its own draw), the triage's prompt and schema, a calibration of its own (seed 91), one batch on the core
- [x] `rerank.soft_labels: none | llm` (`train/rerank.py`): judged negatives take `p_real` as the BCE target; `llm_extra` adds the judged queue pairs as rows; calibrated runs only; the counts in the model's meta
- [x] `configs/rerank_llm.yaml`: its own model, list and tuning file (`rerank_tuning_{system}.json` for any system but `fused_rerank`), the model in use untouched
- [x] Dry run on the real data: 5,100 requests, about $8 (budget $15)
- [x] Tests: the sample, the soft targets and extra rows, calibrated runs only, a run with a fake batch client, the profile (pytest)
- [x] The run (2026-11-05, $9.07): calibration AUC 0.972; 1,647 of the 5,000 negatives called real (33 %)
- [x] Train and tune (2026-11-05, GPU): `bsim train-rerank --config configs/rerank_llm.yaml`, `bsim rerank --tune --config configs/rerank_llm.yaml`; grid best `w_ce` 1.0, dev nDCG@10 0.204
- [x] A control: the model in use over today's fused list (`fused_rerank_control`), since `fused_rerank` was built on 2026-10-04's
- [x] Dev table in RESULTS.md (with the judged pool) and the adoption verdict: not adopted (against the control, Sefaria +0.0029 [−0.0035, +0.0095], ETCBC −0.0072; only the judged pool gains)
- [x] Rebuild `fused_rerank` over today's fused list with the model in use (2026-11-05, `bsim rerank --tune`, at the owner's word): dev nDCG@10 0.194 → 0.201, against fused Sefaria +0.0077 [+0.0026, +0.0130]; `w_ce` 0.25 still the grid's best

✔ Soft targets from Claude do not make a better reranker by Sefaria, OpenBible or ETCBC; the margin over the list in use came from the newer fused list under it. `berel-rerank` stays.

## M150: Training on Claude's verdicts (§16.84, D140; proposed L2)
- [x] `eval/llm_train.py`, `bsim llm-train [--dry-run]`: the label queue's next 10,000 pairs after the triage's 500, its prompt and schema, a calibration of its own (seed 81), one batch on the core
- [x] `extra_pairs: [llm]` (`train/pairs.py`): both runs, each only when calibrated; real with p ≥ 0.7 as positives, not with p ≤ 0.3 as hard negatives (`train/negatives.py`, as labels); the Sefaria split rule; `split_pairs` / `both_ways` shared with labels
- [x] Variant `supervision_experiments.variants.llm`; `report_golds: [llm]` puts the judged pool in the table, no rule reading it
- [x] Dry run on the real queue: 10,100 requests, about $15 (budget $25)
- [x] Tests: the runs read only when calibrated, the source's thresholds and splits, the negatives, the triage's pairs skipped, a run with a fake batch client (pytest)
- [x] The run (2026-11-05, $17.57): calibration AUC 0.938; 3,196 real, 5,162 not, 1,640 unsure; the source 1,221 positive and 5,294 negative train pairs
- [x] Train the `llm` variant (2026-11-05, 2 h 25 min on the GPU: `bsim supervision-exp --only llm`)
- [x] Dev table in RESULTS.md and the adoption verdict: not adopted (fused OpenBible +0.0006 [−0.0013, +0.0025], below the noise bar); the judged pool +0.0064 [+0.0018, +0.0111], read by no rule

✔ Claude's verdicts on 10,500 queue pairs do not move the encoder by the rule fixed in advance: a gain on the judged pool and on the semantic list's Sefaria score, none on OpenBible. `berel_sup` stays.

## M149: A judged dev pool (§16.83, D139; proposed L3)
- [x] `eval/llm_pool.py`, `bsim llm-pool [--dry-run | --score]`: the top 5 of lexical, semantic, fused and `fused_rerank` for each dev Sefaria query (neighbours dropped, Sefaria's pairs left out), the triage's prompt and schema, one batch on the core (L1)
- [x] Calibration fixed before the run: all 602 fair dev Sefaria links against 602 random dev pairs, AUC ≥ 0.75; Claude's recall of Sefaria reported
- [x] The `llm` gold: Sefaria's and Claude's real pairs, `unsure` unjudged, scored on condensed lists; `Scorer` takes it; `--score` writes `artifacts/eval/llm_pool.{json,md}` (nDCG@10, P@5, the judged share of each top 10, the gain over fused)
- [x] Dev judgements never train: `extra_pairs: [llm_pool]` refused
- [x] Dry run on the real data: 9,239 pool pairs, 10,443 requests, about $16 (budget $30)
- [x] Tests: the pool, the judged gold and condensed lists, P@5, a run with a fake batch client, a failed calibration, the training refusal (pytest)
- [x] The run (2026-11-05, $18.60): calibration AUC 0.966 (holds), recall of Sefaria 0.595; the pool 4,095 real, 3,935 not, 1,208 unsure
- [x] `bsim llm-pool --score`; the dev table in RESULTS.md: fused 0.764 on the pool (0.193 on Sefaria), the lists alone about 0.09 below, the cross-encoder level (+0.002, CI across 0); two numbers checked by `test_docs_numbers.py`

✔ About two thirds of the fused list's top 5 are connections Claude calls real, where Sefaria records one in eighteen; fusion's lead over either list holds on the judged pool, and the cross-encoder's does not appear there either.

## M148: One batch core for the Claude jobs (§16.82, D138; proposed L1)
- [x] `eval/llm_batch.py`: `make_request`, `parse_message` with the job's check, `run_batch` (estimate, dry run, budget, submit, batch id first, resume, poll, collect), `mark_collected`, `usage`; `pointed`, `clean_rationale`, `auc` moved here
- [x] `budget_usd` per job (the triage's 5.0): a submission over its typical estimate is refused, nothing sent
- [x] The estimate's typical answer measured: `llm_triage.typical_output_tokens` 1,200 → 160 (152 measured on the M144 runs)
- [x] `llm-triage` on the core: the same prompts, files and meta (with the mean answer); the queue reads `clean_rationale` from the core
- [x] Tests: the core with a fake batch client (`tests/llm_fakes.py`): requests, answers read and refused, dry run, budget refusal, submit / poll / collect, resume without paying again, a batch of errors, missing answers; `test_llm_triage.py` unchanged

✔ Every Claude job shares one tested way to send a batch, refuses to spend past its budget, and estimates from what the last run cost.

## M147: A public read-only server (§10.3, D137, docs/DEPLOY.md; proposed K8)
- [x] Config profiles: `extends:` with a mapping merge; `configs/public.yaml` (nothing personal, no encoder, same-origin only) and `configs/docker.yaml`
- [x] `serve.personal` (labels, notebook, label queue: 404 `personal_off`), `serve.encoder` (`OffEncoder`: semantic / fused search and `/align` 503, no hubness, no torch), `serve.embeddings` (`/compare` 503, no semantic structure basis, null ladder cosines); `/meta` reports them
- [x] The viewer follows them (`useServer`): the nav and the jump box without the personal pages, their hooks idle, `/labels` and `/notebook` say so, lexical-only search, no meaning marks on Compare, the lexical structure basis only, no workbench collections; both catalogs
- [x] `bsim deploy-bundle [--no-nc] [--no-embeddings]`: the DB by backup, the vectors, the Evaluation files, a manifest; nothing personal. `--no-nc` empties 19 tables (636,584 rows) of six stages and takes them off `stages_run`, and leaves out `etcbc.json`; the real bundle is 859 MB
- [x] pyproject: torch, transformers, sentence-transformers, datasets and accelerate in a default `ml` group; a torch-free install of the server is 347 MB and serves the real bundle
- [x] `Dockerfile` (Node build of the viewer, `uv sync --no-default-groups`, read-only bundle mount, unprivileged, health check) and `.dockerignore`
- [x] `docs/DEPLOY.md`: what is served and left out, every source's terms, what `--no-nc` removes, and the decisions that are the user's (non-commercial use; the encoder trained on the ETCBC parallels; share-alike; where to host, with TLS and rate limits)
- [x] Not done as the plan had it: "no embeddings, lexical only" as the public mode; the vectors stay by default, `--no-embeddings` drops them (D137)
- [x] Tests: pytest (profiles, bundles, the public server, no torch imported in a fresh process), vitest (the nav without the personal pages), Playwright over `bsim fixture-serve --public`
- [x] The image built and run (M157, 2026-11-10): `docker build` (1.23 GB), `docker run` with a fresh `--no-nc` bundle (862 MB) mounted read-only: healthy, `/api/books` answers, the personal endpoints 404; `web/e2e-docker/` smoke (15 pages, both languages, desktop and phone, axe; the personal pages off): 62 passed
- [ ] Publishing: the user's decision (DEPLOY.md, step 4)

✔ A public copy runs the same code with nothing personal and without the ML libraries; what it leaves out says so instead of failing.

## M143: Hard negatives from the model's own mistakes (§16.80, D133; proposed K10)
- [x] `train.supervised.negatives_from: bm25 | self | self_ce`, `self_system`, `ce_max` (`train/negatives.py`): the anchor's list chosen; a screen asked once per pair, a refused draw drawn again in rounds (`redrawn`); without one the draws unchanged
- [x] `self_ce`'s screen (`ce_accept`): the cross-encoder's stored `fused_rerank` scores reused, the others computed on first need and the GPU freed after
- [x] Variants `self`, `self_ce`; `supervision_experiments.noise: m115_seed14` (M127's bar, 0.0007), the rule fixed before training
- [x] The negatives mined on the real data: `self` differs from BM25's in 99.6 % of rows; the cross-encoder flags 2.9 % of its draws (2.6 % of BM25's negatives); `self_ce` redraws 2,205 rows
- [x] Tests: the screen and redraws, asked once, the fallback, unchanged draws without a screen, the stored scores reused, the list per `negatives_from` (pytest)
- [x] `train-simcse` / `train-sup` adopted after the dry run (the `train` config and the code changed; no retrain)
- [x] Train `self` (about 2.5 h, GPU: `bsim supervision-exp --only self`; 2026-11-11, 2 h 21 min, best step 830, dev recall@10 0.219)
- [x] Train `self_ce` (about 2.5 h, GPU: `--only self_ce`; 2026-11-11, 2 h 17 min, best step 800, dev recall@10 0.219)
- [x] Dev tables in RESULTS.md and the adoption verdict: neither adopted; `negatives_from` stays `bm25`

## M142: Label queue (§16.79, D132; proposed K9)
- [x] `api/label_queue.py`: the fused verse discoveries between two train-split books, by `|lex_rank − sem_rank|` (beyond the lists = k + 1), ties to the stronger pair and the two sides in turn; labelled pairs left out; the pool read once per DB
- [x] API `GET /labels/queue` (`?side=`, `?limit=`; `no-store`; 503 `splits_missing`), with the counts and the real train pairs against `labels.min_train`
- [x] Training: `extra_pairs: [labels]` (`train/pairs.py`): your real train pairs as positives, kept from the negatives in any split; your not train pairs as hard negatives where eligible (`train/negatives.py`, `from_label`); refused below `labels.min_train`; variant `supervision_experiments.variants.labels`
- [x] Viewer: Labels → What to judge next (`/labels?tab=queue`): both verses, each list's rank, the label buttons (`mode: queue`), Compare, Next pairs; English and Hebrew
- [x] Tests: the ranking, the turns, the side filter (pytest); the endpoint over the fixture DB (which now has a book split); the pairs and negatives from a labels file, the minimum; the page (vitest); fixture e2e (a pair judged from the queue) and smoke on the real build (axe)
- [ ] Train the `labels` variant: waits for 30 real train pairs, and a GPU run (about 2.5 h) the user starts (`bsim supervision-exp --only labels`)

✔ The queue puts first the pairs one list ranks first and the other does not list (Gen 1:1 / Jer 23:24 by the words, Exod 33:13 / 33:17 by meaning), only between train books; a judgement there can train the model and the dev golds stay clean.
