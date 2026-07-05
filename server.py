# server.py - Full License Server with Device Limit

from flask import Flask, request, jsonify
import hashlib
import json
import time
from datetime import datetime, timedelta
import sqlite3
import secrets
import string
import os

app = Flask(__name__)

ADMIN_SECRET_KEY = "CyberVerse_Arcade_TopSecret_GameCenter_2026!@#"
MAX_DEVICES_PER_KEY = 1  # စက်တစ်လုံးပဲ သုံးလို့ရ

# ========================================================================
# 1️⃣ Database Setup
# ========================================================================
def init_db():
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    
    # Drop old table if exists (to fix schema)
    c.execute("DROP TABLE IF EXISTS licenses")
    c.execute("DROP TABLE IF EXISTS activations")
    
    # Create new licenses table with device_count and max_devices
    c.execute('''
        CREATE TABLE licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hwid TEXT,
            license_key TEXT UNIQUE,
            activated_at TIMESTAMP,
            expiry TIMESTAMP,
            status TEXT DEFAULT 'active',
            device_count INTEGER DEFAULT 0,
            max_devices INTEGER DEFAULT 1
        )
    ''')
    
    c.execute('''
        CREATE TABLE activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT,
            hwid TEXT,
            ip TEXT,
            activated_at TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database created with device_count and max_devices columns!")

# ========================================================================
# 2️⃣ Verify License
# ========================================================================
@app.route('/api/verify', methods=['POST'])
def verify_license():
    try:
        data = request.json
        hwid = data.get('hwid')
        license_key = data.get('license_key')
        
        if not hwid or not license_key:
            return jsonify({'valid': False, 'error': 'Missing data'})
        
        conn = sqlite3.connect('licenses.db')
        c = conn.cursor()
        
        c.execute('''
            SELECT expiry, status, device_count, max_devices, hwid 
            FROM licenses 
            WHERE license_key = ? AND status = 'active'
        ''', (license_key,))
        
        result = c.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'valid': False, 'error': 'License not found'})
        
        expiry, status, device_count, max_devices, stored_hwid = result
        
        if datetime.now() > datetime.fromisoformat(expiry):
            conn.close()
            return jsonify({'valid': False, 'error': 'License expired'})
        
        # Device Limit Check
        if stored_hwid and stored_hwid != hwid:
            if device_count >= max_devices:
                conn.close()
                return jsonify({
                    'valid': False, 
                    'error': f'Device limit reached! (Used on {device_count}/{max_devices} devices)'
                })
        
        conn.close()
        return jsonify({
            'valid': True,
            'expiry': expiry,
            'features': ['premium', 'all_games'],
            'device_count': device_count,
            'max_devices': max_devices
        })
        
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

# ========================================================================
# 3️⃣ Activate License
# ========================================================================
@app.route('/api/activate', methods=['POST'])
def activate_license():
    try:
        data = request.json
        hwid = data.get('hwid')
        license_key = data.get('license_key')
        
        if not hwid or not license_key:
            return jsonify({'success': False, 'error': 'Missing data'})
        
        conn = sqlite3.connect('licenses.db')
        c = conn.cursor()
        
        c.execute('''
            SELECT expiry, hwid, device_count, max_devices, status 
            FROM licenses 
            WHERE license_key = ?
        ''', (license_key,))
        
        result = c.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid license key'})
        
        expiry, stored_hwid, device_count, max_devices, status = result
        
        if status != 'active':
            conn.close()
            return jsonify({'success': False, 'error': 'License is not active'})
        
        # Device Limit Check
        if stored_hwid and stored_hwid != hwid:
            if device_count >= max_devices:
                conn.close()
                return jsonify({
                    'success': False, 
                    'error': f'Device limit reached! (Used on {device_count}/{max_devices} devices)'
                })
        
        if not stored_hwid:
            # First activation
            c.execute('''
                UPDATE licenses 
                SET hwid = ?, activated_at = ?, device_count = 1 
                WHERE license_key = ?
            ''', (hwid, datetime.now(), license_key))
        elif stored_hwid == hwid:
            # Same device - allow
            pass
        else:
            # New device
            c.execute('''
                UPDATE licenses 
                SET hwid = ?, device_count = device_count + 1 
                WHERE license_key = ?
            ''', (hwid, license_key))
        
        c.execute('''
            INSERT INTO activations (license_key, hwid, ip, activated_at)
            VALUES (?, ?, ?, ?)
        ''', (license_key, hwid, request.remote_addr, datetime.now()))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'expiry': expiry,
            'features': ['premium', 'all_games']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ========================================================================
# 4️⃣ Generate License Key (Admin)
# ========================================================================
@app.route('/api/generate', methods=['POST'])
def generate_license():
    try:
        admin_key = request.json.get('admin_key')
        
        if admin_key != ADMIN_SECRET_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 4-char parts license key
        license_key = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
        license_key = '-'.join([license_key[i:i+4] for i in range(0, 16, 4)])
        
        conn = sqlite3.connect('licenses.db')
        c = conn.cursor()
        
        expiry = (datetime.now() + timedelta(days=365*10)).isoformat()
        
        c.execute('''
            INSERT INTO licenses (license_key, expiry, status, max_devices)
            VALUES (?, ?, ?, ?)
        ''', (license_key, expiry, 'active', MAX_DEVICES_PER_KEY))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'license_key': license_key,
            'expiry': expiry,
            'max_devices': MAX_DEVICES_PER_KEY
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================================================================
# 5️⃣ Test Endpoint
# ========================================================================
@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({
        'status': 'Server is running!',
        'time': datetime.now().isoformat(),
        'max_devices': MAX_DEVICES_PER_KEY
    })

# ========================================================================
# 6️⃣ Check License Status (Admin)
# ========================================================================
@app.route('/api/status', methods=['POST'])
def license_status():
    try:
        admin_key = request.json.get('admin_key')
        license_key = request.json.get('license_key')
        
        if admin_key != ADMIN_SECRET_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        
        conn = sqlite3.connect('licenses.db')
        c = conn.cursor()
        
        c.execute('''
            SELECT license_key, hwid, device_count, max_devices, activated_at, expiry, status
            FROM licenses 
            WHERE license_key = ?
        ''', (license_key,))
        
        result = c.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'error': 'License not found'}), 404
        
        key, hwid, device_count, max_devices, activated_at, expiry, status = result
        
        return jsonify({
            'license_key': key,
            'hwid': hwid if hwid else 'Not activated yet',
            'device_count': device_count,
            'max_devices': max_devices,
            'activated_at': activated_at if activated_at else 'Not activated yet',
            'expiry': expiry,
            'status': status
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("🚀 License Server Started!")
    print(f"🔑 Admin Key: {ADMIN_SECRET_KEY}")
    print(f"📱 Max Devices: {MAX_DEVICES_PER_KEY}")
    print(f"🌐 Server URL: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)