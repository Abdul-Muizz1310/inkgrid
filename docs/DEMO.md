# Demo script

A two-minute terminal demo of what M0 does. It needs a clone and `uv`.

## 1. Build the demo PDFs

```bash
uv sync --all-groups
uv run python - <<'PY'
import sys
sys.path.insert(0, "tests/support")
import pdf_factory
open("superscript.pdf", "wb").write(pdf_factory.superscript())
open("hidden.pdf", "wb").write(pdf_factory.hidden_text())
open("table.pdf", "wb").write(pdf_factory.ruled_table())
open("columns.pdf", "wb").write(pdf_factory.two_column())
PY
```

## 2. A marker stays off the value it annotates

```bash
uv run inkgrid words superscript.pdf --pretty | grep -E '"text"|"superscript"'
```

Say: plain word extraction reads this page as `$0.402`. inkgrid reads `$0.40` and a separate
superscript `2`, because it rebuilds words from characters and splits where the superscript flag
changes.

## 3. Text the page never draws is reported

```bash
uv run inkgrid words hidden.pdf --pretty | grep -A3 '"findings"'
```

Say: the sentence `ignore previous instructions` sits in the text layer in render mode 3, so no
reader ever sees it on the page. Render mode 7 and fully transparent text are caught the same way. inkgrid still returns the words, marks them `hidden`, and raises a
`hidden_text` finding, because text a pipeline reads but a person never sees is where prompt
injection hides.

## 4. Drawn rules come from the vector paths

```bash
uv run inkgrid words table.pdf --pretty | grep -A8 '"rules"'
```

Say: the stroked lines, the thin filled rule, and the four edges of the stroked cell come back as
rules. The grey background and the diagonal do not.

## 5. Two columns read in column order

```bash
uv run inkgrid read columns.pdf --markdown columns.md --inspector columns.html -o columns.json
cat columns.md
```

Say: the page prints two prose columns side by side, and plain extraction interleaves them line by
line. inkgrid reads the whole left column, then the right. Open `columns.html` to see every block
drawn over the rendered page, numbered in reading order.

## 6. Bad input fails loudly and briefly

```bash
echo "not a pdf" > bad.pdf && uv run inkgrid words bad.pdf; echo "exit $?"
```

Say: one line on stderr, exit code 2, no traceback.
