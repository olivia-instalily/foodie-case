# Foodie & Co. — Case Study Presentation Script

The complete guided-tour narration, in order (32 steps), as authored in `index.html`
(the `TOUR` array). HTML formatting is rendered here as emphasis, with an on-screen
note for each step. The deck runs in two modes: **Viewing: today** (the product as-is)
and **Viewing: the fix** (toggles automatically at "The fix").

---

## Opening

### Slide 1 — "A note on structure" · *(full-screen, Inbound behind)*

- This is one artifact doing two jobs. The presentation runs alongside a working prototype, walking through Foodie's product as it is today, the insights that can be drawn from the provided data, and the resulting changes I'd make to it.
- **Next** and **Back** move through the argument. The bar below jumps between sections. **Exit** leaves the commentary and hands you the product to click through yourself.
- Top right button toggles between **Viewing: today** and **Viewing: the fix**. The default is the pre-fix view. The transition point to show my additions occurs automatically when the Recommendation deliverable is made during the presentation sequence.

### Slide 2 — "Four months in. Renewal in 75 days." · *(full-screen)*

- 2 workflows touched by 80 AM's and a dashboard that falls short.
- *[Table of contents: **Current product** — Inbound · Outbound · PulseBoard. **Deliverables** — Finding · Prioritization · Schema · 75 days. **Recommendation** — The fix. **Addition** — Daybook. **Close** — The 75 days.]*

---

## Part 1 · Current Product

### Workflow 1 — Inbound (Chapter 1 of 3)

#### Slide 3 — "Workflow 1: Inbound order and substitution inquiries"

- A buyer asks whether something is in stock. The agent drafts a reply from inventory and lot data.
- **2,400 interactions a month.** ~1.5 interactions per AM per working day.

#### Slide 4 — "A draft exists before the AM opens the message." · *(highlights the editor)*

- Evidenced by an average edit depth of 23% applied mostly to tone and SKU fixes, this agent fails to draw on the deep client knowledge and history held by AM's.

#### Slide 5 — "Order history lives somewhere else" · *(highlights the right rail)*

- Checking on client history relies on AM knowledge or requires them to navigate off-screen to the accounts system. At an average of 50 accounts per AM, this adds a significant amount of time and effort that the agent was implemented to reduce.

#### Slide 6 — "Example [generated, not given]: The client declined this substitution in March" · *(highlights the draft)*

- The product Marco wants is out of stock, so the draft offers a different brand of a similar product. While it is an accurate catalogue match and a valid replacement option, Marco already turned it down once. If the AM knows this, they rewrite the draft or begin from scratch, taking note not to trust the agent's future suggestions and hurting user rates. If they don't remember this, the AM sends an option to Marco that signals to him that Foodie & Co. isn't providing the level of service he was promised.
- **Figures:** 26% of drafts edited · SKU + tone, most common edits

### Workflow 2 — Outbound (Chapter 2 of 3)

#### Slide 7 — "Workflow 2: Outbound pre-order campaigns" · *(Campaigns view)*

- Seasonal campaigns are triggered at certain times in order to push specific products. They are released to clients based on order history. **Around 800 interactions a month.**

#### Slide 8 — "Best AM sentiment in the deployment" · *(highlights the campaign card)*

- Framed around user sentiment, this workflow is behaving well: time on campaigns for AM's is reduced and their edits are minimal.
- This is evidence of the AM's appreciating drawing from order history.
- **Figures:** 62% less time per message · 34% edited · 8% depth

#### Slide 9 — "This is despite the fact that the unsubscribe rate has tripled"

- This points to a disconnect between user sentiment and business impact.
- While it could be argued that the time saved per AM on these messages balances out the deal lost from lack of engagement, unsubscription is both permanent and compounding in that it prevents the buyer's reception of any future campaigns.

### PulseBoard (Chapter 3 of 3)

#### Slide 10 — "What leadership sees" · *(PulseBoard)*

