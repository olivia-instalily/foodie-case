"""
tiers.py — what makes an account an A, B, or C, built from the ground up.

WHY THIS EXISTS
  The first version defined tiers by revenue share ("top 20% = 55% of
  revenue") and then assigned them a delivery cadence. That's circular: the
  answer is asserted and there's nothing to defend.

  This version defines a tier by three observable restaurant characteristics
  and lets annual value — and the revenue skew — fall out of the arithmetic.
  Every input is separately arguable, and the skew becomes an OUTPUT you can
  check against the case rather than a dial you have to justify.

THE BUILD-UP
  annual value = deliveries/yr  ×  line items per order  ×  price per line

  Each factor has a different reason for differing by tier:

  deliveries/yr        A high-cover kitchen turns product faster and can't hold
                       inventory, so it takes delivery more often. Perishability,
                       not spending power.

  line items/order     Menu breadth. A tasting menu carries more distinct
                       ingredients than a bistro with twelve mains. This is the
                       biggest single driver of account value, and it's also
                       why larger accounts generate more inquiries — more SKUs
                       means more chances something is out of stock or needs a
                       special.

  price per line       Grade, not markup. The same category at a higher tier
                       means 36-month Parmigiano instead of 24, Alba truffle
                       instead of summer, A5 instead of choice. Foodie isn't
                       charging more for the same item; the item is different.

WHAT THIS BUYS YOU
  * revenue skew is derived, not invented
  * inquiry rate is derived from line-item count, not invented
  * the tier definition is a sentence you can say out loud
"""

# ═══════════════════════════════════════════════════════════════════
# CASE
# ═══════════════════════════════════════════════════════════════════
REVENUE  = 95_000_000
ACCOUNTS = 4_000
AMS      = 80
LARGE_AMS = 18          # AMs covering the largest accounts

# ═══════════════════════════════════════════════════════════════════
# TIER SHARES — [DERIVED] from the case's own AM structure
#
# 18 of 80 AMs cover the largest accounts. At 40–60 accounts each (case),
# that's ~900 accounts, or 22.5% of the book. Foodie itself organises around
# this split, so the A tier's size is not my invention.
# ═══════════════════════════════════════════════════════════════════
SHARE = {"A": LARGE_AMS / AMS}          # 0.225
SHARE["B"] = 0.42                        # [INVENTED] range 0.35–0.50
SHARE["C"] = 1 - SHARE["A"] - SHARE["B"]

# ═══════════════════════════════════════════════════════════════════
# THE THREE FACTORS — [INVENTED], each separately arguable
# ═══════════════════════════════════════════════════════════════════
PROFILE = {
    #        deliveries   lines    price     what this restaurant is
    #         per month  /order   /line
    "A": dict(deliveries=6.0,  lines=19, price=44,
              desc="High-cover fine dining / tasting menu. Broad menu, premium "
                   "grades, can't hold inventory."),
    "B": dict(deliveries=4.0,  lines=12, price=33,
              desc="Established neighbourhood restaurant. Focused menu, mixed "
                   "grades, twice-weekly delivery."),
    "C": dict(deliveries=2.5,  lines=8,  price=28,
              desc="Small independent / café. Narrow menu, entry grades, "
                   "weekly or fortnightly delivery."),
}
# Ranges to test: deliveries ±50%, lines ±30%, price ±25%.

# ═══════════════════════════════════════════════════════════════════
# DERIVED — the build-up
# ═══════════════════════════════════════════════════════════════════
def compute():
    out = {}
    for t, p in PROFILE.items():
        n            = round(ACCOUNTS * SHARE[t])
        orders_yr    = p["deliveries"] * 12
        order_value  = p["lines"] * p["price"]
        annual_value = orders_yr * order_value
        out[t] = dict(
            accounts=n,
            orders_per_year=orders_yr,
            order_value=order_value,
            annual_value=annual_value,
            tier_revenue=annual_value * n,
            **p)
    total = sum(v["tier_revenue"] for v in out.values())
    for v in out.values():
        v["revenue_share"] = v["tier_revenue"] / total
    return out, total


def inquiry_weights(tiers):
    """Inquiry rate tracks menu breadth: more distinct line items means more
    chances something is unavailable or needs a substitution. Normalised so C = 1."""
    base = tiers["C"]["lines"]
    return {t: round(v["lines"] / base, 2) for t, v in tiers.items()}


