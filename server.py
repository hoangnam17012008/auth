from flask import Flask, request, jsonify
import psycopg2
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import sys

load_dotenv()

DATABASE_URL = os.environ.get('POSTGRES_URL')

app = Flask(__name__)

if not DATABASE_URL:
    raise RuntimeError("🔴 LỖI NGHIÊM TRỌNG: POSTGRES_URL phải được thiết lập trong môi trường.")

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        raise RuntimeError(f"🔴 LỖI NGHIÊM TRỌNG: Không thể kết nối đến cơ sở dữ liệu: {e}")

def init_database():
    print("Đang kiểm tra bảng trong cơ sở dữ liệu...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                uid TEXT PRIMARY KEY,
                duration_days INTEGER NOT NULL,
                is_activated BOOLEAN DEFAULT FALSE,
                end_date TEXT
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Bảng trong cơ sở dữ liệu đã sẵn sàng.")
    except Exception as e:
        print(f"🔴 Lỗi trong quá trình khởi tạo cơ sở dữ liệu: {e}")

@app.route('/validate', methods=['POST'])
def validate_license():
    data = request.get_json()
    if not data or 'uid' not in data:
        return jsonify({'status': 'error', 'message': 'Thiếu uid.'}), 400

    uid = data['uid']

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT duration_days, is_activated, end_date FROM licenses WHERE uid = %s", (uid,))
    row = cursor.fetchone()

    if not row:
        cursor.close(), conn.close()
        return jsonify({'status': 'error', 'message': 'UID không tồn tại.'}), 404

    duration_days, is_activated, end_date_str = row
    
    if is_activated:
        if end_date_str is None:
            cursor.close(), conn.close()
            return jsonify({'status': 'success', 'message': 'UID hợp lệ (Vĩnh viễn).', 'expires_on': 'VĨNH VIỄN'}), 200

        if datetime.now() > datetime.fromisoformat(end_date_str):
            cursor.close(), conn.close()
            return jsonify({'status': 'error', 'message': 'UID đã hết hạn.'}), 403
            
        cursor.close(), conn.close()
        return jsonify({'status': 'success', 'message': 'UID hợp lệ.', 'expires_on': end_date_str}), 200
        
    else:
        try:
            if duration_days > 0:
                end_date = datetime.now() + timedelta(days=duration_days)
                new_end_date_str = end_date.isoformat()
            else:
                new_end_date_str = None
                
            cursor.execute(
                "UPDATE licenses SET is_activated = TRUE, end_date = %s WHERE uid = %s",
                (new_end_date_str, uid)
            )
            conn.commit()
            
            cursor.close(), conn.close()
            
            expires_on_display = new_end_date_str if new_end_date_str else "VĨNH VIỄN"
            return jsonify({
                'status': 'success', 
                'message': 'Kích hoạt UID thành công!', 
                'expires_on': expires_on_display
            }), 200
            
        except Exception as e:
            print(f"Lỗi kích hoạt UID {uid}: {e}")
            conn.rollback()
            cursor.close(), conn.close()
            return jsonify({'status': 'error', 'message': 'Lỗi nội bộ khi kích hoạt.'}), 500

def verify(uid):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_activated, end_date FROM licenses WHERE uid = %s", (uid,))
    row = cursor.fetchone()

    if not row:
        cursor.close(), conn.close()
        return (False, None)

    is_activated, end_date_str = row
    
    if not is_activated:
        cursor.close(), conn.close()
        return (False, "Chưa kích hoạt")

    if end_date_str is None:
        cursor.close(), conn.close()
        return (True, "VĨNH VIỄN")

    if datetime.now() > datetime.fromisoformat(end_date_str):
        cursor.close(), conn.close()
        return (False, end_date_str)
        
    cursor.close(), conn.close()
    return (True, end_date_str)

init_database()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        input_uid = sys.argv[1]
        is_valid, expires_on = verify(input_uid)
        
        print(f"\n--- KẾT QUẢ XÁC THỰC UID: {input_uid} ---")
        if is_valid:
            print(f"✅ Hợp lệ. Ngày hết hạn: {expires_on}")
        else:
            print(f"❌ KHÔNG Hợp lệ. Trạng thái: {expires_on}")
        print("-" * 35)

    else:
        app.run(debug=True)
