import google.generativeai as genai
from groq import Groq
import logging
from typing import List, Dict, Any, Optional
from api.key_manager import key_manager
from loguru import logger
import os

logger = logging.getLogger(__name__)

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

    def _call_groq_fallback(self, prompt: str) -> str:
        """Hàm nội bộ gọi sang Groq bằng cú pháp riêng của Groq khi Gemini lỗi"""
        groq_key = key_manager.get_groq_key()  # Lấy key Groq từ key_manager của anh
        client = Groq(api_key=groq_key)
        
        completion = client.chat.completions.create(
            model="llama3-70b-8192",  # Hoặc model Groq nào anh muốn dùng
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return completion.choices[0].message.content
    
    def generate_research_ideas(self, context: Dict[str, Any], lit_reviews: List[Dict[str, Any]]) -> str:
        """Generates 3 research titles with tiered analysis."""
        model = self._get_model()
        level = context.get('level')
        
        # Build institutional context
        if level == "Đề tài / Dự án (Nhà nghiên cứu)":
            inst_info = f"- Đơn vị công tác: {context.get('institution')}\n- Lĩnh vực chuyên sâu: {context.get('specialty')}"
        else:
            inst_info = f"- Trường: {context.get('uni')}\n- Khoa: {context.get('fac')} / {context.get('dept')}\n- GVHD: {context.get('advisor')}"

        # Determine focus based on level
        if level == "Khóa luận tốt nghiệp (Sinh viên)":
            focus_instructions = """
            - KHÔNG phân tích tính mới (Novelty) quá cao siêu.
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
        - Thời gian: {context.get('duration')} months
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
        """Generates a detailed proposal outline with tiered structure and deep contextual guide."""
        model = self._get_model()
        level = context.get('level')
        
        # Thiết lập cấu trúc động và chỉ dẫn phân rã ý tưởng theo từng cấp độ
        if level == "Khóa luận tốt nghiệp (Sinh viên)":
            structure_instructions = """
            CẤU TRÚC ĐỀ CƯƠNG YÊU CẦU:
            I. MỞ ĐẦU / ĐẶT VẤN ĐỀ (Viết gọn gàng từ 1/2 đến 1 trang):
               - Giới thiệu bối cảnh thực tế tại địa điểm nghiên cứu.
               - Nêu lý do chọn đề tài và tính cấp thiết ở mức độ cơ bản.
            II. MỤC TIÊU NGHIÊN CỨU:
               - Gồm 1 mục tiêu tổng quát và 2-3 mục tiêu cụ thể (rõ ràng, có thể đo lường được).
            III. ĐỐI TƯỢNG VÀ PHẠM VI NGHIÊN CỨU:
               - Xác định rõ giới hạn về không gian, thời gian và đối tượng khảo sát.
            IV. NỘI DUNG VÀ PHƯƠNG PHÁP NGHIÊN CỨU:
               - Chia nhỏ thành 2-3 nội dung chính bám sát mục tiêu.
               - Với mỗi nội dung, chỉ rõ phương pháp thực hiện tương ứng (Kế thừa các phương pháp có sẵn).
            V. DỰ KIẾN KẾT QUẢ ĐẠT ĐƯỢC VÀ Ý NGHĨA THỰC TIỄN
            VI. KẾ HOẠCH THỰC HIỆN (Timeline chi tiết từng tháng)
            """
            
        elif level == "Luận văn (Thạc sĩ)":
            structure_instructions = """
            CẤU TRÚC ĐỀ CƯƠNG YÊU CẦU:
            I. MỞ ĐẦU
               1.1. Tính cấp thiết của đề tài (Phân tích rõ khoảng cách thực trạng và yêu cầu thực tế).
               1.2. Mục tiêu nghiên cứu (1 tổng quát, 3-4 cụ thể).
               1.3. Đối tượng và Phạm vi nghiên cứu.
               1.4. Ý nghĩa khoa học và thực tiễn của luận văn.
            II. TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU (Phần cốt lõi bắt buộc):
               2.1. Tình hình nghiên cứu ngoài nước (Tóm tắt các xu hướng chính).
               2.2. Tình hình nghiên cứu trong nước.
               2.3. Đánh giá chung và xác định Khoảng trống nghiên cứu (Research Gap - Tại sao nghiên cứu này cần làm để bổ sung vào các nghiên cứu trước).
            III. NỘI DUNG VÀ PHƯƠNG PHÁP NGHIÊN CỨU:
               - Chia làm 3-4 nội dung nghiên cứu chính. Mỗi nội dung phải mô tả chi tiết quy trình, kỹ thuật hoặc thiết kế nghiên cứu chuẩn mực.
            IV. DỰ KIẾN KẾT QUẢ VÀ ĐÓNG GÓP MỚI
            V. KẾ HOẠCH THỰC HIỆN
            """
            
        elif level == "Luận án (Tiến sĩ)":
            structure_instructions = f"""
            CẤU TRÚC ĐỀ CƯƠNG YÊU CẦU (Yêu cầu tư duy hàn lâm chuyên sâu ở tầm Chương Luận án):
            I. PHẦN MỞ ĐẦU:
               1.1. Tính cấp thiết của đề tài.
               1.2. Ý nghĩa khoa học và thực tiễn.
               1.3. TÍNH MỚI CỦA LUẬN ÁN (Novelty - Khẳng định điểm đóng góp mới hoàn toàn về mặt lý thuyết, phương pháp hoặc phát hiện mới).
               1.4. Mục tiêu nghiên cứu (1 tổng quát, 5-7 mục tiêu cụ thể độ khó cao).
               1.5. Giả thuyết nghiên cứu / Câu hỏi nghiên cứu (Phát biểu rõ ràng các giả thuyết khoa học cần chứng minh).
            II. CHƯƠNG 1: TỔNG QUAN LUẬN ÁN VÀ CÁC TRỤC NGHIÊN CỨU CHUYÊN SÂU
               [HƯỚNG DẪN DẪN DẮT AI]: Hãy tự động phân rã tên đề tài "{selected_title}" thành các trục nội dung cốt lõi để tự động bẻ nhỏ phần tổng quan thành các mục 1.1, 1.2, 1.3 chuyên sâu:
               - Mục 1.1: Tổng quan bản chất lý thuyết/khoa học cốt lõi của đối tượng nghiên cứu (Đi từ tổng quát thế giới).
               - Mục 1.2: Phân tích đặc thù của bối cảnh/địa điểm nghiên cứu tại Việt Nam (Ví dụ: cơ chế, chính sách, mô hình thực địa liên quan).
               - Mục 1.3: Sự giao thoa và khoảng trống tri thức (Đánh giá sâu sắc tài liệu quốc tế để chỉ rõ lỗ hổng tri thức hiện tại mà luận án sẽ lấp đầy).
            III. NỘI DUNG VÀ PHƯƠNG PHÁP NGHIÊN CỨU CHI TIẾT:
               - Thiết kế nghiên cứu tổng thể. Đưa ra 5-7 nội dung chính bám sát mục tiêu.
               - Đề xuất ứng dụng mô hình toán học, công nghệ, hoặc sơ đồ khung khái niệm (Conceptual Framework) bằng mã Mermaid.js nếu phù hợp.
            IV. DỰ KIẾN KẾT QUẢ ĐẦU RA VÀ LUẬN ĐIỂM BẢO VỆ
            V. KẾ HOẠCH THỰC HIỆN VÀ TIẾN ĐỘ DỰ KIẾN
            """
            
        else: # Đề tài / Dự án
            structure_instructions = f"""
            CẤU TRÚC ĐỀ CƯƠNG YÊU CẦU (Phù hợp với Đề tài/Dự án nghiên cứu):
            I. ĐẶT VẤN ĐỀ & TÍNH CẤP THIẾT (Gắn liền với mục tiêu kinh tế - xã hội hoặc định hướng phát triển khoa học công nghệ).
            II. TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU VÀ CÔNG NGHỆ HIỆN HÀNH:
               - Tổng quan trong và ngoài nước.
               - Đánh giá ưu/nhược điểm của các giải pháp/sản phẩm hiện có trên thị trường. Chứng minh tính cạnh tranh kỹ thuật.
            III. MỤC TIÊU VÀ SẢN PHẨM DỰ KIẾN:
               - Mục tiêu rõ ràng. Hệ thống sản phẩm (Mẫu 1, Mẫu 2, Bài báo, Đăng ký sáng chế...) phải tương xứng với kinh phí cấp độ: {context.get('budget_level')}.
            IV. NỘI DUNG VÀ GIẢI PHÁP KỸ THUẬT THỰC HIỆN
            V. PHƯƠNG ÁN CHUYỂN GIAO / ỨNG DỤNG KẾT QUẢ
            VI. KẾ HOẠCH VÀ TIẾN ĐỘ THỰC HIỆN
            """

        prompt = f"""
        Bạn là một Giáo sư, Nhà khoa học đầu ngành có tư duy phản biện sắc bén.
        Hãy soạn thảo một Gợi ý Đề cương nghiên cứu (Research Proposal Outline) mang tính đồ sộ, logic và định hướng chuyên sâu cho đề tài: "{selected_title}"
        Cấp độ thực hiện: {level}
        Thời gian: {context.get('duration')} tháng.
        
        {structure_instructions}
        
        HƯỚNG DẪN DẪN DẮT TƯ DUY KHI VIẾT NỘI DUNG:
        - Quy trình thực hiện (Chain of Thought): Hãy suy luận ngầm về mối liên hệ giữa Đối tượng ("{context.get('object')}") và Địa điểm ("{context.get('loc')}") để đắp thịt tạo nội dung thật cụ thể cho đề tài này, TUYỆT ĐỐI không viết chung chung kiểu lý thuyết suông.
        - Tại phần Phương pháp nghiên cứu, nếu đề tài cần mô tả quy trình, hãy xuất thêm một đoạn mã sơ đồ bằng MERMAID.JS (đặt trong block ```mermaid) mô tả Khung khái niệm (Conceptual Framework) hoặc Lưu đồ phương pháp.
        
        Yêu cầu kết quả đầu ra: Văn phong hàn lâm, trang trọng, cấu trúc phân cấp mục rõ ràng (Markdown). Nội dung từng mục phải đủ dày dặn, giàu thông tin gợi ý để người dùng dựa vào đó triển khai bài viết chi tiết.
        """
        
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                try:
                    # <-- Bước 3: Thay đổi tại đây, gọi hàm nội bộ thay vì gọi file ngoài
                    return self._call_groq_fallback(prompt)
                except:
                    return "⚠️ Hiện tại hệ thống đang quá tải hạn mức. Bạn vui lòng quay lại sau ít phút nhé!"
            logger.error(f"Gemini API Error: {str(e)}")
            return "Lỗi khi tạo đề cương."

gemini_client = GeminiClient()
