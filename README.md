# pdftools

A collection of small utilities for working with PDF files. The project currently
provides a command line helper for adding bookmarks to the "Hevajra Tantra"
translation PDF.

## Requirements

* Python 3.9 or newer
* [pikepdf](https://pikepdf.readthedocs.io/)

Install the Python dependency with:

```bash
pip install pikepdf
```

## Hevajra bookmark utility

The `bookmark.py` module can be executed directly. It expects an input PDF and a
path for the output PDF that should receive the generated bookmarks.

```bash
python bookmark.py hevajra-unbookmarked.pdf hevajra-with-bookmarks.pdf
```

The script rebuilds the outline from scratch, so any existing bookmarks in the
input document are replaced with the canonical structure defined in
`bookmark.py`.

To validate that the module is syntactically correct, you can run:

```bash
python -m compileall bookmark.py
```

