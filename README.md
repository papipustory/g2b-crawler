아래는 기존 `README.md` 내용을 보완하고 문법적으로 다듬은 **자세하고 명확한 안내문 수정본**입니다.

---

### 📘 개선된 `README.md`

````markdown
# G2B 제안공고 크롤러 (g2b-crawler)

이 프로젝트는 [나라장터 쇼핑몰](https://shop.g2b.go.kr)에서 **컴퓨터 관련 제안공고**를 자동으로 수집하는 웹 크롤러입니다.  
Python 기반으로 개발되었으며, **Playwright 비동기 크롤러**와 **Streamlit 인터페이스**를 통합하여 웹 환경에서도 동작하도록 구성되어 있습니다.

---

## ✅ 주요 특징

- `playwright`를 이용한 비동기 웹 크롤링
- 사용자가 입력한 검색어로 공고 검색 (예: 컴퓨터, 데스크톱, 노트북 등)
- 크롤링된 데이터를 `Excel`로 자동 저장 및 정리
- Excel 첫 열에 검색어 삽입, 열 너비 및 정렬 서식 자동화
- Streamlit 웹 UI 제공 (검색어 입력 및 실행 버튼 포함)
- Streamlit Cloud 배포용으로 구성

---

## 💻 실행 환경

- Python 3.10 권장 (3.11까지 호환됨)
- `playwright`는 Python 3.10 또는 3.11에서 안정적으로 작동
- 다른 Python 버전과의 충돌을 방지하기 위해 **가상 환경(venv)**에서 실행을 권장

---

## 📦 설치 방법 (로컬 실행 기준)

1. Python 3.10 설치  
2. 가상 환경 구성
   ```bash
   python -m venv venv
   source venv/bin/activate  # (Windows: venv\Scripts\activate)
````

3. 패키지 설치

   ```bash
   pip install -r requirements.txt
   playwright install
   ```
4. Streamlit 실행

   ```bash
   streamlit run streamlit_g2b_crawler.py
   ```

---

## ☁️ Streamlit Cloud 배포 구성

Streamlit Cloud를 통해 배포 시 다음 파일들이 필요합니다:

* `requirements.txt`

  ```txt
  streamlit
  playwright
  pandas
  openpyxl
  ```

* `.streamlit/setup.sh`

  ```bash
  #!/bin/bash
  playwright install
  ```

---

## 📝 사용법

1. Streamlit UI에서 검색어 입력 (예: 컴퓨터, 노트북 등)
2. "크롤링 시작" 버튼 클릭
3. 해당 검색어로 G2B 공고를 검색하고 데이터를 Excel로 저장
4. `g2b_result.xlsx` 파일이 생성되며, 기존 파일과 병합 및 중복 제거 기능 포함

---

## ⚠️ 주의사항

* 본 프로젝트는 **G2B 웹사이트 구조**에 의존하며, 사이트 구조가 변경될 경우 일부 기능이 정상 작동하지 않을 수 있습니다.
* 크롤링 대상은 팝업을 닫고 자동으로 검색 및 적용되도록 구성되어 있으며, **GUI 창 없이 headless로 실행**됩니다.
* Streamlit Cloud는 `.bat` 파일을 지원하지 않으므로 모든 실행은 Python 코드로 처리됩니다.

---

## 📂 디렉토리 구조 예시

```
g2b-crawler/
├── streamlit_g2b_crawler.py      # Streamlit 웹 UI + 크롤러 통합 파일
├── requirements.txt              # 패키지 설치 목록
├── .streamlit/
│   └── setup.sh                  # playwright 설치 스크립트
├── g2b_result.xlsx               # 수집된 데이터 파일 (자동 생성)
└── README.md                     # 이 문서
```

---

## 📬 문의

* 이 프로젝트는 개인/팀용 데이터 자동 수집 목적이며, 상업적 이용은 자제해 주세요.
* 기능 개선이나 오류 수정 요청은 GitHub 이슈나 직접 문의 부탁드립니다.

```

---

필요하시다면 이 내용을 직접 `README.md` 파일로 저장하거나, ZIP 배포용으로 구성해드릴 수 있습니다.  
Streamlit Cloud에 업로드할 준비가 되셨으면 `배포용 ZIP 만들어줘`라고 말씀해 주세요!
```
