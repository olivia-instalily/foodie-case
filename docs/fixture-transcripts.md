# fixture-transcripts.md

Source documents for the fix build. These are the raw records that already sit
on Foodie's servers today — call transcripts and AM notes. In BOTH the current
and fixed states these rows exist (they are seeded into `source_documents`
either way). The difference between the two states is only whether anything was
ever *read* out of them into `buyer_facts`.

That is the whole argument: the 12 March call was on file, and the inbound agent
proposed the Cavalieri anyway.

Locators (`mm:ss` for calls, paragraph index for notes) are stored on each
derived fact so the capture panel can quote the exact source sentence verbatim.

---

## DOC 1 — call_transcript · Vinoteca Ardito (account 10428) · Marco Ardito

- **doc_id:** 9001
- **kind:** call_transcript
- **occurred_at:** 2026-03-12 10:24
- **author:** Marco Ardito (buyer)
- **am_id:** covering AM for 10428
- **title:** Substitution follow-up — paccheri

```
00:58  AM     I wanted to close the loop on the paccheri swap from last week.
01:20  MARCO  Yeah. Don't send that one again.
01:42  MARCO  The bite's wrong for us. Anything that soft, same problem — it
              goes to mush in the pan by service. Texture, not the brand.
01:58  MARCO  I pulled the dish for two nights over it. I'm not doing that again.
02:20  AM     Understood. If the Rustichella is out, what do you want us to reach
              for?
02:31  MARCO  The Gragnano. The IGP one. That's held up every time you've sent it.
              Make that the fallback and I don't need to be asked.
03:05  MARCO  And honestly — I'd rather have an empty slot than the wrong thing.
              If the right one isn't there, leave it off and tell me.
03:40  MARCO  The paccheri itself is a fixed line for us. Six cases, every week,
              it's on the menu. That's not changing.
04:12  MARCO  We're short-staffed until spring, so I can't be chasing corrections
              on the order. It has to be right the first time.
04:30  AM     Got it. I'll note all of that.
```

Derived facts (fixed state):
- **"Won't take a softer bite. Texture, not brand."** — excerpt `the bite's wrong for us. Anything that soft, same problem` @ `01:42`. Excludes soft-texture SKUs in the same category.
- **"Gragnano IGP is the agreed fallback for paccheri."** — excerpt `The Gragnano. The IGP one … Make that the fallback` @ `02:31`.
- **"Prefers a gap to a wrong substitute."** — excerpt `I'd rather have an empty slot than the wrong thing` @ `03:05`.
- **"Paccheri is a fixed menu item, 6 cases weekly."** — excerpt `Six cases, every week, it's on the menu` @ `03:40` (corroborated by 11 weeks of order history).
- **"Short-staffed until spring."** — excerpt `We're short-staffed until spring` @ `04:12`. Display-only; no automated effect.

---

## DOC 2 — call_transcript · Osteria Nina (account 10310) · Gio Fallaci

- **doc_id:** 9002
- **kind:** call_transcript
- **occurred_at:** 2026-03-04 15:07
- **author:** Gio Fallaci (buyer)
- **am_id:** covering AM for 10310
- **title:** Spring menu planning

```
01:40  GIO    We're reworking the spring menu, so ordering will move around a bit.
02:14  GIO    The new chef starts in April, so hold off on locking anything in
              until we've had a chance to sit down with them.
02:21  GIO    — sorry, that's for the Brooklyn location, not this account. Here
              it's the same kitchen, same chef. Ignore that.
02:48  GIO    For this room, keep the pistachios coming as normal.
```

Derived facts (fixed state):
- Three sound candidates from order history and the "pistachios as normal" line.
- **The trap:** an extraction of **"New chef starting in April."** — excerpt `the new chef starts in April` @ `02:14`. Verbatim and unambiguous *in isolation*, but the very next line reassigns it to a different location. Confidence `0.45`, not pre-checked. The AM reads it, sees the correction seven seconds later, and leaves the box empty. One unchecked box is the entire cost of the wrong candidate.

---

## DOC 3 — am_note · Café Duvel (account 10248) · Luc Maes

- **doc_id:** 9003
- **kind:** am_note
- **occurred_at:** 2025-06-30
- **author:** covering AM
- **am_id:** covering AM for 10248
- **title:** Sourcing note

```
Luc mentioned he's traveling in Spain through the summer and wants to trial a
couple of Spanish pantry items when he's back — jamón, a smoked paprika line.
Revisit in the fall.
```

Derived fact (fixed state):
- **"Interested in Spanish pantry items (trial)."** — excerpt `wants to trial a couple of Spanish pantry items` @ paragraph 1. **Its newest evidence is over twelve months old**, so retirement is automatic: the fact expires and its bias rows are deleted. This is the note that must NOT surface in August. It exists only to demonstrate expiry.
