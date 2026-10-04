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
    lexical_chiasm_z REAL
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

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT                      -- JSON-encoded
) WITHOUT ROWID;
