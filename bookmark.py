#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utility for adding bookmarks to the Hevajra PDF.

The repository originally used a placeholder file containing the text
``main 01`` which immediately fails with a :class:`SyntaxError`.  This module
replaces that placeholder with a small command line utility capable of adding
bookmarks to a PDF using :mod:`pikepdf`.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

try:  # pragma: no cover - exercised in environments with pikepdf available
    import pikepdf
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    pikepdf = None  # type: ignore[assignment]
    _PIKEPDF_IMPORT_ERROR = exc
else:  # pragma: no cover - import guard
    _PIKEPDF_IMPORT_ERROR = None


# ====== CONFIGURE OFFSETS ======
# Printed ``i`` is the 3rd physical page (0-based index 2).
ROMAN_I_PHYS = 2
# Printed ``1`` starts at physical index 58 (0-based).
ARABIC_1_PHYS = 58


# ====== TOC DATA ======
@dataclass(frozen=True)
class BookmarkEntry:
    """Representation of a bookmark outline item."""

    title: str
    label: str | int
    children: Sequence["BookmarkEntry"] | None = None

    def flatten(self) -> Iterable["BookmarkEntry"]:
        """Iterate over the bookmark and its children recursively."""

        yield self
        if not self.children:
            return
        for child in self.children:
            yield from child.flatten()


FRONT_MATTER: Sequence[BookmarkEntry] = (
    BookmarkEntry("Preface", "vii"),
    BookmarkEntry("Introduction", "xviii"),
    BookmarkEntry("Acknowledgements", "xlii"),
    BookmarkEntry("A Note Regarding the Translation", "xliii"),
    BookmarkEntry("List of Texts Consulted", "xlvi"),
    BookmarkEntry(
        "A Table of the Textual Contents of the Hevajra Tantra", "xlvii"
    ),
)

PART_I = BookmarkEntry(
    "Hevajra Tantra Part I—The Awakening of the Vajragarbha",
    3,
    children=(
        BookmarkEntry("1. Vajra Family", 3),
        BookmarkEntry("2. Mantras", 25),
        BookmarkEntry("3. Deity", 37),
        BookmarkEntry("4. Consecration by the Deity", 47),
        BookmarkEntry("5. True Principle", 49),
        BookmarkEntry("6. Application of the Vow", 61),
        BookmarkEntry("7. Secret Sign Language", 71),
        BookmarkEntry("8. Circle of the Yoginī", 83),
        BookmarkEntry("9. Purification", 111),
        BookmarkEntry("10. Consecration", 119),
        BookmarkEntry("11. Various Rites", 139),
    ),
)

PART_II = BookmarkEntry(
    "Hevajra Tantra Part II—The Illusion",
    147,
    children=(
        BookmarkEntry("1. Rite of Establishing Sanctity", 147),
        BookmarkEntry("2. Definition of the Accomplishment", 153),
        BookmarkEntry("3. Fundamentals of All Tantras", 179),
        BookmarkEntry("4. Seals", 205),
        BookmarkEntry("5. Manifestation of the Maṇḍala of Hevajra", 241),
        BookmarkEntry("6. Painting the Portrait of Hevajra", 263),
        BookmarkEntry("7. Book and Feast", 267),
        BookmarkEntry("8. Discipline", 271),
        BookmarkEntry("9. Arrangement of Mantras", 275),
        BookmarkEntry("10. Recitation of Mantras", 287),
        BookmarkEntry("11. Means to Attain the Innate", 289),
        BookmarkEntry("12. Instruction for the Four Consecrations", 293),
    ),
)

BACK_MATTER: Sequence[BookmarkEntry] = (
    BookmarkEntry("A Glossary of Important Terms", 297),
    BookmarkEntry("Index", 305),
)


# ====== HELPERS ======
ROMAN_MAP = {"m": 1000, "d": 500, "c": 100, "l": 50, "x": 10, "v": 5, "i": 1}


def roman_to_int(s: str) -> int:
    """Convert a Roman numeral string to an integer."""

    s = s.lower().strip()
    total = 0
    i = 0
    while i < len(s):
        if i + 1 < len(s) and ROMAN_MAP[s[i]] < ROMAN_MAP[s[i + 1]]:
            total += ROMAN_MAP[s[i + 1]] - ROMAN_MAP[s[i]]
            i += 2
        else:
            total += ROMAN_MAP[s[i]]
            i += 1
    return total


