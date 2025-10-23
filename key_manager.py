# key_manager.py
import os
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv

def generate_new_secret():
    """Tạo một secret key mới và in ra màn hình."""
    key = Fernet.generate_key()
    print("🔑 SECRET_KEY mới của bạn là:\n")
    print(key.decode('utf-8'))
    print("\nSao chép key này và dán vào file .env cũng như biến môi trường trên Vercel.")

def generate_license_key(duration_days: int):
    """Tạo một license key đã được mã hóa sử dụng SECRET_KEY từ môi trường."""
    load_dotenv()
    secret_str = os.environ.get('SECRET_KEY')
    
    if not secret_str:
        print("🔴 Không tìm thấy SECRET_KEY trong file .env.")
        print("Vui lòng chạy script này với lệnh 'new' để tạo key trước.")
        return

    try:
        secret_key = secret_str.encode('utf-8')
        f = Fernet(secret_key)
        
        duration_bytes = str(duration_days).encode('utf-8')
        encrypted_token = f.encrypt(duration_bytes)
        license_key = base64.urlsafe_b64encode(encrypted_token).decode('utf-8')
        
        print(f"\n🎉 Đã tạo license key mới có thời hạn {duration_days} ngày:")
        print(license_key)
    except Exception as e:
        print(f"🔴 Đã xảy ra lỗi. SECRET_KEY của bạn có hợp lệ không? Lỗi: {e}")

if __name__ == '__main__':
    print("--- Công Cụ Tạo License Key ---")
    command = input("Nhập 'new' để tạo SECRET_KEY mới, hoặc nhập thời hạn license theo ngày (ví dụ: 30): ")
    
    if command.lower() == 'new':
        generate_new_secret()
    else:
        try:
            days = int(command)
            if days > 0:
                generate_license_key(days)
            else:
                print("🔴 Vui lòng nhập một số dương cho số ngày.")
        except ValueError:
            print("🔴 Đầu vào không hợp lệ. Vui lòng nhập một số.")