import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from datetime import datetime
from loguru import logger
import uuid
import streamlit as st


class FirebaseService:
    def __init__(self):
        self.db = None
        self._initialize()

    def _initialize(self):
        try:
            if not firebase_admin._apps:
                # Kiểm tra Secrets của Streamlit
                import streamlit as st
                if "firebase" in st.secrets:
                    fb_dict = dict(st.secrets["firebase"])
                    # Sửa lỗi ký tự xuống dòng
                    fb_dict["private_key"] = fb_dict["private_key"].replace("\\n", "\n")
                    
                    cred = credentials.Certificate(fb_dict)
                    firebase_admin.initialize_app(cred)
                else:
                    # Nếu chạy local tìm file JSON
                    config_path = "firebase-applet-config.json"
                    if os.path.exists(config_path):
                        cred = credentials.Certificate(config_path)
                        firebase_admin.initialize_app(cred)
                    else:
                        firebase_admin.initialize_app()
            
            # Khởi tạo client
            self.db = firestore.client()
            logger.info("🔥 Kết nối Firebase thành công!")
        except Exception as e:
            logger.error(f"❌ Lỗi khởi tạo Firebase: {e}")
            self.db = None

def get_library_data(self):
    try:
        if self.db is None: return []
        # Chỉ lấy những đề tài có is_featured = True
        docs = self.db.collection("user_journeys").where("is_featured", "==", True).limit(10).stream()
        data = []
        for doc in docs:
            d = doc.to_dict()
            data.append({
                "id": doc.id,
                "Tên đề tài": d.get("topic") or d.get("user_input", {}).get("existing_title", "N/A"),
                "Cấp độ": d.get("level", "N/A"),
                "Nội dung": d.get("generated_outline", "Nội dung đang cập nhật...")
            })
        return data
    except Exception as e:
        logger.error(f"Lỗi truy vấn: {e}")
        return []
    
    def add_comment(self, email, name, content, parent_id=None, is_bot=False):
        if not self.db: return None
        comment_id = str(uuid.uuid4())
        doc_ref = self.db.collection("comments").document(comment_id)
        data = {
            "id": comment_id,
            "user_email": email,
            "user_name": name,
            "content": content,
            "parent_id": parent_id,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "is_bot": is_bot,
            "likes": 0
        }
        doc_ref.set(data)
        return comment_id

    def get_comments(self):
        if not self.db: return []
        try:
            # Attempt to fetch with server-side ordering
            try:
                docs = self.db.collection("comments").order_by("timestamp", direction="DESCENDING").limit(30).stream()
            except Exception as e:
                logger.warning(f"Server-side ordering failed: {e}. Falling back to client-side sort.")
                docs = self.db.collection("comments").limit(30).stream()

            comments_list = []
            for doc in docs:
                d = doc.to_dict()
                if not d: continue
                # Handle Firestore Timestamps correctly
                if "timestamp" in d and d["timestamp"] is not None:
                    try:
                        # If it's a Firestore Timestamp object
                        d["timestamp"] = d["timestamp"].isoformat()
                    except AttributeError:
                        # If it's already a string or something else
                        d["timestamp"] = str(d["timestamp"])
                else:
                    # Fallback for missing timestamp
                    d["timestamp"] = datetime.now().isoformat()
                comments_list.append(d)
            
            # Ensure consistent order even if server-side ordering failed
            return sorted(comments_list, key=lambda x: x.get('timestamp', ''))
        except Exception as e:
            logger.error(f"Error fetching comments: {e}")
            return []

    def add_rating(self, email, stars):
        if not self.db: return False
        try:
            rating_id = str(uuid.uuid4())
            self.db.collection("ratings").document(rating_id).set({
                "user_email": email,
                "stars": stars,
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            logger.error(f"Error saving rating: {e}")
            return False

    def get_average_rating(self):
        if not self.db: return 0.0
        try:
            docs = self.db.collection("ratings").limit(50).stream()
            ratings = []
            for d in docs:
                data = d.to_dict()
                if data and "stars" in data:
                    ratings.append(float(data["stars"]))
            
            if not ratings: return 0.0
            return sum(ratings) / len(ratings)
        except Exception as e:
            logger.error(f"Error getting avg rating: {e}")
            return 0.0

    def add_like(self, comment_id):
        if not self.db: return
        doc_ref = self.db.collection("comments").document(comment_id)
        doc_ref.update({"likes": firestore.Increment(1)})
  
    def log_user_journey(self, session_id, user_email, user_input, generated_outline):
        """Logs the entire user journey from input to outline."""
        if not self.db: return False
        try:
            journey_id = str(uuid.uuid4())
            data = {
                "session_id": session_id,
                "user_email": user_email,
                "user_input": user_input, # Should be a serializable dict
                "generated_outline": generated_outline,
                "timestamp": firestore.SERVER_TIMESTAMP,
                # Optimization for searching
                "topic": user_input.get("existing_title") or user_input.get("object", "N/A"),
                "level": user_input.get("level", "N/A")
            }
            self.db.collection("user_journeys").document(journey_id).set(data)
            return True
        except Exception as e:
            logger.error(f"Error logging journey: {e}")
            return False

firebase_service = FirebaseService()
