// Interface strings of the Overview pages (map, network, style, evaluation) and Names: English
// first, Hebrew typed against it (see ../en.ts).

import type { EntityKind } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

const typeEn: Record<string, string> = { verse: 'Verse', chapter: 'Chapter', pericope: 'Pericope', parasha: 'Parasha' }
const pluralHe: Record<string, string> = { verse: 'פסוקים', chapter: 'פרקים', pericope: 'פיסקאות', parasha: 'פרשות' }
const pluralEn: Record<string, string> = { verse: 'verses', chapter: 'chapters', pericope: 'pericopes', parasha: 'parashot' }
/** Hebrew plural nouns of these unit types are feminine (פיסקאות, פרשות). */
const feminine = (type: string) => type === 'pericope' || type === 'parasha'
const versesHe = (n: number) => countHe(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים')

export const ovEn = {
  chart: {
    scatterKeys: (label: string) => `${label}. Use the arrow keys to step through points and Enter to open one.`,
    heatmapKeys: (label: string) => `${label}. Use the arrow keys to move between cells and Enter to select one.`,
  },

  map: {
    title: 'Map of the Tanakh',
    lede: (type: string) =>
      `Every ${(typeEn[type] ?? type).toLowerCase()} placed by meaning (t-SNE of the semantic embeddings): nearby points read alike. Colours are thematic clusters, labelled by the lemmas they use most.`,
    colourBy: 'Colour by',
    clusters: 'Clusters',
    sections: 'Torah / Prophets / Writings',
    scatter: 'Map of units by meaning',
    point: (n: number) => `· ${countEn(n, 'verse', 'verses')} · click to open`,
    idle: 'Hover a point; click to open the unit.',
    affinity: 'How the books talk to each other',
    affinityLede:
      "Cross-book verse pairs in each other's fused top 10, relative to what the books' sizes would predict (lift; darker = more). Click a cell for its strongest pairs.",
    bookOrder: 'Book order',
    related: 'Related books together',
    canon: 'Canon order',
    cell: (a: string, b: string, n: number, lift: string) => `${a} ↔ ${b}: ${n} pairs, lift ${lift}`,
    heatmap: 'Book by book affinity',
    examples: 'Book pair examples',
    strongest: (a: string, b: string) => `${a} ↔ ${b}: strongest pairs`,
    noPairs: 'No pairs.',
  },

  network: {
    title: 'Network of echoes',
    ledeLinked: (type: string) =>
      `Every ${(typeEn[type] ?? type).toLowerCase()} is linked to those in its top ten (lexical and semantic, fused), consecutive ones of the same book left out. `,
    communities: 'Communities',
    ledeCommunities: ' are groups that echo each other more than the rest — often across books; ',
    central: 'central',
    ledeCentral: ' passages (PageRank) are the ones the rest of the Bible echoes most.',
    nCommunities: (n: number) => `${n} communities`,
    graph: 'Community graph',
    mostEchoedLabel: 'Most echoed passages',
    mostEchoed: (type: string) => `Most echoed ${pluralEn[type] ?? `${type}s`}`,
    moreBooks: (n: number) => ` +${n} books`,
    communityOf: (n: number, type: string) => `Community of ${n} ${pluralEn[type] ?? `${type}s`}`,
    legend:
      'Circle size: centrality · colour: Torah / Prophets / Writings · lines: echoes (darker = stronger). Select a passage to open it.',
    graphLabel: 'Passages and their echoes',
    node: (label: string, partners: number) => `${label}, ${partners} echoes`,
    nodeTitle: (label: string, partners: number, cross: number) =>
      `${label} · ${partners} echoes · ${Math.round(cross * 100)}% to other books`,
    allPassages: (n: number) => `All ${n} passages, most central first`,
    passage: 'Passage',
    echoes: 'Echoes',
    otherBooks: 'Other books',
    otherBooksTitle: 'Share of the echo weight that reaches other books',
    community: 'Community',
  },

  style: {
    title: 'Style',
    lede: 'How the books write, not what they say: rates of the 100 most frequent lemmas and of grammatical forms (wayyiqtol, participles, the article, suffixes …), compared across books and chapters. These are descriptive statistics; groupings are not claims about authorship or date.',
    book: 'Book',
    highlight: '— highlight a book —',
    axis: (pc: number) => `${pc === 1 ? 'Horizontal' : 'Vertical'} axis`,
    variance: (v: number) => `(${Math.round(v * 100)} % of the variance)`,
    positive: (pc: number): string => (pc === 1 ? 'right' : 'up'),
    negative: (pc: number): string => (pc === 1 ? 'left' : 'down'),
    distance: 'Stylistic distance between books',
    distanceLede:
      "Burrows' Delta (mean difference of feature z-scores); darker = more alike. Books are ordered so similar styles sit together.",
    delta: (a: string, b: string, d: string) => `${a} ↔ ${b}: Delta ${d}`,
    profile: 'Book style profile',
    words: (n: number) => `(${numEn(n)} words)`,
    more: 'Uses more than other books',
    less: 'Uses less',
    closest: 'Closest in style:',
    feature: (f: string, rate: string, z: string) => `${f}: ${rate} per 100 words, z ${z}`,
    scatter: 'Chapters by style',
    point: (n: number) => ` · ${n} words`,
    idle: 'Each point is a chapter (≥ 150 words). Hover for its name; click to open it.',
  },

  seams: {
    label: 'Style shifts',
    title: 'Where the style changes',
    lede: (words: number) =>
      `At every verse boundary the ${words} words before and after are compared (Burrows' Delta of the same features). Peaks above the dashed line — the highest a book with shuffled verse order reaches 19 times in 20 — are seams: a new genre, language, speaker or source. Descriptive, not a claim about authorship.`,
    none: (inBook: boolean) => `No significant seams${inBook ? ' in this book' : ''}.`,
    shift: (shift: string, threshold: string) => `shift ${shift} (threshold ${threshold})`,
    chart: 'Style shift along the book',
  },

  eval: {
    title: 'Evaluation',
    lede: "How often each system ranks a known cross-reference near the top. The gold pairs are Sefaria's links between verses or passages of the Tanakh, split by book so that no tested book was seen in training. Known links are a biased sample (famous parallels are over-represented), so low scores also mean many hits are simply unlinked. Rows marked ",
    served: 'served',
    ledeEnd: ' are the systems this viewer shows.',
    none: 'No evaluation has been run yet (`bsim eval`).',
    splitLabel: (name: string) => `${name} split`,
    splits: {
      dev: 'Development books (used to choose models and weights)',
      test: 'Test books (evaluated once, after every choice was made)',
    } as Record<string, string>,
    evaluated: (date: string) => `Evaluated ${date}`,
    caption: (type: string, gold?: { queries: number; pairs: number }) =>
      `${typeEn[type] ?? type}s${gold ? ` · ${gold.queries} queries, ${gold.pairs} gold pairs` : ''}`,
    openbible: (split: string) => `A second opinion: OpenBible cross-references (${split} books)`,
    openbibleLede: 'Crowd-voted cross-references (at least 5 votes), compared with the Sefaria gold on the same queries.',
    openbibleShare: (pct: string) => ` Only ${pct}% of OpenBible pairs are also Sefaria links.`,
    againstOpenbible: 'Against OpenBible',
    againstSefaria: 'Against Sefaria (same books)',
    system: 'System',
    servedAs: (modes: string) => `served: ${modes}`,
  },

  names: {
    title: 'People and places',
    lede: 'Every name in the text. Whether a name is a person or a place comes from Strong\'s lexicon where it says, and is otherwise guessed from its contexts (directional ־ה, "city of", "son of", "and X said"); tribes and peoples count as people. Two names are linked when they share verses more often than their frequencies predict.',
    kindSource: { lexicon: "from Strong's lexicon", cues: 'guessed from context' } as Record<'lexicon' | 'cues', string>,
    kind: 'Kind',
    all: 'All',
    kinds: { person: 'Person', place: 'Place', mixed: 'Person / place', unclear: 'Unclear' } satisfies Record<EntityKind, string>,
    book: 'Book',
    allBooks: 'All books',
    find: 'Find a name',
    list: 'Names',
    noMatch: 'No names match.',
    count: (total: number, inBook: boolean, page: number, pages: number) =>
      `${numEn(total)} names${inBook ? ' in this book' : ''} · page ${page} of ${pages}`,
    details: 'Name details',
    mentions: (n: number, verses: number) => `${n} mentions in ${verses} verses · first `,
    last: ', last ',
    allVerses: 'all verses',
    where: 'Where',
    perBook: 'Verses per book',
    bookCount: (book: string, n: number) => `${book}: ${n} verses`,
    appearsWith: 'Appears with',
    together: (n: number, chance: string) => `${n} verses together (${chance} by chance)`,
    ego: (name: string) => `Names appearing with ${name}`,
    show: (name: string) => `${name}: show this name`,
  },
}

export const ovHe: typeof ovEn = {
  chart: {
    scatterKeys: (label: string) => `${label}. מקשי החצים עוברים בין הנקודות ו־Enter פותח אחת מהן.`,
    heatmapKeys: (label: string) => `${label}. מקשי החצים עוברים בין התאים ו־Enter בוחר אחד מהם.`,
  },

  map: {
    title: 'מפת התנ״ך',
    lede: (type: string) =>
      `כל ה${pluralHe[type] ?? type} ${feminine(type) ? 'ממוקמות' : 'ממוקמים'} לפי משמעות (t-SNE של השיכונים הסמנטיים): נקודות קרובות דומות בתוכנן. הצבעים הם אשכולות נושאיים, המסומנים לפי הערכים השכיחים בהם.`,
    colourBy: 'צביעה לפי',
    clusters: 'אשכולות',
    sections: 'תורה / נביאים / כתובים',
    scatter: 'מפת היחידות לפי משמעות',
    point: (n: number) => `· ${versesHe(n)} · לחיצה לפתיחה`,
    idle: 'העבירו את העכבר מעל נקודה; לחיצה פותחת את היחידה.',
    affinity: 'איך הספרים מדברים זה עם זה',
    affinityLede:
      'זוגות פסוקים מספרים שונים שכל אחד מהם בעשרה המובילים המשולבים של האחר, ביחס למה שגודל הספרים צופה (lift; כהה יותר = יותר). לחיצה על תא מציגה את הזוגות החזקים ביותר שלו.',
    bookOrder: 'סדר הספרים',
    related: 'ספרים קרובים יחד',
    canon: 'סדר הקאנון',
    cell: (a: string, b: string, n: number, lift: string) => `${a} ↔ ${b}: ${n} זוגות, lift ${lift}`,
    heatmap: 'קרבה בין ספר לספר',
    examples: 'דוגמאות לזוג הספרים',
    strongest: (a: string, b: string) => `${a} ↔ ${b}: הזוגות החזקים ביותר`,
    noPairs: 'אין זוגות.',
  },

  network: {
    title: 'רשת ההדים',
    ledeLinked: (_type: string) =>
      'כל יחידה מקושרת ליחידות שבעשר המובילות שלה (מילולי וסמנטי, משולב), בלי יחידות סמוכות מאותו ספר. ',
    communities: 'קהילות',
    ledeCommunities: ' הן קבוצות המהדהדות זו את זו יותר משאר הטקסט — לעתים קרובות בין ספרים; קטעים ',
    central: 'מרכזיים',
    ledeCentral: ' (PageRank) הם אלה ששאר המקרא מהדהד יותר מכול.',
    nCommunities: (n: number) => `${numHe(n)} קהילות`,
    graph: 'גרף הקהילה',
    mostEchoedLabel: 'הקטעים המהדהדים ביותר',
    mostEchoed: (type: string) =>
      feminine(type)
        ? `ה${pluralHe[type]} המהדהדות ביותר`
        : `ה${pluralHe[type] ?? type} המהדהדים ביותר`,
    moreBooks: (n: number) => ` ועוד ${countHe(n, 'ספר אחד', 'שני ספרים', 'ספרים')}`,
    communityOf: (n: number, type: string) => `קהילה של ${n} ${pluralHe[type] ?? type}`,
    legend: 'גודל העיגול: מרכזיות · צבע: תורה / נביאים / כתובים · קווים: הדים (כהה יותר = חזק יותר). בחירה בקטע פותחת אותו.',
    graphLabel: 'קטעים וההדים שלהם',
    node: (label: string, partners: number) => `${label}, ${partners} הדים`,
    nodeTitle: (label: string, partners: number, cross: number) =>
      `${label} · ${partners} הדים · ${Math.round(cross * 100)}% לספרים אחרים`,
    allPassages: (n: number) => `כל ${n} הקטעים, המרכזיים תחילה`,
    passage: 'קטע',
    echoes: 'הדים',
    otherBooks: 'ספרים אחרים',
    otherBooksTitle: 'חלק משקל ההדים המגיע לספרים אחרים',
    community: 'קהילה',
  },

  style: {
    title: 'סגנון',
    lede: 'איך הספרים כותבים, לא מה הם אומרים: שיעורי 100 הערכים השכיחים ביותר ושל צורות דקדוקיות (וי״ו ההיפוך, בינוני, ה״א הידיעה, כינויים חבורים …), בהשוואה בין ספרים ופרקים. אלה נתונים תיאוריים; הקבצות אינן טענות על מחבר או על תיארוך.',
    book: 'ספר',
    highlight: '— הדגשת ספר —',
    axis: (pc: number) => (pc === 1 ? 'הציר האופקי' : 'הציר האנכי'),
    variance: (v: number) => `(${Math.round(v * 100)}% מהשונות)`,
    positive: (pc: number) => (pc === 1 ? 'ימין' : 'למעלה'),
    negative: (pc: number) => (pc === 1 ? 'שמאל' : 'למטה'),
    distance: 'מרחק סגנוני בין הספרים',
    distanceLede: 'הדלתא של ברוז (ההפרש הממוצע בציוני z של התכונות); כהה יותר = דומה יותר. הספרים מסודרים כך שסגנונות דומים סמוכים.',
    delta: (a: string, b: string, d: string) => `${a} ↔ ${b}: דלתא ${d}`,
    profile: 'הפרופיל הסגנוני של הספר',
    words: (n: number) => `(${numHe(n)} מילים)`,
    more: 'משתמש יותר מספרים אחרים',
    less: 'משתמש פחות',
    closest: 'הקרובים ביותר בסגנון:',
    feature: (f: string, rate: string, z: string) => `${f}: ${rate} ל־100 מילים, z ${z}`,
    scatter: 'פרקים לפי סגנון',
    point: (n: number) => ` · ${n} מילים`,
    idle: 'כל נקודה היא פרק (150 מילים לפחות). העבירו את העכבר לשמו; לחיצה פותחת אותו.',
  },

  seams: {
    label: 'מעברי סגנון',
    title: 'היכן הסגנון משתנה',
    lede: (words: number) =>
      `בכל גבול בין פסוקים מושוות ${words} המילים שלפניו ושאחריו (הדלתא של ברוז על אותן תכונות). שיאים מעל הקו המקווקו — הגובה שספר בסדר פסוקים מעורבב מגיע אליו 19 פעמים מתוך 20 — הם מעברי סגנון: סוגה, לשון, דובר או מקור חדשים. תיאורי, לא טענה על מחבר.`,
    none: (inBook: boolean) => `אין מעברי סגנון מובהקים${inBook ? ' בספר הזה' : ''}.`,
    shift: (shift: string, threshold: string) => `שינוי ${shift} (סף ${threshold})`,
    chart: 'שינוי הסגנון לאורך הספר',
  },

  eval: {
    title: 'הערכה',
    lede: 'באיזו תדירות כל מערכת מדרגת הפניה ידועה בראש הרשימה. זוגות הזהב הם הקישורים של ספריא בין פסוקים או קטעים בתנ״ך, מחולקים לפי ספר כך שאף ספר נבדק לא נראה באימון. הקישורים הידועים הם מדגם מוטה (מקבילות מפורסמות מיוצגות ביתר), ולכן ציון נמוך פירושו גם שתוצאות רבות פשוט אינן מקושרות. שורות המסומנות ',
    served: 'מוצג',
    ledeEnd: ' הן המערכות שהממשק מציג.',
    none: 'עדיין לא הורצה הערכה (`bsim eval`).',
    splitLabel: (name: string) => `חלוקת ${name}`,
    splits: {
      dev: 'ספרי הפיתוח (לבחירת מודלים ומשקלים)',
      test: 'ספרי המבחן (נבדקו פעם אחת, אחרי שכל הבחירות נעשו)',
    },
    evaluated: (date: string) => `נבדק ב־${date}`,
    caption: (type: string, gold?: { queries: number; pairs: number }) =>
      `${pluralHe[type] ?? type}${gold ? ` · ${gold.queries} שאילתות, ${gold.pairs} זוגות זהב` : ''}`,
    openbible: (split: string) =>
      `דעה שנייה: הפניות OpenBible (ספרי ${split === 'dev' ? 'הפיתוח' : split === 'test' ? 'המבחן' : split})`,
    openbibleLede: 'הפניות שנבחרו בהצבעת הקהל (5 קולות לפחות), בהשוואה לזהב של ספריא על אותן שאילתות.',
    openbibleShare: (pct: string) => ` רק ${pct}% מזוגות OpenBible הם גם קישורים בספריא.`,
    againstOpenbible: 'מול OpenBible',
    againstSefaria: 'מול ספריא (אותם ספרים)',
    system: 'מערכת',
    servedAs: (modes: string) => `מוצג: ${modes}`,
  },

  names: {
    title: 'אנשים ומקומות',
    lede: 'כל השמות שבטקסט. אם שם הוא אדם או מקום — לפי מילון סטרונג כשהוא קובע, ואחרת מנחשים מהקשריו (ה״א המגמה, ״עיר״, ״בן״, ״ויאמר״); שבטים ועמים נחשבים אנשים. שני שמות מקושרים כשהם חולקים פסוקים יותר משצופות השכיחויות שלהם.',
    kindSource: { lexicon: 'לפי מילון סטרונג', cues: 'לפי ההקשר' },
    kind: 'סוג',
    all: 'הכול',
    kinds: { person: 'אדם', place: 'מקום', mixed: 'אדם / מקום', unclear: 'לא ברור' },
    book: 'ספר',
    allBooks: 'כל הספרים',
    find: 'חיפוש שם',
    list: 'שמות',
    noMatch: 'אין שמות מתאימים.',
    count: (total: number, inBook: boolean, page: number, pages: number) =>
      `${numHe(total)} שמות${inBook ? ' בספר הזה' : ''} · עמוד ${page} מתוך ${pages}`,
    details: 'פרטי השם',
    mentions: (n: number, verses: number) => `${n} אזכורים ב־${versesHe(verses)} · ראשון: `,
    last: ', אחרון: ',
    allVerses: 'כל הפסוקים',
    where: 'היכן',
    perBook: 'פסוקים בכל ספר',
    bookCount: (book: string, n: number) => `${book}: ${versesHe(n)}`,
    appearsWith: 'מופיע עם',
    together: (n: number, chance: string) => `${versesHe(n)} יחד (${chance} במקרה)`,
    ego: (name: string) => `שמות המופיעים עם ${name}`,
    show: (name: string) => `${name}: הצגת השם`,
  },
}
