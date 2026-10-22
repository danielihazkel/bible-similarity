// Interface strings of the dossier bar on a unit page: what every analysis found about this unit
// (DESIGN.md §10). English first, Hebrew typed against it.

import type { DossierKind } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

const fmtQ = (q: number) => (q < 0.001 ? '< 0.001' : q < 0.01 ? q.toFixed(3) : q.toFixed(2))

export const dosEn = {
  label: 'What the analyses found here',
  what: 'what the analyses found here',
  found: 'Found here:',
  none: 'Nothing found:',
  notComputed: 'Not computed in this build:',
  inChapter: ' (chapter)',
  /** a finding, with its count or value */
  chip: {
    phrases: (n: number) => countEn(n, 'shared phrase', 'shared phrases'),
    sequences: (n: number) => countEn(n, 'parallel run', 'parallel runs'),
    changes: (n: number) => countEn(n, 'word change in parallels', 'word changes in parallels'),
    borrowing: (n: number) => countEn(n, 'parallel with a borrowing estimate', 'parallels with a borrowing estimate'),
    wordplay: (n: number) => countEn(n, 'wordplay pair', 'wordplay pairs'),
    alliteration: (n: number) => countEn(n, 'alliteration candidate', 'alliteration candidates'),
    rhymes: (n: number) => countEn(n, 'rhyme run', 'rhyme runs'),
    typescenes: (n: number) => countEn(n, 'action sequence', 'action sequences'),
    discoveries: (n: number) => countEn(n, 'strong pair without a Sefaria link', 'strong pairs without a Sefaria link'),
    seams: (n: number) => countEn(n, 'style seam', 'style seams'),
    names: (n: number) => countEn(n, 'name', 'names'),
    labels: (n: number) => countEn(n, 'pair you labelled', 'pairs you labelled'),
    acrostic: (q: number) => `acrostic, q ${fmtQ(q)}`,
    structure: (q: number) => `inclusio / chiasm, q ${fmtQ(q)}`,
    dating: (score: number) => `late-language profile ${score.toFixed(2)}`,
    speech: (n: number, who: string | null) => `${countEn(n, 'quotation clause', 'quotation clauses')}${who ? `, mostly ${who}` : ''}`,
    voices: (who: string) => `the voice of ${who}`,
    network: (rank: number, of: number) => `echoes: number ${numEn(rank)} of ${numEn(of)}`,
    divisions: (n: number, key: string | null) =>
      n === 1 && key === 'turn'
        ? 'opens at an unmarked turn'
        : n === 1 && key === 'cut'
          ? 'a chapter start inside running text'
          : n === 1 && key === 'quiet'
            ? 'opens at a quiet paragraph break'
            : countEn(n, 'point where text and division disagree', 'points where text and division disagree'),
    ketiv: (n: number) => countEn(n, 'word written one way and read another', 'words written one way and read another'),
    citations: (n: number) => countEn(n, 'explicit citation', 'explicit citations'),
    allusions: (n: number) => countEn(n, 'passage sharing rare words', 'passages sharing rare words'),
    mirrors: (n: number) => countEn(n, 'mirrored order', 'mirrored orders'),
    echoes: (n: number) => countEn(n, 'directed echo with another book', 'directed echoes with other books'),
    meter: (net: number) => `lines fall like a lament (net ${net.toFixed(2)})`,
    roots: (n: number) => countEn(n, 'pair of words of one root', 'pairs of words of one root'),
    refrains: (n: number) => countEn(n, 'refrain', 'refrains'),
    psalms: (n: number) => countEn(n, 'psalm: its genre, form and turn', 'psalms: their genres, form and turns'),
    pentateuch: (n: number) => countEn(n, 'verse on the P-like side', 'verses on the P-like side'),
    dialogue: (n: number) => countEn(n, 'exchange between two speakers', 'exchanges between two speakers'),
    forms: (n: number) => countEn(n, 'graded numerical saying or list', 'graded numerical sayings and lists'),
    places: (n: number, top: string | null) => `${countEn(n, 'place', 'places')} on the map${top ? `, most named ${top}` : ''}`,
    people: (n: number, top: string | null) => `${countEn(n, 'person', 'people')} in the family tree${top ? `, most named ${top}` : ''}`,
    ciphers: (n: number, words: string | null, name: string | null) =>
      `${countEn(n, 'name read through atbash or albam', 'names read through atbash or albam')}${words && name ? ` (${words} read as ${name})` : ''}`,
    gematria: (n: number, texts: string | null, value: number | null, others: number | null) =>
      [
        value === null ? null : `letter value ${numEn(value)}${others ? `, as in ${countEn(others, 'other verse', 'other verses')}` : ', in no other verse'}`,
        n > 0 && texts ? `the tradition's values: ${texts}` : null,
      ]
        .filter(Boolean)
        .join(' · '),
  },
  /** the analysis's name, in the "nothing found" / "not computed" lines */
  kinds: {
    phrases: 'shared phrases',
    sequences: 'parallel runs',
    changes: 'word changes',
    borrowing: 'who borrowed',
    wordplay: 'wordplay',
    alliteration: 'alliteration',
    rhymes: 'rhyme',
    typescenes: 'action sequences',
    discoveries: 'unlinked strong pairs',
    seams: 'style seams',
    names: 'names',
    labels: 'your labels',
    acrostic: 'acrostic',
    structure: 'inclusio / chiasm',
    dating: 'language profile',
    speech: 'direct speech',
    voices: 'speaker voices',
    network: 'echo network',
    divisions: 'text and divisions',
    ketiv: 'ketiv and qere',
    citations: 'explicit citations',
    allusions: 'rare words shared',
    mirrors: 'mirrored order',
    echoes: 'who echoes whom',
    meter: 'falling lines',
    roots: 'words of one root',
    refrains: 'refrains',
    psalms: 'psalm form',
    pentateuch: 'P-like verses',
    dialogue: 'exchanges',
    forms: 'numerical sayings and lists',
    places: 'places on the map',
    people: 'people in the family tree',
    ciphers: 'atbash and albam',
    gematria: 'letter values',
  } as Record<DossierKind, string>,
}