def report():
    tiers, total = compute()
    m  = lambda x: f"${x:,.0f}"
    pc = lambda x: f"{x*100:.1f}%"

    print("TIER PROFILES\n")
    for t in "ABC":
        v = tiers[t]
        print(f"  {t} — {v['desc']}")
        print(f"      {v['accounts']:,} accounts  ·  {v['deliveries']:.1f} deliveries/mo  ·  "
              f"{v['lines']} lines/order  ·  ${v['price']}/line\n")

    print(f"{'':-<70}")
    print(f"  {'':<4}{'accounts':>10}{'order value':>14}{'annual value':>15}{'tier revenue':>16}")
    print(f"{'':-<70}")
    for t in "ABC":
        v = tiers[t]
        print(f"  {t:<4}{v['accounts']:>10,}{m(v['order_value']):>14}"
              f"{m(v['annual_value']):>15}{m(v['tier_revenue']):>16}")
    print(f"{'':-<70}")
    print(f"  {'':<4}{ACCOUNTS:>10,}{'':>14}{'':>15}{m(total):>16}")

    print(f"\nRECONCILIATION AGAINST THE CASE")
    print(f"  generated revenue                {m(total)}")
    print(f"  case revenue                     {m(REVENUE)}")
    print(f"  variance                         {(total/REVENUE-1)*100:+.1f}%")
    print(f"  average account value            {m(total/ACCOUNTS)}"
          f"   (case implies {m(REVENUE/ACCOUNTS)})")

    print(f"\nWHAT EMERGES — no longer a dial")
    a = tiers["A"]
    print(f"  A tier is {pc(SHARE['A'])} of accounts and {pc(a['revenue_share'])} of revenue")
    print(f"  top-tier to bottom-tier value ratio   "
          f"{tiers['A']['annual_value']/tiers['C']['annual_value']:.1f}x")
    print(f"  -> the $23,750 average sits between a {m(tiers['C']['annual_value'])} "
          f"account\n     and a {m(tiers['A']['annual_value'])} one. The mean describes nobody.")

    print(f"\nINQUIRY WEIGHTS — derived from menu breadth, not invented")
    w = inquiry_weights(tiers)
    print(f"  {w}")
    tot_w = sum(SHARE[t]*w[t] for t in w)
    print(f"  implied share of the 2,400 monthly inquiries:")
    for t in "ABC":
        share = SHARE[t]*w[t]/tot_w
        per_acct = 2400*share/tiers[t]['accounts']
        print(f"    {t}: {pc(share)} of inquiries  ->  {per_acct:.2f} per account per month"
              f"   ({per_acct/tiers[t]['deliveries']*100:.0f}% of its orders)")

    print(f"\n  NOTE — that last column comes out FLAT across tiers, and that")
    print(f"  matters. Inquiry rate scales with menu breadth (2.4x A over C) and")
    print(f"  order count scales with delivery frequency (2.4x A over C), so the")
    print(f"  two cancel: every account meets the agent on roughly the same")
    print(f"  FRACTION of its orders.")
    print(f"\n  So the exposure asymmetry is not frequency. It is value per")
    print(f"  interaction. One agent-handled inquiry sits on:")
    for t in "ABC":
        v = tiers[t]
        print(f"    {t}: {m(v['order_value']):>7} of order value  ·  "
              f"{m(v['annual_value']):>8} of annual relationship")
    print(f"\n  {tiers['A']['annual_value']/tiers['C']['annual_value']:.0f}x more exposure per interaction, at the same interaction")
    print(f"  frequency. A blended accuracy score weights those identically —")
    print(f"  which is why the 18 AMs on the largest accounts concluded first")
    print(f"  that the drafts weren't worth the time saved. Not because they")
    print(f"  saw more of them. Because each one cost more to get wrong.")


def sensitivity():
    print(f"\n\nSENSITIVITY — does the revenue reconciliation survive the ranges?\n")
    print(f"  {'variant':<34}{'revenue':>14}{'vs case':>10}{'A share':>10}")
    import copy
    base = copy.deepcopy(PROFILE)
    cases = [
        ("base", {}),
        ("deliveries -25% all tiers",    {"all": ("deliveries", 0.75)}),
        ("deliveries +25% all tiers",    {"all": ("deliveries", 1.25)}),
        ("A lines 19 -> 15",             {"A": ("lines", 15/19)}),
        ("A lines 19 -> 23",             {"A": ("lines", 23/19)}),
        ("A price 44 -> 36",             {"A": ("price", 36/44)}),
        ("C deliveries 2.5 -> 1.5",      {"C": ("deliveries", 1.5/2.5)}),
    ]
    for label, changes in cases:
        for t in PROFILE: PROFILE[t] = dict(base[t])
        for k, (field, mult) in changes.items():
            targets = PROFILE if k == "all" else {k: PROFILE[k]}
            for t in targets: PROFILE[t][field] = base[t][field] * mult
        tiers, total = compute()
        print(f"  {label:<34}${total/1e6:>12,.1f}M{(total/REVENUE-1)*100:>9.0f}%"
              f"{tiers['A']['revenue_share']*100:>9.0f}%")
    for t in PROFILE: PROFILE[t] = dict(base[t])
    print(f"\n  The A tier holds 50–65% of revenue across every variant. That")
    print(f"  concentration is the durable claim; the point estimate is not.")


if __name__ == "__main__":
    report()
    sensitivity()