def phys_from_roman(roman_label: str) -> int:
    """Translate a roman numeral label to a 0-based physical page index."""

    return ROMAN_I_PHYS + (roman_to_int(roman_label) - 1)


def phys_from_arabic(n: int) -> int:
    """Translate an arabic page number to a 0-based physical page index."""

    return ARABIC_1_PHYS + (int(n) - 1)


def _require_pikepdf() -> "pikepdf":
    """Return the :mod:`pikepdf` module or raise a helpful error."""

    if pikepdf is None:  # pragma: no cover - depends on environment
        raise ModuleNotFoundError(
            "pikepdf is required to manipulate PDF bookmarks."
        ) from _PIKEPDF_IMPORT_ERROR
    return pikepdf


def clamp_index(pdf: "pikepdf.Pdf", idx: int) -> int:
    """Ensure the page index is within the PDF's page count."""

    return max(0, min(idx, len(pdf.pages) - 1))


def make_item(
    pdf: "pikepdf.Pdf", title: str, page_index: int
) -> "pikepdf.OutlineItem":
    """Create an :class:`pikepdf.OutlineItem` for the given page index."""

    pp = _require_pikepdf()
    idx = clamp_index(pdf, page_index)
    page = pdf.pages[idx]
    page_obj = page.obj  # some pikepdf builds require the raw object, not helper
    dest = pp.Array([page_obj, pp.Name("/Fit")])
    # Try modern keyword usage first.
    try:
        return pp.OutlineItem(title, destination=dest)
    except TypeError:
        pass
    # Positional fallback.
    try:
        return pp.OutlineItem(title, dest)
    except TypeError:
        pass
    # Very old fallback.
    try:
        return pp.OutlineItem(title, idx)
    except TypeError:
        return pp.OutlineItem(title)


def add_outlines(pdf: "pikepdf.Pdf") -> None:
    """Add the Hevajra bookmarks to ``pdf`` in-place."""

    _require_pikepdf()
    # Hard reset existing outlines (tree will be rebuilt).
    try:
        if "/Outlines" in pdf.Root:
            del pdf.Root["/Outlines"]
    except Exception:  # pragma: no cover - extremely defensive
        # Ignore if Root is not accessible or key missing.
        pass

    def append_children(parent: pikepdf.OutlineItem, children: Sequence[BookmarkEntry]):
        for child in children:
            page_index = (
                phys_from_roman(child.label)
                if isinstance(child.label, str)
                else phys_from_arabic(child.label)
            )
            outline_item = make_item(pdf, child.title, page_index)
            parent.children.append(outline_item)
            if child.children:
                append_children(outline_item, child.children)

    with pdf.open_outline() as outline:
        for entry in FRONT_MATTER:
            outline.root.append(
                make_item(pdf, entry.title, phys_from_roman(entry.label))
            )

        part1_anchor = phys_from_arabic(PART_I.label)
        part1_item = make_item(pdf, PART_I.title, part1_anchor)
        outline.root.append(part1_item)
        append_children(part1_item, PART_I.children or ())

        part2_anchor = phys_from_arabic(PART_II.label)
        part2_item = make_item(pdf, PART_II.title, part2_anchor)
        outline.root.append(part2_item)
        append_children(part2_item, PART_II.children or ())

        for entry in BACK_MATTER:
            outline.root.append(
                make_item(pdf, entry.title, phys_from_arabic(entry.label))
            )


def process_file(input_path: Path, output_path: Path | None = None) -> None:
    """Apply the Hevajra bookmark outline to ``input_path``.

    Parameters
    ----------
    input_path:
        Path to the source PDF.
    output_path:
        Optional destination path.  When omitted the input file is
        overwritten in-place.
    """

    destination = output_path or input_path
    pp = _require_pikepdf()
    with pp.open(str(input_path)) as pdf:
        add_outlines(pdf)
        pdf.save(str(destination))


def build_parser() -> argparse.ArgumentParser:
    """Construct the command line argument parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the source PDF that requires the Hevajra outline.",
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help=(
            "Optional destination path.  When omitted the input file is"
            " modified in-place."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry-point for the command line interface."""

    parser = build_parser()
    ns = parser.parse_args(argv)

    try:
        process_file(ns.input, ns.output)
    except FileNotFoundError as exc:  # pragma: no cover - argument validation
        parser.error(str(exc))
    except pikepdf.PdfError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