export const dosHe: typeof dosEn = {
  label: 'מה מצאו הניתוחים כאן',
  what: 'ממצאי הניתוחים כאן',
  found: 'נמצא כאן:',
  none: 'לא נמצא:',
  notComputed: 'לא חושב בבנייה זו:',
  inChapter: ' (בפרק)',
  chip: {
    phrases: (n: number) => countHe(n, 'צירוף משותף אחד', 'שני צירופים משותפים', 'צירופים משותפים'),
    sequences: (n: number) => countHe(n, 'רצף מקביל אחד', 'שני רצפים מקבילים', 'רצפים מקבילים'),
    changes: (n: number) => countHe(n, 'שינוי מילה אחד במקבילות', 'שני שינויי מילים במקבילות', 'שינויי מילים במקבילות'),
    borrowing: (n: number) => countHe(n, 'מקבילה אחת עם הערכת שאילה', 'שתי מקבילות עם הערכת שאילה', 'מקבילות עם הערכת שאילה'),
    wordplay: (n: number) => countHe(n, 'משחק מילים אחד', 'שני משחקי מילים', 'משחקי מילים'),
    alliteration: (n: number) => countHe(n, 'מועמד אחד לאליטרציה', 'שני מועמדים לאליטרציה', 'מועמדים לאליטרציה'),
    rhymes: (n: number) => countHe(n, 'רצף חרוז אחד', 'שני רצפי חרוז', 'רצפי חרוז'),
    typescenes: (n: number) => countHe(n, 'רצף פעולות אחד', 'שני רצפי פעולות', 'רצפי פעולות'),
    discoveries: (n: number) => countHe(n, 'זוג חזק אחד בלי קישור בספריא', 'שני זוגות חזקים בלי קישור בספריא', 'זוגות חזקים בלי קישור בספריא'),
    seams: (n: number) => countHe(n, 'תפר סגנוני אחד', 'שני תפרים סגנוניים', 'תפרים סגנוניים'),
    names: (n: number) => countHe(n, 'שם אחד', 'שני שמות', 'שמות'),
    labels: (n: number) => countHe(n, 'זוג אחד שתייגתם', 'שני זוגות שתייגתם', 'זוגות שתייגתם'),
    acrostic: (q: number) => `אקרוסטיכון, q ${fmtQ(q)}`,
    structure: (q: number) => `מסגרת / כיאזמוס, q ${fmtQ(q)}`,
    dating: (score: number) => `פרופיל לשון מאוחרת ${score.toFixed(2)}`,
    speech: (n: number, who: string | null) => `${countHe(n, 'פסוקית ציטוט אחת', 'שתי פסוקיות ציטוט', 'פסוקיות ציטוט')}${who ? `, בעיקר ${who}` : ''}`,
    voices: (who: string) => `קולו של ${who}`,
    network: (rank: number, of: number) => `הדים: מקום ${numHe(rank)} מתוך ${numHe(of)}`,
    divisions: (n: number, key: string | null) =>
      n === 1 && key === 'turn'
        ? 'נפתח במפנה שאינו מסומן'
        : n === 1 && key === 'cut'
          ? 'תחילת פרק בתוך טקסט רציף'
          : n === 1 && key === 'quiet'
            ? 'נפתח בפרשה שקטה'
            : countHe(n, 'מקום אחד שבו הטקסט והחלוקה חלוקים', 'שני מקומות שבהם הטקסט והחלוקה חלוקים', 'מקומות שבהם הטקסט והחלוקה חלוקים'),
    ketiv: (n: number) => countHe(n, 'מילה אחת שנכתבת כך ונקראת אחרת', 'שתי מילים שנכתבות כך ונקראות אחרת', 'מילים שנכתבות כך ונקראות אחרת'),
    citations: (n: number) => countHe(n, 'הפניה מפורשת אחת', 'שתי הפניות מפורשות', 'הפניות מפורשות'),
    allusions: (n: number) => countHe(n, 'קטע אחד החולק מילים נדירות', 'שני קטעים החולקים מילים נדירות', 'קטעים החולקים מילים נדירות'),
    mirrors: (n: number) => countHe(n, 'סדר הפוך אחד', 'שני סדרים הפוכים', 'סדרים הפוכים'),
    echoes: (n: number) => countHe(n, 'הד מכוון אחד עם ספר אחר', 'שני הדים מכוונים עם ספרים אחרים', 'הדים מכוונים עם ספרים אחרים'),
    meter: (net: number) => `שורות יורדות כקינה (נטו ${net.toFixed(2)})`,
    roots: (n: number) => countHe(n, 'זוג מילים אחד מאותו שורש', 'שני זוגות מילים מאותו שורש', 'זוגות מילים מאותו שורש'),
    refrains: (n: number) => countHe(n, 'פזמון חוזר אחד', 'שני פזמונים חוזרים', 'פזמונים חוזרים'),
    psalms: (n: number) => countHe(n, 'מזמור אחד: סוגו, צורתו ומפנהו', 'שני מזמורים: סוגם, צורתם ומפנם', 'מזמורים: סוגם, צורתם ומפנם'),
    pentateuch: (n: number) => countHe(n, 'פסוק אחד בצד הדומה ל־P', 'שני פסוקים בצד הדומה ל־P', 'פסוקים בצד הדומה ל־P'),
    dialogue: (n: number) => countHe(n, 'שיחה אחת בין שני דוברים', 'שתי שיחות בין שני דוברים', 'שיחות בין שני דוברים'),
    forms: (n: number) => countHe(n, 'משל מספרי מדורג או רשימה', 'שני משלים מספריים או רשימות', 'משלים מספריים ורשימות'),
    places: (n: number, top: string | null) => `${countHe(n, 'מקום אחד', 'שני מקומות', 'מקומות')} במפה${top ? `, הנזכר ביותר ${top}` : ''}`,
    people: (n: number, top: string | null) => `${countHe(n, 'אדם אחד', 'שני אנשים', 'אנשים')} באילן היוחסין${top ? `, הנזכר ביותר ${top}` : ''}`,
    ciphers: (n: number, words: string | null, name: string | null) =>
      `${countHe(n, 'שם אחד הנקרא באת״ב״ש או באל״ב״ם', 'שני שמות הנקראים באת״ב״ש או באל״ב״ם', 'שמות הנקראים באת״ב״ש או באל״ב״ם')}${words && name ? ` (${words} נקרא ${name})` : ''}`,
    gematria: (n: number, texts: string | null, value: number | null, others: number | null) =>
      [
        value === null ? null : `ערך האותיות ${numHe(value)}${others ? `, כמו ב${others > 2 ? '־' : ''}${countHe(others, 'פסוק אחר', 'שני פסוקים אחרים', 'פסוקים אחרים')}` : ', ואין עוד פסוק כזה'}`,
        n > 0 && texts ? `ערכי המסורת: ${texts}` : null,
      ]
        .filter(Boolean)
        .join(' · '),
  },
  kinds: {
    phrases: 'צירופים משותפים',
    sequences: 'רצפים מקבילים',
    changes: 'שינויי מילים',
    borrowing: 'מי שאל',
    wordplay: 'משחקי מילים',
    alliteration: 'אליטרציה',
    rhymes: 'חרוז',
    typescenes: 'רצפי פעולות',
    discoveries: 'זוגות חזקים בלי קישור',
    seams: 'תפרים סגנוניים',
    names: 'שמות',
    labels: 'התיוגים שלכם',
    acrostic: 'אקרוסטיכון',
    structure: 'מסגרת / כיאזמוס',
    dating: 'פרופיל לשון',
    speech: 'דיבור ישיר',
    voices: 'קולות הדוברים',
    network: 'רשת ההדים',
    divisions: 'טקסט וחלוקות',
    ketiv: 'כתיב וקרי',
    citations: 'הפניות מפורשות',
    allusions: 'מילים נדירות משותפות',
    mirrors: 'סדר הפוך',
    echoes: 'מי מהדהד את מי',
    meter: 'שורות יורדות',
    roots: 'מילים מאותו שורש',
    refrains: 'פזמונים חוזרים',
    psalms: 'צורת המזמור',
    pentateuch: 'פסוקים דומים ל־P',
    dialogue: 'שיחות',
    forms: 'משלים מספריים ורשימות',
    places: 'מקומות במפה',
    people: 'אנשים באילן היוחסין',
    ciphers: 'את״ב״ש ואל״ב״ם',
    gematria: 'ערכי אותיות',
  },
}
