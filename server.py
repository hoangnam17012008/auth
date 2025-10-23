# server.py
from flask import Flask, request, jsonify
import psycopg2
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

# Tải các biến môi trường để phát triển local (Vercel sẽ tự động xử lý)
load_dotenv()

# --- CẤU HÌNH ---
DATABASE_URL = os.environ.get('POSTGRES_URL')
SECRET_KEY_STR = os.environ.get('SECRET_KEY')

# --- KHỞI TẠO ---
app = Flask(__name__)

# Kiểm tra xem các biến môi trường đã được thiết lập chưa
if not DATABASE_URL or not SECRET_KEY_STR:
    raise RuntimeError("🔴 LỖI NGHIÊM TRỌNG: POSTGRES_URL và SECRET_KEY phải được thiết lập trong môi trường.")

try:
    SECRET_KEY = SECRET_KEY_STR.encode('utf-8')
    fernet = Fernet(SECRET_KEY)
except Exception as e:
    raise RuntimeError(f"🔴 LỖI NGHIÊM TRỌNG: SECRET_KEY không hợp lệ. Nó phải là một key Fernet hợp lệ. Lỗi: {e}")


def get_db_connection():
    """Thiết lập kết nối đến cơ sở dữ liệu PostgreSQL."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        raise RuntimeError(f"🔴 LỖI NGHIÊM TRỌNG: Không thể kết nối đến cơ sở dữ liệu: {e}")


def init_database():
    """Khởi tạo bảng trong cơ sở dữ liệu nếu chưa tồn tại."""
    print("Đang kiểm tra bảng trong cơ sở dữ liệu...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                license_key TEXT PRIMARY KEY,
                hwid TEXT NOT NULL,
                end_date TEXT NOT NULL
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Bảng trong cơ sở dữ liệu đã sẵn sàng.")
    except Exception as e:
        print(f"🔴 Lỗi trong quá trình khởi tạo cơ sở dữ liệu: {e}")


# --- ENDPOINT CỦA API ---
@app.route('/validate', methods=['POST'])
def validate_license():
    """Endpoint chính để xác thực license key."""
    data = request.get_json()
    if not data or 'key' not in data or 'hwid' not in data:
        return jsonify({'status': 'error', 'message': 'Thiếu key hoặc hwid.'}), 400

    license_key = data['key']
    hwid = data['hwid']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT hwid, end_date FROM licenses WHERE license_key = %s", (license_key,))
    row = cursor.fetchone()

    if row:
        # Key đã tồn tại: Xác thực HWID và ngày hết hạn
        stored_hwid, end_date_str = row
        if stored_hwid != hwid:
            cursor.close(), conn.close()
            return jsonify({'status': 'error', 'message': 'HWID không khớp.'}), 403

        if datetime.now() > datetime.fromisoformat(end_date_str):
            cursor.close(), conn.close()
            return jsonify({'status': 'error', 'message': 'License đã hết hạn.'}), 403
        
        cursor.close(), conn.close()
        return jsonify({'status': 'success', 'message': 'License hợp lệ.', 'expires_on': end_date_str}), 200
    else:
        # Key chưa tồn tại: Thử kích hoạt lần đầu
        try:
            encrypted_token = base64.urlsafe_b64decode(license_key.encode('utf-8'))
            decrypted_duration_bytes = fernet.decrypt(encrypted_token, ttl=None)
            duration_days = int(decrypted_duration_bytes.decode('utf-8'))
            
            end_date = datetime.now() + timedelta(days=duration_days)
            end_date_str = end_date.isoformat()

            cursor.execute("INSERT INTO licenses (license_key, hwid, end_date) VALUES (%s, %s, %s)",
                           (license_key, hwid, end_date_str))
            conn.commit()
            cursor.close(), conn.close()
            
            return jsonify({'status': 'success', 'message': 'Kích hoạt license thành công!', 'expires_on': end_date_str}), 200
        except Exception:
            cursor.close(), conn.close()
            return jsonify({'status': 'error', 'message': 'License key không hợp lệ.'}), 400

# Khởi tạo bảng cơ sở dữ liệu khi ứng dụng khởi động
init_database()