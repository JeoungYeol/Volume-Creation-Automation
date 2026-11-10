"""
disk_watcher.py - 디스크 삽입/제거 감지 모듈

QThread 기반으로 주기적으로 디스크 목록을 스캔하여,
새 디스크 삽입 또는 기존 디스크 제거를 감지합니다.

감지 흐름:
    1. 일정 주기(기본 2초)로 현재 디스크 목록 스캔
    2. 이전 스캔 결과와 비교
    3. 새 디스크 발견 시 → disk_detected Signal emit
    4. 디스크 제거 시 → disk_removed Signal emit

GUI 연동:
    - disk_detected Signal → formatter.run() 호출
    - disk_removed Signal → 로그 기록
"""

import logging
from PySide6.QtCore import QThread, Signal

from core import disk_info

logger = logging.getLogger(__name__)

# 스캔 주기 (밀리초)
DEFAULT_SCAN_INTERVAL_MS = 2000


class DiskWatcher(QThread):
    """
    디스크 삽입/제거를 감지하는 워커 스레드

    Signals:
        disk_detected(dict): 새 디스크가 감지되었을 때 (디스크 정보 딕셔너리)
        disk_removed(int): 디스크가 제거되었을 때 (디스크 번호)
        scan_error(str): 스캔 중 오류 발생 시 (에러 메시지)
    """

    disk_detected = Signal(dict)
    disk_removed = Signal(int)
    scan_error = Signal(str)

    def __init__(self, scan_interval_ms: int = DEFAULT_SCAN_INTERVAL_MS):
        super().__init__()
        self._scan_interval_ms = scan_interval_ms
        self._running = False

        # 이전 스캔의 디스크 번호 set (비교용)
        self._known_disks: dict[int, dict] = {}

    def run(self):
        """
        스레드 메인 루프.
        _running이 True인 동안 주기적으로 디스크를 스캔합니다.
        """
        self._running = True
        logger.info(f"DiskWatcher 시작 (스캔 주기: {self._scan_interval_ms}ms)")

        # 시작 시 현재 디스크 목록을 기준점으로 저장
        self._init_baseline()

        while self._running:
            try:
                self._scan()
            except Exception as e:
                error_msg = f"디스크 스캔 중 오류: {e}"
                logger.error(error_msg)
                self.scan_error.emit(error_msg)

            # 지정된 주기만큼 대기 (stop 호출 시 즉시 깨어남)
            self.msleep(self._scan_interval_ms)

        logger.info("DiskWatcher 종료")

    def stop(self):
        """스캔을 중지하고 스레드를 종료합니다."""
        self._running = False
        self.quit()
        self.wait(5000)  # 최대 5초 대기
        logger.info("DiskWatcher 중지 완료")

    def _init_baseline(self):
        """
        시작 시 현재 연결된 디스크 목록을 기준점으로 저장합니다.
        프로그램 시작 전부터 꽂혀있던 디스크는 무시하기 위함입니다.
        """
        try:
            current_disks = disk_info.get_all_disks()
            self._known_disks = {d["disk_number"]: d for d in current_disks}
            disk_nums = list(self._known_disks.keys())
            logger.info(f"기준 디스크 목록: {disk_nums}")
        except Exception as e:
            logger.error(f"기준 디스크 목록 수집 실패: {e}")
            self._known_disks = {}

    def _scan(self):
        """
        현재 디스크 목록을 스캔하고, 이전과 비교하여 변경사항을 감지합니다.
        """
        current_disks = disk_info.get_all_disks()
        current_map = {d["disk_number"]: d for d in current_disks}

        current_nums = set(current_map.keys())
        known_nums = set(self._known_disks.keys())

        # ── 새로 삽입된 디스크 ──
        added = current_nums - known_nums
        for disk_num in added:
            disk = current_map[disk_num]
            logger.info(
                f"새 디스크 감지: Disk {disk_num} "
                f"({disk.get('model', '알 수 없음')}, {disk.get('media_type', '알 수 없음')})"
            )
            self.disk_detected.emit(disk)

        # ── 제거된 디스크 ──
        removed = known_nums - current_nums
        for disk_num in removed:
            logger.info(f"디스크 제거 감지: Disk {disk_num}")
            self.disk_removed.emit(disk_num)

        # 현재 상태를 기준으로 갱신
        self._known_disks = current_map
