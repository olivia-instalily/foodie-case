// GET /api/book
// "The Round", one AM's book, live from foodie.db. The book here is the demo
// roster (named accounts, id < 20000). Everything returned is a query result:
// annual (trailing 12mo), how orders arrive (channel split), each account's own
// cadence, days since last order / last two-way contact, the one open thread,
// and kept/unused fact counts. Plus the seven filter counts and the morning read.
const { db } = require("./_db");
const BOOK = "account_id < 20000"; // the demo book

module.exports = (req, res) => {
  try {
    const d = db();
    const anchor = d.prepare(`SELECT max(order_date) a FROM orders`).get().a; // data "today"
    const since365 = `date('${anchor}','-365 days')`;
    const since90 = `date('${anchor}','-90 days')`;
    const since60 = `date('${anchor}','-60 days')`;
    const since14 = `date('${anchor}','-14 days')`;

    // ---- base accounts in the book ----
    const accts = d
      .prepare(
        `SELECT account_id id, name, neighborhood, cuisine, tier,
                round(annual_value) annualValue
           FROM accounts WHERE ${BOOK} ORDER BY name`
      )
      .all();
    const byId = {};
    accts.forEach((a) => {
      byId[a.id] = Object.assign(a, {
        ttm: 0,
        chan: { recurring: 0, inquiry: 0, campaign: 0 },
        n90: 0,
        lastOrder: null,
        daysSince: null,
        cadence: null,
        lastSpoke: null,
        daysSpoke: null,
        lastDoc: null,
        open: null,
        kept: 0,
        unused: 0,
        saidInCall: 0,
        unsubAt: null,
      });
    });

    // ---- orders: TTM channel split + last order + 90d count ----
    d.prepare(
      `SELECT account_id, channel,
              round(sum(CASE WHEN order_date >= ${since365} THEN order_value ELSE 0 END)) ttm,
              sum(CASE WHEN order_date >= ${since90} THEN 1 ELSE 0 END) n90
         FROM orders WHERE ${BOOK} GROUP BY account_id, channel`
    )
      .all()
      .forEach((r) => {
        const a = byId[r.account_id];
        if (!a) return;
        a.ttm += r.ttm || 0;
        a.n90 += r.n90 || 0;
        const bucket =
          r.channel === "inquiry" ? "inquiry" : r.channel === "campaign" ? "campaign" : "recurring";
        a.chan[bucket] += r.ttm || 0;
      });
    d.prepare(
      `SELECT account_id, max(order_date) lastOrder,
              cast(julianday('${anchor}') - julianday(max(order_date)) AS INT) daysSince
         FROM orders WHERE ${BOOK} GROUP BY account_id`
    )
      .all()
      .forEach((r) => {
        const a = byId[r.account_id];
        if (!a) return;
        a.lastOrder = r.lastOrder;
        a.daysSince = r.daysSince;
        // each account's own trailing-90-day median interval; needs >=3 orders
        a.cadence = a.n90 >= 3 ? Math.round((90 / a.n90) * 10) / 10 : null;
      });

    // ---- last contact: any inquiry, call, email, or note. The spec defines
    // "no contact" as no inquiry, call, or sent message, orders are not contact,
    // so an account can order weekly and still be one you haven't spoken to. ----
    const contact = {}; // account_id -> latest ISO date seen across contact sources
    const addContact = (rows) =>
      rows.forEach((r) => {
        if (!r.last) return;
        if (!contact[r.account_id] || r.last > contact[r.account_id]) contact[r.account_id] = r.last;
      });
    addContact(d.prepare(`SELECT account_id, max(occurred_at) last FROM source_documents WHERE ${BOOK} GROUP BY account_id`).all());
    addContact(d.prepare(`SELECT account_id, max(received_date) last FROM inquiries WHERE ${BOOK} GROUP BY account_id`).all());
    const dayDiff = (a, b) => Math.floor((Date.parse(a) - Date.parse((b || "").slice(0, 10))) / 86400000);
    Object.keys(contact).forEach((id) => {
      const a = byId[id];
      if (!a) return;
      a.lastSpoke = contact[id];
      a.daysSpoke = dayDiff(anchor, contact[id]);
    });

    // ---- latest correspondence document per account (for the "last spoke" popup) ----
    d.prepare(
      `SELECT s.account_id, s.doc_id, s.kind, s.occurred_at, s.author, s.title, s.body
         FROM source_documents s
         JOIN (SELECT account_id, max(occurred_at) mx FROM source_documents WHERE ${BOOK} GROUP BY account_id) t
           ON t.account_id = s.account_id AND t.mx = s.occurred_at
        WHERE s.${BOOK}`
    )
      .all()
      .forEach((r) => {
        const a = byId[r.account_id];
        if (!a) return;
        a.lastDoc = { doc_id: r.doc_id, kind: r.kind, occurred_at: r.occurred_at, author: r.author, title: r.title, body: r.body };
      });

    // ---- the one open thread per account (plain language) ----
    d.prepare(
      `SELECT account_id, statement FROM buyer_facts
        WHERE ${BOOK} AND source_kind = 'open_item' ORDER BY fact_id`
    )
      .all()
      .forEach((r) => {
        if (byId[r.account_id] && !byId[r.account_id].open) byId[r.account_id].open = r.statement;
      });

    // ---- fact counts: kept, kept-or-open-but-never-used, said-in-a-call ----
    d.prepare(
      `SELECT f.account_id,
              sum(CASE WHEN f.am_decision='kept' THEN 1 ELSE 0 END) kept,
              sum(CASE WHEN f.last_influenced_at IS NULL
                        AND (f.am_decision='kept' OR f.source_kind='open_item')
                       THEN 1 ELSE 0 END) unused,
              sum(CASE WHEN s.kind='call_transcript' THEN 1 ELSE 0 END) saidInCall
         FROM buyer_facts f
         LEFT JOIN source_documents s ON s.doc_id = f.source_doc_id
        WHERE f.${BOOK} GROUP BY f.account_id`
    )
      .all()
      .forEach((r) => {
        const a = byId[r.account_id];
        if (!a) return;
        a.kept = r.kept || 0;
        a.unused = r.unused || 0;
        a.saidInCall = r.saidInCall || 0;
      });

    // ---- recent campaign unsubscribe ----
    d.prepare(
      `SELECT account_id, max(sent_date) at FROM campaign_sends
        WHERE ${BOOK} AND unsubscribed = 1 GROUP BY account_id`
    )
      .all()
      .forEach((r) => {
        if (byId[r.account_id]) byId[r.account_id].unsubAt = r.at;
      });

    // ---- [three categories] declined subs, open-item age/source, opportunity asks ----
    d.prepare(`SELECT DISTINCT account_id FROM substitutions WHERE ${BOOK} AND buyer_outcome='declined' AND resolved_date >= ${since90}`)
      .all().forEach((r) => { if (byId[r.account_id]) byId[r.account_id].declinedSub = true; });
    d.prepare(
      `SELECT f.account_id, f.statement, COALESCE(f.valid_from, f.decided_at) dated, s.kind
         FROM buyer_facts f LEFT JOIN source_documents s ON s.doc_id = f.source_doc_id
        WHERE f.${BOOK} AND f.source_kind='open_item'`
    ).all().forEach((r) => {
      const a = byId[r.account_id]; if (!a) return;
      if (r.dated && (!a.openDated || r.dated < a.openDated)) a.openDated = r.dated;
      if (r.kind === "call_transcript") a.openFromCall = true;
      if (/complaint/i.test(r.statement || "")) a.hasComplaint = true;
    });
    // opportunity: inquired (recently) about an item that is OUT of stock, "asked and
    // couldn't have it" — a real service gap to follow up on when it returns.
    d.prepare(
      `SELECT i.account_id, min(k.name) item FROM inquiries i JOIN skus k ON k.sku_id = i.requested_sku_id
        WHERE i.${BOOK} AND k.in_stock = 0 AND i.received_date >= ${`date('${anchor}','-120 days')`}
        GROUP BY i.account_id`
    ).all().forEach((r) => { const a = byId[r.account_id]; if (a) { a.oppAsked = true; a.oppItem = r.item; } });

    // ---- derived flags per account (each filter has a stateable rule) ----
    const maxAnnual = Math.max(...accts.map((a) => a.annualValue || 0));
    const sorted = accts.slice().sort((a, b) => b.annualValue - a.annualValue);
    const top20 = new Set(sorted.slice(0, Math.ceil(accts.length * 0.2)).map((a) => a.id));
    accts.forEach((a) => {
      a.pastCadence = a.cadence != null && a.n90 >= 3 && a.daysSince > 1.5 * a.cadence;
      a.approaching =
        a.cadence != null && a.daysSince != null && a.cadence - a.daysSince >= 0 && a.cadence - a.daysSince <= 2;
      a.noContact60 = a.daysSpoke == null || a.daysSpoke > 60;
      a.hasOpen = !!a.open;
      a.saidSomething = a.saidInCall > 0;
      a.toldUnused = a.unused > 0;
      a.top20 = top20.has(a.id);
      a.isLargest = a.annualValue === maxAnnual;
      a.recentUnsub = a.unsubAt != null && a.unsubAt >= d.prepare(`SELECT ${since14} v`).get().v;
    });

    const count = (k) => accts.filter((a) => a[k]).length;
    const filters = {
      pastCadence: count("pastCadence"),
      approaching: count("approaching"),
      noContact60: count("noContact60"),
      openItems: count("hasOpen"),
      saidSomething: count("saidSomething"),
      toldUnused: count("toldUnused"),
      top20: count("top20"),
    };

    // ---- the morning read: everything that meets the bar, grouped. No cap, 
    // on a quiet morning one line, on a bad morning six. The three bars are:
    // a date that has passed (missed reorder), an ask not actioned, a status change.
    const insights = [
      {
        key: "reorder",
        filterKey: "pastCadence",
        label: "missed their usual reorder time",
        members: accts
          .filter((a) => a.pastCadence)
          .sort((x, y) => y.daysSince - x.daysSince)
          .map((a) => ({ id: a.id, name: a.name, detail: `${a.daysSince} days since last order, usual is ~${a.cadence}d` })),
      },
      {
        key: "asked",
        filterKey: "hasOpen",
        label: "asked for something you haven’t actioned",
        members: accts
          .filter((a) => a.hasOpen)
          .map((a) => ({ id: a.id, name: a.name, detail: a.open })),
      },
      {
        key: "status",
        filterKey: "recentUnsub",
        label: "changed status",
        members: accts
          .filter((a) => a.recentUnsub)
          .map((a) => ({ id: a.id, name: a.name, detail: `unsubscribed from campaigns${a.isLargest ? ", your largest account" : ""}` })),
      },
    ].filter((g) => g.members.length);

    const rows = accts.map((a) => ({
      id: a.id,
      name: a.name,
      neighborhood: a.neighborhood,
      annual: a.ttm || a.annualValue,
      chan: a.chan,
      cadence: a.cadence,
      daysSince: a.daysSince,
      lastOrder: a.lastOrder,
      daysSpoke: a.daysSpoke,
      lastDoc: a.lastDoc,
      open: a.open,
      kept: a.kept,
      unused: a.unused,
      pastCadence: a.pastCadence,
      approaching: a.approaching,
      noContact60: a.noContact60,
      hasOpen: a.hasOpen,
      saidSomething: a.saidSomething,
      toldUnused: a.toldUnused,
      top20: a.top20,
      recentUnsub: a.recentUnsub,
    }));

    // ---- the three categories: Slipping (reactive), Outstanding (reactive), Opportunity (not) ----
    const MONTH = (iso) => (iso ? ["January","February","March","April","May","June","July","August","September","October","November","December"][(+iso.split("-")[1]) - 1] : "");
    const slip = accts.filter((a) => a.pastCadence || a.noContact60);
    const outs = accts.filter((a) => a.hasOpen || a.declinedSub);
    const opps = accts.filter((a) => a.oppAsked);
    const hood = {}; slip.forEach((a) => { hood[a.neighborhood] = (hood[a.neighborhood] || 0) + 1; });
    let topHood = null, topHoodN = 0; Object.keys(hood).forEach((h) => { if (hood[h] > topHoodN) { topHoodN = hood[h]; topHood = h; } });
    const oldestOut = outs.filter((a) => a.openDated).sort((x, y) => (x.openDated < y.openDated ? -1 : 1))[0];
    const mem = (a, detail) => ({ id: a.id, name: a.name, detail });
    const groups = [
      {
        key: "slipping", label: "Slipping", color: "#8C2B22", filterKey: "slip", hood: topHood,
        rule: "Past their own reorder rhythm, or nobody has spoken to them.",
        question: "Is something wrong here?",
        members: slip.map((a) => mem(a, a.pastCadence ? `${a.daysSince}d, usually ${a.cadence}` : `no contact in ${a.daysSpoke != null ? a.daysSpoke + "d" : "60+d"}`)),
        prompts: [
          { label: "Since a substitution", rule: "Slipping accounts that declined a substitution in the last 90 days, and have slowed since.", key: "sub", count: slip.filter((a) => a.declinedSub).length },
          { label: "After a complaint", rule: "Slipping accounts with an unresolved complaint on file.", key: "complaint", count: slip.filter((a) => a.hasComplaint).length },
          { label: "No clear reason", rule: "Slipping with nothing on file, no complaint and no declined substitution, to explain it. Worth a call.", key: "unknown", count: slip.filter((a) => !a.declinedSub && !a.hasComplaint).length },
        ],
      },
      {
        key: "outstanding", label: "Outstanding", color: "#8C6A2B", filterKey: "outs",
        rule: "An unresolved complaint, a declined substitution, or a stated condition past its date.",
        question: "What do I owe them?",
        members: outs.map((a) => mem(a, a.open || "declined substitution, no follow-up")),
        prompts: [
          { label: "Open the longest", rule: "Outstanding items sorted by age, oldest first.", key: "old", note: oldestOut ? `oldest since ${MONTH(oldestOut.openDated)}` : "—", count: outs.length },
          { label: "Waiting on us", rule: "Raised in a call, email, or note, and we owe the next move: a complaint, a request, or a condition to action.", key: "waitus", count: outs.filter((a) => a.hasOpen).length },
          { label: "Waiting on them", rule: "We offered a substitution they declined, and we're waiting to hear what they'd prefer.", key: "waitthem", count: outs.filter((a) => a.declinedSub && !a.hasOpen).length },
        ],
      },
      {
        key: "opportunity", label: "Opportunity", color: "#2D5016", filterKey: "opps",
        rule: "Accounts to get ahead of, a product they asked for, a category they under-buy, a standing deal worth proposing. Nobody prompted this one.",
        question: "Who should hear about this?",
        members: opps.map((a) => mem(a, a.oppItem ? `asked about ${a.oppItem}, we were out` : "has a reason on file")),
        prompts: [],   // the card + "Products, who to pitch" panel cover this; no dead prompts
      },
    ];
    // per-row group membership, so the table can filter to a selected card
    rows.forEach((r) => {
      const a = byId[r.id];
      r.slip = !!(a.pastCadence || a.noContact60);
      r.outs = !!(a.hasOpen || a.declinedSub);
      r.opps = !!a.oppAsked;
      r.declinedSub = !!a.declinedSub;
      r.openFromCall = !!a.openFromCall;
      r.hasComplaint = !!a.hasComplaint;
      r.openDated = a.openDated || null;   // oldest open-item date, for "open the longest" sort
    });

    // ---- products panel: one representative item per category, and who in the
    // book would most likely want it (buys that category, ranked by value; flags
    // anyone who already asked for it). The reverse of the account view. ----
    const catAccts = d.prepare(`SELECT account_id, name, categories, round(annual_value) annual FROM accounts WHERE ${BOOK}`)
      .all().map((a) => ({ id: a.account_id, name: a.name, cats: (a.categories || "").split(","), annual: a.annual }));
    const prodList = d.prepare(
      `SELECT sku_id, name, category, in_stock FROM skus
        WHERE sku_id IN (SELECT min(sku_id) FROM skus WHERE name NOT LIKE 'SKU-%' GROUP BY category)
        ORDER BY category`).all();
    const inqBySku = {};
    d.prepare(`SELECT DISTINCT requested_sku_id sku, account_id FROM inquiries WHERE ${BOOK} AND requested_sku_id IN (${prodList.map((p) => p.sku_id).join(",") || 0})`)
      .all().forEach((r) => { (inqBySku[r.sku] = inqBySku[r.sku] || new Set()).add(r.account_id); });
    const products = prodList.map((p) => ({
      sku: p.sku_id, name: p.name, category: p.category, inStock: !!p.in_stock,
      likely: catAccts.filter((a) => a.cats.includes(p.category)).sort((x, y) => y.annual - x.annual).slice(0, 6)
        .map((a) => ({ id: a.id, name: a.name, annual: a.annual, asked: !!(inqBySku[p.sku] && inqBySku[p.sku].has(a.id)) })),
    }));

    // ---- "needs attention now": a flat, ranked list of SPECIFIC items, each a
    // named account + its most urgent concrete reason (like the Le Perchoir line),
    // not category counts. One entry per account, most urgent reason wins. ----
    const lcf = (s) => (s ? s.charAt(0).toLowerCase() + s.slice(1) : s);
    const pri = [];
    accts.forEach((a) => {
      let w = 0, text = null;
      if (a.recentUnsub) { w = 5; text = `unsubscribed from campaigns${a.isLargest ? ", your largest account" : ""}`; }
      else if (a.hasComplaint && a.open) { w = 4; text = lcf(a.open); }
      else if (a.hasOpen && a.open) { w = 3; text = lcf(a.open); }
      else if (a.pastCadence) { w = 2; text = `hasn't ordered in ${a.daysSince} days, past its usual ~${a.cadence}-day rhythm`; }
      if (text) pri.push({ id: a.id, name: a.name, text, w, val: a.annualValue });
    });
    pri.sort((x, y) => (y.w - x.w) || (y.val - x.val));
    const priorities = pri.slice(0, 8).map((p) => ({ id: p.id, name: p.name, text: p.text }));

    const totalAnnual = rows.reduce((s, r) => s + (r.annual || 0), 0);
    const contactedThisMonth = accts.filter((a) => a.daysSpoke != null && a.daysSpoke <= 30).length;

    res.setHeader("content-type", "application/json");
    res.setHeader("cache-control", "no-store");
    res.status(200).json({
      anchor,
      count: rows.length,
      totalAnnual,
      contactedThisMonth,
      filters,
      insights,
      groups,
      products,
      priorities,
      rows,
    });
  } catch (err) {
    res.status(500).json({ error: String((err && err.message) || err) });
  }
};

function lc(s) {
  if (!s) return "";
  s = s.charAt(0).toLowerCase() + s.slice(1);
  return s.replace(/\.$/, "");
}