- The VP who owns the renewal logs in once every two weeks for 47 seconds.

#### Slide 11 — "78% of clicks land here" · *(highlights the volume chart)*

- A metric that moves when the agent is put to work and is blind to both user sentiment and business impact:

#### Slide 12 — "84%, blended across both workflows" · *(opens the tickets detail)*

- Shipped month 3. Support tickets up 4x. Most asked the same two things: what does this number mean, and is it good.

#### Slide 13 — "There is no version of this number that informs whether she should renew." · *(opens the tickets detail)*

- This blends both workflows, preventing any nuanced understanding of what is working where, and the metric itself is flawed.
- On Workflow 1, an ideal response takes into account the client's history and preferences. It currently doesn't generate its answers from that data, thus accuracy references at most a clean catalogue swap suggestion.
- On Workflow 2, suggestions are made based on order history with a different and more nuanced metric of accuracy.

---

## Deliverables

#### Slide 14 — Finding 2: "How the product is read" · *(full-screen)*

- **Inbound:** 3 of 18 AMs closest to the biggest accounts quit using it entirely. Buyers have complained about tone. **Outbound:** the AMs are happiest here, and buyers are quietly leaving.
- One outcome is visible to the user. The other isn't.
- 84% is a single blend across two workflows failing differently. Catalogue matching and accuracy doesn't measure outcome.
- What this means: the VP has no way to scope her decision in either direction.
- **Figures:** 84% blended · 78% clicks, one chart · 4x support tickets

#### Slide 15 – Why this prioritization

- **61% - 44% drop in reorder rate in the last 60 days.**
- Reorder rate fell from 61% to 44% over 60 days. The agent has been live for four months.
- Assuming that, consistent with restaurant and food industry ordering, most of Foodie's revenue comes from recurring ordering rather than one-off inquiries, the purchasing the agent directly touches is a small share of the total. 2,400 engagements a month across 4,000 accounts that likely each order several times a month.
- Yet it sits exactly where customers form judgements. A recurring order arriving as scheduled doesn't bend sentiment. The way an AM handles a one-off request, and what they recommend, does.
- Which explains the gap between month four and the last 60 days. Tone complaints don't produce an immediate fall. They accumulate, and they leak outward into the recurring orders the agent never touches but which carry the volume.
- And the same lag runs forward. Buyer-side recovery won't be visible inside 75 days. So the user-side fix has to be prioritized over the reporting that will eventually show business impact and allow the VP to make an informed decision.

#### Slide 16 - DB build-out strategy

*DB build out process: logic to constructintg out a full schema + extended data consistent with the givens.*

- Using the givens from the case, this is the logic employed in generating the database around which this demo is built:

- **Givens as global constants.** Revenue, account count, AM count, edit rates, reorder rate, conversion. Locked, never touched.
- **Sort accounts into three sizes.** The case says 18 of 80 AMs cover the largest accounts, so I used that to size the top tier and split the rest into middle and lower.
- **Describe each tier by how that restaurant orders.** Deliveries per month is perishability, line items is menu breadth, price per line is grade. Reasons, not size assumptions.
- **Multiply and the values fall out.** I never set a dollar figure. Total lands at $95.6M against the case's $95M, so the revenue concentration is a result, not a decision.
- **Re-run each factor across a range.** Revenue swings; which accounts hold it doesn't. The concentration is the claim, not the number.
- **Generate a year of activity.** Orders, inquiries, drafts, substitutions, calls, notes. Every order records why it exists: standing, portal, inquiry, or campaign. That split is what lets you ask what the agent actually touches.
- **Impose the decline, don't derive it.** The case says reorder fell 61% to 44%, so I made that happen. Finding it again proves nothing about cause. The database shows the query that would settle it.
- **Validate.** Every published figure re-queried and confirmed. Fixed seed, rebuilds identically.

#### Slide 17 — Schema visualization · *(full-screen, interactive)*

