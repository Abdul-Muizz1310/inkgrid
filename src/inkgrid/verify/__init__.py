"""The verifier: a document graded against its PDF as a second engine, PDFium, reads it.

It never imports the code that built the document (`inkgrid.core`, `inkgrid.read`); only
`pdfium_reader` touches PDFium, and everything past it is pure (docs/specs/10-verify.md).
"""
