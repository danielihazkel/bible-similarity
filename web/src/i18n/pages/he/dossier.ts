// The Hebrew half of `../dossier.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { dosEn, fmtQ } from '../dossier'

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
    psalms: (n: number) => countHe(n, 'מזמור אחד: סוגו, צורתו ומפנהו', 'שני מזמורים: סוגיהם, צורתם ומפניהם', 'מזמורים: סוגיהם, צורתם ומפניהם'),
    pentateuch: (n: number) => countHe(n, 'פסוק אחד בצד הדומה ל־P', 'שני פסוקים בצד הדומה ל־P', 'פסוקים בצד הדומה ל־P'),
    dialogue: (n: number) => countHe(n, 'שיחה אחת בין שני דוברים', 'שתי שיחות בין שני דוברים', 'שיחות בין שני דוברים'),
    forms: (n: number) => countHe(n, 'משל מספרי מדורג או רשימה', 'שני משלים מספריים או רשימות', 'משלים מספריים ורשימות'),
    places: (n: number, top: string | null) => `${countHe(n, 'מקום אחד', 'שני מקומות', 'מקומות')} במפה${top ? `, הנזכר ביותר ${top}` : ''}`,
    people: (n: number, top: string | null) => `${countHe(n, 'אדם אחד', 'שני אנשים', 'אנשים')} באילן היוחסין${top ? `, הנזכר ביותר ${top}` : ''}`,
    divine: (n: number, top: string | null, share: number | null) =>
      `${countHe(n, 'שם אחד של האל', 'שני שמות של האל', 'שמות של האל')}${top ? `, לרוב ${top}` : ''}${share === null ? '' : ` (יהוה ${Math.round(share * 100)}% מבין יהוה ואלהים)`}`,
    reception: (n: number, top: string | null) => `${countHe(n, 'ציטוט אחד בספרות חז״ל', 'שני ציטוטים בספרות חז״ל', 'ציטוטים בספרות חז״ל')}${top ? `, רובם ב${top}` : ''}`,
    witnesses: (n: number, top: string | null) => `${countHe(n, 'חילוף אחד', 'שני חילופים', 'חילופים')} בעדי נוסח אחרים${top ? `, רובם ב${top}` : ''}`,
    ciphers: (n: number, words: string | null, name: string | null) =>
      `${countHe(n, 'שם אחד הנקרא באתב״ש או באלב״ם', 'שני שמות הנקראים באתב״ש או באלב״ם', 'שמות הנקראים באתב״ש או באלב״ם')}${words && name ? ` (${words} נקרא ${name})` : ''}`,
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
    borrowing: 'כיוון השאילה',
    wordplay: 'משחקי מילים',
    alliteration: 'אליטרציה',
    rhymes: 'חרוז',
    typescenes: 'רצפי פעולות',
    discoveries: 'זוגות חזקים בלי קישור',
    seams: 'תפרים סגנוניים',
    names: 'שמות',
    labels: 'התוויות שלכם',
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
    places: 'מקומות על המפה',
    people: 'אנשים באילן היוחסין',
    ciphers: 'אתב״ש ואלב״ם',
    divine: 'שמות האל',
    gematria: 'ערכי אותיות',
    reception: 'ציטוטים בספרות חז״ל',
    witnesses: 'עדי נוסח אחרים',
  },
}
