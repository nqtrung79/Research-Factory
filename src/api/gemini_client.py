import google.generativeai as genai
import logging
from typing import List, Dict, Any, Optional
from api.key_manager import key_manager
from loguru import logger
import os
from groq import Groq

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Client for interacting with Google Gemini API with key rotation, 
    dynamic hierarchical persona, and inline Groq fallback.
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
        try:
            groq_key = key_manager.get_groq_key()
            client = Groq(api_key=groq_key)
            
            completion = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq Fallback critically failed: {str(e)}")
            raise e

    def _build_dynamic_persona(self, context: Dict[str, Any]) -> str:
        """Xây dựng Persona chuyên sâu phân cấp theo từng đối tượng và cấp độ tài chính"""
        level = context.get('level')
        # Lấy lĩnh vực chuyên sâu (ưu tiên specialty, nếu không có thì lấy ngành/khoa)
        specialty = context.get('specialty') or context.get('fac') or "Khoa học"
        budget_level = context.get('budget_level', '')

        if level == "Khóa luận tốt nghiệp (Sinh viên)":
            return f"Bạn là một giảng viên trong lĩnh vực {specialty} có kinh nghiệm 20 năm hướng dẫn sinh viên nghiên cứu khoa học để thực hiện khóa luận tốt nghiệp xuất sắc tại Việt Nam."
        
        elif level == "Luận văn (Thạc sĩ)":
            return f"Bạn là một giảng viên, chuyên gia trong lĩnh vực {specialty} có kinh nghiệm 30 năm hướng dẫn học viên cao học nghiên cứu khoa học để thực hiện luận văn thạc sĩ chuẩn mực tại Việt Nam."
        
        elif level == "Luận án (Tiến sĩ)":
            return f"Bạn là một Hội đồng góp ý đề cương luận án nghiên cứu sinh trong lĩnh vực {specialty}, gồm các giáo sư và chuyên gia đầu ngành có kinh nghiệm hơn 30 năm hội chuẩn và phản biện học thuật chuyên sâu tại Việt Nam."
        
        else: # Đề tài / Dự án (Nhà nghiên cứu)
            # Phân tách 3 mức hội đồng dựa theo budget_level (Cơ sở, Bộ/Tỉnh, Nhà nước)
            if "Bộ" in budget_level or "Tỉnh" in budget_level:
                hd_level = "Cấp Bộ / Cấp Tỉnh"
            elif "Quốc gia" in budget_level or "Nhà nước" in budget_level or "Lớn" in budget_level:
                hd_level = "Cấp Quốc gia / Cấp Nhà nước"
            else:
                hd_level = "Cấp Cơ sở"
                
            return f"Bạn là một Hội đồng tư vấn, đánh giá và xét duyệt đề cương {hd_level} gồm các chuyên gia hàng đầu, nhà khoa học cốt lõi có kinh nghiệm nghiên cứu trên 30 năm trong lĩnh vực {specialty} tại Việt Nam."


    def generate_research_ideas(self, context: Dict[str, Any], lit_reviews: List[Dict[str, Any]]) -> str:
        """Generates 3 research titles with tiered analysis and precise persona definition."""
        model = self._get_model()
        level = context.get('level')
        persona = self._build_dynamic_persona(context)
        
        # Khôi phục Tiered requirements gốc của anh
        intro_len = "Viết dài, tối thiểu 20 câu, phân tích sâu bối cảnh và lý do thực hiện."
        
        if level == "Khóa luận tốt nghiệp (Sinh viên)":
            obj_count = "2-3 mục tiêu cụ thể"
            content_count = "2-3 nội dung nghiên cứu chính"
            focus_instructions = """
            - KHÔNG phân tích tính mới (Novelty) quá cao siêu.
            - TẬP TRUNG phân tích Ý nghĩa khoa học và tính thực tiễn phù hợp cấp độ cử nhân.
            - Ưu tiên các đề tài có tính kế thừa và khả thi cao trong thời gian ngắn.
            - KHÔNG phân tích tài liệu quốc tế chuyên sâu.
            """
            inst_info = f"- Trường: {context.get('uni')}\n- Khoa: {context.get('fac')} / {context.get('dept')}\n- GVHD: {context.get('advisor')}"
        elif level == "Luận văn (Thạc sĩ)":
            obj_count = "3-4 mục tiêu cụ thể"
            content_count = "3-4 nội dung nghiên cứu chính"
            focus_instructions = """
            - Phân tích sơ bộ về Đối tượng và Địa điểm nghiên cứu để đánh giá tính mới.
            - Kiểm tra xem có bị trùng lặp không. Nếu trùng, hãy gợi ý cách điều chỉnh (ví dụ: thay đổi địa điểm, quy mô, hoặc thêm biến số).
            - Phân tích ý nghĩa khoa học và thực tiễn.
            """
            inst_info = f"- Trường: {context.get('uni')}\n- Khoa: {context.get('fac')} / {context.get('dept')}\n- GVHD: {context.get('advisor')}"
        elif level == "Luận án (Tiến sĩ)":
            obj_count = "5-7 mục tiêu cụ thể"
            content_count = "5-7 nội dung nghiên cứu chính (độ khó cao)"
            focus_instructions = """
            - PHẢI phân tích Research Gap cụ thể dựa trên tài liệu quốc tế.
            - Yêu cầu tính mới (Novelty) rõ ràng về mặt học thuật.
            - Đánh giá tác động xã hội tiềm năng.
            """
            inst_info = f"- Trường: {context.get('uni')}\n- Khoa: {context.get('fac')} / {context.get('dept')}\n- GVHD: {context.get('advisor')}"
        else: # Project
            obj_count = "Phụ thuộc vào quy mô đề tài"
            content_count = f"Tùy thuộc vào kinh phí {context.get('budget_level')} (Phân bổ hợp lý khối lượng)"
            focus_instructions = f"""
            - Phân tích tính mới đột phá hoặc cải tiến quy trình.
            - Đánh giá tác động và ý nghĩa đối với xã hội, kinh tế.
            - Phải dựa trên khoảng trống nghiên cứu từ các công bố quốc tế mới nhất.
            - Xem xét kinh phí ({context.get('budget_level')}) để đề xuất quy mô phù hợp.
            """
            inst_info = f"- Đơn vị công tác: {context.get('institution')}\n- Lĩnh vực chuyên sâu: {context.get('specialty')}"

        prompt = f"""
        {persona}
        
        Dựa trên thông tin người dùng cung cấp:
        - Cấp độ thực hiện: {level}
        {inst_info}
        - Đối tượng nghiên cứu: {context.get('object')}
        - Địa điểm / Phạm vi thực địa: {context.get('loc')}
        - Phương pháp dự kiến: {context.get('method')}
        - Thời gian thực hiện: {context.get('duration')} tháng
        - Ý tưởng/Sở thích bổ sung: {context.get('interests')}
        
        Tài liệu tham khảo nền tảng (Abstracts):
        {context.get('abstracts_from_uploads', [])}
        {lit_reviews}
        
        Nhiệm vụ của bạn:
        1. Phân tích bối cảnh tổng quan: {intro_len}
        {focus_instructions}
        2. Đề xuất chuẩn xác 03 Tên đề tài (Song ngữ Việt - Anh). Tên đề tài phải chuẩn học thuật, đúng văn phong form mẫu nghiên cứu của Việt Nam.
        3. Với mỗi đề tài, bẻ nhỏ và giải trình chi tiết theo cấu trúc bắt buộc:
           - Lý do lựa chọn (Định lượng rõ ràng bối cảnh).
           - Mục tiêu: Định hướng thiết lập đủ {obj_count}.
           - Nội dung cốt lõi: Định hướng phân rã cụ thể {content_count}.
           - Ý nghĩa khoa học/thực tiễn và các điểm trọng yếu cần lưu ý khi triển khai.
        
        Yêu cầu trình bày: Viết hoàn toàn bằng tiếng Việt (trừ tên tiếng Anh), cấu trúc tường minh, lập luận phản biện, sắc sảo.
        """
        
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                try:
                    return self._call_groq_fallback(prompt)
                except:
                    return "⚠️ Hệ thống đang quá tải hạn mức. Bạn vui lòng quay lại sau ít phút nhé!"
            logger.error(f"Gemini API Error: {str(e)}")
            return "Xin lỗi, hiện tại tôi không thể tạo gợi ý. Vui lòng thử lại sau."


    def generate_proposal_outline(self, selected_title: str, context: Dict[str, Any]) -> str:
        """Generates a detailed proposal outline with strict structural paragraphs and custom persona."""
        model = self._get_model()
        level = context.get('level')
        persona = self._build_dynamic_persona(context)
        tier_specific_instructions = ""
        
        # Khôi phục Tiered định lượng số lượng
        if level == "Khóa luận tốt nghiệp (Sinh viên)":
            obj_count = "2-3 mục tiêu cụ thể"
            content_count = "2-3 nội dung nghiên cứu tương ứng"
            structure_instructions = f"""
            CẤU TRÚC ĐỀ CƯƠNG BẮT BUỘC:
            I. MỞ ĐẦU / ĐẶT VẤN ĐỀ:
            Cần trình bày các vấn đề có tính logic nối tiếp nhau theo các bố cục sau:
               - [Paragraph 1]: Tổng quan bối cảnh thực tế tại địa điểm nghiên cứu.
               - [Paragraph 2]: Nêu thực trạng, lỗ hổng thực tế đang diễn ra.
               - [Paragraph 3]: Tính cấp thiết và lý do bắt buộc lựa chọn đề tài này.
               - [Paragraph 4]: Tóm tắt giới hạn giải pháp mà nghiên cứu sẽ đóng góp.
            II. MỤC TIÊU NGHIÊN CỨU:
               - Thiết lập rõ ràng 1 mục tiêu tổng quát và đúng {obj_count} (đo lường được).
            III. ĐỐI TƯỢNG VÀ PHẠM VI NGHIÊN CỨU:
               - Giới hạn cụ thể không gian, thời gian và khách thể khảo sát.
            IV. NỘI DUNG VÀ PHƯƠNG PHÁP NGHIÊN CỨU:
               - Phân nhỏ thành đúng {content_count} bám sát mục tiêu. Chỉ rõ phương pháp kế thừa thực hiện.
            V. DỰ KIẾN KẾT QUẢ ĐẠT ĐƯỢC VÀ Ý NGHĨA THỰC TIỄN
            VI. KẾ HOẠCH THỰC HIỆN CHI TIẾT TỪNG THÁNG
            """
        elif level == "Luận văn (Thạc sĩ)":
            obj_count = "3-4 mục tiêu cụ thể"
            content_count = "3-4 nội dung nghiên cứu chính"
            structure_instructions = f"""
            CẤU TRÚC ĐỀ CƯƠNG BẮT BUỘC:
            I. MỞ ĐẦU / ĐẶT VẤN ĐỀ (Phần mào đầu gợi mở, dẫn dắt bối cảnh):
               Trình bày các vấn đề có tính logic nối tiếp nhau theo đúng bố cục 6 đoạn văn sau:
               - [Paragraph 1]: Bối cảnh thực tế tại địa điểm nghiên cứu.
               - [Paragraph 2]: Nêu thực trạng, lỗ hổng thực tế đang diễn ra tại địa bàn/đối tượng khảo sát.
               - [Paragraph 3]: Giải thích sơ lược một số khái niệm khoa học trọng tâm trong lĩnh vực nghiên cứu.
               - [Paragraph 4]: Mô tả sơ bộ về tầm ảnh hưởng và tác động của đề tài nghiên cứu đối với xã hội.
               - [Paragraph 5]: Khẳng định tính cấp thiết thực tế và lý do bắt buộc lựa chọn đề tài này.
               - [Paragraph 6]: Tóm tắt giới hạn giải pháp mà nghiên cứu sẽ tập trung đóng góp.

            II. TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU:
               - 2.1. [AI tự động đặt tên mục]: Dựa vào tên đề tài, hãy tự động đưa vào mục tổng quan lý thuyết nền tảng hoặc cơ sở lý luận/khái niệm cốt lõi liên quan trực tiếp đến đối tượng để người đọc hiểu rõ bản chất nghiên cứu này là gì.
               - 2.2. Tình hình nghiên cứu trong và ngoài nước: Tổng quan, tổng hợp các công trình, bài báo nghiên cứu trước đây trên thế giới và tại Việt Nam để làm rõ dòng chảy học thuật hiện nay.
               - 2.3. Ý nghĩa và tính cấp thiết của đề tài: Từ những bình luận, đánh giá ở mục 2.2, chỉ rõ điểm hạn chế của các nghiên cứu trước (Research Gap) để chứng minh tính cấp thiết học thuật và luận giải xem đề tài này được thực hiện thì sẽ giải quyết được lỗ hổng tri thức nào, có ý nghĩa khoa học ra sao.
            II. TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU (YÊU CẦU ĐỘ SÂU ĐẶC BIỆT - KHÔNG VIẾT NGẮN):
               - 2.1. [AI tự động đặt tên mục]: Dựa vào tên đề tài, tự sinh tiêu đề cho mục Cơ sở lý luận/Khái niệm cốt lõi. Yêu cầu viết CHI TIẾT (tối thiểu 3-4 đoạn văn lớn), phân tích tường minh bản chất khoa học, cơ chế hoạt động hoặc các trường phái lý thuyết nền tảng liên quan để người đọc hiểu sâu sắc bản chất nghiên cứu.
               - 2.2. Tình hình nghiên cứu trong nước và ngoài nước : Viết sâu và chi tiết (tối thiểu 4 đoạn văn). Tổng hợp, phân nhóm các xu hướng nghiên cứu, các công trình/bài báo uy tín tại Việt Nam; phân tích xem các học giả trong nước đã giải quyết được những gì và dòng chảy học thuật nội địa đang dừng lại ở đâu. Tổng quan toàn diện các công bố quốc tế (ISI/Scopus), các mô hình và trường phái trên thế giới; phân tích các bước tiến công nghệ/lý thuyết mới nhất trên thế giới liên quan đến đề tài.
               - 2.3. Khoảng trống nghiên cứu (Research Gap) và Điểm mới học thuật (Novelty): Viết cực kỳ sắc sảo (tối thiểu 3 đoạn văn). Từ việc mổ xẻ, đối chiếu giữa mục 2.2 và 2.3, hãy chỉ rõ "điểm mù", giới hạn hoặc mâu thuẫn tri thức mà các nghiên cứu trước chưa giải quyết được. Từ đó, khẳng định Luận án này sẽ bổ sung lỗ hổng nào và tuyên bố TÍNH MỚI HOÀN TOÀN về mặt khoa học (lý thuyết, phương pháp hoặc công nghệ).
            
            III. MỤC TIÊU VÀ CÂU HỎI NGHIÊN CỨU (Tầm Luận văn Thạc sĩ):
               - Thiết lập rõ ràng 1 mục tiêu tổng quát và hệ thống đúng {obj_count} (rõ ràng, đo lường được).
               - Nâng cấp học thuật: Đưa ra các Câu hỏi nghiên cứu (Research Questions) hoặc Giả thuyết nghiên cứu cốt lõi tương ứng với các mục tiêu cụ thể để định hướng tìm lời giải.

            IV. ĐỐI TƯỢNG VÀ PHẠM VI NGHIÊN CỨU:
               - Xác định rõ ràng Khách thể khảo sát / Đối tượng nghiên cứu.
               - Giới hạn cụ thể về không gian (địa điểm) và thời gian thực hiện nghiên cứu.

            V. NỘI DUNG, PHƯƠNG PHÁP NGHIÊN CỨU VÀ KỸ THUẬT SỬ DỤNG:
               - Phân tách tiến trình nghiên cứu thành đúng {content_count} bám sát hệ thống mục tiêu.
               - Đắp thịt chi tiết: Với mỗi nội dung nghiên cứu, AI bắt buộc phải chỉ rõ Phương pháp thu thập dữ liệu, Kỹ thuật phân tích, các công cụ/mô hình tiêu chuẩn được kế thừa hoặc áp dụng để xử lý dữ liệu (đảm bảo tính khoa học cao hơn cấp cử nhân).

            VI. DỰ KIẾN KẾT QUẢ ĐẠT ĐƯỢC VÀ Ý NGHĨA THỰC TIỄN (Hệ thống các sản phẩm, báo cáo, đề xuất giải pháp ứng dụng mong muốn đạt được).

            VII. KẾ HOẠCH THỰC HIỆN CHI TIẾT TỪNG THÁNG (Timeline phân bổ cụ thể trong {context.get('duration')} tháng).
            """
             
        elif level == "Luận án (Tiến sĩ)":
            obj_count = "5-7 mục tiêu cụ thể độ khó cao"
            content_count = "5-7 nội dung nghiên cứu chuyên sâu ở tầm chương luận án"
            structure_instructions = f"""
            CẤU TRÚC ĐỀ CƯƠNG BẮT BUỘC (Yêu cầu tính hàn lâm tối cao, tư duy phản biện sắc bén):
            I. MỞ ĐẦU / ĐẶT VẤN ĐỀ (Phần mào đầu gợi mở, dẫn dắt hệ thống bối cảnh):
               Trình bày các vấn đề có tính logic nối tiếp nhau theo đúng bố cục 6 đoạn văn (Paragraphs) sau:
               - [Paragraph 1]: Bối cảnh thực tế tại địa điểm nghiên cứu.
               - [Paragraph 2]: Nêu thực trạng, lỗ hổng thực tế đang diễn ra tại địa bàn/đối tượng khảo sát.
               - [Paragraph 3]: Giải thích sơ lược một số khái niệm khoa học trọng tâm trong lĩnh vực nghiên cứu.
               - [Paragraph 4]: Mô tả sơ bộ về tầm ảnh hưởng và tác động của đề tài nghiên cứu đối với xã hội.
               - [Paragraph 5]: Khẳng định tính cấp thiết thực tế và lý do bắt buộc lựa chọn đề tài này.
               - [Paragraph 6]: Tóm tắt giới hạn giải pháp mà nghiên cứu sẽ tập trung đóng góp.

            II. TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU (BẮT BUỘC PHÂN RÃ THEO CẤU TRÚC BĂM NHỎ, KHÔNG VIẾT CHUNG CHUNG):
               - 2.1. [AI tự động đặt tên mục - Cơ sở lý luận cốt lõi]: Không viết thành một khối đại khái. Hãy băm nhỏ nội dung và triển khai bắt buộc theo 4 tầng luận điểm nối tiếp:
                      + Tầng 1: Định nghĩa tường minh các thuật ngữ khoa học trọng tâm, làm rõ các khái niệm công cụ sẽ sử dụng trong luận án.
                      + Tầng 2: Hệ thống hóa các mô hình lý thuyết nền tảng (Theoretical Framework) hoặc các trường phái lý luận đang chi phối lĩnh vực này trên thế giới.
                      + Tầng 3: Phân tích cơ chế vận hành, mối quan hệ biện chứng giữa các biến số hoặc các thành phần cấu thành đối tượng nghiên cứu.
                      + Tầng 4: Đánh giá các nhân tố khách quan/chủ quan tác động trực tiếp đến đối tượng tại môi trường học thuật hiện đại.
               
               - 2.2. Tình hình nghiên cứu trong nước: Phải phân rã thành các trục nội dung rõ ràng bao gồm:
                      + Phân nhóm các xu hướng nghiên cứu nội địa theo dòng thời gian (Các công trình tiên phong $\rightarrow$ các nghiên cứu thực nghiệm gần đây).
                      + Chỉ rõ các phương pháp luận, mô hình toán học hoặc công nghệ mà các tác giả Việt Nam thường xuyên sử dụng.
                      + Đánh giá xem giới học thuật trong nước đã giải quyết triệt để được những bài toán nào và những giới hạn nào chưa thể vượt qua do đặc thù địa bàn hoặc công nghệ.
               
               - 2.3. Tình hình nghiên cứu ngoài nước: Đòi hỏi lược khảo hệ thống (Systematic Review) các công bố quốc tế đỉnh cao (ISI/Scopus) theo các lát cắt:
                      + Lát cắt lý thuyết: Thế giới đã nâng cấp, thay đổi tư duy lý luận về đối tượng này như thế nào trong 3-5 năm trở lại đây?
                      + Lát cắt công nghệ/phương pháp: Các kỹ thuật tân tiến nhất, các mô hình mô phỏng hoặc thuật toán hiện đại nào đang được quốc tế áp dụng?
                      + Lát cắt kết quả: Những phát hiện mang tính bước ngoặt của các nhóm nghiên cứu lớn trên thế giới là gì?
               
               - 2.4. Khoảng trống nghiên cứu (Research Gap) và Điểm mới học thuật (Novelty): Bản chất là một bài văn phản biện đỉnh cao, ép AI viết theo logic 3 bước:
                      + Bước 1 (Vạch lỗi): Tổng hợp những "điểm mù", giới hạn về mặt phương pháp, sự lạc hậu về mặt lý thuyết, hoặc sự thiếu hụt dữ liệu thực nghiệm từ tổng quan mục 2.2 và 2.3.
                      + Bước 2 (Tuyên bố khoảng trống): Khẳng định chắc chắn lỗ hổng tri thức/công nghệ nào đang tồn tại mà chưa có bất kỳ công trình nào xử lý một cách trọn vẹn.
                      + Bước 3 (Luận giải điểm mới - Novelty): Tuyên bố đanh thép xem Luận án này sẽ nhảy vào khỏa lấp lỗ hổng đó bằng cách nào (Cải tiến phương pháp luận? Phát hiện cơ chế mới? Hay tối ưu hóa công nghệ?). Chứng minh luận án có đóng góp làm giàu thêm kho tàng tri thức khoa học hiện tại.
            
            III. MỤC TIÊU, CÂU HỎI VÀ GIẢ THUYẾT NGHIÊN CỨU (Tầm Luận án Tiến sĩ):
               - Thiết lập rõ ràng 1 mục tiêu tổng quát (mang tính chiến lược, dài hạn).
               - Phân rã hệ thống thành đúng {obj_count} (rõ ràng, có tính kế thừa phức hợp và đo lường được).
               - BẮT BUỘC phát biểu các Câu hỏi nghiên cứu (Research Questions) cốt lõi và Hệ thống Giả thuyết nghiên cứu (Research Hypotheses) khoa học cho từng mục tiêu cụ thể để Hội đồng bình duyệt.

            IV. ĐỐI TƯỢNG VÀ PHẠM VI NGHIÊN CỨU:
               - Xác định rõ ràng Khách thể khảo sát / Đối tượng nghiên cứu sâu của luận án.
               - Giới hạn khắt khe về không gian (địa điểm thực địa), thời gian và giới hạn về nội dung khoa học.

            V. NỘI DUNG, PHƯƠNG PHÁP NGHIÊN CỨU VÀ KHUNG KHÁI NIỆM:
               - Phân tách tiến trình nghiên cứu thành đúng {content_count}. Mỗi nội dung tương đương với một nhánh chương lớn của Luận án.
               - Thiết lập Khung khái niệm (Conceptual Framework) hoặc Khung phân tích (Analytical Framework) tổng thể cho luận án.
               - Với từng nội dung, AI phải luận giải chi tiết: Phương pháp tiếp cận (Định lượng/Định tính/Hỗn hợp), Thiết kế nghiên cứu, Quy trình thu thập dữ liệu mẫu, các kỹ thuật phân tích sâu, công cụ/phần mềm xử lý nâng cao, và minh chứng tính hợp pháp, độ tin cậy của phương pháp.

            VI. DỰ KIẾN KẾT QUẢ ĐẦU RA VÀ CÁC LUẬN ĐIỂM BẢO VỆ CỦA LUẬN ÁN:
               - Liệt kê các sản phẩm phần cứng/phần mềm, bài báo quốc tế dự kiến (ISI/Scopus) và đóng góp thực tiễn.
               - Phát biểu các luận điểm khoa học cốt lõi mà Nghiên cứu sinh sẽ mang ra bảo vệ trước Hội đồng cấp Quốc gia.

            VII. KẾ HOẠCH TIẾN ĐỘ THỰC HIỆN CHI TIẾT TỪNG THÁNG (Timeline chi tiết, khoa học phân bổ trong {context.get('duration')} tháng).
            """

        else: # Đề tài / Dự án KHCN (Phân cấp Form động: Cấp Cơ sở, Cấp Bộ/Tỉnh, Cấp Nhà nước)
            budget_level = context.get('budget_level', '')
            duration = context.get('duration', 12)
            
            # ==========================================
            # KỊCH BẢN 1: ĐỀ TÀI CẤP BỘ / CẤP TỈNH
            # ==========================================
            if "Bộ" in budget_level or "Tỉnh" in budget_level:
                project_tier = "Cấp Bộ / Cấp Tỉnh"
                obj_count = "3-4 mục tiêu cụ thể giải quyết bài toán quy mô ngành/địa phương"
                content_count = "3-4 nội dung lớn (phải có nội dung điều tra hiện trạng và nội dung ứng dụng kỹ thuật)"

                tier_specific_instructions = """
                - Sản phẩm bắt buộc (Mẫu B01-Thuyết minh): Định hình rõ Sản phẩm dạng I (Quy trình công nghệ xử lý/giảm thiểu, mô hình quản lý được chứng nhận), Sản phẩm dạng II (Báo cáo đánh giá hiện trạng, Bản đồ phân vùng rủi ro, Sổ tay hướng dẫn cho làng nghề), Sản phẩm dạng III (Tối thiểu 02 bài báo trên tạp chí uy tín thuộc danh mục Hội đồng Giáo sư nhà nước hoặc tạp chí chuyên ngành).
                - Địa chỉ ứng dụng: Phải nêu rõ cơ quan tiếp nhận (Ví dụ: Sở Tài nguyên và Môi trường, Ủy ban nhân dân huyện/tỉnh nơi có làng nghề khảo sát).
                - TẬP TRUNG vào tính cấp thiết đối với sự phát triển kinh tế - xã hội của địa phương (nếu là cấp Tỉnh) hoặc định hướng phát triển của Ngành (nếu là cấp Bộ).
                - Đối chiếu sâu với các quy hoạch phát triển, nghị quyết hoặc chương trình hành động cốt lõi hiện hành của Bộ/Tỉnh.
                """
                
                structure_instructions = f"""
                CẤU TRÚC THUYẾT MINH ĐỀ TÀI CẤP BỘ / CẤP TỈNH (Chuẩn hóa mẫu KHCN):
                I. ĐẶT VẤN ĐỀ VÀ TÍNH CẤP BÁCH CỦA ĐỀ TÀI:
                   - 1.1. Bối cảnh thực tiễn và thực trạng nút thắt của ngành/địa phương.
                   - 1.2. Căn cứ pháp lý, quy hoạch phát triển và sự phù hợp chiến lược của Bộ/Tỉnh.
                   - 1.3. Luận giải về Tính cấp bách (Tại sao phải thực hiện ngay để giải quyết điểm nghẽn hiện tại).
                II. TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU VÀ CÔNG NGHỆ HIỆN HÀNH (Băm nhỏ đa tầng):
                   - 2.1. Tổng quan các khái niệm, cơ sở lý luận nền tảng liên quan đến đối tượng nghiên cứu.
                   - 2.2. Tình hình nghiên cứu trong nước (Tổng hợp các công trình, mô hình đã triển khai tại Việt Nam).
                   - 2.3. Tình hình nghiên cứu ngoài nước (Lược khảo các giải pháp, công nghệ tương đương trên thế giới).
                   - 2.4. Đánh giá ưu/nhược điểm của các giải pháp hiện hành và xác định Khoảng trống nghiên cứu (Research Gap).
                   - 2.5. Ý nghĩa khoa học và thực tiễn của đề tài.
                III. MỤC TIÊU VÀ SẢN PHẨM KHCN DỰ KIẾN:
                   - 3.1. Mục tiêu tổng quát và hệ thống đúng {obj_count}.
                   - 3.2. Danh mục sản phẩm cam kết (Thiết lập bảng gồm 3 nhóm):
                     + Sản phẩm dạng I: Quy trình công nghệ, mô hình xử lý, phần mềm, thiết bị thử nghiệm ổn định.
                     + Sản phẩm dạng II: Báo cáo phân tích hiện trạng, Bản đồ phân vùng, Sổ tay hướng dẫn chuyển giao.
                     + Sản phẩm dạng III: Tối thiểu 02 bài báo trên tạp chí chuyên ngành uy tín trong nước (HĐGS nhà nước phê duyệt).
                IV. NỘI DUNG VÀ GIẢI PHÁP KỸ THUẬT THỰC HIỆN CHI TIẾT:
                   - Phân rã tiến trình dự án thành đúng {content_count}. Mỗi nội dung phải băm nhỏ thành các công việc cụ thể, phương pháp thực nghiệm phòng thí nghiệm/hiện trường và tiêu chí nghiệm thu rõ ràng.
                V. PHƯƠNG ÁN CHUYỂN GIAO CÔNG NGHỆ VÀ TÁC ĐỘNG XÃ HỘI:
                   - 5.1. Phương thức đào tạo, tập huấn và bàn giao sản phẩm cho đơn vị thụ hưởng.
                   - 5.2. Địa chỉ ứng dụng cụ thể (Tên Sở, ban, ngành hoặc doanh nghiệp tiếp nhận thực tế).
                   - 5.3. Đánh giá tác động đối với xã hội, môi trường và hiệu quả kinh tế dự kiến.
                VI. KẾ HOẠCH TIẾN ĐỘ THỰC HIỆN (Timeline chi tiết theo từng Quý trong {duration} tháng).
                """
                CHỈ THỊ ĐẶC THÙ CHO CẤP ĐỀ TÀI:
                {tier_specific_instructions}
                """
            # ==========================================
            # KỊCH BẢN 2: ĐỀ TÀI CẤP NHÀ NƯỚC / QUỐC GIA
            # ==========================================
            elif "Quốc gia" in budget_level or "Nhà nước" in budget_level or "Lớn" in budget_level:
                project_tier = "Cấp Nhà nước / Cấp Quốc gia"
                obj_count = "4-5 mục tiêu chiến lược, có tính tiên phong và làm chủ công nghệ tầm vĩ mô"
                content_count = "5-6 nội dung nghiên cứu đa nhánh phức hợp từ lý thuyết đến chế tạo thử nghiệm"

                tier_specific_instructions = """
                - Sản phẩm bắt buộc (Tiêu chuẩn khắt khe): Sản phẩm dạng I (Hệ thống/Công nghệ xử lý có thông số kỹ thuật vượt trội, cạnh tranh ngoại nhập); Sản phẩm dạng III (BẮT BUỘC có tối thiểu 01-02 bài báo quốc tế thuộc danh mục ISI/Scopus uy tín Q1/Q2 và 01 Đơn đăng ký Bằng sáng chế hoặc Giải pháp hữu ích được chấp nhận đơn).
                - Tầm vóc: Luận giải rõ đóng góp của đề tài vào chương trình KHCN trọng điểm quốc gia hoặc giải quyết điểm nghẽn môi trường cấp bách của đất nước.
                - Đòi hỏi lược khảo hệ thống (Systematic Review) các giải pháp/công nghệ tương đương trên thế giới, chứng minh đề tài đạt trình độ tiên tiến trong khu vực hoặc quốc tế.
                - Khung giải pháp (Mục IV): Yêu cầu AI xuất sơ đồ khối hoặc Lưu đồ công nghệ bằng mã MERMAID.JS mô tả kiến trúc/giải pháp tổng thể của dự án.
                """
                
                structure_instructions = f"""
                CẤU TRÚC THUYẾT MINH ĐỀ TÀI CẤP NHÀ NƯỚC / QUỐC GIA (Tiêu chuẩn học thuật và thực chiến tối cao):
                I. ĐẶT VẤN ĐỀ, TÍNH CẤP BÁCH VÀ TẦM VÓC CHIẾN LƯỢC:
                   - 1.1. Bối cảnh vĩ mô, xu hướng công nghệ toàn cầu và thực trạng bức thiết tầm quốc gia.
                   - 1.2. Đường lối, chủ trương của Đảng, Chính phủ và chiến lược phát triển KHCN quốc gia làm căn cứ.
                   - 1.3. Luận giải sâu sắc về Tính cấp bách (Chứng minh đây là điểm nghẽn chiến lược cốt lõi của đất nước).
                II. TỔNG QUAN HỆ THỐNG VÀ PHẢN BIỆN DÒNG CHẢY HỌC THUẬT (Yêu cầu độ sâu tuyệt đối):
                   - 2.1. Phân tích các trường phái lý thuyết, cơ chế vận hành và mô hình toán học/công nghệ công cụ.
                   - 2.2. Tình hình nghiên cứu trong nước (Phân tích, đánh giá giới hạn của các nhóm nghiên cứu mạnh nội địa).
                   - 2.3. Lược khảo hệ thống (Systematic Review) tình hình nghiên cứu ngoài nước (Bắt buộc phân tích các công bố ISI/Scopus mới nhất).
                   - 2.4. Vạch trần Khoảng trống tri thức/công nghệ thế giới chưa xử lý ổn định (Research Gap).
                   - 2.5. Tuyên bố Điểm mới đột phá (Novelty) và Lợi thế cạnh tranh vượt trội của đề tài so với hàng ngoại nhập.
                   - 2.6. Ý nghĩa khoa học, ý nghĩa thực tiễn ở tầm vĩ mô của đề tài.
                III. MỤC TIÊU VÀ HỆ THỐNG SẢN PHẨM KHCN QUỐC GIA CAM KẾT:
                   - 3.1. Mục tiêu chiến lược và hệ thống đúng {obj_count}.
                   - 3.2. Cam kết hệ thống sản phẩm đầu ra (Thiết kế bảng danh mục cực kỳ khắt khe):
                     + Sản phẩm dạng I: Hệ thống thiết bị, vật liệu mới, dây chuyền công nghệ có thông số kỹ thuật rõ ràng.
                     + Sản phẩm dạng II: Bộ dữ liệu quốc gia, bản đồ số hóa quy mô lớn, khung chính sách/khuyến nghị được nghiệm thu.
                     + Sản phẩm dạng III: BẮT BUỘC có bài báo quốc tế thuộc danh mục ISI/Scopus (Q1/Q2), sách chuyên khảo và tối thiểu 01 Đơn đăng ký Bằng sáng chế hoặc Giải pháp hữu ích.
                IV. NỘI DUNG, GIẢI PHÁP KỸ THUẬT VÀ KIẾN TRÚC HỆ THỐNG:
                   - Yêu cầu AI xuất sơ đồ khối hoặc Lưu đồ công nghệ bằng mã MERMAID.JS mô tả kiến trúc giải pháp tổng thể.
                   - Phân rã tiến trình dự án thành đúng {content_count}. Thiết kế chi tiết phương pháp tiếp cận công nghệ, thiết bị chuyên dụng, quy trình thực nghiệm và kiểm định tiêu chuẩn quốc gia.
                V. PHƯƠNG ÁN ỨNG DỤNG, CHUYỂN GIAO VÀ ĐÁNH GIÁ TÁC ĐỘNG TOÀN DIỆN:
                   - 5.1. Phương thức chuyển giao công nghệ cốt lõi, bản quyền phần mềm hoặc bản vẽ kỹ thuật.
                   - 5.2. Địa chỉ ứng dụng thực tế (Tên cụ thể của Bộ, Ngành, Tập đoàn quốc gia cam kết tiếp nhận ứng dụng).
                   - 5.3. Đánh giá tác động sâu sắc đối với Xã hội (nâng cao chất lượng sống, an sinh cộng đồng).
                   - 5.4. Đánh giá hiệu quả Kinh tế, Môi trường và đóng góp vào an ninh quốc phòng/phát triển bền vững.
                VI. KẾ HOẠCH TIẾN ĐỘ VÀ PHÂN BỔ KHỐI LƯỢNG CHI TIẾT (Timeline phân rã theo từng Quý trong {duration} tháng).
                """
                CHỈ THỊ ĐẶC THÙ CHO CẤP ĐỀ TÀI:
                {tier_specific_instructions}
                """
                
            # ==========================================
            # KỊCH BẢN 3: ĐỀ TÀI CẤP CƠ SỞ / NỘI BỘ
            # ==========================================
            else:
                project_tier = "Cấp Cơ sở"
                obj_count = "2-3 mục tiêu cụ thể nhằm giải quyết trực tiếp bài toán nội bộ"
                content_count = "2-3 nội dung thực hiện gọn gàng, có tính khả thi cao"

                tier_specific_instructions = """
                - Sản phẩm bắt buộc: Báo cáo tổng kết kỹ thuật, phần mềm/công cụ cải tiến vận hành nội bộ, quy định/quy trình nội bộ áp dụng thực tế tại đơn vị.
                - Đơn vị ứng dụng: Triển khai trực tiếp tại các phòng, ban, phân xưởng hoặc trung tâm trực thuộc cơ sở.
                """
                
                structure_instructions = f"""
                CẤU TRÚC THUYẾT MINH ĐỀ TÀI CẤP CƠ SỞ (Tập trung thực tiễn, tinh gọn):
                I. ĐẶT VẤN ĐỀ VÀ SỰ CẦN THIẾT THỰC HIỆN:
                   - 1.1. Hiện trạng và những khó khăn kỹ thuật, quản lý đang gặp phải ngay tại đơn vị cơ sở.
                   - 1.2. Lý do chọn đề tài và lợi ích thiết thực mang lại cho đơn vị khi đề tài thành công.
                II. TỔNG QUAN CÔNG NGHỆ VÀ THỰC TRẠNG TẠI ĐƠN VỊ:
                   - 2.1. Khái quát các giải pháp kỹ thuật, phần mềm hoặc quy trình tương tự đang được áp dụng bên ngoài.
                   - 2.2. Đánh giá thực trạng, năng lực kỹ thuật và giới hạn hiện tại của chính đơn vị để làm rõ hướng cải tiến.
                III. MỤC TIÊU VÀ SẢN PHẨM MONG MUỐN ĐẠT ĐƯỢC:
                   - 3.1. Mục tiêu chi tiết và hệ thống đúng {obj_count}.
                   - 3.2. Sản phẩm cam kết: Báo cáo kỹ thuật, phần mềm ứng dụng nội bộ, quy trình cải tiến được áp dụng tại chỗ.
                IV. NỘI DUNG VÀ TIẾN TRÌNH TRIỂN KHAI THỰC NGHIỆM:
                   - Phân rã thành đúng {content_count}. Tập trung vào các bước thu thập số liệu nội bộ, thiết kế chỉnh sửa, chạy thử nghiệm tại các phòng/ban và nghiệm thu cuốn chiếu.
                V. HIỆU QUẢ ỨNG DỤNG TẠI ĐƠN VỊ:
                   - 5.1. Phương án đưa sản phẩm vào vận hành thực tế tại các bộ phận nội bộ.
                   - 5.2. Hiệu quả kinh tế (tiết kiệm chi phí, tối ưu nhân lực) và tác động tích cực đến môi trường làm việc/vận hành của đơn vị.
                VI. KẾ HOẠCH TIẾN ĐỘ THỰC HIỆN CHI TIẾT (Timeline phân bổ theo tháng trong {duration} tháng).
                
            
                CHỈ THỊ ĐẶC THÙ CHO CẤP ĐỀ TÀI:
                {tier_specific_instructions}
                """

        prompt = f"""
        {persona}
        
        Hãy soạn thảo một bản Gợi ý Đề cương nghiên cứu (Research Proposal Outline) mang tính logic tối cao, cấu trúc chặt chẽ và định hướng triển khai chuyên sâu cho đề tài: "{selected_title}"
        Cấp độ thực hiện: {level}
        Thời gian cho phép: {context.get('duration')} tháng.
        
        {structure_instructions}
        
        HƯỚNG DẪN DẪN DẮT TƯ DUY (Chain of Thought):
        - Hãy kết nối biện chứng giữa Đối tượng ("{context.get('object')}") và Địa điểm ("{context.get('loc')}") để đắp nội dung thực tế cực kỳ chi tiết cho đề tài này. TUYỆT ĐỐI không viết lý thuyết suông.
        - Tại phần Phương pháp nghiên cứu, nếu đề tài cần mô tả quy trình hệ thống hoặc thu thập dữ liệu, hãy xuất một đoạn mã sơ đồ bằng MERMAID.JS (nằm gọn trong khối ```mermaid) mô tả Lưu đồ phương pháp thực hiện.
        
        QUY TẮC ĐỊNH DẠNG ĐẦU RA BẮT BUỘC (CRITICAL OUTPUT RULES):
        1. TUYỆT ĐỐI KHÔNG viết lời chào mừng, lời mở đầu sáo rỗng hoặc các câu dẫn dắt (Ví dụ: "Dưới đây là...", "Tuyệt vời!...", "Sau đây là...").
        2. TUYỆT ĐỐI KHÔNG viết lời kết, tóm tắt, lời chúc hoặc bất kỳ câu xã giao nào ở cuối văn bản.
        3. Hãy nhảy THẲNG vào nội dung chuyên môn từ mục đầu tiên cho đến mục cuối cùng.
        4. Định dạng đầu ra: Sử dụng cấu trúc phân cấp Markdown trang trọng, học thuật, sắc bén và dày dặn nội dung thực tế.
        """
        
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                try:
                    return self._call_groq_fallback(prompt)
                except:
                    return "⚠️ Hiện tại hệ thống đang quá tải hạn mức. Bạn vui lòng quay lại sau ít phút nhé!"
            logger.error(f"Gemini API Error: {str(e)}")
            return "Lỗi khi tạo đề cương."

gemini_client = GeminiClient()
