"""
main_window.py - AutoMediaFormatter GUI

PySide6 기반 메인 윈도우.
formatter.py의 on_step 콜백과 연동하여 실시간 상태 업데이트를 지원합니다.

레이아웃:
    ┌─────────────────────────────────────┐
    │  ● 상태 표시          AutoMediaFormatter │
    ├───────────────────────┬─────────────┤
    │                       │ 통계 카드     │
    │   로그 영역            │  총 시도      │
    │                       │  성공        │
    │                       │  실패        │
    │                       │  현재 Disk    │
    │                       ├─────────────┤
    │                       │ [Auto Start] │
    │                       │ [Auto Stop]  │
    │                       │ [Clear Log]  │
    │                       │ [Exit]       │
    └───────────────────────┴─────────────┘
"""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QFrame,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, Signal, Slot, QDateTime
from PySide6.QtGui import QFont, QColor, QIcon


# ── 스타일 상수 ──
COLORS = {
    "bg_primary": "#1a1a2e",       # 메인 배경
    "bg_secondary": "#16213e",     # 카드/패널 배경
    "bg_log": "#0f0f1a",           # 로그 영역 배경
    "accent": "#0ea5e9",           # 포인트 컬러 (스카이블루)
    "success": "#22c55e",          # 성공 (그린)
    "warning": "#f59e0b",          # 경고 (앰버)
    "error": "#ef4444",            # 에러 (레드)
    "text_primary": "#e2e8f0",     # 주 텍스트
    "text_secondary": "#94a3b8",   # 보조 텍스트
    "text_muted": "#64748b",       # 비활성 텍스트
    "border": "#1e293b",           # 테두리
    "button_bg": "#1e293b",        # 버튼 배경
    "button_hover": "#334155",     # 버튼 호버
    "button_active": "#0ea5e9",    # 활성 버튼
}

STATUS_COLORS = {
    "대기 중": COLORS["text_muted"],
    "검증 중": COLORS["warning"],
    "포맷 준비": COLORS["warning"],
    "포맷 중": COLORS["accent"],
    "완료": COLORS["success"],
    "실패": COLORS["error"],
}


STYLESHEET = f"""
    QMainWindow {{
        background-color: {COLORS['bg_primary']};
    }}

    /* ── 로그 영역 ── */
    QTextEdit#logArea {{
        background-color: {COLORS['bg_log']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 12px;
        font-family: 'Consolas', 'D2Coding', monospace;
        font-size: 12px;
        selection-background-color: {COLORS['accent']};
    }}

    /* ── 통계 카드 ── */
    QFrame#statsCard {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 8px;
    }}

    /* ── 버튼 공통 ── */
    QPushButton {{
        background-color: {COLORS['button_bg']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 10px 16px;
        font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
        font-size: 13px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {COLORS['button_hover']};
        border-color: {COLORS['accent']};
    }}
    QPushButton:pressed {{
        background-color: {COLORS['accent']};
    }}
    QPushButton:disabled {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_muted']};
        border-color: {COLORS['bg_primary']};
    }}

    /* ── 시작 버튼 특별 스타일 ── */
    QPushButton#btnStart {{
        background-color: {COLORS['accent']};
        color: #ffffff;
        border: none;
        font-weight: 600;
    }}
    QPushButton#btnStart:hover {{
        background-color: #38bdf8;
    }}
    QPushButton#btnStart:disabled {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_muted']};
    }}

    /* ── 종료 버튼 ── */
    QPushButton#btnExit {{
        background-color: transparent;
        color: {COLORS['text_muted']};
        border: 1px solid {COLORS['border']};
    }}
    QPushButton#btnExit:hover {{
        color: {COLORS['error']};
        border-color: {COLORS['error']};
    }}
"""


