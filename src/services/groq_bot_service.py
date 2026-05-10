from groq import Groq
import os
from loguru import logger
from datetime import datetime, timedelta
import random

class GroqBotService:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        if self.api_key:
            self.client = Groq(api_key=self.api_key)

    def generate_reply(self, message_content):
        if not self.client: return "Groq API Key missing."
        
        try:
            prompt = f"""
            Bạn là một trợ lý ảo của V-Scholar, một ứng dụng hỗ trợ nghiên cứu khoa học.
            Nhiệm vụ: Trả lời bình luận của người dùng một cách tự nhiên, thân thiện và học thuật.
            Nếu bình luận ngắn, trả lời ngắn. Nếu bình luận dài, trả lời dài.
            Bình luận của người dùng: "{message_content}"
            
            Yêu cầu: Trả lời bằng tiếng Việt. Không dùng các từ ngữ thô tục. 
            Giọng văn khích lệ tinh thần nghiên cứu.
            """
            
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1024,
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            return "Cảm ơn bạn đã đóng góp ý kiến cho V-Scholar!"

    def generate_random_comment(self):
        if not self.client: return "Groq API Key missing."
        
        try:
            prompt = """
            Tạo một bình luận ngẫu nhiên về ứng dụng trợ lý nghiên cứu khoa học V-Scholar.
            Bình luận nên mang tính tích cực, chia sẻ về trải nghiệm sử dụng hoặc một lời khen.
            Viết bằng tiếng Việt.
            """
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=1.0,
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            return "Ứng dụng rất tuyệt vời cho sinh viên!"

groq_bot = GroqBotService()
