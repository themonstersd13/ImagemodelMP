# Detections Ingest

This project continuously tails `detections.txt` and writes each new line into the MySQL table `LogDetections` immediately.

## How it works

- `insertLog.js` watches `detections.txt` by polling its size and reading any new bytes.
- Each full line is expected to be in the format:
  - `YYYY-MM-DD HH:MM:SS,lat,lon`
- Lines are parsed and inserted into the database via `db.js`.
- Partial lines are buffered and flushed after a short idle period so "instant" updates still occur when the writer doesn't append a newline.

## Setup

1. Create a `.env` file with your DB credentials or a connection URL. Any of the following are supported:

   - `DATABASE_URL` (full connection string)
   - or individual params:
     - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`

2. Ensure the destination table exists:

```sql
CREATE TABLE IF NOT EXISTS `LogDetections` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `time` DATETIME NOT NULL,
  `latitude` DOUBLE NOT NULL,
  `longitude` DOUBLE NOT NULL
);
```

## Run

From the project root (where `detections.txt` lives):

```cmd
npm install
npm start
```

The ingestor will log inserted IDs and any malformed lines it skips.

## Notes

- Default file: `./detections.txt` (created if missing)
- Default poll interval: 100ms (configurable via `startIngest({ pollMs })` if you import it)
- It starts tailing from the current end of file, so historical lines are not re-inserted.
