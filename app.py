# -*- coding: utf-8 -*-
"""
AI 문제은행 - Streamlit 앱
Claude Haiku 4.5 + ReportLab PDF 생성
"""
import os
import io
import re
import html
import json
import copy as _copy

import streamlit as st
import anthropic

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, KeepTogether, HRFlowable, PageBreak
)


# ============================================================
# 설정
# ============================================================
MODEL = "claude-haiku-4-5-20251001"
MAX_NAME_LEN = 20

BATCH_SIZE = {
    ("수학", "하 (기초)"): 10, ("수학", "중 (표준)"): 10, ("수학", "상 (심화)"): 7,
    ("수학", "최상 (상위1%)"): 5, ("수학", "혼합"): 7,
    ("국어", "하 (기초)"): 7, ("국어", "중 (표준)"): 5, ("국어", "상 (심화)"): 4,
    ("국어", "최상 (상위1%)"): 3, ("국어", "혼합"): 4,
    ("영어", "하 (기초)"): 7, ("영어", "중 (표준)"): 5, ("영어", "상 (심화)"): 4,
    ("영어", "최상 (상위1%)"): 3, ("영어", "혼합"): 4,
    ("과학", "하 (기초)"): 10, ("과학", "중 (표준)"): 7, ("과학", "상 (심화)"): 5,
    ("과학", "최상 (상위1%)"): 4, ("과학", "혼합"): 5,
    ("사회", "하 (기초)"): 10, ("사회", "중 (표준)"): 7, ("사회", "상 (심화)"): 5,
    ("사회", "최상 (상위1%)"): 4, ("사회", "혼합"): 5,
}

GRADE_OPTIONS = {
    "초등": ["1학년", "2학년", "3학년", "4학년", "5학년", "6학년"],
    "중등": ["1학년", "2학년", "3학년"],
    "고등": ["1학년", "2학년", "3학년"],
}

