import sys
from common import load_state, save_state
from notices import process_notices
from events import process_events

# 메인
# ============================================================

def main():
    print(
        "거상 공지/이벤트 "
        "확인을 시작합니다."
    )

    state = load_state()

    changed = False

    # 공지 확인
    if process_notices(
        state
    ):
        changed = True

    # 이벤트 확인
    if process_events(
        state
    ):
        changed = True

    # 상태 저장
    if changed:
        save_state(
            state
        )

        print("")
        print(
            "상태 파일 저장 완료"
        )

    else:
        print("")
        print(
            "상태 변경 없음"
        )

    print("")
    print(
        "확인 작업 완료"
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
