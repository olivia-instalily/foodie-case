# Setup and workflow

Everything here runs on plain Python 3 and SQLite. No packages to install, no
server, no build step.

---

## 1 · Get it into VS Code

```bash
mkdir foodie-case && cd foodie-case
# drop dials.py, tiers.py, schema.sql, generate.py, queries.py in here
code .
```

**Extensions worth having:**
- **Python** (Microsoft) — runs files with the ▷ button
- **SQLite Viewer** (Florian Klampfer) — click `foodie.db` in the sidebar and
  browse tables. This is the one that makes the data feel real.
- **SQLTools** + **SQLTools SQLite** driver — if you want to write ad-hoc
  queries in a scratch file and run them against the db. Optional.

Nothing else. No virtualenv needed — nothing imports anything outside the
standard library.

---

## 2 · The four files and what each one is for

```
tiers.py      What makes an account an A, B, or C. Run it to see the revenue
              build-up reconcile against the case's $95M.

dials.py      Every invented assumption in one place, with ranges. Also
              computes everything derived from the case. Nothing else in the
              project invents a number.

schema.sql    The tables. Three decisions are commented as load-bearing —
              those comments are your answer to "define this as if you were
              briefing an engineer."

generate.py   Reads dials.py + schema.sql, writes foodie.db.

queries.py    Six analyses against foodie.db. Each maps to one slide.
```

**Read them in that order.** `tiers.py` is the argument, `dials.py` is the
inventory of assumptions, `schema.sql` is the design, `generate.py` is
plumbing, `queries.py` is the output.

---

## 3 · The normal loop

```bash
python tiers.py          # sanity-check the tier arithmetic
python dials.py          # see derived numbers + coverage sensitivity
python generate.py       # build foodie.db  (~20 seconds)
python queries.py        # run the six analyses
```

Change a dial, re-run `generate.py`, re-run `queries.py`. That's the whole
cycle. Nothing caches, nothing needs cleaning up.

---

## 4 · Turning the dials

Open `dials.py`. Three values, each with a stated range:

```python
DELIVERIES_PER_MONTH = {"A": 6.0, "B": 4.0, "C": 2.5}   # ±50%
VALUE_SKEW_TOP_20    = 0.55                              # 0.45–0.65
RECURRING_SHARE      = 0.70                              # 0.20–0.85
```

**Note:** now that `tiers.py` exists, `VALUE_SKEW_TOP_20` is redundant — the
skew *emerges* from the tier build-up at ~57%. Either delete the dial and
import from `tiers.py`, or keep it and note in the deck that the two agree
independently, which is a nice check.

To see what a dial moves without rebuilding the database:

```bash
python dials.py          # prints the sensitivity sweep
python tiers.py          # prints its own sensitivity table
```

For anything that needs the actual rows — reorder rate, exposure splits —
change the dial, `python generate.py`, `python queries.py`.

---

## 5 · The scenario switch (the important one)

`SCENARIO` in `dials.py` isn't a dial. It's a hypothesis you render.

```bash
python generate.py agent    && python queries.py > out-agent.txt
python generate.py supply   && python queries.py > out-supply.txt
python generate.py mixed    && python queries.py > out-mixed.txt
```

All three reproduce the case's 61% → 44%. Only the **shape** differs. Diff
query 2 across the three files and you have the slide: *the same aggregate
decline, three causes, and the query that distinguishes them.*

```bash
diff out-agent.txt out-supply.txt
```

---

## 6 · Browsing the data by hand

Click `foodie.db` in the VS Code sidebar with SQLite Viewer installed. Or:

```bash
sqlite3 foodie.db
```

```sql
.tables
.schema orders

-- the 15 named buyers that also appear in the prototype
SELECT account_id, name, tier, round(annual_value) FROM accounts
WHERE account_id < 20000 ORDER BY annual_value DESC;

-- one account's whole story
SELECT channel, COUNT(*), round(SUM(order_value))
FROM orders WHERE account_id = 10428 GROUP BY channel;

-- draft lifecycle for one account
SELECT d.draft_id, e.event_type, e.occurred_at
FROM drafts d JOIN draft_events e USING(draft_id)
WHERE d.account_id = 10428 ORDER BY d.draft_id, e.occurred_at LIMIT 20;
```

That last query is worth running before you present. It's what the
append-only event log actually looks like, and being able to describe it from
memory is the difference between having a schema and having designed one.

---

## 7 · Wiring the prototype to the same data — deliberately partial

**There is no `export_fixtures.py`, and there shouldn't be.**

The database stores SKUs as generated codes (`SKU-0142`). The prototype needs
real product names (`Rustichella d'Abruzzo paccheri`) or the demo reads as
placeholder. Exporting generated order history into the prototype would make
the prototype worse, not more consistent.

**What actually needs to agree** is the handful of values that appear in both
places: account name, tier, annual value, contact. Those already match,
because `generate.py` seeds the 15 named accounts from the same list the
prototype uses.

To pull them for pasting:

```bash
python3 -c "
import sqlite3
db=sqlite3.connect('foodie.db')
for r in db.execute('''SELECT account_id,name,tier,round(annual_value)
  FROM accounts WHERE account_id<20000 ORDER BY annual_value DESC'''):
    print(r)
"
```

Keep the SKU-level detail in the prototype hand-authored. If asked whether the
two match: *same accounts, same tiers, same values; product-level detail in the
prototype is hand-authored because generated SKU codes wouldn't demo well.*

---

## 8 · What to ship, what to leave out

**Ship:** `tiers.py`, `dials.py`, `schema.sql`, `generate.py`, `queries.py`,
and a text file of the query output.

**Leave out:** `foodie.db` itself. It's 22MB of binary nobody will open, and
the generator reproduces it in twenty seconds. Say so in the README — "run
`python generate.py` to rebuild" reads better than shipping the artifact.

---

## 9 · One habit worth keeping

Every time a number appears in a slide, be able to say which of the four it
is: **given**, **derived**, **invented**, or **emergent**.

That last category is the one that earns the most credit and it's new as of
`tiers.py` — the 57% revenue concentration isn't something you assumed, it's
what falls out of three separately-argued inputs. Being able to point at a
number and say "I didn't choose that, it's what the arithmetic produced" is a
different kind of claim than the other three.