"""Inline video preview widget using QMediaPlayer + QVideoWidget."""

import os

from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput  # type: ignore
from PyQt6.QtMultimediaWidgets import QVideoWidget  # type: ignore
from PyQt6.QtWidgets import (  # type: ignore
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QSizePolicy,
)
from PyQt6.QtCore import Qt, QUrl  # type: ignore

from app_debug import dlog as _dlog

_MP4_MAGIC_OFFSET = 4
_MP4_MAGIC = b"ftyp"


def is_video_file(path: str) -> bool:
    """Return True when *path* is an MP4/ISO Base Media file (checks magic bytes)."""
    try:
        with open(path, "rb") as fh:
            fh.seek(_MP4_MAGIC_OFFSET)
            return fh.read(4) == _MP4_MAGIC
    except OSError:
        return False


def _ms_to_str(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


class VideoPreviewWidget(QWidget):
    """Inline video player embeddable as a preview panel."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._path: str = ""
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._video = QVideoWidget()
        self._video.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._video.setStyleSheet("background:#000;")
        layout.addWidget(self._video, 1)

        ctrl = QHBoxLayout()
        ctrl.setContentsMargins(4, 0, 4, 2)
        ctrl.setSpacing(4)

        self._btn_play = QPushButton("\u25b6")
        self._btn_play.setFixedSize(28, 22)
        self._btn_play.setEnabled(False)
        self._btn_play.clicked.connect(self._on_play_pause)
        ctrl.addWidget(self._btn_play)

        self._btn_stop = QPushButton("\u23f9")
        self._btn_stop.setFixedSize(28, 22)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        ctrl.addWidget(self._btn_stop)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.setSingleStep(1000)
        self._slider.setEnabled(False)
        self._slider.sliderMoved.connect(self._on_seek)
        ctrl.addWidget(self._slider, 1)

        self._lbl_time = QLabel("0:00 / 0:00")
        self._lbl_time.setFixedWidth(80)
        self._lbl_time.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        ctrl.addWidget(self._lbl_time)

        layout.addLayout(ctrl)

        self._player = QMediaPlayer()
        self._audio = QAudioOutput()
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video)

        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.errorOccurred.connect(self._on_error)

    # ── Public API ──────────────────────────────────────────────────────────

    def set_path(self, path: str) -> None:
        """Load *path* and auto-play. Qt reads MP4 from file content; extension is irrelevant."""
        self._player.stop()
        self._path = path
        if not path or not os.path.exists(path):
            self._btn_play.setEnabled(False)
            self._btn_stop.setEnabled(False)
            self._slider.setEnabled(False)
            self._slider.setValue(0)
            self._lbl_time.setText("0:00 / 0:00")
            return
        _dlog("VideoPreviewWidget.set_path", f"loading {path!r}")
        self._player.setSource(QUrl.fromLocalFile(path))
        self._btn_play.setEnabled(True)
        self._btn_stop.setEnabled(True)
        self._slider.setEnabled(True)
        self._player.play()

    def clear(self) -> None:
        self._player.stop()
        self._player.setSource(QUrl())
        self._btn_play.setEnabled(False)
        self._btn_stop.setEnabled(False)
        self._slider.setEnabled(False)
        self._slider.setValue(0)
        self._lbl_time.setText("0:00 / 0:00")
        self._path = ""

    # ── Slots ───────────────────────────────────────────────────────────────

    def _on_play_pause(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_stop(self) -> None:
        self._player.stop()

    def _on_seek(self, ms: int) -> None:
        self._player.setPosition(ms)

    def _on_state_changed(self, state) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._btn_play.setText("\u23f8" if playing else "\u25b6")

    def _on_duration_changed(self, ms: int) -> None:
        self._slider.setRange(0, ms)
        self._lbl_time.setText(
            f"{_ms_to_str(self._player.position())} / {_ms_to_str(ms)}")

    def _on_position_changed(self, ms: int) -> None:
        if not self._slider.isSliderDown():
            self._slider.setValue(ms)
        self._lbl_time.setText(
            f"{_ms_to_str(ms)} / {_ms_to_str(self._player.duration())}")

    def _on_error(self, error, msg: str) -> None:
        _dlog("VideoPreviewWidget._on_error", f"{error}: {msg}")
