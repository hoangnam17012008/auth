from flask import Flask, request, jsonify
import psycopg2
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import sys

# Load environment variables (POSTGRES_URL)
load_dotenv()

DATABASE_URL = os.environ.get('POSTGRES_URL')

# Sử dụng múi giờ UTC cho tất cả các thao tác thời gian.
def now_utc():
    return datetime.now(timezone.utc)

app = Flask(__name__)

if not DATABASE_URL:
    raise RuntimeError("🔴 LỖI NGHIÊM TRỌNG: POSTGRES_URL phải được thiết lập trong môi trường.")

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        # Ghi log lỗi vào stderr để Vercel thu thập
        print(f"🔴 LỖI KẾT NỐI DB: {e}", file=sys.stderr)
        raise RuntimeError(f"🔴 LỖI NGHIÊM TRỌNG: Không thể kết nối đến cơ sở dữ liệu: {e}")

def init_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Cập nhật: Loại bỏ is_activated và sử dụng TIMESTAMPTZ cho end_date
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                uid TEXT PRIMARY KEY,
                duration_days INTEGER NOT NULL,
                end_date TIMESTAMPTZ
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        
        if __name__ == '__main__':
            print("✅ Bảng trong cơ sở dữ liệu đã sẵn sàng.")
            
    except Exception as e:
        print(f"🔴 Lỗi trong quá trình khởi tạo cơ sở dữ liệu: {e}", file=sys.stderr)

@app.route('/validate', methods=['POST'])
def validate_license():
    data = request.get_json()
    if not data or 'uid' not in data:
        return jsonify({'status': 'error', 'message': 'Thiếu uid.'}), 400

    uid = data['uid']

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Chỉ lấy duration_days và end_date
    cursor.execute("SELECT duration_days, end_date FROM licenses WHERE uid = %s", (uid,))
    row = cursor.fetchone()

    if not row:
        cursor.close(), conn.close()
        return jsonify({'status': 'error', 'message': 'UID không tồn tại.'}), 404

    duration_days, end_date_dt = row # end_date_dt là đối tượng datetime có múi giờ hoặc None
    
    # ------------------ LOGIC XÁC THỰC ------------------
    if end_date_dt is not None:
        # Key đã được kích hoạt và có thời hạn
        if now_utc() > end_date_dt:
            cursor.close(), conn.close()
            return jsonify({'status': 'error', 'message': 'UID đã hết hạn.', 'expires_on': end_date_dt.isoformat()}), 403
        
        # Key hợp lệ
        cursor.close(), conn.close()
        expires_on_display = 'VĨNH VIỄN' if duration_days == 0 else end_date_dt.isoformat()
        return jsonify({'status': 'success', 'message': 'UID hợp lệ.', 'expires_on': expires_on_display}), 200
        
    else:
        # Key chưa kích hoạt (end_date IS NULL) hoặc là key vĩnh viễn (duration_days = 0)
        
        if duration_days == 0:
            # Key vĩnh viễn, không cần gán end_date, chỉ cần trả về thành công
            cursor.close(), conn.close()
            return jsonify({'status': 'success', 'message': 'UID hợp lệ (Vĩnh viễn).', 'expires_on': 'VĨNH VIỄN'}), 200

        # Kích hoạt key có thời hạn
        try:
            end_date_dt = now_utc() + timedelta(days=duration_days)
                
            cursor.execute(
                "UPDATE licenses SET end_date = %s WHERE uid = %s",
                (end_date_dt, uid)
            )
            conn.commit()
            
            cursor.close(), conn.close()
            
            return jsonify({
                'status': 'success', 
                'message': 'Kích hoạt UID thành công!', 
                'expires_on': end_date_dt.isoformat()
            }), 200
            
        except Exception as e:
            print(f"Lỗi kích hoạt UID {uid}: {e}", file=sys.stderr)
            conn.rollback()
            cursor.close(), conn.close()
            return jsonify({'status': 'error', 'message': 'Lỗi nội bộ khi kích hoạt.'}), 500

def verify(uid):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT duration_days, end_date FROM licenses WHERE uid = %s", (uid,))
    row = cursor.fetchone()

    if not row:
        cursor.close(), conn.close()
        return (False, None)

    duration_days, end_date_dt = row
    
    if end_date_dt is None:
        # Nếu duration_days=0, nó hợp lệ vĩnh viễn
        if duration_days == 0:
            return (True, "VĨNH VIỄN")
        
        # Nếu duration_days > 0 nhưng end_date là NULL, key chưa được kích hoạt
        cursor.close(), conn.close()
        return (False, "Chưa kích hoạt")
        
    # Key đã kích hoạt và có thời hạn
    if now_utc() > end_date_dt:
        cursor.close(), conn.close()
        return (False, end_date_dt.isoformat())
        
    cursor.close(), conn.close()
    expires_on_display = 'VĨNH VIỄN' if duration_days == 0 else end_date_dt.isoformat()
    return (True, expires_on_display)

init_database()

if __name__ == '__main__':
        app.run(host="0.0.0.0", port=8000, debug=True)
