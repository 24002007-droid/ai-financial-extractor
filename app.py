import streamlit as st
import requests
import pandas as pd
from pypdf import PdfReader
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import json

# ==========================================
# 1. ĐỊNH NGHĨA KHUÔN CẤU TRÚC DỮ LIỆU
# ==========================================
class BaoCaoTaiChinh(BaseModel):
    ten_cong_ty: str = Field(description="Tên đầy đủ của công ty hoặc tập đoàn")
    ma_so_thue: str = Field(description="Mã số thuế của doanh nghiệp, chỉ lấy chữ số")
    tong_so_tien: float = Field(description="Tổng doanh thu hoặc tổng doanh số ghi nhận được, đổi về dạng số thuần túy")
    bien_loi_nhuan: str = Field(description="Tỷ lệ biên lợi nhuận hoặc tỷ suất sinh lời, bao gồm cả ký tự %")

# ==========================================
# 2. CẤU HÌNH GIAO DIỆN WEB (STREAMLIT)
# ==========================================
st.set_page_config(page_title="AI Document Financial Extractor", page_icon="📂", layout="centered")

st.title("📂 Hệ Thống AI Đọc File & Bóc Tách Báo Cáo")
st.caption("⚡ Phiên bản nâng cấp tự động đọc PDF/Excel - Phát triển bởi Pro Hiếu")

# Thanh cấu hình bên cạnh
with st.sidebar:
    st.header("⚙️ Cấu Hình Hệ Thống")
    gemini_key = st.text_input("Gemini API Key", type="password", value="AIzaSy...") # Điền key của pro vào đây
    make_webhook = st.text_input("Make Webhook URL", value="https://hook.eu1.make.com/r7pjukb7wgllvcs9idklpld6mmt8x3yi")

# Ô KÉO THẢ FILE (Hỗ trợ cả PDF và Excel)
uploaded_file = st.file_uploader("📥 Kéo và thả file báo cáo tài chính vào đây (Hỗ trợ .pdf, .xlsx, .xls)", type=["pdf", "xlsx", "xls"])

# Biến chứa toàn bộ nội dung văn bản sau khi đọc file
noi_dung_can_xu_ly = ""

if uploaded_file is not None:
    st.info(f"📁 Đã nhận file: **{uploaded_file.name}**. Đang tiến hành đọc dữ liệu...")
    
    try:
        # XỬ LÝ FILE PDF
        if uploaded_file.name.endswith(".pdf"):
            pdf_reader = PdfReader(uploaded_file)
            van_ban_pdf = ""
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    van_ban_pdf += text + "\n"
            noi_dung_can_xu_ly = van_ban_pdf
            st.success("✅ Đã trích xuất xong văn bản từ file PDF!")
            
            # Hiển thị thử một đoạn ngắn cho user xem trước
            with st.expander("🔍 Xem trước nội dung chữ đọc được từ PDF"):
                st.text(noi_dung_can_xu_ly[:1000] + "...")

        # XỬ LÝ FILE EXCEL
        elif uploaded_file.name.endswith((".xlsx", ".xls")):
            # Đọc file Excel thành DataFrame của Pandas, chuyển tất cả về dạng chuỗi text
            df = pd.read_excel(uploaded_file)
            noi_dung_can_xu_ly = df.to_string()
            st.success("✅ Đã chuyển đổi dữ liệu bảng từ Excel thành văn bản cấu trúc!")
            
            # Hiển thị bảng Excel trực quan ngay trên giao diện web
            with st.expander("🔍 Xem bảng dữ liệu Excel trực tiếp"):
                st.dataframe(df)

    except Exception as e:
        st.error(f"❌ Lỗi khi đọc file: {e}")

# NÚT BẤM KÍCH HOẠT AI XỬ LÝ
if st.button("🚀 AI Bắt Đầu Phân Tích & Đồng Bộ", type="primary"):
    if not noi_dung_can_xu_ly:
        st.warning("Pro ơi, vui lòng tải file lên trước đã nhé!")
    elif "ChỗNày" in gemini_key or gemini_key == "":
        st.error("Kiểm tra lại Gemini API Key ở thanh bên cạnh pro ơi!")
    else:
        with st.spinner("🤖 Thần toán Gemini đang đọc hiểu file và trích xuất dữ liệu số..."):
            try:
                # Khởi tạo Client Gemini đời mới
                client = genai.Client(api_key=gemini_key)
                
                prompt = f"Hãy bóc tách các thông tin tài chính từ dữ liệu file được trích xuất dưới đây:\n{noi_dung_can_xu_ly}"
                
                # Gọi Gemini 2.5 Flash xử lý với khuôn Pydantic dữ liệu sạch
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=BaoCaoTaiChinh,
                        temperature=0.1
                    ),
                )
                
                # Ép chuỗi text JSON từ AI thành Dict để hiển thị
                data_clean = json.loads(response.text)
                
                st.success("✨ AI đã bóc tách dữ liệu file thành công!")
                st.subheader("📋 Kết quả phân tích từ file:")
                st.json(data_clean)
                
                # Bắn sang Make.com để đẩy lên Google Sheets
                st.info("📤 Đang bắn dữ liệu sạch lên luồng Google Sheets...")
                headers = {"Content-Type": "application/json"}
                make_response = requests.post(make_webhook, data=response.text, headers=headers)
                
                if make_response.status_code == 200:
                    st.balloons() # Bắn bóng bay ăn mừng
                    st.success("🎉 Quá đỉnh! Dữ liệu từ file đã nằm gọn gàng trên Google Sheets!")
                else:
                    st.error(f"Lỗi gửi dữ liệu sang Make: {make_response.status_code}")
                    
            except Exception as e:
                st.error(f"❌ Hệ thống gặp lỗi xử lý AI: {e}")