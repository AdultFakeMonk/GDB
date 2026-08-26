import os
import sys
import time
from common import load_state, save_state
from notices import process_notices
from events import process_events

# ============================================================
# 메인 실행 엔진 (연속 감시 모드)
# ============================================================

def run_check_cycle(cycle_index, total_cycles):
    print(f"\n--- [체크 {cycle_index}/{total_cycles}] {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    state = load_state()
    changed = False

    # 공지 확인
    if process_notices(state):
        changed = True

    # 이벤트 확인
    if process_events(state):
        changed = True

    # 상태 변경 시 즉시 로컬 파일 갱신
    if changed:
        save_state(state)
        print("상태 파일 갱신 완료")
    else:
        print("신규 등록 항목 없음")

    return changed


def main():
    # 깃허브 액션 1회 실행 당 반복 횟수 및 간격 (환경변수 또는 기본값 3회 / 150초)
    # 총 약 7분간 액션이 켜져 있으면서 2.5분마다 촘촘하게 감시합니다.
    cycles = int(os.environ.get("RUN_CYCLES", "3"))
    delay_seconds = int(os.environ.get("CYCLE_DELAY_SECONDS", "150"))

    print("==================================================")
    print("거상 공지/이벤트 연속 모니터링을 시작합니다.")
    print(f"설정: 총 {cycles}회 반복 감시, 체크 간격 {delay_seconds}초")
    print("==================================================")

    for i in range(1, cycles + 1):
        run_check_cycle(i, cycles)

        # 마지막 주기가 아니면 다음 주기까지 대기
        if i < cycles:
            print(f"\n다음 체크까지 {delay_seconds}초 대기합니다...")
            time.sleep(delay_seconds)

    print("\n==================================================")
    print("이번 모니터링 작업을 성공적으로 마쳤습니다.")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
