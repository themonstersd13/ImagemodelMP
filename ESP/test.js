const express = require('express');
const app = express();
const port = 3000;

// Simple middleware
app.use(express.json());

let alarmStatus = false;

// Simple POST endpoint for ESP32
app.post('/check-alarm', (req, res) => {
    console.log('📡 ESP32 Request received:', req.body);
    
    res.json({
        success: true,
        alarm: alarmStatus,
        alert_count: alarmStatus ? 1 : 0,
        message: 'Server is working!',
        timestamp: new Date().toISOString()
    });
});

// Simple GET endpoint to control alarm
app.get('/set-alarm', (req, res) => {
    const { status } = req.query;
    
    if (status === 'true') {
        alarmStatus = true;
        console.log('🚨 Alarm activated');
    } else if (status === 'false') {
        alarmStatus = false;
        console.log('✅ Alarm deactivated');
    } else {
        alarmStatus = !alarmStatus;
        console.log(`🔄 Alarm toggled to: ${alarmStatus}`);
    }
    
    res.send(`
        <h1>Alarm Control</h1>
        <p>Current status: <strong>${alarmStatus ? 'ACTIVE 🚨' : 'INACTIVE ✅'}</strong></p>
        <a href="/set-alarm?status=true"><button>Activate Alarm</button></a>
        <a href="/set-alarm?status=false"><button>Deactivate Alarm</button></a>
        <a href="/set-alarm"><button>Toggle Alarm</button></a>
        <br><br>
        <a href="/status"><button>Check Status</button></a>
    `);
});

// Status endpoint
app.get('/status', (req, res) => {
    res.json({
        alarm: alarmStatus,
        server: 'running',
        timestamp: new Date().toISOString()
    });
});

// Root redirect
app.get('/', (req, res) => {
    res.redirect('/set-alarm');
});

// Start server
app.listen(port, '0.0.0.0', () => {
    console.log(`🚀 Simple Server running on:`);
    console.log(`   http://localhost:${port}`);
    console.log(`   http://10.39.22.163:${port}`);
    console.log(`\n📡 Test in browser first, then use ESP32!`);
});

console.log('✅ Server code loaded - waiting for connections...');