// Interface strings of the Findings page: each analysis's tested claim and its verdict (DESIGN.md
// §10, `/findings`). English first, Hebrew typed against it. Each text reads its numbers from the
// API, so it states what the current build found; wording that depends on a direction branches.

import type { FindingKey } from '../../api/types'
import { numEn, numHe, pct } from '../fmt'

type V = Record<string, number | null>
const n = (v: V, k: string) => v[k] ?? 0
const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const x2 = (r: number) => r.toFixed(2)
const x3 = (r: number) => r.toFixed(3)

export const findEn = {
  title: 'Findings',
  lede: (alpha: number) =>
    `What each analysis set out to test, and what the data say, with the numbers that decide it. A claim holds when its test passes at p ≤ ${alpha}; the verdicts are recomputed with every build, and each links to the page with the evidence.`,
  noData: 'No analysis has been computed in this build: run `bsim all`, then `bsim build-db`.',
  groups: {
    holds: { title: 'Borne out', hint: 'Above chance, or the check passes' },
    fails: { title: 'Not borne out', hint: 'No better than chance, or the data point the other way' },
    lead: { title: 'Leads, not findings', hint: 'Candidates no test yet separates from chance' },
  },
  items: {
    acrostics: {
      title: 'Alphabetic acrostics',
      text: (v: V) =>
        `${numEn(n(v, 'found'))} chapters run through the alphabet beyond chance; they include ${pct(n(v, 'recall'))} of the acrostics scholars list, and nothing else.`,
    },
    divisions: {
      title: 'Where the text divides',
      text: (v: V) =>
        `The scribes' paragraph breaks fall where the text itself turns: open breaks score ${x2(n(v, 'open'))} and closed ones ${x2(n(v, 'closed'))} on a scale where chance is ${x2(n(v, 'null'))} and unmarked verse ends ${x2(n(v, 'unmarked'))} (p ${fp(n(v, 'p'))}).`,
    },
    dating: {
      title: 'A late-language profile',
      text: (v: V) =>
        `Trained without Samuel, Kings and Chronicles, the profile finds the Chronicles side later in ${numEn(n(v, 'later'))} of ${numEn(n(v, 'pairs'))} parallel passages (p ${fp(n(v, 'p'))}): the same content in two states of the language. Each book left out in turn, it tells the late books from the early at AUC ${x2(n(v, 'auc'))}.`,
    },
    borrowing: {
      title: 'Who borrowed',
      text: (v: V) =>
        `Language and spelling name the borrower that scholars accept in ${numEn(n(v, 'agree'))} of ${numEn(n(v, 'n'))} parallels they decide, each book pair held out in turn (${numEn(n(v, 'unclear'))} undecided; p ${fp(n(v, 'p'))}).`,
    },
    citations: {
      title: 'Explicit citations',
      text: (v: V) =>
        `“As the LORD commanded Moses” points to the command it carries out: ${pct(n(v, 'share'))} resolve to one source, against ${pct(n(v, 'null'))} of random verses (p ${fp(n(v, 'p'))}). Of the ${numEn(n(v, 'others'))} other formulas, ${numEn(n(v, 'others_held'))} do better than chance.`,
    },
    voices: {
      title: 'Speaker voices',
      text: (v: V) =>
        `${numEn(n(v, 'significant'))} of ${numEn(n(v, 'speakers'))} speakers talk unlike the other speakers of their own books; with the speakers shuffled, ${numEn(n(v, 'calibration'))} do.`,
    },
    clauses: {
      title: 'Mirrored clauses',
      text: (v: V) =>
        `${n(v, 'poetry') > n(v, 'prose') ? 'Poetry reverses the order of two parallel clauses more often than prose' : 'Poetry does not reverse two parallel clauses more often than prose'}: ${pct(n(v, 'poetry'))} of ${numEn(n(v, 'poetry_n'))} pairs against ${pct(n(v, 'prose'))} of ${numEn(n(v, 'prose_n'))} (p ${fp(n(v, 'p'))}).`,
    },
    meter: {
      title: 'The falling lament line',
      text: (v: V) =>
        `Do the lines of Lamentations 1–4 fall — a longer member, then a shorter one (3:2), the lament's line? Net fall ${x2(n(v, 'mean'))} against ${x2(n(v, 'pool_mean'))} for other poetry under the same accents (p ${fp(n(v, 'p'))}; against Psalms, Proverbs and Job p ${fp(n(v, 'poetic_p'))}). Lamentations 5, a lament in even lines, falls more than ${pct(n(v, 'control_pct'))} of that poetry.`,
    },
    cognate: {
      title: 'A verb and a noun of one root',
      text: (v: V) =>
        `Does a verb take a noun of its own root nearby (ויחלם חלום, “he dreamt a dream”) by choice? ${numEn(n(v, 'observed'))} such pairs within three words, against ${n(v, 'expected').toFixed(0)} with the content words of each chapter shuffled (${n(v, 'ratio').toFixed(1)}×, p ${fp(n(v, 'p'))}).`,
    },
    echoes: {
      title: 'Who echoes whom',
      text: (v: V) =>
        `Where the spelling of a parallel points to its borrower, the language profile points the same way in ${numEn(n(v, 'agree'))} of ${numEn(n(v, 'n'))} (p ${fp(n(v, 'p'))}). ${numEn(n(v, 'backward'))} of the ${numEn(n(v, 'language'))} directions given by language alone run against the canon order: leads to read.`,
    },
    sevens: {
      title: 'Sevens',
      text: (v: V) =>
        n(v, 'largest') === 7
          ? `Key words come in multiples of 7 ${x2(n(v, 'ratio7'))} times as often as expected, more than for any other divisor.`
          : `Key words come in multiples of 7 ${x2(n(v, 'ratio7'))} times as often as expected — but every divisor shows an excess (10: ${x2(n(v, 'ratio10'))} times; the most, ${numEn(n(v, 'largest'))})${n(v, 'smallest') === 7 ? ', and 7 the least' : ''}. Nothing singles out 7.`,
    },
    chiasm: {
      title: 'Chiasm in repeated words',
      text: (v: V) =>
        n(v, 'share') < 0.5
          ? `Two words repeated in a verse come back in the same order more often than mirrored: ${numEn(n(v, 'verses_parallel'))} verses against ${numEn(n(v, 'verses_chiastic'))} (${pct(n(v, 'share'))} of pairs mirrored, p ${fp(n(v, 'p'))}). The figure exists, but it is not the habit.`
          : `Two words repeated in a verse come back mirrored more often than in the same order: ${numEn(n(v, 'verses_chiastic'))} verses against ${numEn(n(v, 'verses_parallel'))} (p ${fp(n(v, 'p'))}).`,
    },
    laments: {
      title: 'Chapters that speak of a lament',
      text: (v: V) =>
        `Do the ${numEn(n(v, 'n'))} chapters outside Lamentations that use the word קינה fall too? Net fall ${x2(n(v, 'mean'))} against ${x2(n(v, 'pool_mean'))} for other poetry (p ${fp(n(v, 'p'))}). The word also picks chapters that only mention a lament.`,
    },
    root_leitworte: {
      title: 'Leitworte counted by root',
      text: (v: V) =>
        `Do the Leitworte scholars name rank higher when a root's words are counted together? Of ${numEn(n(v, 'n'))}, ${numEn(n(v, 'by_root'))} are in their chapter's top ${numEn(n(v, 'top'))} by root and ${numEn(n(v, 'by_lemma'))} by word; the root ranks higher for ${numEn(n(v, 'better'))}. Counted by root, ${numEn(n(v, 'hidden'))} key roots appear that no single word shows: leads.`,
    },
    refrains: {
      title: 'Refrains',
      text: (v: V) =>
        `Are the refrains scholars name found among the phrases that come back nearby? ${numEn(n(v, 'found'))} of ${numEn(n(v, 'n'))}, among ${numEn(n(v, 'refrains'))} refrains against ${n(v, 'expected').toFixed(0)} runs as strong with each book's verses shuffled (${numEn(n(v, 'distinct'))} distinct).`,
    },
    refrain_regular: {
      title: 'Refrains at even intervals',
      text: (v: V) =>
        `Do refrains come back at even intervals? ${numEn(n(v, 'regular'))} of ${numEn(n(v, 'testable'))} testable refrains are more even than the same repeats placed at random in their span (${pct(n(v, 'share'))} against 5%, p ${fp(n(v, 'p'))}).`,
    },
    refrain_turns: {
      title: 'Refrains at the turns',
      text: (v: V) =>
        `Does a refrain stand where the text turns? The sharper gap next to a refrain's verse scores ${x2(n(v, 'observed'))} against ${x2(n(v, 'expected'))} for other verses of its span (p ${fp(n(v, 'p'))}, ${numEn(n(v, 'n'))} verses).`,
    },
    psalm_genres: {
      title: 'Psalm genres from their form',
      text: (v: V) =>
        `Does the counted form of the psalms (persons, imperatives, questions, words of distress and praise) recover Gunkel's genres? Clusters of the counts agree with the genres of ${numEn(n(v, 'labelled'))} psalms by NMI ${x3(n(v, 'nmi'))}, against ${x3(n(v, 'null'))} with the genres shuffled (p ${fp(n(v, 'p'))}).`,
    },
    psalm_forms: {
      title: 'The form of each genre',
      text: (v: V) =>
        `Does each genre show the form named in advance — laments "I" and distress, communal laments "we", hymns praise and plural imperatives and little "I"? ${numEn(n(v, 'held'))} of ${numEn(n(v, 'n'))} (largest q ${fp(n(v, 'max_q'))}).`,
    },
    lament_turn: {
      title: 'Where the lament turns',
      text: (v: V) =>
        `Does the point where a psalm's mood rises most fall at the turns scholars name (Ps 6:9, 13:6, 22:23 …)? ${numEn(n(v, 'found'))} of ${numEn(n(v, 'n'))} within a verse, against ${n(v, 'expected').toFixed(1)} for a random split (p ${fp(n(v, 'p'))}).`,
    },
    lament_turns: {
      title: 'Laments turn more than hymns',
      text: (v: V) =>
        `Do individual laments turn from distress to praise more often than hymns? ${numEn(n(v, 'laments'))} of ${numEn(n(v, 'n_laments'))} laments have a turn above chance, against ${numEn(n(v, 'hymns'))} of ${numEn(n(v, 'n_hymns'))} hymns (p ${fp(n(v, 'p'))}).`,
    },
    pentateuch_split: {
      title: "P from the Pentateuch's synonyms",
      text: (v: V) =>
        `Split in two by its choices between synonyms and its function words, without being told where P is, does Genesis–Numbers fall along the critics' P? On ${Math.round(n(v, 'agreement') * 100)}% of the verses: kappa ${x3(n(v, 'observed'))} against ${x3(n(v, 'null'))} for the split shifted within each book (p ${fp(n(v, 'p'))}).`,
    },
    pentateuch_genesis: {
      title: 'P within Genesis',
      text: (v: V) =>
        `In Genesis, where both sources tell stories, does the split still find P? Kappa ${x3(n(v, 'observed'))} against ${x3(n(v, 'null'))} (p ${fp(n(v, 'p'))}).`,
    },
    dialogue_deference: {
      title: '“Your servant” to God and to kings',
      text: (v: V) =>
        `Does speech addressed up, to God or to a king, call the speaker “your servant” (עבדך, אמתך) more than other speech does? ${x2(n(v, 'up'))} times per 1,000 words against ${x2(n(v, 'rest'))} (${numEn(n(v, 'up_count'))} in ${numEn(n(v, 'up_of'))} words; p ${fp(n(v, 'p'))}, the “up” label shuffled within each book).`,
    },
    dialogue_particle: {
      title: 'נא after a command to God or a king',
      text: (v: V) =>
        `Is a command to God or a king softened with נא more often than other commands? This is the politeness reading of נא, which is contested. ${pct(n(v, 'up'))} of those imperatives take it, against ${pct(n(v, 'rest'))} of the others (p ${fp(n(v, 'p'))}).`,
    },
    dialogue_last_word: {
      title: 'Who has the last word',
      text: (v: V) =>
        `In an exchange between God or a king and someone of lower rank, does the higher one speak last more often than their share of the turns would give? ${numEn(n(v, 'observed'))} of ${numEn(n(v, 'exchanges'))} exchanges, against ${n(v, 'expected').toFixed(1)} expected (p ${fp(n(v, 'p'))}).`,
    },
    pentateuch_names: {
      title: 'The divine names follow the split',
      text: (v: V) =>
        `Before Exodus 6, does the P-like side avoid יהוה, which it never saw? יהוה is ${Math.round(n(v, 'p_like') * 100)}% of its divine names against ${Math.round(n(v, 'non_p') * 100)}% on the other side (gap ${x3(n(v, 'observed'))} against ${x3(n(v, 'null'))}, p ${fp(n(v, 'p'))}).`,
    },
    forms_known: {
      title: 'Graded numerical sayings',
      text: (v: V) =>
        `Are the sayings that name a number and then the next (שלשה … וארבעה), as scholars list them, found? ${numEn(n(v, 'found'))} of ${numEn(n(v, 'n'))}, among ${numEn(n(v, 'sayings'))} verses with such a pair.`,
    },
    forms_chance: {
      title: 'A number and the next, more than chance?',
      text: (v: V) =>
        `Do a number and the next stand a few words apart more often than the book's own numbers placed at random give? ${numEn(n(v, 'observed'))} pairs against ${n(v, 'expected').toFixed(1)} (p ${fp(n(v, 'p'))}); most are “one … two” in measurements. Without “one … two”, described after the first run: ${numEn(n(v, 'without_observed'))} against ${n(v, 'without_expected').toFixed(1)} (p ${fp(n(v, 'without_p'))}).`,
    },
    forms_parallel: {
      title: 'Graded numbers stand in parallel lines',
      text: (v: V) =>
        `Is a verse with a number and the next more often a parallel line than one with another pair of numbers? ${pct(n(v, 'saying_parallel'))} of ${numEn(n(v, 'sayings'))} against ${pct(n(v, 'other_parallel'))} of ${numEn(n(v, 'others'))} (p ${fp(n(v, 'p'))}).`,
    },
    forms_lists: {
      title: 'Lists by the shape of their verses',
      text: (v: V) =>
        `Are the genealogies, itineraries and rolls named in advance found as runs of verses shaped alike? ${numEn(n(v, 'found'))} of ${numEn(n(v, 'n'))}, among ${numEn(n(v, 'lists'))} lists against ${n(v, 'expected').toFixed(1)} with each book's verses shuffled.`,
    },
    allusions: {
      title: 'Rare words over a few verses',
      text: (v: V) =>
        `${numEn(n(v, 'pairs'))} pairs of passages share three or more rare words; ${numEn(n(v, 'known'))} are known parallels, and the best new one has q ${x2(n(v, 'best_new_q'))} against shuffled verses.`,
    },
  } satisfies Record<FindingKey, { title: string; text: (v: V) => string }>,
}

