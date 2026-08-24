# Prototype brief — Foodie AM Workspace

*What I'm building, why, and the prompt to hand a coding agent.*

---

## What this is

A product case study for InstaLily's Product Associate role. The fictional
client is **Foodie & Co.**, a $95M NY specialty food distributor with 80 account
managers covering 4,000 upscale restaurant accounts. InstaLily deployed AI
agents four months ago inside a custom platform — the **Foodie AM Workspace** —
plus **PulseBoard**, a leadership dashboard. The contract renews in 75 days and
the VP who owns the decision has disengaged.

Two live workflows, both inside the Workspace:

1. **Inbound order & substitution inquiries** (~2,400/month). A buyer asks
   whether something is in stock. The agent reads the message, checks inventory
   and lot data, drafts a reply proposing SKUs or substitutions. The AM reviews,
   edits, sends.
2. **Outbound pre-order campaigns** (~800/month). Seasonal items — white truffle,
   holiday charcuterie. The agent generates personalized outreach from each
   buyer's order history and suggests quantities. AMs review and send.

**Deliverables:** an interactive clickable prototype covering both a fix to the
existing Workspace and a new workflow, plus a slide presentation.

---

## My diagnosis (what the prototype has to demonstrate)

**Finding 1 — The agent knows the catalogue, not the buyer.**
The case states the inputs: Workflow 1 reads the message, inventory, and lot
data. Workflow 2 generates outreach *based on order history*. So the path that
most needs to know what a buyer wants is the one that doesn't look. That is
exactly the gap the edit data reports — AMs swapping SKUs "for buyer
preferences," supplying the input the agent doesn't have.

Two defects in two layers: **SKU accuracy is retrieval** (querying the wrong
table), **tone is generation**. They need different fixes.

Buyers exit two ways for one reason: inbound produces **complaints** (+18%
impersonality) because the buyer still needs the product and has no exit;
outbound produces **unsubscribes** (1.2% → 3.1%) because there's nothing to
complain about, it just wasn't for them. Complaints are loud and reversible.
Unsubscribes are quiet and permanent.

**Finding 2 — Foodie measures the agent's effort, not its effect.**
Four months in, nobody can say whether this worked. Every metric counts
activity. The 84% Agent Accuracy Score isn't just blended across two workflows —
it's the wrong construct, because a recommendation isn't accurate or inaccurate,
it's accepted or declined.

**Recommendation — one buyer context, one review surface.** Extend the buyer
context Workflow 2 already reads to Workflow 1's substitution ranking. Add the
one table neither has: substitution outcomes.

---

## Design rule that governs everything

**The current-state mock must look competent.**

A good team shipped this in four months. Plain, well-organised enterprise B2B.
If it reads as an obvious strawman the diagnosis becomes trivial and I'm beating
up a fictional colleague's work. "This looks fine, and here's why it isn't" is a
far stronger moment than "look how bad this is."

**The defects are absences, not ugliness.** They must not be fixed, annotated, or
softened in the current-state screens:

- The draft is **pre-filled the instant a message opens.** Send is the default
  path; editing is extra work. That is the rubber-stamp mechanism, on screen.
- The right rail has **no order history.** Contact, phone, last order date,
  delivery days, terms — then a dashed box saying order history lives in the
  accounts system. The AM would have to leave to check.
- **Zero provenance on substitutions.** The draft asserts a replacement is
  "comparable, same format and price band" — a defensible *inventory* match —
  with no reference to whether this buyer has ever accepted it.
- **The queue sorts by recency only.** No account value, no tier.
- **Campaigns are segment-first:** pick item → check category boxes → generate
  all → "Send all 41." Personalisation is in the prose, not the targeting.
- **PulseBoard is ten activity charts.** Volume is hero, the 84% sits beside it
  with no definition, and reorder rate and unsubscribe rate appear nowhere.

Critically: **the outbound drafts must be genuinely good.** Each one references
that buyer's real order history — last season's quantity, the dish it went on,
which delivery day ran short. The prose is fine, which is why edit depth is only
8%. The failure is visible only in the *list*, where a Japanese izakaya that
buys maitake and a Belgian café that buys one cheese are both in an Alba white
truffle campaign. Nothing on screen shows why anyone was included.

---

## What exists and what doesn't

**Exists:**
- `foodie-workspace-current.html` — the current-state mock. Four views (Inbound,
  Campaigns, Accounts, PulseBoard), all clickable, 15 hand-authored buyers with
  real product names, 11 personalised campaign drafts, working modals and toasts.
- `foodie-data/` — schema, generator, dials, queries, and a calibrated SQLite
  database. Supports the analysis, not the UI.

**Doesn't exist yet:**
- The **future-state** version of the Workspace (the fix)
- The **Part 2 workflow** — what the VP actually asked for
- Slides beyond the pre-part draft

---

## Two data sources, deliberately separate

The database stores SKUs as generated codes (`SKU-0142`). The prototype needs
real product names or the demo reads as placeholder. So:

- **Product-level detail stays hand-authored in the HTML.** Rustichella
  d'Abruzzo paccheri, Parmigiano Reggiano 36mo, Alba white truffle.
- **Account-level numbers come from the database** — tier, annual value —
  because those appear in both the prototype and the deck and must agree.

If asked whether they match: *same accounts, same tiers, same values;
product-level detail is hand-authored because generated SKU codes wouldn't demo
well.*

