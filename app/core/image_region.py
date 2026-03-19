from __future__ import annotations

from dataclasses import dataclass

from app.core.grid import CellCoordinate, GridConfig


@dataclass(frozen=True)
class PixelBounds:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def compute_cell_bounds(
    image_width: int,
    image_height: int,
    grid: GridConfig,
    cell: CellCoordinate,
) -> PixelBounds:
    grid.validate()
    cell.validate(grid)

    left = ((cell.x - 1) * image_width) // grid.columns
    right = (cell.x * image_width) // grid.columns
    top = ((cell.y - 1) * image_height) // grid.rows
    bottom = (cell.y * image_height) // grid.rows
    return PixelBounds(left=left, top=top, right=right, bottom=bottom)


def compute_cell_bounds_within_bounds(
    bounds: PixelBounds,
    grid: GridConfig,
    cell: CellCoordinate,
) -> PixelBounds:
    local = compute_cell_bounds(bounds.width, bounds.height, grid, cell)
    return PixelBounds(
        left=bounds.left + local.left,
        top=bounds.top + local.top,
        right=bounds.left + local.right,
        bottom=bounds.top + local.bottom,
    )
