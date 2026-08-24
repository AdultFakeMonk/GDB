import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests
from common import EVENT_URL, HEADERS, MAX_SEND_PER_RUN, fetch_html, normalize_image_url
from discord_sender import send_discord

# ============================================================
# 이벤트 URL 확인
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
# CSS background-image에서 URL 추출
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
# 이벤트 대표 이미지 추출
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

    # img 태그
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
# 이벤트 상세페이지에서 이미지 찾기
# ============================================================

def extract_detail_page_image(event_url):
    print("목록에서 이벤트 이미지를 찾지 못했습니다.")
    print(f"상세페이지 이미지 확인: {event_url}")

    try:
        html = fetch_html(event_url)
    except Exception as e:
        print(f"이벤트 상세페이지 접속 실패: {e}")
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
# 이벤트 이미지 다운로드
# ============================================================

def download_event_image(image_url, event_url):
    """
    Discord가 거상 서버에서 직접 이미지를
    가져가도록 하지 않고,
    GitHub Actions가 먼저 원본 이미지를
    다운로드한 뒤 Discord에 파일로 첨부합니다.
    이미지 크기는 변경하지 않습니다.
    """
    print("")
    print("이벤트 이미지 다운로드 시작")
    print(f"이미지 URL: {image_url}")

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
            raise RuntimeError("이미지 응답 내용이 비어 있습니다.")

        content_type = (
            response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        )

        print(f"이미지 다운로드 성공 (HTTP {response.status_code})")
        print(f"Content-Type: {content_type}")
        print(f"이미지 크기: {len(response.content)} bytes")

        # 확장자 결정
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
        print(f"이벤트 이미지 다운로드 실패: {e}")
        return None


# ============================================================
# 이벤트 파싱
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

        # 진행중인 이벤트만
        if status != "진행중":
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

        # 이벤트 대표 이미지 추출
        image_url = extract_event_image(box, EVENT_URL)

        # 목록에서 못 찾으면 상세페이지에서 검색
        if not image_url:
            image_url = extract_detail_page_image(full_url)

        if image_url:
            print(f"이벤트 이미지 발견: {image_url}")
        else:
            print(f"이벤트 이미지 없음: {title}")

        events[full_url] = {
            "kind": "이벤트",
            "title": title,
            "status": status,
            "period": period,
            "url": full_url,
            "image_url": image_url,
        }

    return list(events.values())


# ============================================================
# 이벤트 처리
# ============================================================

def process_events(state):
    print("")
    print("===== 이벤트 확인 =====")

    try:
        html = fetch_html(EVENT_URL)
    except Exception as e:
        print(f"이벤트 페이지 접속 실패: {e}")
        return False

    events = parse_events(html)
    print(f"진행중 이벤트 감지 개수: {len(events)}")

    for item in events[:10]:
        print(f"감지: {item['title']} / {item['period']} / {item['url']}")
        print(f"  이미지: {item.get('image_url')}")

    if not events:
        print("경고: 진행중인 이벤트를 찾지 못했습니다.")
        return False

    old_seen = set(state.get("event_seen_urls", []))
    current_urls = [item["url"] for item in events]

    # 첫 실행
    if not old_seen:
        state["event_seen_urls"] = current_urls[:100]
        print(f"이벤트 초기화: 현재 진행중 이벤트 {len(current_urls)}개를 기준점으로 저장")
        return True

    # 새 이벤트 확인
    new_events = [item for item in events if item["url"] not in old_seen]

    if new_events:
        print(f"새 이벤트 {len(new_events)}개 발견")
        for item in new_events[:MAX_SEND_PER_RUN]:
            image_file = None
            if item.get("image_url"):
                image_file = download_event_image(item["image_url"], item["url"])
                if not image_file:
                    print("이미지 다운로드 실패. 이미지 없이 Discord 전송")

            send_discord(item, image_file=image_file)
            print(f"이벤트 Discord 전송: {item['title']} / {item['period']}")
    else:
        print("새 이벤트 없음")

    # 상태 저장
    merged = []
    for url in (current_urls + list(old_seen)):
        if url not in merged:
            merged.append(url)

    new_state = merged[:100]
    changed = new_state != state.get("event_seen_urls", [])
    state["event_seen_urls"] = new_state

    return changed or bool(new_events)