# 폰트 경로
FONT_PATHS = {
    "regular": [
        "/Users/onipam/Library/Fonts/NanumGothic-Regular.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ],
    "bold": [
        "/Users/onipam/Library/Fonts/NanumGothic-Bold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    ],
}
FONT_REG = "NanumGothic"
FONT_BOLD = "NanumGothicBold"


# ============================================================
# 시스템 프롬프트 (1024 토큰 이상 - 캐싱 대상)
# ============================================================
SYSTEM_PROMPT = """당신은 대한민국 최고 수준의 베테랑 교과서 집필진이자 학원 대표 강사입니다. 초등학교부터 고등학교까지 전 학년 교육과정(2015/2022 개정 교육과정)을 완벽히 숙지하고 있으며, 한국 학생들의 실제 학교 시험, 학원 내신, 경시대회, 수능 유형까지 모두 출제해본 전문가입니다. 학생의 학교급, 학년, 과목, 난이도에 정확히 맞는 양질의 문제를 생성합니다.

[교육과정 세부 기준]
▶ 초등학교
- 1~2학년: 한 자리/두 자리 덧셈뺄셈, 기초 낱말, 그림 해석, 일상 어휘, 간단한 비교/분류
- 3~4학년: 곱셈구구 확장, 나눗셈, 분수 기초, 평면도형, 독해(짧은 설명문/동화), 기초 영단어, 우리 고장
- 5~6학년: 약수와 배수, 분수와 소수의 사칙연산, 비와 비율, 원의 넓이, 비례식, 속력, 설명문/논설문 독해, 영어 문장 구조(be동사/일반동사), 역사(조선 이후), 지리(자연환경/인문환경)
- 초등 문제는 상황이 구체적이어야 하며, 실생활 소재(간식, 운동장, 가족, 마트, 놀이공원 등)를 적극 활용합니다.

▶ 중학교
- 1학년: 정수와 유리수, 문자와 식, 일차방정식, 좌표평면, 통계, 기본 도형, 작도, 평면/입체도형의 성질
- 2학년: 유리수와 순환소수, 식의 계산, 연립방정식, 일차함수, 확률, 삼각형/사각형의 성질, 도형의 닮음
- 3학년: 제곱근과 실수, 인수분해, 이차방정식, 이차함수, 통계, 피타고라스 정리, 삼각비, 원의 성질
- 국어는 문학(시/소설/수필), 비문학(인문/사회/과학/예술), 문법(음운/단어/문장)으로 구성합니다.
- 영어는 문법(시제/to부정사/동명사/분사/관계사/수동태), 어휘, 독해, 어법 어울림으로 출제합니다.
- 과학은 물리, 화학, 생명과학, 지구과학 전 영역을 골고루 다룹니다.
- 사회는 지리, 역사, 일반사회(정치/경제/법)를 포함합니다.

▶ 고등학교
- 1학년(공통수학): 다항식, 방정식과 부등식, 도형의 방정식, 집합과 명제, 함수, 수열, 순열과 조합
- 2학년: 수학Ⅰ(지수로그, 삼각함수, 수열), 수학Ⅱ(함수의 극한과 연속, 미분, 적분)
- 3학년: 미적분, 확률과 통계, 기하 심화
- 국어는 화법/작문/문학/독서/언어와 매체, 수능형 지문(긴 지문 + 복합 선지)을 반영합니다.
- 영어는 수능 유형(대의 파악, 세부 정보, 어법, 어휘, 빈칸 추론, 순서, 삽입, 요약)에 맞춥니다.
- 과학은 통합과학, 물리학Ⅰ/Ⅱ, 화학Ⅰ/Ⅱ, 생명과학Ⅰ/Ⅱ, 지구과학Ⅰ/Ⅱ를 포함합니다.
- 사회는 통합사회, 한국사, 경제, 정치와 법, 세계사, 지리 영역을 포함합니다.

[난이도 기준 - 매우 중요]
▶ 하 (기초): 교과서 예제 수준. 개념 확인과 단순 적용. 1단계 풀이. 정답률 85% 이상 기대.
  예) 수학: "사과 3개와 배 2개가 있을 때 과일은 모두 몇 개입니까?"
▶ 중 (표준): 학교 정기고사 중간 난이도. 기본 개념을 응용한 문제. 2단계 풀이. 정답률 60% 수준.
  예) 수학: 공식을 1~2번 사용하는 활용 문제. 국어: 단락 독해 후 핵심 내용 찾기.
▶ 상 (심화): 상위 10% 학생이 풀 수 있는 수준. 2~3단계 사고력. 여러 개념 융합. 정답률 30% 수준.
  예) 수학: 도형과 방정식을 함께 사용, 조건이 2개 이상. 국어: 긴 지문, 추론/적용 선지.
▶ 최상 (상위1%): 경시대회/영재원/수능 최고 난이도 준비생 수준. 긴 지문(4문장 이상), 조건 중첩(2~3개), 여러 단원 복합, 풀이 3단계 이상. 창의적 사고와 정교한 계산/해석 요구. 정답률 5~10% 수준.
  예) 수학: "A는 B보다 3살 많고 C는 A의 2배보다 4살 적다. 세 사람의 나이 합이 41살일 때, B가 몇 년 후에 현재 C의 나이가 되는지 구하시오."
▶ 혼합: 하 30%, 중 40%, 상 20%, 최상 10% 비율로 골고루 구성합니다.

[수학 과목 특별 규칙 - 과목이 수학일 때만 적용]
1. 단순 계산식 문제 금지 (예: "3+5=?" 형태 절대 금지).
2. 반드시 실생활 스토리 형식의 문장제로 출제합니다. 예: 쇼핑, 여행, 운동, 학교, 가족, 나이, 거리, 시간, 돈 등.
3. 상/최상 난이도는 지문이 최소 3~5문장 이상이어야 하며, 상황을 충분히 설명한 뒤 식을 세울 수 있도록 합니다.
4. 최상 난이도는 조건 2~3개를 중첩한 복합 문장제로 구성합니다.
5. 수식은 유니코드를 사용합니다: √ ∠ ∆ × ÷ ≤ ≥ π ∞ ± ² ³ ₁ ₂. LaTeX 금지.

[출제 원칙]
- 문제는 반드시 학년 교육과정 범위 안에서 출제합니다.
- 주관식은 답이 명확히 떨어지는 형태여야 하며(숫자/단어/짧은 문장), 풀이를 단계별로 상세히 제시합니다.
- 객관식은 5개 선택지(①②③④⑤)를 제공하고, 오답 선지도 그럴듯하게 구성합니다. 정답은 1개만 존재해야 합니다.
- 동일 세트에서 문제 번호가 중복되지 않도록 주의합니다(시작 번호를 반드시 따릅니다).
- 같은 단원이 연속되지 않게 다양한 단원을 골고루 섞습니다.
- 지문(jimen)은 필요한 경우에만 사용하고, 없으면 빈 문자열("")로 둡니다.
- solution(풀이)은 학생이 혼자 이해할 수 있도록 단계별로 자세히 씁니다.

[응답 형식 - 엄수]
반드시 아래의 순수 JSON 하나만 출력합니다. 마크다운 코드 블록(```), 설명 문구, 인사말 등은 절대 포함하지 않습니다. 문자열은 유효한 JSON 문자열이어야 하며, 개행은 \\n으로 이스케이프합니다.

{
  "problems": [
    {
      "no": 1,
      "category": "단원명(예: 분수의 덧셈)",
      "question": "문제 본문",
      "jimen": "지문(없으면 빈 문자열)",
      "options": ["선택지1", "선택지2", "선택지3", "선택지4", "선택지5"],
      "answer": "정답",
      "solution": "단계별 풀이"
    }
  ]
}

- 주관식 문제는 options를 빈 배열([])로 둡니다.
- 객관식 문제는 options 배열에 정확히 5개의 항목을 넣습니다.
- 혼합 유형일 때는 주관식과 객관식을 적절히 섞습니다(대략 5:5).
- answer는 객관식의 경우 선택지의 텍스트(예: "②" 또는 숫자 "12" 등) 또는 번호 기호 중 하나로 명확히 표기합니다.
"""


# ============================================================
# 폰트 등록
# ============================================================
@st.cache_resource
def register_fonts():
    """한글 폰트 등록. 실패 시 에러 반환."""
    reg_path = None
    bold_path = None
    for p in FONT_PATHS["regular"]:
        if os.path.exists(p):
            reg_path = p
            break
    for p in FONT_PATHS["bold"]:
        if os.path.exists(p):
            bold_path = p
            break
    if not reg_path or not bold_path:
        return False, f"한글 폰트를 찾을 수 없습니다.\nRegular: {reg_path}\nBold: {bold_path}"
    try:
        pdfmetrics.registerFont(TTFont(FONT_REG, reg_path))
        pdfmetrics.registerFont(TTFont(FONT_BOLD, bold_path))
        # 폰트 패밀리 등록: ReportLab가 <b> 태그 등 볼드 매핑을 찾을 때 사용
        pdfmetrics.registerFontFamily(
            FONT_REG,
            normal=FONT_REG,
            bold=FONT_BOLD,
            italic=FONT_REG,
            boldItalic=FONT_BOLD,
        )
        pdfmetrics.registerFontFamily(
            FONT_BOLD,
            normal=FONT_BOLD,
            bold=FONT_BOLD,
            italic=FONT_BOLD,
            boldItalic=FONT_BOLD,
        )
        return True, ""
    except Exception as e:
        return False, f"폰트 등록 실패: {e}"


# ============================================================
# API 호출 + 재시도 + 캐싱
# ============================================================
def extract_json(text: str) -> dict:
    """응답 문자열에서 JSON 추출 (마크다운 코드블록 대비)."""
    t = text.strip()
    # ```json ... ``` 또는 ``` ... ``` 제거
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    # 첫 { 부터 마지막 } 까지
    start = t.find("{")
    end = t.rfind("}")
    if start >= 0 and end > start:
        t = t[start:end + 1]
    return json.loads(t)


class PartialGenerationError(RuntimeError):
    """생성 도중 실패 — 이미 생성된 부분 문제를 같이 전달."""

    def __init__(self, message: str, partial):
        super().__init__(message)
        self.partial = partial or []


def korean_api_error(e: Exception) -> str:
    """API 오류 한국어 변환."""
    msg = str(e)
    if "401" in msg or "authentication" in msg.lower() or "invalid x-api-key" in msg.lower():
        return "API 키를 확인해주세요"
    if "429" in msg or "rate" in msg.lower():
        return "요청이 많습니다. 잠시 후 다시 시도해주세요"
    if "500" in msg or "502" in msg or "503" in msg:
        return "서버 오류입니다. 잠시 후 다시 시도해주세요"
    return f"오류가 발생했습니다. 다시 시도해주세요 ({msg[:80]})"


def call_batch(client, school, grade, subject, level, qtype, start_no, count, progress_slot=None, batch_label=""):
    """한 배치 API 호출. 재시도 최대 3회. 성공 시 problems 리스트 반환."""
    user_msg = f"""[요청 정보]
- 학교급: {school}
- 학년: {grade}
- 과목: {subject}
- 난이도: {level}
- 유형: {qtype}
- 시작 문제 번호: {start_no}
- 생성할 문제 수: {count}

위 조건에 맞춰 문제 {count}개를 생성하세요.
문제 번호는 반드시 {start_no}번부터 {start_no + count - 1}번까지 연속으로 매깁니다(중복/누락 금지).
JSON 필드 no 에 해당 번호를 넣습니다.
반드시 순수 JSON만 출력하세요. 마크다운 코드블록 금지.
"""

    last_err = None
    for attempt in range(3):
        try:
            extra = ""
            if attempt > 0:
                extra = "\n\n[재시도 안내] 이전 응답이 유효한 JSON이 아니었습니다. 반드시 순수 JSON만, 마크다운 코드블록 없이 응답하세요. 설명/인사말 금지. { 로 시작해서 } 로 끝나야 합니다."
                if progress_slot is not None:
                    progress_slot.warning(
                        f"⚠️ {batch_label} 응답 재시도 중... ({attempt+1}/3)"
                    )

            resp = client.messages.create(
                model=MODEL,
                max_tokens=8000,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {"role": "user", "content": user_msg + extra}
                ],
                extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            )
            text = resp.content[0].text
            data = extract_json(text)
            problems = data.get("problems", [])
            if not isinstance(problems, list) or len(problems) == 0:
                raise ValueError("problems 비어있음")
            # 번호 보정
            for i, p in enumerate(problems):
                p["no"] = start_no + i
                p.setdefault("category", "")
                p.setdefault("question", "")
                p.setdefault("jimen", "")
                p.setdefault("options", [])
                p.setdefault("answer", "")
                p.setdefault("solution", "")
            return problems[:count]
        except json.JSONDecodeError as e:
            last_err = e
            continue
        except ValueError as e:
            last_err = e
            continue
        except Exception as e:
            # API 오류는 즉시 한국어 메시지로 전환
            raise RuntimeError(korean_api_error(e))
    raise RuntimeError(f"문제 생성에 실패했습니다(JSON 파싱 3회 실패). 잠시 후 다시 시도해주세요.")


def generate_all(client, school, grade, subject, level, qtype, total):
    """전체 문제 배치 생성. 진행 상황 표시.

    실패해도 이미 받은 문제(all_problems)는 유지하기 위해, 예외 시
    (partial_problems, error_message) 튜플을 담은 RuntimeError 를 던진다.
    """
    import time as _time

    batch = BATCH_SIZE.get((subject, level), 5)
    all_problems = []
    next_no = 1
    remaining = total
    total_batches = (total + batch - 1) // batch
    idx = 0
    t0 = _time.time()

    progress_slot = st.empty()
    bar = st.progress(0)

    while remaining > 0:
        idx += 1
        cnt = min(batch, remaining)
        elapsed = int(_time.time() - t0)
        progress_slot.info(
            f"⏳ {idx}/{total_batches} 배치 생성 중... "
            f"({len(all_problems)}/{total} 문제 · 경과 {elapsed}초)"
        )
        try:
            problems = call_batch(
                client, school, grade, subject, level, qtype, next_no, cnt,
                progress_slot=progress_slot,
                batch_label=f"{idx}/{total_batches} 배치",
            )
        except RuntimeError as e:
            # 부분 결과를 함께 전달하여 호출자가 복구 옵션을 제시할 수 있게 함
            raise PartialGenerationError(str(e), all_problems) from None
        all_problems.extend(problems)
        next_no += cnt
        remaining -= cnt
        bar.progress(min(1.0, len(all_problems) / total))

    bar.progress(1.0)
    elapsed = int(_time.time() - t0)
    progress_slot.success(f"✅ 총 {len(all_problems)}문제 생성 완료! ({elapsed}초 소요)")
    return all_problems


# ============================================================
# PDF 생성
# ============================================================
CIRCLE_NUMS = ["①", "②", "③", "④", "⑤"]


def _page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_REG, 9)
    page_num = canvas.getPageNumber()
    total = getattr(doc, "_total_pages", page_num)
    text = f"{page_num}/{total}"
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, text)
    canvas.restoreState()


