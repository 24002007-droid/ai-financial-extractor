import streamlit as st
import requests
import pandas as pd
from pypdf import PdfReader
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import json
import time

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
st.set_page_config(page_title="AI Bulk Financial Extractor", page_icon="📚", layout="wide")

st.title("📚 Hệ Thống AI Xử Lý File Báo Cáo Hàng Loạt")
st.caption("⚡ Phiên bản tối ưu hóa hiệu suất - Phát triển bởi Pro Hiếu")

# Thanh cấu hình bên cạnh
with st.sidebar:
    st.header("⚙️ Cấu Hình Hệ Thống")
    gemini_key = st.text_input("Gemini API Key", type="password", value="AIzaSy...")
    make_webhook = st.text_input("Make Webhook URL", value="https://hook.eu1.make.com/r7pjukb7wgllvcs9idklpld6mmt8x3yi")

# Ô KÉO THẢ NHIỀU FILE CÙNG LÚC (Kích hoạt accept_multiple_files=True)
uploaded_files = st.file_uploader(
    "📥 Chọn hoặc kéo thả CÙNG LÚC NHIỀU FILE vào đây (Hỗ trợ .pdf, .xlsx, .xls)", 
    type=["pdf", "xlsx", "xls"], 
    accept_multiple_files=True
)

# Danh sách chứa dữ liệu thô của từng file sau khi đọc
danh_sach_file_cho_xu_ly = []

if uploaded_files:
    st.info(f"📂 Đã nhận tổng cộng: **{len(uploaded_files)} file**. Đang tiến hành chuẩn bị đọc dữ liệu...")
    
    for f in uploaded_files:
        try:
            noi_dung_file = ""
            # Đọc file PDF
            if f.name.endswith(".pdf"):
                pdf_reader = PdfReader(f)
                van_ban_pdf = ""
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        van_ban_pdf += text + "\n"
                noi_dung_file = van_ban_pdf
            
            # Đọc file Excel
            elif f.name.endswith((".xlsx", ".xls")):
                df = pd.read_excel(f)
                noi_dung_file = df.to_string()
            
            # Lưu vào danh sách xử lý nếu đọc thành công dữ liệu chữ
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
    if not danh_sach_file_cho_xu_ly:
        st.warning("Pro ơi, vui lòng tải ít nhất một file lên trước nhé!")
    elif gemini_key == "" or "AIzaSy" not in gemini_key:
        st.error("Kiểm tra lại Gemini API Key ở thanh bên cạnh pro ơi!")
    else:
        # Khởi tạo thanh tiến trình trực quan
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Bảng hiển thị kết quả tổng hợp ngay trên Web
        ket_qua_tong_hop = []
        
        # Khởi tạo Client Gemini đời mới
        client = genai.Client(api_key=gemini_key)
        
        # Vòng lặp "Thần tốc" duyệt qua từng file
        for idx, item in enumerate(danh_sach_file_cho_xu_ly):
            ten_file = item["ten_file"]
            noi_dung = item["noi_dung"]
            
            status_text.text(f"🤖 AI đang xử lý file ({idx + 1}/{len(danh_sach_file_cho_xu_ly)}): {ten_file}...")
            
            try:
                prompt = f"Hãy bóc tách các thông tin tài chính từ dữ liệu file được trích xuất dưới đây:\n{noi_dung}"
                
                # Gọi AI bóc tách
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
                data_clean["File Nguồn"] = ten_file # Thêm tên file vào dữ liệu để dễ quản lý
                ket_qua_tong_hop.append(data_clean)
                
                # Bắn sang Make.com để đẩy lên Google Sheets
                headers = {"Content-Type": "application/json"}
                requests.post(make_webhook, data=response.text, headers=headers)
                
                # Tránh gửi request quá dồn dập làm nghẽn API (nghỉ 0.5 giây mỗi file)
                time.sleep(0.5)
                
            except Exception as e:
                st.error(f"❌ Lỗi khi AI xử lý file {ten_file}: {e}")
            
            # Cập nhật thanh tiến trình %
            progress_bar.progress((idx + 1) / len(danh_sach_file_cho_xu_ly))
            
        # KẾT THÚC VÒNG LẶP - ĂN MỪNG
        status_text.text("🎉 Đã hoàn thành xử lý toàn bộ các file!")
        st.balloons()
        
        # Hiển thị bảng tổng hợp dữ liệu cực đẹp ngay trên Web cho pro xem
        st.subheader("📋 Bảng tổng hợp kết quả bóc tách hàng loạt:")
        df_ket_qua = pd.DataFrame(ket_qua_tong_hop)
        st.dataframe(df_ket_qua, use_container_width=True)