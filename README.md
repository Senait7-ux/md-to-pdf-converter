# CCDI Hub Release Notes PDF

`converter.py` downloads the release notes Markdown from GitHub and writes `CCDI_Hub_Release_Notes.pdf` in this directory.

The notes come from the `dev` branch of [CCDI_Hub_Static_Contents](https://github.com/CBIIT/CCDI_Hub_Static_Contents/blob/dev/releaseNotesData.md).

## Requirements

- Python 3
- Network access to GitHub

## Setup

From this directory:

```bash
python3 -m venv .venv
.venv/bin/pip install reportlab beautifulsoup4 svglib markdown
```

## Optional logo

Place `Portal_Logo.svg` in this directory, next to `converter.py`, to show it in the PDF header. If that file is missing, the script looks for `nih_logo.png`. If neither file is present, the header is the text "NATIONAL CANCER INSTITUTE".

## Run

```bash
.venv/bin/python converter.py
```

The PDF is written to `CCDI_Hub_Release_Notes.pdf` in this directory.