class NumberedDocTemplate(SimpleDocTemplate):
    """2-pass 빌드로 총 페이지 수를 얻어 '1/3' 형식 표시."""

    def multiBuild(self, flowables, **kwargs):
        # 1-pass: 총 페이지 수 측정 (deepcopy 로 원본 flowables 보호)
        dummy_buf = io.BytesIO()
        dummy = SimpleDocTemplate(
            dummy_buf, pagesize=self.pagesize,
            leftMargin=self.leftMargin, rightMargin=self.rightMargin,
            topMargin=self.topMargin, bottomMargin=self.bottomMargin,
        )
        dummy.build(_copy.deepcopy(flowables))
        self._total_pages = dummy.page
        SimpleDocTemplate.build(
            self, flowables, onFirstPage=self._on_page, onLaterPages=self._on_page
        )

    def _on_page(self, canvas, doc):
        doc._total_pages = getattr(self, "_total_pages", doc.page)
        _page_number(canvas, doc)


def _styles():
    title = ParagraphStyle(
        "Title", fontName=FONT_BOLD, fontSize=20, leading=26,
        alignment=1, textColor=colors.HexColor("#111827"), wordWrap="CJK",
        splitLongWords=True,
    )
    subtitle = ParagraphStyle(
        "Sub", fontName=FONT_REG, fontSize=11, leading=16,
        alignment=1, textColor=colors.HexColor("#374151"), wordWrap="CJK",
        splitLongWords=True,
    )
    category = ParagraphStyle(
        "Cat", fontName=FONT_BOLD, fontSize=10, leading=14,
        textColor=colors.HexColor("#2563EB"), wordWrap="CJK",
        splitLongWords=True,
    )
    question = ParagraphStyle(
        "Q", fontName=FONT_BOLD, fontSize=12, leading=18,
        textColor=colors.HexColor("#111827"), wordWrap="CJK",
        splitLongWords=True, spaceBefore=2, spaceAfter=4,
    )
    jimen = ParagraphStyle(
        "J", fontName=FONT_REG, fontSize=10.5, leading=17,
        textColor=colors.HexColor("#1F2937"), wordWrap="CJK",
        splitLongWords=True,
        leftIndent=8, rightIndent=8, spaceBefore=4, spaceAfter=4,
        backColor=colors.HexColor("#F3F4F6"),
        borderPadding=8,
    )
    option = ParagraphStyle(
        "Opt", fontName=FONT_REG, fontSize=11, leading=16,
        textColor=colors.HexColor("#1F2937"), wordWrap="CJK",
        splitLongWords=True, leftIndent=10,
    )
    answer_line = ParagraphStyle(
        "Ans", fontName=FONT_REG, fontSize=11, leading=16,
        textColor=colors.HexColor("#374151"), wordWrap="CJK",
        splitLongWords=True, leftIndent=10, spaceBefore=4,
    )
    answer_red = ParagraphStyle(
        "AnsR", fontName=FONT_BOLD, fontSize=11.5, leading=17,
        textColor=colors.HexColor("#CC0000"), wordWrap="CJK",
        splitLongWords=True, spaceBefore=2,
    )
    solution_blue = ParagraphStyle(
        "Sol", fontName=FONT_REG, fontSize=10.5, leading=17,
        textColor=colors.HexColor("#0055AA"), wordWrap="CJK",
        splitLongWords=True, spaceBefore=2, spaceAfter=6,
    )
    return dict(
        title=title, subtitle=subtitle, category=category, question=question,
        jimen=jimen, option=option, answer_line=answer_line,
        answer_red=answer_red, solution_blue=solution_blue,
    )


