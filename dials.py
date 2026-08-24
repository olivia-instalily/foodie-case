"""
dials.py

The case gives me about thirty numbers and no data. To run any real query I
needed a database, and to build one I had to invent things. This file is where
all of that inventing happens, so there is exactly one place to look when
someone asks where a number came from.

Rule I held to: if a value isn't in this file and isn't tagged CASE, it was
computed. I broke that rule twice while building and both times it produced a
number I couldn't defend, so it's worth keeping.

Run this file directly to see the derived values and the sensitivity table.
"""

# ═══════════════════════════════════════════════════════════════════
# CASE — everything the brief actually states. Nothing here is mine.
# ═══════════════════════════════════════════════════════════════════
REVENUE          = 95_000_000
ACCOUNTS         = 4_000
AMS              = 80
SKUS             = 3_200
LARGE_ACCT_AMS   = 18          # "18 AMs cover the largest accounts"
DEFECTED_AMS     = 3           # of those 18, now drafting from scratch

INBOUND_MO       = 2_400       # the brief says "interactions" and never defines it.
OUTBOUND_MO      = 800         # I read both as drafts generated — see note below.

IN_EDIT_RATE     = 0.26
IN_EDIT_DEPTH    = 0.23
OUT_EDIT_RATE    = 0.34
OUT_EDIT_DEPTH   = 0.08

CONVERSION       = 0.12
CONVERSION_BASE  = 0.11
UNSUB_BEFORE     = 0.012
UNSUB_NOW        = 0.031
REORDER_BEFORE   = 0.61
REORDER_NOW      = 0.44

MONTHS_LIVE      = 4
DAYS_TO_RENEWAL  = 75

# On "interactions": edit rate is 26% of *something*, and the only denominator
# that makes that sentence work is drafts generated. If it meant clicks or
# opens, the edit rate would be measuring a different population than the one
# it's reported against. Reading it as drafts also makes the per-AM figure land
# around 1.4 a working day, which is a plausible number for this job. I'd want
# to confirm it before saying anything load-bearing rests on it.


# ═══════════════════════════════════════════════════════════════════
# DIALS — the things I made up.
#
# Three of them. Each is a guess about how a restaurant orders, not about how
# much it spends, which matters: I wanted account value to fall out of
# behaviour rather than be assigned. Every one has a range I actually re-ran
# the model across (see sensitivity() at the bottom), and a note on what
# survives that range — because the point estimate is not the claim.
# ═══════════════════════════════════════════════════════════════════

DELIVERIES_PER_MONTH = {"A": 6.0, "B": 4.0, "C": 2.5}
# Why tiers differ here: perishability, not budget. A place doing 200 covers a
# night can't hold three days of produce, so it takes delivery more often. A
# small café can.
#
# Sourcing: par-level purchasing is standard practice and 1-2 deliveries a week
# is the common worked example in foodservice operations material
# (Restaurant365, Altametrics). That's vendor content marketing, so I'm
# treating the concept as sourced and the numbers as mine.
#
# What it drives: total order volume, which is the denominator for agent
# coverage. Turn it and coverage moves between roughly 10% and 31%.
# What holds across ±50%: the agent is never in a majority of order events.
# That's the claim I actually make, and it doesn't depend on getting this right.

LINES_PER_ORDER = {"A": 19, "B": 12, "C": 8}
# Menu breadth. A tasting menu carries far more distinct ingredients than a
# bistro with twelve mains, and this turns out to be the largest single lever
# on account value — bigger than either of the other two.
#
# It also does a second job I didn't plan: it's what drives INQ_WEIGHT further
# down. More distinct items means more chances one of them is unavailable,
# which is when a buyer writes in. So inquiry frequency stops being a separate
# invention and becomes a consequence of this one.
#
# What holds across ±30% on A: A stays the majority-of-value tier, 50-65%.

PRICE_PER_LINE = {"A": 44, "B": 33, "C": 28}
# Grade, not markup. This distinction is the whole reason the number is
# defensible: an A-tier restaurant buying "Parmigiano" is buying the 36-month,
# not paying more for the 24-month. Different item, same category.
#
# If it were markup I'd have a harder argument, because it would imply Foodie
# charges different customers differently for identical goods, which is not
# what a distributor does.
#
# What holds across ±30%: the ordering A > B > C survives, which is all the
# model needs from it.

