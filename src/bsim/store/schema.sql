-- results.sqlite (DESIGN.md §9). Written by `bsim build-db`; read-only for the API.
-- Indexes beyond the primary keys are created after loading (db.INDEXES).

CREATE TABLE books (
    book_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,             -- Sefaria title
    he_name TEXT NOT NULL,
    osis TEXT NOT NULL,
    section TEXT NOT NULL,          -- Torah | Prophets | Writings
    n_chapters INTEGER NOT NULL
);

CREATE TABLE verses (
    verse_id INTEGER PRIMARY KEY,   -- canon ordinal = embedding row
    book_id INTEGER NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    ref TEXT NOT NULL,
    osis TEXT NOT NULL,
    text_display TEXT NOT NULL,     -- MAM, pointed + te'amim
    text_plain TEXT NOT NULL,       -- consonantal MAM
    ketiv_note TEXT,
    display_tokens TEXT NOT NULL    -- JSON list; words.display_idx indexes it
);

CREATE TABLE words (
    verse_id INTEGER NOT NULL,
    idx INTEGER NOT NULL,
    display_idx INTEGER,            -- NULL when not aligned to a MAM token
    surface TEXT NOT NULL,
    lemma TEXT NOT NULL,            -- OSHB lemma attribute, e.g. b/7225
    content_lemmas TEXT NOT NULL,   -- space-joined content lemmas, e.g. 7225
    morph TEXT,
    in_formula INTEGER NOT NULL,    -- 1 if inside a down-weighted formula occurrence
    domains TEXT,                   -- space-joined SDBH domain codes of its content morphemes (§16.22)
    PRIMARY KEY (verse_id, idx)
) WITHOUT ROWID;

CREATE TABLE units (
    unit_id TEXT PRIMARY KEY,
    unit_type TEXT NOT NULL,
    label_en TEXT NOT NULL,
    label_he TEXT NOT NULL,
    book_id INTEGER NOT NULL,
    start_verse_id INTEGER NOT NULL,
    end_verse_id INTEGER NOT NULL,
    n_verses INTEGER NOT NULL,
    marker TEXT                     -- pericope closing marker: pe | samekh
);

CREATE TABLE unit_members (
    unit_id TEXT NOT NULL,
    verse_id INTEGER NOT NULL,
    PRIMARY KEY (unit_id, verse_id)
) WITHOUT ROWID;

CREATE TABLE matches (
    unit_type TEXT NOT NULL,
    mode TEXT NOT NULL,             -- lexical | semantic | fused
    src_id TEXT NOT NULL,
    rank INTEGER NOT NULL,          -- 1-based, self excluded
    tgt_id TEXT NOT NULL,
    score REAL NOT NULL,
    lex_score REAL,                 -- breakdown: fused rows only
    lex_rank INTEGER,
    sem_score REAL,
    sem_rank INTEGER,
    link_level TEXT,                -- Sefaria gold link: verse (direct) | unit (passage) | NULL
    link_type TEXT,                 -- comma-joined connection types ('' when untyped)
    PRIMARY KEY (unit_type, mode, src_id, rank)
) WITHOUT ROWID;

-- Strong unlinked pairs (db.discoveries): unordered (a = earlier unit), min rank <= max_rank,
-- no Sefaria link, verse neighbours dropped.
CREATE TABLE discoveries (
    unit_type TEXT NOT NULL,
    mode TEXT NOT NULL,
    a_id TEXT NOT NULL,
    b_id TEXT NOT NULL,
    score REAL NOT NULL,            -- max of the two directional scores
    tie REAL NOT NULL,              -- secondary sort: semantic score for fused pairs, else score
    rank_ab INTEGER,                -- rank of b in a's list (NULL: not in it)
    rank_ba INTEGER,
    a_book INTEGER NOT NULL,
    b_book INTEGER NOT NULL,
    PRIMARY KEY (unit_type, mode, a_id, b_id)
) WITHOUT ROWID;

-- Shared phrases between verses (`bsim phrases`), a < b; *_words = JSON lists of words.idx.
CREATE TABLE phrases (
    a INTEGER NOT NULL,
    b INTEGER NOT NULL,
    score REAL NOT NULL,
    n_tokens INTEGER NOT NULL,
    a_words TEXT NOT NULL,
    b_words TEXT NOT NULL,
    spread INTEGER NOT NULL,        -- verses sharing the exact matched lemma sequence (2 = unique)
    a_book INTEGER NOT NULL,
    b_book INTEGER NOT NULL,
    PRIMARY KEY (a, b)
) WITHOUT ROWID;

