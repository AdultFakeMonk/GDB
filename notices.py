from bs4 import BeautifulSoup
from common import NOTICE_URL, NOTICE_PAGE_URL, MAX_SEND_PER_RUN, fetch_html
from discord_sender import send_discord

# 공지사항 파싱
# ============================================================

def parse_notices(html):
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    notices = []

    for row in soup.select(
        "div.tr[data-uid]"
    ):
        uid_text = (
            row.get("data-uid")
            or ""
        ).strip()

        if not uid_text.isdigit():
            continue

        subject = row.select_one(
            ".box-subject"
        )

        date_box = row.select_one(
            ".box-date"
        )

        if subject is None:
            continue

        title = " ".join(
            subject.stripped_strings
        ).strip()

        if not title:
            continue

        date = ""

        if date_box:
            date = " ".join(
                date_box.stripped_strings
            ).strip()

        notices.append(
            {
                "kind": "공지",
                "id": int(uid_text),
                "title": title,
                "date": date,
                "url": f"https://www.gersang.co.kr/news/notice.gs?GSbid=1001&seq={uid_text}",
            }
        )

    notices.sort(
        key=lambda item: item["id"],
        reverse=True,
    )

    return notices



# 공지 처리
# ============================================================

def process_notices(state):
    print("")
    print(
        "===== 공지사항 확인 ====="
    )

    notices_dict = {}

    for page in (1, 2):
        page_url = NOTICE_PAGE_URL.format(page=page)
        try:
            print(f"공지사항 {page}페이지 확인 중...")
            html = fetch_html(page_url)
            page_notices = parse_notices(html)
            for item in page_notices:
                if item["id"] not in notices_dict:
                    notices_dict[item["id"]] = item
            print(
                f"공지사항 {page}페이지 수집 완료: "
                f"{len(page_notices)}건 감지 "
                f"(누적 고유: {len(notices_dict)}건)"
            )
        except Exception as e:
            print(
                f"공지사항 {page}페이지 "
                f"접속 실패: {e}"
            )

    if not notices_dict:
        print(
            "경고: 공지사항 게시물을 "
            "찾지 못했습니다."
        )
        return False

    notices = sorted(
        notices_dict.values(),
        key=lambda item: item["id"],
        reverse=True,
    )

    print(
        f"공지사항 최종 고유 개수: "
        f"{len(notices)}"
    )

    for item in notices[:5]:
        print(
            f"감지: ID={item['id']} / "
            f"{item['date']} / "
            f"{item['title']}"
        )

    newest_id = notices[0]["id"]

    last_id = state.get(
        "notice_last_id"
    )

    if last_id is None:
        state[
            "notice_last_id"
        ] = newest_id

        print(
            f"공지 초기화: 최신 ID "
            f"{newest_id}을 "
            "기준점으로 저장"
        )

        return True

    try:
        last_id = int(
            last_id
        )

    except Exception:
        last_id = 0

    # 안전장치: last_id가 0이거나 newest_id와 50 이상 차이나면
    # 상태 파일이 리셋된 것으로 보고 초기화만 수행 (중복 전송 방지)
    if last_id == 0 or (newest_id - last_id) > 50:
        print(
            f"경고: last_id({last_id})가 비정상입니다. "
            f"최신 ID {newest_id}로 초기화합니다. (중복 전송 방지)"
        )
        state["notice_last_id"] = newest_id
        return True

    new_notices = [
        item
        for item in notices
        if item["id"] > last_id
    ]

    if not new_notices:
        print(
            f"새 공지 없음. "
            f"last={last_id}, "
            f"newest={newest_id}"
        )

        return False

    print(
        f"새 공지 "
        f"{len(new_notices)}개 발견"
    )

    new_notices.sort(
        key=lambda item: item["id"]
    )

    selected = new_notices[
        -MAX_SEND_PER_RUN:
    ]

    for item in selected:
        send_discord(
            item
        )

        print(
            f"공지 Discord 전송: "
            f"{item['id']} / "
            f"{item['title']}"
        )

    state[
        "notice_last_id"
    ] = max(
        item["id"]
        for item in selected
    )

    return True