def _esc(s: str) -> str:
    if s is None:
        return ""
    return html.escape(str(s)).replace("\n", "<br/>")


def build_problem_pdf(student, school, grade, subject, level, qtype, count, problems) -> bytes:
    buf = io.BytesIO()
    doc = NumberedDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2.5 * cm,
        title="문제지",
    )
    s = _styles()
    story = []

    display_name = (student or "").strip()[:MAX_NAME_LEN]

    story.append(Paragraph(f"{_esc(school)} {_esc(grade)} {_esc(subject)} 문제지", s["title"]))
    story.append(Spacer(1, 0.2 * cm))
    sub = (
        f"난이도: {_esc(level)} | 유형: {_esc(qtype)} | {count}문제 | "
        f"이름: {_esc(display_name) if display_name else '_______________'}"
    )
    story.append(Paragraph(sub, s["subtitle"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB")))
    story.append(Spacer(1, 0.4 * cm))

    for p in problems:
        block = []
        cat = p.get("category", "").strip()
        no = p.get("no", "")
        q = p.get("question", "").strip()
        jimen = (p.get("jimen") or "").strip()
        options = p.get("options") or []

        if cat:
            block.append(Paragraph(f"[{_esc(cat)}]", s["category"]))
        block.append(Paragraph(f"{no}. {_esc(q)}", s["question"]))
        if jimen:
            block.append(Paragraph(f"▶ {_esc(jimen)}", s["jimen"]))

        if options:
            for i, opt in enumerate(options[:5]):
                mark = CIRCLE_NUMS[i]
                block.append(Paragraph(f"{mark} {_esc(opt)}", s["option"]))
        else:
            block.append(Paragraph("정 답: _________________________", s["answer_line"]))

        block.append(Spacer(1, 0.35 * cm))
        story.append(KeepTogether(block))

    doc.multiBuild(story)
    return buf.getvalue()


def build_answer_pdf(student, school, grade, subject, level, qtype, count, problems) -> bytes:
    buf = io.BytesIO()
    doc = NumberedDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2.5 * cm,
        title="해설 답안지",
    )
    s = _styles()
    story = []

    display_name = (student or "").strip()[:MAX_NAME_LEN]

    story.append(Paragraph(f"{_esc(school)} {_esc(grade)} {_esc(subject)} 해설 답안지", s["title"]))
    story.append(Spacer(1, 0.2 * cm))
    sub = (
        f"난이도: {_esc(level)} | 유형: {_esc(qtype)} | {count}문제 | "
        f"이름: {_esc(display_name) if display_name else '_______________'}"
    )
    story.append(Paragraph(sub, s["subtitle"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#16A34A")))
    story.append(Spacer(1, 0.4 * cm))

    for p in problems:
        block = []
        cat = p.get("category", "").strip()
        no = p.get("no", "")
        q = p.get("question", "").strip()
        ans = (p.get("answer") or "").strip()
        sol = (p.get("solution") or "").strip()

        if cat:
            block.append(Paragraph(f"[{_esc(cat)}]", s["category"]))
        block.append(Paragraph(f"{no}. {_esc(q)}", s["question"]))
        block.append(Paragraph(f"정답: {_esc(ans)}", s["answer_red"]))
        if sol:
            block.append(Paragraph(f"풀이: {_esc(sol)}", s["solution_blue"]))
        block.append(Spacer(1, 0.35 * cm))
        story.append(KeepTogether(block))

    doc.multiBuild(story)
    return buf.getvalue()


# ============================================================
# Streamlit UI
# ============================================================
def on_school_change():
    """학교급 변경 시 학년을 해당 학교급의 1학년으로 리셋."""
    new_school = st.session_state.get("school", "초등")
    st.session_state["grade"] = GRADE_OPTIONS[new_school][0]


def reset_results():
    for k in ("problems", "pdf_q", "pdf_a", "meta"):
        if k in st.session_state:
            del st.session_state[k]


def main():
    st.set_page_config(page_title="AI 문제은행", page_icon="📚", layout="centered")
    st.title("📚 AI 문제은행")
    st.caption("Claude Haiku 4.5 기반 · 초중고 전 학년 · 맞춤 난이도 · PDF 자동 생성")

    # 폰트 등록
    ok, msg = register_fonts()
    if not ok:
        st.error(f"❌ {msg}\nPDF 생성을 위해 나눔고딕 폰트가 필요합니다.")
        st.stop()

    # API 키
    try:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        st.error("❌ st.secrets['ANTHROPIC_API_KEY'] 가 설정되지 않았습니다.")
        st.stop()

    # 세션 기본값
    st.session_state.setdefault("school", "초등")
    st.session_state.setdefault("grade", GRADE_OPTIONS["초등"][0])

    # --- 입력 폼 ---
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            student = st.text_input("학생 이름", max_chars=MAX_NAME_LEN, placeholder="최대 20자")
            school = st.selectbox(
                "학교급", list(GRADE_OPTIONS.keys()), key="school",
                on_change=on_school_change,
            )
        with col2:
            grade = st.selectbox(
                "학년", GRADE_OPTIONS[st.session_state["school"]], key="grade"
            )
            subject = st.selectbox("과목", ["수학", "국어", "영어", "과학", "사회"])

        col3, col4, col5 = st.columns(3)
        with col3:
            count = st.selectbox("문제 수", [10, 20, 30], index=0)
        with col4:
            level = st.selectbox(
                "난이도",
                ["하 (기초)", "중 (표준)", "상 (심화)", "최상 (상위1%)", "혼합"],
                index=1,
            )
        with col5:
            qtype = st.selectbox("문제 유형", ["주관식", "객관식 5지선다", "혼합"], index=0)

        is_generating = st.session_state.get("generating", False)
        generate = st.button(
            "🚀 문제지 생성" if not is_generating else "⏳ 생성 중...",
            type="primary", use_container_width=True,
            disabled=is_generating,
        )

    # --- 생성 ---
    if generate:
        reset_results()
        st.session_state["generating"] = True
        student_safe = (student or "").strip()[:MAX_NAME_LEN]

        client = anthropic.Anthropic(api_key=api_key)

        problems = None
        try:
            try:
                problems = generate_all(
                    client, school, grade, subject, level, qtype, count
                )
            except PartialGenerationError as e:
                partial = e.partial
                if partial:
                    st.warning(
                        f"⚠️ 생성 중 오류: {e}\n"
                        f"이미 생성된 **{len(partial)}문제**로 PDF를 만듭니다."
                    )
                    problems = partial
                    count = len(partial)
                else:
                    st.error(f"❌ {e}")
                    st.stop()
            except RuntimeError as e:
                st.error(f"❌ {e}")
                st.stop()
            except Exception as e:
                st.error(f"❌ {korean_api_error(e)}")
                st.stop()
        finally:
            st.session_state["generating"] = False

        # 생성 직후 PDF 미리 제작 → 세션 저장
        with st.spinner("PDF 생성 중..."):
            try:
                pdf_q = build_problem_pdf(
                    student_safe, school, grade, subject, level, qtype, count, problems
                )
                pdf_a = build_answer_pdf(
                    student_safe, school, grade, subject, level, qtype, count, problems
                )
            except Exception as e:
                st.error(f"❌ PDF 생성 실패: {e}")
                st.stop()

        st.session_state["problems"] = problems
        st.session_state["pdf_q"] = pdf_q
        st.session_state["pdf_a"] = pdf_a
        st.session_state["meta"] = dict(
            student=student_safe, school=school, grade=grade, subject=subject,
            level=level, qtype=qtype, count=count,
        )

    # --- 결과 화면 ---
    if "problems" in st.session_state:
        meta = st.session_state["meta"]
        problems = st.session_state["problems"]
        pdf_q = st.session_state["pdf_q"]
        pdf_a = st.session_state["pdf_a"]

        st.markdown("---")
        st.subheader(
            f"📄 {meta['school']} {meta['grade']} {meta['subject']} — {meta['level']} · {meta['qtype']} · {meta['count']}문제"
        )

        name_part = meta["student"] or "student"
        # 파일명에서 파일시스템에 안전하지 않은 문자 치환
        safe_name = re.sub(r"[^\w가-힣]", "", name_part) or "student"
        fname_q = f"{safe_name}_{meta['subject']}_{meta['grade']}_문제지.pdf"
        fname_a = f"{safe_name}_{meta['subject']}_{meta['grade']}_정답지.pdf"

        dc1, dc2, dc3 = st.columns([1, 1, 1])
        with dc1:
            st.download_button(
                "📥 문제지 PDF", data=pdf_q, file_name=fname_q,
                mime="application/pdf", use_container_width=True,
            )
        with dc2:
            st.download_button(
                "📥 정답지 PDF", data=pdf_a, file_name=fname_a,
                mime="application/pdf", use_container_width=True,
            )
        with dc3:
            if st.button("🔄 새로 생성", use_container_width=True):
                reset_results()
                st.rerun()

        show_ans = st.toggle("정답 보기", value=False)

        st.markdown("### 📝 문제 미리보기")
        for p in problems:
            cat = p.get("category", "")
            no = p.get("no", "")
            q = p.get("question", "")
            jimen = (p.get("jimen") or "").strip()
            options = p.get("options") or []
            ans = p.get("answer", "")
            sol = p.get("solution", "")

            header = f"**[{cat}] {no}. {q}**" if cat else f"**{no}. {q}**"
            st.markdown(header)
            if jimen:
                st.info(jimen)
            if options:
                for i, opt in enumerate(options[:5]):
                    mark = CIRCLE_NUMS[i]
                    st.markdown(f"&nbsp;&nbsp;{mark} {opt}", unsafe_allow_html=True)
            else:
                st.markdown("&nbsp;&nbsp;정 답: _________________________", unsafe_allow_html=True)

            if show_ans:
                st.markdown(
                    f"<span style='color:#CC0000;font-weight:700;'>정답: {html.escape(str(ans))}</span>",
                    unsafe_allow_html=True,
                )
                if sol:
                    st.markdown(
                        f"<span style='color:#0055AA;'>풀이: {html.escape(str(sol))}</span>",
                        unsafe_allow_html=True,
                    )
            st.markdown("---")


if __name__ == "__main__":
    main()
