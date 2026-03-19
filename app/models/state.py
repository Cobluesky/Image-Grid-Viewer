from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.grid import CellCoordinate, GridConfig

if TYPE_CHECKING:
    from app.core.image_region import PixelBounds


@dataclass
class ImageMetadata:
    path: Path | None = None
    width: int = 0
    height: int = 0

    @property
    def is_loaded(self) -> bool:
        return self.path is not None and self.width > 0 and self.height > 0


@dataclass
class RoiState:
    index: int
    bounds: PixelBounds | None = None

    @property
    def is_defined(self) -> bool:
        return self.bounds is not None


@dataclass
class AppState:
    image: ImageMetadata = field(default_factory=ImageMetadata)
    grid: GridConfig = field(default_factory=lambda: GridConfig(columns=6, rows=4))
    selected_cell: CellCoordinate = field(default_factory=lambda: CellCoordinate(x=1, y=1))
    selected_roi_index: int = 0
    selection_active: bool = False
    label_visible: bool = True
    label_scale_percent: int = 100
    label_color_hex: str = "#ffffff"
    crop_mode_enabled: bool = False
    rois: list[RoiState] = field(
        default_factory=lambda: [RoiState(index=1), RoiState(index=2)]
    )
