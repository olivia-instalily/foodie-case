"""
generate.py, build foodie.db

WHAT THIS DOES
  Reproduces the aggregates the case publishes, so the queries in queries.py
  execute and return plausible numbers.

WHAT IT DOES NOT DO
  Explain the reorder decline. The case gives the 17-point drop; this script
  imposes it under a chosen SCENARIO ('agent' / 'supply' / 'mixed'). Running
  the exposure-split query under each scenario shows what the diagnostic would
  look like if that hypothesis were true. The data is invented; the query is
  what you would run against Foodie's warehouse.

USAGE
  python generate.py            # uses SCENARIO from dials.py
  python generate.py supply     # override
"""
import sqlite3, random, sys, math, json, datetime as dt
from pathlib import Path
import dials as D

SEED = 20260818
random.seed(SEED)          # fixed: screenshots must match the live demo

TODAY      = dt.date(2026, 8, 18)
START      = TODAY - dt.timedelta(days=365)
AGENT_LIVE = TODAY - dt.timedelta(days=30 * D.MONTHS_LIVE)
DECLINE_ON = TODAY - dt.timedelta(days=60)          # the 60-day slide

# [FIX] Whether the captured record (buyer_facts / bias / impressions) is
# populated. Source documents and substitution history exist EITHER way, the
# only difference between the current and fixed states is whether anything was
# read out of the documents. One DB serves both: current-mode queries never
# touch the record tables. Set False to inspect a bare current-state build.
FACTS_SEEDED = True

# Calibration constants, solved rather than chosen. Inquiry-driven orders add
# order-days beyond the cadence dial, so the raw generated reorder rate
# overshoots the case's 61%. These two constants pull it onto the published
# figures. They are fitting the DATASET to the case, not fitting a model to
# a conclusion.
CADENCE_CAL   = 0.8900      # -> pre-decline reorder rate = 61%
# Average drop is solved PER SCENARIO so all three land on the case's 44%.
# They differ because a concentrated drop removes more accounts from a short
# window than the same average spread uniformly, the metric is non-linear in
# how concentrated the damage is. Worth knowing: two businesses with identical
# average decline can report different reorder rates.
AVG_DROP_BY_SCENARIO = {"agent": 0.352, "supply": 0.442, "mixed": 0.424}

CATEGORIES = ["Specialty pasta", "Cheese & charcuterie", "Truffle & mushroom",
              "Caviar & roe", "Oils & vinegars", "Center of plate",
              "Dairy", "Pantry", "Nuts", "Produce"]

# Real product names per category, so substitutions read as distinct products
# rather than SKU codes. Cosmetic only (no RNG, no anchors touched); a SKU's name
# is picked deterministically by its id, so a handful surface varied in any ledger.
NAME_POOLS = {
 "Specialty pasta": ["Bucatini","Paccheri","Orecchiette","Trofie","Casarecce","Mafaldine",
   "Tonnarelli","Gigli","Strozzapreti","Garganelli","Bigoli","Pici","Calamarata","Fusilli lunghi"],
 "Cheese & charcuterie": ["Parmigiano 24-month","Taleggio DOP","Gorgonzola dolce","Pecorino Sardo",
   "Aged Gouda","Comté","Prosciutto di Parma","'Nduja","Soppressata","Finocchiona","Manchego",
   "Robiola","Culatello","Bresaola"],
 "Truffle & mushroom": ["Black winter truffle","Summer truffle","Dried porcini","Fresh chanterelle",
   "Maitake","King trumpet","Morels","Truffle paste","Hen of the woods","Shiitake","Matsutake",
   "Cremini","Truffle carpaccio","Trumpet royale"],
 "Caviar & roe": ["Osetra","Kaluga hybrid","Hackleback","Trout roe","Salmon roe","Bottarga",
   "Tobiko","Paddlefish roe","Siberian sturgeon","Golden osetra","Smoked roe","Sevruga",
   "Whitefish roe","Ikura"],
 "Oils & vinegars": ["Frantoia EVOO","Sicilian EVOO","Aged balsamico","White balsamic","Banyuls vinegar",
   "Sherry vinegar","Ligurian EVOO","Tuscan EVOO","Moscatel vinegar","Pumpkin seed oil","Walnut oil",
   "Red wine vinegar","Champagne vinegar","Cider vinegar"],
 "Center of plate": ["Dry-aged ribeye","Ibérico loin","Lamb rack","Duck breast","Short rib","Veal chop",
   "Wagyu striploin","Berkshire pork belly","Guinea hen","Venison loin","Oxtail","Bavette","Hanger steak","Quail"],
 "Dairy": ["Cultured butter","Crème fraîche","Buffalo mozzarella","Burrata","Mascarpone","Ricotta",
   "Normandy butter","Clotted cream","Labneh","Stracciatella","Fresh curds","Farmer's cheese","Quark","Kefir"],
 "Pantry": ["San Marzano tomatoes","Castelvetrano olives","Marcona almonds","Saffron","Calabrian chili",
   "Salt-packed capers","Piquillo peppers","Anchovies","Chickpeas","Arborio rice","Polenta","Smoked paprika",
   "Fennel pollen","Dried figs"],
 "Nuts": ["Sicilian pistachios","Marcona almonds","Piedmont hazelnuts","Pine nuts","Candied walnuts",
   "Pecans","Cashews","Macadamias","Chestnuts","Almond flour","Hazelnut paste","Pistachio paste",
   "Black walnuts","Roasted peanuts"],
 "Produce": ["Heirloom tomatoes","Wild ramps","Fava beans","Castelfranco","Puntarelle","Romanesco",
   "Fingerling potatoes","Baby artichokes","Meyer lemons","Black garlic","Cipollini","Sunchokes",
   "Watercress","Delicata squash"],
}

