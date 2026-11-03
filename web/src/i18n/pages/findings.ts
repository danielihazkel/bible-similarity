// Interface strings of the Findings page: each analysis's tested claim and its verdict (DESIGN.md
// §10, `/findings`). English first, Hebrew typed against it. Each text reads its numbers from the
// API, so it states what the current build found; wording that depends on a direction branches.

import type { FindingKey } from '../../api/types'
import { numEn, numHe, pct } from '../fmt'

export type V = Record<string, number | null>
export const n = (v: V, k: string) => v[k] ?? 0
export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
export const x2 = (r: number) => r.toFixed(2)
export const x1 = (r: number) => r.toFixed(1)
export const fp3 = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.1 ? p.toFixed(3) : p.toFixed(2))
export const x3 = (r: number) => r.toFixed(3)
/** How far the tradition's middle falls from ours: "4,829 letters after ours". */
const away = (d: number, one: string, many: string, after: string, before: string, num: (n: number) => string) =>
  d === 0 ? 'It is ours exactly' : `It falls ${num(Math.abs(d))} ${Math.abs(d) === 1 ? one : many} ${d > 0 ? after : before} ours`
export const awayHe = (d: number, many: string, after: string, before: string) =>
  d === 0 ? 'הוא האמצע שלנו בדיוק' : `הוא נופל ${numHe(Math.abs(d))} ${many} ${d > 0 ? after : before} האמצע שלנו`

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
    ciphers_known: {
      title: 'Atbash in Jeremiah',
      text: (v: V) =>
        `Are the places where Jeremiah writes a name in atbash (ששך for בבל in 25:26 and 51:41, לב קמי for כשדים in 51:1) found by reading every unusual word through the swap? ${numEn(n(v, 'found'))} of ${numEn(n(v, 'n'))}.`,
    },
    ciphers_jeremiah: {
      title: 'Atbash stands out where it is known',
      text: (v: V) =>
        `Does atbash turn more words of Jeremiah 25 and 51 into names than a random swap of the letters does? ${numEn(n(v, 'observed'))} against ${x2(n(v, 'expected'))} (p ${fp(n(v, 'p'))}).`,
    },
    ciphers_elsewhere: {
      title: 'Atbash names hidden in the rest of the Bible?',
      text: (v: V) =>
        `Outside those chapters, does atbash turn more words into names than random swaps of the letters? ${numEn(n(v, 'observed'))} against ${n(v, 'expected').toFixed(1)} (p ${fp(n(v, 'p'))}).`,
    },
    ciphers_albam: {
      title: 'Albam names hidden anywhere?',
      text: (v: V) =>
        `Does albam, the other letter swap of the tradition, turn more words into names than random swaps do? ${numEn(n(v, 'observed'))} against ${n(v, 'expected').toFixed(1)} (p ${fp(n(v, 'p'))}).`,
    },
    masorah_letter: {
      title: 'The middle letter of the Torah',
      text: (v: V) =>
        `Is the ו of גחון (Leviticus 11:42) the middle of the Torah’s ${numEn(n(v, 'n'))} letters as written, as Kiddushin 30a says? ${away(n(v, 'distance'), 'letter', 'letters', 'after', 'before', numEn)}, ${numEn(Math.abs(n(v, 'verses_apart')))} verses on.`,
    },
    masorah_words: {
      title: 'The middle words of the Torah',
      text: (v: V) =>
        `Do דרש דרש (Leviticus 10:16) stand at the middle of the Torah’s ${numEn(n(v, 'n'))} words as written? ${away(n(v, 'distance'), 'word', 'words', 'after', 'before', numEn)}, ${numEn(Math.abs(n(v, 'verses_apart')))} verses on.`,
    },
    masorah_verse: {
      title: 'The middle verse of the Torah',
      text: (v: V) =>
        `Is Leviticus 8:8, the Masorah’s middle verse, the middle of the Torah’s ${numEn(n(v, 'n'))} verses here? ${away(n(v, 'distance'), 'verse', 'verses', 'after', 'before', numEn)}.`,
    },
    masorah_books: {
      title: 'The Masorah’s verse totals',
      text: (v: V) =>
        `Does each book have as many verses as the Masorah says? ${numEn(n(v, 'agree'))} of ${numEn(n(v, 'n'))}; the others differ by at most ${numEn(n(v, 'max_diff'))}, ${numEn(n(v, 'reasoned'))} of them for a reason the page gives (the Ten Commandments divided otherwise, a verse counted as two, two verses left out).`,
    },
    gematria_links: {
      title: 'Equal values, related words?',
      text: (v: V) =>
        `Are words of equal letter value closer in meaning than words matched on length and frequency? Over ${numEn(n(v, 'pairs'))} pairs: semantic domains shared ${x3(n(v, 'domains_observed'))} against ${x3(n(v, 'domains_null'))} (p ${fp(n(v, 'domains_p'))}), one root family ${pct(n(v, 'root_observed'))} against ${pct(n(v, 'root_null'))} (p ${fp(n(v, 'root_p'))}), used alike ${x3(n(v, 'vector_observed'))} against ${x3(n(v, 'vector_null'))} (p ${fp(n(v, 'vector_p'))}).`,
    },
    gematria_measures: {
      title: 'The measures of relatedness see it where it is',
      text: (v: V) =>
        `A check: are ${numEn(n(v, 'pairs'))} pairs of one root family closer than matched pairs? Domains shared ${x3(n(v, 'domains_observed'))} against ${x3(n(v, 'domains_null'))} (p ${fp(n(v, 'domains_p'))}), used alike ${x3(n(v, 'vector_observed'))} against ${x3(n(v, 'vector_null'))} (p ${fp(n(v, 'vector_p'))}).`,
    },
    gematria_genesis: {
      title: 'Genesis 1:1 singular by its numbers?',
      text: (v: V) =>
        `Is Genesis 1:1 (${numEn(n(v, 'value'))}, 7 words, 28 letters) rarer by its own numbers than verses usually are? ${n(v, 'unique_here') ? 'It is the only verse with its word count, letter count and largest prime factor' : `${numEn(n(v, 'twins'))} other verses share its word count, letter count and largest prime factor`}, while ${pct(n(v, 'unique_share'))} of verses are alone with theirs.`,
    },
    place_lists_order: {
      title: 'Place lists ordered on the ground',
      text: (v: V) =>
        `Do the itineraries, borders and town lists name their places in an order that walks the ground, a shorter path than random orders of the same places? ${numEn(n(v, 'held'))} of ${numEn(n(v, 'n'))} lists (the weakest p ${fp(n(v, 'max_p'))}); on sure sites alone, ${numEn(n(v, 'sure_held'))} of ${numEn(n(v, 'sure_n'))}.`,
    },
    place_lists_districts: {
      title: 'Joshua’s towns by district',
      text: (v: V) =>
        `Do the towns of one district of Joshua’s lists lie closer together than towns with the districts shuffled over them? ${numEn(n(v, 'held'))} of ${numEn(n(v, 'n'))} groupings (the weakest p ${fp(n(v, 'max_p'))}); on sure sites alone, ${numEn(n(v, 'sure_held'))} of ${numEn(n(v, 'sure_n'))}.`,
    },
    place_arc_order: {
      title: 'Consecutive chapters close on the map',
      text: (v: V) =>
        `Do consecutive chapters of a book lie closer on the map than its chapters in shuffled order, each chapter placed at the mean of the places it names? ${numEn(n(v, 'placed'))} of ${numEn(n(v, 'chapters'))} chapters placed: ${numEn(Math.round(n(v, 'mean_step')))} km from one to the next against ${numEn(Math.round(n(v, 'null_mean')))} km shuffled (p ${fp(n(v, 'p'))}); ${numEn(n(v, 'books_held'))} of ${numEn(n(v, 'books'))} books on their own.`,
    },
    place_arc_moves: {
      title: 'The story’s known moves',
      text: (v: V) =>
        `Does the chapters’ centre move where the story goes: Abram to Canaan, down to Egypt, out into the wilderness, to Babylon? ${numEn(n(v, 'held'))} of ${numEn(n(v, 'n'))} moves go from the region left towards the region entered.`,
    },
    place_arc_oracles: {
      title: 'The oracles against the nations range wider',
      text: (v: V) =>
        `Do the chapters of the oracles against the nations range wider than the other chapters of the prophets? Spread ${numEn(Math.round(n(v, 'spread_observed')))} km against ${numEn(Math.round(n(v, 'spread_other')))} km (p ${fp(n(v, 'spread_p'))}), reach from Jerusalem ${numEn(Math.round(n(v, 'reach_observed')))} km against ${numEn(Math.round(n(v, 'reach_other')))} km (p ${fp(n(v, 'reach_p'))}), each at α / 2.`,
    },
    place_links_decay: {
      title: 'Places named together lie together',
      text: (v: V) =>
        `Are places the text names together nearer each other the more strongly they are linked? Over ${numEn(n(v, 'pairs'))} linked pairs of ${numEn(n(v, 'places'))} places, Spearman’s ρ between link strength and distance is ${x2(n(v, 'rho'))} against ${x2(n(v, 'null_mean'))} with the points shuffled (p ${fp(n(v, 'p'))}); on sure sites alone ${x2(n(v, 'sure_rho'))}, without the place lists ${x2(n(v, 'no_lists_rho'))}.`,
    },
    place_links_known: {
      title: 'From Dan to Beersheba',
      text: (v: V) =>
        `Is the land’s length, Dan and Beersheba (${numEn(Math.round(n(v, 'km')))} km apart), among the ${numEn(n(v, 'top'))} most strongly linked far pairs of places? ${v.rank == null ? 'It is not among them.' : `It ranks ${numEn(n(v, 'rank'))}.`}`,
    },
    els_counts: {
      title: 'No more names at equal skips than chance',
      text: (v: V) =>
        `Does the Torah hold more names at equal skips (${numEn(n(v, 'terms'))} names, skips up to 1,000 either way) than its letters shuffled, its verses shuffled or stretches of the other books as long? Its hits run at ${x3(n(v, 'torah_r'))} on a log scale against the shuffles’ expectation; p ${fp(n(v, 'torah_letters_p'))} against shuffled letters, ${fp(n(v, 'torah_verses_p'))} against shuffled verses, ${fp(n(v, 'torah_blocks_p'))} against the other books; Genesis alone ${x3(n(v, 'genesis_r'))}.`,
    },
    divine_elohistic: {
      title: 'The Elohistic Psalter, found without being named',
      text: (v: V) =>
        `Cut in three where the mix of \u2068יהוה\u2069 and \u2068אלהים\u2069 changes most, does Psalms set apart the psalms that scholars call the Elohistic Psalter (${numEn(n(v, 'named_first'))}–${numEn(n(v, 'named_last'))})? The middle part found is ${numEn(n(v, 'first'))}–${numEn(n(v, 'last'))}, with \u2068יהוה\u2069 ${pct(n(v, 'share2'))} of the two against ${pct(n(v, 'share1'))} and ${pct(n(v, 'share3'))} around it (p ${fp(n(v, 'p'))} against the psalms shuffled).`,
    },
    divine_doubled: {
      title: 'The doubled psalms: \u2068אלהים\u2069 for \u2068יהוה\u2069',
      text: (v: V) =>
        `Where a psalm is found twice (${numEn(n(v, 'pairs'))} pairs), does the copy inside the Elohistic Psalter have \u2068אלהים\u2069 where the other has \u2068יהוה\u2069 more often than the reverse? ${numEn(n(v, 'e_ward'))} against ${numEn(n(v, 'y_ward'))} (sign test, p ${fp(n(v, 'p'))}).`,
    },
    haftarot_claim: {
      title: 'The sages’ haftarot are where the systems look',
      text: (v: V) =>
        `Ranking all ${numEn(n(v, 'candidates'))} chapters of the Prophets for each parasha, where do the ${numEn(n(v, 'thematic'))} haftarot chosen for their parasha fall? At percentile ${pct(n(v, 'thematic_pct'))} on average (0 the first chapter), against ${pct(n(v, 'shuffled_pct'))} with the haftarot shuffled among the parashot (p ${fp(n(v, 'p'))}). ${numEn(n(v, 'fused_hits'))} lie in the first ${numEn(n(v, 'list'))} chapters; words put the most first (MRR ${x2(n(v, 'lexical_mrr'))}, against ${x2(n(v, 'semantic_mrr'))} for meaning and ${x2(n(v, 'fused_mrr'))} for both).`,
    },
    haftarot_calendar: {
      title: 'The calendar’s haftarot do not follow their parasha',
      text: (v: V) =>
        `The ten haftarot fixed by the calendar (three of rebuke before the Ninth of Av, seven of consolation after) are not chosen for their parasha. Do they rank lower than the rest? At percentile ${pct(n(v, 'calendar_pct'))} against ${pct(n(v, 'thematic_pct'))} (p ${fp(n(v, 'calendar_p'))}).`,
    },
    haftarot_known: {
      title: 'Noah’s waters and the Shunammite’s son',
      text: (v: V) =>
        `Are the haftarot of Noach (Isaiah 54, \u2068כי מי נח זאת לי\u2069) and Vayera (II Kings 4, a son promised to a woman without one) among the first ${numEn(n(v, 'known_rank'))} of the 380 chapters for their parasha? Ranked ${numEn(n(v, 'rank_0'))} and ${numEn(n(v, 'rank_1'))}.`,
    },
    binomials_short: {
      title: 'In a fixed pair the shorter word comes first',
      text: (v: V) =>
        `Of the ${numEn(n(v, 'binomials'))} pairs of words joined by \u2068ו\u2069 that recur (\u2068שמים וארץ\u2069), those whose words differ in length put the shorter first ${numEn(n(v, 'letters_k'))} times of ${numEn(n(v, 'letters_m'))} in letters (p ${fp3(n(v, 'letters_p'))}) and ${numEn(n(v, 'syll_k'))} of ${numEn(n(v, 'syll_m'))} in syllables (p ${fp3(n(v, 'syll_p'))}); both were to hold.`,
    },
    binomials_late: {
      title: 'The late books turn the pairs round',
      text: (v: V) =>
        `A pair stands in its rarer order ${pct(n(v, 'rate_early'))} of the time in the early books and ${pct(n(v, 'rate_late'))} in the late, with the periods shuffled within each pair (p ${fp(n(v, 'p'))}). Without \u2068כסף וזהב\u2069, whose turn is the textbook case, p ${fp(n(v, 'without_p'))}.`,
    },
    binomials_known: {
      title: 'Heaven and earth fixed; gold before silver late',
      text: (v: V) =>
        `\u2068שמים וארץ\u2069 stands in that order ${pct(n(v, 'share_0'))} of ${numEn(n(v, 'n_0'))} times, \u2068איש ואשה\u2069 ${pct(n(v, 'share_1'))} of ${numEn(n(v, 'n_1'))}; \u2068זהב וכסף\u2069 rather than \u2068כסף וזהב\u2069 ${pct(n(v, 'gold_early'))} of the time in the early books, ${pct(n(v, 'gold_late'))} in the late.`,
    },
    sums_lists: {
      title: 'The lists add up, or fail to, as known',
      text: (v: V) =>
        `${numEn(n(v, 'adding_up'))} of the ${numEn(n(v, 'lists'))} lists named in advance add up to the total the text states, each as expected: the census of Numbers 1 comes to ${numEn(n(v, 'num1_sum'))} against ${numEn(n(v, 'num1_total'))}; the families of Ezra 2 to ${numEn(n(v, 'ezra2_sum'))} against the ${numEn(n(v, 'ezra2_total'))} of the whole assembly. A check of the reading of the numbers.`,
    },
    sums_parallels: {
      title: 'Where parallels’ numbers differ, they differ by one step',
      text: (v: V) =>
        `Of ${numEn(n(v, 'tested'))} numbers that differ between parallel verses in different books, ${numEn(n(v, 'one_step'))} (${pct(n(v, 'share'))}) are a power of ten or one decimal place apart (40,000 / 4,000; 18 / 8), against ${pct(n(v, 'expected'))} with the second number drawn from its book (p ${fp(n(v, 'p'))}).`,
    },
    frameworks_cycle: {
      title: 'The judges’ cycle breaks down through the book',
      text: (v: V) =>
        `Each major judge’s story is searched for the cycle’s ${numEn(n(v, 'slots'))} slots: did evil, given into a hand, years of servitude, cried out, a deliverer raised, the land at rest. Does the share fall through the book? Spearman’s rho with the order of the ${numEn(n(v, 'episodes'))} episodes ${x2(n(v, 'rho'))}, against every order (p ${fp(n(v, 'p'))}).`,
    },
    frameworks_cycle_known: {
      title: 'Othniel’s cycle whole, Samson’s broken',
      text: (v: V) =>
        `Othniel’s story (Judges 3:7–11) is the paradigm: it lacks ${numEn(n(v, 'othniel_missing'))} of the ${numEn(n(v, 'slots'))} slots. Samson’s lacks the cry and the rest (${numEn(n(v, 'samson_missing'))} missing in all).`,
    },
    frameworks_verdicts: {
      title: 'Each kingdom’s verdicts have their own wording',
      text: (v: V) =>
        `The ${numEn(n(v, 'verdicts'))} verdicts of Kings (he did evil, or right, in the eyes of the LORD) with the verses after them, compared word by word: alike ${x2(n(v, 'within_all'))} within a kingdom (Judah ${x2(n(v, 'within_judah'))}, Israel ${x2(n(v, 'within_israel'))}), ${x2(n(v, 'between'))} across, with the kingdoms shuffled (p ${fp(n(v, 'p'))}).`,
    },
    frameworks_verdicts_known: {
      title: 'The known verdicts are read right',
      text: (v: V) => `Kings whose verdict is known in advance (Asa, Jehoshaphat, Hezekiah and Josiah right; Ahaz, Ahab and Manasseh evil): ${numEn(n(v, 'found'))} of ${numEn(n(v, 'known'))} read so.`,
    },
    chronology_known: {
      title: 'The text’s numbers give the tradition’s years',
      text: (v: V) =>
        `Adding up the fathers’ ages of Genesis 5 and 11 from Adam, then the stated spans: the Flood falls in ${n(v, 'flood')}, Abram is born in ${n(v, 'abram')} and the Exodus in ${n(v, 'exodus')}, the years of Seder Olam (${n(v, 'flood_expected')}, ${n(v, 'abram_expected')}, ${n(v, 'exodus_expected')}). Where the text counts the same event twice, ${numEn(n(v, 'conflicts'))} give another year.`,
    },
    chronology_syncs: {
      title: 'The kings’ synchronisms agree with their reigns',
      text: (v: V) =>
        `Kings dates each accession by a year of the other kingdom’s king. Between two synchronisms in a row, are the years counted by Judah’s reigns those counted by Israel’s, within ${numEn(n(v, 'tolerance'))}? ${numEn(n(v, 'agree'))} of ${numEn(n(v, 'intervals'))} intervals are, against ${x1(n(v, 'expected'))} with the reign lengths shuffled within each kingdom (p ${fp(n(v, 'p'))}).`,
    },
    chronology_digits: {
      title: 'Genesis 5’s numbers end in 0, 2, 5 or 7',
      text: (v: V) =>
        `${numEn(n(v, 'hits'))} of the ${numEn(n(v, 'n'))} year numbers of Genesis 5 end in 0, 2, 5 or 7 (${pct(n(v, 'share'))}), against ${pct(n(v, 'rest_share'))} of the year numbers elsewhere in the Bible (p ${fp(n(v, 'p'))}).`,
    },
    retold_claim: {
      title: 'Speech retold by another speaker changes more than speech carried out',
      text: (v: V) =>
        `When one speaker tells again what another said (${numEn(n(v, 'a_n'))} retellings), are more of the words changed (substituted, left out, added or moved) than when the narrator tells a speech again as done, command and execution (${numEn(n(v, 'b_n'))})? ${pct(n(v, 'a_rate'))} of the words against ${pct(n(v, 'b_rate'))}, within the same lengths (p ${fp(n(v, 'p'))}).`,
    },
    retold_known: {
      title: 'The retellings the commentaries read side by side',
      text: (v: V) =>
        `Of the ${numEn(n(v, 'known'))} named in advance (God’s command as the woman tells it, Abraham’s charge as his servant tells it, Pharaoh’s dreams as he tells them), the alignment finds ${numEn(n(v, 'known_found'))}; all of them were asked for.`,
    },
    brackets_insertion: {
      title: 'A repeated clause brackets a block that interrupts',
      text: (v: V) =>
        `When a clause is said again a few verses later (${numEn(n(v, 'brackets'))} repetitions, 3 to 40 verses apart), do the verses between cohere with the text around them less than any stretch as long in the same book? Their bracket score averages ${x3(n(v, 'mean'))}, random brackets ${x3(n(v, 'mean_null'))} (p ${fp(n(v, 'p'))}); ${numEn(n(v, 'leads'))} brackets beyond chance one by one after correction.`,
    },
    brackets_known: {
      title: 'The editors’ brackets the commentaries name',
      text: (v: V) =>
        `Of the ${numEn(n(v, 'known'))} named in advance (Genesis 37:36 and 39:1 around Judah and Tamar, Exodus 6:12 and 6:30 around the genealogy, Ezra 4:5 and 4:24 around the Aramaic letters), the alignment finds ${numEn(n(v, 'known_found'))} and ${numEn(n(v, 'known_beat'))} beat their random brackets; all three were asked for.`,
    },
    etiology_echo: {
      title: 'A name sounds like its own explanation',
      text: (v: V) =>
        `When the text names someone or somewhere (${numEn(n(v, 'namings'))} namings), does the name echo the words of its own verse more than the explanations given for the other names? On average ${pct(n(v, 'mean_own'))} of a name’s consonants stand in order in one word of its own verse, against ${pct(n(v, 'mean_null'))} with the explanations shuffled (p ${fp(n(v, 'p'))}); ${numEn(n(v, 'leads'))} namings beyond chance one by one.`,
    },
    etiology_known: {
      title: 'The etiologies everyone agrees on',
      text: (v: V) =>
        `Of the ${numEn(n(v, 'known'))} named in advance (Jacob’s sons, \u2068נח\u2069, \u2068משה\u2069, \u2068באר שבע\u2069 …), the formula finds ${numEn(n(v, 'known_found'))}, and ${numEn(n(v, 'known_echo'))} echo their name better than all but ${pct(n(v, 'known_rank'))} of the other explanations; three in four were asked for. Short names of common letters (\u2068שת\u2069, \u2068לוי\u2069) are echoed by chance too often to stand out.`,
    },
    els_known: {
      title: 'The tradition’s sequences in our letters',
      text: (v: V) =>
        `Are the sequences read at the start of each book of the Torah (תורה at every 50th letter from Genesis 1:1, and the others) in our letter string? ${numEn(n(v, 'found'))} of ${numEn(n(v, 'n'))}.`,
    },
    allusions: {
      title: 'Rare words over a few verses',
      text: (v: V) =>
        `${numEn(n(v, 'pairs'))} pairs of passages share three or more rare words; ${numEn(n(v, 'known'))} are known parallels, and the best new one has q ${x2(n(v, 'best_new_q'))} against shuffled verses.`,
    },
  } satisfies Record<FindingKey, { title: string; text: (v: V) => string }>,
}
