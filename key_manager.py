# key_manager.py
import os
import psycopg2
import random
import string
import sys
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('POSTGRES_URL')
if not DATABASE_URL:
    raise RuntimeError("🔴 LỖI: POSTGRES_URL phải được thiết lập trong file .env.")

def generate_random_key(length=6):
    """Tạo một key ngẫu nhiên gồm chữ và số."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def create_keys(count: int, duration: int):
    """Tạo và lưu một số lượng key mới vào database."""
    print(f"Đang kết nối tới database để tạo {count} key với thời hạn {duration} ngày...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    generated_keys = []
    for i in range(count):
        while True:
            # Tạo key mới cho đến khi tìm được key chưa tồn tại trong DB
            new_key = generate_random_key()
            cursor.execute("SELECT license_key FROM licenses WHERE license_key = %s", (new_key,))
            if cursor.fetchone() is None:
                break
        
        try:
            cursor.execute(
                "INSERT INTO licenses (license_key, duration_days) VALUES (%s, %s)",
                (new_key, duration)
            )
            generated_keys.append(new_key)
        except Exception as e:
            print(f"🔴 Lỗi khi chèn key {new_key}: {e}")
            conn.rollback() # Hoàn tác nếu có lỗi
            
    conn.commit()
    cursor.close()
    conn.close()
    
    if generated_keys:
        print("\n🎉 Đã tạo và lưu thành công các key sau vào database:")
        for key in generated_keys:
            print(key)
    else:
        print("Không có key nào được tạo.")

if __name__ == '__main__':
    print("--- Công Cụ Quản Lý License Key ---")
    try:
        # Lấy tham số từ dòng lệnh, ví dụ: python key_manager.py 10 30
        num_keys_to_create = int(sys.argv[1])
        duration_days = int(sys.argv[2])
        create_keys(num_keys_to_create, duration_days)
    except IndexError:
        print("Cách dùng: python key_manager.py <số lượng key> <thời hạn theo ngày>")
        print("Ví dụ:   python key_manager.py 10 30  (để tạo 10 key, mỗi key 30 ngày)")
    except ValueError:
        print("🔴 Dữ liệu không hợp lệ. Vui lòng nhập số cho số lượng và thời hạn.")