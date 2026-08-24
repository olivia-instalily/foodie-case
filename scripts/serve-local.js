// Local preview that mirrors Vercel routing WITHOUT needing `vercel dev`
// or a linked project. Serves index.html at / and runs the same api/*.js
// handlers under /api/*. Run: node scripts/serve-local.js  (then open :3000)
const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const PORT = process.env.PORT || 3000;

// Load .env (KEY=VALUE lines) so /api/generate gets ANTHROPIC_API_KEY under plain
// `node` too, not only `vercel dev`. Existing env vars win; quotes are stripped.
try {
  const envPath = path.join(ROOT, ".env");
  if (fs.existsSync(envPath)) {
    for (const line of fs.readFileSync(envPath, "utf8").split("\n")) {
      const m = line.match(/^\s*([A-Za-z0-9_]+)\s*=\s*(.*)\s*$/);
      if (!m || process.env[m[1]] !== undefined) continue;
      let v = m[2].trim();
      if ((v[0] === '"' && v.endsWith('"')) || (v[0] === "'" && v.endsWith("'"))) v = v.slice(1, -1);
      process.env[m[1]] = v;
    }
  }
} catch (_) {}

const server = http.createServer((req, res) => {
  const url = req.url.split("?")[0];

  // API routes -> api/<name>.js
  if (url.startsWith("/api/")) {
    const name = url.slice("/api/".length).replace(/\/$/, "");
    const file = path.join(ROOT, "api", name + ".js");
    if (fs.existsSync(file)) {
      try {
        const handler = require(file);
        // minimal res.status().json() / setHeader shim
        res.status = (c) => { res.statusCode = c; return res; };
        res.json = (o) => {
          res.setHeader("content-type", "application/json");
          res.end(JSON.stringify(o));
        };
        return handler(req, res);
      } catch (err) {
        res.statusCode = 500;
        return res.end(JSON.stringify({ error: String(err.stack || err) }));
      }
    }
    res.statusCode = 404;
    return res.end("no such function: " + name);
  }

  // static: / -> index.html, otherwise the file if it exists
  const rel = url === "/" ? "index.html" : url.replace(/^\/+/, "");
  const file = path.join(ROOT, rel);
  if (fs.existsSync(file) && fs.statSync(file).isFile()) {
    const ext = path.extname(file);
    const type =
      ext === ".html" ? "text/html" :
      ext === ".js" ? "text/javascript" :
      ext === ".css" ? "text/css" : "application/octet-stream";
    res.setHeader("content-type", type);
    res.setHeader("cache-control", "no-store, no-cache, must-revalidate");  // always serve fresh edits
    return res.end(fs.readFileSync(file));
  }
  res.statusCode = 404;
  res.end("not found: " + rel);
});

server.listen(PORT, () => {
  console.log(`Foodie AM Workspace → http://localhost:${PORT}`);
  console.log(`(local preview; on Vercel the same api/data.js runs as a function)`);
});
