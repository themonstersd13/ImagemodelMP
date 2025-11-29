// db.cjs — CommonJS database pool wrapper
require('dotenv').config();
const mysql = require('mysql2/promise');

function createPoolFromEnv() {
  const url = process.env.DATABASE_URL || process.env.MYSQL_URL || process.env.MYSQL_DATABASE_URL;
  if (url) {
    console.log("[db] Using DATABASE_URL style connection");
    return mysql.createPool(url);
  }

  const host = process.env.DB_HOST || "trolley.proxy.rlwy.net";
  const user = process.env.DB_USER || "root";
  const password = process.env.DB_PASSWORD || "";
  const database = process.env.DB_NAME || "railway";
  const port = Number(process.env.DB_PORT || 51500);

  console.log("[db] Connecting", { host, user, database, port });
  return mysql.createPool({
    host,
    user,
    password,
    database,
    port,
    waitForConnections: true,
    connectionLimit: 10,
  });
}

const pool = createPoolFromEnv();
module.exports = pool;
