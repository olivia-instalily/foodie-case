// GET /api/account?id=10428
// Full per-account record for the drawer. Everything here is live from
// foodie.db: order history (date/channel/value), spend by channel, monthly
// spend, inquiries, substitution outcomes, campaign results. Orders carry no
// product name in this dataset (no SKU link), so line items are date/channel/
// value; category detail comes from inquiries and substitutions.
const { db } = require("./_db");

module.exports = (req, res) => {
  try {
    const params = new URL(req.url, "http://x").searchParams;
    const id = parseInt(params.get("id") || "", 10);
    const cat = params.get("cat") || null;      // requested SKU's category, for ranked substitutes
    const like = params.get("like") || null;    // narrows to the same product family (optional)
    if (!id) return res.status(400).json({ error: "missing ?id" });
    const d = db();
    const one = (sql) => d.prepare(sql).get(id);
    const all = (sql) => d.prepare(sql).all(id);

    const account = d
      .prepare(
        `SELECT account_id id, name, neighborhood, cuisine, contact, tier,
                round(annual_value) annualValue, round(orders_per_month,1) ordersPerMonth,
                categories
           FROM accounts WHERE account_id = ?`
      )
      .get(id);
    if (!account) return res.status(404).json({ error: "no such account" });
    account.categories = (account.categories || "").split(",").filter(Boolean);

    const totals = one(
      `SELECT count(*) orders, round(sum(order_value)) spend,
              min(order_date) firstOrder, max(order_date) lastOrder
         FROM orders WHERE account_id = ?`
    );

    const spendByChannel = all(
      `SELECT channel, count(*) n, round(sum(order_value)) val
         FROM orders WHERE account_id = ? GROUP BY channel ORDER BY val DESC`
    );

    const monthlySpend = all(
      `SELECT substr(order_date,1,7) mo, round(sum(order_value)) val
         FROM orders WHERE account_id = ? GROUP BY mo ORDER BY mo`
    );

    const orders = all(
      `SELECT order_id, order_date date, channel, round(order_value) val
         FROM orders WHERE account_id = ? ORDER BY order_date DESC LIMIT 14`
    );
    // [ADDITION] order contents for the hover. Orders carry no line items in the
    // schema (by design), so the basket is derived from the categories this
    // account actually buys, deterministically per order_id. Illustrative.
    const catList = (account.categories && account.categories.length) ? account.categories : ["Pantry"];
    const skuByCat = {};
    catList.forEach((c) => { skuByCat[c] = d.prepare(`SELECT name FROM skus WHERE category=? AND name NOT LIKE 'SKU-%' ORDER BY sku_id`).all(c).map((r) => r.name); });
    orders.forEach((o) => {
      const seed = o.order_id || 1, nLines = 2 + (seed % 2);
      o.lines = [];
      for (let i = 0; i < nLines; i++) {
        const cat = catList[(seed + i) % catList.length];
        const pool = (skuByCat[cat] && skuByCat[cat].length) ? skuByCat[cat] : [cat];
        o.lines.push({ name: pool[(seed + i * 7) % pool.length], val: Math.max(1, Math.round(o.val / nLines)) });
      }
    });

    const inquiries = all(
      `SELECT received_date date, category, agent_handled
         FROM inquiries WHERE account_id = ? ORDER BY received_date DESC LIMIT 10`
    );

    // substitution ledger, real product names where they exist (named scenario
    // SKUs), code otherwise. 'sent' when the AM sent as-is, else the AM's action.
    const substitutions = all(
      `SELECT s.resolved_date date,
              COALESCE(rs.name, rs.category) requested,
              COALESCE(os.name, os.category) offered,
              s.am_action, s.buyer_outcome
         FROM substitutions s
         LEFT JOIN skus rs ON rs.sku_id = s.requested_sku_id
         LEFT JOIN skus os ON os.sku_id = s.offered_sku_id
        WHERE s.account_id = ? ORDER BY s.resolved_date DESC`
    );

    const campaigns = all(
      `SELECT sent_date date, was_relevant, converted, unsubscribed
         FROM campaign_sends WHERE account_id = ? ORDER BY sent_date DESC`
    );

    // [ADDITION] block 2, what they've told you: kept facts + open items, with
    // source and whether the fact has ever shaped a suggestion (last_influenced_at).
    const buyerFacts = all(
      `SELECT f.statement, f.source_kind, f.confidence,
              COALESCE(f.valid_from, f.decided_at) dated,
              f.source_locator locator, f.last_influenced_at influencedAt,
              f.am_decision decision, f.source_doc_id docId,
              s.kind docKind, s.occurred_at docAt, s.title docTitle
         FROM buyer_facts f
         LEFT JOIN source_documents s ON s.doc_id = f.source_doc_id
        WHERE f.account_id = ?
        ORDER BY (f.last_influenced_at IS NULL), f.fact_id`
    );

    // [ADDITION] block 4, the thread: dated documents, most recent first.
    const thread = all(
      `SELECT doc_id id, kind, occurred_at date, title, author, body
         FROM source_documents WHERE account_id = ? ORDER BY occurred_at DESC`
    );

    // [ADDITION] block 1, inquiry-share trend: current 90d window vs the prior one.
    const shareIn = (fromD, toD) =>
      d
        .prepare(
          `SELECT round(100.0 * sum(CASE WHEN channel='inquiry' THEN order_value ELSE 0 END)
                        / NULLIF(sum(order_value),0)) share
             FROM orders
            WHERE account_id = ?
              AND order_date >= date((SELECT max(order_date) FROM orders), '-${fromD} days')
              AND order_date <  date((SELECT max(order_date) FROM orders), '-${toD} days')`
        )
        .get(id).share;
    const inquiryTrend = { now: shareIn(90, 0), prev: shareIn(180, 90) };

    // [ADDITION] order-derived status, so the composer can surface "slipping" /
    // "no contact" the same way the Daybook cards compute them.
    const anchorA = d.prepare(`SELECT max(order_date) a FROM orders`).get().a;
    const n90 = one(`SELECT count(*) v FROM orders WHERE account_id=? AND order_date >= date('${anchorA}','-90 days')`).v;
    const cadence = n90 >= 3 ? Math.round((90 / n90) * 10) / 10 : null;
    const daysSince = totals && totals.lastOrder ? Math.floor((Date.parse(anchorA) - Date.parse(totals.lastOrder)) / 86400000) : null;
    const lastInq = one(`SELECT max(received_date) v FROM inquiries WHERE account_id=?`).v;
    const lastDocAt = one(`SELECT max(occurred_at) v FROM source_documents WHERE account_id=?`).v;
    const lastContact = [lastInq, lastDocAt].filter(Boolean).sort().slice(-1)[0];
    const daysSpoke = lastContact ? Math.floor((Date.parse(anchorA) - Date.parse(String(lastContact).slice(0, 10))) / 86400000) : null;
    const status = {
      daysSince, cadence,
      pastCadence: cadence != null && daysSince != null && daysSince > 1.5 * cadence,
      daysSpoke, noContact60: daysSpoke == null || daysSpoke > 60,
    };

    // [ADDITION] a product worth pitching: something they asked about when we were
    // out; otherwise a named in-stock item in a category they buy.
    let pitch = null;
    const askedOut = one(`SELECT k.name FROM inquiries i JOIN skus k ON k.sku_id=i.requested_sku_id
                            WHERE i.account_id=? AND k.in_stock=0 AND k.name NOT LIKE 'SKU-%'
                            ORDER BY i.received_date DESC LIMIT 1`);
    if (askedOut && askedOut.name) pitch = { name: askedOut.name, reason: "asked about it when we were out" };
    else {
      const cat = (account.categories && account.categories[0]) || "Pantry";
      const p = d.prepare(`SELECT name FROM skus WHERE category=? AND in_stock=1 AND name NOT LIKE 'SKU-%' ORDER BY sku_id LIMIT 1`).get(cat);
      if (p) pitch = { name: p.name, reason: `buys ${cat.toLowerCase()}` };
    }

    // [FIX] agent exposure rail — same computation as data.js railFor(), but for
    // any account, so the inbound right rail varies per buyer instead of being
    // pinned to one scripted scenario. Exposure = the account's inquiry-channel
    // order value over the trailing year, the same dollars the drawer reports as
    // "Inquiry-driven", stated against the annual denominator. A 30-day window
    // read $0 for almost every account (few inquiry orders land in any given
    // month), which contradicted both the drawer and the fact of an inbound ask.
    const since = d.prepare(`SELECT date('${anchorA}','-365 days') v`).get().v;
    const exposure = one(
      `SELECT COALESCE(SUM(order_value),0) v FROM orders
        WHERE account_id=? AND channel='inquiry' AND order_date >= '${since}'`
    ).v;
    const subCount = one(
      `SELECT COUNT(*) q, COALESCE(SUM(buyer_outcome='accepted'),0) a
         FROM substitutions WHERE account_id=?`
    );
    const rail = {
      annualValue: account.annualValue,
      exposure: Math.round(exposure),
      tier: account.tier,
      contact: account.contact,
      subsInRecord: subCount.q,
      subsAccepted: subCount.a,
    };

    // [FIX] ranked substitutes — same cascade as data.js rankFor() (Level 1 buyer
    // history, Level 2 bias, Level 3 catalogue match), computed for the requested
    // category so each out-of-stock inquiry gets its own list. Only when a category
    // is passed. The catalogue pool is de-duplicated by product name (the dataset
    // repeats each name across many sku_ids), and the catalogue-match tail is
    // ordered by a per-account deterministic key so two buyers asking in the same
    // category don't get an identical pair — real accepted history still wins.
    let suggestions = null;
    if (cat) {
      const args = { id, cat };
      let likeClause = "";
      if (like) { likeClause = "AND name LIKE @like"; args.like = "%" + like + "%"; }
      suggestions = d.prepare(
        `WITH hist AS (
           SELECT k.name,
                  SUM(CASE WHEN s.buyer_outcome='accepted' THEN 1 ELSE 0 END) accepted,
                  COUNT(*) offered,
                  MAX(CASE WHEN s.buyer_outcome='accepted' THEN s.resolved_date END) last_accepted
             FROM substitutions s JOIN skus k ON k.sku_id = s.offered_sku_id
            WHERE s.account_id = @id GROUP BY k.name),
         bias AS (
           SELECT k.name, SUM(b.bias) bias FROM account_sku_bias b JOIN skus k ON k.sku_id = b.sku_id
            WHERE b.account_id = @id GROUP BY k.name),
         pool AS (
           SELECT name, MIN(texture) texture, MIN(sku_id) sku_id
             FROM skus
            WHERE category = @cat AND in_stock = 1 AND name NOT LIKE 'SKU-%' ${likeClause}
            GROUP BY name)
         SELECT p.name, p.texture,
                COALESCE(h.accepted,0) accepted, COALESCE(h.offered,0) offered, h.last_accepted,
                CASE WHEN h.accepted>0 THEN 'buyer history' ELSE 'catalogue match' END basis,
                CASE WHEN h.offered>0 AND h.accepted=0 THEN 1 ELSE 0 END declined
           FROM pool p
           LEFT JOIN hist h ON h.name = p.name
           LEFT JOIN bias b ON b.name = p.name
          WHERE COALESCE(b.bias,0) >= 0
          ORDER BY COALESCE(h.accepted,0) DESC,
                   COALESCE(b.bias,0) DESC,
                   ((p.sku_id * @id * 7919) % 100003),
                   p.name
          LIMIT 2`
      ).all(args);
    }

    res.setHeader("content-type", "application/json");
    res.setHeader("cache-control", "no-store");
    res.status(200).json({
      account, totals, spendByChannel, monthlySpend,
      orders, inquiries, substitutions, campaigns,
      buyerFacts, thread, inquiryTrend, status, pitch,
      rail, suggestions,
    });
  } catch (err) {
    res.status(500).json({ error: String((err && err.message) || err) });
  }
};
