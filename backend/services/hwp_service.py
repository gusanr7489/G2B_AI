import asyncio
import io
import logging
import zipfile

import httpx

from config import get_settings

logger = logging.getLogger(__name__)


async def convert_hwp(file_bytes: bytes, file_name: str = "document.hwp") -> dict:
    """
    리브레AI API로 HWP → HTML + MD 변환.
    비동기 플로우: POST(업로드) → 폴링 → ZIP 다운로드 → 추출.

    Returns:
        {"html": str, "md": str, "metadata": dict | None}
    """
    settings = get_settings()
    base_url = settings.libreai_api_url
    headers = {"X-API-Key": settings.libreai_api_key}

    async with httpx.AsyncClient(timeout=60) as client:
        # Step 1: 변환 요청
        files = {"file": (file_name, file_bytes)}
        resp = await client.post(f"{base_url}/convert", headers=headers, files=files)
        resp.raise_for_status()
        job = resp.json()
        job_id = job["job_id"]
        logger.info(f"HWP 변환 요청 완료: job_id={job_id}")

        # Step 2: 상태 폴링 (최대 60초)
        for _ in range(120):
            await asyncio.sleep(0.5)
            status_resp = await client.get(
                f"{base_url}/jobs/{job_id}", headers=headers
            )
            status_resp.raise_for_status()
            status_data = status_resp.json()

            if status_data.get("status") == "completed":
                break
            if status_data.get("status") == "failed":
                raise RuntimeError(f"HWP 변환 실패: {status_data}")
        else:
            raise TimeoutError("HWP 변환 타임아웃 (60초)")

        # Step 3: ZIP 다운로드
        dl_resp = await client.get(
            f"{base_url}/download/{job_id}", headers=headers
        )
        dl_resp.raise_for_status()

        # ZIP 파싱
        return _extract_zip(dl_resp.content)


def _extract_zip(zip_bytes: bytes) -> dict:
    """ZIP에서 content.html, content.md, metadata.json 추출"""
    result = {"html": "", "md": "", "metadata": None}

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if name.endswith("content.html"):
                result["html"] = zf.read(name).decode("utf-8", errors="replace")
            elif name.endswith("content.md"):
                result["md"] = zf.read(name).decode("utf-8", errors="replace")
            elif name.endswith("metadata.json"):
                import json
                result["metadata"] = json.loads(zf.read(name))

    return result


async def download_and_convert(file_url: str, file_name: str = "") -> dict:
    """URL에서 파일 다운로드 → 확장자에 따라 변환 처리"""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(file_url)
        resp.raise_for_status()

    file_bytes = resp.content
    content_type = resp.headers.get("content-type", "")
    if not file_name:
        file_name = file_url.split("/")[-1].split("?")[0]

    # HWP / PDF → 리브레AI API 변환
    if file_name.lower().endswith((".hwp", ".pdf")) or any(
        k in content_type.lower() for k in ("hwp", "pdf")
    ):
        return await convert_hwp(file_bytes, file_name)

    return {"html": "", "md": f"[지원하지 않는 형식: {file_name}]", "metadata": None}
