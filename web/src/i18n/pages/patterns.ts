// Interface strings of the Patterns pages: English first, Hebrew typed against it (see ../en.ts).
// Structure, Acrostics, Poetry (parallel halves, word pairs) and Wordplay (pairs, alliteration, rhyme).

import type { StructureSort, WordplayPair } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

type Basis = 'semantic' | 'lexical'
type StructureCol = 'semantic_chiasm_pct' | 'lexical_chiasm_pct' | 'semantic_inclusio_pct' | 'lexical_inclusio_pct'

export const patEn = {
  pageOf: (page: number, pages: number) => `page ${page} of ${pages}`,
  units: (n: number) => countEn(n, 'unit', 'units'),
  chapters: (n: number) => countEn(n, 'chapter', 'chapters'),
  pairs: (n: number) => countEn(n, 'pair', 'pairs'),
  cola: (n: number) => countEn(n, 'colon', 'cola'),
  runs: (n: number) => countEn(n, 'run', 'runs'),
  includeQ: 'Include q > 0.05',
  show: 'Show',
  kind: 'Kind',
  any: 'Any',
  view: 'View',

  structure: {
    title: 'Structure',
    lede: [
      'Units whose verses frame them (',
      'inclusio',
      ': the opening returns at the close) or mirror each other (',
      'chiasm',
      ': A B C … C′ B′ A′), each scored against random pairs of the same unit. Open a unit for its heatmap and Leitworte.',
    ],
    sorts: {
      semantic_chiasm: 'Chiasm (semantic)',
      lexical_chiasm: 'Chiasm (lexical)',
      semantic_inclusio: 'Inclusio (semantic)',
      lexical_inclusio: 'Inclusio (lexical)',
    } satisfies Record<StructureSort, string>,
    cols: {
      semantic_chiasm_pct: 'Chiasm sem',
      lexical_chiasm_pct: 'Chiasm lex',
      semantic_inclusio_pct: 'Inclusio sem',
      lexical_inclusio_pct: 'Inclusio lex',
    } satisfies Record<StructureCol, string>,
    sortBy: 'Sort by',
    atLeast: 'At least',
    minVerses: (n: number) => `${n} verses`,
    note: 'Percentiles are per unit; with thousands of units about 5 % reach the 95th by chance. The q column corrects for that (Benjamini–Hochberg over all units of the type): only units with q ≤ 0.05 stand out from chance.',
    empty: 'No scored units.',
    unit: 'Unit',
    verses: 'Verses',
    qTitle: 'Benjamini–Hochberg q of the sorted score',
    sevens: (leitworte: number, multiples: number, expected: number, ratio: string, divisors: string, range: string | null, below: number) =>
      `Sevens: of ${numEn(leitworte)} chapter Leitworte, ${multiples} occur a multiple of 7 times against ${expected} expected from words with similar counts (${ratio}×). Other divisors (${divisors}) show ${range ?? 'no data'}${below === 0 ? ', so nothing singles out 7.' : `; ${below} of them less than 7.`}`,
  },

  panel: {
    computing: 'Computing structure…',
    basis: 'Similarity basis',
    hints: {
      semantic: 'cosine of the semantic verse embeddings',
      lexical: 'cosine of idf-weighted lemma bags (shared rare words)',
    } satisfies Record<Basis, string>,
    verseByVerse: (hint: string) => `Verse × verse similarity: ${hint}.`,
    inclusio: 'Inclusio',
    inclusioHint: 'opening and closing verses echo each other',
    chiasm: 'Chiasm',
    chiasmHint: 'mirror pairs (1st ↔ last, 2nd ↔ second-to-last …) are more alike than other pairs at the same distance',
    note: 'Percentiles compare the unit with itself (random pairs of the same unit). Across thousands of units some reach the 95th by chance: treat them as leads to read.',
    echoes: 'Strongest internal echoes',
    leitworte: 'Leitworte',
    leitworteLede: 'Lemmas this unit uses far more than the rest of the Tanakh (log-likelihood). Click to highlight.',
    leitwortTitle: (count: number, expected: string, g2: string) => `${count} times here, ${expected} expected · G² ${g2}`,
    tooFew: 'Too few verses.',
    percentile: (p: number) => `${Math.round(p * 100)}th percentile`,
    meanMirror: 'mean mirror similarity ',
    heatmap: 'Verse-by-verse similarity heatmap; arrow keys move between cells',
    heatmapKey: 'Darker = more similar · outlined cells = mirror pairs',
  },

  acrostics: {
    title: 'Acrostics',
    lede: "Poems whose lines start with the letters of the alphabet in order: verse by verse (Psalm 145, Proverbs 31, Lamentations 1), half-verse by half-verse (Psalms 111–112) or in blocks of verses (Psalm 119, Lamentations 3) — and broken ones with letters missing or out of place (Psalms 9–10). For every chapter the longest run through the alphabet is found, a skipped letter costing one, and compared with the same chapter's lines shuffled.",
    check: (recall: number) => `Check: ${Math.round(recall * 100)}% of the acrostics scholars list are found with q ≤ 0.05.`,
    q: { '0.05': 'q ≤ 0.05 (significant)', '0.5': 'q ≤ 0.5 (candidates)', all: 'Every chapter' } as Record<string, string>,
    qTitle: 'Benjamini–Hochberg q over all chapters: the share of chance chains expected among chains this strong',
    empty: 'No chapters match these filters.',
    letters: (n: number, missing: number) => `${n} letters${missing > 0 ? `, ${missing} skipped` : ''}`,
    peAyin: ' · פ before ע',
    chain: (n: number, first: string, last: string, missing: number) =>
      `${n} letters in order from ${first} to ${last}, ${missing} skipped`,
    skipped: 'skipped',
  },

  poetry: {
    title: 'Parallel halves',
    unitsView: 'Parallel verses',
    pairsView: 'Word pairs',
    lede: "The accents divide every verse at its main pause (etnahta; oleh-ve-yored in Psalms, Proverbs and Job). In poetry the two halves restate each other: similar meaning, other words, the same grammar, balanced length. A model trained only on how the halves relate — Psalms, Proverbs and Job against narrative and law — scores every verse; the share of parallel verses shows poetry wherever it is, including poems embedded in prose.",
    heldOut: (aucs: string) => `Held-out accuracy (AUC on a poetic book the model did not see): ${aucs}`,
    includePoetic: 'Include Psalms, Proverbs, Job',
    includePoeticTitle: 'Psalms, Proverbs and Job: the books the model learned from',
    empty: 'No units match these filters.',
    ranked: (n: number, plural: string) => `${numEn(n)} ${plural}, most parallel first`,
    parallelVerses: 'Parallel verses',
    parallelTitle: 'Verses whose halves score as parallel',
    mean: 'Mean',
    meanTitle: "Mean probability over the unit's verses",
    verses: 'Verses',
    byBook: 'By book',
    perBook: 'Parallel verses per book',
    perBookLede: "Share of each book's verses with parallel halves; green = the poetic-accent books.",
  },

  wordPairs: {
    lede: 'Hebrew poets answer a word in the first half of a line with a fixed partner in the second: ארץ // תבל, יעקב // ישראל, צדיק // רשע. Counted over every line whose halves score as parallel (and pairs of verses that form one line), these are the lemma pairs found together across the halves far more often than their frequencies predict, in at least three chapters.',
    empty: 'No word pairs.',
    first: 'First half',
    second: 'Second half',
    lines: 'Lines',
    linesTitle: 'Parallel lines with the pair / expected by chance',
    reversed: 'Reversed',
    reversedTitle: 'The pair in the other order',
    examples: 'Examples',
  },

  wordplay: {
    title: 'Wordplay',
    pattern: 'Sound pattern',
    pairsView: 'Sound-alike words',
    alliteration: 'Alliteration',
    rhyme: 'Rhyme',
    kinds: {
      substitution: 'One letter changed',
      metathesis: 'Letters swapped',
      extension: 'One letter added',
    } satisfies Record<WordplayPair['kind'], string>,
    lede: 'Different words that sound alike, a few words apart: one consonant changed, two swapped or one added, with the same vowels — as in Isaiah 5:7, מִשְׁפָּט / מִשְׂפָּח and צְדָקָה / צְעָקָה. Rare words first: that is what makes the echo audible.',
    chance: (total: number, expected: number, more: number) =>
      `${numEn(total)} pairs; shuffling the word order within each chapter yields about ${numEn(expected)}, so roughly ${numEn(more)} are more than chance — read the list as candidates, not proofs.`,
    empty: 'No wordplay matches these filters.',
  },

  sound: {
    alliterationLede: 'Within one colon, content words that begin with the same sound (after their prefixes; ב / כ / פ count as one sound with or without dagesh): פַּחַד וָפַחַת וָפָח (Isa 24:17), סִירִים סְבֻכִים (Nah 1:10). Chance is measured per word shape, since grammar fixes many first letters (every wayyiqtol starts with י).',
    alliterationNote: 'No single colon stands out once all 45,000 are tested together, so this is a ranking of candidates (p per colon), not a list of findings.',
    empty: 'Nothing here.',
    ofWords: (n: number, p: string) => `of ${n} content words · p = ${p}`,
    rhymeLede: 'Three or more lines in a row ending alike, with different words: Job 10:8–11 (‑נִי, “me”), Psalm 104:29–30 (‑וּן). Biblical rhyme is mostly the rhyme of suffixes; each run is compared with how common its ending is at line ends.',
    rhymeEmpty: 'No rhymes for these filters.',
  },
}

