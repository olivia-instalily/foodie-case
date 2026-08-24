"""
queries.py — the five analyses. Each maps to one slide.

Run after generate.py. The numbers are synthetic; the SQL is what you would
run against Foodie's warehouse.

  python queries.py
"""
import sqlite3, datetime as dt
import dials as D

db = sqlite3.connect("foodie.db"); db.row_factory = sqlite3.Row
TODAY      = dt.date(2026, 8, 18)
AGENT_LIVE = TODAY - dt.timedelta(days=30 * D.MONTHS_LIVE)
DECLINE_ON = TODAY - dt.timedelta(days=60)
W          = int(D.WINDOW_DAYS)

def head(n, t): print(f"\n{'':=<74}\n{n}.  {t}\n{'':=<74}")
def orderers(a):
    s = (a - dt.timedelta(days=W)).isoformat()
    return {r[0] for r in db.execute(
        "SELECT DISTINCT account_id FROM orders WHERE order_date BETWEEN ? AND ?",
        (s, a.isoformat()))}

PRE, NOW = orderers(DECLINE_ON), orderers(TODAY)

# ─────────────────────────────────────────────────────────────────────────
head(1, "REORDER RATE — two definitions, and what the window implies")
total = db.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]

def cohort(anchor):
    cur = orderers(anchor)
    prev = orderers(anchor - dt.timedelta(days=W + 1))
    return len(cur & prev) / len(prev)

print(f"  {'':<14}{'A: ordered / all':>20}{'B: cohort repeat':>20}")
for label, anchor, s in [("pre-decline", DECLINE_ON, PRE), ("current", TODAY, NOW)]:
    print(f"  {label:<14}{len(s)/total*100:>19.1f}%{cohort(anchor)*100:>19.1f}%")

print(f"""
  Definition A is accounts ordering divided by all accounts. B is the
  intersection — of accounts that ordered last window, what share ordered
  again. Comparing counts instead of accounts gives >100%, which is how the
  error surfaces.

  Window = {D.WINDOW_DAYS:.1f} days, solved not chosen. At these delivery cadences a
  30-day window puts ~96% of accounts in the numerator, so the case's 61%
  baseline is only consistent with a roughly weekly window.

  Consequence: the metric is dominated by cadence composition, not account
  health. An account stretching from a 7-day to an 11-day cycle drops out of
  the window while retaining ~90% of annual spend. Part of the 17-point
  decline may be accounts ordering less often rather than leaving — very
  different revenue implications, and Foodie cannot tell them apart.

  Accounts that stopped appearing: {D.ACCOUNTS_LOST_ORDER:,}  (17 pts of 4,000)""")

# ─────────────────────────────────────────────────────────────────────────
head(2, "EXPOSURE SPLIT — the query that decides product vs. supply")
print("""  Splits accounts by agent-era inquiry count, stratified by tier. The
  stratification matters: inquiry volume correlates with account size, so an
  unstratified split shows high-exposure accounts improving. That is a
  confound, not a finding.
""")

rows = db.execute(f"""
  SELECT a.account_id, a.tier,
         CASE WHEN COALESCE(SUM(i.agent_handled),0)=0 THEN 'none'
              WHEN COALESCE(SUM(i.agent_handled),0)<=2 THEN '1-2'
              ELSE '3+' END AS bucket
  FROM accounts a
  LEFT JOIN inquiries i ON i.account_id=a.account_id
       AND i.received_date >= '{AGENT_LIVE}'
  GROUP BY a.account_id""").fetchall()

groups = {}
for r in rows:
    groups.setdefault((r["tier"], r["bucket"]), []).append(r["account_id"])

print(f"  {'tier':<6}{'exposure':<10}{'accounts':>10}{'before':>10}{'after':>9}{'change':>10}")
for tier in "ABC":
    for b in ("none", "1-2", "3+"):
        ids = groups.get((tier, b), [])
        if len(ids) < 25: continue
        p = sum(i in PRE for i in ids) / len(ids)
        n = sum(i in NOW for i in ids) / len(ids)
        print(f"  {tier:<6}{b:<10}{len(ids):>10,}{p*100:>9.1f}%{n*100:>8.1f}%"
              f"{(n-p)*100:>9.1f}pt")

print(f"""
  Under scenario '{D.SCENARIO}'. Run generate.py with 'supply' and the decline is
  flat across exposure; with 'agent' it concentrates. Same aggregate 17-point
  drop either way — only the shape differs. That shape is what the query
  reads, and it is the difference between a product fix and a supply
  escalation.""")

# ─────────────────────────────────────────────────────────────────────────
head(3, "EDIT DEPTH BY CATEGORY — separating retrieval from generation")
print("""  Foodie reports one blended figure (23%). The case names the categories in
  'Common Edits' but the metric discards the taxonomy. Note that depth alone
  cannot separate the two defects: a wrong SKU usually forces a rewrite of
  the justification too, so a substance error can produce a large diff, and a
  tone fix can be small. That is the argument for category capture at the
  field level rather than a text diff.
""")
rows = db.execute("""
  SELECT edit_category cat, COUNT(*) n, AVG(edit_depth) depth
  FROM drafts WHERE edit_depth > 0 GROUP BY edit_category ORDER BY n DESC""").fetchall()
