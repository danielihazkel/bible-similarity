// Interface strings of the Overview pages (map, network, style, evaluation) and Names: English
// first, Hebrew typed against it (see ../en.ts).

import type { EntityKind, NameKind, PlaceKind } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

const typeEn: Record<string, string> = { verse: 'Verse', chapter: 'Chapter', pericope: 'Pericope', parasha: 'Parasha' }
const pluralHe: Record<string, string> = { verse: 'פסוקים', chapter: 'פרקים', pericope: 'פיסקאות', parasha: 'פרשות' }
const pluralEn: Record<string, string> = { verse: 'verses', chapter: 'chapters', pericope: 'pericopes', parasha: 'parashot' }
/** Hebrew plural nouns of these unit types are feminine (פיסקאות, פרשות). */
const feminine = (type: string) => type === 'pericope' || type === 'parasha'
const versesHe = (n: number) => countHe(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים')

const goldEn: Record<string, string> = { sefaria: 'Sefaria', openbible: 'OpenBible', etcbc: 'ETCBC' }
const goldHe: Record<string, string> = { sefaria: 'ספריא', openbible: 'OpenBible', etcbc: 'ETCBC' }

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
    lists: 'Lists',
    listsLegend: 'Share of the verses in a list (genealogies, itineraries, rolls of names): darker = more.',
    listShare: (n: number, of: number) => `· ${countEn(n, 'verse', 'verses')} of ${of} in a list`,
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
    etcbc: (split: string) => `A third opinion: ETCBC's parallel passages (${split} books)`,
    etcbcLede: (parallels: number, formulas: number, max: number) =>
      `Verse pairs whose text is nearly the same (ETCBC parallels notebook, similarity ≥ 75 %): ${numEn(parallels)} parallels. The ${numEn(formulas)} pairs among verses with more than ${numEn(max)} partners are formulas and list items (וידבר יהוה אל משה לאמר has 157) and are left out.`,
    etcbcShare: (sef: string, ob: string) => ` ${sef}% of them are also Sefaria links and ${ob}% OpenBible references: the commentary rarely links a verse to its near-copy.`,
    againstEtcbc: 'Against ETCBC',
    etcbcBands: (bands: string) => `Fused recall@10 by similarity: ${bands}.`,
    etcbcCoverage: (fused: string, phrase: string, seq: string, prec: string, nSeq: number) =>
      `All parallels (every split): ${fused}% are in the fused top 10, ${phrase}% share a phrase, ${seq}% lie in a strong sequence; ${prec}% of the ${numEn(nSeq)} verse pairs of the strong sequences are ETCBC parallels (the rest are reworded).`,
    // the encoder retrained with more supervision (§16.41)
    supLabel: 'More supervision',
    sup: (split: string) => `More supervision: the semantic model retrained with other golds' pairs (${split} books)`,
    supLede: (metric: string, noise: string) =>
      `The semantic model learns from Sefaria's links between training books, which lean towards the famous ones. Each variant retrains it the same way with more pairs between training books (OpenBible's cross-references, ETCBC's parallels), or with only another seed (${noise}) to show what a retrain alone moves. The cells give the gain in ${metric} over the model the experiment started from (Sefaria's pairs only), with a 95% bootstrap interval over the development queries; the development and test books are never trained on. The rule was fixed before any training: a variant is adopted only if the fused list gains on OpenBible, with the interval above 0 and the gain larger than the retrain alone moves, and loses nothing significant on Sefaria or ETCBC. `,
    supChosen: (name: string) => `Passed: ${name}, now the semantic model in use.`,
    supNone: 'No variant passed, so the model in use stays.',
    supList: { fused: 'Fused list (lexical + semantic)', semantic: 'Semantic list alone' } as Record<string, string>,
    supCaption: (list: string, base: string, scores: string) => `${list} · gain over ${base} (${scores})`,
    supVariant: 'Variant',
    supRows: 'Training pairs (rows)',
    supAdopt: 'Passes the rule',
    supSource: (source: string, n: number) => `${goldEn[source] ?? source} ${numEn(n)}`,
    supCounts: (better: number, worse: number, queries: number) =>
      `${numEn(better)} queries better, ${numEn(worse)} worse, of ${numEn(queries)}`,
    supYes: 'yes',
    supNo: 'no',
    // newer encoders against the model in use (§16.48)
    encLabel: 'Newer encoders',
    enc: (split: string) => `Newer encoders against the model in use (${split} books)`,
    encLede: (metric: string, bar: string) =>
      `The semantic model is BEREL, a BERT trained on rabbinic Hebrew, fine-tuned on the cross-references. Two kinds of candidate: DictaBERT (modern Hebrew, base and large) fine-tuned the same way, with the same pairs and seed; and multilingual embedders used as they are, never trained here. The cells give the gain in ${metric} over the model in use, with a 95% bootstrap interval over the development queries. The rule was fixed before any candidate ran: a candidate is adopted only if the fused list gains on Sefaria with the interval above 0 and the gain larger than ${bar} (the most a retrain with another seed moved), and loses nothing significant on OpenBible or ETCBC. `,
    encChosen: (name: string) => `Passed: ${name}.`,
    encNone: 'No candidate passed, so BEREL stays.',
    encList: { fused: 'Newer encoders: fused list', semantic: 'Newer encoders: semantic list alone' } as Record<string, string>,
    encCandidate: 'Candidate',
    encModel: 'Model',
    encKind: { trained: 'fine-tuned here', zero_shot: 'used as it is' } as Record<string, string>,
    encZero: (ref: string, scores: string) => `Zero-shot: the multilingual embedders against ${ref}, the zero-shot system already built (semantic list; ${ref} ${scores})`,
    encZeroLabel: 'Zero-shot embedders against the one already built',
    // a third fusion list for chapters and pericopes (§16.50)
    unitLabel: 'A third list for chapters and pericopes',
    unit: (split: string) => `A third list for chapters and pericopes (${split} books)`,
    unitLede: (metric: string) =>
      `Chapters and pericopes are found by fusing a word list (TF-IDF) with the semantic list. Three candidates for a third list, each built from what the verses of two passages share: the parallel sequences that run through them, the phrases they share, and each verse's own top ten (fused). Each is added at three weights; the weight is chosen on one half of the development queries and scored on the other (cross-fitted), and the gain in ${metric} over the fused list is given with a 95% bootstrap interval. The rule was fixed before the first run: a list is adopted for a unit type only if its cross-fitted gain on Sefaria has the interval above 0 and it loses nothing significant on OpenBible or ETCBC.`,
    unitVerdict: (type: string, family: string | null) =>
      family ? `${pluralEn[type] ?? type}: the ${family} list passed the rule and is now fused.` : `${pluralEn[type] ?? type}: no list passed.`,
    unitCaption: (type: string, scores: string) => `${typeEn[type] ?? type}s · gain over the fused list (${scores})`,
    unitAloneCaption: (type: string) => `${typeEn[type] ?? type}s · each list alone, not fused`,
    unitFamily: 'Third list',
    unitSelected: 'Best on Sefaria',
    unitCrossFitted: 'Cross-fitted (Sefaria)',
    unitList: 'List',
    unitUnits: 'Passages with a list',
    unitFamilies: { sequences: 'parallel sequences', phrases: 'shared phrases', hits: 'verse hits' } as Record<string, string>,
    gold: goldEn,
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
    nameKinds: { person: 'a person', people: 'a people', location: 'a place', landform: 'a landform', water: 'water' } satisfies Record<NameKind, string>,
    sdbhKind: (kind: string) => `In SDBH’s domains, mostly ${kind}.`,
    sites: 'On the ground',
    sitesLede: 'Where the places this name stands for lie: each mention matched to a place by STEPBible’s TIPNR, located by OpenBible.info’s best-voted identification. One name may be several places.',
    placeKinds: { town: 'Town', region: 'Region', landform: 'Landform', water: 'Water' } satisfies Record<PlaceKind, string>,
    siteVerses: (n: number) => countEn(n, 'verse', 'verses'),
    coords: (lat: number, lon: number) => `${Math.abs(lat).toFixed(2)}° ${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lon).toFixed(2)}° ${lon >= 0 ? 'E' : 'W'}`,
    votes: (score: number) => `identification voted ${numEn(score)} / 1,000`,
    contested: (share: number) => `a second site has ${Math.round(share * 100)}% of its votes`,
    tipnrPoint: 'TIPNR’s point, not voted on',
    unlocated: 'not located',
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
    lists: 'רשימות',
    listsLegend: 'חלק הפסוקים שבתוך רשימה (יחסים, מסעות, רשימות שמות): כהה יותר = יותר.',
    listShare: (n: number, of: number) => `· ${versesHe(n)} מתוך ${of} ברשימה`,
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
    etcbc: (split: string) =>
      `דעה שלישית: הקטעים המקבילים של ETCBC (ספרי ${split === 'dev' ? 'הפיתוח' : split === 'test' ? 'המבחן' : split})`,
    etcbcLede: (parallels: number, formulas: number, max: number) =>
      `זוגות פסוקים שנוסחם כמעט זהה (מחברת המקבילות של ETCBC, דמיון 75% ומעלה): ${numHe(parallels)} מקבילות. ${numHe(formulas)} הזוגות בין פסוקים שיש להם יותר מ־${numHe(max)} בני זוג הם נוסחאות ופריטי רשימה (לוידבר יהוה אל משה לאמר יש 157) ואינם נכללים.`,
    etcbcShare: (sef: string, ob: string) => ` ${sef}% מהם הם גם קישורים בספריא ו־${ob}% הפניות OpenBible: הפרשנות כמעט אינה מקשרת פסוק להעתקו.`,
    againstEtcbc: 'מול ETCBC',
    etcbcBands: (bands: string) => `החזרה@10 של המשולב לפי דמיון: ${bands}.`,
    etcbcCoverage: (fused: string, phrase: string, seq: string, prec: string, nSeq: number) =>
      `כל המקבילות (בכל החלוקות): ${fused}% נמצאות בעשרה הראשונים של המשולב, ${phrase}% חולקות צירוף, ${seq}% נמצאות ברצף חזק; ${prec}% מ־${numHe(nSeq)} זוגות הפסוקים של הרצפים החזקים הם מקבילות ETCBC (השאר מנוסחים מחדש).`,
    supLabel: 'פיקוח נוסף',
    sup: (split: string) =>
      `פיקוח נוסף: המודל הסמנטי מאומן מחדש עם זוגות מתקני זהב אחרים (ספרי ${split === 'dev' ? 'הפיתוח' : split === 'test' ? 'המבחן' : split})`,
    supLede: (metric: string, noise: string) =>
      `המודל הסמנטי לומד מהקישורים של ספריא בין ספרי האימון, הנוטים אל המפורסמים. כל גרסה מאמנת אותו מחדש באותה דרך עם זוגות נוספים בין ספרי האימון (הפניות OpenBible, מקבילות ETCBC), או רק עם זרע אקראי אחר (${noise}), כדי להראות כמה אימון חוזר לבדו מזיז. התאים מראים את השיפור ב־${metric} לעומת המודל שממנו יצא הניסוי (זוגות ספריא בלבד), עם רווח bootstrap של 95% על שאילתות הפיתוח; ספרי הפיתוח והמבחן אינם משמשים לאימון לעולם. הכלל נקבע לפני כל אימון: גרסה מאומצת רק אם הרשימה המשולבת משתפרת מול OpenBible, כשהרווח מעל 0 והשיפור גדול ממה שאימון חוזר לבדו מזיז, ואינה מפסידה באופן מובהק מול ספריא או ETCBC. `,
    supChosen: (name: string) => `עברה את הכלל: ${name}, וזהו כעת המודל הסמנטי שבשימוש.`,
    supNone: 'אף גרסה לא עברה את הכלל, ולכן המודל הנוכחי נשאר.',
    supList: { fused: 'הרשימה המשולבת (מילונית + סמנטית)', semantic: 'הרשימה הסמנטית לבדה' },
    supCaption: (list: string, base: string, scores: string) => `${list} · שיפור לעומת ${base} (${scores})`,
    supVariant: 'גרסה',
    supRows: 'זוגות אימון (שורות)',
    supAdopt: 'עוברת את הכלל',
    supSource: (source: string, n: number) => `${goldHe[source] ?? source} ${numHe(n)}`,
    supCounts: (better: number, worse: number, queries: number) =>
      `${numHe(better)} שאילתות השתפרו, ${numHe(worse)} הורעו, מתוך ${numHe(queries)}`,
    supYes: 'כן',
    supNo: 'לא',
    encLabel: 'מקודדים חדשים',
    enc: (split: string) => `מקודדים חדשים לעומת המודל שבשימוש (ספרי ${split === 'dev' ? 'הפיתוח' : split === 'test' ? 'המבחן' : split})`,
    encLede: (metric: string, bar: string) =>
      `המודל הסמנטי הוא BEREL, מודל BERT שאומן על עברית רבנית, ומכוונן על ההפניות. שני סוגי מועמדים: DictaBERT (עברית חדשה, בסיס וגדול) המכוונן באותה דרך, עם אותם זוגות ואותו זרע; ומקודדים רב־לשוניים כפי שהם, שאינם מאומנים כאן כלל. התאים מראים את השיפור ב־${metric} לעומת המודל שבשימוש, עם רווח bootstrap של 95% על שאילתות הפיתוח. הכלל נקבע לפני שרץ מועמד כלשהו: מועמד מאומץ רק אם הרשימה המשולבת משתפרת מול ספריא, כשהרווח מעל 0 והשיפור גדול מ־${bar} (המרב שאימון חוזר בזרע אחר הזיז), ואינה מפסידה באופן מובהק מול OpenBible או ETCBC. `,
    encChosen: (name: string) => `עבר את הכלל: ${name}.`,
    encNone: 'אף מועמד לא עבר את הכלל, ולכן BEREL נשאר.',
    encList: { fused: 'מקודדים חדשים: הרשימה המשולבת', semantic: 'מקודדים חדשים: הרשימה הסמנטית לבדה' },
    encCandidate: 'מועמד',
    encModel: 'מודל',
    encKind: { trained: 'מכוונן כאן', zero_shot: 'כפי שהוא' },
    encZero: (ref: string, scores: string) => `ללא אימון: המקודדים הרב־לשוניים לעומת ${ref}, המערכת ללא אימון שכבר בנויה (הרשימה הסמנטית; ${ref} ${scores})`,
    encZeroLabel: 'מקודדים ללא אימון לעומת זה שכבר בנוי',
    unitLabel: 'רשימה שלישית לפרקים ולפיסקאות',
    unit: (split: string) => `רשימה שלישית לפרקים ולפיסקאות (ספרי ${split === 'dev' ? 'הפיתוח' : split === 'test' ? 'המבחן' : split})`,
    unitLede: (metric: string) =>
      `פרקים ופיסקאות נמצאים בשילוב רשימת מילים (TF-IDF) עם הרשימה הסמנטית. שלושה מועמדים לרשימה שלישית, כל אחד בנוי ממה שפסוקי שני קטעים חולקים: הרצפים המקבילים העוברים בהם, הביטויים המשותפים להם, ועשרת המובילים (המשולבים) של כל פסוק. כל אחד מתווסף בשלושה משקלים; המשקל נבחר על חצי משאילתות הפיתוח ונמדד על החצי האחר (cross-fitting), והשיפור ב־${metric} לעומת הרשימה המשולבת מוצג עם רווח bootstrap של 95%. הכלל נקבע לפני ההרצה הראשונה: רשימה מאומצת לסוג יחידה רק אם השיפור שלה מול ספריא, ב־cross-fitting, עם רווח מעל 0, והיא אינה מפסידה באופן מובהק מול OpenBible או ETCBC.`,
    unitVerdict: (type: string, family: string | null) =>
      family ? `${pluralHe[type] ?? type}: הרשימה "${family}" עברה את הכלל ומשולבת עתה.` : `${pluralHe[type] ?? type}: אף רשימה לא עברה את הכלל.`,
    unitCaption: (type: string, scores: string) => `${pluralHe[type] ?? type} · שיפור לעומת הרשימה המשולבת (${scores})`,
    unitAloneCaption: (type: string) => `${pluralHe[type] ?? type} · כל רשימה לבדה, בלי שילוב`,
    unitFamily: 'רשימה שלישית',
    unitSelected: 'הטובה ביותר מול ספריא',
    unitCrossFitted: 'cross-fitting (ספריא)',
    unitList: 'רשימה',
    unitUnits: 'קטעים עם רשימה',
    unitFamilies: { sequences: 'רצפים מקבילים', phrases: 'ביטויים משותפים', hits: 'פגיעות פסוקים' } as Record<string, string>,
    gold: goldHe,
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
    nameKinds: { person: 'אדם', people: 'עם', location: 'מקום', landform: 'תוואי קרקע', water: 'מים' },
    sdbhKind: (kind: string) => `בתחומים של SDBH, על פי רוב: ${kind}.`,
    sites: 'על פני הארץ',
    sitesLede: 'היכן שוכנים המקומות שהשם הזה מציין: כל אזכור מותאם למקום לפי TIPNR של STEPBible, וממוקם לפי הזיהוי שקיבל הכי הרבה קולות ב־OpenBible.info. שם אחד יכול לציין כמה מקומות.',
    placeKinds: { town: 'עיר', region: 'אזור', landform: 'תוואי קרקע', water: 'מים' },
    siteVerses: (n: number) => versesHe(n),
    coords: (lat: number, lon: number) => `${Math.abs(lat).toFixed(2)}° ${lat >= 0 ? 'צפון' : 'דרום'}, ${Math.abs(lon).toFixed(2)}° ${lon >= 0 ? 'מזרח' : 'מערב'}`,
    votes: (score: number) => `הזיהוי קיבל ${numHe(score)} מתוך 1,000 קולות`,
    contested: (share: number) => `לאתר שני ${Math.round(share * 100)}% מקולותיו`,
    tipnrPoint: 'הנקודה של TIPNR, בלי הצבעה',
    unlocated: 'לא ממוקם',
  },
}
