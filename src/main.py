import streamlit as st
import time
import random
from datetime import datetime, timedelta
from loguru import logger
from auth.auth_handler import auth_handler
from api.key_manager import key_manager
from nlp.vietnamese_processor import process_and_translate
from models.research_models import ResearchLevel, ProjectBudget
from search.crossref_search import crossref_searcher
from search.duckduckgo_search import duckduckgo_searcher
from api.gemini_client import gemini_client
from utils.pdf_processor import extract_abstract_from_pdf
from services.firebase_service import firebase_service
from services.groq_bot_service import groq_bot
from utils.spam_check import is_spam
from pathlib import Path
import sys

# Thêm đường dẫn thư mục src vào hệ thống
file_path = Path(__file__).resolve()
root_path = file_path.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))
    
# Page configuration
st.set_page_config(
    page_title="V-Scholar Research Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styles
st.markdown("""
<style>
    .stButton>button {
        border-radius: 10px;
        height: 3.5em;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #f0f7ff;
        border-color: #1E3A8A;
    }
    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        color: #1E3A8A;
        text-align: left;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    .comment-card {
        padding: 1rem;
        border-radius: 8px;
        background-color: #f9fafb;
        margin-bottom: 0.5rem;
        border-left: 4px solid #1E3A8A;
    }
    .bot-comment {
        border-left: 4px solid #10b981;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session():
    if "research_level" not in st.session_state:
        st.session_state.research_level = None
    if "step" not in st.session_state:
        st.session_state.step = "LANDING"
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "has_rated" not in st.session_state:
        st.session_state.has_rated = False
    if "has_commented" not in st.session_state:
        st.session_state.has_commented = False
    if "last_bot_check" not in st.session_state:
        st.session_state.last_bot_check = datetime.now()

def handle_bot_activity():
    """Simulates background bot activity."""
    # This runs periodically on refresh
    now = datetime.now()
    # Check if more than 1 hour passed since last bot check or if it is first run
    # Since st.session_state is user-specific, we'd ideally use a central flag,
    # but Firebase doesn't easily store a singleton for this without a cloud function.
    # We'll use a local check but randomize triggers to simulate global activity.
    
    if random.random() < 0.05: # 5% chance on refresh to trigger bot actions
        comments = firebase_service.get_comments()
        
        # Action 1: Reply to un-replied comments
        unreplied = [c for c in comments if not c.get("is_bot") and not any(r.get("parent_id") == c.get("id") for r in comments)]
        if unreplied:
            target = random.choice(unreplied)
            # Add delay check simulation: since we can't 'wait', we just do it sometimes
            reply = groq_bot.generate_reply(target["content"])
            firebase_service.add_comment("bot@vscholar.ai", "V-Scholar Bot", reply, parent_id=target["id"], is_bot=True)
            logger.info(f"Bot replied to comment {target['id']}")

        # Action 2: Random new comment if long time no activity
        if not comments or (now - datetime.fromisoformat(comments[-1]["timestamp"])).total_seconds() > 3600:
            content = groq_bot.generate_random_comment()
            firebase_service.add_comment("bot@vscholar.ai", "V-Scholar Bot", content, is_bot=True)
            logger.info("Bot posted a random comment.")

def render_comments():
    st.write("---")
    st.subheader("💬 Cộng đồng V-Scholar")
    
    # Rating UI
    st.write("#### Bạn đánh giá thế nào về trợ lý này?")
    c1, c2 = st.columns([1, 3])
    with c1:
        rating = st.select_slider("Số sao", options=[1, 2, 3, 4, 5], value=5)
        if st.button("Gửi đánh giá"):
            firebase_service.add_rating("anonymous@user.com", rating)
            st.session_state.has_rated = True
            st.success("Cảm ơn bạn đã đánh giá!")
    
    avg_rating = firebase_service.get_average_rating()
    st.caption(f"⭐ Đánh giá trung bình: {avg_rating:.1f}/5")

    # Comment Form
    st.write("#### Thảo luận & Góp ý")
    with st.expander("Gửi bình luận mới", expanded=not st.session_state.has_commented):
        with st.form("comment_form", clear_on_submit=True):
            user_email = st.text_input("Email của bạn*", placeholder="email@example.com")
            user_name = st.text_input("Tên hiển thị (Tùy chọn)", placeholder="V-Scholar User")
            comment_text = st.text_area("Nội dung*", placeholder="Chia sẻ ý kiến hoặc thắc mắc của bạn...")
            sub = st.form_submit_button("Gửi bình luận")
            
            if sub:
                if not user_email or not comment_text:
                    st.error("Vui lòng điền đầy đủ thông tin bắt buộc.")
                elif is_spam(comment_text):
                    st.warning("⚠️ Bình luận của bạn nghi ngờ là spam. Vui lòng thử lại với nội dung khác.")
                else:
                    firebase_service.add_comment(user_email, user_name or "Người dùng ẩn danh", comment_text)
                    st.session_state.has_commented = True
                    st.success("Bình luận của bạn đã được gửi!")
                    st.rerun()

    # Display Comments
    comments = firebase_service.get_comments()
    if not comments:
        st.info("Chưa có bình luận nào. Hãy là người đầu tiên!")
    else:
        # Group replies
        main_comments = [c for c in comments if not c.get("parent_id")]
        replies = [c for c in comments if c.get("parent_id")]
        
        for c in reversed(main_comments):
            is_bot = c.get("is_bot")
            card_class = "comment-card bot-comment" if is_bot else "comment-card"
            
            st.markdown(f"""
            <div class="{card_class}">
                <strong>{c.get('user_name')}</strong> {'🤖' if is_bot else '👤'} <br>
                <small style="color: #6b7280;">{c.get('timestamp')}</small> <br>
                <p style="margin-top: 0.5rem;">{c.get('content')}</p>
                <small style="color: #1E3A8A; font-weight: bold;">👍 {c.get('likes', 0)} likes</small>
            </div>
            """, unsafe_allow_html=True)
            
            # Action buttons row
            col_act1, col_act2 = st.columns([1, 8])
            with col_act1:
                if st.button("❤️ Like", key=f"like_{c.get('id')}"):
                    firebase_service.add_like(c.get('id'))
                    st.rerun()
            with col_act2:
                if not is_bot:
                    if st.button("💬 Phản hồi", key=f"reply_{c.get('id')}"):
                        st.session_state.reply_to = c.get("id")
                        st.rerun()

            # Show replies
            c_replies = [r for r in replies if r.get("parent_id") == c.get("id")]
            for r in c_replies:
                r_is_bot = r.get("is_bot")
                r_card_class = "comment-card bot-comment" if r_is_bot else "comment-card"
                st.markdown(f"""
                <div style="margin-left: 2rem;" class="{r_card_class}">
                    <strong>{r.get('user_name')}</strong> {'🤖' if r_is_bot else '👤'} <br>
                    <small style="color: #6b7280;">{r.get('timestamp')}</small> <br>
                    <p style="margin-top: 0.5rem;">{r.get('content')}</p>
                </div>
                """, unsafe_allow_html=True)
            
            if st.session_state.get("reply_to") == c.get("id"):
                with st.form(f"reply_form_{c.get('id')}"):
                    re_email = st.text_input("Email của bạn*", key=f"re_email_{c.get('id')}")
                    re_content = st.text_area("Nội dung phản hồi*", key=f"re_content_{c.get('id')}")
                    if st.form_submit_button("Gửi phản hồi"):
                        if re_email and re_content and not is_spam(re_content):
                            firebase_service.add_comment(re_email, "Người dùng phản hồi", re_content, parent_id=c.get("id"))
                            st.session_state.reply_to = None
                            st.rerun()

def render_landing_page():
    st.markdown('<h1 class="main-header">Chào mừng đến với V-Scholar 🎓</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Hãy lựa chọn một mục dưới đây để tôi có thể giúp gợi ý đề tài và xây dựng đề cương nghiên cứu..</p>', unsafe_allow_html=True)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎓 KHÓA LUẬN TỐT NGHIỆP\n\n(Dành cho sinh viên đại học)", use_container_width=True):
            st.session_state.research_level = ResearchLevel.UNDERGRADUATE
            st.session_state.step = "FORM"
            st.rerun()
            
        st.write("")
        if st.button("📚 LUẬN VĂN THẠC SĨ\n\n(Dành cho Học viên cao học)", use_container_width=True):
            st.session_state.research_level = ResearchLevel.MASTER
            st.session_state.step = "FORM"
            st.rerun()
            
    with col2:
        if st.button("🔬 LUẬN ÁN TIẾN SĨ\n\n(Dành cho Nghiên cứu sinh)", use_container_width=True):
            st.session_state.research_level = ResearchLevel.PHD
            st.session_state.step = "FORM"
            st.rerun()
            
        st.write("")
        if st.button("🚀 ĐỀ TÀI KHCN CÁC CẤP\n\n(Dành cho Nhà khoa học)", use_container_width=True):
            st.session_state.research_level = ResearchLevel.PROJECT
            st.session_state.step = "FORM"
            st.rerun()
            
    st.divider()
    st.caption("✨ **Mẹo:** Cung cấp càng nhiều thông tin chi tiết, gợi ý càng chính xác.")
    
    # Show comments on landing too
    render_comments()

def render_research_form():
    level = st.session_state.research_level
    st.button("⬅️ Trang chủ", on_click=lambda: st.session_state.update({"research_level": None, "step": "LANDING"}))
    
    st.write(f"## 📝 Xây dựng {level.value}")
    st.write("*( * ) Càng nhiều thông tin gợi ý càng chính xác*")
    
    is_pro = (level == ResearchLevel.PROJECT)

    with st.form("main_info_form"):
        if not is_pro:
            st.markdown("##### 🏫 Thông tin Đơn vị đào tạo")
            col1, col2 = st.columns(2)
            with col1:
                u_uni = st.text_input("Trường Đại học*", placeholder="Ví dụ: Đại học Bách Khoa")
                u_fac = st.text_input("Khoa bạn đang học*", placeholder="Ví dụ: Khoa Môi trường")
            with col2:
                u_dept = st.text_input("Bộ môn / Ngành học*", placeholder="Ví dụ: Công nghệ sinh học")
                u_advisor = st.text_input("Tên Giáo viên hướng dẫn chính*", placeholder="Giáo sư Lê Văn B")
            u_inst = ""
            u_spec = ""
        else:
            st.markdown("##### 🏢 Thông tin Đơn vị công tác & Chuyên môn")
            col1, col2 = st.columns(2)
            with col1:
                u_inst = st.text_input("Tên Viện nghiên cứu / Công ty / Tổ chức*", placeholder="Ví dụ: Viện Hàn lâm KH&CN Việt Nam")
            with col2:
                u_spec = st.text_input("Lĩnh vực chuyên sâu / Ngành học*", placeholder="Ví dụ: Hóa phân tích, Robot học")
            u_uni = u_fac = u_dept = u_advisor = ""

        st.divider()
        st.markdown("##### 🔬 Vài ý tưởng ban đầu của bạn")
        col3, col4 = st.columns(2)
        with col3:
            u_obj = st.text_input("Đối tượng bạn muốn nghiên cứu* (Ví dụ: nước thải, cây trồng, vi nhựa...)", placeholder="Nước thải sản xuất")
            u_loc = st.text_input("Địa điểm bạn muốn nghiên cứu* (Ví dụ: Sông Hồng, Hà Nội...)", placeholder="Công ty ABC")
        with col4:
            u_method = st.text_input("Kỹ thuật/phương pháp/thiết bị bạn có thể sử dụng* (Ví dụ: sắc ký, phỏng vấn...)", placeholder="Phỏng vấn bằng phiếu hỏi")
            
            if level == ResearchLevel.UNDERGRADUATE:
                u_time = st.slider("Thời gian bạn có thể dành cho nghiên cứu (Tháng)*", 2, 8, 4)
            elif level == ResearchLevel.MASTER:
                u_time = st.slider("Thời gian bạn có thể dành cho nghiên cứu (Tháng)*", 6, 24, 12)
            else:
                u_time = st.slider("Thời gian bạn có thể dành cho nghiên cứu (Tháng)*", 12, 60, 36)

        st.divider()
        st.markdown("##### 📚 Tài liệu tham khảo liên quan (PDF)")
        if level == ResearchLevel.MASTER:
            max_files = 1
            st.info("Cấp độ Thạc sĩ: Cho phép tải lên tối đa 01 bài báo liên quan.")
        elif level == ResearchLevel.PHD:
            max_files = 5
            st.info("Cấp độ Tiến sĩ: Cho phép tải lên 3-5 bài báo liên quan.")
        elif level == ResearchLevel.PROJECT:
            max_files = 10
            st.info("Cấp độ Nhà nghiên cứu: Cho phép tải lên tối đa 10 bài báo liên quan.")
        else:
            max_files = 0
            st.caption("Cấp độ Sinh viên: Không yêu cầu tải lên tài liệu quốc tế.")

        uploaded_files = []
        if max_files > 0:
            uploaded_files = st.file_uploader("Tải lên các bài báo (PDF) để AI phân tích định hướng", 
                                            type=["pdf"], 
                                            accept_multiple_files=(max_files > 1))

        st.divider()
        st.markdown("##### 🎯 Thông tin khác")
        
        u_budget = ""
        u_scope = ""
        u_intl = False
        u_gap = ""

        if level in [ResearchLevel.PHD, ResearchLevel.PROJECT]:
            col_plus1, col_plus2 = st.columns(2)
            with col_plus1:
                u_scope = st.selectbox("Phạm vi nghiên cứu", ["Cấp Quốc gia", "Cấp Bộ/Tỉnh", "Cấp Cơ sở"])
                if level == ResearchLevel.PROJECT:
                    u_budget = st.selectbox("Mức kinh phí dự kiến", [b.value for b in ProjectBudget])
            with col_plus2:
                u_intl = st.checkbox("Có mục tiêu công bố quốc tế (Q1-Q4 / Scopus)", value=True)
                u_gap = st.text_area("Khoảng trống nghiên cứu sơ bộ (Nếu đã xác định)", placeholder="Những gì nghiên cứu trước chưa giải quyết được...")

        u_title = st.text_input("Bạn đã có đề tài (Để trống nếu muốn được gợi ý tên đề tài)", placeholder="Nghiên cứu đặc tính nước thải sản xuất công ty ABC nhằm tối ưu hóa chi phí xử lý")
        u_extra = st.text_area("Mô tả thêm về hướng nghiên cứu hoặc từ khóa", placeholder="Tên hợp chất nghiên cứu. Tên bài báo khoa học liên quan...")

        submitted = st.form_submit_button("🚀 Phân tích thông tin và Chuẩn bị gợi ý", use_container_width=True)
        
        if submitted:
            # Basic validation
            required_fields = [u_obj, u_loc, u_method]
            if is_pro:
                if not (u_inst and u_spec):
                    st.error("⚠️ Vui lòng điền đầy đủ các thông tin chuyên môn (*)")
                    st.stop()
            else:
                if not (u_uni and u_fac and u_dept and u_advisor):
                    st.error("⚠️ Vui lòng điền đầy đủ các thông tin học thuật (*)")
                    st.stop()
            
            if not all(required_fields):
                st.error("⚠️ Vui lòng điền đầy đủ các thông tin bắt buộc (*)")
            else:
                abstracts = []
                if uploaded_files:
                    files_list = uploaded_files if isinstance(uploaded_files, list) else [uploaded_files]
                    for f in files_list:
                        with st.spinner(f"Đang đọc Abstract từ: {f.name}..."):
                            abstracts.append(extract_abstract_from_pdf(f))
                
                params = {
                    "level": level.value, "uni": u_uni, "fac": u_fac, "dept": u_dept,
                    "advisor": u_advisor, "institution": u_inst, "specialty": u_spec,
                    "object": u_obj, "loc": u_loc, "method": u_method,
                    "duration": u_time, "interests": u_extra, "existing_title": u_title,
                    "budget_level": u_budget, "scope": u_scope, "intl_target": u_intl,
                    "research_gap": u_gap, "abstracts_from_uploads": abstracts
                }
                handle_workflow(params)

def handle_workflow(params):
    """Executes the analysis and search workflow."""
    with st.spinner("V-Scholar đang phân tích ý tưởng và tìm kiếm tài liệu tham khảo..."):
        try:
            # 1. NLP & Translation
            search_text = params["interests"] if params["interests"] else f"{params['object']} {params['method']} {params['loc']}"
            if params.get("specialty"):
                search_text += f" {params['specialty']}"
            
            nlp_result = process_and_translate(search_text)
            
            # 2. Search limits & Reference strategy
            level = params["level"]
            if level == ResearchLevel.UNDERGRADUATE.value:
                limit = 3
            elif level == ResearchLevel.MASTER.value:
                limit = 5
            elif level == ResearchLevel.PHD.value:
                limit = 7
            else: # Project
                limit = 12
            
            # 3. Parallel fetching
            literature = crossref_searcher.search_papers(nlp_result["english_translation"], limit=limit)
            web_results = duckduckgo_searcher.search_web(nlp_result["english_translation"], limit=3)
            
            # 4. Gemini Analysis
            report = gemini_client.generate_research_ideas(params, literature)
            
            st.session_state.analysis_result = {
                "params": params,
                "nlp": nlp_result,
                "literature": literature,
                "web": web_results,
                "report": report
            }
            st.session_state.step = "RESULT"
            st.rerun()
            
        except Exception as e:
            st.error(f"Lỗi: {str(e)}")
            logger.error(f"Workflow Error: {str(e)}")

def render_results():
    """Renders the analysis result and proposal outline."""
    res = st.session_state.analysis_result
    st.button("⬅️ Quay lại Form", on_click=lambda: st.session_state.update({"step": "FORM"}))
    
    st.write(f"## 💡 Kết quả phân tích cho: {res['params']['level']}")
    
    tab_ideas, tab_literature, tab_nlp = st.tabs(["🎯 Phân tích & Gợi ý", "📚 Tài liệu tham khảo", "🧠 Dữ liệu NLP"])
    
    with tab_ideas:
        st.markdown(res['report'])
        st.divider()
        st.write("### 📝 Gợi ý Đề cương nghiên cứu")
        
        # Title selection and editing
        selected_title = st.text_input("Tên đề tài bạn chọn (Bạn có thể chỉnh sửa trực tiếp tại đây):", 
                                       value=res['params']['existing_title'] if res['params']['existing_title'] else "")
        
        if st.button("Gợi ý đề cương", use_container_width=True):
            if not selected_title:
                st.warning("Vui lòng nhập hoặc chọn một tên đề tài để soạn thảo đề cương.")
            else:
                with st.spinner("Đang soạn thảo đề cương học thuật chi tiết..."):
                    outline = gemini_client.generate_proposal_outline(selected_title, res['params'])
                    st.session_state.proposal_outline = outline
                    st.session_state.selected_research_title = selected_title

        if "proposal_outline" in st.session_state:
            st.markdown("---")
            st.subheader(f"📄 Bản đề cương tham khảo: {st.session_state.selected_research_title}")
            st.markdown(st.session_state.proposal_outline)
            
            st.divider()
            st.write("#### 📥 Tải xuống đề cương")
            if not (st.session_state.has_rated and st.session_state.has_commented):
                st.warning("⚠️ Vui lòng đánh giá 5 sao và để lại bình luận góp ý ở cuối trang để mở khóa tính năng tải xuống đề cương.")
            else:
                st.success("✅ Tuyệt vời! Bạn đã có thể tải xuống đề cương dưới dạng file văn bản.")
                st.download_button(
                    label="💾 Tải xuống Đề cương (.txt)",
                    data=st.session_state.proposal_outline,
                    file_name=f"De_cuong_{st.session_state.selected_research_title.replace(' ', '_')}.txt",
                    mime="text/plain"
                )

    with tab_literature:
        st.write("### 📜 Tài liệu tham khảo đề xuất")
        level = res['params']['level']
        
        if not res['literature']:
            st.info("Không tìm thấy tài liệu phù hợp trực tiếp qua API.")
        else:
            if level == ResearchLevel.UNDERGRADUATE.value:
                st.warning("Ưu tiên bài tiếng Việt (nếu tìm thấy). Dưới đây là các tài liệu liên quan nhất:")
            elif level == ResearchLevel.MASTER.value:
                st.info("Danh mục gồm 3 bài tiếng Việt và 2 bài tiếng Anh (nếu có).")
            elif level == ResearchLevel.PHD.value:
                st.info("Danh mục tập trung vào các tài liệu tiếng Anh để phân tích Research Gap.")
            
            for p in res['literature']:
                with st.expander(f"📖 {p['title']} ({p['year']})"):
                    st.write(f"**Tác giả:** {', '.join(p['authors'])}")
                    st.write(f"**DOI:** {p['doi']}")
                    st.write(f"**Abstract:** {p['abstract'][:1000]}...")
                    st.link_button("Xem chi tiết", p['url'])
                    
    with tab_nlp:
        st.json(res['nlp'])
    
    # Show comments at the end of results too
    render_comments()

def main():
    initialize_session()
    
    # 0. Bot Activity Simulation
    handle_bot_activity()
    
    # 1. Sidebar Authentication
    # Note: User mentioned "người dùng không cần đăng nhập vẫn comment được"
    # So we keep auth optional
    name, auth_status, username = auth_handler.login()
    
    # 2. Main Logic Flow
    if st.session_state.step == "DANG_KY_FORM":
        auth_handler.render_registration_form()
    elif st.session_state.step == "LANDING":
        render_landing_page()
    elif st.session_state.step == "FORM":
        render_research_form()
    elif st.session_state.step == "RESULT":
        render_results()

if __name__ == "__main__":
    main()
