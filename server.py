# server.py
from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# --- CẤU HÌNH ---
DATABASE_URL = os.environ.get('POSTGRES_URL')
app = Flask(__name__)

if not DATABASE_URL:
    raise RuntimeError("🔴 LỖI: POSTGRES_URL phải được thiết lập trong môi trường.")

def get_db_connection():
    """Thiết lập kết nối đến cơ sở dữ liệu PostgreSQL."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_database():
    """Khởi tạo bảng licenses với cấu trúc mới."""
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

# --- ENDPOINT CỦA API ---
@app.route('/validate', methods=['POST'])
def validate_license():
    data = request.get_json()
    if not data or 'key' not in data or 'hwid' not in data:
        return jsonify({'status': 'error', 'message': 'Thiếu key hoặc hwid.'}), 400

    license_key = data['key']
    hwid = data['hwid']

    conn = get_db_connection()
    # Dùng DictCursor để dễ dàng truy cập cột bằng tên
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute("SELECT * FROM licenses WHERE license_key = %s", (license_key,))
    key_data = cursor.fetchone()

    # TRƯỜNG HỢP 1: KEY KHÔNG TỒN TẠI
    if not key_data:
        cursor.close(), conn.close()
        return jsonify({'status': 'error', 'message': 'License key không tồn tại.'}), 404

    # TRƯỜNG HỢP 2: KÍCH HOẠT LẦN ĐẦU
    if not key_data['is_activated']:
        print(f"Kích hoạt key lần đầu: {license_key} cho HWID: {hwid}")
        activation_date = datetime.now()
        end_date = activation_date + timedelta(days=key_data['duration_days'])
        
        cursor.execute("""
            UPDATE licenses 
            SET is_activated = TRUE, hwid = %s, activation_date = %s, end_date = %s
            WHERE license_key = %s
        """, (hwid, activation_date.isoformat(), end_date.isoformat(), license_key))
        
        conn.commit()
        cursor.close(), conn.close()
        return jsonify({
            'status': 'success', 
            'message': 'Kích hoạt license thành công!',
            'expires_on': end_date.isoformat()
        }), 200

    # TRƯỜNG HỢP 3: XÁC THỰC KEY ĐÃ KÍCH HOẠT
    if key_data['hwid'] != hwid:
        cursor.close(), conn.close()
        return jsonify({'status': 'error', 'message': 'HWID không khớp. Key đã được dùng trên máy khác.'}), 403

    end_date = datetime.fromisoformat(key_data['end_date'])
    if datetime.now() > end_date:
        cursor.close(), conn.close()
        return jsonify({'status': 'error', 'message': 'License đã hết hạn.'}), 403

    # Mọi thứ hợp lệ
    cursor.close(), conn.close()
    return jsonify({
        'status': 'success', 
        'message': 'License hợp lệ.',
        'expires_on': key_data['end_date']
    }), 200
