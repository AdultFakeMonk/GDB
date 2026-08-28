import os
import sys
import time
import requests
from common import load_state, save_state
from notices import process_notices
from events import process_events

# ============================================================
# 메인 실행 엔진 (연속 감시 & 자가 릴레이 모드)
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


def trigger_next_relay():
    """
    깃허브 액션이 게으른 자체 cron 스케줄러 때문에 멈추지 않도록,
    작업 종료 직전 깃허브 API를 호출하여 다음 액션을 즉시 깨우는 자가 릴레이 함수입니다.
    """
    token = os.environ.get("GH_PAT")
    if not token:
        print("\n[자가 릴레이] GH_PAT 환경변수가 설정되지 않아 기본 스케줄러로 대기합니다.")
        return

    repo = os.environ.get("GITHUB_REPOSITORY", "AdultFakeMonk/GDB")
    workflow_id = "337555667"
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/dispatches"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Gersang-Self-Relay",
    }
    data = {"ref": "main"}
    
    try:
        print("\n[자가 릴레이] 다음 실행을 깃허브에 예약합니다...")
        res = requests.post(url, headers=headers, json=data, timeout=15)
        if res.status_code in (200, 204):
            print("다음 릴레이 예약 성공! (24시간 무중단 연속 감시 유지)")
        else:
            print(f"릴레이 응답: HTTP {res.status_code} ({res.text})")
    except Exception as e:
        print(f"릴레이 호출 예외 발생 (cron 스케줄러로 백업): {e}")


def main():
    # 깃허브 액션 1회 실행 당 반복 횟수 및 간격 (기본 3회 / 180초 = 약 9분 상주)
    cycles = int(os.environ.get("RUN_CYCLES", "3"))
    delay_seconds = int(os.environ.get("CYCLE_DELAY_SECONDS", "180"))

    print("==================================================")
    print("거상 공지/이벤트 24시간 자가 릴레이 모니터링 시작")
    print(f"설정: 총 {cycles}회 반복 감시, 체크 간격 {delay_seconds}초 (총 약 {int(cycles * delay_seconds / 60)}분 상주)")
    print("==================================================")

    for i in range(1, cycles + 1):
        run_check_cycle(i, cycles)

        # 마지막 주기가 아니면 다음 주기까지 대기
        if i < cycles:
            print(f"\n다음 체크까지 {delay_seconds}초 대기합니다...")
            time.sleep(delay_seconds)

    # 모든 주기를 마치면 다음 릴레이 액션을 즉시 호출하여 무중단 연속성 유지
    trigger_next_relay()

    print("\n==================================================")
    print("이번 모니터링 작업을 성공적으로 마쳤습니다.")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
