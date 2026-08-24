# Foodie & Co. — AM Workspace case study

A product case study for InstaLily's Product Associate role. The fictional
client, **Foodie & Co.**, is a $95M NY specialty-food distributor: 80 account
managers, 4,000 restaurant accounts, AI agents live for four months inside an
internal tool (the **AM Workspace**) plus a leadership dashboard (**PulseBoard**).
Two agent workflows — inbound substitution inquiries (~2,400/mo) and outbound
pre-order campaigns (~800/mo). The contract renews in 75 days and the numbers
have slipped. The brief asked for a diagnosis, an interactive prototype (the
current tool, a fix to it, and one new workflow), and a presentation.

The repo is two halves that meet at `foodie.db`:

1. **A data model** (Python) that turns the ~30 numbers the case states into a
   defensible synthetic dataset and builds `foodie.db`.
2. **A prototype** (`index.html` + `api/`) that reads `foodie.db` live, so every
   figure on screen is a real query result rather than a hand-typed mock.

## Run it

```bash
# prototype (needs foodie.db, which is committed)
npm install
node scripts/serve-local.js          # → http://localhost:3000

# rebuild the database from the model
python generate.py                   # writes foodie.db (~20s)

# the analysis behind the slides
python tiers.py                      # tier build-up + revenue reconciliation
python dials.py                      # derived numbers + sensitivity sweep
python queries.py                    # six analyses, each mapped to a slide
```

The Python is standard-library only (see `requirements.txt`). Deploy with
`vercel --prod`; `vercel.json` bundles `foodie.db` into the query functions.
The optional "generate draft" button calls Claude via `api/generate.js` and
needs `ANTHROPIC_API_KEY` (copy `.env.example` to `.env`); everything else works
without a key.

## What's where

**Data model** — stdlib Python, read in this order:
| file | what it is |
|---|---|
| `dials.py` | Every invented assumption and every derived number, in one place. The single source of "where did this come from." Run it. |
| `tiers.py` | The A/B/C tier build-up. Revenue concentration is computed here, not assumed. |
| `schema.sql` | The database schema. Three design decisions are commented as load-bearing. |
| `generate.py` | Reads `dials.py` + `schema.sql`, writes `foodie.db`. |
| `queries.py` | Six analyses against `foodie.db`, each mapped to one slide. |

**Prototype** — no build step, opens from a static host:
| file | what it is |
|---|---|
| `index.html` | Single-file clickable prototype: the current tool, the fix (a mode toggle), the new Daybook workflow, and a guided walkthrough. One large file on purpose — no framework, servable as a static asset. |
| `api/data.js`, `api/account.js`, `api/book.js` | Serverless functions. Open `foodie.db` read-only and return the JSON the UI renders. |
| `api/generate.js` | Optional. Calls Claude to draft a reply/note. Needs `ANTHROPIC_API_KEY`. |
| `api/_db.js` | Shared read-only DB connection. |
| `foodie.db` | The SQLite database, **committed** so the prototype shows real numbers on first open without running the generator. Reproduce it with `python generate.py`. |
| `fixtures.json` | Precomputed `/api/data` payload — the `file://` fallback when no serverless runtime is available. |
| `scripts/serve-local.js` | Local server mirroring Vercel routing (no `vercel dev` needed). |
| `scripts/dump-fixtures.js` | Regenerates `fixtures.json` from the live handler. |

**Config:** `vercel.json`, `package.json`. **`docs/`:** the working notes — the
build brief (`prompt.md`), the Python workflow (`SETUP.md`), the presentation
script, and the source transcripts behind the fixtures.

## Invented vs. given

The discipline the case rewards is being able to say which kind each number is:

- **Given** — the ~30 figures the brief states (revenue, account/AM counts, edit
  rates, reorder 61% → 44%). Tagged `CASE` in `dials.py`.
- **Invented** — three behavioural dials (deliveries per month, line items per
  order, price per line) plus a couple of structural shares. Each carries a
  stated range in `dials.py`, and the argument is built to survive that range.
- **Derived / emergent** — everything else. The revenue concentration in
  particular *falls out* of the tier arithmetic (built revenue lands at $95.6M
  against the case's $95M); it was not assumed and then distributed to match.

In the **prototype**, every number is a query result against `foodie.db`, with
two deliberately hardcoded, clearly-labelled exceptions: the **84% "Agent
Accuracy Score"** (a case-given figure) and the PulseBoard **average response
time** (an estimate — no inbound timing is captured, so the card is tagged
`est.` to say so). Product names and buyer message text are hand-authored — the
database stores SKUs as generated codes (`SKU-0142`), so real names live in the
HTML — while all account-level numbers (tier, annual value, cadence) come from
the database.
