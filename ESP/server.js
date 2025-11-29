// server.js (CommonJS)
const express = require('express');
const pool = require('./db.cjs'); // uses the pool created above
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

let manualAlarm = false;

// Helper: get latest detection if within maxAgeMs
async function getLatestDetectionIfRecent(maxAgeMs = 10 * 60 * 1000) {
  try {
    const [rows] = await pool.execute(
      "SELECT id, `time`, latitude, longitude FROM LogDetections ORDER BY id DESC LIMIT 1"
    );
    if (!rows || rows.length === 0) return null;
    const row = rows[0];
    // mysql2 returns JS Date objects for DATETIME columns by default
    const dbTime = row.time instanceof Date ? row.time : new Date(row.time);
    if (isNaN(dbTime.getTime())) return null;
    const ageMs = Date.now() - dbTime.getTime();
    if (ageMs <= maxAgeMs) {
      return {
        id: row.id,
        time: dbTime.toISOString(),
        latitude: Number(row.latitude),
        longitude: Number(row.longitude),
        age_seconds: Math.round(ageMs / 1000)
      };
    }
    return null;
  } catch (err) {
    console.error("[db] error in getLatestDetectionIfRecent:", err);
    throw err;
  }
}

app.post('/check-alarm', async (req, res) => {
  try {
    // optional: inspect request
    if (req.body && Object.keys(req.body).length) {
      console.log('📡 ESP32 Request received:', req.body);
    } else {
      console.log('📡 ESP32 Request received (no body)');
    }

    // manual override: if you set manualAlarm true via /set-alarm, you can immediately respond alarm: true
    if (manualAlarm) {
      return res.json({
        success: true,
        alarm: true,
        alert_count: 1,
        message: 'manual alarm override',
        timestamp: new Date().toISOString()
      });
    }

    const detection = await getLatestDetectionIfRecent(10 * 60 * 1000);
    if (detection) {
      return res.json({
        success: true,
        alarm: true,
        alert_count: 1,
        detection,
        message: 'recent detection found',
        timestamp: new Date().toISOString()
      });
    } else {
      return res.json({
        success: true,
        alarm: false,
        alert_count: 0,
        message: 'no recent detection (older than 10 minutes or no rows)',
        timestamp: new Date().toISOString()
      });
    }
  } catch (err) {
    console.error('ERROR /check-alarm:', err);
    return res.status(500).json({ success: false, error: 'internal_server_error' });
  }
});

app.get('/set-alarm', (req, res) => {
  const { status } = req.query;
  if (status === 'true') {
    manualAlarm = true;
    console.log('🚨 Manual Alarm activated');
  } else if (status === 'false') {
    manualAlarm = false;
    console.log('✅ Manual Alarm deactivated');
  } else {
    manualAlarm = !manualAlarm;
    console.log(`🔄 Manual Alarm toggled to: ${manualAlarm}`);
  }
  res.send(`
    <h1>Alarm Control</h1>
    <p>Current manual status: <strong>${manualAlarm ? 'ACTIVE 🚨' : 'INACTIVE ✅'}</strong></p>
    <a href="/set-alarm?status=true"><button>Activate Alarm</button></a>
    <a href="/set-alarm?status=false"><button>Deactivate Alarm</button></a>
    <a href="/set-alarm"><button>Toggle Alarm</button></a>
    <br><br>
    <a href="/status"><button>Check Status</button></a>
  `);
});

app.get('/status', (req, res) => {
  res.json({
    manualAlarm,
    server: 'running',
    timestamp: new Date().toISOString()
  });
});

app.get('/', (req, res) => res.redirect('/set-alarm'));

app.listen(port, '0.0.0.0', () => {
  console.log(`🚀 Server running on http://localhost:${port}`);
});
