import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from datetime import datetime
from loguru import logger
import uuid

class FirebaseService:
    def __init__(self):
        self.db = None
        self._initialize()

    def _initialize(self):
        try:
            # We assume firebase-applet-config.json exists after set_up_firebase
            config_path = "firebase-applet-config.json"
            if os.path.exists(config_path):
                # For admin SDK in this environment, we might need to handle credentials
                # However, if we are in a container with default service account, it might work.
                # If not, we use the client SDK or initialize with nothing if locally available.
                if not firebase_admin._apps:
                    # In AI Studio, we often use the project ID from config
                    with open(config_path) as f:
                        config = json.load(f)
                    firebase_admin.initialize_app()
                self.db = firestore.client()
            else:
                logger.warning("Firebase config not found. Comments will not be saved.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")

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
            # We add a check for existence and ensure it returns a list
            docs = self.db.collection("comments").order_by("timestamp", direction=firestore.Query.ASCENDING).stream()
            comments_list = []
            for doc in docs:
                d = doc.to_dict()
                if not d: continue
                # Handle Firestore Timestamps correctly
                if "timestamp" in d and d["timestamp"] is not None:
                    try:
                        d["timestamp"] = d["timestamp"].isoformat()
                    except AttributeError:
                        # If it's already a string or something else
                        d["timestamp"] = str(d["timestamp"])
                else:
                    d["timestamp"] = datetime.now().isoformat()
                comments_list.append(d)
            return comments_list
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
            docs = self.db.collection("ratings").stream()
            ratings = [d.to_dict()["stars"] for d in docs]
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
