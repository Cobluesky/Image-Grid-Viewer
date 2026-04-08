from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget, QGroupBox, QCheckBox
)
from app.core.grid import MAX_COLUMNS, MAX_ROWS, GridConfig, allocate_columns_by_width, compute_label, global_x_to_local_x
from app.core.image_region import PixelBounds, compute_cell_bounds, compute_cell_bounds_within_bounds
from app.core.tiled_image import TiledImageSource
from app.models.state import AppState
from app.ui.tiled_image_canvas import TiledImageCanvas
from app.ui.zoom_panel import ZoomPanel

DARK_STYLE = """
QMainWindow { background-color: #1a1a1a; }
QWidget { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
QGroupBox { 
    font-weight: bold; border: 1px solid #333333; border-radius: 6px; 
    margin-top: 12px; padding-top: 10px; color: #007acc;
}
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px; }
QPushButton { 
    background-color: #333333; border: 1px solid #444444; border-radius: 4px; 
    padding: 6px; min-height: 20px; color: #ffffff;
}
QPushButton:hover { background-color: #444444; }
QPushButton#Primary { background-color: #007acc; border: none; font-weight: bold; }
QPushButton#Primary:hover { background-color: #0098ff; }
QPushButton#Danger { color: #ff6b6b; border: 1px solid #663333; }
QPushButton#Danger:hover { background-color: #442222; }
QPushButton:checked { background-color: #005a9e; border-color: #007acc; }
QSpinBox { 
    background-color: #252525; border: 1px solid #333333; border-radius: 4px; 
    padding: 4px; color: #ffffff; 
}
QLabel#InfoValue { color: #aaaaaa; font-family: 'Consolas', monospace; }
"""