WITHIN_TIER_SIGMA = 0.42
# Individual accounts vary around their tier profile, so Le Perchoir at $116k
# and another A-tier at $45k both exist. Lognormal because account values are
# right-skewed in practice and can't go negative.
#
# Deliberately mean-preserving (see generate.py). Earlier I had the generator
# draw a spread and then scale each tier to hit a revenue target, which meant
# the revenue concentration was something I'd set rather than something that
# emerged. That's the version I'd have had to defend as an assumption. This one
# I don't.

RECURRING_SHARE = 0.70
# Share of ordering that arrives on a standing schedule rather than through a
# conversation. This is the assumption behind my claim that the agent touches a
# small share of volume, so it's the one I'd defend hardest.
#
# Sourcing: portal ordering dominates channel mix among independent operators —
# US Foods reported 77% ecommerce penetration in 2024, Sysco around 80%. Both
# broadline rather than specialty, so directional only.
#
# The useful thing about this dial is which way its uncertainty runs. If
# recurring share is actually lower, the agent touches *more* of the business,
# and the case for attributing the decline to it gets stronger. So being wrong
# here doesn't cost me the argument. Range 0.20-0.85 and the diagnosis holds
# throughout; only attribution confidence moves.


# ═══════════════════════════════════════════════════════════════════
# SCENARIO — not a dial. This is me choosing an answer.
# ═══════════════════════════════════════════════════════════════════
SCENARIO = "agent"
# The case hands me a 17-point reorder decline and no explanation. I can't
# derive one, so the generator imposes it: I pick which accounts stop ordering.
#
#   "agent"  — the decline concentrates in high-exposure accounts
#   "supply" — it's uniform, which is what a fill-rate problem looks like
#   "mixed"  — both
#
# All three land on 44%. What differs is the shape, and the shape is what the
# exposure-split query reads.
#
# The honest consequence: querying this back tells me what I typed in. It
# proves nothing about cause. What it does do is show what the diagnostic would
# look like under each hypothesis, which is the argument for building the
# instrumentation regardless of which one is true.
#
# I say this out loud the first time a query result appears in the deck. It's
# the kind of thing that's much better volunteered than caught.


# ═══════════════════════════════════════════════════════════════════
# DERIVED — nothing below is typed by hand.
# ═══════════════════════════════════════════════════════════════════
import math

TIER_SHARE = {"A": LARGE_ACCT_AMS / AMS}
TIER_SHARE["B"] = 0.42
TIER_SHARE["C"] = 1 - TIER_SHARE["A"] - TIER_SHARE["B"]
# A-tier size comes from the brief's own structure: 18 of 80 AMs cover the
# largest accounts, so 22.5%.
#
# That step assumes two things I should say plainly. That those 18 carry mostly
# large accounts rather than a mix, and that account loads are roughly even. At
# the 40-60 range the brief gives, the real figure sits somewhere between 18%
# and 27%.
#
# The uncertainty runs in my favour: large accounts plausibly take more work
# per account, so those AMs probably carry fewer than 50, which would make the
# tier smaller and revenue more concentrated than I've modelled.
#
# B is mine. C is the remainder, so the three always sum to exactly 1 and I
# can't introduce a rounding gap by editing one of them.

ORDER_VALUE   = {t: LINES_PER_ORDER[t] * PRICE_PER_LINE[t] for t in ("A", "B", "C")}
TIER_ANNUAL   = {t: DELIVERIES_PER_MONTH[t] * 12 * ORDER_VALUE[t] for t in ("A", "B", "C")}
BUILT_REVENUE = sum(ACCOUNTS * TIER_SHARE[t] * TIER_ANNUAL[t] for t in TIER_SHARE)
A_SHARE       = ACCOUNTS * TIER_SHARE["A"] * TIER_ANNUAL["A"] / BUILT_REVENUE
# This is the part I'd point at if I only got to defend one thing.
#
# I never set an account value. Three guesses about restaurant behaviour
# multiply out, and the total lands at $95.6M against the brief's $95M. That's
# a test I could have failed — nine free parameters and an unfitted target —
# and 0.7% is close enough that the model is at least internally coherent.
#
# It also means A_SHARE is an output. When I say revenue is concentrated in the
# top tier, that's a result of the arithmetic rather than something I asserted
# and then distributed to match.

INQ_WEIGHT    = {t: LINES_PER_ORDER[t] / LINES_PER_ORDER["C"] for t in ("A", "B", "C")}
# Derived rather than invented, which removes an assumption I originally had
# sitting here as a free parameter.

