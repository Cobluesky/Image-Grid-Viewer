from __future__ import annotations

from math import hypot

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import QFrame

from app.core.grid import CellCoordinate, GridConfig, allocate_columns_by_width, compute_column_offsets, compute_label, global_x_to_local_x
from app.core.image_region import PixelBounds, compute_cell_bounds, compute_cell_bounds_within_bounds


class ImageCanvas(QFrame):
    cellClicked = Signal(int, int, int)
    cropSelectionChanged = Signal(bool)
    zoomChanged = Signal(int)
    roiChanged = Signal(int, bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumSize(640, 420)
        self.setMouseTracking(True)
        # 더 깊이감 있는 다크 배경과 부드러운 테두리
        self.setStyleSheet("background-color: #121212; border: 1px solid #333333; border-radius: 4px;")

        self._pixmap: QPixmap | None = None
        self._grid = GridConfig(columns=6, rows=4)
        self._selected_cell = CellCoordinate(x=1, y=1)
        self._label_scale_percent = 100
        self._label_color = QColor("#00ff00")
        self._label_visible = True
        self._selection_active = False

        self._base_scale = 1.0
        self._view_scale = 1.0
        self._pan_offset = QPointF(0.0, 0.0)
        self._drag_origin: QPointF | None = None
        self._drag_start_offset = QPointF(0.0, 0.0)
        self._press_pos: QPointF | None = None
        self._is_panning = False

        self._crop_mode = False
        self._point_start_image: QPointF | None = None
        self._point_preview_image: QPointF | None = None
        self._crop_bounds: PixelBounds | None = None
        self._rois: list[PixelBounds | None] = [None, None]
        self._roi_define_index = 0
        self._selected_roi_index = 0

    def set_image(self, pixmap: QPixmap | None) -> None:
        self._pixmap = pixmap
        self._crop_bounds = None
        self._point_start_image = None
        self._point_preview_image = None
        self._fit_image()
        self.cropSelectionChanged.emit(False)
        self.update()

    def set_grid(self, grid: GridConfig) -> None:
        self._grid = grid
        self.update()

    def set_selected_cell(self, cell: CellCoordinate) -> None:
        self._selected_cell = cell
        self.update()

    def set_selected_roi_index(self, roi_index: int) -> None:
        self._selected_roi_index = roi_index
        self.update()

    def set_selection_active(self, active: bool) -> None:
        self._selection_active = active
        self.update()

    def set_label_scale_percent(self, value: int) -> None:
        self._label_scale_percent = max(50, min(300, value))
        self.update()

    def set_label_color(self, color: QColor | str) -> None:
        self._label_color = QColor(color)
        self.update()

    def set_label_visible(self, visible: bool) -> None:
        self._label_visible = visible
        self.update()

    def set_crop_mode(self, enabled: bool) -> None:
        self._crop_mode = enabled
        # 모드에 따른 커서 변경
        self.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)
        if enabled:
            self._roi_define_index = 0
        self._cancel_point_mode()
        self.update()

    def set_rois(self, rois: list[PixelBounds | None]) -> None:
        self._rois = list(rois[:2]) + [None] * max(0, 2 - len(rois))
        self._rois = self._rois[:2]
        self.update()

    def start_roi_definition(self, roi_index: int) -> None:
        self._roi_define_index = roi_index
        self._crop_mode = False
        self._crop_bounds = None
        self.setCursor(Qt.CursorShape.CrossCursor if roi_index > 0 else Qt.CursorShape.ArrowCursor)
        self._cancel_point_mode()
        self.update()

    def clear_rois(self) -> None:
        self._rois = [None, None]
        self._roi_define_index = 0
        self._selected_roi_index = 0
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._cancel_point_mode()
        self.update()

    def clear_crop_selection(self) -> None:
        self._cancel_point_mode()
        self._crop_bounds = None
        self.cropSelectionChanged.emit(False)
        self.update()

    def has_crop_selection(self) -> bool:
        return self._crop_bounds is not None

    def get_crop_bounds(self) -> PixelBounds | None:
        return self._crop_bounds

    def get_rois(self) -> list[PixelBounds | None]:
        return list(self._rois)

    def reset_view(self) -> None:
        self._fit_image()
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._pixmap and not self._pixmap.isNull():
            self._fit_image()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self._pixmap or self._pixmap.isNull():
            return
        angle = event.angleDelta().y()
        if angle == 0:
            return

        zoom_factor = 1.15 if angle > 0 else 1 / 1.15
        old_scale = self._view_scale
        min_scale = self._base_scale * 0.1
        max_scale = self._base_scale * 50.0
        new_scale = max(min_scale, min(max_scale, old_scale * zoom_factor))

        cursor = event.position()
        image_pos_before = self._widget_to_image(cursor)
        self._view_scale = new_scale
        self._pan_offset = cursor - QPointF(
            image_pos_before.x() * self._view_scale,
            image_pos_before.y() * self._view_scale,
        )
        self._clamp_pan()
        self.zoomChanged.emit(int((self._view_scale / self._base_scale) * 100))
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._pixmap or self._pixmap.isNull():
            return

        if event.button() == Qt.MouseButton.LeftButton and (self._crop_mode or self._roi_define_index):
            self._handle_point_mode_click(event.position())
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position()
            self._is_panning = False
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            self._drag_origin = event.position()
            self._drag_start_offset = QPointF(self._pan_offset)
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._pixmap or self._pixmap.isNull():
            return

        if (
            (self._crop_mode or self._roi_define_index)
            and self._point_start_image is not None
            and not (event.buttons() & Qt.MouseButton.MiddleButton)
        ):
            self._point_preview_image = self._clamp_image_point(self._widget_to_image(event.position()))
            self.update()
            return

        if self._drag_origin is None or not (event.buttons() & Qt.MouseButton.MiddleButton):
            return

        delta = event.position() - self._drag_origin
        if hypot(delta.x(), delta.y()) >= 4:
            self._is_panning = True

        if self._is_panning:
            self._pan_offset = self._drag_start_offset + delta
            self._clamp_pan()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if not self._pixmap or self._pixmap.isNull():
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._drag_origin = None
            self._is_panning = False
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._crop_mode or self._roi_define_index:
            return

        if not self._is_panning and self._press_pos is not None:
            image_pos = self._widget_to_image(self._press_pos)
            if self._point_in_image(image_pos):
                roi_index, column, row = self._map_point_to_grid(image_pos)
                self.cellClicked.emit(roi_index, column, row)

        self._press_pos = None
        self._is_panning = False

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._pixmap or self._pixmap.isNull():
            painter.setPen(QColor("#555555"))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Image Loaded")
            return

        target = self._image_rect()
        painter.drawPixmap(target, self._pixmap, self._pixmap.rect())

        self._draw_grid_and_labels(painter)

        # Selection Highlight (강조색 개선)
        if self._selection_active:
            bounds = self._selected_cell_bounds()
            highlight = self._image_bounds_to_widget_rect(bounds)
            painter.fillRect(highlight, QColor(0, 122, 204, 40))
            painter.setPen(QPen(QColor("#007acc"), 2))
            painter.drawRect(highlight)

        # Crop Preview
        crop_bounds = self._preview_bounds() or self._crop_bounds
        if crop_bounds is not None:
            crop_rect = self._image_bounds_to_widget_rect(crop_bounds)
            painter.fillRect(crop_rect, QColor(255, 170, 0, 30))
            crop_pen = QPen(QColor("#ffb000"), 1, Qt.PenStyle.DashLine)
            painter.setPen(crop_pen)
            painter.drawRect(crop_rect)

        # ROI Boxes
        for idx, roi in enumerate(self._sorted_rois_with_index()):
            rect = self._image_bounds_to_widget_rect(roi[1])
            roi_color = QColor("#7ddc6f" if roi[0] == 1 else "#d26fff")
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(roi_color, 1.5, Qt.PenStyle.DashLine))
            painter.drawRect(rect)
            # ROI 번호 표시
            painter.setBrush(roi_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(rect.left(), rect.top() - 15, 35, 15)
            painter.setPen(QColor("#000000"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(rect.adjusted(4, -15, 0, 0), Qt.AlignmentFlag.AlignTop, f"ROI {roi[0]}")
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # --- 상단 모드 오버레이 안내 ---
        if self._crop_mode or self._roi_define_index:
            painter.save()
            overlay_rect = QRectF(10, 10, 220, 30)
            painter.setBrush(QColor(0, 0, 0, 180))
            painter.setPen(QPen(QColor("#007acc"), 1))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawRoundedRect(overlay_rect, 4, 4)
            painter.setPen(QColor("#ffffff"))
            msg = "CROP MODE: Click two points" if self._crop_mode else f"SET ROI {self._roi_define_index}: Click two points"
            painter.drawText(overlay_rect, Qt.AlignmentFlag.AlignCenter, msg)
            painter.restore()

    def _content_rect(self) -> QRectF:
        return QRectF(self.rect().adjusted(12, 12, -12, -12))

    def _fit_image(self) -> None:
        if not self._pixmap or self._pixmap.isNull():
            return
        content = self._content_rect()
        self._base_scale = min(content.width() / self._pixmap.width(), content.height() / self._pixmap.height())
        self._view_scale = self._base_scale
        self._center_image()
        self.zoomChanged.emit(100)

    def _center_image(self) -> None:
        content = self._content_rect()
        self._pan_offset = QPointF(
            content.left() + (content.width() - self._pixmap.width() * self._view_scale) / 2,
            content.top() + (content.height() - self._pixmap.height() * self._view_scale) / 2,
        )

    def _image_rect(self) -> QRectF:
        if not self._pixmap: return QRectF()
        return QRectF(self._pan_offset.x(), self._pan_offset.y(),
                      self._pixmap.width() * self._view_scale, self._pixmap.height() * self._view_scale)

    def _widget_to_image(self, pos: QPointF) -> QPointF:
        rect = self._image_rect()
        return QPointF((pos.x() - rect.left()) / self._view_scale, (pos.y() - rect.top()) / self._view_scale)

    def _point_in_image(self, image_pos: QPointF) -> bool:
        return self._pixmap and 0 <= image_pos.x() <= self._pixmap.width() and 0 <= image_pos.y() <= self._pixmap.height()

    def _clamp_image_point(self, pos: QPointF) -> QPointF:
        if not self._pixmap: return pos
        return QPointF(max(0, min(pos.x(), self._pixmap.width())), max(0, min(pos.y(), self._pixmap.height())))

    def _clamp_pan(self) -> None:
        if not self._pixmap: return
        content = self._content_rect()
        sw, sh = self._pixmap.width() * self._view_scale, self._pixmap.height() * self._view_scale
        x = content.left() + (content.width() - sw) / 2 if sw <= content.width() else min(content.left(),
                                                                                          max(content.right() - sw,
                                                                                              self._pan_offset.x()))
        y = content.top() + (content.height() - sh) / 2 if sh <= content.height() else min(content.top(),
                                                                                           max(content.bottom() - sh,
                                                                                               self._pan_offset.y()))
        self._pan_offset = QPointF(x, y)

    def _build_bounds(self, start: QPointF, end: QPointF) -> PixelBounds | None:
        l, t, r, b = int(min(start.x(), end.x())), int(min(start.y(), end.y())), int(max(start.x(), end.x())), int(
            max(start.y(), end.y()))
        return PixelBounds(left=l, top=t, right=r, bottom=b) if (r - l >= 2 and b - t >= 2) else None

    def _preview_bounds(self) -> PixelBounds | None:
        return self._build_bounds(self._point_start_image,
                                  self._point_preview_image) if self._point_start_image and self._point_preview_image else None

    def _cancel_point_mode(self) -> None:
        self._point_start_image = self._point_preview_image = None

    def _handle_point_mode_click(self, widget_pos: QPointF) -> None:
        image_pos = self._clamp_image_point(self._widget_to_image(widget_pos))
        if self._point_start_image is None:
            self._point_start_image = self._point_preview_image = image_pos
            if self._crop_mode: self.cropSelectionChanged.emit(False)
            self.update()
            return
        bounds = self._build_bounds(self._point_start_image, image_pos)
        if self._crop_mode:
            self._crop_bounds = bounds
            self.cropSelectionChanged.emit(bounds is not None)
        elif self._roi_define_index and bounds:
            self._rois[self._roi_define_index - 1] = bounds
            self.roiChanged.emit(self._roi_define_index, True)
            self._roi_define_index = 0
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self._cancel_point_mode()
        self.update()

    def _image_bounds_to_widget_rect(self, bounds: PixelBounds) -> QRectF:
        rect = self._image_rect()
        return QRectF(rect.left() + bounds.left * self._view_scale, rect.top() + bounds.top * self._view_scale,
                      bounds.width * self._view_scale, bounds.height * self._view_scale)

    def _sorted_rois_with_index(self) -> list[tuple[int, PixelBounds]]:
        return sorted([(i + 1, r) for i, r in enumerate(self._rois) if r], key=lambda x: (x[1].left, x[1].top))

    def _roi_layout(self) -> tuple[list[tuple[int, PixelBounds]], list[int], list[int]]:
        rois = self._sorted_rois_with_index()
        if not rois:
            return [], [], []
        widths = [roi.width for _, roi in rois]
        columns = allocate_columns_by_width(self._grid.columns, widths)
        offsets = compute_column_offsets(columns)
        return rois, columns, offsets

    def _map_point_to_grid(self, image_pos: QPointF) -> tuple[int, int, int]:
        rois, columns_per_roi, offsets = self._roi_layout()
        for order, (idx, roi) in enumerate(rois, start=1):
            if roi.left <= image_pos.x() <= roi.right and roi.top <= image_pos.y() <= roi.bottom:
                local_columns = max(1, columns_per_roi[order - 1])
                local_col = min(
                    local_columns,
                    max(1, int((image_pos.x() - roi.left) / roi.width * local_columns) + 1),
                )
                col = offsets[order - 1] + local_col
                row = min(self._grid.rows, max(1, int((image_pos.y() - roi.top) / roi.height * self._grid.rows) + 1))
                return idx, col, row
        col = min(self._grid.columns, max(1, int(image_pos.x() / self._pixmap.width() * self._grid.columns) + 1))
        row = min(self._grid.rows, max(1, int(image_pos.y() / self._pixmap.height() * self._grid.rows) + 1))
        return 0, col, row

    def _draw_grid_and_labels(self, painter: QPainter) -> None:
        rois, columns_per_roi, offsets = self._roi_layout()
        if not rois:
            self._draw_grid_region(
                painter,
                PixelBounds(0, 0, self._pixmap.width(), self._pixmap.height()),
                self._grid.columns,
                0,
            )
        else:
            for i, (_, roi) in enumerate(rois, 1):
                local_columns = columns_per_roi[i - 1]
                if local_columns <= 0:
                    continue
                self._draw_grid_region(painter, roi, local_columns, offsets[i - 1])

    def _draw_grid_region(self, painter: QPainter, bounds: PixelBounds, local_columns: int, global_x_offset: int) -> None:
        rect = self._image_bounds_to_widget_rect(bounds)
        cw, ch = rect.width() / local_columns, rect.height() / self._grid.rows

        # Grid Lines (Semi-transparent White)
        painter.setPen(QPen(QColor(255, 255, 255, 60), 0.5))
        for c in range(1, local_columns):
            x = rect.left() + c * cw
            painter.drawLine(x, rect.top(), x, rect.bottom())
        for r in range(1, self._grid.rows):
            y = rect.top() + r * ch
            painter.drawLine(rect.left(), y, rect.right(), y)

        if not self._label_visible:
            return

        f_size = max(6, int(min(cw, ch) * 0.25 * self._label_scale_percent / 100))
        painter.setFont(QFont("Segoe UI", f_size, QFont.Weight.DemiBold))
        for r in range(1, self._grid.rows + 1):
            for c in range(1, local_columns + 1):
                lbl = str(compute_label(self._grid, CellCoordinate(global_x_offset + c, r)))
                c_rect = QRectF(rect.left() + (c - 1) * cw, rect.top() + (r - 1) * ch, cw, ch).adjusted(2, 2, -2, -2)
                painter.setPen(QColor(0, 0, 0, 180))
                painter.drawText(c_rect.adjusted(1, 1, 1, 1), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, lbl)
                painter.setPen(self._label_color)
                painter.drawText(c_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, lbl)

    def _selected_cell_bounds(self) -> PixelBounds:
        if self._selected_roi_index:
            rois, columns_per_roi, _ = self._roi_layout()
            for order, (idx, roi) in enumerate(rois, start=1):
                if idx == self._selected_roi_index:
                    local_columns = max(1, columns_per_roi[order - 1])
                    local_x = global_x_to_local_x(self._selected_cell.x, columns_per_roi, order)
                    if not (1 <= local_x <= local_columns):
                        break
                    local_cell = CellCoordinate(
                        local_x,
                        self._selected_cell.y,
                    )
                    return compute_cell_bounds_within_bounds(roi, GridConfig(local_columns, self._grid.rows), local_cell)
        return compute_cell_bounds(self._pixmap.width(), self._pixmap.height(), self._grid, self._selected_cell)
