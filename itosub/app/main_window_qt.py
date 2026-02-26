from __future__ import annotations

try:
    from PyQt6 import QtCore, QtWidgets

    _PYQT_IMPORT_ERROR: ModuleNotFoundError | None = None
except ModuleNotFoundError as e:  # pragma: no cover - import guard path
    QtCore = None  # type: ignore[assignment]
    QtWidgets = None  # type: ignore[assignment]
    _PYQT_IMPORT_ERROR = e


if QtWidgets is not None:
    class MainWindow(QtWidgets.QMainWindow):
        run_requested = QtCore.pyqtSignal()
        stop_requested = QtCore.pyqtSignal()
        settings_requested = QtCore.pyqtSignal()
        test_mic_requested = QtCore.pyqtSignal()

        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("ItoSub")
            self.resize(760, 420)
            self._running = False

            root = QtWidgets.QWidget(self)
            self.setCentralWidget(root)
            lay = QtWidgets.QVBoxLayout(root)
            lay.setContentsMargins(22, 20, 22, 20)
            lay.setSpacing(16)

            title = QtWidgets.QLabel("ItoSub", root)
            title.setObjectName("title")
            lay.addWidget(title)

            self.status_label = QtWidgets.QLabel("", root)
            self.status_label.setObjectName("status")
            self.status_label.setWordWrap(True)
            lay.addWidget(self.status_label)

            btn_row = QtWidgets.QHBoxLayout()
            btn_row.setSpacing(10)
            self.btn_run = QtWidgets.QPushButton("Start", root)
            self.btn_run.setObjectName("primary")
            self.btn_settings = QtWidgets.QPushButton("Settings", root)
            self.btn_test_mic = QtWidgets.QPushButton("Test Mic", root)
            btn_row.addWidget(self.btn_run)
            btn_row.addWidget(self.btn_settings)
            btn_row.addWidget(self.btn_test_mic)
            btn_row.addStretch(1)
            lay.addLayout(btn_row)

            meter_wrap = QtWidgets.QFrame(root)
            meter_wrap.setObjectName("card")
            meter_lay = QtWidgets.QVBoxLayout(meter_wrap)
            meter_lay.setContentsMargins(14, 12, 14, 12)
            meter_lay.setSpacing(8)
            meter_title = QtWidgets.QLabel("Mic Level", meter_wrap)
            meter_title.setObjectName("subhead")
            self.meter = QtWidgets.QProgressBar(meter_wrap)
            self.meter.setRange(0, 100)
            self.meter.setValue(0)
            self.meter.setTextVisible(False)
            meter_lay.addWidget(meter_title)
            meter_lay.addWidget(self.meter)
            lay.addWidget(meter_wrap)
            lay.addStretch(1)

            self.btn_run.clicked.connect(self._on_run_clicked)
            self.btn_settings.clicked.connect(self.settings_requested.emit)
            self.btn_test_mic.clicked.connect(self.test_mic_requested.emit)

            self.setStyleSheet(
                """
                QMainWindow { background: #121416; color: #e8ecef; }
                QLabel#title { font-size: 34px; font-weight: 700; letter-spacing: 0.3px; }
                QLabel#status { color: #a7b0b8; font-size: 13px; }
                QLabel#subhead { color: #b8c1c8; font-size: 12px; font-weight: 600; }
                QFrame#card {
                    background: #1a1e22;
                    border: 1px solid #2a3138;
                    border-radius: 14px;
                }
                QPushButton {
                    background: #22272d;
                    border: 1px solid #313840;
                    border-radius: 10px;
                    color: #e7edf3;
                    padding: 10px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover { background: #2a3037; }
                QPushButton#primary {
                    background: #c8f25f;
                    color: #172005;
                    border-color: #c8f25f;
                }
                QPushButton#primary:hover { background: #d3f67f; border-color: #d3f67f; }
                QProgressBar {
                    background: #13181d;
                    border: 1px solid #2f3740;
                    border-radius: 8px;
                    height: 16px;
                }
                QProgressBar::chunk {
                    background: #6ec7ff;
                    border-radius: 8px;
                }
                """
            )

        def _on_run_clicked(self) -> None:
            if self._running:
                self.stop_requested.emit()
            else:
                self.run_requested.emit()

        def set_running(self, running: bool) -> None:
            self._running = running
            self.btn_run.setText("Stop" if running else "Start")

        def set_status_text(self, text: str) -> None:
            self.status_label.setText(text)

        def set_meter_level(self, level_0_to_100: int) -> None:
            self.meter.setValue(max(0, min(100, int(level_0_to_100))))
else:
    class MainWindow:
        def __init__(self) -> None:
            raise ModuleNotFoundError(
                "PyQt6 is required for MainWindow. Install with: python -m pip install PyQt6"
            ) from _PYQT_IMPORT_ERROR