- [NUMBER] tables — click any one and its subfields to see what it holds and where its values came from.
- *(No narration; this is the interactive provenance map — click a table to enlarge it and see column-level Given / Derived / Invented / New sourcing.)*

#### Slide 18 — "What we should aim to move in 75 days with a fix" *(Before the vote)*

- Reorder rate and buyer sentiment won't move much in 75 days. AM behaviour can.
- The three AMs who went manual cover the largest accounts, they see every draft, and they carry the cost when one is wrong. That's why they stopped, and it's why their coming back means something a usage count never could.
- Edit rate is the obvious target and it's unreadable. 26% edited means 74% something, and that bucket holds read-and-approved, waved-through-unread, opened-and-rewritten, and never-opened. The three AMs sit inside it, indistinguishable from someone who agreed.
- So I'd log the draft lifecycle and measure four things instead:

**Metrics table:**

| Leading | Predicts | Lag |
|---|---|---|
| Substitution accept rate | The suggestions got better | 3 wks |
| SKU edits down, tone edits down | Which of the two defects closed | 3 wks |
| Edit depth by category | Which defect got fixed | 3 wks |
| Time between opening a draft and sending it | Whether AMs are still reading them | 3 wks |
| The 3 AMs using drafts again | It's safe on the biggest accounts | 4–6 wks |

- Sentiment about time saved is not evidence of quality. Workflow 2 already proved that here.

---

## The Recommendation · The fix  *(mode switches to "Viewing: the fix")*

#### Slide 19 — "Give the agent what the AM already knows" · *(Inbound, fixed, Marco)*

- The agent was falling short on two counts: tone and the product recommendation itself.
- Recommendation: Most of the information already exists and is not connected: As in the previous example: Marco's order history and the March call.
- Present these to the AM as both a reference and a tool to be looped into email generation.
- Add helpful context while maintaining human oversight.
- **Position the agent to learn from AM style and customer style.**
- Generate accurate

#### Slide 20 — "Review where it matters, auto-send where it doesn't" · *(Café Duvel, auto-send banner)*

- A C-tier in-stock confirmation with no substitution. Nothing to check, nothing to get wrong. It sends itself, and the AM's attention goes to the drafts that need it.
- **This is the answer to "so you slowed everyone down."**

#### Slide 21 — "The one it got wrong, and what that costs" · *(Nina, Worth remembering)*

- "New chef starting in April," verbatim from the call — and wrong. Gio was talking about his Brooklyn location, and corrected himself seven seconds later. The extractor can't tell; the AM can.
- **One unchecked box is the entire cost of a wrong candidate.**

#### Slide 22 — "The March call was already on file" · *(highlights ranked substitutes)*

- Marco refused this exact substitute and said why: texture, not brand. It rides as a notice on the declined option, and the source opens the call itself. The old system proposed the Cavalieri anyway.
- **This half is plumbing. It works on day one.**

#### Slide 23 – Opening a path for personalization · *(highlights the custom field, fill it with "he's going on vacation soon to spain" filled in. adds it + check off and generate email.)*

- The AM also remembers that Marco mentioned that he'll be going on vacation to Spain next week. The AM can add that as a field and loop it into the email to add an extra personal touch.

#### Slide 24 – build institutional knowledge · *(pin a note to profile)*

- The AM understands that Marco's declaration about his company's preferences is important to remember. The AM can pin this information to the company's profile so that he or another AM can draw from this information later on.
- Additionally, an understanding of Marco's emailing style preferences gets stronger with more interaction, better informing how to generate drafts on the AM's side.

---

## Addition · Daybook *(Accounts view, fixed)*

**The VP's ask:**

> "What I actually want is for my AMs to stay genuinely connected to the 40 or 50 buyers they each cover. Something that helps them be the kind of account manager they were when they only had 10 accounts."

#### Slide 25 — "Five numbers leadership can read" · *(Daybook page, fixed)*

