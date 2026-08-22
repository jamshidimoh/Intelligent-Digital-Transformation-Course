# Published Chapter Files

This directory contains the final distribution files for each textbook chapter.

Expected structure:

- `01-foundations/01-foundations.docx`
- `01-foundations/01-foundations.pdf`
- `02-enabling-technologies/02-enabling-technologies.docx`
- `02-enabling-technologies/02-enabling-technologies.pdf`
- and so on for all ten chapters.

The GitHub Actions publication workflow builds these files from the Markdown source in `BOOK/` so that the source remains version-controlled and the Word/PDF outputs remain reproducible.