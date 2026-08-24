// POST /api/generate
// Rewrites an inbound reply using the buyer context the AM checked off in the
// capture panel. This is the "loop it back in" step made real: the checked
// facts are sent to Claude, which regenerates the draft in the AM's voice.
//
// The API key is read from the ANTHROPIC_API_KEY environment variable — never
// from the client. Set it locally in .env (for `vercel dev`) or in the Vercel
// project settings for production. See .env.example.
const Anthropic = require("@anthropic-ai/sdk");

const MODEL = "claude-opus-4-8";

const SYSTEM_REPLY = `You are helping a Foodie & Co. account manager reply to a restaurant buyer's inbound message.
Rewrite the reply so it reflects the context the account manager selected about this buyer.

Rules:
- Output ONLY the email body. No subject line, no "Subject:", no preamble such as "Here is" or "Sure".
- Use only the buyer's message and the selected context. Never invent prices, stock levels, lot numbers, dates, or any fact not given to you.
- Respect the buyer's stated preferences and past refusals in the context. If they refused something, do not offer it again.
- Match the tone, greeting, and sign-off style of the reference draft: if it has no greeting or sign-off and uses a first name, do the same; if it is formal, stay formal.
- Weave the relevant context in naturally and specifically, do not list it or quote it verbatim.
- Do not use em-dashes anywhere; use commas or periods instead.
- Keep it concise.`;

const SYSTEM_NOTE = `You are helping a Foodie & Co. account manager write a short, PROACTIVE outreach note to a restaurant buyer. This is not a reply — the buyer has not written in. The account manager is reaching out because the account is on their radar.

Rules:
- Output ONLY the email body. No subject line, no "Subject:", no preamble such as "Here is" or "Sure".
- Use only the selected context about this buyer. Never invent prices, stock levels, lot numbers, dates, or any fact not given to you.
- Weave the context in naturally and specifically, do not list it or quote it verbatim.
- If the context includes a personal life event (a retirement, a child starting college, a wedding, a new arrival, a new location), acknowledge it warmly and by name where a name is given.
- If it includes an unresolved/open item, own it and say it's being handled.
- Warm, personal, concise. Match the greeting and sign-off of the reference draft (first-name greeting; sign off as Olivia Joergens, Foodie & Co.).
- Do not use em-dashes anywhere; use commas or periods instead.`;

function readBody(req) {
  if (req.body && typeof req.body === "object") return Promise.resolve(req.body);
  return new Promise((resolve) => {
    let data = "";
    req.on("data", (c) => (data += c));
    req.on("end", () => {
      try { resolve(JSON.parse(data || "{}")); } catch { resolve({}); }
    });
  });
}

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    res.setHeader("allow", "POST");
    return res.status(405).json({ error: "Use POST." });
  }
  if (!process.env.ANTHROPIC_API_KEY) {
    return res.status(500).json({
      error:
        "ANTHROPIC_API_KEY is not set. Add it to .env (local) or Vercel project settings, then restart `vercel dev`.",
    });
  }

  try {
    const body = await readBody(req);
    const { account, contact, buyerMessage, referenceDraft, context, kind, thread } = body;
    // reply mode needs the buyer's message; note mode (proactive outreach) does not
    const isNote = kind === "note" || !buyerMessage;
    if (!isNote && !buyerMessage) return res.status(400).json({ error: "buyerMessage is required." });

    const picked = Array.isArray(context) ? context.filter((c) => c && c.statement) : [];
    const contextBlock = picked.length
      ? picked.map((c) => `- ${c.statement}${c.source ? ` (source: ${c.source})` : ""}`).join("\n")
      : "(none selected)";

    // the recent thread (calls/emails/notes) so the model matches tone and doesn't contradict it
    const threadText = typeof thread === "string" ? thread.trim()
      : Array.isArray(thread) ? thread.map((t) => (typeof t === "string" ? t : `[${t.date || ""} ${t.kind || ""}] ${t.body || ""}`)).join("\n") : "";
    const threadBlock = threadText
      ? `Recent thread with this buyer (read it for their tone and current situation; do not contradict anything in it):\n${threadText}\n\n`
      : "";

    const userContent = isNote
      ? `Buyer: ${contact || "the buyer"}${account ? ` at ${account}` : ""}\n\n` +
        threadBlock +
        (referenceDraft ? `Reference for voice and format:\n${referenceDraft}\n\n` : "") +
        `Context the account manager selected to reflect:\n${contextBlock}\n\n` +
        `Write the proactive outreach note.`
      : `Buyer: ${contact || "the buyer"}${account ? ` at ${account}` : ""}\n\n` +
        `Their message:\n"${buyerMessage}"\n\n` +
        threadBlock +
        (referenceDraft ? `Reference draft, match this voice and format:\n${referenceDraft}\n\n` : "") +
        `Context the account manager selected to reflect:\n${contextBlock}\n\n` +
        `Rewrite the reply.`;

    const client = new Anthropic(); // reads ANTHROPIC_API_KEY from env

    const response = await client.messages.create({
      model: MODEL,
      max_tokens: 1024,
      thinking: { type: "adaptive" },       // let Claude decide how much to reason
      output_config: { effort: "low" },     // short, simple task, keep it fast
      system: isNote ? SYSTEM_NOTE : SYSTEM_REPLY,
      messages: [{ role: "user", content: userContent }],
    });

    if (response.stop_reason === "refusal") {
      return res.status(422).json({ error: "The model declined to rewrite this draft." });
    }
    const textBlock = response.content.find((b) => b.type === "text");
    let draft = textBlock ? textBlock.text.trim() : "";
    draft = draft.replace(/[ \t]*—[ \t]*/g, ", "); // house rule: no em-dashes anywhere
    if (!draft) return res.status(502).json({ error: "Empty draft returned." });

    res.setHeader("content-type", "application/json");
    res.status(200).json({ draft, model: response.model, usedContext: picked.length });
  } catch (err) {
    // surface auth/rate-limit errors clearly for the demo
    const status = (err && err.status) || 500;
    res.status(status >= 400 && status < 600 ? status : 500).json({
      error: String((err && err.message) || err),
    });
  }
};
