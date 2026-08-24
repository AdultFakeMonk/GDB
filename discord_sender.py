import json
import requests
from common import NOTICE_WEBHOOK_URL, EVENT_WEBHOOK_URL

# ============================================================
# Discord Webhook ?꾩넚
# ============================================================

def send_discord(item, image_file=None):
    kind = item["kind"]

    if kind == "怨듭?":
        webhook_url = NOTICE_WEBHOOK_URL
    elif kind == "?대깽??:
        webhook_url = EVENT_WEBHOOK_URL
    else:
        raise RuntimeError(f"?????녿뒗 ?뚮┝ 醫낅쪟?낅땲?? {kind}")

    if not webhook_url:
        raise RuntimeError(f"{kind}??Discord Webhook ?섍꼍蹂?섍? ?놁뒿?덈떎.")

    fields = []

    # 怨듭? ?깅줉??    if kind == "怨듭?" and item.get("date"):
        fields.append({
            "name": "?깅줉??,
            "value": item["date"],
            "inline": False,
        })

    # ?대깽??湲곌컙
    if kind == "?대깽?? and item.get("period"):
        fields.append({
            "name": "?대깽??湲곌컙",
            "value": item["period"],
            "inline": False,
        })

    embed = {
        "title": f"[{kind}] {item['title']}"[:256],
        "url": item["url"],
        "description": f"嫄곗긽 ?덊럹?댁?????{kind}??媛) ?깅줉?섏뿀?듬땲??",
        "fields": fields,
        "footer": {
            "text": "泥쒗븯?쒖씪??嫄곗긽 怨듭떇 ?덊럹?댁?"
        },
    }

    # ?대깽???먮낯 ????대?吏媛 泥⑤???寃쎌슦
    if image_file:
        filename = image_file[0]
        embed["image"] = {
            "url": f"attachment://{filename}"
        }
        print(f"Discord Embed ?대?吏 ?곌껐: attachment://{filename}")

    payload = {
        "username": "嫄곗긽 ?뚯떇 ?뚮┝",
        "embeds": [embed],
    }

    # ?대?吏媛 ?덉쑝硫??뚯씪 泥⑤?
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
    print("Discord ?꾩넚 ?깃났")