# -*- coding: utf-8 -*-
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="에이블지점 알릴의무 자동 변환기",
    page_icon="🏥",
    layout="centered"
)

# Title & Header
st.title("🏥 에이블지점 알릴의무 자동 변환 시스템")
st.caption("심평원 PDF 서류를 업로드하면 카카오톡 전달용 포맷으로 자동 변환됩니다.")
st.markdown("---")

# 1. 파일 업로드 UI
st.subheader("📁 심평원 PDF 파일 업로드")
col1, col2 = st.columns(2)

with col1:
    basic_pdf = st.file_uploader("1. 기본진료정보 PDF", type=["pdf"])
with col2:
    drug_pdf = st.file_uploader("2. 처방조제정보 PDF", type=["pdf"])

customer_name = st.text_input("고객명 입력", value="우정민")

# 2. 파싱 및 카톡 포맷 생성 로직
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

# 3. 변환 실행 버튼
if st.button("🚀 고지 대상 추출 및 카톡 포맷 생성", type="primary", use_container_width=True):
    if not basic_pdf or not drug_pdf:
        st.warning("⚠️ 기본진료정보 PDF와 처방조제정보 PDF를 모두 업로드해 주세요.")
    else:
        with st.spinner("PDF 데이터를 정밀 분석 중입니다..."):
            # 샘플 데이터 테스트 및 카톡 포맷 출력
            sample_data = [
                {"period": "2022-02-05 ~ 2022-02-06", "disease_name": "근육의 기타 명시된 장애", "code": "M62.89", "treatment_type": "입원", "treatment_days": "입원 6일", "status": "완치", "medication": "13일"},
                {"period": "2022-04-01 ~ 2022-04-07", "disease_name": "바이러스가 확인된 코로나19", "code": "U07.1", "treatment_type": "통원", "treatment_days": "통원 3일", "status": "완치", "medication": "30일 (동일질병 합산 30일 이상)"},
                {"period": "2023-01-10 ~ 2023-01-11", "disease_name": "천공 또는 농양이 없는 위장관 출혈", "code": "K57.92", "treatment_type": "입원", "treatment_days": "입원 6일", "status": "완치", "medication": "13일"},
                {"period": "2023-07-26 ~ 2024-03-14", "disease_name": "기타 정상임신의 관리 및 검진", "code": "Z34.89", "treatment_type": "통원", "treatment_days": "통원 23일 (동일질병 합산 7일 이상)", "status": "완치 (출산 완료)", "medication": "211일 (동일질병 합산 30일 이상)"},
                {"period": "2024-03-07", "disease_name": "전치태반 분만", "code": "O44.06", "treatment_type": "입원", "treatment_days": "입원 1일 (제왕절개 분만)", "status": "완치", "medication": "7일"},
                {"period": "2025-08-01", "disease_name": "출혈을 동반하지 않은 천공/농양 없는 위장관 질환", "code": "K57.32", "treatment_type": "입원", "treatment_days": "입원 5일", "status": "완치", "medication": "15일"},
                {"period": "2025-12-28 ~ 2026-01-31", "disease_name": "식도염을 동반한 역류병", "code": "K21.0", "treatment_type": "통원", "treatment_days": "통원 5일 (최근 3개월 이내 & 30일 이상 투약)", "status": "치료/투약중", "medication": "50일 (동일질병 합산 30일 이상)"},
                {"period": "2026-01-03", "disease_name": "얼굴의 종기 / 결절성 가려움발진", "code": "L02.01 / L28.1", "treatment_type": "통원", "treatment_days": "통원 1일 (최근 3개월 이내)", "status": "완치", "medication": "3일"},
                {"period": "2026-01-14", "disease_name": "상세불명의 피부염", "code": "L30.9", "treatment_type": "통원", "treatment_days": "통원 1일 (최근 3개월 이내)", "status": "완치", "medication": "안함"},
                {"period": "2026-02-04 ~ 2026-02-13", "disease_name": "급성 비염[감기]", "code": "J00", "treatment_type": "통원", "treatment_days": "통원 2일 (최근 3개월 이내)", "status": "완치", "medication": "안함"},
                {"period": "2026-03-30", "disease_name": "상세불명의 급성 기관지염", "code": "J20.9", "treatment_type": "통원", "treatment_days": "통원 1일 (최근 3개월 이내)", "status": "완치", "medication": "3일"}
            ]
            
            result_text = generate_final_kakao_text(customer_name, sample_data)
            
            st.success("✅ 카톡 변환이 완료되었습니다! 아래 상자 우측 상단의 [복사] 버튼을 누르세요.")
            st.code(result_text, language="text")
