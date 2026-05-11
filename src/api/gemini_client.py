import google.generativeai as genai
from typing import List, Dict, Any, Optional
from api.key_manager import key_manager
from loguru import logger
import os

class GeminiClient:
    """
    Client for interacting with Google Gemini API with key rotation.
    """
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        
    def _get_model(self):
        # Rotate key on every call
        api_key = key_manager.get_gemini_key()
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(self.model_name)

    def generate_research_ideas(self, context: Dict[str, Any], lit_reviews: List[Dict[str, Any]]) -> str:
        """Generates 3 research titles with tiered analysis."""
        model = self._get_model()
        level = context.get('level')
        
        # Build institutional context
        inst_info = ""
        if level == "Đề tài / Dự án (Nhà nghiên cứu)":
             inst_info = f"- Đơn vị công tác: {context.get('institution')}\n- Lĩnh vực chuyên sâu: {context.get('specialty')}"
        else:
             inst_info = f"- Trường: {context.get('uni')}\n- Khoa: {context.get('fac')} / {context.get('dept')}\n- GVHD: {context.get('advisor')}"

        # Determine focus based on level
        focus_instructions = ""
        if level == "Khóa luận tốt nghiệp (Sinh viên)":
            focus_instructions = """
            - KHÔNG phân tích tính mới (Novelty).
            - TẬP TRUNG phân tích Ý nghĩa khoa học và tính thực tiễn phù hợp cấp độ cử nhân.
            - Ưu tiên các đề tài có tính kế thừa và khả thi cao trong thời gian ngắn.
            - KHÔNG phân tích tài liệu quốc tế chuyên sâu.
            """
        elif level == "Luận văn (Thạc sĩ)":
            focus_instructions = """
            - Phân tích sơ bộ về Đối tượng và Địa điểm nghiên cứu để đánh giá tính mới.
            - Kiểm tra xem có bị trùng lặp không. Nếu trùng, hãy gợi ý cách điều chỉnh (ví dụ: thay đổi địa điểm, quy mô, hoặc thêm biến số).
            - Phân tích ý nghĩa khoa học và thực tiễn.
            """
        elif level == "Luận án (Tiến sĩ)":
            focus_instructions = """
            - PHẢI phân tích Research Gap cụ thể dựa trên tài liệu quốc tế.
            - Yêu cầu tính mới (Novelty) rõ ràng về mặt học thuật.
            - Đánh giá tác động xã hội tiềm năng.
            """
        else: # Project
            focus_instructions = f"""
            - Phân tích tính mới đột phá hoặc cải tiến quy trình.
            - Đánh giá tác động và ý nghĩa đối với xã hội, kinh tế.
            - Phải dựa trên khoảng trống nghiên cứu từ các công bố quốc tế mới nhất.
            - Xem xét kinh phí ({context.get('budget_level')}) để đề xuất quy mô phù hợp.
            """

        prompt = f"""
        Bạn là một chuyên gia tư vấn nghiên cứu khoa học cấp cao tại Việt Nam. 
        Dựa trên thông tin người dùng:
        - Cấp độ: {level}
        {inst_info}
        - Đối tượng: {context.get('object')}
        - Địa điểm: {context.get('loc')}
        - Phương pháp dự kiến: {context.get('method')}
        - Thời gian: {context.get('duration')} tháng
        - Ý tưởng bổ sung: {context.get('interests')}
        
        Tài liệu tham khảo (Abstract từ file upload / Search):
        {context.get('abstracts_from_uploads', [])}
        {lit_reviews}
        
        Nhiệm vụ:
        1. Phân tích bối cảnh và hướng đi phù hợp cho người dùng.
        {focus_instructions}
        2. Đề xuất 03 Tên đề tài (Song ngữ Việt - Anh). Tên đề tài phải học thuật, đúng format Việt Nam.
        3. Với mỗi đề tài, trình bày các mục: Lý do lựa chọn, Ý nghĩa khoa học/thực tiễn, và điểm cần lưu ý.
        
        Yêu cầu: Viết hoàn toàn bằng tiếng Việt (trừ tên đề tài tiếng Anh), phong cách chuyên nghiệp, khích lệ.
        """
        
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                try:
                    from api.groq_client import groq_client
                    return groq_client.generate_research_ideas(context, lit_reviews)
                except:
                    return "⚠️ Hệ thống đang quá tải hạn mức. Bạn vui lòng quay lại sau ít phút nhé!"
            logger.error(f"Gemini API Error: {str(e)}")
            return "Xin lỗi, hiện tại tôi không thể tạo gợi ý. Vui lòng thử lại sau."

    def generate_proposal_outline(self, selected_title: str, context: Dict[str, Any]) -> str:
        """Generates a detailed proposal outline with tiered depth."""
        model = self._get_model()
        level = context.get('level')
        
        # Tiered requirements
        intro_len = "Viết dài, tối thiểu 20 câu, phân tích sâu bối cảnh và lý do thực hiện."
        
        if level == "Khóa luận tốt nghiệp (Sinh viên)":
            obj_count = "2-3 mục tiêu cụ thể"
            content_count = "2-3 nội dung nghiên cứu chính"
        elif level == "Luận văn (Thạc sĩ)":
            obj_count = "3-4 mục tiêu cụ thể"
            content_count = "3-4 nội dung nghiên cứu chính"
        elif level == "Luận án (Tiến sĩ)":
            obj_count = "5-7 mục tiêu cụ thể"
            content_count = "5-7 nội dung nghiên cứu chính (độ khó cao)"
        else: # Project
            obj_count = "Phụ thuộc vào quy mô đề tài"
            content_count = f"Tùy thuộc vào kinh phí {context.get('budget_level')} (Phân bổ hợp lý khối lượng)"

        prompt = f"""
        Hãy soạn thảo một Gợi ý Đề cương nghiên cứu (Research Proposal Outline) chi tiết cho đề tài: "{selected_title}"
        Cấp độ: {level}
        Thời gian: {context.get('duration')} tháng.
        
        Yêu cầu cấu trúc CHI TIẾT bậc nhất:
        I. Mở đầu/Đặt vấn đề: 
           - {intro_len}
        II. Mục tiêu nghiên cứu:
           - Gồm mục tiêu tổng quát và {obj_count}.
        III. Đối tượng và Phạm vi.
        IV. Nội dung nghiên cứu:
           - Trình bày {content_count}. Mỗi nội dung phải đi kèm phương pháp thực hiện tương ứng.
        V. Phương pháp nghiên cứu chi tiết:
           - Mô tả các kỹ thuật, thiết kế nghiên cứu.
        VI. Dự kiến kết quả và đóng góp xã hội/khoa học. (Phù hợp với cấp độ {level}).
        VII. Kế hoạch thực hiện (Timeline chia theo tháng).
        
        Yêu cầu: Văn phong học thuật, trang trọng. Nội dung mang tính định hướng để người dùng có thể dựa vào đó viết bài chi tiết.
        """
        
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                try:
                    from api.groq_client import groq_client
                    return groq_client.generate_proposal_outline(selected_title, context)
                except:
                    return "⚠️ Hiện tại hệ thống đang quá tải hạn mức. Bạn vui lòng quay lại sau ít phút nhé!"
            logger.error(f"Gemini API Error: {str(e)}")
            return "Lỗi khi tạo đề cương."

gemini_client = GeminiClient()
