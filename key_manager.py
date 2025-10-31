import os
import psycopg2
import sys
from dotenv import load_dotenv

load_dotenv()

class KeyManager:
    """
    Lớp quản lý license key (UID), tương tác với cơ sở dữ liệu PostgreSQL.
    """
    def __init__(self, database_url=None):
        """
        Khởi tạo KeyManager.
        
        Args:
            database_url (str, optional): Chuỗi kết nối database. 
                                          Nếu không được cung cấp, sẽ đọc từ biến môi trường 'POSTGRES_URL'.
        """
        self.db_url = database_url or os.environ.get('POSTGRES_URL')
        if not self.db_url:
            raise ValueError("🔴 LỖI: URL của database phải được cung cấp hoặc thiết lập trong biến môi trường 'POSTGRES_URL'.")

    def _get_connection(self):
        """Tạo và trả về một kết nối database mới."""
        return psycopg2.connect(self.db_url)

    def create_key_manual(self, uid: str, duration: int):
        """
        Tạo và lưu một key mới vào database với UID được nhập thủ công.

        Args:
            uid (str): UID/License Key được nhập thủ công.
            duration (int): Thời hạn của key (tính bằng ngày). Dùng 0 cho key vĩnh viễn.

        Returns:
            bool: True nếu tạo thành công, False nếu UID đã tồn tại.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 1. Kiểm tra UID đã tồn tại chưa
        cursor.execute("SELECT uid FROM licenses WHERE uid = %s", (uid,))
        if cursor.fetchone() is not None:
            cursor.close()
            conn.close()
            return False
            
        try:
            # 2. Chèn key mới vào database
            cursor.execute(
                "INSERT INTO licenses (uid, duration_days, is_activated, end_date) VALUES (%s, %s, FALSE, NULL)",
                (uid, duration)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"🔴 Lỗi khi chèn UID {uid}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def delete_key(self, uid: str):
        """
        Xóa một UID khỏi cơ sở dữ liệu.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM licenses WHERE uid = %s", (uid,))
        
        success = cursor.rowcount > 0
        
        conn.commit()
        cursor.close()
        conn.close()
        return success

    def reset_activation(self, uid: str):
        """
        Reset trạng thái kích hoạt của một UID (is_activated=FALSE, end_date=NULL).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE licenses SET is_activated = FALSE, end_date = NULL WHERE uid = %s", (uid,))
        
        success = cursor.rowcount > 0
        
        conn.commit()
        cursor.close()
        conn.close()
        return success

    def add_days(self, uid: str, days_to_add: int):
        """
        Thêm ngày sử dụng cho một UID đã được kích hoạt.
        
        (Lưu ý: Logic này đơn giản hơn bản gốc vì không cần kiểm tra is_activated,
        nhưng tôi sẽ giữ nguyên cấu trúc để hỗ trợ việc gia hạn sau này.)
        """
        print("Lỗi: Chức năng gia hạn (add_days) không được triển khai đầy đủ trong phiên bản này.")
        return False, "Chức năng chưa được hỗ trợ."


if __name__ == '__main__':
    print("--- Công Cụ Quản Lý License Key (Nhập Thủ Công) ---")
    try:
        input_uid = sys.argv[1]
        duration_days = int(sys.argv[2])
        
        if not input_uid or not input_uid.strip():
            print("🔴 LỖI: UID không được để trống.")
            sys.exit(1)

        if duration_days < 0:
            print("🔴 LỖI: Thời hạn phải là số nguyên dương hoặc 0.")
            sys.exit(1)
        
        manager = KeyManager()
        
        if manager.create_key_manual(input_uid, duration_days):
            duration_text = f"{duration_days} ngày" if duration_days > 0 else "VĨNH VIỄN"
            print(f"\n🎉 Đã tạo và lưu thành công UID: {input_uid}")
            print(f"   Thời hạn: {duration_text}")
        else:
            print(f"\n🔴 LỖI: UID '{input_uid}' đã tồn tại trong cơ sở dữ liệu. Không thể tạo.")
            
    except IndexError:
        print("\nCách dùng: python key_manager.py <UID_nhập_tay> <thời hạn theo ngày>")
        print("Ví dụ:   python key_manager.py MY_NEW_KEY_1 30  (tạo key 30 ngày)")
        print("         python key_manager.py UNLIMITED_UID 0    (tạo key vĩnh viễn)")
    except ValueError:
        print("🔴 Dữ liệu không hợp lệ. Vui lòng nhập số cho thời hạn.")
    except Exception as e:
        print(f"🔴 Lỗi hệ thống: {e}")