# The buyers the prototype displays with real names. Everything else about them
# (tier, value, categories, cadence) is generated exactly as for any account, 
# a real name is the only thing added. The first 15 are the original demo set;
# the block above them is an extra roster so the accounts/campaign lists feel
# full. NOTE: new names are PREPENDED so the original 15 keep their exact
# generated values (the named accounts are popped from the end of each tier
# list, so front insertions never shift the originals' slots).
NAMED = [
 # ── extra roster (real names for more accounts) ──
 (11001, "Marrow & Vine",     "NoMad",            "American",      "Dorian West",    "A"),
 (11002, "Shibumi",           "Midtown",          "Japanese",      "Ken Arai",       "A"),
 (11003, "La Rambla",         "West Village",     "Spanish",       "Elena Puig",     "A"),
 (11004, "Cardoon",           "Tribeca",          "Italian",       "Vito Marchetti", "A"),
 (11005, "Fennel & Rye",      "Williamsburg",     "New American",  "Josie Hartman",  "B"),
 (11006, "Tabla Verde",       "East Village",     "Mexican",       "Mateo Cruz",     "B"),
 (11007, "The Copper Pot",    "Astoria",          "Mediterranean", "Yara Demir",     "B"),
 (11008, "Silvercup Kitchen", "Long Island City", "New American",  "Nate Fisk",      "B"),
 (11009, "Osteria Bruna",     "Cobble Hill",      "Italian",       "Bruna Ricci",    "B"),
 (11010, "Hanok",             "Koreatown",        "Korean",        "Sun-Hee Park",   "B"),
 (11011, "Bar Lamia",         "Greenwich Village","Greek",         "Nikos Vasil",    "B"),
 (11012, "The Gilded Fig",    "Prospect Heights", "New American",  "Della Voss",     "B"),
 (11013, "Maison Lune",       "Fort Greene",      "French",        "Adele Mercier",  "B"),
 (11014, "Smoke & Ember",     "Bushwick",         "Barbecue",      "Cal Rourke",     "B"),
 (11015, "Poppy's Counter",   "Bed-Stuy",         "Cafe",          "Poppy Nair",     "C"),
 (11016, "The Anchovy Bar",   "Red Hook",         "Seafood",       "Sal Verano",     "C"),
 (11017, "Verdant",           "Gowanus",          "Vegetarian",    "Mira Chen",      "C"),
 (11018, "Little Sparrow",    "Sunnyside",        "French",        "Colette Fabre",  "C"),
 (11019, "Rye House",         "Ridgewood",        "American",      "Hank Doyle",     "C"),
 (11020, "Casa Lima",         "Jackson Heights",  "Peruvian",      "Ana Solano",     "C"),
 (11021, "The Daily Crumb",   "Carroll Gardens",  "Bakery",        "Ben Ash",        "C"),
 (11022, "Nori & Nori",       "Murray Hill",      "Japanese",      "Emi Sato",       "C"),
 (11023, "Thistle & Fern",    "Ditmas Park",      "British",       "Rue Baptiste",   "C"),
 (11024, "El Farolito",       "Bushwick",         "Mexican",       "Tomas Gil",      "C"),
 (11025, "Kettle & Stone",    "Inwood",           "American",      "Gwen Poole",     "C"),
 (11026, "Saffron Lane",      "Kips Bay",         "Indian",        "Ravi Menon",     "C"),
 (11027, "The Plum Line",     "Clinton Hill",     "Cafe",          "Lena Ford",      "C"),
 (11028, "Brine",             "Greenpoint",       "Seafood",       "Ivo Marsh",      "C"),
 (11029, "Gramercy Larder",   "Gramercy",         "New American",  "Hugo Ellis",     "C"),
 (11030, "Wildseed Table",    "Park Slope",       "Vegetarian",    "Fern Ito",       "C"),
 # ── original 15 demo accounts ──
 (10428, "Vinoteca Ardito",   "West Village",     "Italian",      "Marco Ardito",   "A"),
 (10193, "Le Perchoir",       "Tribeca",          "French",       "Céline Roux",    "A"),
 (10310, "Osteria Nina",      "Upper East Side",  "Italian",      "Gio Fallaci",    "A"),
 (10999, "Aurum",             "Midtown",          "Tasting menu", "Elliot Reyes",   "A"),
 (10771, "Saltbox",           "Brooklyn Heights", "New American", "Dana Whitfield", "B"),
 (10855, "Kōji House",        "Flatiron",         "Japanese",     "Aiko Tanabe",    "B"),
 (10634, "Marisol",           "Lower East Side",  "Spanish",      "Rafa Olmedo",    "B"),
 (10917, "Hearth & Bramble",  "Greenpoint",       "New American", "Iris Kelleher",  "B"),
 (10086, "Nonna Piera",       "Carroll Gardens",  "Italian",      "Piera Costa",    "B"),
 (10420, "The Salt Cellar",   "Battery Park",     "Seafood",      "Nadia Brandt",   "B"),
 (10502, "The Wren & Larder", "Cobble Hill",      "British",      "Tom Beasley",    "C"),
 (10248, "Café Duvel",        "Park Slope",       "Belgian",      "Luc Maes",       "C"),
 (10377, "Verbena",           "Fort Greene",      "Vegetarian",   "Nia Osei",       "C"),
 (10611, "Bar Ossola",        "Nolita",           "Italian",      "Franco Ossola",  "C"),
 (10788, "Quince & Co.",      "Chelsea",          "New American", "Priya Raman",    "C"),
]


