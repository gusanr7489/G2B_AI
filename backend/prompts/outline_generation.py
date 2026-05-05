"""제안목차 생성 프롬프트 (유형별 동적 구성)"""
from services.outline_types import get_guideline, get_label, load_samples


OUTLINE_SYSTEM_PROMPT = """당신은 대한민국 공공 IT 컨설팅 제안서 목차 작성 전문가입니다.
RFP 분석 결과와 동일 유형의 실제 제안 샘플을 바탕으로 제안서 정보를 JSON으로 생성합니다.

원칙:
1. 제안요청서 평가항목은 모두 목차에 반영합니다.
2. 사업 유형의 표준 가이드라인을 준수합니다.
3. 평가배점이 높은 항목에 더 깊은 하위 목차를 배정합니다.
4. 첨부된 샘플의 트리 구조·깊이·번호 체계를 학습해 동일한 형식을 따릅니다.
5. 페이지수는 평가배점 비례로 분배하며 총합 200p 내외로 합니다.
6. 분석된 RFP 요구사항을 빠짐없이 requirements 섹션에 정리합니다.
"""


OUTLINE_PROMPT_TEMPLATE = """## 사업 유형
{type_label}

## 가이드라인
{guideline}

## 참고 샘플 (동일 유형의 실제 제안서 분석본)

{samples}

---

## 분석 대상 RFP

### 사업 메타정보
- 발주기관: {issuing_org}
- 마감일시: {deadline}
- 사업기간: {project_duration}
- 추정가격: {estimated_price}
- 배정예산: {allocated_budget}
- 계약방법: {contract_method}

### 사업 개요
{project_summary}

### 사업 범위
{project_scope}

### 평가항목
{eval_criteria}

### 요구사항
{requirements}

### 참가 자격
{qualification}

---

## 출력 JSON 스키마

반드시 아래 스키마 그대로 출력하세요:

```json
{{
  "main": {{
    "project_name": "사업명",
    "client": "고객(발주처) — 부서/담당자 포함 가능",
    "duration": "사업기간 (예: '6개월', '180일')",
    "amount": "용역금액 (예: '200,000,000원')",
    "submit_date": "제출일 (YYYY-MM-DD HH:MM 또는 빈 문자열)",
    "submit_place": "제출장소",
    "notes": "비고/특이사항 (여러 줄 가능)"
  }},
  "outline": [
    {{
      "code": "Ⅰ",
      "title": "일반현황",
      "page_count": 13,
      "eval_mapping": "정량평가-경영상태 5점",
      "children": [
        {{
          "level": 1,
          "number": "1",
          "title": "제안사 일반현황",
          "page_count": 5,
          "eval_mapping": null,
          "children": [
            {{
              "level": 2,
              "number": "1.1",
              "title": "현황 및 연혁",
              "page_count": 1,
              "eval_mapping": null,
              "children": []
            }}
          ]
        }}
      ]
    }}
  ],
  "requirements": [
    {{
      "category": "컨설팅 요구사항",
      "code": "CSR-001",
      "name": "환경분석 수행 방안",
      "definition": "한 줄 정의",
      "detail": "상세 설명",
      "output": "산출물명",
      "note": ""
    }}
  ]
}}
```

규칙:
- outline 최상위(대분류)는 4~7개 (Ⅰ~Ⅳ 또는 Ⅰ~Ⅶ). code 컬럼에 로마 숫자 사용.
- children에서 level 1~4 활용, number는 "1", "1.1", "1.1.1", "1.1.1.1" 형태.
- page_count는 정수 또는 null. 합계 약 200p.
- eval_mapping은 평가항목명+배점 (예: "정량평가-PM실적 7.2점") 또는 null.
- requirements는 분석된 RFP 요구사항을 그대로 옮김. 빠짐없이.
- 작성자(담당자) 정보는 만들지 말고 비워두세요. 사용자가 엑셀에서 직접 기입합니다.
"""


def build_outline_prompt(analysis_data: dict, project_type: str) -> str:
    samples = load_samples(project_type)
    if samples:
        samples_text = "\n\n---\n\n".join(
            f"### 샘플 {i + 1}: {s['name']}\n\n{s['content']}"
            for i, s in enumerate(samples)
        )
    else:
        samples_text = "(샘플 없음)"

    basic = analysis_data.get("basic_info") or {}

    eval_text = ""
    for item in analysis_data.get("eval_criteria") or []:
        eval_text += (
            f"- {item.get('category', '')}/{item.get('item', '')}: "
            f"{item.get('score', 0)}점\n"
        )

    req_text = ""
    raw_reqs = analysis_data.get("requirements")
    if isinstance(raw_reqs, dict) and "groups" in raw_reqs:
        for group in raw_reqs.get("groups", []):
            req_text += f"\n[{group.get('group_name', '')}]\n"
            for r in group.get("items", []):
                desc = (r.get("description") or "")[:140]
                req_text += f"- [{r.get('id', '')}] {r.get('name', '')}: {desc}\n"
    elif isinstance(raw_reqs, list):
        for r in raw_reqs:
            desc = (r.get("description") or "")[:140]
            req_text += f"- [{r.get('id', '')}] {r.get('name', '')}: {desc}\n"

    return OUTLINE_PROMPT_TEMPLATE.format(
        type_label=get_label(project_type),
        guideline=get_guideline(project_type),
        samples=samples_text,
        project_summary=analysis_data.get("project_summary")
        or basic.get("project_summary", ""),
        project_scope=analysis_data.get("project_scope")
        or basic.get("project_scope", ""),
        eval_criteria=eval_text or "정보 없음",
        requirements=req_text or "정보 없음",
        qualification=analysis_data.get("qualification") or "",
        issuing_org=basic.get("issuing_org", ""),
        deadline=basic.get("deadline", ""),
        project_duration=basic.get("project_duration", ""),
        estimated_price=basic.get("estimated_price", ""),
        allocated_budget=basic.get("allocated_budget", ""),
        contract_method=basic.get("contract_method", ""),
    )