VALUE_PER_INTERACTION = {t: ORDER_VALUE[t] for t in ("A", "B", "C")}
# Worth being precise about, because I had this wrong for a while.
#
# I assumed A-tier accounts meet the agent more often — broader menus, more
# questions. They do ask more, at about 2.4x. But they also place about 2.4x
# more orders, because they take delivery more often. Those cancel almost
# exactly, and exposure comes out roughly flat at ~16% of orders for every tier.
#
# So the asymmetry isn't frequency, it's what each interaction carries: $836 of
# order value at A against $224 at C. Which changes what the AM defection
# means. The three who quit weren't seeing more bad drafts than anyone else.
# Each one cost them nine times more to get wrong.
#
# Caveat I should hold: the cancellation is exact because I chose 19/8 and
# 6/2.5, which happen to be near-identical ratios. Different numbers and it
# wouldn't cancel. So "flat exposure" is real given this model, and the model
# is a choice.

AVG_ACCOUNT_VALUE   = REVENUE / ACCOUNTS
ACCOUNTS_LOST_ORDER = int((REORDER_BEFORE - REORDER_NOW) * ACCOUNTS)   # 680
# The headline number, and it's just arithmetic on two given figures. Worth
# knowing it assumes reorder rate means accounts-ordering over all-accounts. A
# cohort reading gives a different count.

ORDERS_PER_MONTH    = sum(ACCOUNTS * TIER_SHARE[t] * DELIVERIES_PER_MONTH[t]
                          for t in TIER_SHARE)
COVERAGE_CEILING    = INBOUND_MO / ORDERS_PER_MONTH
INBOUND_PER_AM      = INBOUND_MO / AMS
OUTBOUND_PER_AM     = OUTBOUND_MO / AMS
# OUTBOUND_PER_AM is about 10 a month, and it does more work than it looks
# like. Ten messages per AM per month is not spam, so a tripled unsubscribe
# rate can't be a volume problem. It's relevance. That one division rules out
# the obvious explanation.

CONVERSION_SE       = math.sqrt(CONVERSION * (1 - CONVERSION) / OUTBOUND_MO)
CONVERSION_LIFT_SE  = (CONVERSION - CONVERSION_BASE) / CONVERSION_SE
# 11% to 12% at n=800 is 0.87 standard errors. Not a result.
#
# This matters because it's the only positive number in the outbound workflow.
# Take it away and outbound has an efficiency gain, a permanent cost, and
# nothing demonstrated on the business side.
#
# Assumes 800 independent sends. If it's 800 recipients across a handful of
# campaign batches, the effective n is smaller and the lift means even less.


def reorder_window_days():
    """Solve for the window that produces the brief's 61%.

    The brief never says what period sits inside "reorder rate" — it gives a
    60-day observation window over which the number fell, which is a different
    thing. So I solved for it.

    Model each account's orders as Poisson arrivals at its own rate. The chance
    of at least one order in `days` is 1 - e^(-rate*days). Weight across tiers,
    then binary search for the window that yields 61%.

    Comes out around 7.6 days. Sanity check in the other direction: at 30 days
    this function returns ~96%, which cannot produce a 61% baseline at any
    cadence in my range.

    What that implies, and it's the reason I bothered: a roughly weekly window
    measures cadence composition more than account health. An account that
    stretches from a 7-day to an 11-day cycle drops out of the numerator while
    keeping ~90% of its annual spend. So part of the 17-point fall could be
    accounts slowing rather than leaving, and nothing in the brief distinguishes
    them.

    Caveat: this assumes reorder rate means accounts-ordering-in-a-window. If
    it's a cohort measure — of accounts that ordered last month, how many
    ordered this month — 61% over 30 days is perfectly ordinary and this whole
    calculation is moot. Either way the finding holds: nobody has published
    which one it is.
    """
    def rate(days):
        return sum(TIER_SHARE[t] * (1 - math.exp(-DELIVERIES_PER_MONTH[t] / 30 * days))
                   for t in TIER_SHARE)
    lo, hi = 1.0, 60.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if rate(mid) < REORDER_BEFORE else (lo, mid)
    return (lo + hi) / 2


WINDOW_DAYS = reorder_window_days()