-- Same-order parallel passages (`bsim sequences`, DESIGN.md §16.7); pairs = JSON [[a, b, w, gold], ...];
-- n_gold = aligned pairs that are a Sefaria gold link (verse- or passage-level, either direction).
CREATE TABLE sequences (
    seq_id INTEGER PRIMARY KEY,     -- 1 = strongest chain
    a_start INTEGER NOT NULL,
    a_end INTEGER NOT NULL,
    b_start INTEGER NOT NULL,
    b_end INTEGER NOT NULL,
    direction TEXT NOT NULL,        -- forward | reverse | mixed (order of the b side)
    a_book INTEGER NOT NULL,
    b_book INTEGER NOT NULL,
    same_chapter INTEGER NOT NULL,
    n_pairs INTEGER NOT NULL,
    score REAL NOT NULL,
    q REAL NOT NULL,                -- expected share of chance chains at least this strong
    pairs TEXT NOT NULL,
    n_gold INTEGER NOT NULL
);

-- Word-level changes inside parallel sequences (`bsim diffs`, DESIGN.md §16.8); A = earlier verse.
-- op: spelling | form | substitution | omitted | added | moved; *_idx = words.idx (NULL: no word).
CREATE TABLE diff_changes (
    seq_id INTEGER NOT NULL,
    a INTEGER NOT NULL,
    b INTEGER NOT NULL,
    a_book INTEGER NOT NULL,
    b_book INTEGER NOT NULL,
    op TEXT NOT NULL,
    a_idx INTEGER,
    b_idx INTEGER,
    a_key TEXT,
    b_key TEXT,
    a_form TEXT,                    -- consonantal surface as written
    b_form TEXT
);

-- Verse halves from the te'amim and their parallelism (`bsim parallelism`, DESIGN.md §16.9).
-- cola = JSON inclusive display-token spans; features and prob NULL for a one-colon verse.
CREATE TABLE parallelism (
    verse_id INTEGER PRIMARY KEY,
    n_cola INTEGER NOT NULL,
    cola TEXT NOT NULL,
    pauses TEXT NOT NULL,           -- JSON accent names of the pauses between cola
    cos REAL,
    shared REAL,
    shape REAL,
    balance REAL,
    prob REAL,                      -- probability the halves are parallel like poetry
    clauses TEXT NOT NULL,          -- JSON spans between accent pauses of level 1-2 (§16.18)
    next_prob REAL,                 -- bicolon with the next verse (two one-colon verses)
    relation TEXT,                  -- antithetic | synonymous | NULL (parallel verses, §16.22)
    relation_pairs TEXT             -- JSON [a, b, kind] lemma pairs that decided it
);

-- Fixed word pairs across the members of parallel lines (`bsim parallelism`, §16.18).
CREATE TABLE word_pairs (
    a_lemma TEXT NOT NULL,          -- in the first member
    b_lemma TEXT NOT NULL,          -- in the second
    n INTEGER NOT NULL,
    expected REAL NOT NULL,
    g2 REAL NOT NULL,
    p REAL NOT NULL,
    q REAL NOT NULL,
    reverse INTEGER NOT NULL,       -- the pair in the other order
    examples TEXT NOT NULL          -- JSON verse ids
);

-- Sound-alike words close together (`bsim wordplay`, DESIGN.md §16.10); *_idx = words.idx.
CREATE TABLE wordplay (
    a_vid INTEGER NOT NULL,
    a_idx INTEGER NOT NULL,
    b_vid INTEGER NOT NULL,
    b_idx INTEGER NOT NULL,
    a_lemma TEXT NOT NULL,
    b_lemma TEXT NOT NULL,
    a_form TEXT NOT NULL,           -- heard form: consonants without prefixes
    b_form TEXT NOT NULL,
    kind TEXT NOT NULL,             -- substitution | metathesis | extension
    gap INTEGER NOT NULL,           -- words apart
    score REAL NOT NULL,
    q REAL NOT NULL,
    book_id INTEGER NOT NULL
);

