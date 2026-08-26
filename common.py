import json
import os
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import urllib3


urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


# ============================================================
# 기본 설정
# ============================================================

NOTICE_URL = (
    "https://www.gersang.co.kr/"
    "news/notice.gs?GSbid=1001"
)

EVENT_URL = (
    "https://www.gersang.co.kr/"
    "news/event.gs"
)

STATE_FILE = Path("last_seen.json")


NOTICE_WEBHOOK_URL = os.environ.get(
    "DISCORD_NOTICE_WEBHOOK_URL",
    "",
).strip()

EVENT_WEBHOOK_URL = os.environ.get(
    "DISCORD_EVENT_WEBHOOK_URL",
    "",
).strip()

MAX_SEND_PER_RUN = int(
    os.environ.get(
        "MAX_SEND_PER_RUN",
        "5",
    )
)



# HTTP 헤더
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": (
        "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    ),
    "Referer": (
        "https://www.gersang.co.kr/"
    ),
}


# 거상 홈페이지 가져오기
# ============================================================

def fetch_html(url):
    last_error = None

    for attempt in range(5):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=30,
                verify=False,
            )

            response.raise_for_status()

            if (
                not response.encoding
                or response.encoding.lower()
                == "iso-8859-1"
            ):
                response.encoding = (
                    response.apparent_encoding
                    or "utf-8"
                )

            print(
                f"페이지 접속 성공: {url} "
                f"(HTTP {response.status_code}, "
                f"{len(response.text)} bytes)"
            )

            return response.text

        except requests.RequestException as e:
            last_error = e

            print(
                f"접속 실패 "
                f"({attempt + 1}/5): {e}"
            )

            if attempt < 4:
                wait_seconds = (
                    5 * (attempt + 1)
                )

                print(
                    f"{wait_seconds}초 후 "
                    "다시 시도합니다."
                )

                time.sleep(
                    wait_seconds
                )

    raise last_error



# ============================================================

def normalize_image_url(
    image_url,
    base_url,
):
    if not image_url:
        return None

    image_url = image_url.strip()

    if not image_url:
        return None

    if image_url.lower().startswith(
        "data:"
    ):
        return None

    if image_url.lower().startswith(
        "javascript:"
    ):
        return None

    if image_url.startswith("//"):
        image_url = (
            "https:"
            + image_url
        )

    full_url = urljoin(
        base_url,
        image_url,
    )

    parsed = urlparse(
        full_url
    )

    if parsed.scheme not in {
        "http",
        "https",
    }:
        return None

    return full_url



# ============================================================

def load_state():
    default = {
        "notice_last_id": None,
        "event_seen_urls": [],
    }

    if not STATE_FILE.exists():
        return default

    try:
        data = json.loads(
            STATE_FILE.read_text(
                encoding="utf-8"
            )
        )

        return {
            "notice_last_id": data.get(
                "notice_last_id"
            ),
            "event_seen_urls": list(
                data.get(
                    "event_seen_urls",
                    [],
                )
            ),
        }

    except Exception as e:
        print(
            f"상태 파일 읽기 실패: {e}"
        )

        return default


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


