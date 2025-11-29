import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import pool from "./db.js";

let FILE = "./detections.txt"; // default path
let POLL_MS = 10; // default polling interval (ms)
let COOLDOWN_MS = 5 * 60 * 1000; // default 10 minutes server-side cooldown
let lastSize = 0; // byte offset of the last read position
let leftover = ""; // holds a partial line between reads
let reading = false; // prevent overlapping reads
let leftoverTimer = null; // timer to flush leftover if stable
const FLUSH_MS = 300; // flush partial line if no more bytes arrive in this time
let onDetection = null; // optional callback to notify server/app

// server-side map to prevent duplicate inserts: key -> lastInsertEpochMs
// key format: `${lat.toFixed(6)},${lon.toFixed(6)}`
const lastInsertMap = new Map();

async function insertLog(time, latitude, longitude) {
	try {
			const sql = `
				INSERT INTO LogDetections (\`time\`, latitude, longitude)
				VALUES (?, ?, ?)
			`;
		const [result] = await pool.execute(sql, [time, latitude, longitude]);
		console.log(`Inserted ID ${result.insertId}: ${time}, ${latitude}, ${longitude}`);
		if (typeof onDetection === "function") {
			onDetection({ id: result.insertId, time, latitude, longitude });
		}
	} catch (err) {
		console.error("Insert error:", err && err.message ? err.message : err);
	}
}

async function processLine(line) {
	const trimmed = line.trim();
	if (!trimmed) return;

	// Expect: "YYYY-MM-DD HH:MM:SS,lat,lon"
	const parts = trimmed.split(",");
	if (parts.length < 3) {
		console.warn("Skipping malformed line:", trimmed);
		return;
	}
	const time = parts[0].trim();
	const lat = parseFloat(parts[1]);
	const lon = parseFloat(parts[2]);
	if (Number.isNaN(lat) || Number.isNaN(lon)) {
		console.warn("Skipping line with invalid coordinates:", trimmed);
		return;
	}

	// server-side dedupe/cooldown: do not insert if same lat/lon inserted within COOLDOWN_MS
	const key = `${lat.toFixed(6)},${lon.toFixed(6)}`;
	const now = Date.now();
	const last = lastInsertMap.get(key) || 0;
	if (now - last < COOLDOWN_MS) {
		console.log(`Skipping insert for ${key} (within cooldown ${Math.round((COOLDOWN_MS - (now-last))/1000)}s)`);
		return;
	}

	// perform DB insert
	await insertLog(time, lat, lon);
	lastInsertMap.set(key, now);
}

function poll() {
	if (reading) return; // avoid overlap if previous read still finishing
	reading = true;

		fs.stat(FILE, (err, stats) => {
		if (err) {
			reading = false;
			return console.error("stat error:", err);
		}

		// Handle truncation/reset
		if (stats.size < lastSize) {
			lastSize = 0;
			leftover = "";
		}

		if (stats.size === lastSize) {
			reading = false; // no new data
			return;
		}

		const stream = fs.createReadStream(FILE, {
			start: lastSize,
			end: stats.size - 1,
			encoding: "utf8",
		});

		let chunk = "";
		stream.on("data", (c) => (chunk += c));

		stream.on("end", async () => {
			lastSize = stats.size;
			let data = leftover + chunk;
			const lines = data.split(/\r?\n/);

			// If the last chunk does not end with a newline, keep it as leftover
			if (!data.endsWith("\n") && !data.endsWith("\r\n")) {
					leftover = lines.pop();
					// schedule a flush if no new bytes arrive soon
					if (leftoverTimer) clearTimeout(leftoverTimer);
					const snapshot = leftover;
					const sizeAtSchedule = lastSize;
					leftoverTimer = setTimeout(async () => {
						// if nothing changed and leftover still present, treat it as a full line
						if (leftover && leftover === snapshot && lastSize === sizeAtSchedule) {
							try {
								await processLine(leftover);
							} catch (e) {
								console.error("leftover flush error:", e && e.message ? e.message : e);
							}
							leftover = "";
							leftoverTimer = null;
						}
					}, FLUSH_MS);
			} else {
				leftover = "";
					if (leftoverTimer) {
						clearTimeout(leftoverTimer);
						leftoverTimer = null;
					}
			}

			for (const line of lines) {
				try {
					await processLine(line);
				} catch (e) {
					console.error("processLine error:", e && e.message ? e.message : e);
				}
			}

			reading = false;
		});

		stream.on("error", (e) => {
			console.error("read stream error:", e);
			reading = false;
		});
	});
}

/**
 * Start ingest/tail loop
 * options:
 *  - file: path to detections file
 *  - pollMs: polling interval (ms)
 *  - cooldownMs: server-side cooldown (ms)
 *  - onDetection: optional callback when DB insert succeeds
 *
 * returns: function to stop the timer
 */
export function startIngest(options = {}) {
	FILE = options.file || FILE;
	POLL_MS = typeof options.pollMs === 'number' ? options.pollMs : POLL_MS;
	COOLDOWN_MS = typeof options.cooldownMs === 'number' ? options.cooldownMs : COOLDOWN_MS;
	onDetection = options.onDetection || null;

	// Ensure the file exists
	if (!fs.existsSync(FILE)) {
		fs.writeFileSync(FILE, "", { encoding: "utf8" });
	}

	// Start tailing from current end of file (do not process old lines)
	try {
		const stats = fs.statSync(FILE);
		lastSize = stats.size;
	} catch (e) {
		lastSize = 0;
	}

	const timer = setInterval(poll, POLL_MS);
	console.log(`Watching ${FILE} for new lines (every ${POLL_MS}ms)... (server cooldown ${COOLDOWN_MS}ms)`);
	return () => clearInterval(timer);
}

// If run directly, start ingestion with defaults (robust cross-platform check)
const isDirectRun = (() => {
	try {
		const thisFile = fileURLToPath(import.meta.url);
		const invoked = path.resolve(process.argv[1] || "");
		return path.resolve(thisFile) === invoked;
	} catch {
		return false;
	}
})();

if (isDirectRun) {
	startIngest();
}
