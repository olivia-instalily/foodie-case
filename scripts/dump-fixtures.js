// scripts/dump-fixtures.js
// Static fallback for the submission. Runs the real /api/data handler once
// against foodie.db and writes the exact payload to fixtures.json. The app
// fetches /api/data live; if that fails (e.g. SQLite misbehaves on the host),
// it falls back to this file. The queries are still real — they ran at build
// rather than on request. Re-run after any generate.py change:
//   node scripts/dump-fixtures.js
const fs = require("fs");
const path = require("path");
const handler = require("../api/data.js");

const out = path.join(__dirname, "..", "fixtures.json");
const res = {
  setHeader() {},
  status() { return this; },
  json(o) {
    if (o && o.error) { console.error("handler error:", o.error); process.exit(1); }
    const json = JSON.stringify(o);
    fs.writeFileSync(out, json);
    console.log(`wrote ${out}  (${(json.length / 1024).toFixed(1)} KB)`);
  },
};
handler({}, res);
