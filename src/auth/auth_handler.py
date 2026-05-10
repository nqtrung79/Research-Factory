import streamlit as st
import streamlit_authenticator as stauth
import sqlite3
import os
from loguru import logger
from typing import Optional, Dict, Any

class AuthHandler:
    """
    Handles user authentication with a manual Sidebar UI inspired by the user's example,
    but integrated with SQLite and stauth.Hasher.
    """
    
    def __init__(self, db_path: str = "vscholar_users.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                password TEXT NOT NULL,
                email TEXT NOT NULL
            )
        ''')
        
        # Check if we have any users, if not add a default admin for testing (password: admin123)
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            logger.info("No users found in database. Creating default admin user.")
            # Use stauth.Hasher to hash the password
            hashed_pw = stauth.Hasher.hash('admin123')
            cursor.execute(
                "INSERT INTO users (username, name, password, email) VALUES (?, ?, ?, ?)",
                ("admin", "Administrator", hashed_pw, "admin@vscholar.edu.vn")
            )
        
        conn.commit()
        conn.close()

    def verify_login(self, username, password):
        """Verifies credentials against the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user:
            # Use stauth.Hasher to verify the password
            # Note: streamlit-authenticator 0.3.1 Hasher verifies differently than older versions
            # We can use bcrypt directly for simplicity if Hasher is problematic, 
            # but let's try to follow the user's request for Hasher.
            try:
                # In 0.3.1, we can use verify method if available or bcrypt
                import bcrypt
                if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                    return True, user['name'], user['username']
            except Exception as e:
                logger.error(f"Verification error: {e}")
        
        return False, None, None

    def login(self):
        """
        Renders a manual login/register UI in the sidebar.
        Returns: (name, authentication_status, username)
        """
        with st.sidebar:
            st.title("🛡️ V-Scholar")

            # Check session state for logged in user
            if st.session_state.get('authentication_status'):
                st.success(f"👤 Chào mừng, {st.session_state.get('name')}")
                if st.button("Đăng xuất", use_container_width=True):
                    self.logout()
                    st.rerun()
                return st.session_state.get('name'), True, st.session_state.get('username')
            
            else:
                st.subheader("🔑 Tài khoản")
                tab1, tab2 = st.tabs(["Đăng nhập", "Đăng ký"])

                # --- Tab 1: LOGIN ---
                with tab1:
                    l_user = st.text_input("Tên đăng nhập", key="login_username")
                    l_pass = st.text_input("Mật khẩu", type="password", key="login_password")
                    if st.button("Xác nhận Đăng nhập", use_container_width=True):
                        if l_user and l_pass:
                            success, name, username = self.verify_login(l_user, l_pass)
                            if success:
                                st.session_state['authentication_status'] = True
                                st.session_state['name'] = name
                                st.session_state['username'] = username
                                st.success("Đăng nhập thành công!")
                                st.rerun()
                            else:
                                st.error("Sai tên đăng nhập hoặc mật khẩu.")
                        else:
                            st.warning("Vui lòng nhập đầy đủ thông tin.")

                # --- Tab 2: REGISTER ---
                with tab2:
                    st.info("💡 Bạn chưa có tài khoản? Hãy đăng ký để lưu trữ đề cương.")
                    if st.button("Tạo tài khoản mới", use_container_width=True):
                        st.session_state.step = "DANG_KY_FORM"
                        st.rerun()
                
                return None, None, None

    def logout(self):
        """Clears auth session state."""
        st.session_state['authentication_status'] = None
        st.session_state['name'] = None
        st.session_state['username'] = None
        logger.info("User logged out.")

    def render_registration_form(self):
        """Form đăng ký chi tiết hiện ở màn hình chính"""
        st.header("📝 Đăng ký tài khoản V-Scholar")
        with st.form("full_registration_form"):
            col1, col2 = st.columns(2)
            with col1:
                r_username = st.text_input("Tên đăng nhập*", placeholder="Dùng để đăng nhập")
                r_full_name = st.text_input("Họ và Tên*", placeholder="Ví dụ: Nguyễn Văn A")
            with col2:
                r_email = st.text_input("Email*", placeholder="Ví dụ: email@gmail.com")
                r_password = st.text_input("Mật khẩu*", type="password")

            submitted = st.form_submit_button("✅ Hoàn tất Đăng ký")
            if submitted:
                if not (r_username and r_full_name and r_email and r_password):
                    st.error("Vui lòng điền đủ các trường bắt buộc (*)")
                else:
                    success = self._save_user(r_username, r_full_name, r_password, r_email)
                    if success:
                        st.session_state['authentication_status'] = True
                        st.session_state['name'] = r_full_name
                        st.session_state['username'] = r_username
                        st.success("Tạo tài khoản thành công!")
                        st.session_state.step = "LANDING"
                        st.rerun()
                    else:
                        st.error("Tên đăng nhập đã tồn tại hoặc có lỗi xảy ra.")

        if st.button("⬅️ Quay lại"):
            st.session_state.step = "LANDING"
            st.rerun()

    def _save_user(self, username, name, password, email):
        """Saves a new user to the SQLite database."""
        hashed_pw = stauth.Hasher.hash(password)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, name, password, email) VALUES (?, ?, ?, ?)",
                (username, name, hashed_pw, email)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            logger.error(f"Error saving user: {e}")
            return False

# Global instance
auth_handler = AuthHandler()