export const findHe: typeof findEn = {
  title: 'ממצאים',
  lede: (alpha: number) =>
    `מה ביקש כל ניתוח לבדוק ומה אומרים הנתונים, עם המספרים המכריעים. טענה עומדת כשהמבחן שלה עובר ב־p ≤ ${alpha}; ההכרעות מחושבות מחדש בכל בנייה, וכל אחת מקשרת לעמוד שבו הראיות.`,
  noData: 'אף ניתוח לא חושב בבנייה זו: יש להריץ `bsim all` ואחר כך `bsim build-db`.',
  groups: {
    holds: { title: 'עומדות במבחן', hint: 'מעל המקרה, או שהבדיקה עוברת' },
    fails: { title: 'אינן עומדות במבחן', hint: 'לא טוב מן המקרה, או שהנתונים מצביעים לכיוון ההפוך' },
    lead: { title: 'כיווני חקירה, לא ממצאים', hint: 'מועמדים שאף מבחן עוד אינו מבדיל מן המקרה' },
  },
  items: {
    acrostics: {
      title: 'אקרוסטיכונים אלפביתיים',
      text: (v: V) =>
        `${numHe(n(v, 'found'))} פרקים עוברים על האלף־בית מעבר למקרה; הם כוללים ${pct(n(v, 'recall'))} מן האקרוסטיכונים שבספרות המחקר, ושום דבר אחר.`,
    },
    divisions: {
      title: 'היכן הטקסט מתחלק',
      text: (v: V) =>
        `הפרשיות של הסופרים נופלות היכן שהטקסט עצמו פונה: פתוחות מקבלות ${x2(n(v, 'open'))} וסתומות ${x2(n(v, 'closed'))}, בסולם שבו המקרה ${x2(n(v, 'null'))} וסופי פסוקים בלי סימן ${x2(n(v, 'unmarked'))} (p ${fp(n(v, 'p'))}).`,
    },
    dating: {
      title: 'פרופיל של לשון מאוחרת',
      text: (v: V) =>
        `כשהוא מאומן בלי שמואל, מלכים ודברי הימים, הפרופיל מוצא את צד דברי הימים מאוחר יותר ב־${numHe(n(v, 'later'))} מתוך ${numHe(n(v, 'pairs'))} קטעים מקבילים (p ${fp(n(v, 'p'))}): אותו תוכן בשני מצבים של הלשון. כשכל ספר מושאר בחוץ בתורו, הוא מבחין בין הספרים המאוחרים למוקדמים ב־AUC ${x2(n(v, 'auc'))}.`,
    },
    borrowing: {
      title: 'מי שאל ממי',
      text: (v: V) =>
        `הלשון והכתיב מצביעים על השואל המקובל במחקר ב־${numHe(n(v, 'agree'))} מתוך ${numHe(n(v, 'n'))} מקבילות שהם מכריעים בהן, כשכל זוג ספרים מושאר בחוץ בתורו (${numHe(n(v, 'unclear'))} לא הוכרעו; p ${fp(n(v, 'p'))}).`,
    },
    citations: {
      title: 'הפניות מפורשות',
      text: (v: V) =>
        `„כאשר צוה יהוה את משה” מצביע על הציווי שהוא מקיים: ${pct(n(v, 'share'))} מזוהים למקור אחד, לעומת ${pct(n(v, 'null'))} מפסוקים אקראיים (p ${fp(n(v, 'p'))}). מתוך ${numHe(n(v, 'others'))} הנוסחאות האחרות, ${numHe(n(v, 'others_held'))} טובות מן המקרה.`,
    },
    voices: {
      title: 'קולות הדוברים',
      text: (v: V) =>
        `${numHe(n(v, 'significant'))} מתוך ${numHe(n(v, 'speakers'))} דוברים מדברים אחרת משאר הדוברים בספריהם; בערבוב אקראי של הדוברים עוברים ${numHe(n(v, 'calibration'))}.`,
    },
    clauses: {
      title: 'פסוקיות במהופך',
      text: (v: V) =>
        `${n(v, 'poetry') > n(v, 'prose') ? 'השירה הופכת את סדר שתי פסוקיות מקבילות יותר מן הפרוזה' : 'השירה אינה הופכת את סדר שתי פסוקיות מקבילות יותר מן הפרוזה'}: ${pct(n(v, 'poetry'))} מתוך ${numHe(n(v, 'poetry_n'))} זוגות לעומת ${pct(n(v, 'prose'))} מתוך ${numHe(n(v, 'prose_n'))} (p ${fp(n(v, 'p'))}).`,
    },
    meter: {
      title: 'שורת הקינה היורדת',
      text: (v: V) =>
        `האם שורות איכה א–ד יורדות — צלע ארוכה ואחריה קצרה (3:2), שורת הקינה? ירידה נטו ${x2(n(v, 'mean'))} לעומת ${x2(n(v, 'pool_mean'))} בשירה אחרת באותה מערכת טעמים (p ${fp(n(v, 'p'))}; מול תהלים, משלי ואיוב p ${fp(n(v, 'poetic_p'))}). איכה ה, קינה בשורות שקולות, יורדת יותר מ־${pct(n(v, 'control_pct'))} מאותה שירה.`,
    },
    cognate: {
      title: 'פועל ושם מאותו שורש',
      text: (v: V) =>
        `האם פועל לוקח שם מאותו שורש בסמוך לו (מושא פנימי: ויחלם חלום) מתוך בחירה? ${numHe(n(v, 'observed'))} זוגות כאלה בטווח שלוש מילים, לעומת ${n(v, 'expected').toFixed(0)} כשמילות התוכן של כל פרק מעורבבות (פי ${n(v, 'ratio').toFixed(1)}, p ${fp(n(v, 'p'))}).`,
    },
    echoes: {
      title: 'מי מהדהד את מי',
      text: (v: V) =>
        `היכן שכתיב המקבילה מצביע על השואל, פרופיל הלשון מצביע לאותו כיוון ב־${numHe(n(v, 'agree'))} מתוך ${numHe(n(v, 'n'))} (p ${fp(n(v, 'p'))}). ${numHe(n(v, 'backward'))} מתוך ${numHe(n(v, 'language'))} הכיוונים שנקבעו בלשון בלבד הולכים נגד סדר הקאנון: כיווני חקירה.`,
    },
    sevens: {
      title: 'שבע',
      text: (v: V) =>
        n(v, 'largest') === 7
          ? `מילים מנחות מופיעות בכפולות של 7 פי ${x2(n(v, 'ratio7'))} מן הצפוי, יותר מכל מחלק אחר.`
          : `מילים מנחות מופיעות בכפולות של 7 פי ${x2(n(v, 'ratio7'))} מן הצפוי — אבל כל מחלק מראה עודף (10: פי ${x2(n(v, 'ratio10'))}; הגדול ביותר, ${numHe(n(v, 'largest'))})${n(v, 'smallest') === 7 ? ', ול־7 הקטן ביותר' : ''}. שום דבר אינו מייחד את 7.`,
    },
    chiasm: {
      title: 'כיאזמוס במילים חוזרות',
      text: (v: V) =>
        n(v, 'share') < 0.5
          ? `שתי מילים החוזרות בפסוק שבות באותו סדר יותר מאשר במהופך: ${numHe(n(v, 'verses_parallel'))} פסוקים לעומת ${numHe(n(v, 'verses_chiastic'))} (${pct(n(v, 'share'))} מן הזוגות במהופך, p ${fp(n(v, 'p'))}). התבנית קיימת, אבל אינה ההרגל.`
          : `שתי מילים החוזרות בפסוק שבות במהופך יותר מאשר באותו סדר: ${numHe(n(v, 'verses_chiastic'))} פסוקים לעומת ${numHe(n(v, 'verses_parallel'))} (p ${fp(n(v, 'p'))}).`,
    },
    laments: {
      title: 'פרקים המדברים על קינה',
      text: (v: V) =>
        `האם גם ${numHe(n(v, 'n'))} הפרקים מחוץ לאיכה שבהם המילה קינה יורדים? ירידה נטו ${x2(n(v, 'mean'))} לעומת ${x2(n(v, 'pool_mean'))} בשירה אחרת (p ${fp(n(v, 'p'))}). המילה מאתרת גם פרקים שרק מזכירים קינה.`,
    },
    root_leitworte: {
      title: 'מילים מנחות לפי שורש',
      text: (v: V) =>
        `האם המילים המנחות שהמחקר מונה מדורגות גבוה יותר כשמילות השורש נספרות יחד? מתוך ${numHe(n(v, 'n'))}, ${numHe(n(v, 'by_root'))} נמצאות בין ${numHe(n(v, 'top'))} המובילות בפרקן לפי שורש ו־${numHe(n(v, 'by_lemma'))} לפי מילה; השורש מדורג גבוה יותר ב־${numHe(n(v, 'better'))}. בספירה לפי שורש מופיעים ${numHe(n(v, 'hidden'))} שורשים מנחים שאף מילה בודדת אינה מראה: כיווני חקירה.`,
    },
    refrains: {
      title: 'פזמונים חוזרים',
      text: (v: V) =>
        `האם הפזמונים שהמחקר מונה נמצאים בין הצירופים החוזרים בסמיכות? ${numHe(n(v, 'found'))} מתוך ${numHe(n(v, 'n'))}, בין ${numHe(n(v, 'refrains'))} פזמונים לעומת ${n(v, 'expected').toFixed(0)} רצפים חזקים כמותם כשפסוקי כל ספר מעורבבים (${numHe(n(v, 'distinct'))} נפרדים).`,
    },
    refrain_regular: {
      title: 'פזמונים במרווחים שווים',
      text: (v: V) =>
        `האם פזמונים חוזרים במרווחים שווים? ${numHe(n(v, 'regular'))} מתוך ${numHe(n(v, 'testable'))} פזמונים שאפשר לבחון שווים יותר מאותן חזרות שהונחו באקראי בטווח שלהם (${pct(n(v, 'share'))} לעומת 5%, p ${fp(n(v, 'p'))}).`,
    },
    refrain_turns: {
      title: 'פזמונים במפנים',
      text: (v: V) =>
        `האם פזמון עומד היכן שהטקסט מתחלף? המעבר החד ליד פסוק של פזמון מקבל ${x2(n(v, 'observed'))} לעומת ${x2(n(v, 'expected'))} בפסוקים אחרים בטווח שלו (p ${fp(n(v, 'p'))}, ${numHe(n(v, 'n'))} פסוקים).`,
    },
    psalm_genres: {
      title: 'סוגי המזמורים מן הצורה',
      text: (v: V) =>
        `האם הצורה הנמנית של המזמורים (גופים, ציוויים, שאלות, מילות מצוקה ושבח) מחזירה את סוגי גונקל? אשכולות הספירות מתאימים לסוגים של ${numHe(n(v, 'labelled'))} מזמורים במידע הדדי מנורמל ${x3(n(v, 'nmi'))}, לעומת ${x3(n(v, 'null'))} כשהסוגים מעורבבים (p ${fp(n(v, 'p'))}).`,
    },
    psalm_forms: {
      title: 'הצורה של כל סוג',
      text: (v: V) =>
        `האם כל סוג מראה את הצורה שנקבעה מראש — בקינות "אני" ומצוקה, בקינות הציבור "אנחנו", במזמורי השבח שבח וציוויים ברבים ומעט "אני"? ${numHe(n(v, 'held'))} מתוך ${numHe(n(v, 'n'))} (ה־q הגדול ${fp(n(v, 'max_q'))}).`,
    },
    lament_turn: {
      title: 'היכן פונה הקינה',
      text: (v: V) =>
        `האם הנקודה שבה מצב הרוח של מזמור עולה הכי הרבה נופלת במפנים שהמחקר מונה (תה׳ ו 9, יג 6, כב 23 …)? ${numHe(n(v, 'found'))} מתוך ${numHe(n(v, 'n'))} בטווח פסוק, לעומת ${n(v, 'expected').toFixed(1)} לחלוקה אקראית (p ${fp(n(v, 'p'))}).`,
    },
    lament_turns: {
      title: 'קינות פונות יותר ממזמורי שבח',
      text: (v: V) =>
        `האם קינות יחיד פונות מן המצוקה אל השבח יותר ממזמורי שבח? ל־${numHe(n(v, 'laments'))} מתוך ${numHe(n(v, 'n_laments'))} קינות יש מפנה מעל המקרה, לעומת ${numHe(n(v, 'hymns'))} מתוך ${numHe(n(v, 'n_hymns'))} מזמורי שבח (p ${fp(n(v, 'p'))}).`,
    },
    pentateuch_split: {
      title: 'P מן הנרדפות של התורה',
      text: (v: V) =>
        `כשבראשית–במדבר מחולקים לשניים לפי הבחירה בין נרדפות ולפי מילות התפקוד, בלי שנאמר היכן P, האם החלוקה נופלת לאורך P של המבקרים? ב־${Math.round(n(v, 'agreement') * 100)}% מן הפסוקים: קאפה ${x3(n(v, 'observed'))} לעומת ${x3(n(v, 'null'))} לחלוקה מוזזת בתוך כל ספר (p ${fp(n(v, 'p'))}).`,
    },
    pentateuch_genesis: {
      title: 'P בתוך בראשית',
      text: (v: V) =>
        `בבראשית, ששני המקורות בה מספרים סיפורים, האם החלוקה עדיין מוצאת את P? קאפה ${x3(n(v, 'observed'))} לעומת ${x3(n(v, 'null'))} (p ${fp(n(v, 'p'))}).`,
    },
    dialogue_deference: {
      title: '„עבדך” אל האל ואל המלך',
      text: (v: V) =>
        `האם דיבור המופנה כלפי מעלה, אל האל או אל מלך, מכנה את הדובר „עבדך” (או „אמתך”) יותר משאר הדיבור? ${x2(n(v, 'up'))} פעמים לכל 1,000 מילים לעומת ${x2(n(v, 'rest'))} (${numHe(n(v, 'up_count'))} ב־${numHe(n(v, 'up_of'))} מילים; p ${fp(n(v, 'p'))}, כשהסימון „כלפי מעלה” מעורבב בתוך כל ספר).`,
    },
    dialogue_particle: {
      title: '„נא” אחרי ציווי אל האל או אל מלך',
      text: (v: V) =>
        `האם ציווי אל האל או אל מלך מרוכך ב„נא” יותר משאר הציוויים? זו קריאת הנימוס של „נא”, והיא שנויה במחלוקת. ${pct(n(v, 'up'))} מן הציוויים האלה באים עמה, לעומת ${pct(n(v, 'rest'))} מן האחרים (p ${fp(n(v, 'p'))}).`,
    },
    dialogue_last_word: {
      title: 'למי המילה האחרונה',
      text: (v: V) =>
        `בשיחה בין האל או מלך לבין מי שמעמדו נמוך ממנו, האם העליון מדבר אחרון יותר ממה שחלקו בתורי הדיבור היה נותן? ${numHe(n(v, 'observed'))} מתוך ${numHe(n(v, 'exchanges'))} שיחות, לעומת ${n(v, 'expected').toFixed(1)} צפויות (p ${fp(n(v, 'p'))}).`,
    },
    pentateuch_names: {
      title: 'שמות האל הולכים אחר החלוקה',
      text: (v: V) =>
        `לפני שמות ו, האם הצד הדומה ל־P נמנע מיהוה, שלא ראה? יהוה הוא ${Math.round(n(v, 'p_like') * 100)}% משמות האל שבו לעומת ${Math.round(n(v, 'non_p') * 100)}% בצד האחר (פער ${x3(n(v, 'observed'))} לעומת ${x3(n(v, 'null'))}, p ${fp(n(v, 'p'))}).`,
    },
    forms_known: {
      title: 'משלים מספריים מדורגים',
      text: (v: V) =>
        `האם המשלים המונים מספר ואחריו את הבא (שלשה … וארבעה), כפי שהמחקר מונה אותם, נמצאים? ${numHe(n(v, 'found'))} מתוך ${numHe(n(v, 'n'))}, בין ${numHe(n(v, 'sayings'))} פסוקים שיש בהם זוג כזה.`,
    },
    forms_chance: {
      title: 'מספר והבא אחריו, יותר מן המקרה?',
      text: (v: V) =>
        `האם מספר והבא אחריו עומדים במרחק מילים אחדות זה מזה יותר ממה שמספרי הספר עצמו, מפוזרים באקראי, נותנים? ${numHe(n(v, 'observed'))} זוגות לעומת ${n(v, 'expected').toFixed(1)} (p ${fp(n(v, 'p'))}); רובם ”אחד … שנים“ שבמידות. בלי ”אחד … שנים“, תיאור שנוסף אחרי הריצה הראשונה: ${numHe(n(v, 'without_observed'))} לעומת ${n(v, 'without_expected').toFixed(1)} (p ${fp(n(v, 'without_p'))}).`,
    },
    forms_parallel: {
      title: 'מספרים מדורגים עומדים בצלעות מקבילות',
      text: (v: V) =>
        `האם פסוק שיש בו מספר והבא אחריו הוא צלע מקבילה יותר מפסוק שיש בו זוג מספרים אחר? ${pct(n(v, 'saying_parallel'))} מתוך ${numHe(n(v, 'sayings'))} לעומת ${pct(n(v, 'other_parallel'))} מתוך ${numHe(n(v, 'others'))} (p ${fp(n(v, 'p'))}).`,
    },
    forms_lists: {
      title: 'רשימות לפי צורת פסוקיהן',
      text: (v: V) =>
        `האם היחסים, המסעות והמפקדים שנמנו מראש נמצאים כרצפים של פסוקים דומי צורה? ${numHe(n(v, 'found'))} מתוך ${numHe(n(v, 'n'))}, בין ${numHe(n(v, 'lists'))} רשימות לעומת ${n(v, 'expected').toFixed(1)} כשפסוקי כל ספר מעורבבים.`,
    },
    allusions: {
      title: 'מילים נדירות על פני פסוקים אחדים',
      text: (v: V) =>
        `${numHe(n(v, 'pairs'))} זוגות קטעים חולקים שלוש מילים נדירות או יותר; ${numHe(n(v, 'known'))} מהם מקבילות ידועות, ולחדש הטוב ביותר q ${x2(n(v, 'best_new_q'))} מול פסוקים מעורבבים.`,
    },
  },
}
