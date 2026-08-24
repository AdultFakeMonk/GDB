import json
import requests
from common import NOTICE_WEBHOOK_URL, EVENT_WEBHOOK_URL

# ============================================================
# Discord Webhook 전송
# ============================================================

def send_discord(item, image_file=None):
    kind = item["kind"]

    if kind == "공지":
        webhook_url = NOTICE_WEBHOOK_URL
    elif kind == "이벤트":
        webhook_url = EVENT_WEBHOOK_URL
    else:
        raise RuntimeError(f"알 수 없는 항목 종류입니다: {kind}")

    if not webhook_url:
        raise RuntimeError(f"{kind}용 Discord Webhook 설정이 없습니다.")

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
        "title": f"[{kind}] {item['title']}"[:256],
        "url": item["url"],
        "description": f"거상 홈페이지에 새로운 {kind}이(가) 등록되었습니다.",
        "fields": fields,
        "footer": {
            "text": "공식 거상 공지 페이지"
        },
    }

    # 이벤트 전송 시 이미지가 있는 경우
    if image_file:
        filename = image_file[0]
        embed["image"] = {
            "url": f"attachment://{filename}"
        }
        print(f"Discord Embed 이미지 설정: attachment://{filename}")

    payload = {
        "username": "거상 알림 봇",
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