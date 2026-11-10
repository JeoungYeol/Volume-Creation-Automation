"""
validator.py - 디스크 포맷 가능 여부 검증 모듈

포맷 실행 전 반드시 이 모듈의 검증을 통과해야 합니다.
검증 조건:
    1. 디스크 번호 0(시스템 디스크) 제외
    2. 디스크 타입이 Removable(이동식)인지 확인
    3. 볼륨이 이미 존재하는 디스크는 제외
    4. 현재 포맷 진행 중인 디스크 중복 방지
"""

import threading

ALLOWED_MEDIA_TYPES = (
    "removable media",
    "external hard disk media",
)


class DiskValidator:
    """디스크 포맷 가능 여부를 검증하는 클래스"""

    def __init__(self):
        # 현재 포맷 진행 중인 디스크 번호를 추적
        self._formatting_disks: set[int] = set()
        self._lock = threading.Lock()

    def validate(self, disk_info: dict) -> tuple[bool, str]:
        """
        디스크 정보를 받아 포맷 가능 여부를 판단합니다.

        Args:
            disk_info: 디스크 정보 딕셔너리
                - disk_number (int): 디스크 번호
                - media_type (str): 디스크 타입 (예: "Removable Media", "Fixed hard disk media")
                - has_volumes (bool): 볼륨 존재 여부

        Returns:
            (bool, str): (포맷 가능 여부, 사유 메시지)
        """
        disk_number = disk_info.get("disk_number")
        media_type = disk_info.get("media_type", "")
        has_volumes = disk_info.get("has_volumes", False)

        # 1. 디스크 번호 0(시스템 디스크) 제외
        if disk_number == 0:
            return False, f"디스크 {disk_number}: 시스템 디스크(Disk 0)는 포맷할 수 없습니다."

        # 2. 디스크 타입이 Removable인지 확인
        if media_type.lower() not in ALLOWED_MEDIA_TYPES:
            return False, f"디스크 {disk_number}: 포맷 허용 타입이 아닙니다. (타입: {media_type})"

        # 3. 볼륨이 이미 존재하면 제외
        if has_volumes:
            return False, f"디스크 {disk_number}: 이미 볼륨이 존재합니다. 포맷 대상이 아닙니다."

        # 4. 현재 포맷 진행 중인 디스크 중복 방지
        with self._lock:
            if disk_number in self._formatting_disks:
                return False, f"디스크 {disk_number}: 이미 포맷이 진행 중입니다."

        return True, f"디스크 {disk_number}: 검증 통과. 포맷을 진행합니다."

    def mark_formatting(self, disk_number: int) -> None:
        """포맷 시작 시 해당 디스크를 진행 중 상태로 등록합니다."""
        with self._lock:
            self._formatting_disks.add(disk_number)

    def unmark_formatting(self, disk_number: int) -> None:
        """포맷 완료/실패 시 해당 디스크를 진행 중 상태에서 해제합니다."""
        with self._lock:
            self._formatting_disks.discard(disk_number)

    def is_formatting(self, disk_number: int) -> bool:
        """해당 디스크가 현재 포맷 진행 중인지 확인합니다."""
        with self._lock:
            return disk_number in self._formatting_disks

    def reset(self) -> None:
        """모든 포맷 진행 상태를 초기화합니다."""
        with self._lock:
            self._formatting_disks.clear()