#### Slide 26 — "The first thing here that doesn't wait" · *(full-screen)*

- Everything in the product today waits for a stimulus. Workflow 1 fires when a buyer writes in; Workflow 2 fires on a campaign date. So an account that orders reliably and asks for nothing is rarely touched by the agent.
- Daybook sits on top of the accounts screen an AM already opens. Today that screen is a contact list, the spreadsheet equivalent of a client roster. It becomes the place where the same book carries cadence, coverage, and what's unresolved.
- Paired with the drafting surface from inbound, one screen now covers three things the product couldn't: accounts that are slipping, items still owed, and a reason to reach out before the buyer has said anything.
- Events update as they land. Cadence and coverage rebuild overnight.

#### Slide 27 — "Highest priorities, written out" · *(highlights the read-out)*

- Prose, not a task queue. Each line names an account or a grouping of accounts and the specific reason, built from the book.

#### Slide 28 — "Category screen, split into slipping, outstanding, and opportunity" · *(highlights the filters)*

- allows the AM to come in with a question - what do I need to address? What are some accounts I can get further value from? And see the client list through that lens. Not overcrowded, filterable insight generated on a tool he already engages with.

#### Slide 29 — "Data insights attached to spreadsheet" · *(highlights the table)*

- Added datapoints attached to accounts screen, including `orders.channel` - one of the fix's schema decisions. An account that's a third inquiry-driven is structurally different from one that runs on standing orders, and that difference is invisible today. This allows both the agent and the user to understand how the customer makes inquiries and where there's room to expand.

#### Slide 30 — "Generate messages straight from this screen" · *(highlights The Wren & Larder row)*

- Same drafting surface as inbound. Same review, same buyer record, same Send or Change. An AM reviews drafts thirty times a day already, so this is that action again in a new place rather than a second thing to learn.
- Familiar shape, new trigger. A surface that looks and behaves like one already in use gets picked up; a separate tool with its own conventions competes for attention. This is the same review, adding more value to a surface that is already in use.
- Example: The Wren & Larder: a Welsh cheese asked about in November, never followed up. Nine months old, sitting in plain sight. The Open column reads it straight from the note.
- That row makes the case for the screen better than any number on it. Nobody was negligent. There was just nowhere for it to live.

#### Slide 31 — "How a new account starts"

- Tracked from the first order. Cadence and channel mix build from order history, so a new account joins the book immediately. What it doesn't have is preference history, and neither does the AM.
- Nothing is suggested, because nothing is known. No candidates in the panel, no checkboxes, no inferred preferences. The ranking falls to catalogue level and says so. Absence is shown, not filled in.
- The AM works the account the way they always have. The difference is that this time the pattern gets captured as they go, rather than living in their head until they leave.
- **What success looks like:** contact that originates from the agent rather than from a blank page. A message the AM approves instead of one they compose.

---

## Close

#### Slide 32 — "The 75 days" · *(full-screen)*

| | Ship | Measure |
|---|---|---|
| **Wk 1** | Order history in the review rail. No new data. Add the channel column, start logging substitutions. | How much of each account's ordering runs through the agent, and whether the decline concentrated there. |
| **Wk 2–4** | Ranking on this buyer's acceptance history, with the reason shown. Capture panel. Auto-send below the top tier. | Accept rate. SKU and tone edits separately. Time from opening to sending. |
| **Wk 4–8** | PulseBoard on five charts. Conversion beside unsubscribe. The 84% retired. | Whether any of the three AMs opens a draft again. |
| **Wk 8–11** | Daybook. Three categories, drafting per row. | Coverage of book. Outstanding items closed, and the age of the oldest. |

- Week 1 informs the human. Weeks 2–4 improve the machine. The first needs no new data, which is why 75 days is enough.
- **What she sees at the vote:** where the decline landed · accept rate before and after · how many of the three came back · coverage of book.