def build(scenario, path="foodie.db"):
    Path(path).unlink(missing_ok=True)
    db = sqlite3.connect(path)
    db.executescript(Path("schema.sql").read_text())

    # ── account managers ────────────────────────────────────────────────
    db.executemany("INSERT INTO account_managers VALUES (?,?,?,?)", [
        (i, f"AM {i:02d}", int(i <= D.LARGE_ACCT_AMS), int(i <= D.DEFECTED_AMS))
        for i in range(1, D.AMS + 1)])

    # ── skus ────────────────────────────────────────────────────────────
    # Now carrying name / in_stock / texture / perishable  [FIX]. Generic SKUs
    # get code-as-name and ~86% stock; texture is null (only pasta cares here).
    PERISHABLE_CATS = {"Cheese & charcuterie", "Truffle & mushroom", "Caviar & roe",
                       "Dairy", "Produce", "Center of plate"}
    # [FIX] New per-SKU draws (in_stock, scenario prices) go through a SEPARATE
    # RNG so the main `random` stream reaching account generation is byte-for-
    # byte unchanged, every account keeps its original annual_value (the brief
    # pins Vinoteca $77,352, Café Duvel $4,641, Osteria Nina $44,196).
    srng = random.Random(SEED + 1)
    skus = []
    for i in range(1, D.SKUS + 1):
        cat = CATEGORIES[i % len(CATEGORIES)]
        code = f"SKU-{i:04d}"
        pool = NAME_POOLS[cat]
        nm = pool[(i // len(CATEGORIES)) % len(pool)]   # real product name, varied within category
        skus.append((i, code, nm, cat, round(random.uniform(14, 480), 2),
                     int(srng.random() < 0.86), None, int(cat in PERISHABLE_CATS)))
    db.executemany("INSERT INTO skus VALUES (?,?,?,?,?,?,?,?)", skus)
    by_cat = {c: [s[0] for s in skus if s[3] == c] for c in CATEGORIES}

    # scenario SKUs: the paccheri story, hand-authored and named. Appended with
    # high ids so nothing generated shifts; added to by_cat so ranking sees them.
    SCEN_SKU = {}
    scenario_skus = [
        # key,          name,                               texture, in_stock
        ("rustichella", "Rustichella d'Abruzzo paccheri",   "firm",  0),  # requested, OOS
        ("gragnano",    "Gragnano IGP paccheri",            "firm",  1),  # agreed fallback
        ("cavalieri",   "Benedetto Cavalieri paccheri",     "firm",  1),  # catalogue match, declined
        ("soft1",       "Pastificio dei Campi paccheri",    "soft",  1),  # excluded by texture fact
        ("soft2",       "La Fabbrica della Pasta paccheri", "soft",  1),
        ("soft3",       "Pasta Mancini paccheri",           "soft",  1),
    ]
    for k, (key, nm, tex, stock) in enumerate(scenario_skus, start=1):
        sid = 90000 + k
        SCEN_SKU[key] = sid
        db.execute("INSERT INTO skus VALUES (?,?,?,?,?,?,?,?)",
                   (sid, f"SKU-{sid}", nm, "Specialty pasta",
                    round(srng.uniform(38, 72), 2), stock, tex, 0))
        by_cat["Specialty pasta"].append(sid)

    # ── accounts ────────────────────────────────────────────────────────
    counts = {t: int(D.ACCOUNTS * D.TIER_SHARE[t]) for t in D.TIER_SHARE}
    counts["C"] += D.ACCOUNTS - sum(counts.values())

    named = {"A": [], "B": [], "C": []}
    for n in NAMED:
        named[n[5]].append(n)

    # Value is built bottom-up: each account's annual value is its tier profile
    # (deliveries x 12 x lines x $/line, from dials.TIER_ANNUAL) times a mean-
    # preserving lognormal, so accounts vary around the tier without shifting its
    # mean. Tiers are NOT scaled to a target afterwards, the totals are what they
    # are (~$95.6M against the case's $95M; see dials.summary()).
    sig = D.WITHIN_TIER_SIGMA
    mu  = -sig * sig / 2                          # makes E[multiplier] = 1.0
    rows, next_id = [], 20_000
    for tier in ("A", "B", "C"):
        n    = counts[tier]
        base = D.TIER_ANNUAL[tier]
        ams  = (list(range(1, D.LARGE_ACCT_AMS + 1)) if tier == "A"
                else list(range(D.LARGE_ACCT_AMS + 1, D.AMS + 1)))
        for k in range(n):
            if named[tier]:
                aid, nm, hood, cuisine, contact, _ = named[tier].pop()
            else:
                next_id += 1
                aid, nm, hood, cuisine, contact = (
                    next_id, f"Account {next_id}", "New York", ", ", ", ")
            cats  = random.sample(CATEGORIES, random.randint(2, 5))
            value = base * random.lognormvariate(mu, sig)
            rows.append((aid, nm, hood, cuisine, contact, tier,
                         round(value, 2),
                         round(D.DELIVERIES_PER_MONTH[tier] * random.uniform(.8, 1.2), 3),
                         ",".join(cats), random.choice(ams)))
    db.executemany("INSERT INTO accounts VALUES (?,?,?,?,?,?,?,?,?,?)", rows)

    A = {r[0]: dict(tier=r[5], value=r[6], cadence=r[7],
                    cats=r[8].split(","), am=r[9]) for r in rows}

    # ── inquiries, drafts, substitutions ────────────────────────────────
    inq_weight = D.INQ_WEIGHT     # derived from line counts (19/12/8 -> 2.4/1.5/1.0):
    #                              more distinct items -> more chances something is out
    weights    = [inq_weight[A[a]["tier"]] for a in A]
    ids        = list(A)

    inquiries, drafts, events, subs = [], [], [], []
    iid = did = sid = 0
    exposure = {a: 0 for a in A}          # agent-era inquiry count per account

    # Daily inbound is NOT flat. Real desks swing by weekday and week. These
    # factors are mean-preserving (each averages ~1 over its period) so the
    # published INBOUND_MO=2,400 monthly figure is unchanged, only the
    # distribution across days gains realistic texture. [INVENTED shape]
    WD = {0: 1.18, 1: 1.22, 2: 1.12, 3: 1.18,    # Mon–Thu run hot
          4: 1.05, 5: 0.68, 6: 0.57}             # Fri easing, weekend quiet  (Σ=7.0)
    _wk_shock = {}
    def week_factor(d):                          # one random level per ISO week
        k = d.isocalendar()[:2]
        if k not in _wk_shock:
            _wk_shock[k] = max(0.65, random.gauss(1.0, 0.11))
        return _wk_shock[k]
    def season(d):                               # slow annual swell (±10%)
        return 1 + 0.10 * math.sin(2 * math.pi * d.timetuple().tm_yday / 365.0)

    # Staggered agent adoption per AM: most onboard in the weeks after launch,
    # a tail lags. Defected AMs engage from day one (they open and discard).
    # This is what makes the PulseBoard adoption line RAMP rather than sit flat.
    adopt_day = {}
    for am in range(1, D.AMS + 1):
        adopt_day[am] = (AGENT_LIVE if am <= D.DEFECTED_AMS
                         else AGENT_LIVE + dt.timedelta(days=int(random.triangular(0, 56, 10))))

    # Even after adoption, not every AM is active every week (PTO, quiet desks).
    # ~8% weekly dropout keeps the adoption line off a dead-flat 80 ceiling.
    _avail = {}
    def actor_for(am, d):
        if am <= D.DEFECTED_AMS:        # defected AMs always engage (open+discard)
            return am
        if d < adopt_day[am]:           # not yet onboarded → draft sits unengaged
            return None
        k = (am, d.isocalendar()[:2])
        if k not in _avail:
            _avail[k] = random.random() > 0.08
        return am if _avail[k] else None

    day = START
    while day <= TODAY:
        agent_on = day >= AGENT_LIVE
        lam      = (D.INBOUND_MO / 30) * WD[day.weekday()] * week_factor(day) * season(day)
        n_today  = int(lam) + (random.random() < lam % 1)

        for acc in random.choices(ids, weights=weights, k=n_today):
            iid += 1
            cat   = random.choice(A[acc]["cats"])
            asked = random.choice(by_cat[cat])
            chan  = "portal" if random.random() < 0.72 else "direct_to_am"
            inquiries.append((iid, acc, day.isoformat(), chan, cat, asked,
                              int(agent_on)))
            if not agent_on:
                continue
            exposure[acc] += 1

            did += 1
            defected = A[acc]["am"] <= D.DEFECTED_AMS
            edited   = (not defected) and random.random() < D.IN_EDIT_RATE
            depth    = (round(min(.95, max(.03, random.gauss(D.IN_EDIT_DEPTH, .08))), 3)
                        if edited else 0.0)
            # [INVENTED] breakdown of the given 23%. Case names SKU swaps and
            # tone as the two most common edits.
            ecat = (random.choices(["sku", "tone", "quantity", "factual"],
                                   weights=[.34, .44, .11, .11])[0]
                    if edited else None)
            drafts.append((did, iid, acc, "inbound", day.isoformat(), depth, ecat))

            # actor is attributed only once this AM has adopted the agent;
            # before that the draft is generated but sits unengaged (actor NULL).
            am_id  = A[acc]["am"]
            actor  = actor_for(am_id, day)
            events.append((did, "generated", day.isoformat(), None))
            events.append((did, "opened",    day.isoformat(), actor))
            if defected:
                events.append((did, "discarded", day.isoformat(), A[acc]["am"]))
            else:
                if edited:
                    events.append((did, "edited", day.isoformat(), actor))
                events.append((did, "sent", day.isoformat(), actor))

            # a substitution record exists whenever the draft proposed one.
            # No stockout dial: tied to the SKU-edit path plus a share of
            # unedited drafts, so the table is populated without a new
            # invented rate driving the analysis.
            if ecat == "sku" or (not edited and random.random() < 0.12):
                sid += 1
                offered = random.choice([s for s in by_cat[cat] if s != asked])
                action  = "replaced" if ecat == "sku" else "sent_as_is"
                repl    = (random.choice(by_cat[cat]) if action == "replaced" else None)
                # AM-chosen substitutes land better than agent-chosen ones.
                # This is the HYPOTHESIS, encoded, not a discovery.
                p = 0.78 if action == "replaced" else 0.44
                subs.append((sid, did, acc, asked, offered, action, repl,
                             "accepted" if random.random() < p else "declined",
                             day.isoformat()))
        day += dt.timedelta(days=1)

    db.executemany("INSERT INTO inquiries VALUES (?,?,?,?,?,?,?)", inquiries)
    db.executemany("INSERT INTO drafts VALUES (?,?,?,?,?,?,?)", drafts)
    db.executemany("INSERT INTO draft_events VALUES (?,?,?,?)", events)
    db.executemany(
        """INSERT INTO substitutions
           (substitution_id, draft_id, account_id, requested_sku_id, offered_sku_id,
            am_action, am_replacement_sku_id, buyer_outcome, resolved_date)
           VALUES (?,?,?,?,?,?,?,?,?)""", subs)

    inq_by_acct_day = {}
    for r in inquiries:
        inq_by_acct_day.setdefault((r[1], r[2]), []).append(r[0])

    # ── the imposed decline ─────────────────────────────────────────────
    # The case gives 61% -> 44%. Distribute the shortfall according to the
    # scenario, then generate orders. This is REPRODUCTION, not explanation.
    hi_exposure = {a for a in A if exposure[a] >= 3}
    share_hi    = len(hi_exposure) / len(A)

    # Each scenario distributes the SAME average drop differently. That is the
    # point: the aggregate is fixed by the case, only the shape differs.
    avg_drop = AVG_DROP_BY_SCENARIO[scenario]

    def split(ratio):
        """ratio = drop_hi / drop_lo. Solve so the weighted mean = avg_drop."""
        lo = avg_drop / (share_hi * ratio + (1 - share_hi))
        return min(0.95, lo * ratio), lo

    if scenario == "agent":     hi, lo = split(6.0)   # concentrated in exposed
    elif scenario == "supply":  hi, lo = avg_drop, avg_drop   # uniform
    else:                       hi, lo = split(2.0)   # mixed
    drop = {a: (hi if a in hi_exposure else lo) for a in A}

    orders, oid = [], 0
    day = START
    while day <= TODAY:
        declining = day >= DECLINE_ON
        for a, info in A.items():
            factor = (1 - drop[a]) if declining else 1.0
            base   = info["cadence"] / 30 * CADENCE_CAL * factor
            if random.random() < base * D.RECURRING_SHARE:
                oid += 1
                orders.append((oid, a, day.isoformat(), "standing", None, None,
                               order_value(info)))
            if random.random() < base * (1 - D.RECURRING_SHARE):
                oid += 1
                orders.append((oid, a, day.isoformat(), "portal_adhoc", None, None,
                               order_value(info)))
            for q in inq_by_acct_day.get((a, day.isoformat()), []):
                if random.random() < 0.62 * factor:
                    oid += 1
                    orders.append((oid, a, day.isoformat(), "inquiry", q, None,
                                   order_value(info)))

        day += dt.timedelta(days=1)

    # ── campaigns (built BEFORE the revenue scale so a converted send can post
    #    a campaign-channel order into the same $95M pool) ─────────────────
    camps, sends, cid, csid = [], [], 0, 0
    month = AGENT_LIVE.replace(day=1)
    while month <= TODAY:
        cid += 1
        cat = CATEGORIES[cid % len(CATEGORIES)]
        camps.append((cid, f"{cat} pre-order", cat, month.isoformat()))
        pool = [a for a in A if cat in A[a]["cats"]]
        random.shuffle(pool)
        for acc in pool[:D.OUTBOUND_MO]:
            csid += 1
            relevant  = cat == A[acc]["cats"][0]        # [INVENTED] definition
            edited    = random.random() < D.OUT_EDIT_RATE
            depth     = (round(min(.4, max(.01, random.gauss(D.OUT_EDIT_DEPTH, .04))), 3)
                         if edited else 0.0)
            converted = int(random.random() < (0.29 if relevant else 0.055))
            unsub     = int((not relevant) and random.random() < 0.043)
            sends.append((csid, cid, acc, month.isoformat(), int(relevant),
                          int(edited), depth, converted, unsub))
            # a conversion IS an order, and the only source of channel='campaign'.
            # Same value model as any order; carries campaign_send_id back to the send.
            if converted:
                oid += 1
                orders.append((oid, acc, month.isoformat(), "campaign", None, csid,
                               order_value(A[acc])))
        month = (month.replace(day=28) + dt.timedelta(days=6)).replace(day=1)
    db.executemany("INSERT INTO campaigns VALUES (?,?,?,?)", camps)
    db.executemany("INSERT INTO campaign_sends VALUES (?,?,?,?,?,?,?,?,?)", sends)

    # scale order values so 12-month revenue matches the case, campaign orders
    # included, so the channel split still sums to the same $95M.
    total = sum(o[6] for o in orders)
    k = D.REVENUE / total
    orders = [(*o[:6], round(o[6] * k, 2)) for o in orders]
    db.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", orders)

    seed_fix(db, A, SCEN_SKU, by_cat)     # [FIX] the paccheri scenario + record
    seed_book_records(db, A, by_cat)      # [ADDITION] a thread + facts for every book account

    db.commit()
    return db


# ════════════════════════════════════════════════════════════════════════
# [ADDITION] Give every named book account a real thread (call/email/note) and
# captured facts, so The Round's per-account view and Draft-a-note composer are
# fully functional for every customer, not just the three scenario accounts.
# Deterministic per account (seeded by account_id), so screenshots stay stable.
# ════════════════════════════════════════════════════════════════════════
# A pool of distinct buyer situations. Each account is dealt a few at random
# (seeded), so no two books read alike: complaints, opt-outs, sourcing asks,
# praise, terms, events, volume shifts, life changes. `open` -> unresolved
# (Outstanding); `used` -> the fact currently biases a suggestion.
#   fields: key, kind, title, body, stmt, fkind, conf(lo,hi), aff, used, open
SITUATIONS = [
 dict(key="complaint", kind="am_note", title="Quality complaint",
   body="{first} flagged the last {catl} delivery as below standard, chalky and off-spec, and wants a credit plus tighter QC on the next lot.",
   stmt="Quality complaint on {catl}; credit still pending.", fkind="open_item", conf=(.78,.86), aff=False, used=False, open=True),
 dict(key="optout", kind="email", title="Re: campaign emails",
   body="Please take us off the weekly campaign emails, we plan our own list and the sends aren't useful. Nothing wrong with the account otherwise.",
   stmt="Asked to stop the weekly campaign emails.", fkind="stated_fact", conf=(.78,.86), aff=False, used=False, open=True),
 dict(key="sourcing", kind="email", title="Sourcing question",
   body="Any chance you can source a specialty {catl} item for a dish we're testing next month? No rush, just exploring.",
   stmt="Asked us to source a specialty {catl} item; not yet followed up.", fkind="open_item", conf=(.7,.8), aff=False, used=False, open=True),
 dict(key="terms", kind="email", title="Payment terms",
   body="Could we move to Net 45 for a couple of months? Cash flow is tight coming out of the slow season.",
   stmt="Asked about Net 45 terms; awaiting an answer.", fkind="open_item", conf=(.72,.82), aff=False, used=False, open=True),
 dict(key="event", kind="email", title="Private event",
   body="We've got a 90-cover private dinner next month and will need extra {catl}. Can you hold some back for us?",
   stmt="Large event next month; needs extra {catl} held.", fkind="open_item", conf=(.72,.82), aff=False, used=False, open=True),
 dict(key="cadence", kind="call_transcript", title="Quarterly check-in",
   body="{first}: keep the {catl} on the standing order, it anchors the menu and I don't want to think about it week to week.",
   stmt="Keeps a standing {catl} order, don't let it lapse.", fkind="cadence_lock", conf=(.86,.93), aff=True, used=True, open=False),
 dict(key="delivery", kind="email", title="Delivery window",
   body="Can we shift deliveries to {day} mornings? The afternoons collide with prep and things sit on the dock.",
   stmt="Prefers {day} morning deliveries.", fkind="delivery_pref", conf=(.72,.85), aff=False, used=False, open=False),
 dict(key="refusal", kind="call_transcript", title="Substitution note",
   body="{first}: don't swap the {catl} without checking with me first, the last substitute didn't work for us at service.",
   stmt="Won't take substitutes on {catl} without a heads-up.", fkind="refusal_pattern", conf=(.85,.92), aff=True, used=True, open=False),
 dict(key="praise", kind="call_transcript", title="Check-in",
   body="{first}: the {catl} has been excellent lately, the kitchen's really happy with it, keep it exactly as is.",
   stmt="Very happy with the {catl} quality right now.", fkind="stated_fact", conf=(.55,.7), aff=False, used=False, open=False),
 dict(key="volup", kind="am_note", title="Account note",
   body="{first} is scaling up, covers climbing, leaning harder on {catl} this {season}. Expect larger orders.",
   stmt="Scaling up on {catl}; volume trending up.", fkind="stated_fact", conf=(.6,.72), aff=True, used=True, open=False),
 dict(key="voldown", kind="am_note", title="Account note",
   body="{first} is trimming the menu and easing off {catl} for now. Watch for the standing order to lapse.",
   stmt="Easing off {catl}; watch for a lapse.", fkind="stated_fact", conf=(.55,.68), aff=False, used=False, open=False),
 dict(key="spec", kind="am_note", title="Spec requirement",
   body="{first} needs the {catl} to meet a specific grade for the tasting menu, no substitutions on grade.",
   stmt="Requires a specific {catl} grade for the tasting menu.", fkind="stated_fact", conf=(.6,.72), aff=False, used=False, open=False),
 dict(key="competitor", kind="am_note", title="Account note",
   body="{first} mentioned another distributor quoted lower on {catl}. Worth a pricing check-in before the next renewal.",
   stmt="Comparing another supplier on {catl} pricing.", fkind="stated_fact", conf=(.5,.65), aff=False, used=False, open=False),
 dict(key="closed", kind="email", title="Schedule change",
   body="We're closed {day}s now, please don't schedule a delivery that day going forward.",
   stmt="Closed {day}s, no delivery that day.", fkind="delivery_pref", conf=(.72,.85), aff=False, used=False, open=False),
 dict(key="menu", kind="am_note", title="Menu planning",
   body="{first} is planning a {season} menu refresh, leaning into {catl}. Good moment to pitch a pairing.",
   stmt="Planning a {season} menu refresh.", fkind="stated_fact", conf=(.45,.6), aff=False, used=False, open=False),
 dict(key="personal", kind="am_note", title="Account note",
   body="{first} mentioned they're opening a second location in the {season}. Exciting, and it'll change their volume.",
   stmt="Opening a second location in the {season}.", fkind="stated_fact", conf=(.5,.62), aff=False, used=False, open=False),
]

def seed_book_records(db, A, by_cat):
    HERO = {VINOTECA, NINA, DUVEL, PIERA, WREN, PERCHOIR}   # hand-authored already
    rows = db.execute(
        "SELECT account_id, name, contact, cuisine, categories FROM accounts "
        "WHERE account_id < 20000").fetchall()
    SEASONS = ["spring", "summer", "autumn", "winter"]
    DAYS    = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    docs, facts, bias = [], [], []
    doc_id = 9100
    fid = db.execute("SELECT COALESCE(MAX(fact_id),0) FROM buyer_facts").fetchone()[0]

    for aid, name, contact, cuisine, cats in rows:
        if aid in HERO:
            continue
        rng = random.Random(SEED * 7 + aid)
        cat0 = (cats or "Pantry").split(",")[0]
        ctx = dict(first=(contact or "there").split(" ")[0], cat=cat0, catl=cat0.lower(),
                   cui=(cuisine or "kitchen").lower(), day=rng.choice(DAYS), season=rng.choice(SEASONS))
        am = A[aid]["am"]
        chosen = rng.sample(SITUATIONS, 3)                       # three distinct situations
        offs = sorted([rng.randint(150, 330), rng.randint(45, 130), rng.randint(4, 32)], reverse=True)
        aff_pool = (by_cat.get(cat0) or by_cat["Pantry"])[:2]
        for k, sit in enumerate(chosen):
            d = (TODAY - dt.timedelta(days=offs[k])).isoformat()
            occ = d + (" 10:15" if sit["kind"] == "call_transcript" else "")
            body = sit["body"].format(**ctx)
            docs.append((doc_id + 1, aid, sit["kind"], occ, contact or ctx["first"], am,
                         sit["title"].format(**ctx), body))
            if FACTS_SEEDED:
                aff = aff_pool if sit["aff"] else None
                dec = None if sit["open"] else "kept"
                fid += 1
                facts.append((fid, aid, sit["stmt"].format(**ctx), sit["fkind"],
                              f"book_{sit['key']}_{aid}", doc_id + 1, body[:90], "1",
                              round(rng.uniform(*sit["conf"]), 2),
                              json.dumps(aff) if aff else None,
                              dec, am if dec else None, d if dec else None, None, d,
                              d if sit["used"] else None))
                if aff:
                    for s in aff:
                        bias.append((aid, s, -1.0, fid))
            doc_id += 1
        doc_id += 2                                              # gap between accounts

    db.executemany("INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?)", docs)
    if facts:
        db.executemany("INSERT INTO buyer_facts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", facts)
    if bias:
        db.executemany("INSERT INTO account_sku_bias VALUES (?,?,?,?)", bias)


# ════════════════════════════════════════════════════════════════════════
# [FIX] Scenario + captured record.
#
# Source documents and Marco's substitution history are seeded ALWAYS, they
# exist on Foodie's servers today. buyer_facts / account_sku_bias /
# fact_impressions are seeded only when FACTS_SEEDED: that is the entire
# difference between the current and fixed states.
#
# Screen 1's ranking is driven by SUBSTITUTION HISTORY, not by facts (Gragnano
# wins because it was accepted 3/3; Cavalieri shows "declined before"). The
# four buyer_facts on Marco are PENDING capture candidates for the panel, the
# texture one's `affects` list is what the panel means by "would rank out 3
# more SKUs" if kept. Kept facts on other accounts populate the record so the
# PulseBoard capture metrics have something real to read.
# ════════════════════════════════════════════════════════════════════════
VINOTECA, NINA, DUVEL = 10428, 10310, 10248   # named scenario accounts
PIERA, WREN, PERCHOIR = 10086, 10502, 10193   # [ADDITION] book open-thread accounts

def seed_fix(db, A, S, by_cat):
    am = lambda a: A[a]["am"]

    # ── source documents (exist in both states) ─────────────────────────
    docs = [
     (9001, VINOTECA, "call_transcript", "2026-03-12 10:24", "Marco Ardito", am(VINOTECA),
      "Substitution follow-up, paccheri",
      "MARCO: Don't send that one again. The bite's wrong for us. Anything that soft, "
      "same problem, it goes to mush in the pan by service. Texture, not the brand. I "
      "pulled the dish for two nights over it.\nAM: If the Rustichella is out, what do "
      "you want us to reach for?\nMARCO: The Gragnano. The IGP one. That's held up every "
      "time you've sent it. Make that the fallback and I don't need to be asked. And "
      "honestly, I'd rather have an empty slot than the wrong thing. The paccheri itself "
      "is a fixed line for us, six cases, every week, it's on the menu. We're "
      "short-staffed until spring, so it has to be right the first time."),
     (9002, NINA, "call_transcript", "2026-03-04 15:07", "Gio Fallaci", am(NINA),
      "Spring menu planning",
      "GIO: We're reworking the spring menu, so ordering will move around. The new chef "
      "starts in April, so hold off on locking anything in until we've sat down with "
      "them., sorry, that's for the Brooklyn location, not this account. Here it's the "
      "same kitchen, same chef. Ignore that. For this room, keep the pistachios coming "
      "as normal."),
     (9003, DUVEL, "am_note", "2025-06-30", "covering AM", am(DUVEL),
      "Sourcing note",
      "Luc mentioned he's traveling in Spain through the summer and wants to trial a "
      "couple of Spanish pantry items when he's back, jamón, a smoked paprika line. "
      "Revisit in the fall."),
     # [ADDITION] the book's open threads, real documents behind The Round's Open column
     (9004, PIERA, "am_note", "2026-07-24", "AM", am(PIERA),
      "Lot complaint, pecorino",
      "Piera flagged the last pecorino lot as off, chalky, not what she's had before. "
      "Asked for a credit and a different lot next time. Credit not yet issued. She was "
      "short with me; this one matters to her."),
     (9005, WREN, "am_note", "2025-11-06", "AM", am(WREN),
      "Welsh cheese request",
      "Tom asked whether we can source a Welsh cheese, a Caerphilly or a Perl Las, for "
      "a winter board he's planning. Said no rush. Never followed up."),
     (9006, PERCHOIR, "email", "2026-08-11", "Céline Roux", am(PERCHOIR),
      "Re: August pre-order campaign",
      "Please take us off the campaign emails. We plan the list ourselves and the weekly "
      "sends aren't useful. Nothing wrong with the account otherwise, just the emails."),
    ]
    db.executemany("INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?)", docs)

    # ── Marco's substitution history (exists in both states) ────────────
    # Drives Screen 1: Gragnano accepted 3/3 (last 8 Feb), Cavalieri declined once.
    sid0 = 900000
    hist = [
        (sid0+1, None, VINOTECA, S["rustichella"], S["gragnano"], "replaced", S["gragnano"], "accepted", "2025-11-15"),
        (sid0+2, None, VINOTECA, S["rustichella"], S["gragnano"], "replaced", S["gragnano"], "accepted", "2026-01-10"),
        (sid0+3, None, VINOTECA, S["rustichella"], S["gragnano"], "replaced", S["gragnano"], "accepted", "2026-02-08"),
        (sid0+4, None, VINOTECA, S["rustichella"], S["cavalieri"], "sent_as_is", None,        "declined", "2026-03-12"),
    ]
    db.executemany(
        """INSERT INTO substitutions
           (substitution_id, draft_id, account_id, requested_sku_id, offered_sku_id,
            am_action, am_replacement_sku_id, buyer_outcome, resolved_date)
           VALUES (?,?,?,?,?,?,?,?,?)""", hist)

    if not FACTS_SEEDED:
        return

    # ── captured record: fixed state only ───────────────────────────────
    facts, bias, imps = [], [], []
    fid = [0]
    def fact(acc, statement, kind, dedup, doc, excerpt, loc, conf, affects,
             decision=None, valid_from=None, last_used="auto"):
        fid[0] += 1
        # [ADDITION] a fact has influenced a suggestion iff it biases SKUs (affects);
        # facts with nothing to bias are captured-but-never-used. Override explicitly
        # with last_used to model an open item that was ignored.
        li = (("2026-08-14" if affects else None) if last_used == "auto" else last_used)
        facts.append((fid[0], acc, statement, kind, dedup, doc, excerpt, loc, conf,
                      json.dumps(affects) if affects else None,
                      decision, am(acc) if decision else None,
                      "2026-03-12" if decision else None, None, valid_from, li))
        return fid[0]

    # Marco: four PENDING capture candidates (Screen 3). Two clear the 0.85
    # pre-check bar (texture, cadence); two do not (stated facts, capped at 0.5).
    fT = fact(VINOTECA, "Won't take a softer bite. Texture, not brand.",
              "refusal_pattern", "texture_soft", 9001,
              "the bite's wrong for us. Anything that soft, same problem", "01:42",
              0.90, [S["soft1"], S["soft2"], S["soft3"]])
    fact(VINOTECA, "Paccheri is a fixed menu item, 6 cases weekly.",
         "cadence_lock", "paccheri_cadence", 9001,
         "six cases, every week, it's on the menu", "03:40", 0.88, [S["gragnano"]])
    fact(VINOTECA, "Prefers a gap to a wrong substitute.",
         "stated_fact", "empty_slot", 9001,
         "I'd rather have an empty slot than the wrong thing", "03:05", 0.50, None)
    fact(VINOTECA, "Short-staffed until spring.",
         "stated_fact", "short_staffed", 9001,
         "We're short-staffed until spring", "04:12", 0.40, None)
    # one KEPT fact: the agreed fallback. Sources Screen 1's fallback annotation
    # and gives Gragnano a small positive bias.
    ffid = fact(VINOTECA, "Gragnano IGP is the agreed fallback for paccheri.",
                "refusal_pattern", "gragnano_fallback", 9001,
                "The Gragnano. The IGP one. Make that the fallback", "02:31",
                0.90, [S["gragnano"]], decision="kept", valid_from="2026-03-12")
    bias.append((VINOTECA, S["gragnano"], 0.5, ffid))

    # Osteria Nina: three sound candidates + the trap (Screen 4).
    fact(NINA, "Pistachios are a standing item, keep them coming.",
         "cadence_lock", "pistachio_standing", 9002,
         "keep the pistachios coming as normal", "02:48", 0.86, None)
    fact(NINA, "Spring menu is being reworked; ordering will shift.",
         "stated_fact", "spring_rework", 9002,
         "We're reworking the spring menu", "01:40", 0.45, None)
    fact(NINA, "Prefers Tuesday delivery for perishables.",
         "delivery_pref", "nina_tue", None, None, None, 0.50, None)
    fact(NINA, "New chef starting in April.",              # the wrong candidate
         "stated_fact", "new_chef_april", 9002,
         "the new chef starts in April", "02:14", 0.45, None)

    # ~9 KEPT facts on assorted accounts populate the record so the PulseBoard
    # capture metrics read real rows. Each expands into account_sku_bias.
    kept_targets = [10193, 10999, 10771, 10855, 10634, 10917, 10086, 10420, 10502]
    for n, acc in enumerate(kept_targets, start=1):
        cat = A[acc]["cats"][0]
        pool = by_cat.get(cat) or by_cat["Pantry"]
        affected = pool[:2]
        kfid = fact(acc, f"Standing preference on {cat.lower()}.",
                    "refusal_pattern", f"kept_pref_{acc}", None,
                    "captured from correction history", None, 0.90, affected,
                    decision="kept", valid_from="2026-05-01")
        for s in affected:
            bias.append((acc, s, -1.0, kfid))

    # Café Duvel: a KEPT fact whose evidence is >12 months old, the expiry demo.
    # Seeded kept with bias; the retirement query deletes it (newest evidence
    # 2025-06-30 is over a year before TODAY). Left in so expiry is observable.
    dfid = fact(DUVEL, "Interested in Spanish pantry items (trial).",
                "stated_fact", "duvel_spain", 9003,
                "wants to trial a couple of Spanish pantry items", "1",
                0.50, [by_cat["Pantry"][0]], decision="kept", valid_from="2025-06-30")
    bias.append((DUVEL, by_cat["Pantry"][0], -1.0, dfid))

    # ── [ADDITION] open threads: captured, unresolved, never used. These drive
    # The Round's Open column and the morning read. Pending (no decision), no
    # affects, last_used forced null so each counts as "told you / not acted on". ──
    fact(PIERA, "Lot complaint on the pecorino, credit not issued.",
         "open_item", "piera_lot", 9004,
         "flagged the last pecorino lot as off ... credit not yet issued", "1",
         0.80, None, last_used=None)
    fact(WREN, "Asked about a Welsh cheese in November, never followed up.",
         "open_item", "wren_welsh", 9005,
         "asked whether we can source a Welsh cheese", "1",
         0.70, None, last_used=None)
    fact(NINA, "Asked for the pistachio increase for April, never set up.",
         "open_item", "nina_pistachio", 9002,
         "keep the pistachios coming as normal", "02:48",
         0.75, None, last_used=None)
    # Le Perchoir: their campaign opt-out, captured from the email so it's both a
    # worth-remembering point and something the reply must respect (tone included).
    fact(PERCHOIR, "Wants off the campaign emails; plans the weekly list themselves.",
         "stated_fact", "perchoir_optout", 9006,
         "Please take us off the campaign emails. We plan the list ourselves", "1",
         0.82, None, last_used=None)

    db.executemany("INSERT INTO buyer_facts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", facts)
    db.executemany("INSERT INTO account_sku_bias VALUES (?,?,?,?)", bias)
    # a couple of impression rows so the suppress/retire caps have data
    imps = [(fT, None, "2026-08-17", 1)]
    db.executemany("INSERT INTO fact_impressions VALUES (?,?,?,?)", imps)

    # [ADDITION] Le Perchoir opted out of campaigns last week, a real
    # campaign_send with unsubscribed=1 that sources the morning read's third line.
    last_cid = db.execute("SELECT MAX(campaign_id) FROM campaigns").fetchone()[0]
    if last_cid:
        db.execute("INSERT INTO campaign_sends VALUES (?,?,?,?,?,?,?,?,?)",
                   (990001, last_cid, PERCHOIR, "2026-08-11", 1, 0, 0.0, 0, 1))


def order_value(info):
    monthly = info["value"] / 12
    return max(55.0, random.gauss(monthly / max(info["cadence"], .5), monthly * .13))


def validate(db, scenario):
    q = lambda s: db.execute(s).fetchone()
    w = int(D.WINDOW_DAYS)

    def rate(anchor):
        s = (anchor - dt.timedelta(days=w)).isoformat()
        n = q(f"SELECT COUNT(DISTINCT account_id) FROM orders "
              f"WHERE order_date BETWEEN '{s}' AND '{anchor}'")[0]
        return n / D.ACCOUNTS

    print(f"\nSCENARIO: {scenario}")
    print(f"{'':-<64}")
    print(f"{'metric':<34}{'generated':>13}{'case':>15}")
    print(f"{'':-<64}")
    rev = q("SELECT SUM(order_value) FROM orders")[0]
    print(f"{'revenue, 12 months':<34}{'$'+format(rev,',.0f'):>13}{'$95,000,000':>15}")
    print(f"{'inquiries / month':<34}"
          f"{q('SELECT COUNT(*) FROM inquiries')[0]/12:>13,.0f}{'2,400':>15}")

    e = q("SELECT 1.0*SUM(edit_depth>0)/COUNT(*), "
          "AVG(CASE WHEN edit_depth>0 THEN edit_depth END) FROM drafts")
    print(f"{'inbound edit rate':<34}{e[0]*100:>12.1f}%{'26%':>15}")
    print(f"{'inbound edit depth | edited':<34}{e[1]*100:>12.1f}%{'23%':>15}")

    c = q("SELECT 1.0*SUM(was_edited)/COUNT(*), AVG(CASE WHEN was_edited "
          "THEN edit_depth END), 1.0*SUM(converted)/COUNT(*), "
          "1.0*SUM(unsubscribed)/COUNT(*) FROM campaign_sends")
    print(f"{'outbound edit rate':<34}{c[0]*100:>12.1f}%{'34%':>15}")
    print(f"{'outbound edit depth | edited':<34}{c[1]*100:>12.1f}%{'8%':>15}")
    print(f"{'campaign conversion':<34}{c[2]*100:>12.1f}%{'12%':>15}")
    print(f"{'unsubscribe rate':<34}{c[3]*100:>12.2f}%{'3.1%':>15}")

    print(f"{'reorder rate, pre-decline':<34}"
          f"{rate(DECLINE_ON)*100:>12.1f}%{'61%':>15}")
    print(f"{'reorder rate, current':<34}{rate(TODAY)*100:>12.1f}%{'44%':>15}")
    print(f"{'':-<64}")
    print(f"reorder window {w} days (solved, not chosen)  ·  "
          f"orders/mo {q('SELECT COUNT(*) FROM orders')[0]/12:,.0f}")

    # Tier reconciliation: account values built bottom-up, summed, vs the case.
    built  = q("SELECT SUM(annual_value) FROM accounts")[0]
    a_val  = q("SELECT SUM(annual_value) FROM accounts WHERE tier='A'")[0]
    print(f"tier reconciliation: built ${built:,.0f} vs $95,000,000 "
          f"({(built/D.REVENUE-1)*100:+.1f}%)  ·  A-tier {100*a_val/built:.1f}% of value")

    # Agent coverage: inbound as a share of order events, flat across tiers,
    # because inquiry rate (2.4x on menu breadth) and order count (2.4x on
    # delivery frequency) scale together and cancel.
    n_ord = q("SELECT COUNT(*) FROM orders")[0]
    n_inq = q("SELECT COUNT(*) FROM inquiries")[0]
    by_tier = []
    for t in ("A", "B", "C"):
        io = q(f"SELECT COUNT(*) FROM inquiries WHERE account_id IN "
               f"(SELECT account_id FROM accounts WHERE tier='{t}')")[0]
        oo = q(f"SELECT COUNT(*) FROM orders WHERE account_id IN "
               f"(SELECT account_id FROM accounts WHERE tier='{t}')")[0]
        by_tier.append(f"{t} {100*io/oo:.0f}%")
    print(f"agent coverage: inbound {100*n_inq/n_ord:.1f}% of order events "
          f"(10-30% on the dial)  ·  by tier {' '.join(by_tier)}, asymmetry is "
          f"value/interaction (A ${D.ORDER_VALUE['A']:,} vs C ${D.ORDER_VALUE['C']:,}), not frequency")


if __name__ == "__main__":
    sc = sys.argv[1] if len(sys.argv) > 1 else D.SCENARIO
    db = build(sc)
    validate(db, sc)
    print(f"\nwrote foodie.db  (scenario={sc})")
