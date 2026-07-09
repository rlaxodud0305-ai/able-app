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
        return "-"
    code = code_str.strip()
    if code.startswith('A') and len(code) >= 4:
        code = code[1:]
    if len(code) > 3 and '.' not in code:
        code = code[:3] + '.' + code[3:]
    return code

# 3. 超경량 초스피드 PDF 파싱 엔진
def process_hira_fast(pdf_files):
    raw_records = []
    
    for pdf_file in pdf_files:
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    # 텍스트 라인 기반 추출
                    text = page.extract_text(layout=False) or ""
                    lines = text.split("\n")
                    
                    for line in lines:
                        # 날짜 패턴 탐색 (YYYY-MM-DD 또는 YYYY.MM.DD)
                        dates = re.findall(r'\d{4}[-./]\d{2}[-./]\d{2}', line)
                        if not dates:
                            continue
                            
                        date_str = dates[0].replace(".", "-").replace("/", "-")
                        
                        # 심평원 주상병 코드 패턴 탐색 (AB351, AK047, AL600, AN46 등)
                        codes = re.findall(r'A[A-Z0-9]{3,5}|[A-Z]\d{2}(?:\.\d{1,2})?', line)
                        code_val = format_disease_code(codes[0]) if codes else "-"
                        
                        # 한글 단어 추출
                        korean_words = re.findall(r'[가-힣]+', line)
                        
                        # 불필요 단어 제거
                        exclude = {"기본진료정보", "처방조제정보", "순번", "진료시작일", "병", "의원", "약국", "진단과", "입원", "외래", "주상병", "주상병명", "코드", "총", "진료비", "내원", "일수", "건강보험", "혜택받은", "금액", "내가", "낸", "의료비", "일반의", "해당없음", "처방조제", "양방", "한방", "본인", "자료"}
                        filtered = [w for w in korean_words if w not in exclude and len(w) > 1]
                        
                        disease_name = " ".join(filtered[:2]) if filtered else "진료 내역"
                        treatment_type = "입원" if "입원" in line else "통원"
                        
                        raw_records.append({
                            "date": date_str,
                            "code": code_val,
                            "disease_name": disease_name,
                            "treatment_type": treatment_type
                        })
        except Exception:
            pass

    # 동일 질병 병합 처리
    grouped = {}
    for r in raw_records:
        key = (r["code"], r["disease_name"])
        if key not in grouped:
            grouped[key] = {
                "dates": [],
                "types": set(),
                "disease_name": r["disease_name"],
                "code": r["code"]
            }
        grouped[key]["dates"].append(r["date"])
        grouped[key]["types"].add(r["treatment_type"])
        
    final_items = []
    for key, info in grouped.items():
        sorted_dates = sorted(list(set(info["dates"])))
        if not sorted_dates:
            continue
            
        period_str = f"{sorted_dates[0]} ~ {sorted_dates[-1]}" if len(sorted_dates) > 1 else sorted_dates[0]
        t_type = "입원" if "입원" in info["types"] else "통원"
        visit_cnt = len(sorted_dates)
        
        treatment_days_str = f"{t_type} {visit_cnt}일"
        if visit_cnt >= 7:
            treatment_days_str += " (동일질병 합산 7일 이상)"
            
        final_items.append({
            "period": period_str,
            "disease_name": info["disease_name"],
            "code": info["code"],
            "treatment_type": t_type,
            "treatment_days": treatment_days_str,
            "status": "완치 / 구두확인 필요",
            "medication": "처방조제 내역 참조"
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
        with st.spinner("PDF 데이터를 초고속 분석 중입니다..."):
            parsed_data = process_hira_fast(uploaded_files)
            
            if not parsed_data:
                st.warning("⚠️ PDF 파일에서 병력 데이터를 추출하지 못했습니다. 파일 상태를 확인해 주세요.")
            else:
                result_text = generate_final_kakao_text(customer_name, parsed_data)
                st.success("✅ 파일 분석 및 카톡 변환이 성공적으로 완료되었습니다!")
                st.code(result_text, language="text")
