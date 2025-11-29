// checkLastDetections.js
import pool from "./db.js";

async function main() {
  try {
    const [rows] = await pool.execute("SELECT * FROM LogDetections ORDER BY id DESC LIMIT 10");
    console.table(rows);
  } catch (err) {
    console.error("DB query error:", err);
  } finally {
    process.exit(0);
  }
}

main();
