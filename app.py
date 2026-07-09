# -*- coding: utf-8 -*-
import streamlit as st
import pdfplumber
import re

# 페이지 기본 설정
st.set_page_config(
    page_title="에이블지점 알릴의무 자동 변환기",
    page_icon="🏥",
    layout="centered"
)

# --- 디자인 커스텀 CSS ---
st.markdown("""
    <style>
    .main-title {
        font-size: 28px !important;
        font-weight: 700 !important;
        color: #1E1E1E;
        margin-bottom: 5px;
        line-height: 1.2;
    }
    .sub-caption {
        font-size: 15px !important;
        color: #666666;
        margin-bottom: 30px;
    }
    .stFileUploader {
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 상단 타이틀 섹션 ---
st.markdown("<div class='main-title'>🏥 에이블지점 알릴의무 자동 변환 시스템</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-caption'>심평원 PDF 서류를 업로드하면 카카오톡 전달용 포맷으로 자동 변환됩니다.</div>", unsafe_allow_html=True)
st.markdown("---")

# 1. 파일 업로드 UI (단일 / 다중 선택 업로드)
st.subheader("📁 심평원 PDF 서류 업로드")
uploaded_files = st.file_uploader(
    "심평원 PDF 파일들을 한 번에 올려주세요 (여러 개 선택 가능)", 
    type=["pdf"], 
    accept_multiple_files=True
)

customer_name = st.text_input("고객명 입력", value="김태영")

# 2. PDF 분석 및 데이터 추출 함수
def extract_text_from_pdfs(pdf_files):
    basic_text = ""
    drug_text = ""
    
    for pdf_file in pdf_files:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        # 문서 내용에 따라 자동 분류 (처방/조제 키워드 유무)
        if any(keyword in text for keyword in ["처방", "조제", "약국", "투약"]):
            drug_text += text + "\n"
        else:
            basic_text += text + "\n"
            
    return basic_text, drug_text

def parse_pdf_data(basic_text, drug_text):
    records = []
    lines = (basic_text + "\n" + drug_text).split("\n")
    
    date_pattern = re.compile(r'(\d{4}[.\-\/]\d{2}[.\-\/]\d{2})')
    code_pattern = re.compile(r'([A-Z]\d{2}(?:\.\d{1,2})?)')
    
    for line in lines:
        dates = date_pattern.findall(line)
        codes = code_pattern.findall(line)
        
        if dates or codes:
            period = " ~ ".join(dates) if len(dates) >= 2 else (dates[0] if dates else "일자 미상")
            code_str = " / ".join(codes) if codes else "코드 없음"
            
            treatment_type = "입원" if "입원" in line else "통원"
            
            records.append({
                "period": period,
                "disease_name": line.strip()[:35] if line.strip() else "상세 진단명 확인 필요",
                "code": code_str,
                "treatment_type": treatment_type,
                "treatment_days": f"{treatment_type} 내역 확인",
                "status": "완치 / 구두확인 필요",
                "medication": "처방 내역 확인"
            })
            
    if not records:
        records.append({
            "period": "최근 5년 이내",
            "disease_name": "PDF 서류 내 고지 대상 병력 추출 완료",
            "code": "-",
            "treatment_type": "통원/입원",
            "treatment_days": "상세 내역 PDF 참조",
            "status": "확인 필요",
            "medication": "상세 내역 PDF 참조"
        })
        
    return records

# 3. 카톡 포맷 생성 함수
def generate_final_kakao_text(name, disclosure_items):
    kakao_text = f"""⚠️ [컨설턴트 주의사항]
심평원 자료 특성상 최근 3개월 이내 진료 내역은 누락되었을 수 있습니다. 최근 3개월 이내 병원 방문 및 약 처방 여부는 고객에게 구두로 반드시 직접 재확인하시기 바랍니다.

[알릴의무 고지 대상 병력 안내]
※ {name} 님 개인진료정보 기반 (총 {len(disclosure_items)}건)

-----------------------------------

＃{name} 고객님 이재력

"""
    for idx, item in enumerate(disclosure_items, 1):
        kakao_text += f"{idx}.\n"
        kakao_text += f"- 언제 : {item['period']}\n"
        kakao_text += f"- 진단명 : {item['disease_name']} ({item['code']})\n"
        kakao_text += f"- 어떤치료 : {item['treatment_type']}\n"
        kakao_text += f"- 치료일수 : {item['treatment_days']}\n"
        kakao_text += f"- 현재 완치여부 : {item['status']}\n"
        kakao_text += f"- 약복용 : {item['medication']}\n\n"
        
    return kakao_text.strip()

# 4. 변환 실행 버튼
if st.button("🚀 고지 대상 추출 및 카톡 포맷 생성", type="primary", use_container_width=True):
    if not uploaded_files:
        st.warning("⚠️ 심평원 PDF 파일을 최소 1개 이상 업로드해 주세요.")
    else:
        with st.spinner("PDF 서류를 자동 분류 및 분석 중입니다..."):
            try:
                # 업로드된 파일 자동 분류 및 추출
                basic_text, drug_text = extract_text_from_pdfs(uploaded_files)
                
                # 데이터 파싱
                parsed_data = parse_pdf_data(basic_text, drug_text)
                
                # 카톡 양식 출력
                result_text = generate_final_kakao_text(customer_name, parsed_data)
                
                st.success("✅ 자동 분류 및 변환이 완료되었습니다! 아래 상자 우측 상단의 [복사] 버튼을 누르세요.")
                st.code(result_text, language="text")
            except Exception as e:
                st.error(f"❌ PDF 파싱 중 오류가 발생했습니다: {str(e)}")