-- Recurring action sequences between pericopes (`bsim typescenes`, DESIGN.md §16.20).
CREATE TABLE typescenes (
    a_unit TEXT NOT NULL,
    b_unit TEXT NOT NULL,
    a_book INTEGER NOT NULL,
    b_book INTEGER NOT NULL,
    score REAL NOT NULL,
    n_matches INTEGER NOT NULL,
    aligned TEXT NOT NULL,          -- JSON [a_vid, b_vid, lemma] per matched verb
    parallel_text INTEGER NOT NULL, -- a significant parallel sequence joins the two
    q REAL NOT NULL
);

-- Alliteration per colon (`bsim sound`, DESIGN.md §16.19); words = JSON display indexes.
CREATE TABLE alliteration (
    verse_id INTEGER NOT NULL,
    colon INTEGER NOT NULL,
    sound TEXT NOT NULL,
    count INTEGER NOT NULL,
    n_words INTEGER NOT NULL,
    words TEXT NOT NULL,
    p REAL NOT NULL,
    q REAL NOT NULL,
    book_id INTEGER NOT NULL
);

-- Runs of cola ending alike (`bsim sound`); members = JSON [verse_id, display_idx] of each end.
CREATE TABLE rhymes (
    start_vid INTEGER NOT NULL,
    end_vid INTEGER NOT NULL,
    n_cola INTEGER NOT NULL,
    ending TEXT NOT NULL,
    members TEXT NOT NULL,
    p REAL NOT NULL,
    q REAL NOT NULL,
    book_id INTEGER NOT NULL
);

