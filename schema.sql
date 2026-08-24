-- ════════════════════════════════════════════════════════════════════════
-- Foodie & Co., schema
--
-- Three decisions in here are load-bearing. Each is marked. The rest is
-- ordinary bookkeeping.
-- ════════════════════════════════════════════════════════════════════════

CREATE TABLE account_managers (
  am_id                 INTEGER PRIMARY KEY,
  name                  TEXT,
  covers_large_accounts INTEGER,   -- 18 of 80  [CASE]
  has_defected          INTEGER    -- 3 of those 18  [CASE]
);

CREATE TABLE skus (
  sku_id     INTEGER PRIMARY KEY,
  code       TEXT,
  name       TEXT,      -- real product name; UI prints this, not the code  [FIX]
  category   TEXT,
  unit_price REAL,
  in_stock   INTEGER,   -- Level 0 ranking filter                           [FIX]
  texture    TEXT,      -- e.g. 'firm'/'soft'; drives the texture exclusion [FIX]
  perishable INTEGER    -- delivery-preference generator input              [FIX]
);

CREATE TABLE accounts (
  account_id       INTEGER PRIMARY KEY,
  name             TEXT,
  neighborhood     TEXT,
  cuisine          TEXT,
  contact          TEXT,
  tier             TEXT,      -- A/B/C  [DERIVED from 18-of-80 AM split]
  annual_value     REAL,      -- sums to $95M  [CASE], distribution  [DIAL]
  orders_per_month REAL,      -- [DIAL] delivery cadence
  categories       TEXT,      -- what this account actually buys
  am_id            INTEGER REFERENCES account_managers(am_id)
);


-- ════════════════════════════════════════════════════════════════════════
-- DECISION 1, orders.channel as an enum plus nullable FKs
--
-- The whole diagnosis rests on separating orders that arrived on a standing
-- cadence from orders that arrived because a buyer asked a question. A
-- boolean is_recurring collapses four origins into two and can't join back
-- to the cause. A polymorphic origin_type/origin_id loses referential
-- integrity and forces a CASE into every query.
--
-- Enum + three nullable FKs is slightly denormalised (channel is derivable
-- from which FK is populated) but gives a fast filterable column AND real
-- foreign keys. Would switch to polymorphic only if many more origin types
-- were coming, which they aren't.
-- ════════════════════════════════════════════════════════════════════════
CREATE TABLE orders (
  order_id         INTEGER PRIMARY KEY,
  account_id       INTEGER REFERENCES accounts(account_id),
  order_date       TEXT,
  channel          TEXT CHECK (channel IN
                     ('standing','portal_adhoc','inquiry','campaign')),
  inquiry_id       INTEGER REFERENCES inquiries(inquiry_id),
  campaign_send_id INTEGER REFERENCES campaign_sends(send_id),
  order_value      REAL
);

CREATE TABLE inquiries (
  inquiry_id       INTEGER PRIMARY KEY,
  account_id       INTEGER REFERENCES accounts(account_id),
  received_date    TEXT,
  channel          TEXT CHECK (channel IN ('portal','direct_to_am')),
  category         TEXT,
  requested_sku_id INTEGER REFERENCES skus(sku_id),
  agent_handled    INTEGER   -- false before the launch date  [CASE: 4 months]
);


-- ════════════════════════════════════════════════════════════════════════
-- DECISION 2, draft_events as an append-only log, not a status column
--
-- A single status field cannot distinguish an approved draft from one an AM
-- opened, rejected, and rewrote from scratch. Both land in "not edited".
-- That is the finding: Foodie's 74% unedited bucket contains approved,
-- rubber-stamped, rejected, and never-opened, and nothing separates them.
--
-- The same table is the substrate any learning loop needs. Logging deltas
-- alone can only learn from AMs who edit, which excludes exactly the AMs
-- whose judgement is most valuable, because they bypass drafting entirely.
-- ════════════════════════════════════════════════════════════════════════
CREATE TABLE drafts (
  draft_id      INTEGER PRIMARY KEY,
  inquiry_id    INTEGER REFERENCES inquiries(inquiry_id),
  account_id    INTEGER REFERENCES accounts(account_id),
  workflow      TEXT CHECK (workflow IN ('inbound','outbound')),
  created_date  TEXT,
  edit_depth    REAL,      -- 0 when not edited  [CASE: 23% mean when edited]
  edit_category TEXT CHECK (edit_category IN
                  ('sku','tone','quantity','factual','other'))
                           -- [INVENTED breakdown, sums to the given 23%]
);

CREATE TABLE draft_events (
  draft_id    INTEGER REFERENCES drafts(draft_id),
  event_type  TEXT CHECK (event_type IN
                ('generated','opened','edited','sent','discarded')),
  occurred_at TEXT,
  actor_am_id INTEGER REFERENCES account_managers(am_id)
);


