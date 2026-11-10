"""
diskpart.py - diskpart 스크립트 생성 및 실행 모듈

디스크 번호를 받아 diskpart 스크립트 파일을 동적으로 생성하고,
subprocess로 diskpart.exe를 실행합니다.

스크립트 파일 생명주기:
    - 프로그램 시작 시: 스크립트 파일 1개 생성 (init)
    - 포맷 요청 시: 파일 내용만 덮어쓰기 (_write_script)
    - 프로그램 종료 시: 파일 삭제 (shutdown)

스크립트 명령 순서:
    1. Select Disk {n}
    2. Clean
    3. Create Partition Primary
    4. Format FS=exFAT Label=NOVACHIPS QUICK
    5. Assign Letter=D
    6. Exit

주의: diskpart는 관리자 권한이 필요합니다.
"""

import os
import subprocess
import logging

logger = logging.getLogger(__name__)

# 포맷 설정 (변경 금지)
FILE_SYSTEM = "exFAT"
VOLUME_LABEL = "NOVACHIPS"
DRIVE_LETTER = "D"

# 스크립트 파일 경로
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(_BASE_DIR, "resources", "diskpart_script.txt")


def init():
    """
    프로그램 시작 시 호출합니다.
    resources 폴더와 빈 스크립트 파일을 생성합니다.
    """
    os.makedirs(os.path.dirname(SCRIPT_PATH), exist_ok=True)
    with open(SCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write("")
    logger.info(f"diskpart 스크립트 파일 초기화: {SCRIPT_PATH}")


def shutdown():
    """
    프로그램 종료 시 호출합니다.
    스크립트 파일을 삭제합니다.
    """
    try:
        if os.path.exists(SCRIPT_PATH):
            os.remove(SCRIPT_PATH)
            logger.info(f"diskpart 스크립트 파일 삭제: {SCRIPT_PATH}")
    except OSError as e:
        logger.warning(f"스크립트 파일 삭제 실패: {e}")


def _write_script(disk_number: int) -> None:
    """
    스크립트 파일에 해당 디스크 번호의 포맷 명령을 덮어씁니다.

    Args:
        disk_number: 포맷할 디스크 번호 (0은 허용하지 않음)

    Raises:
        ValueError: 디스크 번호가 0인 경우
    """
    if disk_number == 0:
        raise ValueError("시스템 디스크(Disk 0)에 대한 스크립트 생성은 차단됩니다.")

    script = (
        f"Select Disk {disk_number}\n"
        f"Clean\n"
        f"Create Partition Primary\n"
        f"Format FS={FILE_SYSTEM} Label={VOLUME_LABEL} QUICK\n"
        f"Assign Letter={DRIVE_LETTER}\n"
        f"Exit\n"
    )

    with open(SCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(script)

    logger.info(f"디스크 {disk_number} 포맷 스크립트 작성 완료")


def execute(disk_number: int) -> tuple[bool, str]:
    """
    디스크 번호를 받아 스크립트 작성 → diskpart 실행을 수행합니다.

    Args:
        disk_number: 포맷할 디스크 번호

    Returns:
        (성공 여부, 결과 메시지)
    """
    try:
        # 1. 관리자 권한 확인
        if not is_admin():
            raise RuntimeError("diskpart 실행에는 관리자 권한이 필요합니다.")

        # 2. 스크립트 파일 존재 확인
        if not os.path.exists(SCRIPT_PATH):
            raise RuntimeError(f"스크립트 파일이 없습니다. init()을 먼저 호출하세요: {SCRIPT_PATH}")

        # 3. 스크립트 내용 덮어쓰기
        _write_script(disk_number)

        # 4. diskpart 실행
        cmd = f"diskpart /s \"{SCRIPT_PATH}\""
        logger.info(f"diskpart 실행: {cmd}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True,
            timeout=120,
        )

        output = result.stdout.strip()
        logger.info(f"diskpart 출력:\n{output}")

        # 5. 출력 내용으로 에러 판단
        if _check_diskpart_error(output):
            error_msg = _extract_error_message(output)
            logger.error(f"diskpart 오류: {error_msg}")
            return False, error_msg

        return True, output

    except ValueError as e:
        logger.error(str(e))
        return False, str(e)
    except RuntimeError as e:
        logger.error(str(e))
        return False, str(e)
    except subprocess.TimeoutExpired:
        logger.error("diskpart 실행 시간 초과 (120초)")
        return False, "diskpart 실행 시간 초과 (120초)"
    except Exception as e:
        logger.error(f"diskpart 실행 중 예외: {e}")
        return False, str(e)


def is_admin() -> bool:
    """현재 프로세스가 관리자 권한으로 실행 중인지 확인합니다."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except (AttributeError, OSError):
        return False


def _check_diskpart_error(output: str) -> bool:
    """diskpart 출력에서 오류 발생 여부를 확인합니다."""
    error_keywords = [
        "오류", "error", "실패", "fail",
        "액세스가 거부", "access is denied",
        "찾을 수 없습니다", "not found",
        "사용할 수 없습니다", "not available",
    ]
    output_lower = output.lower()
    return any(kw.lower() in output_lower for kw in error_keywords)


def _extract_error_message(output: str) -> str:
    """diskpart 출력에서 오류 관련 줄만 추출합니다."""
    error_keywords = ["오류", "error", "실패", "fail", "거부", "denied"]
    error_lines = []
    for line in output.split("\n"):
        line_lower = line.strip().lower()
        if any(kw.lower() in line_lower for kw in error_keywords):
            error_lines.append(line.strip())

    return " | ".join(error_lines) if error_lines else "알 수 없는 오류가 발생했습니다."