-- People and places (`bsim entities`, DESIGN.md §16.11): name lemmas, kind from context cues.
CREATE TABLE entities (
    lemma TEXT PRIMARY KEY,
    he TEXT NOT NULL,
    kind TEXT NOT NULL,             -- person | place | mixed | unclear
    n_mentions INTEGER NOT NULL,
    n_verses INTEGER NOT NULL,
    first_vid INTEGER NOT NULL,
    last_vid INTEGER NOT NULL,
    place REAL NOT NULL,            -- context cue scores
    person REAL NOT NULL,
    kind_cues TEXT NOT NULL,        -- the kind from the context cues alone
    kind_source TEXT NOT NULL       -- lexicon (Strong's part of speech) | cues
) WITHOUT ROWID;

CREATE TABLE entity_mentions (
    lemma TEXT NOT NULL,
    verse_id INTEGER NOT NULL,
    n INTEGER NOT NULL,
    PRIMARY KEY (lemma, verse_id)
) WITHOUT ROWID;

-- Names sharing verses more often than chance (G²), each name's strongest links, both directions.
CREATE TABLE entity_links (
    a TEXT NOT NULL,
    b TEXT NOT NULL,
    n_verses INTEGER NOT NULL,
    expected REAL NOT NULL,
    g2 REAL NOT NULL,
    PRIMARY KEY (a, b)
) WITHOUT ROWID;

-- Where a book's style changes (`bsim seams`, DESIGN.md §16.12): the shift curve at every verse
-- boundary (verse_id = first verse after it) and its significant peaks.
CREATE TABLE seam_curve (
    book_id INTEGER NOT NULL,
    verse_id INTEGER PRIMARY KEY,
    shift REAL NOT NULL
);

CREATE TABLE seams (
    book_id INTEGER NOT NULL,
    verse_id INTEGER NOT NULL,
    shift REAL NOT NULL,
    threshold REAL NOT NULL,        -- the book's 95th percentile of shuffled maxima
    rank INTEGER NOT NULL,          -- 1 = the book's strongest seam
    features TEXT NOT NULL,         -- JSON [[name, label, z after - before], ...]
    PRIMARY KEY (book_id, rank)
);

-- Inner-unit structure scores (`bsim structure`, DESIGN.md §16.2); NULL = unit too small.
CREATE TABLE structure (
    unit_id TEXT PRIMARY KEY,
    unit_type TEXT NOT NULL,
    n_verses INTEGER NOT NULL,
    semantic_inclusio REAL,
    semantic_inclusio_pct REAL,
    semantic_chiasm REAL,
    semantic_chiasm_pct REAL,
    semantic_chiasm_z REAL,
    lexical_inclusio REAL,
    lexical_inclusio_pct REAL,
    lexical_chiasm REAL,
    lexical_chiasm_pct REAL,
    lexical_chiasm_z REAL,
    semantic_inclusio_q REAL,       -- Benjamini-Hochberg q within the unit type (DESIGN.md §16.14)
    semantic_chiasm_q REAL,
    lexical_inclusio_q REAL,
    lexical_chiasm_q REAL
) WITHOUT ROWID;

-- Alphabetic acrostics (`bsim acrostics`, DESIGN.md §16.15): each chapter's best chain.
CREATE TABLE acrostics (
    unit_id TEXT PRIMARY KEY,
    book_id INTEGER NOT NULL,
    granularity TEXT NOT NULL,      -- verse | colon (line unit)
    order_name TEXT NOT NULL,       -- standard | pe-ayin
    score REAL NOT NULL,            -- letters - penalty x skipped letters
    n_letters INTEGER NOT NULL,
    missing INTEGER NOT NULL,       -- letters skipped inside the chain
    first_letter TEXT NOT NULL,
    last_letter TEXT NOT NULL,
    start_vid INTEGER NOT NULL,
    end_vid INTEGER NOT NULL,
    n_lines INTEGER NOT NULL,
    p REAL NOT NULL,
    q REAL NOT NULL,
    chain TEXT NOT NULL             -- JSON [verse_id, display_idx, letter] per line
) WITHOUT ROWID;

-- Changes one book makes consistently against another (`bsim diffs`, DESIGN.md §16.16).
CREATE TABLE rewrites (
    a_book INTEGER NOT NULL,
    b_book INTEGER NOT NULL,
    op TEXT NOT NULL,               -- substitution | omitted | added
    a_key TEXT,
    b_key TEXT,
    n INTEGER NOT NULL,
    base INTEGER NOT NULL,          -- words with the key on the side the change starts from
    rate REAL,
    g2 REAL NOT NULL,
    p REAL NOT NULL,
    q REAL NOT NULL
);

-- Per book pair of parallel passages: how much and how they differ.
CREATE TABLE rewrite_profiles (
    a_book INTEGER NOT NULL,
    b_book INTEGER NOT NULL,
    verse_pairs INTEGER NOT NULL,
    a_words INTEGER NOT NULL,
    b_words INTEGER NOT NULL,
    spelling INTEGER NOT NULL,
    form INTEGER NOT NULL,
    substitution INTEGER NOT NULL,
    omitted INTEGER NOT NULL,
    added INTEGER NOT NULL,
    moved INTEGER NOT NULL,
    to_plene INTEGER NOT NULL,
    to_defective INTEGER NOT NULL,
    PRIMARY KEY (a_book, b_book)
) WITHOUT ROWID;

-- Network of echoes (`bsim network`, DESIGN.md §16.17).
CREATE TABLE network_nodes (
    unit_id TEXT PRIMARY KEY,
    unit_type TEXT NOT NULL,
    pagerank REAL NOT NULL,
    strength REAL NOT NULL,         -- sum of edge weights
    partners INTEGER NOT NULL,
    cross_book REAL NOT NULL,       -- share of the strength reaching other books
    community INTEGER NOT NULL,
    x REAL NOT NULL,                -- spring layout inside the community, 0..1
    y REAL NOT NULL
) WITHOUT ROWID;

CREATE TABLE network_edges (
    unit_type TEXT NOT NULL,
    a TEXT NOT NULL,
    b TEXT NOT NULL,
    weight REAL NOT NULL
);

CREATE TABLE network_communities (
    unit_type TEXT NOT NULL,
    community INTEGER NOT NULL,     -- 0 = largest
    size INTEGER NOT NULL,
    lemmas TEXT NOT NULL,           -- JSON label lemmas (G²)
    books TEXT NOT NULL,            -- JSON [[book_id, units], ...], most first
    PRIMARY KEY (unit_type, community)
) WITHOUT ROWID;

-- Corpus map (`bsim map`, DESIGN.md §16.4).
CREATE TABLE map_points (
    unit_id TEXT PRIMARY KEY,
    unit_type TEXT NOT NULL,
    x REAL NOT NULL,                -- t-SNE, scaled to 0..1
    y REAL NOT NULL,
    cluster INTEGER NOT NULL
) WITHOUT ROWID;

CREATE TABLE map_clusters (
    unit_type TEXT NOT NULL,
    cluster INTEGER NOT NULL,
    size INTEGER NOT NULL,
    lemmas TEXT NOT NULL,           -- JSON list: label lemmas, strongest first
    PRIMARY KEY (unit_type, cluster)
) WITHOUT ROWID;

CREATE TABLE book_affinity (
    a_book INTEGER NOT NULL,        -- a < b
    b_book INTEGER NOT NULL,
    n_pairs INTEGER NOT NULL,       -- cross-book verse pairs within the fused top-N
    expected REAL NOT NULL,
    lift REAL NOT NULL,
    PRIMARY KEY (a_book, b_book)
) WITHOUT ROWID;

CREATE TABLE book_examples (
    a_book INTEGER NOT NULL,
    b_book INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    a_vid INTEGER NOT NULL,
    b_vid INTEGER NOT NULL,
    score REAL NOT NULL,            -- fused score (best of both directions)
    PRIMARY KEY (a_book, b_book, rank)
) WITHOUT ROWID;

-- Stylometry (`bsim stylometry`, DESIGN.md §16.6).
CREATE TABLE stylo_points (
    unit_id TEXT PRIMARY KEY,       -- chapters with >= stylometry.min_words words
    x REAL NOT NULL,                -- PC1 / PC2 of the feature z-scores, scaled to 0..1
    y REAL NOT NULL,
    n_words INTEGER NOT NULL
) WITHOUT ROWID;

CREATE TABLE stylo_delta (
    a_book INTEGER NOT NULL,        -- a < b
    b_book INTEGER NOT NULL,
    delta REAL NOT NULL,            -- Burrows' Delta (mean |z| difference)
    PRIMARY KEY (a_book, b_book)
) WITHOUT ROWID;

CREATE TABLE stylo_features (
    book_id INTEGER NOT NULL,
    side TEXT NOT NULL,             -- over | under
    rank INTEGER NOT NULL,
    feature TEXT NOT NULL,          -- lemma:<lemma> | pos:N | verb:w | article ...
    label TEXT NOT NULL,            -- Hebrew label
    rate REAL NOT NULL,             -- per word
    z REAL NOT NULL,
    PRIMARY KEY (book_id, side, rank)
) WITHOUT ROWID;

CREATE TABLE lemma_gloss (
    lemma TEXT PRIMARY KEY,
    he_lemma TEXT NOT NULL,         -- most common consonantal form, prefixes stripped
    n_words INTEGER NOT NULL,       -- occurrences in the corpus
    n_verses INTEGER NOT NULL,      -- verses containing it
    pos TEXT                        -- most common OSHB part of speech (N V A C R T P D ...)
) WITHOUT ROWID;

-- Concordance: every verse containing a content lemma.
CREATE TABLE lemma_verses (
    lemma TEXT NOT NULL,
    verse_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    PRIMARY KEY (lemma, verse_id)
) WITHOUT ROWID;

-- SDBH lexical semantic domains (`bsim lexicon`, §16.22); counts include the subdomains.
CREATE TABLE domains (
    code TEXT PRIMARY KEY,          -- 3 digits per level: 002001001069
    level INTEGER NOT NULL,
    parent TEXT,
    label_en TEXT NOT NULL,
    n_verses INTEGER NOT NULL,      -- verses with a content word in it
    weight REAL NOT NULL            -- content words in it (a word split over k domains counts 1/k)
) WITHOUT ROWID;

-- Domain concordance: the verses whose content words fall in a (leaf) domain.
CREATE TABLE domain_verses (
    code TEXT NOT NULL,
    verse_id INTEGER NOT NULL,
    weight REAL NOT NULL,
    PRIMARY KEY (code, verse_id)
) WITHOUT ROWID;

-- A frequent lemma's senses and uses across corpus groups (`bsim senses`, §16.23).
CREATE TABLE lemma_shifts (
    lemma TEXT PRIMARY KEY,
    n INTEGER NOT NULL,             -- occurrences compared
    groups TEXT NOT NULL,           -- JSON group -> occurrences
    k INTEGER NOT NULL,             -- contextual-use clusters
    silhouette REAL NOT NULL,
    use_mi REAL NOT NULL,           -- MI(group; use) in bits
    use_excess REAL NOT NULL,       -- ... minus its shuffled mean
    use_p REAL NOT NULL,
    use_q REAL NOT NULL,
    sense_n INTEGER NOT NULL,       -- occurrences with one SDBH meaning (of the compared ones)
    n_senses INTEGER NOT NULL,
    sense_mi REAL,                  -- NULL: fewer than two meanings to compare
    sense_excess REAL,
    sense_p REAL,
    sense_q REAL,
    nmi REAL,                       -- contextual clusters vs SDBH meanings
    nmi_null REAL
) WITHOUT ROWID;

CREATE TABLE lemma_senses (
    lemma TEXT NOT NULL,
    kind TEXT NOT NULL,             -- use (contextual cluster) | sdbh (dictionary meaning)
    sense TEXT NOT NULL,            -- cluster number or SDBH meaning id
    n INTEGER NOT NULL,
    groups TEXT NOT NULL,           -- JSON group -> occurrences
    collocates TEXT NOT NULL,       -- JSON lemmas over-represented in the cluster's verses
    examples TEXT NOT NULL,         -- JSON [verse_id, word idx]
    domains TEXT NOT NULL,          -- JSON SDBH domain codes of the meaning
    PRIMARY KEY (lemma, kind, sense)
) WITHOUT ROWID;

-- BHSA syntax (`bsim syntax`, §16.26): clauses and phrases over OSHB words (`words` = JSON idx).
CREATE TABLE clauses (
    clause INTEGER PRIMARY KEY,     -- BHSA node, in text order
    verse_id INTEGER NOT NULL,
    words TEXT NOT NULL,
    typ TEXT NOT NULL,              -- clause type: WayX, xQtX, NmCl, InfC, ...
    kind TEXT NOT NULL,             -- VC verbal | NC nominal | WP without predication
    txt TEXT NOT NULL,              -- text type with its embedding: N, NQ, ?NQQ, ...
    rela TEXT NOT NULL,             -- relation to another clause (NA: none)
    speaker TEXT,                   -- quotation: speaker lemma
    speaker_source TEXT             -- explicit | carried
);

CREATE TABLE syntax_phrases (
    phrase INTEGER PRIMARY KEY,     -- BHSA node
    clause INTEGER NOT NULL,
    verse_id INTEGER NOT NULL,
    words TEXT NOT NULL,
    typ TEXT NOT NULL,              -- VP, NP, PP, PrNP, ...
    function TEXT NOT NULL          -- Pred, Subj, Objc, Cmpl, Adju, Time, Loca, Conj, ...
);

-- Verses built the same way: the clause-shape list (`syntax.system`), top `syntax.neighbors`.
CREATE TABLE syntax_neighbors (
    verse_id INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    tgt INTEGER NOT NULL,
    score REAL NOT NULL,
    PRIMARY KEY (verse_id, rank)
) WITHOUT ROWID;

-- Narration and direct speech (analysis/speech.py): shares of words; `speakers` per book.
CREATE TABLE speech_chapters (
    unit_id TEXT PRIMARY KEY,
    book_id INTEGER NOT NULL,
    chapter INTEGER NOT NULL,
    narration REAL NOT NULL,
    speech REAL NOT NULL,
    discourse REAL NOT NULL,
    divine REAL NOT NULL,           -- speech by יהוה / אלהים / אדני
    attributed REAL NOT NULL,       -- speech with a speaker found
    n_words INTEGER NOT NULL
) WITHOUT ROWID;

CREATE TABLE speech_books (
    book_id INTEGER PRIMARY KEY,
    narration REAL NOT NULL,
    speech REAL NOT NULL,
    discourse REAL NOT NULL,
    divine REAL NOT NULL,
    attributed REAL NOT NULL,
    n_words INTEGER NOT NULL
);

CREATE TABLE speakers (
    book_id INTEGER NOT NULL,
    lemma TEXT NOT NULL,
    n_words INTEGER NOT NULL,
    n_explicit INTEGER NOT NULL,    -- words whose introduction names the speaker itself
    PRIMARY KEY (book_id, lemma)
) WITHOUT ROWID;

-- Speaker voices (`bsim voices`, §16.28): each person's speech against the other speech of
-- their books, Burrows' Delta with a within-book label-shuffle null. key: speaker lemma | divine.
CREATE TABLE voice_speakers (
    key TEXT PRIMARY KEY,
    n_words INTEGER NOT NULL,
    n_explicit INTEGER NOT NULL,    -- words whose introduction names the speaker itself
    n_clauses INTEGER NOT NULL,
    main_book INTEGER NOT NULL,     -- the book with most of the speaker's words
    books TEXT NOT NULL,            -- JSON book ids, most words first
    delta REAL NOT NULL,            -- Delta to the same books' other attributed speech
    null_mean REAL NOT NULL,
    effect REAL NOT NULL,           -- (delta - null mean) / null sd
    p REAL NOT NULL,
    q REAL NOT NULL
) WITHOUT ROWID;

CREATE TABLE voice_features (
    key TEXT NOT NULL,
    side TEXT NOT NULL,             -- over | under
    rank INTEGER NOT NULL,
    feature TEXT NOT NULL,
    label TEXT NOT NULL,
    rate REAL NOT NULL,
    rate_ref REAL NOT NULL,
    z REAL NOT NULL,                -- (rate - rate_ref) / chapter sd
    PRIMARY KEY (key, rank)
) WITHOUT ROWID;

CREATE TABLE voice_pairs (
    a TEXT NOT NULL,                -- speaker keys, narrator, unattributed
    b TEXT NOT NULL,
    delta REAL NOT NULL,
    PRIMARY KEY (a, b)
) WITHOUT ROWID;

-- Which side of a parallel looks like the borrower (`bsim borrowing`, §16.27). A = earlier in
-- the canon; a sign > 0 says B looks later. direction: a_to_b | b_to_a | unclear.
CREATE TABLE borrowing_sequences (
    seq_id INTEGER PRIMARY KEY,
    a_book INTEGER NOT NULL,
    b_book INTEGER NOT NULL,
    a_start INTEGER NOT NULL,
    a_end INTEGER NOT NULL,
    b_start INTEGER NOT NULL,
    b_end INTEGER NOT NULL,
    n_pairs INTEGER NOT NULL,
    language REAL NOT NULL,
    spelling REAL,                  -- NULL: too few spelling changes
    smoothing REAL,
    expansion REAL,
    n_spelling INTEGER NOT NULL,
    n_substitution INTEGER NOT NULL,
    known TEXT,                     -- the accepted direction, for the check pairs
    votes INTEGER NOT NULL,         -- sum of the used signs' votes
    n_votes INTEGER NOT NULL,
    direction TEXT NOT NULL
);

CREATE TABLE borrowing_books (
    a_book INTEGER NOT NULL,
    b_book INTEGER NOT NULL,
    sequences INTEGER NOT NULL,
    n_pairs INTEGER NOT NULL,
    votes INTEGER NOT NULL,
    a_to_b INTEGER NOT NULL,        -- sequences voted each way
    b_to_a INTEGER NOT NULL,
    known TEXT,
    direction TEXT NOT NULL,
    PRIMARY KEY (a_book, b_book)
) WITHOUT ROWID;

-- Late Biblical Hebrew profile (`bsim dating`, §16.24): feature rates and the model's score.
CREATE TABLE dating_chapters (
    unit_id TEXT PRIMARY KEY,       -- the chapter unit
    book_id INTEGER NOT NULL,
    chapter INTEGER NOT NULL,
    n_words INTEGER NOT NULL,       -- Hebrew words (Aramaic left out)
    role TEXT NOT NULL,             -- early | late (training books, scored held out) | scored
    out_of_domain INTEGER NOT NULL, -- poetry: the model is calibrated on prose
    lbh_lexemes REAL NOT NULL,
    anokhi REAL NOT NULL,
    inf_abs REAL NOT NULL,
    et_suffix REAL NOT NULL,
    directional_he REAL NOT NULL,
    cohortative_wayyiqtol REAL NOT NULL,
    david_plene REAL NOT NULL,
    score REAL,                     -- NULL: too few Hebrew words
    drivers TEXT NOT NULL           -- JSON features pushing the score up most
) WITHOUT ROWID;

CREATE TABLE dating_books (
    book_id INTEGER PRIMARY KEY,
    role TEXT NOT NULL,
    out_of_domain INTEGER NOT NULL,
    n_chapters INTEGER NOT NULL,    -- chapters scored
    score REAL,                     -- mean chapter score
    low REAL,                       -- 10th / 90th chapter percentiles
    high REAL,
    lbh_lexemes REAL NOT NULL,
    anokhi REAL NOT NULL,
    inf_abs REAL NOT NULL,
    et_suffix REAL NOT NULL,
    directional_he REAL NOT NULL,
    cohortative_wayyiqtol REAL NOT NULL,
    david_plene REAL NOT NULL
);

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT                      -- JSON-encoded
) WITHOUT ROWID;
