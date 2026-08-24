// GET /api/data
// Everything numeric in the prototype is derived here, live from foodie.db.
// Product names + message prose are NOT in the DB (SKUs are generated codes),
// so those stay in the hand-authored layer in index.html, merged by account id.
const { db } = require("./_db");

module.exports = (req, res) => {
  try {
    const d = db();

    // ---- the 15 named demo accounts (account_id < 20000) -------------------
    const accounts = d
      .prepare(
        `SELECT a.account_id                              AS id,
                a.name, a.neighborhood, a.cuisine, a.contact,
                a.tier, a.categories,
                round(a.annual_value)                     AS annualValue,
                round(a.orders_per_month, 1)              AS ordersPerMonth,
                (SELECT max(order_date) FROM orders o
                   WHERE o.account_id = a.account_id)     AS lastOrder,
                (SELECT count(*) FROM inquiries i
                   WHERE i.account_id = a.account_id)     AS inquiries,
                (SELECT count(*) FROM campaign_sends c
                   WHERE c.account_id = a.account_id)     AS sends,
                (SELECT coalesce(sum(converted),0) FROM campaign_sends c
                   WHERE c.account_id = a.account_id)     AS converted,
                (SELECT coalesce(max(unsubscribed),0) FROM campaign_sends c
                   WHERE c.account_id = a.account_id)     AS unsubscribed
           FROM accounts a
          WHERE a.account_id < 20000
          ORDER BY a.annual_value DESC`
      )
      .all();

    // per-account channel split (standing vs portal vs inquiry vs campaign)
    const chanStmt = d.prepare(
      `SELECT channel, count(*) n, round(sum(order_value)) val
         FROM orders WHERE account_id = ? GROUP BY channel`
    );
    for (const a of accounts) {
      a.channels = chanStmt.all(a.id);
      a.unsubscribed = !!a.unsubscribed;
      a.categories = (a.categories || "").split(",").filter(Boolean);
    }

    // ---- PulseBoard: team-wide metrics, last 30 days -----------------------
    // Event metrics below are scoped to a rolling 30-day window, anchored to
    // the latest date present in the data (NOT the wall clock) so the demo is
    // deterministic. Structural totals — accounts, revenue, AM headcount — are
    // point-in-time and stay all-time. Date columns: drafts.created_date,
    // inquiries.received_date, campaign_sends.sent_date.
    const one = (sql) => d.prepare(sql).get();
    const anchor = one(`SELECT max(order_date) v FROM orders`).v;
    const since = one(`SELECT date('${anchor}','-29 days') v`).v; // 30 inclusive days
    const pulse = {
      windowDays: 30,
      windowSince: since,
      messagesHandled: one(`SELECT count(*) v FROM drafts WHERE created_date >= '${since}'`).v,
      sent: one(`SELECT count(DISTINCT e.draft_id) v FROM draft_events e JOIN drafts d ON d.draft_id=e.draft_id WHERE e.event_type='sent' AND d.created_date >= '${since}'`).v,
      inquiriesTotal: one(`SELECT count(*) v FROM inquiries WHERE received_date >= '${since}'`).v,
      agentHandled: one(`SELECT sum(agent_handled) v FROM inquiries WHERE received_date >= '${since}'`).v,
      editRate: one(
        `SELECT round(100.0*sum(CASE WHEN edit_depth>0 THEN 1 ELSE 0 END)/count(*)) v FROM drafts WHERE created_date >= '${since}'`
      ).v,
      avgEditDepth: one(
        `SELECT round(100.0*avg(edit_depth)) v FROM drafts WHERE edit_depth>0 AND created_date >= '${since}'`
      ).v,
      editCategories: d
        .prepare(
          `SELECT edit_category category, count(*) n FROM drafts
            WHERE edit_depth>0 AND created_date >= '${since}' GROUP BY edit_category ORDER BY n DESC`
        )
        .all(),
      campaignConversion: one(
        `SELECT round(100.0*sum(converted)/count(*)) v FROM campaign_sends WHERE sent_date >= '${since}'`
      ).v,
      unsubRate: one(
        `SELECT round(100.0*sum(unsubscribed)/count(*),1) v FROM campaign_sends WHERE sent_date >= '${since}'`
      ).v,
      unsubIrrelevant: one(
        `SELECT round(100.0*sum(unsubscribed)/count(*),1) v FROM campaign_sends WHERE was_relevant=0 AND sent_date >= '${since}'`
      ).v,
      unsubRelevant: one(
        `SELECT round(100.0*sum(unsubscribed)/count(*),1) v FROM campaign_sends WHERE was_relevant=1 AND sent_date >= '${since}'`
      ).v,
      inbound: one(`SELECT count(*) v FROM drafts WHERE workflow='inbound' AND created_date >= '${since}'`).v,
      outbound: one(`SELECT count(*) v FROM campaign_sends WHERE sent_date >= '${since}'`).v,
      totalAccounts: one(`SELECT count(*) v FROM accounts`).v,
      totalRevenue: one(`SELECT round(sum(annual_value)) v FROM accounts`).v,
    };

    // daily order volume, last 30 days (hero bar chart). Orders carry real
    // day-to-day variation; drafts/inquiries are generated at a flat 80/day.
    const volRows = d
      .prepare(
        `SELECT substr(order_date,1,10) day, count(*) n
           FROM orders GROUP BY day ORDER BY day DESC LIMIT 30`
      )
      .all()
      .reverse();
    pulse.dailyVolume = volRows.map((r) => r.n); // hero bar heights
    pulse.dailyVolumeDays = volRows.map((r) => r.day); // parallel date labels

    // ---- per-tile weekly trend series, last 12 weeks, all live -------------
    // Each sparkline plots a REAL metric so hover reports the true value + its
    // unit, not a decorative number. Every series is [{wk, v}] oldest→newest;
    // wk is the first calendar day seen in that ISO week. Tiles with no real
    // time source (AM hours saved, avg response time) are deliberately absent
    // here and rendered as "modeled" on the client rather than faked.
    // `weeklyC` drops the most-recent row — the in-progress current week, which
    // is only partial (today is mid-week) and would otherwise distort the
    // sparkline's min/max and range caption. We pull 13 and keep 12 complete
    // weeks. Conversion is monthly-cadence (campaigns fire on the 1st) so its
    // latest bucket isn't partial; it keeps the plain `weekly` helper.
    const weekly = (sql) => d.prepare(sql).all().reverse();
    const weeklyC = (sql) => d.prepare(sql).all().slice(1).reverse();
    pulse.series = {
      // messages handled === drafts generated in this dataset
      messages: weeklyC(
        `SELECT substr(min(created_date),1,10) wk, count(*) v
           FROM drafts GROUP BY strftime('%Y-%W', created_date)
          ORDER BY strftime('%Y-%W', created_date) DESC LIMIT 13`
      ),
      editRate: weeklyC(
        `SELECT substr(min(created_date),1,10) wk,
                round(100.0*sum(CASE WHEN edit_depth>0 THEN 1 ELSE 0 END)/count(*),1) v
           FROM drafts GROUP BY strftime('%Y-%W', created_date)
          ORDER BY strftime('%Y-%W', created_date) DESC LIMIT 13`
      ),
      editDepth: weeklyC(
        `SELECT substr(min(created_date),1,10) wk, round(100.0*avg(edit_depth),1) v
           FROM drafts WHERE edit_depth>0 GROUP BY strftime('%Y-%W', created_date)
          ORDER BY strftime('%Y-%W', created_date) DESC LIMIT 13`
      ),
      conversion: weekly(
        `SELECT substr(min(sent_date),1,10) wk,
                round(100.0*sum(converted)/count(*),1) v
           FROM campaign_sends GROUP BY strftime('%Y-%W', sent_date)
          ORDER BY strftime('%Y-%W', sent_date) DESC LIMIT 12`
      ),
      adoption: weeklyC(
        `SELECT substr(min(occurred_at),1,10) wk, count(DISTINCT actor_am_id) v
           FROM draft_events WHERE event_type='sent' AND actor_am_id IS NOT NULL
          GROUP BY strftime('%Y-%W', occurred_at)
          ORDER BY strftime('%Y-%W', occurred_at) DESC LIMIT 13`
      ),
    };
    pulse.amTotal = one(`SELECT count(*) v FROM account_managers`).v;
    // adoption = distinct AMs who actually SENT an agent draft in the window.
    // AMs who only open and discard (drafting from scratch) are not adopters, so
    // the defected AMs are correctly excluded — this reads below the 80 ceiling.
    pulse.amActive = one(
      `SELECT count(DISTINCT actor_am_id) v FROM draft_events
        WHERE event_type='sent' AND actor_am_id IS NOT NULL AND occurred_at >= '${since}'`
    ).v;

    // ======================= THE FIX (fixed-mode data) ===================
    // Everything fixed mode reads. Current mode never touches this block, so
    // current-mode rendering is byte-identical. One fetch carries both, so
    // flipping modes is instant (no round trip on the reveal).
    const fAll = (sql) => d.prepare(sql).all();
    const fGet = (sql) => d.prepare(sql).get();

    // provenance: every source document, keyed by id, so any quoted string
    // on screen can be traced back to a call / note that exists today.
    const documents = {};
    for (const doc of fAll(
      `SELECT doc_id, account_id, kind, occurred_at, author, title, body FROM source_documents`
    ))
      documents[doc.doc_id] = doc;

    // pending capture candidates for an account (the panel). prechecked is
    // COMPUTED (confidence >= 0.85), never stored.
    const candidatesFor = (acc) =>
      fAll(
        `SELECT f.fact_id, f.statement, f.source_kind, f.source_doc_id, f.source_excerpt,
                f.source_locator, f.confidence, f.affects, d.kind, d.occurred_at
           FROM buyer_facts f LEFT JOIN source_documents d ON d.doc_id = f.source_doc_id
          WHERE f.account_id = ${acc} AND f.am_decision IS NULL
          ORDER BY f.confidence DESC`
      ).map((r) => ({
        ...r,
        affects: r.affects ? JSON.parse(r.affects) : [],
        prechecked: r.confidence >= 0.85 ? 1 : 0,
      }));

    // ranked substitution suggestions — the cascade (Level 1 history, Level 3
    // catalogue). Requested SKU is out of stock, so the in_stock filter drops
    // it. `like` narrows the pool to the same product family for the demo.
    const rankFor = (acc, cat, like) =>
      fAll(
        `WITH history AS (
           SELECT offered_sku_id sku_id, SUM(buyer_outcome='accepted') accepted, COUNT(*) offered,
                  MAX(CASE WHEN buyer_outcome='accepted' THEN resolved_date END) last_accepted
             FROM substitutions WHERE account_id = ${acc} GROUP BY offered_sku_id),
         bias AS (SELECT sku_id, SUM(bias) bias FROM account_sku_bias
                   WHERE account_id = ${acc} GROUP BY sku_id)
         SELECT k.name, k.texture,
                COALESCE(h.accepted,0) accepted, COALESCE(h.offered,0) offered, h.last_accepted,
                CASE WHEN h.accepted>0 THEN 'buyer history' ELSE 'catalogue match' END basis,
                CASE WHEN h.offered>0 AND h.accepted=0 THEN 1 ELSE 0 END declined
           FROM skus k
           LEFT JOIN history h ON h.sku_id = k.sku_id
           LEFT JOIN bias    b ON b.sku_id = k.sku_id
          WHERE k.category = '${cat}' AND k.in_stock = 1
            ${like ? `AND k.name LIKE '%${like}%'` : ""}
          ORDER BY COALESCE(h.accepted,0) DESC, COALESCE(h.offered,0) DESC,
                   COALESCE(b.bias,0) DESC, k.sku_id LIMIT 2`
      );

    const railFor = (acc) => {
      const a = fGet(
        `SELECT annual_value, tier, neighborhood, cuisine, contact FROM accounts WHERE account_id = ${acc}`
      );
      // Exposure = inquiry-channel dollars over the trailing year (the same
      // figure the drawer reports as "Inquiry-driven"), not the 30-day pulse
      // window — that read $0 for almost every account and contradicted both
      // the drawer and the fact that the buyer is messaging inbound right now.
      const exposureSince = one(`SELECT date('${anchor}','-365 days') v`).v;
      const exposure = fGet(
        `SELECT COALESCE(SUM(order_value),0) v FROM orders
          WHERE account_id = ${acc} AND channel='inquiry' AND order_date >= '${exposureSince}'`
      ).v;
      const subs = fGet(
        `SELECT COUNT(*) q, COALESCE(SUM(buyer_outcome='accepted'),0) a FROM substitutions WHERE account_id = ${acc}`
      );
      return {
        annualValue: Math.round(a.annual_value),
        exposure: Math.round(exposure),
        tier: a.tier, contact: a.contact,
        subsInRecord: subs.q, subsAccepted: subs.a,
      };
    };

    // Vinoteca banner: the 12-March decline + the texture excerpt behind it
    const vDecline = fGet(
      `SELECT s.resolved_date, k.name FROM substitutions s JOIN skus k ON k.sku_id = s.offered_sku_id
        WHERE s.account_id = 10428 AND s.buyer_outcome='declined' ORDER BY s.resolved_date DESC LIMIT 1`
    );
    const vTexture = fGet(
      `SELECT source_excerpt, source_locator, source_doc_id FROM buyer_facts
        WHERE account_id = 10428 AND dedup_key='texture_soft'`
    );

    // auto-send eligibility for Café Duvel's AM (the "N of M" on Screen 2).
    // Auto-send applies below the top tier, on in-stock confirmations with no
    // substitution. Measured per confirmation: of this AM's below-top-tier
    // inbound inquiries in the window, how many were for an in-stock item
    // (so no substitution, nothing to review). A real fraction, not tier alone.
    const duvelAm = fGet(`SELECT am_id FROM accounts WHERE account_id = 10248`).am_id;
    const autoSend = fGet(
      `SELECT COUNT(*) total,
              COALESCE(SUM(CASE WHEN k.in_stock=1 THEN 1 ELSE 0 END),0) eligible
         FROM inquiries i
         JOIN accounts a ON a.account_id = i.account_id
         LEFT JOIN skus k ON k.sku_id = i.requested_sku_id
        WHERE a.am_id = ${duvelAm} AND a.tier <> 'A' AND i.received_date >= '${since}'`
    );

    // retirement demo: kept facts whose newest evidence is >12 months old
    const retired = fAll(
      `SELECT f.account_id, f.statement, d.occurred_at FROM buyer_facts f
         JOIN source_documents d ON d.doc_id = f.source_doc_id
        WHERE f.am_decision='kept' AND d.occurred_at < date('${anchor}','-12 months')`
    );

    // substitution accept rate, weekly, last 90 days (Screen 5, leading metric)
    const substAcceptRate = fAll(
      `SELECT substr(min(resolved_date),1,10) wk,
              round(100.0*SUM(buyer_outcome='accepted')/COUNT(*),1) v
         FROM substitutions WHERE resolved_date >= date('${anchor}','-90 days')
        GROUP BY strftime('%Y-%W', resolved_date) ORDER BY strftime('%Y-%W', resolved_date)`
    );

    // ══ PulseBoard rebuilt: the four buildable charts ═════════════════════
    const launchISO = fGet(`SELECT date('${anchor}','-120 days') d`).d;   // agent launch ~4 months back

    // 2 · agent coverage weekly: inquiry-channel orders as a share of all orders
    const coverageWeekly = fAll(
      `SELECT substr(min(order_date),1,10) wk,
              round(100.0*sum(channel='inquiry')/count(*),1) v
         FROM orders WHERE order_date >= '${launchISO}'
        GROUP BY strftime('%Y-%W', order_date) ORDER BY strftime('%Y-%W', order_date)`
    );

    // 3 · substitution accept rate weekly, split by AM action (sent vs replaced)
    const subByAction = fAll(
      `SELECT substr(min(resolved_date),1,10) wk,
              round(100.0*sum(CASE WHEN am_action='sent_as_is' AND buyer_outcome='accepted' THEN 1 ELSE 0 END)
                    /NULLIF(sum(am_action='sent_as_is'),0),0) sent,
              round(100.0*sum(CASE WHEN am_action='replaced' AND buyer_outcome='accepted' THEN 1 ELSE 0 END)
                    /NULLIF(sum(am_action='replaced'),0),0) replaced
         FROM substitutions WHERE resolved_date >= '${launchISO}'
        GROUP BY strftime('%Y-%W', resolved_date) ORDER BY strftime('%Y-%W', resolved_date)`
    );

    // 4 · conversion against unsubscribe, monthly, one axis
    const convUnsub = fAll(
      `SELECT substr(min(sent_date),1,7) mo,
              round(100.0*sum(converted)/count(*),1) conv,
              round(100.0*sum(unsubscribed)/count(*),2) unsub
         FROM campaign_sends GROUP BY strftime('%Y-%m', sent_date) ORDER BY strftime('%Y-%m', sent_date)`
    );

    // 1 · retention curves. Fix each account's cohort at launch by its agent-era
    // inbound drafts, then track the share still ordering each month, by tier.
    const months = fAll(`SELECT DISTINCT strftime('%Y-%m', order_date) mo FROM orders WHERE order_date >= '${launchISO}' ORDER BY mo`).map((r) => r.mo);
    const draftAgg = fAll(`SELECT account_id, count(*) n, sum(CASE WHEN edit_depth>0 THEN 1 ELSE 0 END) e
                             FROM drafts WHERE workflow='inbound' AND created_date >= '${launchISO}' GROUP BY account_id`);
    const cohortOf = {};
    draftAgg.forEach((r) => { cohortOf[r.account_id] = r.e > r.n / 2 ? "edited" : (r.e < r.n / 2 ? "unedited" : "mixed"); });
    const accs = fAll(`SELECT account_id, tier FROM accounts`);
    const tierOf = {};
    accs.forEach((a) => { tierOf[a.account_id] = a.tier; if (!cohortOf[a.account_id]) cohortOf[a.account_id] = "never"; });
    const orderedByMonth = {}; months.forEach((m) => (orderedByMonth[m] = new Set()));
    fAll(`SELECT DISTINCT account_id, strftime('%Y-%m', order_date) mo FROM orders WHERE order_date >= '${launchISO}'`)
      .forEach((r) => { if (orderedByMonth[r.mo]) orderedByMonth[r.mo].add(r.account_id); });
    const COH = ["never", "unedited", "mixed", "edited"];
    const retentionFor = (tier) => {
      const ids = Object.keys(cohortOf).filter((id) => !tier || tierOf[id] === tier);
      const size = {}; COH.forEach((c) => (size[c] = 0));
      ids.forEach((id) => { size[cohortOf[id]]++; });
      const out = {}; COH.forEach((c) => (out[c] = []));
      months.forEach((m) => {
        const set = orderedByMonth[m];
        const cnt = {}; COH.forEach((c) => (cnt[c] = 0));
        ids.forEach((id) => { if (set.has(+id)) cnt[cohortOf[id]]++; });
        COH.forEach((c) => out[c].push(size[c] ? Math.round((100 * cnt[c]) / size[c]) : null));
      });
      return out;
    };
    const retention = { months, cohorts: COH, all: retentionFor(null), A: retentionFor("A"), B: retentionFor("B"), C: retentionFor("C") };

    // ---- Screen 5: PulseBoard, fixed. Five metrics, each a real query. ----
    const substAccept = fGet(
      `SELECT round(100.0*SUM(buyer_outcome='accepted')/COUNT(*)) v FROM substitutions
        WHERE resolved_date >= date('${anchor}','-90 days')`
    ).v;
    const outEditRate = fGet(
      `SELECT round(100.0*sum(was_edited)/count(*)) v FROM campaign_sends WHERE sent_date >= '${since}'`
    ).v;
    const coverTouched = fGet(
      `SELECT COUNT(*) v FROM (
         SELECT account_id FROM orders    WHERE order_date    >= '${since}'
         UNION
         SELECT account_id FROM inquiries WHERE received_date >= '${since}')`
    ).v;
    // reorder rate uses an ~8-day window (weekly cadence), same basis the case
    // reports; marked lagging because it moves only after buyers act.
    const reorderTouched = fGet(
      `SELECT COUNT(DISTINCT account_id) v FROM orders WHERE order_date >= date('${anchor}','-8 days')`
    ).v;
    const board = {
      substAccept,                                 // leading
      conversion: pulse.campaignConversion,        // paired with unsub
      unsub: pulse.unsubRate,
      accuracyInbound: 100 - pulse.editRate,       // split, not one blend
      accuracyOutbound: 100 - outEditRate,
      coverTouched, coverTotal: pulse.totalAccounts,
      reorderRate: Math.round((100 * reorderTouched) / pulse.totalAccounts),  // lagging
      reorderLagDays: 8,
      accuracyGiven: 84,                           // case-given, labelled as such
    };

    const fix = {
      documents,
      scenario: {
        vinoteca: {
          accountId: 10428,
          banner: vDecline && {
            declinedSku: vDecline.name,
            date: vDecline.resolved_date,
            quote: vTexture && vTexture.source_excerpt,
            locator: vTexture && vTexture.source_locator,
            docId: vTexture && vTexture.source_doc_id,
            provenance: "From the 12 March call. On file since March.",
          },
          suggestions: (() => {
            const list = rankFor(10428, "Specialty pasta", "paccheri");
            // the previously-declined option must be surfaced and flagged, never
            // silently dropped — that flag is the point of Screen 1.
            if (vDecline && !list.some((s) => s.declined)) {
              const declinedOpt = {
                name: vDecline.name, texture: "firm", accepted: 0, offered: 1,
                last_accepted: null, basis: "catalogue match", declined: 1,
              };
              if (list.length >= 2) list[1] = declinedOpt; else list.push(declinedOpt);
            }
            return list;
          })(),
          candidates: candidatesFor(10428),
          rail: railFor(10428),
        },
        duvel: {
          accountId: 10248,
          candidates: candidatesFor(10248), // empty — nothing needing a decision
          rail: railFor(10248),
        },
        nina: {
          accountId: 10310,
          candidates: candidatesFor(10310), // 3 sound + the 0.45 trap
          rail: railFor(10310),
        },
      },
      autoSend: { amId: duvelAm, eligible: autoSend.eligible, total: autoSend.total },
      substAcceptRate,
      board,
      charts: { retention, coverageWeekly, subByAction, convUnsub },
      retired,
    };

    res.setHeader("content-type", "application/json");
    res.setHeader("cache-control", "s-maxage=3600, stale-while-revalidate");
    res.status(200).json({ accounts, pulse, fix });
  } catch (err) {
    res.status(500).json({ error: String(err && err.message || err) });
  }
};
