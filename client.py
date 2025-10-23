# client.py
import requests
import uuid
import hashlib

# --- CẤU HÌNH ---
SERVER_URL = "http://127.0.0.1:5000/validate"
#
# DÁN LICENSE KEY BẠN VỪA TẠO BẰNG key_manager.py VÀO ĐÂY
#
LICENSE_KEY = "DÁN_KEY_CỦA_BẠN_VÀO_ĐÂY"

def get_hwid():
    """Tạo một mã HWID duy nhất và nhất quán cho máy này."""
    # Sử dụng địa chỉ MAC là một phương pháp phổ biến.
    mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8*6, 8)][::-1])
    # Chúng ta băm (hash) nó để tránh gửi địa chỉ MAC thô và để đảm bảo định dạng nhất quán.
    return hashlib.sha256(mac_address.encode()).hexdigest()


def main_app_logic():
    """Hàm này đại diện cho logic chính của ứng dụng của bạn."""
    print("\n=================================")
    print("🎉 Chào mừng đến với ứng dụng! 🎉")
    print("Xác thực thành công. Ứng dụng đang chạy.")
    print("=================================")
    # ... code của ứng dụng sẽ nằm ở đây ...
    

if __name__ == '__main__':
    if LICENSE_KEY == "DÁN_KEY_CỦA_BẠN_VÀO_ĐÂY":
        print("🔴 Vui lòng dán một license key hợp lệ vào biến 'LICENSE_KEY' trong file client.py")
        exit()

    print("Đang xác thực với máy chủ...")
    
    # Chuẩn bị dữ liệu để gửi đi
    payload = {
        'key': LICENSE_KEY,
        'hwid': get_hwid()
    }

    try:
        response = requests.post(SERVER_URL, json=payload)
        
        # Kiểm tra xem yêu cầu có thành công không
        response.raise_for_status()

        # Phân tích phản hồi JSON
        data = response.json()
        print(f"Phản hồi từ Server: {data}")
        
        if data.get('status') == 'success':
            main_app_logic()
        else:
            print(f"Xác thực thất bại: {data.get('message', 'Lỗi không xác định')}")

    except requests.exceptions.RequestException as e:
        print(f"🔴 Không thể kết nối đến máy chủ xác thực. Lỗi: {e}")
    except Exception as e:
        print(f"Đã xảy ra lỗi không mong muốn: {e}")