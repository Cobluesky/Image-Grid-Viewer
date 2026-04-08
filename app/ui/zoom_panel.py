from __future__ import annotations
from collections.abc import Callable
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QScrollArea, QSlider, QSpinBox, QVBoxLayout, QWidget, QPushButton
)


class ZoomPanel(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(250, 280)
        self.setStyleSheet("""
            QScrollArea { border: 1px solid #333; background-color: #000; border-radius: 4px; }
            QSlider::groove:horizontal { height: 4px; background: #333; }
            QSlider::handle:horizontal { background: #007acc; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }
            QPushButton#ActionButton { font-size: 10px; padding: 2px; min-width: 60px; background: #252525; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(8)

        self._status = QLabel("Zoom View")
        self._status.setStyleSheet("color: #007acc; font-size: 10px; font-weight: bold;")
        layout.addWidget(self._status)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._image_label)
        layout.addWidget(self._scroll)

        zoom_ctrls = QHBoxLayout()
        self._save_button = QPushButton("Save")
        self._save_button.setObjectName("ActionButton")
        self._save_button.setEnabled(False)
        self._save_button.clicked.connect(self._save_current_pixmap)
        zoom_ctrls.addWidget(self._save_button)

        self._zoom_input = QSpinBox()
        self._zoom_input.setRange(50, 800)
        self._zoom_input.setSuffix("%")
        self._zoom_input.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        zoom_ctrls.addWidget(self._zoom_input)
        layout.addLayout(zoom_ctrls)

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(50, 800)
        layout.addWidget(self._zoom_slider)

        self._pixmap: QPixmap | None = None
        self._save_handler: Callable[[str, str], bool] | None = None
        self._zoom_percent = 200
        self._zoom_slider.setValue(200)
        self._zoom_input.setValue(200)

        self._zoom_slider.valueChanged.connect(self.set_zoom_percent)
        self._zoom_input.valueChanged.connect(self.set_zoom_percent)

    def set_zoom_content(
        self,
        pixmap: QPixmap | None,
        save_handler: Callable[[str, str], bool] | None,
    ) -> None:
        self._pixmap = pixmap
        self._save_handler = save_handler
        self._refresh()

    def set_zoom_pixmap(self, pixmap: QPixmap | None) -> None:
        self._pixmap = pixmap
        self._save_handler = None
        self._refresh()

    def set_zoom_percent(self, value: int) -> None:
        self._zoom_percent = max(50, min(800, value))
        self._zoom_slider.blockSignals(True);
        self._zoom_slider.setValue(self._zoom_percent);
        self._zoom_slider.blockSignals(False)
        self._zoom_input.blockSignals(True);
        self._zoom_input.setValue(self._zoom_percent);
        self._zoom_input.blockSignals(False)
        self._refresh()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        self.set_zoom_percent(self._zoom_percent + (25 if delta > 0 else -25))

    def _refresh(self) -> None:
        if not self._pixmap or self._pixmap.isNull():
            self._image_label.setPixmap(QPixmap())
            self._status.setText("Zoom View: -")
            self._save_button.setEnabled(False)
            return
        w, h = self._pixmap.width() * self._zoom_percent / 100, self._pixmap.height() * self._zoom_percent / 100
        scaled = self._pixmap.scaled(int(w), int(h), Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
        self._image_label.setPixmap(scaled)
        self._status.setText(f"Zoom View: {self._zoom_percent}% ({self._pixmap.width()}x{self._pixmap.height()})")
        self._save_button.setEnabled(True)

    def _save_current_pixmap(self) -> None:
        if not self._pixmap or self._pixmap.isNull():
            return

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Cell Image As",
            "cell_preview.png",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;Bitmap Image (*.bmp)",
        )
        if not path:
            return

        file_format = "PNG"
        if "JPEG" in selected_filter:
            file_format = "JPG"
        elif "Bitmap" in selected_filter:
            file_format = "BMP"
        if self._save_handler is not None:
            self._save_handler(path, file_format)
            return
        self._pixmap.save(path, file_format)
