from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('POSTGRES_URL')
app = Flask(__name__)

if not DATABASE_URL:
    raise RuntimeError("🔴 LỖI: POSTGRES_URL phải được thiết lập trong môi trường.")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_database():
    print("Đang kiểm tra bảng 'licenses' với cấu trúc mới...")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            license_key TEXT PRIMARY KEY,
            duration_days INTEGER NOT NULL,
            is_activated BOOLEAN DEFAULT FALSE,
            hwid TEXT,
            activation_date TEXT,
            end_date TEXT
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Bảng 'licenses' đã sẵn sàng.")

@app.route('/validate', methods=['POST'])
def validate_license():
    data = request.get_json()
    if not data or 'key' not in data or 'hwid' not in data:
        return jsonify({'status': 'error', 'message': 'Thiếu key hoặc hwid.'}), 400

    license_key = data['key']
    hwid = data['hwid']

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute("SELECT * FROM licenses WHERE license_key = %s", (license_key,))
    key_data = cursor.fetchone()

    if not key_data:
        cursor.close(), conn.close()
        return jsonify({'status': 'error', 'message': 'License key không tồn tại.'}), 404

    if not key_data['is_activated']:
        print(f"Kích hoạt key lần đầu: {license_key} cho HWID: {hwid}")
        
        activation_date = datetime.now()
        end_date = None
        
        if key_data['duration_days'] > 0:
            end_date = activation_date + timedelta(days=key_data['duration_days'])
            end_date = end_date.isoformat()
            
        cursor.execute("""
            UPDATE licenses 
            SET is_activated = TRUE, hwid = %s, activation_date = %s, end_date = %s
            WHERE license_key = %s
        """, (hwid, activation_date.isoformat(), end_date, license_key))
        
        conn.commit()
        cursor.close(), conn.close()
        return jsonify({
            'status': 'success', 
            'message': 'Kích hoạt license thành công!',
            'expires_on': end_date
        }), 200

    if key_data['hwid'] != hwid:
        cursor.close(), conn.close()
        return jsonify({'status': 'error', 'message': 'HWID không khớp. Key đã được dùng trên máy khác.'}), 403

    if key_data['end_date'] is not None:
        end_date_obj = datetime.fromisoformat(key_data['end_date'])
        if datetime.now() > end_date_obj:
            cursor.close(), conn.close()
            return jsonify({'status': 'error', 'message': 'License đã hết hạn.'}), 403

    cursor.close(), conn.close()
    return jsonify({
        'status': 'success', 
        'message': 'License hợp lệ.',
        'expires_on': key_data['end_date']
    }), 200

init_database()