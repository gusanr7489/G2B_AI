"""IT 컨설팅 유형별 목차 생성 레지스트리.

확장 방법:
1. samples/{sample_subdir}/sampleN/analysis.md 파일 추가
2. 아래 OUTLINE_TYPES dict에 항목 추가
"""
from pathlib import Path

SAMPLES_ROOT = Path(__file__).resolve().parent.parent.parent / "samples"

OUTLINE_TYPES: dict[str, dict[str, str]] = {
    "ISP": {
        "label": "정보화전략계획",
        "sample_subdir": "ISP",
        "guideline_summary": (
            "기획재정부 ISP/ISMP 수립 공통가이드 표준 6단계 적용 "
            "(환경분석 → 현황분석 → Gap → 비전·전략 → 목표모델 → 이행계획)"
        ),
    },
    "ISMP": {
        "label": "정보시스템 마스터플랜",
        "sample_subdir": "ISMP",
        "guideline_summary": (
            "ISMP 표준 5단계 프로세스 적용 "
            "(착수 → 방향성 수립 → 요건분석 → 구조·요건 정의 → 이행방안 수립)"
        ),
    },
}


def is_supported(project_type: str | None) -> bool:
    return project_type in OUTLINE_TYPES


def get_label(project_type: str | None) -> str:
    if not project_type:
        return ""
    return OUTLINE_TYPES.get(project_type, {}).get("label", project_type)


def get_guideline(project_type: str | None) -> str:
    if not project_type:
        return ""
    return OUTLINE_TYPES.get(project_type, {}).get("guideline_summary", "")


def supported_types() -> list[dict[str, str]]:
    """프론트 노출용 (code, label)"""
    return [{"code": code, "label": cfg["label"]} for code, cfg in OUTLINE_TYPES.items()]


def _extract_outline_sections(content: str) -> str:
    """analysis.md에서 `## 3.` (제안목차 구조)과 `## 4.` (패턴 분석) 섹션만 추출.

    프롬프트 토큰 절약 목적. 추출 실패 시 원문 반환.
    """
    parts = content.split("\n## ")
    keep: list[str] = []
    for part in parts[1:]:  # parts[0]은 첫 `## ` 이전 헤더 영역
        head = part.split(".", 1)[0].strip()
        if head in ("3", "4"):
            keep.append("## " + part)
    extracted = "\n".join(keep).strip()
    return extracted or content


def load_samples(project_type: str | None) -> list[dict[str, str]]:
    """samples/{sample_subdir}/*/analysis.md 자동 스캔.

    각 샘플은 ## 3 (제안목차 구조) + ## 4 (패턴 분석) 섹션만 포함.
    """
    if not project_type:
        return []
    cfg = OUTLINE_TYPES.get(project_type)
    if not cfg:
        return []
    type_dir = SAMPLES_ROOT / cfg["sample_subdir"]
    if not type_dir.exists():
        return []
    samples: list[dict[str, str]] = []
    for sample_dir in sorted(type_dir.iterdir()):
        if not sample_dir.is_dir():
            continue
        analysis_md = sample_dir / "analysis.md"
        if analysis_md.exists():
            raw = analysis_md.read_text(encoding="utf-8")
            samples.append(
                {
                    "name": sample_dir.name,
                    "content": _extract_outline_sections(raw),
                }
            )
    return samples
