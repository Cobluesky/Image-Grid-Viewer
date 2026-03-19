from __future__ import annotations

from dataclasses import dataclass


MAX_COLUMNS = 80
MAX_ROWS = 50


@dataclass(frozen=True)
class GridConfig:
    columns: int
    rows: int

    def validate(self) -> None:
        if not (1 <= self.columns <= MAX_COLUMNS):
            raise ValueError(f"columns must be between 1 and {MAX_COLUMNS}")
        if not (1 <= self.rows <= MAX_ROWS):
            raise ValueError(f"rows must be between 1 and {MAX_ROWS}")


@dataclass(frozen=True)
class CellCoordinate:
    x: int
    y: int

    def validate(self, grid: GridConfig) -> None:
        if not (1 <= self.x <= grid.columns):
            raise ValueError(f"x must be between 1 and {grid.columns}")
        if not (1 <= self.y <= grid.rows):
            raise ValueError(f"y must be between 1 and {grid.rows}")


def compute_label(grid: GridConfig, cell: CellCoordinate) -> int:
    grid.validate()
    cell.validate(grid)
    return (cell.y - 1) * grid.columns + cell.x


def compute_roi_cell_count(grid: GridConfig) -> int:
    grid.validate()
    return grid.columns * grid.rows


def compute_combined_label(grid: GridConfig, roi_order: int, roi_count: int, cell: CellCoordinate) -> int:
    grid.validate()
    cell.validate(grid)
    if roi_order < 1:
        raise ValueError("roi_order must be 1 or greater")
    if roi_count < 1:
        raise ValueError("roi_count must be 1 or greater")

    combined_columns = grid.columns * roi_count
    global_x = ((roi_order - 1) * grid.columns) + cell.x
    return (cell.y - 1) * combined_columns + global_x


def compute_global_label(grid: GridConfig, roi_order: int, roi_count: int, cell: CellCoordinate) -> int:
    return compute_combined_label(grid, roi_order, roi_count, cell)


def sort_rois_left_to_right(rois: list[object]) -> list[object]:
    return sorted(rois, key=lambda roi: (roi.left, roi.top))


def allocate_columns_by_width(total_columns: int, widths: list[int]) -> list[int]:
    if total_columns < 1:
        raise ValueError("total_columns must be 1 or greater")
    if not widths:
        return []

    total_width = sum(max(0, width) for width in widths)
    if total_width <= 0:
        base = total_columns // len(widths)
        remainder = total_columns % len(widths)
        return [base + (1 if index < remainder else 0) for index in range(len(widths))]

    raw_allocations = [(max(0, width) / total_width) * total_columns for width in widths]
    allocated = [int(value) for value in raw_allocations]
    remainder = total_columns - sum(allocated)

    fractional = sorted(
        enumerate(raw_allocations),
        key=lambda item: (item[1] - int(item[1]), widths[item[0]]),
        reverse=True,
    )
    for index, _ in fractional[:remainder]:
        allocated[index] += 1

    return allocated


def compute_column_offsets(columns_per_roi: list[int]) -> list[int]:
    offsets: list[int] = []
    running = 0
    for count in columns_per_roi:
        offsets.append(running)
        running += count
    return offsets


def global_x_to_local_x(global_x: int, columns_per_roi: list[int], roi_order: int) -> int:
    if roi_order < 1 or roi_order > len(columns_per_roi):
        raise ValueError("roi_order out of range")
    offsets = compute_column_offsets(columns_per_roi)
    return global_x - offsets[roi_order - 1]
