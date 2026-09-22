import json
import os
import requests
from common import NOTICE_WEBHOOK_URL, EVENT_WEBHOOK_URL

KAKAO_NOTIFY_URL = os.environ.get(
    "KAKAO_NOTIFY_URL",
    "https://pose-volumes-dress-concern.trycloudflare.com/api/notify",
).strip()

def send_kakao(item):
    if not KAKAO_NOTIFY_URL:
        return
    try:
        payload = {
            "kind": item.get("kind"),
            "title": item.get("title"),
            "url": item.get("url"),
            "date_or_period": item.get("date") or item.get("period"),
        }
        resp = requests.post(KAKAO_NOTIFY_URL, json=payload, timeout=10)
        resp.raise_for_status()
        print(f"KakaoTalk 전송 성공: [{item.get('kind')}] {item.get('title')}")
    except Exception as e:
        print(f"KakaoTalk 전송 실패: {e}")

# ============================================================
# Discord Webhook 전송
# ============================================================

def send_discord(item, image_file=None):
    # 1. 카카오톡으로 동시 전송
    send_kakao(item)

    kind = item["kind"]

    if kind == "공지":
        webhook_url = NOTICE_WEBHOOK_URL
    elif kind == "이벤트":
        webhook_url = EVENT_WEBHOOK_URL
    else:
        raise RuntimeError(
            f"알 수 없는 알림 종류입니다: "
            f"{kind}"
        )

    if not webhook_url:
        raise RuntimeError(
            f"{kind}용 Discord Webhook "
            "환경변수가 없습니다."
        )

    fields = []

    # 공지 등록일
    if kind == "공지" and item.get("date"):
        fields.append({
            "name": "등록일",
            "value": item["date"],
            "inline": False,
        })

    # 이벤트 기간
    if kind == "이벤트" and item.get("period"):
        fields.append({
            "name": "이벤트 기간",
            "value": item["period"],
            "inline": False,
        })

    embed = {
        "title": (
            f"[{kind}] "
            f"{item['title']}"
        )[:256],
        "url": item["url"],
        "description": (
            f"거상 홈페이지에 새 "
            f"{kind}이(가) 등록되었습니다."
        ),
        "fields": fields,
        "footer": {
            "text": (
                "천하제일상 거상 "
                "공식 홈페이지"
            )
        },
    }

    # 이미지가 있는 경우 embed에 연결
    if image_file:
        filename = image_file[0]
        embed["image"] = {
            "url": f"attachment://{filename}"
        }
        print(
            "Discord Embed 이미지 연결: "
            f"attachment://{filename}"
        )
    else:
        if item.get("image_url"):
            print(
                "이미지 다운로드 실패. "
                "이미지 없이 Discord 전송"
            )

    payload = {
        "username": "거상 소식 알림",
        "embeds": [embed],
    }

    # 이미지가 있으면 파일 첨부
    if image_file:
        filename, image_bytes, content_type = image_file
        files = {
            "file": (filename, image_bytes, content_type)
        }
        data = {
            "payload_json": json.dumps(payload, ensure_ascii=False)
        }
        response = requests.post(
            webhook_url,
            data=data,
            files=files,
            timeout=30,
        )
    else:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=30,
        )

    response.raise_for_status()
    print("Discord 전송 성공")