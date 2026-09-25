# Why inkgrid?

## The obvious version

The obvious way to pull tables out of a PDF today is to render each page and hand the pixels to a
vision model. It works surprisingly well, and it fails in the worst possible way: quietly. A vision
reader can turn a superscript asterisk into a plus-minus sign or drop a four-thousand-dollar cap
from a cell, and nothing downstream can tell the output from a correct one. For a born-digital PDF
that is a strange trade, because the file already states every character exactly.

## Why I built it differently

I started from the text layer and made correctness a property of the design rather than a hope.
Every word is owned by exactly one block, and one proof checks that at the end instead of a guard in
every pass. A merged cell is one span, never a copied value. Anything the reader cannot trust, such as
an image-only page, clipped text, or text that is never drawn, becomes a typed finding instead of a
silent gap. A verifier built on a different PDF engine, which cannot import the builder, checks the
tables. And the "better than OCR" claim has to earn its place on a public benchmark before the README
makes it.

## What I'd change if I did it again

I would pick the permissively licensed PDFium engine for the page model from the start. PyMuPDF is
excellent, but its AGPL license follows every product that uses inkgrid, and moving later means
re-measuring every rule the reader encodes.