tot = sum(r["n"] for r in rows)
print(f"  {'category':<12}{'edits':>9}{'share':>9}{'mean depth':>13}")
for r in rows:
    print(f"  {r['cat']:<12}{r['n']:>9,}{r['n']/tot*100:>8.1f}%{r['depth']*100:>12.1f}%")

# ─────────────────────────────────────────────────────────────────────────
head(4, "UNSUBSCRIBE BY RELEVANCE — targeting, not frequency")
print(f"""  At {D.OUTBOUND_PER_AM:.0f} outbound messages per AM per month, nobody is being spammed.
  The question is whether unsubscribes concentrate among recipients for whom
  the pitched category was not a real buying pattern.
""")
rows = db.execute("""
  SELECT CASE was_relevant WHEN 1 THEN 'core category'
                           ELSE 'category flag only' END seg,
         COUNT(*) sends,
         1.0*SUM(converted)/COUNT(*) conv,
         1.0*SUM(unsubscribed)/COUNT(*) unsub,
         AVG(CASE WHEN was_edited THEN edit_depth END) depth
  FROM campaign_sends GROUP BY was_relevant ORDER BY was_relevant DESC""").fetchall()
print(f"  {'segment':<22}{'sends':>8}{'conversion':>13}{'unsubscribe':>14}{'edit depth':>13}")
for r in rows:
    print(f"  {r['seg']:<22}{r['sends']:>8,}{r['conv']*100:>12.1f}%"
          f"{r['unsub']*100:>13.2f}%{r['depth']*100:>12.1f}%")
print("""
  Edit depth is flat across both segments. The AM could not tell the
  difference at review — inbound has a specific question to check the answer
  against, outbound has none. The prose was fine. The send list was not.""")

# ─────────────────────────────────────────────────────────────────────────
head(5, "THE 84% — reweighted by what each interaction put at risk")
print("""  A blended score counts every interaction once. Accounts are not uniform,
  so the same failure on a top-tier and a long-tail account register
  identically and the ones that matter dilute into the mean.
""")
r = db.execute("""
  WITH d AS (SELECT dr.draft_id, a.annual_value,
                    CASE WHEN dr.edit_depth=0 THEN 1 ELSE 0 END clean
             FROM drafts dr JOIN accounts a USING(account_id))
  SELECT 1.0*SUM(clean)/COUNT(*) unw,
         SUM(clean*annual_value)/SUM(annual_value) wtd FROM d""").fetchone()
print(f"  unweighted 'clean draft' rate          {r['unw']*100:.1f}%")
print(f"  weighted by annual account value       {r['wtd']*100:.1f}%")

rows = db.execute("""
  SELECT a.tier, COUNT(*) n,
         1.0*SUM(dr.edit_depth>0)/COUNT(*) edited,
         1.0*SUM(CASE WHEN dr.draft_id IN
           (SELECT draft_id FROM draft_events WHERE event_type='discarded')
           THEN 1 ELSE 0 END)/COUNT(*) discarded
  FROM drafts dr JOIN accounts a USING(account_id)
  GROUP BY a.tier ORDER BY a.tier""").fetchall()
print(f"\n  {'tier':<7}{'drafts':>9}{'edited':>10}{'discarded':>12}")
for x in rows:
    print(f"  {x['tier']:<7}{x['n']:>9,}{x['edited']*100:>9.1f}%{x['discarded']*100:>11.1f}%")
print("""
  'Accuracy' also has no ground truth for a recommendation. A substitution is
  not right or wrong — it is accepted or declined. The honest metric is
  acceptance, below.""")

# ─────────────────────────────────────────────────────────────────────────
head(6, "SUBSTITUTION ACCEPT RATE — the leading indicator for the 75 days")
rows = db.execute("""
  SELECT CASE am_action WHEN 'replaced' THEN 'agent proposed, AM overrode'
                        ELSE 'agent proposed, sent as-is' END path,
         COUNT(*) n, 1.0*SUM(buyer_outcome='accepted')/COUNT(*) acc
  FROM substitutions GROUP BY am_action ORDER BY n DESC""").fetchall()
print(f"  {'path':<32}{'n':>8}{'accepted':>11}")
for r in rows:
    print(f"  {r['path']:<32}{r['n']:>8,}{r['acc']*100:>10.0f}%")
print("""
  Sits on the exception path, has real ground truth, moves in weeks. Reorder
  rate detects the same failure a quarter later — after the renewal vote.

  Caveat to state aloud: the gap between these two rates is the HYPOTHESIS
  encoded in the generator, not a discovery. A mechanism I specified cannot be
  validated by querying data I generated from it. What this demonstrates is
  the query and the schema it needs.""")
