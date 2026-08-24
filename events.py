import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests
from common import EVENT_URL, HEADERS, MAX_SEND_PER_RUN, fetch_html, normalize_image_url
from discord_sender import send_discord

# ============================================================
# ?대깽??URL ?뺤씤
# ============================================================

def normalize_event_url(href):
    full_url = urljoin(EVENT_URL, href)
    parsed = urlparse(full_url)

    if parsed.scheme not in {"http", "https"}:
        return None

    if parsed.netloc.lower() not in {"gersang.co.kr", "www.gersang.co.kr"}:
        return None

    if not parsed.path.lower().startswith("/event/"):
        return None

    return parsed._replace(query="", fragment="").geturl()

# ============================================================
# CSS background-image?먯꽌 URL 異붿텧
# ============================================================

def extract_background_image(element):
    style = (element.get("style") or "").strip()
    if not style:
        return None

    match = re.search(
        r"""background-image\s*:\s*url\s*\(\s*[\'"]?([^\'"]+)[\'"]?\s*\)""",
        style,
        flags=re.IGNORECASE | re.VERBOSE,
    )
    if match:
        return match.group(1).strip()
    return None

# ============================================================
# ?대깽??????대?吏 異붿텧
# ============================================================

def extract_event_image(box, base_url):
    image_attributes = [
        "src",
        "data-src",
        "data-original",
        "data-lazy-src",
        "data-image",
        "data-original-src",
    ]

    # img ?쒓렇
    for img in box.select("img"):
        for attr in image_attributes:
            image_url = normalize_image_url(img.get(attr), base_url)
            if image_url:
                return image_url

    # source srcset
    for source in box.select("source"):
        srcset = (source.get("srcset") or "").strip()
        if srcset:
            first_url = srcset.split(",")[0].strip().split(" ")[0]
            image_url = normalize_image_url(first_url, base_url)
            if image_url:
                return image_url

    # background-image
    for element in box.select("[style]"):
        raw_url = extract_background_image(element)
        image_url = normalize_image_url(raw_url, base_url)
        if image_url:
            return image_url

    return None

# ============================================================
# ?대깽???곸꽭?섏씠吏?먯꽌 ?대?吏 李얘린
# ============================================================

def extract_detail_page_image(event_url):
    print("紐⑸줉?먯꽌 ?대깽???대?吏瑜?李얠? 紐삵뻽?듬땲??")
    print(f"?곸꽭?섏씠吏 ?대?吏 ?뺤씤: {event_url}")

    try:
        html = fetch_html(event_url)
    except Exception as e:
        print(f"?대깽???곸꽭?섏씠吏 ?묒냽 ?ㅽ뙣: {e}")
        return None

    soup = BeautifulSoup(html, "html.parser")
    selectors = [
        ".event-view",
        ".event-detail",
        ".view-content",
        ".contents",
        ".content",
        ".board-view",
        "article",
        "body",
    ]

    for selector in selectors:
        container = soup.select_one(selector)
        if container is None:
            continue

        image_url = extract_event_image(container, event_url)
        if image_url:
            return image_url

    return None

# ============================================================
# ?대깽???대?吏 ?ㅼ슫濡쒕뱶
# ============================================================

def download_event_image(image_url, event_url):
    print("")
    print("?대깽???대?吏 ?ㅼ슫濡쒕뱶 ?쒖옉")
    print(f"?대?吏 URL: {image_url}")

    image_headers = dict(HEADERS)
    image_headers["Referer"] = event_url

    try:
        response = requests.get(
            image_url,
            headers=image_headers,
            timeout=30,
            verify=False,
        )
        response.raise_for_status()

        if not response.content:
            raise RuntimeError("?대?吏 ?묐떟 ?댁슜??鍮꾩뼱 ?덉뒿?덈떎.")

        content_type = (
            response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        )

        print(f"?대?吏 ?ㅼ슫濡쒕뱶 ?깃났 (HTTP {response.status_code})")
        print(f"Content-Type: {content_type}")
        print(f"?대?吏 ?ш린: {len(response.content)} bytes")

        # ?뺤옣??寃곗젙
        extension = ".jpg"
        if content_type == "image/png":
            extension = ".png"
        elif content_type == "image/webp":
            extension = ".webp"
        elif content_type == "image/gif":
            extension = ".gif"
        elif content_type in {"image/jpeg", "image/jpg"}:
            extension = ".jpg"

        filename = "gersang_event_image" + extension
        return (filename, response.content, content_type or "image/jpeg")

    except requests.RequestException as e:
        print(f"?대깽???대?吏 ?ㅼ슫濡쒕뱶 ?ㅽ뙣: {e}")
        return None

