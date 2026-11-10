"""
app.py - AutoMediaFormatter 실행 진입점

모든 모듈을 초기화하고 연결합니다.

연결 구조:
    DiskWatcher (QThread)
        │ disk_detected Signal
        ▼
    Formatter (on_step 콜백)
        │ step_signal emit
        ▼
    MainWindow (GUI 업데이트)

실행:
    관리자 권한으로 실행해야 합니다.
    python app.py
"""

import sys
import os
import logging
from datetime import datetime

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QThread

from ui.main_window import MainWindow
from core.disk_watcher import DiskWatcher
from core.formatter import Formatter
from core import diskpart


# ── 로그 설정 ──
def setup_logging():
    """
    로그 시스템을 초기화합니다.
    logs 폴더에 날짜별 로그 파일을 생성합니다.
    """
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f"{today}_logs.txt")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


class App:
    """
    애플리케이션 전체를 관리하는 클래스.
    모듈 간 연결과 생명주기를 담당합니다.
    """

    def __init__(self):
        self.qt_app = QApplication(sys.argv)
        self.window = MainWindow()
        self.formatter = Formatter()
        self.watcher = DiskWatcher()

        self._connect_all()

    def _connect_all(self):
        """모든 모듈 간 Signal/Slot/콜백을 연결합니다."""

        # ── formatter → GUI ──
        # formatter의 on_step 콜백이 호출되면 GUI의 step_signal을 emit
        self.formatter.on_step = lambda disk, step, msg: (
            self.window.step_signal.emit(disk, step, msg)
        )

        # ── watcher → formatter ──
        # 새 디스크 감지 시 포맷 워커 스레드에서 formatter.run() 실행
        self.watcher.disk_detected.connect(self._on_disk_detected)

        # 디스크 제거 시 로그 기록
        self.watcher.disk_removed.connect(self._on_disk_removed)

        # 스캔 에러 시 로그 기록
        self.watcher.scan_error.connect(self._on_scan_error)

        # ── GUI 버튼 → watcher ──
        # 기존 on_auto_start/stop을 오버라이드
        self.window.on_auto_start = self._start_watching
        self.window.on_auto_stop = self._stop_watching

        # ── GUI 종료 → 정리 ──
        self.window.closeEvent = self._on_close

    def _on_disk_detected(self, disk_info: dict):
        """
        새 디스크 감지 시 호출됩니다.
        별도 스레드에서 formatter를 실행하여 GUI가 멈추지 않도록 합니다.
        """
        disk_number = disk_info.get("disk_number", -1)
        model = disk_info.get("model", "알 수 없음")

        self.window.append_log(
            f"새 디스크 감지: Disk {disk_number} ({model})", "info"
        )

        # formatter.run()은 diskpart 실행으로 시간이 걸릴 수 있으므로
        # QThread에서 실행 (watcher 스레드에서 직접 호출하면 스캔이 멈춤)
        self._format_thread = FormatWorker(self.formatter, disk_info)
        self._format_thread.start()

    def _on_disk_removed(self, disk_number: int):
        """디스크 제거 시 호출됩니다."""
        self.window.append_log(f"디스크 제거 감지: Disk {disk_number}", "warning")

    def _on_scan_error(self, error_msg: str):
        """스캔 에러 시 호출됩니다."""
        self.window.append_log(error_msg, "error")

    def _start_watching(self):
        """Auto Start: watcher 시작"""
        self.window.set_running(True)

        if not self.watcher.isRunning():
            self.watcher.start()

    def _stop_watching(self):
        """Auto Stop: watcher 중지"""
        self.window.set_running(False)

        if self.watcher.isRunning():
            self.watcher.stop()

    def _on_close(self, event):
        """프로그램 종료 시 모든 리소스를 정리합니다."""
        logging.info("프로그램 종료 시작")

        # watcher 중지
        if self.watcher.isRunning():
            self.watcher.stop()

        # diskpart 스크립트 파일 삭제
        diskpart.shutdown()

        logging.info("프로그램 종료 완료")
        event.accept()

    def run(self) -> int:
        """애플리케이션을 실행합니다."""
        # 1. 관리자 권한 확인
        if not diskpart.is_admin():
            QMessageBox.critical(
                None,
                "권한 오류",
                "AutoMediaFormatter는 관리자 권한으로 실행해야 합니다.\n"
                "프로그램을 우클릭하여 '관리자 권한으로 실행'을 선택하세요.",
            )
            return 1

        # 2. diskpart 스크립트 파일 초기화
        diskpart.init()

        # 3. GUI 표시
        self.window.show()
        self.window.append_log("AutoMediaFormatter가 시작되었습니다.", "info")
        self.window.append_log("Auto Start를 눌러 자동 포맷 모드를 시작하세요.", "info")

        # 4. 이벤트 루프 실행
        return self.qt_app.exec()


class FormatWorker(QThread):
    """
    포맷 작업을 별도 스레드에서 실행합니다.
    GUI 멈춤 방지 및 watcher 스캔 지속을 위해 분리합니다.
    """

    def __init__(self, formatter: Formatter, disk_info: dict):
        super().__init__()
        self._formatter = formatter
        self._disk_info = disk_info

    def run(self):
        result = self._formatter.run(self._disk_info)
        logging.info(f"포맷 결과: {result}")


def main():
    setup_logging()
    logging.info("=" * 50)
    logging.info("AutoMediaFormatter 시작")
    logging.info("=" * 50)

    app = App()
    exit_code = app.run()

    logging.info("AutoMediaFormatter 종료")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