-- ════════════════════════════════════════════════════════════════════════
-- DECISION 3, substitutions, with TWO outcome columns
--
-- This table does not exist at Foodie today, and it is the core of the
-- recommendation. Two outcomes, not one, because they are different signals:
--
--   am_action, the AM's judgement, available immediately. Fast feedback.
--   buyer_outcome, what the buyer did. Ground truth, available later.
--
-- Collapsing them loses the ability to learn from AM overrides before any
-- buyer responds, which is the only signal that moves inside 75 days.
-- ════════════════════════════════════════════════════════════════════════
CREATE TABLE substitutions (
  substitution_id       INTEGER PRIMARY KEY,
  draft_id              INTEGER REFERENCES drafts(draft_id),
  account_id            INTEGER REFERENCES accounts(account_id),
  requested_sku_id      INTEGER REFERENCES skus(sku_id),
  offered_sku_id        INTEGER REFERENCES skus(sku_id),
  am_action             TEXT CHECK (am_action IN
                          ('sent_as_is','replaced','discarded')),
  am_replacement_sku_id INTEGER REFERENCES skus(sku_id),
  buyer_outcome         TEXT CHECK (buyer_outcome IN
                          ('accepted','declined','no_response')),
  resolved_date         TEXT,
  fact_id               INTEGER REFERENCES buyer_facts(fact_id)  -- [FIX] the fact this correction produced
);


CREATE TABLE campaigns (
  campaign_id INTEGER PRIMARY KEY,
  name        TEXT,
  category    TEXT,
  sent_month  TEXT
);

CREATE TABLE campaign_sends (
  send_id      INTEGER PRIMARY KEY,
  campaign_id  INTEGER REFERENCES campaigns(campaign_id),
  account_id   INTEGER REFERENCES accounts(account_id),
  sent_date    TEXT,
  was_relevant INTEGER,   -- does the pitched category match a real buying
                          -- pattern for this account?  [INVENTED]
  was_edited   INTEGER,   -- [CASE: 34%]
  edit_depth   REAL,      -- [CASE: 8% mean]
  converted    INTEGER,   -- [CASE: 12% overall]
  unsubscribed INTEGER    -- [CASE: 3.1% overall]
);

CREATE INDEX ix_orders_acct  ON orders(account_id, order_date);
CREATE INDEX ix_orders_chan  ON orders(channel, order_date);
CREATE INDEX ix_inq_acct     ON inquiries(account_id, received_date);
CREATE INDEX ix_drafts_acct  ON drafts(account_id);
CREATE INDEX ix_sends_acct   ON campaign_sends(account_id);


-- ════════════════════════════════════════════════════════════════════════
-- THE FIX, connect the record the AM already has, and capture new record.
--
-- source_documents already exist on Foodie's servers today (seeded in BOTH
-- states). buyer_facts / fact_impressions / account_sku_bias are the captured
-- record, empty in the current state, populated in the fixed state. Ranking
-- reads account_sku_bias on every draft, so a kept fact is live immediately.
-- ════════════════════════════════════════════════════════════════════════

-- Raw records that exist today: calls, emails, AM notes. Present in both states.
CREATE TABLE source_documents (
  doc_id      INTEGER PRIMARY KEY,
  account_id  INTEGER REFERENCES accounts(account_id),
  kind        TEXT CHECK (kind IN ('email','call_transcript','am_note')),
  occurred_at TEXT,
  author      TEXT,
  am_id       INTEGER REFERENCES account_managers(am_id),
  title       TEXT,
  body        TEXT
);

-- The captured record. am_decision NULL = shown but not yet decided (a
-- candidate never shown is different from one skipped, same distinction as
-- the draft event log). source_excerpt is STORED, not computed: the panel
-- quotes it verbatim, so it has to exist.
CREATE TABLE buyer_facts (
  fact_id        INTEGER PRIMARY KEY,
  account_id     INTEGER REFERENCES accounts(account_id),
  statement      TEXT,
  source_kind    TEXT,            -- refusal_pattern / cadence_lock / delivery_pref / stated_fact
  dedup_key      TEXT,
  source_doc_id  INTEGER REFERENCES source_documents(doc_id),
  source_excerpt TEXT,            -- the source sentence, verbatim
  source_locator TEXT,            -- mm:ss for calls, paragraph index for notes
  confidence     REAL,
  affects        TEXT,            -- json list of sku_ids this fact biases
  am_decision    TEXT CHECK (am_decision IN ('kept','skipped')),   -- NULL = pending
  decided_by     INTEGER REFERENCES account_managers(am_id),
  decided_at     TEXT,
  superseded_by  INTEGER REFERENCES buyer_facts(fact_id),
  valid_from     TEXT,
  last_influenced_at TEXT       -- [ADDITION] set when this fact last shaped a suggestion/message; NULL = kept but never used
);

-- Impression log: what was shown, when, and whether it was pre-checked.
-- Drives the suppress-after-two / retire-after-four caps.
CREATE TABLE fact_impressions (
  fact_id       INTEGER REFERENCES buyer_facts(fact_id),
  draft_id      INTEGER REFERENCES drafts(draft_id),
  shown_at      TEXT,
  was_prechecked INTEGER
);

-- Materialised expansion of kept facts, one row per affected SKU. Ranking
-- reads this on every substitution. Writes are rare, reads constant, 
-- optimise the read. fact_id in the PK means retiring a fact is a clean delete.
CREATE TABLE account_sku_bias (
  account_id INTEGER REFERENCES accounts(account_id),
  sku_id     INTEGER REFERENCES skus(sku_id),
  bias       REAL,                -- negative excludes
  fact_id    INTEGER REFERENCES buyer_facts(fact_id),
  PRIMARY KEY (account_id, sku_id, fact_id)
);

CREATE INDEX ix_bias         ON account_sku_bias(account_id, sku_id);
CREATE INDEX ix_srcdoc_acct  ON source_documents(account_id, occurred_at);
CREATE UNIQUE INDEX ux_facts_dedup   ON buyer_facts(account_id, dedup_key);
CREATE INDEX ix_facts_pending ON buyer_facts(account_id, am_decision, confidence DESC);
