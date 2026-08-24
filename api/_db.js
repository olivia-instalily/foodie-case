// Shared read-only connection to foodie.db.
// On Vercel the DB is bundled with the function via `includeFiles` in
// vercel.json; we probe a few candidate paths so the same code works in
// `vercel dev`, local `node`, and the deployed Lambda.
const Database = require("better-sqlite3");
const fs = require("fs");
const path = require("path");

let _db = null;

function resolveDbPath() {
  const candidates = [
    path.join(process.cwd(), "foodie.db"),
    path.join(__dirname, "..", "foodie.db"),
    path.join(__dirname, "foodie.db"),
    "/var/task/foodie.db",
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  throw new Error(
    "foodie.db not found. Looked in:\n" + candidates.join("\n")
  );
}

function db() {
  if (!_db) {
    _db = new Database(resolveDbPath(), { readonly: true, fileMustExist: true });
    _db.pragma("journal_mode = OFF");
  }
  return _db;
}

module.exports = { db };