# ============================================================
# ?대깽???뚯떛
# ============================================================

def parse_events(html):
    soup = BeautifulSoup(html, "html.parser")
    events = {}

    for box in soup.select("div.list-box"):
        label_box = box.select_one(".txt-box .label")
        subject_link = box.select_one(".txt-box .subject a")
        subject_box = box.select_one(".txt-box .subject")
        date_box = box.select_one(".txt-box .date")

        if label_box is None or subject_link is None:
            continue

        status = " ".join(label_box.stripped_strings).strip()
        if status != "吏꾪뻾以?:
            continue

        href = (subject_link.get("href") or "").strip()
        full_url = normalize_event_url(href)
        if not full_url:
            continue

        title = " ".join(subject_link.stripped_strings).strip()
        if not title and subject_box:
            title = " ".join(subject_box.stripped_strings).strip()

        if not title:
            continue

        period = ""
        if date_box:
            period = " ".join(date_box.stripped_strings).strip()

        # ?대깽??????대?吏 異붿텧
        image_url = extract_event_image(box, EVENT_URL)
        if not image_url:
            image_url = extract_detail_page_image(full_url)

        if image_url:
            print(f"?대깽???대?吏 諛쒓껄: {image_url}")
        else:
            print(f"?대깽???대?吏 ?놁쓬: {title}")

        events[full_url] = {
            "kind": "?대깽??,
            "title": title,
            "status": status,
            "period": period,
            "url": full_url,
            "image_url": image_url,
        }

    return list(events.values())

# ============================================================
# ?대깽??泥섎━
# ============================================================

def process_events(state):
    print("")
    print("===== ?대깽???뺤씤 =====")

    try:
        html = fetch_html(EVENT_URL)
    except Exception as e:
        print(f"?대깽???섏씠吏 ?묒냽 ?ㅽ뙣: {e}")
        return False

    events = parse_events(html)
    print(f"吏꾪뻾以??대깽??媛먯? 媛쒖닔: {len(events)}")

    for item in events[:10]:
        print(f"媛먯?: {item['title']} / {item['period']} / {item['url']}")
        print(f"  ?대?吏: {item.get('image_url')}")

    if not events:
        print("寃쎄퀬: 吏꾪뻾以묒씤 ?대깽?몃? 李얠? 紐삵뻽?듬땲??")
        return False

    old_seen = set(state.get("event_seen_urls", []))
    current_urls = [item["url"] for item in events]

    # 泥??ㅽ뻾
    if not old_seen:
        state["event_seen_urls"] = current_urls[:100]
        print(f"?대깽??珥덇린?? ?꾩옱 吏꾪뻾以??대깽??{len(current_urls)}媛쒕? 湲곗??먯쑝濡????)
        return True

    # ???대깽???뺤씤
    new_events = [item for item in events if item["url"] not in old_seen]

    if new_events:
        print(f"???대깽??{len(new_events)}媛?諛쒓껄")
        for item in new_events[:MAX_SEND_PER_RUN]:
            image_file = None
            if item.get("image_url"):
                image_file = download_event_image(item["image_url"], item["url"])
                if not image_file:
                    print("?대?吏 ?ㅼ슫濡쒕뱶 ?ㅽ뙣. ?대?吏 ?놁씠 Discord ?꾩넚")

            send_discord(item, image_file=image_file)
            print(f"?대깽??Discord ?꾩넚: {item['title']} / {item['period']}")
    else:
        print("???대깽???놁쓬")

    # ?곹깭 ???    merged = []
    for url in (current_urls + list(old_seen)):
        if url not in merged:
            merged.append(url)

    new_state = merged[:100]
    changed = new_state != state.get("event_seen_urls", [])
    state["event_seen_urls"] = new_state

    return changed or bool(new_events)