class MainWindow(QMainWindow):
    """AutoMediaFormatter 메인 윈도우"""

    # GUI 스레드에서 안전하게 업데이트하기 위한 Signal
    step_signal = Signal(int, str, str)  # disk_number, step, message

    def __init__(self):
        super().__init__()

        # 통계
        self._total_count = 0
        self._success_count = 0
        self._fail_count = 0
        self._current_disk = "-"
        self._is_running = False

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("AutoMediaFormatter")
        self.setFixedSize(780, 480)
        self.setStyleSheet(STYLESHEET)

        # 중앙 위젯
        central = QWidget()
        self.setCentralWidget(central)

        # ── 최상위 레이아웃 ──
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 12, 16, 16)
        root_layout.setSpacing(12)

        # ── 상단: 상태 바 ──
        root_layout.addLayout(self._create_status_bar())

        # ── 하단: 로그 + 우측 패널 ──
        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        # 좌측: 로그
        body_layout.addWidget(self._create_log_area(), stretch=3)

        # 우측: 통계 + 버튼
        body_layout.addLayout(self._create_right_panel(), stretch=1)

        root_layout.addLayout(body_layout)

    def _create_status_bar(self) -> QHBoxLayout:
        """상단 상태 바"""
        layout = QHBoxLayout()

        # 상태 인디케이터 (●)
        self.status_dot = QLabel("●")
        self.status_dot.setFont(QFont("Segoe UI", 14))
        self.status_dot.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(self.status_dot)

        # 상태 텍스트
        self.status_label = QLabel("대기 중")
        self.status_label.setFont(QFont("Malgun Gothic", 13, QFont.Weight.DemiBold))
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # 타이틀
        title = QLabel("AutoMediaFormatter")
        title.setFont(QFont("Segoe UI", 11))
        title.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(title)

        return layout

    def _create_log_area(self) -> QTextEdit:
        """로그 표시 영역"""
        self.log_area = QTextEdit()
        self.log_area.setObjectName("logArea")
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("로그가 여기에 표시됩니다...")
        return self.log_area

    def _create_right_panel(self) -> QVBoxLayout:
        """우측 패널 (통계 카드 + 버튼)"""
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # ── 통계 카드 ──
        stats_card = QFrame()
        stats_card.setObjectName("statsCard")
        stats_layout = QVBoxLayout(stats_card)
        stats_layout.setContentsMargins(14, 14, 14, 14)
        stats_layout.setSpacing(10)

        self.label_total = self._create_stat_row("총 시도", "0")
        self.label_success = self._create_stat_row("성공", "0")
        self.label_fail = self._create_stat_row("실패", "0")
        self.label_disk = self._create_stat_row("현재 Disk", "-")

        for label_pair in [self.label_total, self.label_success, self.label_fail, self.label_disk]:
            row_layout = QHBoxLayout()
            row_layout.addWidget(label_pair[0])
            row_layout.addStretch()
            row_layout.addWidget(label_pair[1])
            stats_layout.addLayout(row_layout)

        layout.addWidget(stats_card)

        # ── 버튼 그룹 ──
        layout.addSpacing(4)

        self.btn_start = QPushButton("Auto Start")
        self.btn_start.setObjectName("btnStart")

        self.btn_stop = QPushButton("Auto Stop")
        self.btn_stop.setEnabled(False)

        self.btn_clear = QPushButton("Clear Log")

        self.btn_exit = QPushButton("Exit")
        self.btn_exit.setObjectName("btnExit")

        for btn in [self.btn_start, self.btn_stop, self.btn_clear, self.btn_exit]:
            btn.setFixedHeight(38)
            layout.addWidget(btn)

        layout.addStretch()
        return layout

    def _create_stat_row(self, label_text: str, value_text: str) -> tuple[QLabel, QLabel]:
        """통계 행 생성 (라벨, 값)"""
        label = QLabel(label_text)
        label.setFont(QFont("Malgun Gothic", 11))
        label.setStyleSheet(f"color: {COLORS['text_secondary']};")

        value = QLabel(value_text)
        value.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        value.setStyleSheet(f"color: {COLORS['text_primary']};")

        return label, value

    def _connect_signals(self):
        """Signal/Slot 연결"""
        self.step_signal.connect(self._on_step_update)
        self.btn_start.clicked.connect(self.on_auto_start)
        self.btn_stop.clicked.connect(self.on_auto_stop)
        self.btn_clear.clicked.connect(self.clear_log)
        self.btn_exit.clicked.connect(self.close)

    # ── public 메서드: 외부에서 호출 ──

    def append_log(self, message: str, level: str = "info") -> None:
        """
        로그 영역에 메시지를 추가합니다.

        Args:
            message: 로그 메시지
            level: 로그 레벨 ("info", "success", "warning", "error")
        """
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")

        color_map = {
            "info": COLORS["text_primary"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "error": COLORS["error"],
        }
        color = color_map.get(level, COLORS["text_primary"])

        html = (
            f'<span style="color:{COLORS["text_muted"]}">[{timestamp}]</span> '
            f'<span style="color:{color}">{message}</span>'
        )
        self.log_area.append(html)

    def update_status(self, step: str) -> None:
        """
        상단 상태 표시를 업데이트합니다.

        Args:
            step: 현재 단계 ("대기 중", "검증 중", "포맷 준비", "포맷 중", "완료", "실패")
        """
        color = STATUS_COLORS.get(step, COLORS["text_muted"])
        self.status_dot.setStyleSheet(f"color: {color};")
        self.status_label.setText(step)
        self.status_label.setStyleSheet(f"color: {color};")

    def update_stats(self, total: int, success: int, fail: int, disk: str) -> None:
        """통계 카드를 업데이트합니다."""
        self.label_total[1].setText(str(total))
        self.label_success[1].setText(str(success))
        self.label_success[1].setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        self.label_fail[1].setText(str(fail))
        if fail > 0:
            self.label_fail[1].setStyleSheet(f"color: {COLORS['error']}; font-weight: bold;")
        self.label_disk[1].setText(disk)

    def clear_log(self) -> None:
        """로그 영역을 초기화합니다."""
        self.log_area.clear()
        self.append_log("로그를 초기화했습니다.", "info")

    def set_running(self, running: bool) -> None:
        """자동 실행 상태를 설정합니다."""
        self._is_running = running
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)

        if running:
            self.update_status("대기 중")
            self.append_log("자동 포맷 모드를 시작합니다. 디스크 삽입을 대기합니다.", "info")
        else:
            self.update_status("대기 중")
            self.append_log("자동 포맷 모드를 중지했습니다.", "warning")

    # ── Slot: Signal 수신 처리 ──

    @Slot(int, str, str)
    def _on_step_update(self, disk_number: int, step: str, message: str) -> None:
        """
        formatter의 on_step 콜백에서 emit된 Signal을 처리합니다.
        GUI 스레드에서 안전하게 실행됩니다.
        """
        # 상태 업데이트
        self.update_status(step)

        # 로그 레벨 매핑
        level_map = {
            "검증 중": "info",
            "포맷 준비": "info",
            "포맷 중": "warning",
            "완료": "success",
            "실패": "error",
        }
        level = level_map.get(step, "info")
        self.append_log(message, level)

        # 현재 디스크 표시
        self._current_disk = f"Disk {disk_number}" if disk_number >= 0 else "-"

        # 통계 업데이트 (완료/실패 시)
        if step == "완료":
            self._total_count += 1
            self._success_count += 1
        elif step == "실패":
            self._total_count += 1
            self._fail_count += 1

        self.update_stats(
            self._total_count,
            self._success_count,
            self._fail_count,
            self._current_disk,
        )

        # 완료/실패 후 상태 복원
        if step in ("완료", "실패"):
            if self._is_running:
                self.update_status("대기 중")
                self._current_disk = "-"
                self.update_stats(
                    self._total_count,
                    self._success_count,
                    self._fail_count,
                    self._current_disk,
                )

    # ── 이벤트 핸들러 (나중에 disk_watcher와 연결) ──

    def on_auto_start(self) -> None:
        """Auto Start 버튼 클릭 - 하위 클래스 또는 외부에서 오버라이드"""
        self.set_running(True)

    def on_auto_stop(self) -> None:
        """Auto Stop 버튼 클릭 - 하위 클래스 또는 외부에서 오버라이드"""
        self.set_running(False)

    def closeEvent(self, event):
        """프로그램 종료 시 정리"""
        self.set_running(False)
        event.accept()
