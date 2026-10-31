"""
Document compilation, PDF aggregation, and image sequence ordering.
"""

from __future__ import annotations

# PDF = Portable Document Format

from white_pepper.document.pdf_builder import (
    compile_images_to_pdf,
    compile_pdf_with_config,
    discover_image_sequence,
    natural_sort_key,
)

__all__: list[str] = [
    "natural_sort_key",
    "discover_image_sequence",
    "compile_images_to_pdf",
    "compile_pdf_with_config",
]