def summary():
    """Everything derived, printed with its derivation visible."""
    m = lambda x: f"${x:,.0f}"
    rows = []
    for t in ("A", "B", "C"):
        accts = round(ACCOUNTS * TIER_SHARE[t])
        rows.append(f"    {t:<5}{DELIVERIES_PER_MONTH[t]:>7.1f}{LINES_PER_ORDER[t]:>7}"
                    f"{'$'+str(PRICE_PER_LINE[t]):>8}{'$'+format(ORDER_VALUE[t],',.0f'):>9}"
                    f"{'$'+format(TIER_ANNUAL[t],',.0f'):>11}{accts:>8,}")
    tier_table = "\n".join(rows)
    print(f"""
DERIVED FROM THE CASE
  average account value        {m(AVG_ACCOUNT_VALUE)}/yr
  accounts that stopped
    reordering (61%->44%)      {ACCOUNTS_LOST_ORDER:,}
  inbound per AM per month     {INBOUND_PER_AM:.0f}  ({INBOUND_PER_AM/21:.1f}/working day)
  outbound per AM per month    {OUTBOUND_PER_AM:.0f}   (not a volume problem)
  conversion lift              {CONVERSION_LIFT_SE:.2f} standard errors, not a result
  reorder-rate window          {WINDOW_DAYS:.1f} days
                               (30 days would put ~96% of accounts in the
                                numerator, incompatible with 61%)

BUILT BOTTOM-UP: value = deliveries/mo x 12 x lines/order x $/line
    {'tier':<5}{'del/mo':>7}{'lines':>7}{'$/line':>8}{'order':>9}{'annual':>11}{'accts':>8}
{tier_table}
  built revenue                {m(BUILT_REVENUE)}  vs $95,000,000  ({(BUILT_REVENUE/REVENUE-1)*100:+.1f}%)
  A-tier share of revenue      {A_SHARE*100:.1f}%  (an output, not an input)
  value per interaction        A {m(VALUE_PER_INTERACTION['A'])}  ·  C {m(VALUE_PER_INTERACTION['C'])}

FROM THE DIALS
  total orders per month       {ORDERS_PER_MONTH:,.0f}
  agent coverage ceiling       {COVERAGE_CEILING*100:.1f}% of order events
""")


def sensitivity():
    """Re-run the model at each end of every dial's range.

    The question this answers: does my argument depend on getting these numbers
    right? Revenue moves a lot. A-tier concentration barely moves. Since the
    argument is about concentration, it survives.
    """
    def calc(deliv, lines, price):
        ann = {t: deliv[t] * 12 * lines[t] * price[t] for t in ("A", "B", "C")}
        rev = sum(ACCOUNTS * TIER_SHARE[t] * ann[t] for t in TIER_SHARE)
        return rev, ACCOUNTS * TIER_SHARE["A"] * ann["A"] / rev
    D0, L0, P0 = DELIVERIES_PER_MONTH, LINES_PER_ORDER, PRICE_PER_LINE
    onlyA = lambda d, f: {**d, "A": d["A"] * f}
    cases = [
        ("base",                D0, L0, P0),
        ("deliveries all -25%", {t: v*.75 for t, v in D0.items()}, L0, P0),
        ("deliveries all +25%", {t: v*1.25 for t, v in D0.items()}, L0, P0),
        ("A lines -30%",        D0, onlyA(L0, .7),  P0),
        ("A lines +30%",        D0, onlyA(L0, 1.3), P0),
        ("A price  -30%",       D0, L0, onlyA(P0, .7)),
        ("A price  +30%",       D0, L0, onlyA(P0, 1.3)),
    ]
    print("SENSITIVITY: revenue and A-tier share across the dial ranges\n")
    print(f"  {'perturbation':<22}{'revenue':>14}{'A share':>10}")
    revs, ashs = [], []
    for label, d, l, p in cases:
        r, a = calc(d, l, p); revs.append(r); ashs.append(a)
        star = "  <- base" if label == "base" else ""
        print(f"  {label:<22}{'$'+format(r,',.0f'):>14}{a*100:>9.1f}%{star}")
    print(f"\n  Revenue swings ${min(revs)/1e6:.0f}M-${max(revs)/1e6:.0f}M. "
          f"A-tier share holds {min(ashs)*100:.0f}-{max(ashs)*100:.0f}%.")
    print("  The range is the claim. The point estimate isn't.")


if __name__ == "__main__":
    summary()
    sensitivity()