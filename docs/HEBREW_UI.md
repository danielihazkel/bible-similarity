# The Hebrew interface: terms and conventions

The Hebrew catalogs (`web/src/i18n/he.ts`, `web/src/i18n/pages/he/`) are an interface language, not a translation (D54). The terms below were agreed in the 2026-11-05 review (DESIGN.md §16.89, D145, M155): Claude Opus 5.5 read every group beside its English, the owner accepted all 252 suggestions, and the same terms were then carried to the strings the review did not list. A new string uses these terms. The glossary (`pages/he/glossary.ts`) is the source for anything it defines.

## Terms

| English | Hebrew | Not |
|---|---|---|
| lemma | ערך מילוני (pl. ערכים מילוניים; masculine) | למה, למות |
| label (your judgement of a pair) | תווית, התוויות שלכם | סימון, תיוג |
| cross-reference | הפניה | (citations of scripture are ציטוטים) |
| citation (a formula of reference) | ציטוט | הפניה |
| resumptive repetition | חזרה מקשרת | חזרה מסגרת |
| reciprocal rank fusion | מיזוג לפי דרגה הפוכה | מיזוג דירוגים הדדי |
| rank | דרגה | דירוג |
| semantic | סמנטי | משמעות (as an adjective) |
| recall | החזר | החזרה |
| log-likelihood (G²) | יחס נראות לוגריתמי | יחס נראות |
| Benjamini–Hochberg | בנימיני–הוכברג | בנג׳מיני |
| Spearman's rho | rho של ספירמן | ρ, מקדם ספירמן |
| confidence interval | רווח סמך | רווח |
| paragraph (Masoretic pericope) | פיסקה | פרשה (a weekly parasha only) |
| phrase (a shared run of words) | צירוף | ביטוי, in the core and ranks |
| genealogy (a kind of list) | יוחסין | יחס |
| canon order | סדר הקאנון / סדר הכתובים | סדר הספרים |
| the Leningrad Codex | כתב יד לנינגרד | כתר (the Aleppo Codex) |
| atbash, albam | אתב״ש, אלב״ם | את״ב״ש, אל״ב״ם |
| Strong's number | מספר סטרונג | מספר הסטרונג |
| unattached (family tree) | ללא שיוך | בלי קשר |
| the map page | מקומות על המפה | מקומות במפה |
| synopses (the page) | סינופסיסים | סינופסיס |
| continue (the start page) | המשיכו מכאן | המשך |
| zoom (the control group) | הגדלה והקטנה | הגדלה (the zoom-in button) |
| pin (a page, a hit), pinned | נעיצה, נעוצים | הצמדה, מוצמדים (צמד is a pair) |
| the top bar | הסרגל העליון | סרגל הכלים |

## Conventions

- The reader is addressed in the plural: שלכם, ששפטתם, נסו.
- Chapter and verse in Hebrew numerals with a colon: תה׳ ו:ט, not ו 9.
- Quotation marks „…”, opening low and closing high, as elsewhere in a group.
- Plurals and numbers through `countHe` / `numHe` (one / two / many); never a JavaScript expression inside a template string.
- A word with a one-letter prefix before a number takes a maqaf: ב־3, ל־P.
- A scholar's name that is also a book of the Bible stays in Latin letters (Roth, not רות).
- Words a reader could take two ways get the longer form: כיוון השאילה, not מי שאל; מי שמספר אותו, not המספר (the narrator).
