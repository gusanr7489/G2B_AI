"""제안목차 생성용 Gemini 프롬프트 템플릿"""

OUTLINE_SYSTEM_PROMPT = """당신은 대한민국 공공 IT 컨설팅 제안서 목차 작성 전문가입니다.
RFP 분석 결과를 기반으로 제안서 목차(L1~L4 계층)를 JSON으로 생성합니다.

원칙:
1. 제안요청서에 명시된 평가항목은 반드시 모두 포함합니다.
2. ISP/ISMP 공통 가이드라인(행정안전부/NIA 제9판) 기본 구성을 따릅니다.
3. 평가항목 배점을 반영하여 중요 항목에 더 많은 하위 목차를 배정합니다.
4. ISMP 사업은 고정 5단계 프로세스에 맞춰 작성합니다.
"""

ISP_STRUCTURE = """
## ISP 기본 구성 (가이드라인 기준)
L1-1. 환경분석: 경영환경, 법령·제도, IT환경
L1-2. 현황분석(As-Is): 업무현황, IT현황, 벤치마킹
L1-3. 차이(Gap)분석 → 이슈통합 및 개선과제 도출
L1-4. 정보화 비전 및 전략 수립
L1-5. 목표모델 설계(To-Be): 개선과제 상세화, 업무프로세스, 정보시스템 구조, 데이터 구조, 기술/보안 구조
L1-6. 통합 이행계획: 이행계획, 총구축비(FP기반), 효과분석
"""

ISMP_STRUCTURE = """
## ISMP 기본 구성 (가이드라인 기준)
L1-1. 프로젝트 착수 및 참여자 결정
L1-2. 정보시스템 방향성 수립 (정보화전략 검토, 벤치마킹, 추진범위/방향 정의)
L1-3. 업무 및 정보기술 요건 분석 (업무/IT 현황분석, 요건분석, 요건검토)
L1-4. 정보시스템 구조 및 요건 정의 (아키텍처, 연관성식별, 요건기술서)
L1-5. 정보시스템 구축 사업 이행방안 수립 (사업계획, 분리발주평가, 예산, RFP, 업체선정)
"""

OUTLINE_PROMPT_TEMPLATE = """아래 RFP 분석 결과를 기반으로 제안서 목차를 L1~L4 계층 구조의 JSON으로 생성하세요.

{structure_guide}

## 출력 JSON 스키마

```json
{{
  "is_ismp": true,
  "outline": [
    {{
      "level": 1,
      "number": "1",
      "title": "제안 개요",
      "eval_item": "사업이해도",
      "eval_score": 10,
      "children": [
        {{
          "level": 2,
          "number": "1.1",
          "title": "사업 배경 및 목적",
          "children": [
            {{
              "level": 3,
              "number": "1.1.1",
              "title": "추진 배경",
              "children": []
            }}
          ]
        }}
      ]
    }}
  ]
}}
```

- level: 1~4
- number: 계층 번호 (1, 1.1, 1.1.1, 1.1.1.1)
- title: 목차 제목
- eval_item: 연관 평가항목명 (해당 시)
- eval_score: 연관 평가 배점 (해당 시)
- children: 하위 목차 배열

## RFP 분석 결과

사업 개요: {project_summary}

사업 범위: {project_scope}

평가항목:
{eval_criteria}

요구사항:
{requirements}
"""


def build_outline_prompt(analysis_data: dict, is_ismp: bool = False) -> str:
    """제안목차 생성 프롬프트 구성"""
    structure = ISMP_STRUCTURE if is_ismp else ISP_STRUCTURE

    eval_text = ""
    for item in analysis_data.get("eval_criteria", []):
        eval_text += f"- {item.get('category', '')}/{item.get('item', '')}: {item.get('score', 0)}점\n"

    req_text = ""
    for req in analysis_data.get("requirements", []):
        req_text += f"- [{req.get('id', '')}] {req.get('category', '')}: {req.get('name', '')} — {req.get('description', '')}\n"

    return OUTLINE_PROMPT_TEMPLATE.format(
        structure_guide=structure,
        project_summary=analysis_data.get("project_summary", ""),
        project_scope=analysis_data.get("project_scope", ""),
        eval_criteria=eval_text or "정보 없음",
        requirements=req_text or "정보 없음",
    )
