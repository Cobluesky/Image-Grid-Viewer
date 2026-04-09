from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap

from app.core.image_region import PixelBounds


# This app works with trusted local image files, so we explicitly allow
# very large pixel counts and handle memory by partial loading instead.
Image.MAX_IMAGE_PIXELS = None


class TiledImageSource:
    _max_source_tile_size = 2048

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        with Image.open(self.path) as image:
            width, height = image.size

        self._original_bounds = PixelBounds(0, 0, width, height)
        self._current_bounds = self._original_bounds
        self._cache_version = 0
        self._render_cache: OrderedDict[tuple[int, int, int, int, int, int, int], QPixmap] = OrderedDict()
        self._cache_limit = 24

    @property
    def width(self) -> int:
        return self._current_bounds.width

    @property
    def height(self) -> int:
        return self._current_bounds.height

    @property
    def bounds(self) -> PixelBounds:
        return self._current_bounds

    def apply_crop(self, bounds: PixelBounds) -> None:
        self._current_bounds = self._to_original_bounds(bounds)
        self._invalidate_cache()

    def render_viewport(self, bounds: PixelBounds, target_width: int, target_height: int) -> QPixmap:
        safe_bounds = self._clamp_bounds(bounds)
        if safe_bounds.width <= 0 or safe_bounds.height <= 0 or target_width <= 0 or target_height <= 0:
            return QPixmap()

        key = (
            self._cache_version,
            safe_bounds.left,
            safe_bounds.top,
            safe_bounds.right,
            safe_bounds.bottom,
            target_width,
            target_height,
        )
        cached = self._render_cache.get(key)
        if cached is not None:
            self._render_cache.move_to_end(key)
            return cached

        pixmap = QPixmap(max(1, target_width), max(1, target_height))
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        try:
            with Image.open(self.path) as image:
                for tile_bounds, target_x, target_y, tile_target_width, tile_target_height in self._iter_render_tiles(
                    safe_bounds,
                    target_width,
                    target_height,
                ):
                    tile_image = self._open_region_from_image(
                        image,
                        tile_bounds,
                        target_size=(tile_target_width, tile_target_height),
                    )
                    tile_pixmap = self._pil_to_pixmap(tile_image)
                    painter.drawPixmap(target_x, target_y, tile_pixmap)
        finally:
            painter.end()

        self._render_cache[key] = pixmap
        while len(self._render_cache) > self._cache_limit:
            self._render_cache.popitem(last=False)
        return pixmap

    def extract_region_preview(self, bounds: PixelBounds, max_side: int = 2048) -> QPixmap:
        safe_bounds = self._clamp_bounds(bounds)
        if safe_bounds.width <= 0 or safe_bounds.height <= 0:
            return QPixmap()

        if safe_bounds.width >= safe_bounds.height:
            target_width = min(max_side, safe_bounds.width)
            target_height = max(1, round(safe_bounds.height * (target_width / safe_bounds.width)))
        else:
            target_height = min(max_side, safe_bounds.height)
            target_width = max(1, round(safe_bounds.width * (target_height / safe_bounds.height)))

        return self.render_viewport(safe_bounds, target_width, target_height)

    def save_region(self, bounds: PixelBounds, path: str, file_format: str) -> bool:
        safe_bounds = self._clamp_bounds(bounds)
        if safe_bounds.width <= 0 or safe_bounds.height <= 0:
            return False

        image = self._open_region_image(safe_bounds)
        save_image = image
        normalized_format = "JPEG" if file_format.upper() == "JPG" else file_format.upper()
        if normalized_format in {"JPEG", "BMP"}:
            save_image = image.convert("RGB")
        save_image.save(path, normalized_format)
        return True

    def _iter_render_tiles(
        self,
        bounds: PixelBounds,
        target_width: int,
        target_height: int,
    ) -> list[tuple[PixelBounds, int, int, int, int]]:
        scale_x = target_width / bounds.width
        scale_y = target_height / bounds.height
        tiles: list[tuple[PixelBounds, int, int, int, int]] = []

        for top in range(bounds.top, bounds.bottom, self._max_source_tile_size):
            bottom = min(bounds.bottom, top + self._max_source_tile_size)
            for left in range(bounds.left, bounds.right, self._max_source_tile_size):
                right = min(bounds.right, left + self._max_source_tile_size)

                target_left = round((left - bounds.left) * scale_x)
                target_top = round((top - bounds.top) * scale_y)
                target_right = round((right - bounds.left) * scale_x)
                target_bottom = round((bottom - bounds.top) * scale_y)
                tile_target_width = max(1, target_right - target_left)
                tile_target_height = max(1, target_bottom - target_top)

                tiles.append(
                    (
                        PixelBounds(left, top, right, bottom),
                        target_left,
                        target_top,
                        tile_target_width,
                        tile_target_height,
                    )
                )
        return tiles

    def _clamp_bounds(self, bounds: PixelBounds) -> PixelBounds:
        left = max(0, min(self.width, bounds.left))
        top = max(0, min(self.height, bounds.top))
        right = max(left + 1, min(self.width, bounds.right))
        bottom = max(top + 1, min(self.height, bounds.bottom))
        return PixelBounds(left, top, right, bottom)

    def _to_original_bounds(self, bounds: PixelBounds) -> PixelBounds:
        safe_bounds = self._clamp_bounds(bounds)
        return PixelBounds(
            left=self._current_bounds.left + safe_bounds.left,
            top=self._current_bounds.top + safe_bounds.top,
            right=self._current_bounds.left + safe_bounds.right,
            bottom=self._current_bounds.top + safe_bounds.bottom,
        )

    def _open_region_image(
        self,
        bounds: PixelBounds,
        target_size: tuple[int, int] | None = None,
    ) -> Image.Image:
        with Image.open(self.path) as image:
            return self._open_region_from_image(image, bounds, target_size=target_size)

    def _open_region_from_image(
        self,
        image: Image.Image,
        bounds: PixelBounds,
        target_size: tuple[int, int] | None = None,
    ) -> Image.Image:
        original_bounds = self._to_original_bounds(bounds)
        region = image.crop(
            (original_bounds.left, original_bounds.top, original_bounds.right, original_bounds.bottom)
        )
        region.load()
        region = region.convert("RGBA")
        if target_size is not None and region.size != target_size:
            region = region.resize(target_size, Image.Resampling.BILINEAR)
        return region

    def _invalidate_cache(self) -> None:
        self._cache_version += 1
        self._render_cache.clear()

    @staticmethod
    def _pil_to_pixmap(image: Image.Image) -> QPixmap:
        rgba = image.convert("RGBA")
        qimage = QImage(
            rgba.tobytes("raw", "RGBA"),
            rgba.width,
            rgba.height,
            rgba.width * 4,
            QImage.Format.Format_RGBA8888,
        ).copy()
        return QPixmap.fromImage(qimage)
