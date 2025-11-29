import 'dotenv/config';
import mysql from "mysql2/promise"; // using promise version for async/await

// Replace these with your Railway credentials
function createPoolFromEnv() {
  const url = process.env.DATABASE_URL || process.env.MYSQL_URL || process.env.MYSQL_DATABASE_URL;
  if (url) {
    console.log(`[db] Using DATABASE_URL style connection`);
    return mysql.createPool(url);
  }

  const host = process.env.DB_HOST || "localhost";
  const user = process.env.DB_USER || "root";
  const password = process.env.DB_PASSWORD || "";
  const database = process.env.DB_NAME || "railway";
  const port = Number(process.env.DB_PORT || 3306);

  if (!process.env.DB_HOST || !process.env.DB_USER || !process.env.DB_NAME) {
    console.warn(`[db] Missing DB env vars. Falling back to defaults (host=${host}, user=${user}, db=${database}, port=${port}). Create a .env file to override.`);
  }

  console.log(`[db] Connecting`, { host, user, database, port });
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

export default pool;
