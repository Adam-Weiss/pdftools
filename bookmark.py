#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add structured bookmarks (outlines) to the Hevajra PDF.

- Removes ALL existing bookmarks.
- Adds front-matter (roman labels), Part I & II (arabic), back matter.
- Uses robust pikepdf calls compatible with older/newer builds:
  * deletes /Outlines via pdf.Root
  * commits outline via context manager
  * builds destinations with [page.obj, /Fit]

USAGE:
  python3 add_hevajra_bookmarks.py INPUT.pdf OUTPUT.pdf
"""

import sys
import pikepdf

# ====== CONFIGURE OFFSETS ======
# printed 'i' is the 3rd physical page (0-based index 2)
ROMAN_I_PHYS = 2
# printed '1' starts at physical index 58 (0-based)
ARABIC_1_PHYS = 58

# ====== TOC DATA ======
FRONT_MATTER = [
    ("Preface", "vii"),
    ("Introduction", "xviii"),
    ("Acknowledgements", "xlii"),
    ("A Note Regarding the Translation", "xliii"),
    ("List of Texts Consulted", "xlvi"),
    ("A Table of the Textual Contents of the Hevajra Tantra", "xlvii"),
]

PART_I_TITLE = "Hevajra Tantra Part I—The Awakening of the Vajragarbha"
PART_I = [
    ("1. Vajra Family", 3),
    ("2. Mantras", 25),
    ("3. Deity", 37),
    ("4. Consecration by the Deity", 47),
    ("5. True Principle", 49),
    ("6. Application of the Vow", 61),
    ("7. Secret Sign Language", 71),
    ("8. Circle of the Yoginī", 83),
    ("9. Purification", 111),
    ("10. Consecration", 119),
    ("11. Various Rites", 139),
]

PART_II_TITLE = "Hevajra Tantra Part II—The Illusion"
PART_II = [
    ("1. Rite of Establishing Sanctity", 147),
    ("2. Definition of the Accomplishment", 153),
    ("3. Fundamentals of All Tantras", 179),
    ("4. Seals", 205),
    ("5. Manifestation of the Maṇḍala of Hevajra", 241),
    ("6. Painting the Portrait of Hevajra", 263),
    ("7. Book and Feast", 267),
    ("8. Discipline", 271),
    ("9. Arrangement of Mantras", 275),
    ("10. Recitation of Mantras", 287),
    ("11. Means to Attain the Innate", 289),
    ("12. Instruction for the Four Consecrations", 293),
]

BACK_MATTER = [
    ("A Glossary of Important Terms", 297),
    ("Index", 305),
]

# ====== HELPERS ======
ROMAN_MAP = {'m':1000,'d':500,'c':100,'l':50,'x':10,'v':5,'i':1}

def roman_to_int(s: str) -> int:
    s = s.lower().strip()
    total = 0
    i = 0
    while i < len(s):
        if i+1 < len(s) and ROMAN_MAP[s[i]] < ROMAN_MAP[s[i+1]]:
            total += ROMAN_MAP[s[i+1]] - ROMAN_MAP[s[i]]
            i += 2
        else:
            total += ROMAN_MAP[s[i]]
            i += 1
    return total

def phys_from_roman(roman_label: str) -> int:
    return ROMAN_I_PHYS + (roman_to_int(roman_label) - 1)

def phys_from_arabic(n: int) -> int:
    return ARABIC_1_PHYS + (int(n) - 1)

def clamp_index(pdf: pikepdf.Pdf, idx: int) -> int:
    return max(0, min(idx, len(pdf.pages) - 1))

def make_item(pdf: pikepdf.Pdf, title: str, page_index: int) -> pikepdf.OutlineItem:
    idx = clamp_index(pdf, page_index)
    page = pdf.pages[idx]
    page_obj = page.obj  # some pikepdf builds require raw object, not helper
    dest = pikepdf.Array([page_obj, pikepdf.Name('/Fit')])
    # Try modern keyword
    try:
        return pikepdf.OutlineItem(title, destination=dest)
    except TypeError:
        pass
    # Positional fallback
    try:
        return pikepdf.OutlineItem(title, dest)
    except TypeError:
        pass
    # Very old fallback
    try:
        return pikepdf.OutlineItem(title, idx)
    except TypeError:
        return pikepdf.OutlineItem(title)

def main(inp: str, outp: str):
    pdf = pikepdf.Pdf.open(inp)

    # Hard reset existing outlines (tree will be rebuilt)
    try:
        if '/Outlines' in pdf.Root:
            del pdf.Root['/Outlines']
    except Exception:
        # ignore if Root not accessible or key missing
        pass

    # Build outline and auto-commit on exit
    with pdf.open_outline() as outline:
        # Front matter (roman labels)
        for title, rlabel in FRONT_MATTER:
            outline.root.append(
                make_item(pdf, title, phys_from_roman(rlabel))
            )

        # Part I (anchor as top-level, chapters as children)
        part1_anchor = phys_from_arabic(PART_I[0][1])
        outline.root.append(make_item(pdf, PART_I_TITLE, part1_anchor))
        part1_item = outline.root[-1]
        for title, pno in PART_I:
            part1_item.children.append(
                make_item(pdf, title, phys_from_arabic(pno))
            )

        # Part II (anchor + children)
        part2_anchor = phys_from_arabic(PART_II[0][1])
        outline.root.append(make_item(pdf, PART_II_TITLE, part2_anchor))
        part2_item = outline.root[-1]
        for title, pno in PART_II:
            part2_item.children.append(
                make_item(pdf, title, phys_from_arabic(pno))
            )

        # Back matter (arabic)
        for title, pno in BACK_MATTER:
            outline.root.append(
                make_item(pdf, title, phys_from_arabic(pno))
            )

    pdf.save(outp)
    print(f"Saved with bookmarks → {outp}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 add_hevajra_bookmarks.py INPUT.pdf OUTPUT.pdf")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
