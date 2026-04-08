from __future__ import annotations

from math import ceil, floor, hypot

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import QFrame

from app.core.grid import (
    CellCoordinate,
    GridConfig,
    allocate_columns_by_width,
    compute_column_offsets,
    compute_label,
    global_x_to_local_x,
)
from app.core.image_region import PixelBounds, compute_cell_bounds, compute_cell_bounds_within_bounds
from app.core.tiled_image import TiledImageSource


class TiledImageCanvas(QFrame):
    cellClicked = Signal(int, int, int)
    cropSelectionChanged = Signal(bool)
    zoomChanged = Signal(int)
    roiChanged = Signal(int, bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumSize(640, 420)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: #121212; border: 1px solid #333333; border-radius: 4px;")

        self._image_source: TiledImageSource | None = None
        self._grid = GridConfig(columns=6, rows=4)
        self._selected_cell = CellCoordinate(x=1, y=1)
        self._selected_roi_index = 0
        self._selection_active = False
        self._label_scale_percent = 100
        self._label_color = QColor("#00ff00")
        self._label_visible = True

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

    def set_image_source(self, image_source: TiledImageSource | None) -> None:
        self._image_source = image_source
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
        if self._has_image():
            self._fit_image()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self._has_image():
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
        if not self._has_image():
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
        if not self._has_image():
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
        if not self._has_image():
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
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            if not self._has_image():
                painter.setPen(QColor("#555555"))
                painter.setFont(QFont("Segoe UI", 11))
                painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Image Loaded")
                return

            target = self._image_rect()
            visible_target = target.intersected(self._content_rect())
            if not visible_target.isEmpty():
                visible_bounds = self._widget_rect_to_image_bounds(visible_target)
                tile = self._image_source.render_viewport(
                    visible_bounds,
                    max(1, int(visible_target.width())),
                    max(1, int(visible_target.height())),
                )
                painter.drawPixmap(visible_target, tile, tile.rect())

            self._draw_grid_and_labels(painter)

            if self._selection_active:
                bounds = self._selected_cell_bounds()
                highlight = self._image_bounds_to_widget_rect(bounds)
                painter.fillRect(highlight, QColor(0, 122, 204, 40))
                painter.setPen(QPen(QColor("#007acc"), 2))
                painter.drawRect(highlight)

            crop_bounds = self._preview_bounds() or self._crop_bounds
            if crop_bounds is not None:
                crop_rect = self._image_bounds_to_widget_rect(crop_bounds)
                painter.fillRect(crop_rect, QColor(255, 170, 0, 30))
                painter.setPen(QPen(QColor("#ffb000"), 1, Qt.PenStyle.DashLine))
                painter.drawRect(crop_rect)

            for roi_index, roi_bounds in self._sorted_rois_with_index():
                rect = self._image_bounds_to_widget_rect(roi_bounds)
                roi_color = QColor("#7ddc6f" if roi_index == 1 else "#d26fff")
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(roi_color, 1.5, Qt.PenStyle.DashLine))
                painter.drawRect(rect)
                painter.setBrush(roi_color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(rect.left(), rect.top() - 15, 35, 15)
                painter.setPen(QColor("#000000"))
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                painter.drawText(rect.adjusted(4, -15, 0, 0), Qt.AlignmentFlag.AlignTop, f"ROI {roi_index}")
            painter.setBrush(Qt.BrushStyle.NoBrush)

            if self._crop_mode or self._roi_define_index:
                painter.save()
                overlay_rect = QRectF(10, 10, 220, 30)
                painter.setBrush(QColor(0, 0, 0, 180))
                painter.setPen(QPen(QColor("#007acc"), 1))
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.drawRoundedRect(overlay_rect, 4, 4)
                painter.setPen(QColor("#ffffff"))
                message = (
                    "CROP MODE: Click two points"
                    if self._crop_mode
                    else f"SET ROI {self._roi_define_index}: Click two points"
                )
                painter.drawText(overlay_rect, Qt.AlignmentFlag.AlignCenter, message)
                painter.restore()
        finally:
            if painter.isActive():
                painter.end()

    def _content_rect(self) -> QRectF:
        return QRectF(self.rect().adjusted(12, 12, -12, -12))

    def _has_image(self) -> bool:
        return self._image_source is not None and self._image_source.width > 0 and self._image_source.height > 0

    def _image_width(self) -> int:
        return 0 if self._image_source is None else self._image_source.width

    def _image_height(self) -> int:
        return 0 if self._image_source is None else self._image_source.height

    def _fit_image(self) -> None:
        if not self._has_image():
            return
        content = self._content_rect()
        self._base_scale = min(content.width() / self._image_width(), content.height() / self._image_height())
        self._view_scale = self._base_scale
        self._center_image()
        self.zoomChanged.emit(100)

    def _center_image(self) -> None:
        content = self._content_rect()
        self._pan_offset = QPointF(
            content.left() + (content.width() - self._image_width() * self._view_scale) / 2,
            content.top() + (content.height() - self._image_height() * self._view_scale) / 2,
        )

    def _image_rect(self) -> QRectF:
        if not self._has_image():
            return QRectF()
        return QRectF(
            self._pan_offset.x(),
            self._pan_offset.y(),
            self._image_width() * self._view_scale,
            self._image_height() * self._view_scale,
        )

    def _widget_to_image(self, pos: QPointF) -> QPointF:
        rect = self._image_rect()
        return QPointF((pos.x() - rect.left()) / self._view_scale, (pos.y() - rect.top()) / self._view_scale)

    def _widget_rect_to_image_bounds(self, rect: QRectF) -> PixelBounds:
        image_rect = self._image_rect()
        width = self._image_width()
        height = self._image_height()
        left = int(max(0, min(width, floor((rect.left() - image_rect.left()) / self._view_scale))))
        top = int(max(0, min(height, floor((rect.top() - image_rect.top()) / self._view_scale))))
        right = int(max(left + 1, min(width, ceil((rect.right() - image_rect.left()) / self._view_scale))))
        bottom = int(max(top + 1, min(height, ceil((rect.bottom() - image_rect.top()) / self._view_scale))))
        return PixelBounds(left, top, right, bottom)

    def _point_in_image(self, image_pos: QPointF) -> bool:
        return 0 <= image_pos.x() <= self._image_width() and 0 <= image_pos.y() <= self._image_height()

    def _clamp_image_point(self, pos: QPointF) -> QPointF:
        return QPointF(
            max(0, min(pos.x(), self._image_width())),
            max(0, min(pos.y(), self._image_height())),
        )

    def _clamp_pan(self) -> None:
        if not self._has_image():
            return
        content = self._content_rect()
        scaled_width = self._image_width() * self._view_scale
        scaled_height = self._image_height() * self._view_scale

        x = (
            content.left() + (content.width() - scaled_width) / 2
            if scaled_width <= content.width()
            else min(content.left(), max(content.right() - scaled_width, self._pan_offset.x()))
        )
        y = (
            content.top() + (content.height() - scaled_height) / 2
            if scaled_height <= content.height()
            else min(content.top(), max(content.bottom() - scaled_height, self._pan_offset.y()))
        )
        self._pan_offset = QPointF(x, y)

    def _build_bounds(self, start: QPointF, end: QPointF) -> PixelBounds | None:
        left = int(floor(min(start.x(), end.x())))
        top = int(floor(min(start.y(), end.y())))
        right = int(ceil(max(start.x(), end.x())))
        bottom = int(ceil(max(start.y(), end.y())))
        return PixelBounds(left=left, top=top, right=right, bottom=bottom) if (right - left >= 2 and bottom - top >= 2) else None

    def _preview_bounds(self) -> PixelBounds | None:
        if self._point_start_image is None or self._point_preview_image is None:
            return None
        return self._build_bounds(self._point_start_image, self._point_preview_image)

    def _cancel_point_mode(self) -> None:
        self._point_start_image = None
        self._point_preview_image = None

    def _handle_point_mode_click(self, widget_pos: QPointF) -> None:
        image_pos = self._clamp_image_point(self._widget_to_image(widget_pos))
        if self._point_start_image is None:
            self._point_start_image = image_pos
            self._point_preview_image = image_pos
            if self._crop_mode:
                self.cropSelectionChanged.emit(False)
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
        return QRectF(
            rect.left() + bounds.left * self._view_scale,
            rect.top() + bounds.top * self._view_scale,
            bounds.width * self._view_scale,
            bounds.height * self._view_scale,
        )

    def _sorted_rois_with_index(self) -> list[tuple[int, PixelBounds]]:
        return sorted(
            [(index + 1, roi) for index, roi in enumerate(self._rois) if roi is not None],
            key=lambda item: (item[1].left, item[1].top),
        )

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
        for order, (roi_index, roi_bounds) in enumerate(rois, start=1):
            if roi_bounds.left <= image_pos.x() <= roi_bounds.right and roi_bounds.top <= image_pos.y() <= roi_bounds.bottom:
                local_columns = max(1, columns_per_roi[order - 1])
                local_column = min(
                    local_columns,
                    max(1, int((image_pos.x() - roi_bounds.left) / roi_bounds.width * local_columns) + 1),
                )
                global_column = offsets[order - 1] + local_column
                row = min(
                    self._grid.rows,
                    max(1, int((image_pos.y() - roi_bounds.top) / roi_bounds.height * self._grid.rows) + 1),
                )
                return roi_index, global_column, row

        column = min(self._grid.columns, max(1, int(image_pos.x() / self._image_width() * self._grid.columns) + 1))
        row = min(self._grid.rows, max(1, int(image_pos.y() / self._image_height() * self._grid.rows) + 1))
        return 0, column, row

    def _draw_grid_and_labels(self, painter: QPainter) -> None:
        rois, columns_per_roi, offsets = self._roi_layout()
        if not rois:
            self._draw_grid_region(
                painter,
                PixelBounds(0, 0, self._image_width(), self._image_height()),
                self._grid.columns,
                0,
            )
            return

        for order, (_, roi_bounds) in enumerate(rois, start=1):
            local_columns = columns_per_roi[order - 1]
            if local_columns <= 0:
                continue
            self._draw_grid_region(painter, roi_bounds, local_columns, offsets[order - 1])

    def _draw_grid_region(self, painter: QPainter, bounds: PixelBounds, local_columns: int, global_x_offset: int) -> None:
        rect = self._image_bounds_to_widget_rect(bounds)
        cell_width = rect.width() / local_columns
        cell_height = rect.height() / self._grid.rows

        painter.setPen(QPen(QColor(255, 255, 255, 60), 0.5))
        for column in range(1, local_columns):
            x = rect.left() + column * cell_width
            painter.drawLine(x, rect.top(), x, rect.bottom())
        for row in range(1, self._grid.rows):
            y = rect.top() + row * cell_height
            painter.drawLine(rect.left(), y, rect.right(), y)

        if not self._label_visible:
            return

        font_size = max(6, int(min(cell_width, cell_height) * 0.25 * self._label_scale_percent / 100))
        painter.setFont(QFont("Segoe UI", font_size, QFont.Weight.DemiBold))
        for row in range(1, self._grid.rows + 1):
            for column in range(1, local_columns + 1):
                label = str(compute_label(self._grid, CellCoordinate(global_x_offset + column, row)))
                cell_rect = QRectF(
                    rect.left() + (column - 1) * cell_width,
                    rect.top() + (row - 1) * cell_height,
                    cell_width,
                    cell_height,
                ).adjusted(2, 2, -2, -2)
                painter.setPen(QColor(0, 0, 0, 180))
                painter.drawText(cell_rect.adjusted(1, 1, 1, 1), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, label)
                painter.setPen(self._label_color)
                painter.drawText(cell_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, label)

    def _selected_cell_bounds(self) -> PixelBounds:
        if self._selected_roi_index:
            rois, columns_per_roi, _ = self._roi_layout()
            for order, (roi_index, roi_bounds) in enumerate(rois, start=1):
                if roi_index == self._selected_roi_index:
                    local_columns = max(1, columns_per_roi[order - 1])
                    local_x = global_x_to_local_x(self._selected_cell.x, columns_per_roi, order)
                    if not (1 <= local_x <= local_columns):
                        break
                    local_cell = CellCoordinate(local_x, self._selected_cell.y)
                    return compute_cell_bounds_within_bounds(
                        roi_bounds,
                        GridConfig(local_columns, self._grid.rows),
                        local_cell,
                    )
        return compute_cell_bounds(self._image_width(), self._image_height(), self._grid, self._selected_cell)
