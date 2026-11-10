"""
formatter.py - 포맷 실행 컨트롤러

validator와 diskpart를 조합하여 포맷의 전체 흐름을 관리합니다.
GUI는 이 모듈의 Formatter 클래스만 사용하면 됩니다.

포맷 흐름:
    1. [검증 중]  validator로 디스크 검증
    2. [포맷 준비] 포맷 진행 상태 등록
    3. [포맷 중]  diskpart 실행
    4. [완료/실패] 결과 처리 및 상태 해제

각 단계마다 콜백(on_step)을 호출하여 GUI에서 로그 및 상태 업데이트가 가능합니다.
"""

import logging
from typing import Callable, Optional

from core.validator import DiskValidator
from core import diskpart

logger = logging.getLogger(__name__)


# 포맷 진행 단계 상수 (GUI 상태창에서 사용)
STEP_VALIDATING = "검증 중"
STEP_PREPARING = "포맷 준비"
STEP_FORMATTING = "포맷 중"
STEP_COMPLETED = "완료"
STEP_FAILED = "실패"


class FormatResult:
    """포맷 결과를 담는 데이터 클래스"""

    def __init__(self, disk_number: int, success: bool, step: str, message: str):
        self.disk_number = disk_number
        self.success = success
        self.step = step        # 마지막 단계 (GUI 상태창용)
        self.message = message  # 상세 메시지 (GUI 로그용)

    def __repr__(self):
        status = "성공" if self.success else "실패"
        return f"[{status}] 디스크 {self.disk_number} | {self.step} | {self.message}"


class Formatter:
    """
    포맷 실행 컨트롤러

    사용법:
        formatter = Formatter()

        # GUI에서 단계별 업데이트를 받으려면 콜백 등록
        formatter.on_step = lambda disk, step, msg: print(f"{step}: {msg}")

        result = formatter.run(disk_info)
    """

    def __init__(self):
        self.validator = DiskValidator()

        # 콜백: 각 단계마다 호출됨 (disk_number, step, message)
        # GUI에서 이 콜백을 Signal emit으로 연결하면 됩니다.
        self.on_step: Optional[Callable[[int, str, str], None]] = None

    def _notify(self, disk_number: int, step: str, message: str) -> None:
        """단계 변경을 콜백으로 알립니다."""
        logger.info(f"[{step}] 디스크 {disk_number}: {message}")
        if self.on_step:
            self.on_step(disk_number, step, message)

    def run(self, disk_info: dict) -> FormatResult:
        """
        디스크 정보를 받아 검증 → 포맷 → 결과 반환까지 수행합니다.

        Args:
            disk_info: disk_info.py에서 반환한 디스크 정보 딕셔너리
                - disk_number (int)
                - media_type (str)
                - has_volumes (bool)

        Returns:
            FormatResult 객체
        """
        disk_number = disk_info.get("disk_number", -1)

        # ── 1단계: 검증 ──
        self._notify(disk_number, STEP_VALIDATING, "디스크 검증을 시작합니다.")

        passed, reason = self.validator.validate(disk_info)
        if not passed:
            self._notify(disk_number, STEP_FAILED, reason)
            return FormatResult(disk_number, False, STEP_FAILED, reason)

        self._notify(disk_number, STEP_VALIDATING, reason)

        # ── 2단계: 포맷 준비 (진행 상태 등록) ──
        self._notify(disk_number, STEP_PREPARING, "포맷 진행 상태를 등록합니다.")
        self.validator.mark_formatting(disk_number)

        try:
            # ── 3단계: 포맷 실행 ──
            self._notify(disk_number, STEP_FORMATTING, "diskpart를 실행합니다.")

            success, output = diskpart.execute(disk_number)

            if success:
                # ── 4a: 성공 ──
                self._notify(disk_number, STEP_COMPLETED, "포맷이 완료되었습니다.")
                return FormatResult(disk_number, True, STEP_COMPLETED, "포맷이 완료되었습니다.")
            else:
                # ── 4b: 실패 ──
                self._notify(disk_number, STEP_FAILED, output)
                return FormatResult(disk_number, False, STEP_FAILED, output)

        except Exception as e:
            # ── 예외 발생 ──
            error_msg = f"포맷 중 예외 발생: {e}"
            self._notify(disk_number, STEP_FAILED, error_msg)
            return FormatResult(disk_number, False, STEP_FAILED, error_msg)

        finally:
            # 성공이든 실패든 진행 상태 해제
            self.validator.unmark_formatting(disk_number)

    def reset(self) -> None:
        """모든 포맷 진행 상태를 초기화합니다."""
        self.validator.reset()
        logger.info("Formatter 상태 초기화 완료")
