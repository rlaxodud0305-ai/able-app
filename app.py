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

# 1. 파일 업로드 UI
st.subheader("📁 심평원 PDF 서류 업로드")
uploaded_files = st.file_uploader(
    "심평원 PDF 파일들을 한 번에 올려주세요 (여러 개 선택 가능)", 
    type=["pdf"], 
    accept_multiple_files=True
)

customer_name = st.text_input("고객명 입력", value="김태영")

# 2. 질병코드 정제 함수 (예: AB351 -> B35.1)
def format_disease_code(code_str):
    if not code_str:
        return ""
    code = code_str.strip()
    if code.startswith('A') and len(code) >= 4:
        code = code[1:]
    if len(code) > 3 and '.' not in code:
        code = code[:3] + '.' + code[3:]
    return code

# 3. 심평원 PDF 표 추출 및 고지대상 분석 핵심 로직
def process_hira_pdfs(pdf_files):
    raw_records = []
    
    for pdf_file in pdf_files:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 5:
                            continue
                        
                        # 행 데이터 결합 텍스트
                        row_str = " ".join([str(cell) for cell in row if cell])
                        
                        # 날짜 추출 (YYYY-MM-DD)
                        dates = re.findall(r'\d{4}-\d{2}-\d{2}', row_str)
                        if not dates:
                            continue
                        
                        date_str = dates[0]
                        
                        # 질병코드 추출 패턴 (예: AB351, AK047, K57.9 등)
                        codes = re.findall(r'\b[A-Z]{1,2}\d{3,4}\b|\b[A-Z]\d{2}(?:\.\d{1,2})?\b', row_str)
                        code_val = format_disease_code(codes[0]) if codes else ""
                        
                        # 입원/외래 구분
                        treatment_type = "입원" if "입원" in row_str else "통원"
                        
                        # 약 복용일수 추출 (숫자)
                        med_days = 0
                        numbers = re.findall(r'\b\d{1,3}\b', row_str)
                        if numbers:
                            med_days = int(numbers[-1])
                        
                        # 진단명/병의원 추출
                        disease_name = "상세 진단명 확인"
                        for cell in row:
                            if cell and any(keyword in cell for keyword in ["염", "전", "양", "통", "염좌", "백선", "출혈", "장애", "관리", "분만"]):
                                disease_name = cell.replace("\n", " ").strip()
                                break
                        
                        raw_records.append({
                            "date": date_str,
                            "code": code_val,
                            "disease_name": disease_name,
                            "treatment_type": treatment_type,
                            "med_days": med_days
                        })
                        
    # 질병/코드별 병합 처리
    grouped = {}
    for r in raw_records:
        key = r["code"] if r["code"] else r["disease_name"]
        if key not in grouped:
            grouped[key] = {
                "dates": [],
                "disease_name": r["disease_name"],
                "code": r["code"],
                "types": set(),
                "total_med": 0
            }
        grouped[key]["dates"].append(r["date"])
        grouped[key]["types"].add(r["treatment_type"])
        grouped[key]["total_med"] += r["med_days"]
        
    final_items = []
    for key, info in grouped.items():
        sorted_dates = sorted(list(set(info["dates"])))
        if not sorted_dates:
            continue
            
        period_str = f"{sorted_dates[0]} ~ {sorted_dates[-1]}" if len(sorted_dates) > 1 else sorted_dates[0]
        t_type = "입원" if "입원" in info["types"] else "통원"
        visit_cnt = len(sorted_dates)
        
        # 치료일수 및 약복용 정보 가공
        treatment_days_str = f"{t_type} {visit_cnt}일"
        if visit_cnt >= 7:
            treatment_days_str += " (동일질병 합산 7일 이상)"
            
        med_str = f"{info['total_med']}일" if info['total_med'] > 0 else "안함 / 별도확인"
        if info['total_med'] >= 30:
            med_str += " (동일질병 합산 30일 이상)"
            
        final_items.append({
            "period": period_str,
            "disease_name": info["disease_name"],
            "code": info["code"] if info["code"] else "-",
            "treatment_type": t_type,
            "treatment_days": treatment_days_str,
            "status": "완치 / 구두확인 필요",
            "medication": med_str
        })
        
    return final_items

# 4. 카톡 포맷 생성 함수
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

# 5. 변환 실행 버튼
if st.button("🚀 고지 대상 추출 및 카톡 포맷 생성", type="primary", use_container_width=True):
    if not uploaded_files:
        st.warning("⚠️ 심평원 PDF 파일을 최소 1개 이상 업로드해 주세요.")
    else:
        with st.spinner("심평원 PDF 표 데이터를 정밀 분석 및 병합 중입니다..."):
            try:
                parsed_data = process_hira_pdfs(uploaded_files)
                
                if not parsed_data:
                    st.warning("⚠️ PDF 파일에서 병력 표 데이터를 인식하지 못했습니다. 파일 상태를 확인해 주세요.")
                else:
                    result_text = generate_final_kakao_text(customer_name, parsed_data)
                    st.success("✅ 심평원 데이터 분석 및 카톡 변환이 완료되었습니다! 아래 [복사] 버튼을 누르세요.")
                    st.code(result_text, language="text")
            except Exception as e:
                st.error(f"❌ PDF 파싱 중 오류가 발생했습니다: {str(e)}")
