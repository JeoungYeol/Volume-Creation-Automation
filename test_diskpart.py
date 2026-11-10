"""
diskpart.py 테스트 스크립트

실제 diskpart를 실행하지 않고 안전하게 검증합니다.

사용법:
    python test_diskpart.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.diskpart import (
    init,
    shutdown,
    _write_script,
    is_admin,
    _check_diskpart_error,
    _extract_error_message,
    SCRIPT_PATH,
    FILE_SYSTEM,
    VOLUME_LABEL,
    DRIVE_LETTER,
)


def test_init_and_shutdown():
    """프로그램 시작/종료 시 파일 생성/삭제 테스트"""
    print("=" * 50)
    print("[테스트 1] init / shutdown")
    print("=" * 50)

    # init → 파일 생성 확인
    init()
    assert os.path.exists(SCRIPT_PATH), "init 후 스크립트 파일이 없습니다."
    print(f"[통과] init → 파일 생성됨: {SCRIPT_PATH}")

    # shutdown → 파일 삭제 확인
    shutdown()
    assert not os.path.exists(SCRIPT_PATH), "shutdown 후 파일이 남아있습니다."
    print(f"[통과] shutdown → 파일 삭제됨\n")


def test_write_script():
    """스크립트 덮어쓰기 테스트"""
    print("=" * 50)
    print("[테스트 2] 스크립트 덮어쓰기")
    print("=" * 50)

    init()

    # 디스크 1 스크립트 작성
    _write_script(1)
    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    print(f"--- 디스크 1 ---\n{content}")
    assert "Select Disk 1" in content
    assert f"FS={FILE_SYSTEM}" in content
    assert f"Label={VOLUME_LABEL}" in content
    assert f"Letter={DRIVE_LETTER}" in content
    print("[통과] 디스크 1 스크립트 정상")

    # 디스크 2로 덮어쓰기 → 기존 내용이 교체되는지 확인
    _write_script(2)
    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    print(f"--- 디스크 2 (덮어쓰기) ---\n{content}")
    assert "Select Disk 2" in content
    assert "Select Disk 1" not in content, "이전 내용이 남아있습니다."
    print("[통과] 덮어쓰기 정상 (이전 내용 없음)")

    shutdown()
    print()


def test_disk0_blocked():
    """디스크 0 차단 테스트"""
    print("=" * 50)
    print("[테스트 3] 디스크 0 차단")
    print("=" * 50)

    init()
    try:
        _write_script(0)
        print("[실패] 디스크 0이 차단되지 않았습니다!")
    except ValueError as e:
        print(f"[통과] 디스크 0 차단됨: {e}")
    shutdown()
    print()


def test_error_detection():
    """diskpart 출력 에러 감지 테스트"""
    print("=" * 50)
    print("[테스트 4] 에러 감지")
    print("=" * 50)

    # 정상 출력
    normal_output = "DiskPart에서 볼륨을 포맷했습니다.\nDiskPart를 마칩니다..."
    assert not _check_diskpart_error(normal_output)
    print("[통과] 정상 출력 → 에러 없음")

    # 에러 출력들
    error_cases = [
        ("한국어 오류", "가상 디스크 서비스 오류:\n데이터 영역이 작습니다."),
        ("영어 error", "Virtual Disk Service error:\nThe volume is too small."),
        ("액세스 거부", "액세스가 거부되었습니다."),
        ("실패 메시지", "포맷 실패: 디스크를 찾을 수 없습니다."),
    ]

    for name, output in error_cases:
        assert _check_diskpart_error(output), f"'{name}' 에러를 감지 못함"
        msg = _extract_error_message(output)
        print(f"[통과] {name} → {msg}")

    print()


def test_admin_check():
    """관리자 권한 확인"""
    print("=" * 50)
    print("[테스트 5] 관리자 권한")
    print("=" * 50)
    print(f"현재 관리자 권한: {is_admin()}")
    print(f"[참고] 포맷 실행 시 관리자 권한 없으면 자동 차단됩니다.\n")


def main():
    print("\n" + "=" * 50)
    print("  diskpart.py 테스트 시작")
    print("=" * 50 + "\n")

    test_init_and_shutdown()
    test_write_script()
    test_disk0_blocked()
    test_error_detection()
    test_admin_check()

    print("=" * 50)
    print("  모든 테스트 완료!")
    print("=" * 50)


if __name__ == "__main__":
    main()