COLOR_DIALOG_STYLE = """
QColorDialog {
    background-color: #111111;
}
QWidget {
    background-color: #111111;
    color: #e0e0e0;
}
QLabel {
    color: #d0d0d0;
}
QPushButton {
    background-color: #2a2a2a;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 6px 10px;
    color: #ffffff;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #3a3a3a;
}
QSpinBox, QLineEdit {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    border-radius: 4px;
    color: #ffffff;
    padding: 4px;
}
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.state = AppState()
        self._image_source: TiledImageSource | None = None
        self.setWindowTitle("Image Grid Viewer")
        self.resize(1300, 900)
        self.setStyleSheet(DARK_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(15)

        self.canvas = TiledImageCanvas()
        root.addWidget(self.canvas, stretch=4)

        # Sidebar setup
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sidebar_scroll.setStyleSheet("background: transparent;")
        sidebar_host = QWidget()
        sidebar = QVBoxLayout(sidebar_host)
        sidebar.setContentsMargins(0, 0, 5, 0)
        sidebar.setSpacing(10)

        # --- File & Tools ---
        file_group = QGroupBox("TOOLS")
        file_l = QVBoxLayout(file_group)
        self.open_button = QPushButton("Open Image...")
        self.open_button.setObjectName("Primary")
        self.reset_view_button = QPushButton("Reset View")
        self.crop_mode_button = QPushButton("Crop Mode")
        self.crop_mode_button.setCheckable(True)
        self.apply_crop_button = QPushButton("Apply Crop")
        self.cancel_crop_button = QPushButton("Cancel Crop")
        self.apply_crop_button.setEnabled(False)
        self.cancel_crop_button.setEnabled(False)
        file_l.addWidget(self.open_button)
        file_l.addWidget(self.reset_view_button)
        file_l.addWidget(self.crop_mode_button)
        file_l.addWidget(self.apply_crop_button)
        file_l.addWidget(self.cancel_crop_button)
        sidebar.addWidget(file_group)

        # --- ROI Controls ---
        roi_group = QGroupBox("REGION OF INTEREST")
        roi_l = QVBoxLayout(roi_group)
        self.roi1_button = QPushButton("Define ROI 1")
        self.roi1_button.setCheckable(True)
        self.roi2_button = QPushButton("Define ROI 2")
        self.roi2_button.setCheckable(True)
        self.clear_roi_button = QPushButton("Clear All ROIs")
        self.clear_roi_button.setObjectName("Danger")
        roi_l.addWidget(self.roi1_button)
        roi_l.addWidget(self.roi2_button)
        self.roi1_coords = self._create_roi_coord_group("ROI 1")
        self.roi2_coords = self._create_roi_coord_group("ROI 2")
        roi_l.addWidget(self.roi1_coords["group"])
        roi_l.addWidget(self.roi2_coords["group"])
        roi_l.addWidget(self.clear_roi_button)
        sidebar.addWidget(roi_group)

        # --- Grid Config ---
        grid_group = QGroupBox("GRID CONFIG")
        grid_l = QFormLayout(grid_group)
        self.columns_input = QSpinBox()
        self.columns_input.setRange(1, MAX_COLUMNS)
        self.rows_input = QSpinBox()
        self.rows_input.setRange(1, MAX_ROWS)
        self.cell_x_input = QSpinBox()
        self.cell_y_input = QSpinBox()
        self.cell_x_input.setRange(1, self.state.grid.columns)
        self.cell_y_input.setRange(1, self.state.grid.rows)
        self.cell_x_input.setValue(self.state.selected_cell.x)
        self.cell_y_input.setValue(self.state.selected_cell.y)
        self.label_scale_input = QSpinBox()
        self.label_scale_input.setRange(50, 300)
        self.label_scale_input.setSuffix("%")
        self.label_toggle = QCheckBox("Show Labels")
        self.label_toggle.setChecked(self.state.label_visible)
        self.apply_selection_button = QPushButton("Apply Selection")
        self.unselect_button = QPushButton("Unselect")
        self.label_color_button = QPushButton("Pick Color")
        grid_l.addRow("Cols:", self.columns_input)
        grid_l.addRow("Rows:", self.rows_input)
        grid_l.addRow("Cell X:", self.cell_x_input)
        grid_l.addRow("Cell Y:", self.cell_y_input)
        grid_l.addRow("", self.apply_selection_button)
        grid_l.addRow("", self.unselect_button)
        grid_l.addRow("Label Size:", self.label_scale_input)
        grid_l.addRow("", self.label_toggle)
        grid_l.addRow("Color:", self.label_color_button)
        sidebar.addWidget(grid_group)

        # --- Status Info ---
        status_group = QGroupBox("STATUS")
        status_l = QVBoxLayout(status_group)
        self.image_info = QLabel("No Image")
        self.label_info = QLabel("Label: -")
        for lbl in (self.image_info, self.label_info):
            lbl.setWordWrap(True)
            lbl.setObjectName("InfoValue")
            status_l.addWidget(lbl)

        self.zoom_panel = ZoomPanel()
        status_l.addWidget(self.zoom_panel)
        sidebar.addWidget(status_group)

        sidebar.addStretch(1)
        sidebar_scroll.setWidget(sidebar_host)
        root.addWidget(sidebar_scroll, stretch=1)

        # Signal Connections
        self.open_button.clicked.connect(self._open_image)
        self.reset_view_button.clicked.connect(self.canvas.reset_view)
        self.crop_mode_button.toggled.connect(self._handle_crop_mode_toggled)
        self.roi1_button.toggled.connect(lambda c: self._handle_roi_button_toggled(1, c))
        self.roi2_button.toggled.connect(lambda c: self._handle_roi_button_toggled(2, c))
        self.clear_roi_button.clicked.connect(self._clear_rois)
        self.apply_crop_button.clicked.connect(self._apply_crop)
        self.cancel_crop_button.clicked.connect(self._cancel_crop)
        self.columns_input.valueChanged.connect(self._handle_grid_change)
        self.rows_input.valueChanged.connect(self._handle_grid_change)
        self.label_scale_input.valueChanged.connect(self._handle_label_scale_change)
        self.apply_selection_button.clicked.connect(self._apply_selection_from_inputs)
        self.unselect_button.clicked.connect(self._clear_selection)
        self.label_toggle.toggled.connect(self._handle_label_toggle)
        self.label_color_button.clicked.connect(self._pick_label_color)
        self.canvas.cellClicked.connect(self._handle_canvas_click)
        self.canvas.cropSelectionChanged.connect(self._handle_crop_selection_changed)
        self.canvas.roiChanged.connect(self._handle_roi_changed)

        # Initial State
        self.columns_input.setValue(self.state.grid.columns)
        self.rows_input.setValue(self.state.grid.rows)
        self.label_scale_input.setValue(self.state.label_scale_percent)
        self.canvas.set_label_visible(self.state.label_visible)
        self.canvas.set_label_color(self.state.label_color_hex)
        self._update_label_color_button()
        self._update_roi_input_ranges()
        self._sync_roi_inputs()

    def _create_roi_coord_group(self, title: str) -> dict[str, object]:
        group = QGroupBox(title)
        layout = QFormLayout(group)

        left = QSpinBox()
        top = QSpinBox()
        right = QSpinBox()
        bottom = QSpinBox()
        for widget in (left, top, right, bottom):
            widget.setRange(0, 999999)

        apply_button = QPushButton("Apply ROI")
        clear_button = QPushButton("Clear ROI")

        layout.addRow("Left:", left)
        layout.addRow("Top:", top)
        layout.addRow("Right:", right)
        layout.addRow("Bottom:", bottom)
        layout.addRow("", apply_button)
        layout.addRow("", clear_button)

        roi_index = 1 if title.endswith("1") else 2
        apply_button.clicked.connect(lambda: self._apply_roi_from_inputs(roi_index))
        clear_button.clicked.connect(lambda: self._clear_single_roi(roi_index))

        return {
            "group": group,
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "apply": apply_button,
            "clear": clear_button,
        }

    def _open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if not path: return
        try:
            self._image_source = TiledImageSource(Path(path))
            self.state.image.width = self._image_source.width
            self.state.image.height = self._image_source.height
            self.state.image.path = Path(path)
            self.canvas.set_image_source(self._image_source)
            self._clear_rois()
            self._update_roi_input_ranges()
            self._sync_roi_inputs()
            self._refresh_summary()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _handle_grid_change(self) -> None:
        defined_roi_count = sum(1 for roi in self.state.rois if roi.bounds is not None)
        columns = self.columns_input.value()
        if defined_roi_count > 0 and columns < defined_roi_count:
            columns = defined_roi_count
            self.columns_input.blockSignals(True)
            self.columns_input.setValue(columns)
            self.columns_input.blockSignals(False)

        self.state.grid = self.state.grid.__class__(columns=columns, rows=self.rows_input.value())
        self.cell_x_input.setRange(1, self.state.grid.columns)
        self.cell_y_input.setRange(1, self.state.grid.rows)
        self.state.selected_cell = self.state.selected_cell.__class__(
            x=min(self.state.selected_cell.x, self.state.grid.columns),
            y=min(self.state.selected_cell.y, self.state.grid.rows),
        )
        self.cell_x_input.setValue(self.state.selected_cell.x)
        self.cell_y_input.setValue(self.state.selected_cell.y)
        self.canvas.set_grid(self.state.grid)
        self._refresh_summary()

    def _handle_canvas_click(self, r_idx: int, x: int, y: int) -> None:
        self.state.selected_roi_index = r_idx
        self.state.selected_cell = self.state.selected_cell.__class__(x=x, y=y)
        self.state.selection_active = True
        self.cell_x_input.setValue(x)
        self.cell_y_input.setValue(y)
        self.canvas.set_selected_cell(self.state.selected_cell)
        self.canvas.set_selected_roi_index(r_idx)
        self.canvas.set_selection_active(True)
        self._refresh_summary()

    def _apply_selection_from_inputs(self) -> None:
        if not self._image_source:
            return
        self.state.selected_cell = self.state.selected_cell.__class__(
            x=self.cell_x_input.value(),
            y=self.cell_y_input.value(),
        )
        self.state.selection_active = True
        self.canvas.set_selected_cell(self.state.selected_cell)
        self.canvas.set_selected_roi_index(self.state.selected_roi_index)
        self.canvas.set_selection_active(True)
        self._refresh_summary()

    def _clear_selection(self) -> None:
        self.state.selection_active = False
        self.state.selected_roi_index = 0
        self.canvas.set_selected_roi_index(0)
        self.canvas.set_selection_active(False)
        self._refresh_summary()

    def _handle_roi_button_toggled(self, idx: int, checked: bool) -> None:
        if checked:
            self.crop_mode_button.setChecked(False)
            self.canvas.clear_crop_selection()
            if idx == 1:
                self.roi2_button.setChecked(False)
            else:
                self.roi1_button.setChecked(False)
            self.canvas.start_roi_definition(idx)
        else:
            self.canvas.start_roi_definition(0)

    def _handle_roi_changed(self, idx: int, defined: bool) -> None:
        if defined:
            self.state.rois[idx - 1].bounds = self.canvas.get_rois()[idx - 1]
            self.state.selected_roi_index = 0
            self.state.selection_active = False
            self.canvas.set_selected_roi_index(0)
            self.canvas.set_selection_active(False)
            self.roi1_button.setChecked(False)
            self.roi2_button.setChecked(False)
            self._sync_roi_inputs()
            self._refresh_summary()

    def _clear_rois(self) -> None:
        for r in self.state.rois:
            r.bounds = None
        self.canvas.clear_rois()
        self.state.selected_roi_index = 0
        self.state.selection_active = False
        self.canvas.set_selected_roi_index(0)
        self.canvas.set_selection_active(False)
        self._sync_roi_inputs()
        self._refresh_summary()

    def _clear_single_roi(self, roi_index: int) -> None:
        self.state.rois[roi_index - 1].bounds = None
        self.canvas.set_rois([r.bounds for r in self.state.rois])
        if self.state.selected_roi_index == roi_index:
            self.state.selected_roi_index = 0
            self.state.selection_active = False
            self.canvas.set_selected_roi_index(0)
            self.canvas.set_selection_active(False)
        self._sync_roi_inputs()
        self._refresh_summary()

    def _handle_label_scale_change(self) -> None:
        self.canvas.set_label_scale_percent(self.label_scale_input.value())

    def _handle_label_toggle(self, checked: bool) -> None:
        self.state.label_visible = checked
        self.canvas.set_label_visible(checked)

    def _pick_label_color(self) -> None:
        dialog = QColorDialog(QColor(self.state.label_color_hex), self)
        dialog.setWindowTitle("Select Label Color")
        dialog.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, False)
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        dialog.setStyleSheet(COLOR_DIALOG_STYLE)
        if dialog.exec():
            color = dialog.selectedColor()
            if color.isValid():
                self.state.label_color_hex = color.name()
                self.canvas.set_label_color(color)
                self._update_label_color_button()

    def _update_label_color_button(self) -> None:
        c = self.state.label_color_hex
        self.label_color_button.setStyleSheet(
            f"background-color: {c}; color: {'#000' if QColor(c).lightness() > 150 else '#fff'};")

    def _handle_crop_mode_toggled(self, c: bool) -> None:
        if c: self.roi1_button.setChecked(False); self.roi2_button.setChecked(False)
        self.canvas.set_crop_mode(c)
        self.cancel_crop_button.setEnabled(c or self.canvas.has_crop_selection())

    def _handle_crop_selection_changed(self, has_selection: bool) -> None:
        self.apply_crop_button.setEnabled(has_selection)
        self.cancel_crop_button.setEnabled(self.crop_mode_button.isChecked() or has_selection)

    def _apply_crop(self) -> None:
        b = self.canvas.get_crop_bounds()
        if b and self._image_source:
            self._image_source.apply_crop(b)
            self.state.image.width = self._image_source.width
            self.state.image.height = self._image_source.height
            self.canvas.set_image_source(self._image_source)
            self.crop_mode_button.setChecked(False)
            self.apply_crop_button.setEnabled(False)
            self.cancel_crop_button.setEnabled(False)
            self._clear_rois()
            self._update_roi_input_ranges()
            self._sync_roi_inputs()

    def _cancel_crop(self) -> None:
        self.canvas.clear_crop_selection()
        self.apply_crop_button.setEnabled(False)
        self.cancel_crop_button.setEnabled(False)
        if self.crop_mode_button.isChecked():
            self.crop_mode_button.setChecked(False)

    def _refresh_summary(self) -> None:
        if not self._image_source:
            return
        self.image_info.setText(
            f"Size: {self.state.image.width}x{self.state.image.height}\nPath: {self.state.image.path.name}"
        )

        if self.state.selection_active:
            if self.state.selected_roi_index and self.state.rois[self.state.selected_roi_index - 1].bounds:
                ordered = sorted(
                    [(i + 1, r.bounds) for i, r in enumerate(self.state.rois) if r.bounds],
                    key=lambda x: (x[1].left, x[1].top),
                )
                columns_per_roi = allocate_columns_by_width(
                    self.state.grid.columns,
                    [bounds.width for _, bounds in ordered],
                )
                roi_order = [x[0] for x in ordered].index(self.state.selected_roi_index) + 1
                roi_b = self.state.rois[self.state.selected_roi_index - 1].bounds
                local_columns = max(1, columns_per_roi[roi_order - 1])
                local_cell = self.state.selected_cell.__class__(
                    x=global_x_to_local_x(self.state.selected_cell.x, columns_per_roi, roi_order),
                    y=self.state.selected_cell.y,
                )
                cell_b = compute_cell_bounds_within_bounds(
                    roi_b,
                    GridConfig(local_columns, self.state.grid.rows),
                    local_cell,
                )
                lbl = compute_label(self.state.grid, self.state.selected_cell)
            else:
                cell_b = compute_cell_bounds(self.state.image.width, self.state.image.height, self.state.grid,
                                             self.state.selected_cell)
                lbl = compute_label(self.state.grid, self.state.selected_cell)

            self.label_info.setText(
                f"Label: {lbl}\nRegion: L{cell_b.left} T{cell_b.top} R{cell_b.right} B{cell_b.bottom}")
            crop_preview = self._image_source.extract_region_preview(cell_b)
            self.zoom_panel.set_zoom_content(
                crop_preview,
                lambda path, file_format, bounds=cell_b: self._image_source.save_region(bounds, path, file_format),
            )
        else:
            self.label_info.setText("Label: -")
            self.zoom_panel.set_zoom_content(None, None)

    def _update_roi_input_ranges(self) -> None:
        width = max(0, self.state.image.width)
        height = max(0, self.state.image.height)
        for roi_inputs in (self.roi1_coords, self.roi2_coords):
            roi_inputs["left"].setRange(0, width)
            roi_inputs["right"].setRange(0, width)
            roi_inputs["top"].setRange(0, height)
            roi_inputs["bottom"].setRange(0, height)

    def _sync_roi_inputs(self) -> None:
        for roi_state, roi_inputs in zip(self.state.rois, (self.roi1_coords, self.roi2_coords), strict=False):
            bounds = roi_state.bounds
            values = (0, 0, 0, 0) if bounds is None else (bounds.left, bounds.top, bounds.right, bounds.bottom)
            for key, value in zip(("left", "top", "right", "bottom"), values, strict=False):
                widget = roi_inputs[key]
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)

    def _apply_roi_from_inputs(self, roi_index: int) -> None:
        if not self._image_source:
            return

        roi_inputs = self.roi1_coords if roi_index == 1 else self.roi2_coords
        left = roi_inputs["left"].value()
        top = roi_inputs["top"].value()
        right = roi_inputs["right"].value()
        bottom = roi_inputs["bottom"].value()

        left, right = sorted((left, right))
        top, bottom = sorted((top, bottom))
        if right - left < 2 or bottom - top < 2:
            QMessageBox.warning(self, "Invalid ROI", "ROI must be at least 2 pixels wide and high.")
            return

        bounds = PixelBounds(left=left, top=top, right=right, bottom=bottom)
        self.state.rois[roi_index - 1].bounds = bounds
        self.state.selected_roi_index = 0
        self.state.selection_active = False
        self.canvas.set_selected_roi_index(0)
        self.canvas.set_selection_active(False)
        self.canvas.set_rois([r.bounds for r in self.state.rois])
        self.roi1_button.setChecked(False)
        self.roi2_button.setChecked(False)
        self._sync_roi_inputs()
        self._refresh_summary()
