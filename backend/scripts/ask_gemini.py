"""Gemini 임의 질의 CLI.

사용:
  python scripts/ask_gemini.py "프롬프트"
  python scripts/ask_gemini.py --system "시스템지시" "프롬프트"
  python scripts/ask_gemini.py --file prompt.txt
  python scripts/ask_gemini.py --json --out result.json "프롬프트"
"""
import argparse
import sys
from pathlib import Path

# backend/ 루트를 import 경로에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai  # noqa: E402

from config import get_settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="?", help="질의 내용 (생략 시 --file 사용)")
    parser.add_argument("--file", help="프롬프트 파일 경로")
    parser.add_argument("--system", default="", help="시스템 지시 (선택)")
    parser.add_argument("--model", help="모델명 (기본: settings.gemini_model)")
    parser.add_argument("--json", action="store_true", help="JSON 응답 모드 (response_mime_type=application/json)")
    parser.add_argument("--temp", type=float, default=0.2, help="temperature (기본 0.2)")
    parser.add_argument("--out", help="응답을 저장할 파일")
    args = parser.parse_args()

    if args.file:
        prompt = Path(args.file).read_text(encoding="utf-8")
    elif args.prompt:
        prompt = args.prompt
    else:
        parser.error("prompt 또는 --file 필요")

    settings = get_settings()
    model = args.model or settings.gemini_model
    client = genai.Client(api_key=settings.gemini_api_key)

    config = {"temperature": args.temp}
    if args.system:
        config["system_instruction"] = args.system
    if args.json:
        config["response_mime_type"] = "application/json"

    print(f"[model={model}, temp={args.temp}, json={args.json}]", file=sys.stderr)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    text = response.text
    print(text)

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"\n저장됨: {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
