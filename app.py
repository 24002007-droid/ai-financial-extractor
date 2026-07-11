import streamlit as st
import requests
import pandas as pd
from pypdf import PdfReader
from google import genai
from google.genai import types
import json
import time

# ==========================================
# 1. ĐỊNH NGHĨA KHUÔN CẤU TRÚC DỮ LIỆU
# ==========================================
from pydantic import BaseModel, Field

class BaoCaoTaiChinh(BaseModel):
    ten_cong_ty: str = Field(description="Tên đầy đủ của công ty hoặc tập đoàn")
    ma_so_thue: str = Field(description="Mã số thuế của doanh nghiệp, chỉ lấy chữ số")
    tong_so_tien: float = Field(description="Tổng doanh thu hoặc tổng doanh số ghi nhận được, đổi về dạng số thuần túy")
    bien_loi_nhuan: str = Field(description="Tỷ lệ biên lợi nhuận hoặc tỷ suất sinh lời, bao gồm cả ký tự %")

# ==========================================
# 2. CẤU HÌNH GIAO DIỆN WEB (STREAMLIT)
# ==========================================
st.set_page_config(page_title="AI Bulk Financial Extractor", page_icon="📚", layout="wide")

st.title("📚 Hệ Thống AI Xử Lý File Báo Cáo Hàng Loạt")
st.caption("⚡ Phiên bản tối ưu hóa hiệu suất - Phát triển bởi Pro Hiếu")

# Thanh cấu hình bên cạnh
with st.sidebar:
    st.header("⚙️ Cấu Hình Hệ Thống")
    # Đã bỏ chữ mẫu phiền phức, để ô trống hoàn toàn cho pro dán và hiển thị rõ ký tự
    gemini_key = st.text_input("Dán Gemini API Key của pro vào đây:", value="")
    make_webhook = st.text_input("Make Webhook URL", value="https://hook.eu1.make.com/r7pjukb7wgllvcs9idklpld6mmt8x3yi")

# Ô KÉO THẢ NHIỀU FILE CÙNG LÚC
uploaded_files = st.file_uploader(
    "📥 Chọn hoặc kéo thả CÙNG LÚC NHIỀU FILE vào đây (Hỗ trợ .pdf, .xlsx, .xls)", 
    type=["pdf", "xlsx", "xls"], 
    accept_multiple_files=True
)

# Danh sách chứa dữ liệu thô của từng file
danh_sach_file_cho_xu_ly = []

if uploaded_files:
    st.info(f"📂 Đã nhận tổng cộng: **{len(uploaded_files)} file**. Đang tiến hành chuẩn bị đọc dữ liệu...")
    
    for f in uploaded_files:
        try:
            noi_dung_file = ""
            if f.name.endswith(".pdf"):
                pdf_reader = PdfReader(f)
                van_ban_pdf = ""
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        van_ban_pdf += text + "\n"
                noi_dung_file = van_ban_pdf
            
            elif f.name.endswith((".xlsx", ".xls")):
                df = pd.read_excel(f)
                noi_dung_file = df.to_string()
            
            if noi_dung_file:
                danh_sach_file_cho_xu_ly.append({
                    "ten_file": f.name,
                    "noi_dung": noi_dung_file
                })
        except Exception as e:
            st.error(f"❌ Lỗi khi đọc file {f.name}: {e}")

    st.success(f"✅ Đã trích xuất xong văn bản từ {len(danh_sach_file_cho_xu_ly)}/{len(uploaded_files)} file thành công!")

# NÚT BẤM KÍCH HOẠT HỆ THỐNG LIÊN THANH
if st.button("🚀 Bắt Đầu Quét Toàn Bộ File & Đồng Bộ", type="primary"):
    # Chuẩn hóa chuỗi key: xóa khoảng trắng thừa ở đầu/cuối nếu có
    pure_key = gemini_key.strip()
    
    if not danh_sach_file_cho_xu_ly:
        st.warning("Pro ơi, vui lòng tải ít nhất một file lên trước nhé!")
    elif not pure_key:
        st.error("Pro ơi, ô nhập Gemini API Key hiện tại đang để trống kìa!")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        ket_qua_tong_hop = []
        
        try:
            # Khởi tạo client với key đã được chuẩn hóa sạch sẽ
            client = genai.Client(api_key=pure_key)
            
            for idx, item in enumerate(danh_sach_file_cho_xu_ly):
                ten_file = item["ten_file"]
                noi_dung = item["noi_dung"]
                
                status_text.text(f"🤖 AI đang xử lý file ({idx + 1}/{len(danh_sach_file_cho_xu_ly)}): {ten_file}...")
                
                prompt = f"Hãy bóc tách các thông tin tài chính từ dữ liệu file được trích xuất dưới đây:\n{noi_dung}"
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=BaoCaoTaiChinh,
                        temperature=0.1
                    ),
                )
                
                data_clean = json.loads(response.text)
                data_clean["File Nguồn"] = ten_file
                ket_qua_tong_hop.append(data_clean)
                
                headers = {"Content-Type": "application/json"}
                requests.post(make_webhook, data=response.text, headers=headers)
                
                time.sleep(0.5)
                progress_bar.progress((idx + 1) / len(danh_sach_file_cho_xu_ly))
                
            status_text.text("🎉 Đã hoàn thành xử lý toàn bộ các file!")
            st.balloons()
            
            st.subheader("📋 Bảng tổng hợp kết quả bóc tách hàng loạt:")
            df_ket_qua = pd.DataFrame(ket_qua_tong_hop)
            st.dataframe(df_ket_qua, use_container_width=True)
            
        except Exception as e:
            st.error(f"❌ Hệ thống gặp lỗi xử lý AI: {e}")