export const patHe: typeof patEn = {
  pageOf: (page: number, pages: number) => `עמוד ${page} מתוך ${pages}`,
  units: (n: number) => countHe(n, 'יחידה אחת', 'שתי יחידות', 'יחידות'),
  chapters: (n: number) => countHe(n, 'פרק אחד', 'שני פרקים', 'פרקים'),
  pairs: (n: number) => countHe(n, 'זוג אחד', 'שני זוגות', 'זוגות'),
  cola: (n: number) => countHe(n, 'צלע אחת', 'שתי צלעות', 'צלעות'),
  runs: (n: number) => countHe(n, 'רצף אחד', 'שני רצפים', 'רצפים'),
  includeQ: 'כולל q > 0.05',
  show: 'הצגה',
  kind: 'סוג',
  any: 'הכול',
  view: 'תצוגה',

  structure: {
    title: 'מבנה',
    lede: [
      'יחידות שפסוקיהן ממסגרים אותן (',
      'מסגרת',
      ': הפתיחה חוזרת בסיום) או משקפים זה את זה (',
      'כיאזם',
      ': A B C … C′ B′ A′), כל אחת מול זוגות אקראיים מאותה יחידה. פתחו יחידה כדי לראות את מפת החום ואת המילים המנחות שלה.',
    ],
    sorts: {
      semantic_chiasm: 'כיאזם (סמנטי)',
      lexical_chiasm: 'כיאזם (מילולי)',
      semantic_inclusio: 'מסגרת (סמנטית)',
      lexical_inclusio: 'מסגרת (מילולית)',
    },
    cols: {
      semantic_chiasm_pct: 'כיאזם סמ׳',
      lexical_chiasm_pct: 'כיאזם מיל׳',
      semantic_inclusio_pct: 'מסגרת סמ׳',
      lexical_inclusio_pct: 'מסגרת מיל׳',
    },
    sortBy: 'מיון לפי',
    atLeast: 'לפחות',
    minVerses: (n: number) => `${n} פסוקים`,
    note: 'האחוזונים מחושבים לכל יחידה בנפרד; מתוך אלפי יחידות כ־5% מגיעות לאחוזון ה־95 במקרה. עמודת q מתקנת זאת (בנימיני–הוכברג על כל היחידות מאותו סוג): רק יחידות עם q ≤ 0.05 בולטות מעל המקרה.',
    empty: 'אין יחידות מדורגות.',
    unit: 'יחידה',
    verses: 'פסוקים',
    qTitle: 'q של בנימיני–הוכברג לציון שלפיו ממוין',
    sevens: (leitworte: number, multiples: number, expected: number, ratio: string, divisors: string, range: string | null, below: number) =>
      `שבע: מתוך ${numHe(leitworte)} מילים מנחות בפרקים, ${multiples} מופיעות מספר פעמים שהוא כפולה של 7, לעומת ${expected} הצפויות ממילים בשכיחות דומה (${ratio}×). מחלקים אחרים (${divisors}) מראים ${range ?? 'אין נתונים'}${below === 0 ? ', כך שאין דבר המייחד את 7.' : `; ${below} מהם פחות מ־7.`}`,
  },

  panel: {
    computing: 'מחשב את המבנה…',
    basis: 'בסיס הדמיון',
    hints: {
      semantic: 'קוסינוס של שיכוני הפסוקים הסמנטיים',
      lexical: 'קוסינוס של שקי ערכים במשקל idf (מילים נדירות משותפות)',
    },
    verseByVerse: (hint: string) => `דמיון פסוק מול פסוק: ${hint}.`,
    inclusio: 'מסגרת',
    inclusioHint: 'פסוקי הפתיחה והסיום מהדהדים זה את זה',
    chiasm: 'כיאזם',
    chiasmHint: 'זוגות המראה (ראשון ↔ אחרון, שני ↔ לפני אחרון …) דומים יותר מזוגות אחרים באותו מרחק',
    note: 'האחוזונים משווים את היחידה לעצמה (זוגות אקראיים מאותה יחידה). מתוך אלפי יחידות חלקן מגיעות לאחוזון ה־95 במקרה: ראו בהן כיווני קריאה.',
    echoes: 'ההדים הפנימיים החזקים ביותר',
    leitworte: 'מילים מנחות',
    leitworteLede: 'ערכים שהיחידה משתמשת בהם הרבה יותר משאר התנ״ך (יחס נראות). לחיצה מדגישה אותם.',
    leitwortTitle: (count: number, expected: string, g2: string) => `${count} פעמים כאן, ${expected} צפויות · G² ${g2}`,
    tooFew: 'מעט מדי פסוקים.',
    percentile: (p: number) => `אחוזון ${Math.round(p * 100)}`,
    meanMirror: 'דמיון מראה ממוצע ',
    heatmap: 'מפת חום של הדמיון פסוק מול פסוק; מקשי החצים עוברים בין התאים',
    heatmapKey: 'כהה יותר = דומה יותר · תאים מסומנים = זוגות מראה',
  },

  acrostics: {
    title: 'אקרוסטיכונים',
    lede: 'שירים ששורותיהם פותחות באותיות הא״ב לפי הסדר: פסוק אחר פסוק (תהלים קמה, משלי לא, איכה א), צלע אחר צלע (תהלים קיא–קיב) או בגושי פסוקים (תהלים קיט, איכה ג) — וגם שבורים, שחסרות בהם אותיות או שהן שלא במקומן (תהלים ט–י). בכל פרק נמצא הרצף הארוך ביותר לאורך הא״ב, כשכל אות חסרה עולה נקודה, ומושווה לשורות אותו פרק בסדר מעורבב.',
    check: (recall: number) => `בדיקה: ${Math.round(recall * 100)}% מהאקרוסטיכונים שמונים החוקרים נמצאים עם q ≤ 0.05.`,
    q: { '0.05': 'q ≤ 0.05 (מובהקים)', '0.5': 'q ≤ 0.5 (מועמדים)', all: 'כל הפרקים' },
    qTitle: 'q של בנימיני–הוכברג על כל הפרקים: שיעור השרשראות המקריות הצפוי מבין השרשראות החזקות כמו זו',
    empty: 'אין פרקים המתאימים לסינון.',
    letters: (n: number, missing: number) => `${n} אותיות${missing > 0 ? `, ${missing} חסרות` : ''}`,
    peAyin: ' · פ לפני ע',
    chain: (n: number, first: string, last: string, missing: number) =>
      `${n} אותיות לפי הסדר מ־${first} עד ${last}, ${missing} חסרות`,
    skipped: 'חסרה',
  },

  poetry: {
    title: 'צלעות מקבילות',
    unitsView: 'פסוקים מקבילים',
    pairsView: 'זוגות מילים',
    lede: 'הטעמים מחלקים כל פסוק בהפסק העיקרי שלו (אתנחתא; עולה ויורד בתהלים, משלי ואיוב). בשירה שתי הצלעות חוזרות זו על זו: משמעות דומה, מילים אחרות, אותו דקדוק, אורך מאוזן. מודל שלמד רק את היחס בין הצלעות — תהלים, משלי ואיוב מול סיפור וחוק — מדרג כל פסוק; שיעור הפסוקים המקבילים מראה שירה בכל מקום שהיא, גם שירים המשובצים בפרוזה.',
    heldOut: (aucs: string) => `דיוק על נתונים שלא נראו (AUC על ספר שירי שהמודל לא ראה): ${aucs}`,
    includePoetic: 'כולל תהלים, משלי, איוב',
    includePoeticTitle: 'תהלים, משלי ואיוב: הספרים שמהם המודל למד',
    empty: 'אין יחידות המתאימות לסינון.',
    ranked: (n: number, plural: string) => `${numHe(n)} ${plural}, המקבילים ביותר תחילה`,
    parallelVerses: 'פסוקים מקבילים',
    parallelTitle: 'פסוקים שצלעותיהם מדורגות כמקבילות',
    mean: 'ממוצע',
    meanTitle: 'ההסתברות הממוצעת על פני פסוקי היחידה',
    verses: 'פסוקים',
    byBook: 'לפי ספר',
    perBook: 'פסוקים מקבילים בכל ספר',
    perBookLede: 'שיעור הפסוקים בכל ספר שצלעותיהם מקבילות; ירוק = ספרי טעמי אמ״ת.',
  },

  wordPairs: {
    lede: 'משוררי המקרא עונים על מילה בצלע הראשונה בבת זוג קבועה בצלע השנייה: ארץ // תבל, יעקב // ישראל, צדיק // רשע. בספירה על כל שורה שצלעותיה מדורגות כמקבילות (ועל זוגות פסוקים היוצרים שורה אחת), אלה זוגות הערכים המופיעים יחד משני צדי השורה הרבה יותר משכיחותם מנבאת, בשלושה פרקים לפחות.',
    empty: 'אין זוגות מילים.',
    first: 'צלע ראשונה',
    second: 'צלע שנייה',
    lines: 'שורות',
    linesTitle: 'שורות מקבילות עם הזוג / הצפוי במקרה',
    reversed: 'הפוך',
    reversedTitle: 'הזוג בסדר ההפוך',
    examples: 'דוגמאות',
  },

  wordplay: {
    title: 'משחקי לשון',
    pattern: 'דפוס צליל',
    pairsView: 'מילים בעלות צליל דומה',
    alliteration: 'אליטרציה',
    rhyme: 'חריזה',
    kinds: {
      substitution: 'אות אחת הוחלפה',
      metathesis: 'אותיות התחלפו',
      extension: 'אות אחת נוספה',
    },
    lede: 'מילים שונות בעלות צליל דומה, במרחק מילים ספורות: עיצור אחד הוחלף, שניים התחלפו או אחד נוסף, באותם תנועות — כמו בישעיהו ה:ז, מִשְׁפָּט / מִשְׂפָּח וצְדָקָה / צְעָקָה. המילים הנדירות תחילה: הן שעושות את ההד לשמיע.',
    chance: (total: number, expected: number, more: number) =>
      `${numHe(total)} זוגות; ערבוב סדר המילים בתוך כל פרק נותן כ־${numHe(expected)}, כך שבערך ${numHe(more)} הם מעבר למקרה — קראו את הרשימה כמועמדים, לא כהוכחות.`,
    empty: 'אין משחקי לשון המתאימים לסינון.',
  },

  sound: {
    alliterationLede: 'בתוך צלע אחת, מילות תוכן הפותחות באותו צליל (אחרי התחיליות; ב / כ / פ נחשבות לצליל אחד עם דגש או בלעדיו): פַּחַד וָפַחַת וָפָח (ישעיהו כד:יז), סִירִים סְבֻכִים (נחום א:י). המקרה נמדד לפי תבנית המילה, כי הדקדוק קובע אותיות פותחות רבות (כל ויקטל פותח ב־י).',
    alliterationNote: 'אף צלע לא בולטת לבדה כשכל 45,000 נבדקות יחד, ולכן זהו דירוג של מועמדים (p לכל צלע), לא רשימת ממצאים.',
    empty: 'אין כאן דבר.',
    ofWords: (n: number, p: string) => `מתוך ${n} מילות תוכן · p = ${p}`,
    rhymeLede: 'שלוש שורות רצופות או יותר המסתיימות באותו צליל, במילים שונות: איוב י:ח–יא (‑נִי, "אותי"), תהלים קד:כט–ל (‑וּן). החריזה המקראית היא בעיקר חריזת סיומות; כל רצף מושווה לשכיחות הסיומת שלו בסופי שורות.',
    rhymeEmpty: 'אין חריזות המתאימות לסינון.',
  },
}