Consistency values for the 15 shared accounts:

```js
{id:10193, tier:'A', annualValue:116025, unsubscribed:true },  // Le Perchoir
{id:10428, tier:'A', annualValue:77352,  unsubscribed:false},  // Vinoteca Ardito
{id:10999, tier:'A', annualValue:59613,  unsubscribed:false},  // Aurum
{id:10310, tier:'A', annualValue:44196,  unsubscribed:false},  // Osteria Nina
{id:10086, tier:'B', annualValue:22921,  unsubscribed:false},  // Nonna Piera
{id:10917, tier:'B', annualValue:19362,  unsubscribed:false},  // Hearth & Bramble
{id:10771, tier:'B', annualValue:15582,  unsubscribed:false},  // Saltbox
{id:10634, tier:'B', annualValue:15245,  unsubscribed:false},  // Marisol
{id:10855, tier:'B', annualValue:11329,  unsubscribed:false},  // Kōji House
{id:10420, tier:'B', annualValue:10620,  unsubscribed:false},  // The Salt Cellar
{id:10502, tier:'C', annualValue:7299,   unsubscribed:false},  // The Wren & Larder
{id:10377, tier:'C', annualValue:6451,   unsubscribed:false},  // Verbena
{id:10788, tier:'C', annualValue:5871,   unsubscribed:false},  // Quince & Co.
{id:10611, tier:'C', annualValue:4943,   unsubscribed:false},  // Bar Ossola
{id:10248, tier:'C', annualValue:4641,   unsubscribed:false},  // Café Duvel
```

Note: **Le Perchoir is the largest account and it unsubscribed.** A $116K
relationship where the buyer opted out because category-flag targeting pitched
them something they don't buy. Best single demo moment available for the outbound
argument.

---

## THE PROMPT

Paste from here down, with `foodie-workspace-current.html` attached.

---

I'm building a product case study prototype. Attached is
`foodie-workspace-current.html` — a working mock of the **current state** of a
client's internal tool (the Foodie AM Workspace). It has four views: Inbound,
Campaigns, Accounts, PulseBoard.

**Do not improve the current-state mock.** Its shortcomings are deliberate and
they are the entire diagnosis. Specifically, leave these alone: the draft is
pre-filled on open, the right rail has no order history, substitutions carry no
provenance, the queue sorts by recency only, campaigns target by category
checkbox, and PulseBoard shows only activity metrics. If you find yourself
wanting to add a buyer-context panel or a "why this SKU" badge to the current
state, stop — that's the future state.

**Build the future state as a separate file**, `foodie-workspace-future.html`,
matching the existing visual system exactly (same CSS variables, same
components, same tone of copy). Reuse the same 15 buyers and the same product
names so the two files are directly comparable side by side.

The future state changes four things:

1. **Buyer context beside the draft.** Order cadence, what they've bought,
   prior substitutions and whether the buyer accepted or declined each one, and
   anything they've explicitly refused. Read from the fixture, not a stub.

2. **Provenance on every suggestion.** Each proposed SKU shows why it was
   chosen for this buyer — prior acceptance of that item or its attributes,
   falling back to segment-level, falling back to category similarity. Show
   which fallback level fired. When there's no history, say so and mark the
   suggestion low-confidence rather than presenting it as equivalent.

3. **One review surface for both workflows.** Inbound and outbound drafts go
   through the same component, because the AM's job is the same on both. Hard
   constraint: **commercial content never enters a service reply.** If the
   system surfaces a relevant item during an inbound exchange it appears in the
   AM's sidebar, never in the buyer's message.

4. **Relevance-based outbound targeting.** Replace category checkboxes with
   per-buyer relevance evaluated against the same buyer context. Show the
   segment shrinking, show which accounts dropped out and why, and show
   estimated revenue per send rather than raw conversion rate.

Use `Vinoteca Ardito` as the worked example: the buyer asks for Rustichella
d'Abruzzo paccheri; it's out of stock; the current state proposes Benedetto
Cavalieri with no context; the future state shows that this buyer **declined
that exact substitution in March** and ranks a different SKU first.

Keep it a single self-contained HTML file with no build step, openable from
`file://`. No localStorage. All buttons functional. Match the existing file's
restrained enterprise-B2B aesthetic — this should look like the same product
one version later, not a redesign.

---

## After the future state

The Part 2 workflow still needs designing before it's built. The VP's ask:
*"help my AMs stay genuinely connected to the 40 or 50 buyers they each cover —
be the kind of account manager they were when they only had 10."*

Design constraint from the case: it must live inside the Workspace and surface
in an AM's existing daily rhythm. Not a new destination they have to remember to
visit.

My direction: **event-triggered, not score-based.** Concrete triggers (order
cadence break against that account's own baseline, a SKU they buy coming back in
stock, a lot or vintage change on something they order) each carry a built-in
reason to reach out. A relationship score only ranks between competing triggers,
never generates them on its own.

Rationale: a score has no action attached and decays into wallpaper. Events
carry their own "so what." Also, a deterministic trigger has a stateable
definition — *fires when an account's inter-order interval exceeds its trailing
90-day median by 1.5x, minimum 3 prior orders* — which survives being asked how
it's computed. A composite score invites exactly the question that's hardest to
answer.

Still to specify before building: the trigger set, per-buyer and per-AM rate
limits, cold start for new accounts and new AMs, and what the AM sees when a
trigger fires.