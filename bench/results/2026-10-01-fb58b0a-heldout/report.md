# inkgrid benchmark: the held-out fee set (M5d)

Measured on 2026-10-01 at commit `fb58b0a` by `bench/inkgrid_bench/run.py --datasets heldout`, under the pre-registered protocol of `docs/specs/16-held-out-fee-set.md`. **These documents are held out**: exchange fee schedules chosen by a fixed rule after M5c's fixes were frozen, read by inkgrid as the tuned run read (`src/inkgrid` as at `7f70dd6`), so its numbers are its reading of documents no fix has seen. Each table's grid was drafted from the page's rendering, never from inkgrid's reading, and each cell's text is the PDF's own words as PyMuPDF reads them: the text layer inkgrid and the other text-layer tools read too, so their characters match the truth's wherever their cells do, and an OCR tool's need not. The user verified every table, and none of the 200 cells whose glyphs were checked needed a correction. 11 documents give wide intervals. docling-ocr, unstructured, and inkgrid-ocr read the pages with OCR; docling OCRs only a page's regions without text, a page with no text layer included; marker reads with OCR off, its tables built from the text layer; every other tool reads the PDF's text layer. `inkgrid-ocr` is inkgrid with Tesseract's words for its own. The heavy tools' seconds are a warm process's, its models loaded, and a document that timed out has no seconds.

Each cell is the point estimate and its 95% interval from 10,000 resamples of documents (seed 20260928). A difference marked `*` has an interval that excludes 0; only those are findings. `ground-truth` is the dataset's ground truth read as a tool: a check on the pipeline and on each metric's ceiling, not a competitor.

## Held-out fee set (11 documents)

### Structure (the competition's DAR)

| Tool | Structure P | Structure R | Structure F | Structure P (pooled) | Structure R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid | 0.669 [0.439, 0.871] | 0.628 [0.395, 0.833] | 0.647 [0.418, 0.849] | 0.744 [0.565, 0.914] | 0.629 [0.427, 0.802] |
| pdfplumber | 0.590 [0.347, 0.823] | 0.430 [0.205, 0.668] | 0.498 [0.263, 0.711] | 0.558 [0.324, 0.819] | 0.404 [0.187, 0.655] |
| pymupdf | 0.549 [0.310, 0.783] | 0.443 [0.214, 0.683] | 0.490 [0.259, 0.711] | 0.578 [0.340, 0.819] | 0.422 [0.198, 0.678] |
| camelot | 0.584 [0.279, 0.871] | 0.402 [0.153, 0.665] | 0.476 [0.202, 0.725] | 0.740 [0.521, 0.951] | 0.356 [0.134, 0.620] |
| docling | 0.718 [0.525, 0.880] | 0.699 [0.518, 0.855] | 0.708 [0.521, 0.867] | 0.728 [0.509, 0.890] | 0.741 [0.569, 0.870] |
| docling-ocr | 0.718 [0.523, 0.879] | 0.697 [0.514, 0.848] | 0.707 [0.519, 0.862] | 0.729 [0.534, 0.884] | 0.746 [0.597, 0.858] |
| marker | 0.327 [0.179, 0.488] | 0.182 [0.081, 0.299] | 0.234 [0.114, 0.364] | 0.320 [0.140, 0.491] | 0.197 [0.077, 0.316] |
| unstructured | 0.389 [0.232, 0.557] | 0.296 [0.183, 0.415] | 0.336 [0.206, 0.473] | 0.404 [0.201, 0.595] | 0.318 [0.156, 0.478] |
| inkgrid-ocr | 0.443 [0.306, 0.591] | 0.314 [0.165, 0.489] | 0.368 [0.218, 0.532] | 0.422 [0.261, 0.627] | 0.283 [0.167, 0.427] |

| Difference | Structure P | Structure R | Structure F | Structure P (pooled) | Structure R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.079 [-0.201, +0.361] | +0.197 [+0.029, +0.390] * | +0.150 [-0.037, +0.376] | +0.186 [-0.039, +0.475] | +0.225 [+0.015, +0.445] * |
| inkgrid - pymupdf | +0.120 [-0.179, +0.416] | +0.185 [+0.011, +0.382] * | +0.157 [-0.050, +0.397] | +0.166 [-0.074, +0.469] | +0.207 [-0.011, +0.433] |
| inkgrid - camelot | +0.085 [-0.238, +0.404] | +0.225 [+0.018, +0.457] * | +0.171 [-0.050, +0.433] | +0.005 [-0.101, +0.182] | +0.273 [+0.004, +0.514] * |
| inkgrid - docling | -0.050 [-0.179, +0.070] | -0.071 [-0.229, +0.074] | -0.061 [-0.202, +0.065] | +0.017 [-0.135, +0.252] | -0.112 [-0.262, +0.055] |
| inkgrid - docling-ocr | -0.049 [-0.173, +0.064] | -0.069 [-0.221, +0.072] | -0.060 [-0.197, +0.065] | +0.016 [-0.106, +0.219] | -0.117 [-0.252, +0.036] |
| inkgrid - marker | +0.341 [+0.112, +0.558] * | +0.445 [+0.210, +0.668] * | +0.413 [+0.183, +0.634] * | +0.424 [+0.314, +0.582] * | +0.431 [+0.241, +0.626] * |
| inkgrid - unstructured | +0.280 [+0.066, +0.503] * | +0.332 [+0.107, +0.551] * | +0.311 [+0.093, +0.530] * | +0.340 [+0.194, +0.543] * | +0.311 [+0.110, +0.533] * |
| inkgrid - inkgrid-ocr | +0.226 [+0.063, +0.380] * | +0.313 [+0.154, +0.471] * | +0.280 [+0.122, +0.435] * | +0.322 [+0.208, +0.438] * | +0.346 [+0.195, +0.476] * |

Check, the ground truth read as a tool:

| Tool | Structure P | Structure R | Structure F | Structure P (pooled) | Structure R (pooled) |
| --- | --- | --- | --- | --- | --- |
| ground-truth | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |

### Regions

| Tool | Regions P | Regions R | Regions F | Regions P (pooled) | Regions R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid | 0.836 [0.658, 0.972] | 0.800 [0.598, 0.959] | 0.818 [0.655, 0.945] | 0.801 [0.631, 0.965] | 0.847 [0.704, 0.960] |
| pdfplumber | 0.797 [0.629, 0.939] | 0.647 [0.375, 0.913] | 0.714 [0.480, 0.900] | 0.808 [0.674, 0.964] | 0.655 [0.328, 0.957] |
| pymupdf | 0.849 [0.690, 0.986] | 0.715 [0.453, 0.928] | 0.776 [0.558, 0.939] | 0.858 [0.704, 0.993] | 0.719 [0.417, 0.976] |
| camelot | 0.840 [0.608, 1.000] | 0.637 [0.370, 0.876] | 0.725 [0.496, 0.900] | 0.666 [0.390, 1.000] | 0.680 [0.379, 0.927] |
| docling | 0.892 [0.720, 1.000] | 0.899 [0.775, 1.000] | 0.895 [0.747, 1.000] | 0.923 [0.763, 1.000] | 0.947 [0.873, 1.000] |
| docling-ocr | 0.856 [0.662, 1.000] | 0.868 [0.675, 1.000] | 0.862 [0.661, 1.000] | 0.876 [0.715, 1.000] | 0.944 [0.866, 1.000] |
| marker | 0.944 [0.832, 1.000] | 0.773 [0.578, 0.936] | 0.850 [0.709, 0.953] | 0.863 [0.663, 1.000] | 0.824 [0.655, 0.942] |
| unstructured | 0.908 [0.829, 0.977] | 0.901 [0.817, 0.973] | 0.905 [0.839, 0.962] | 0.894 [0.794, 0.977] | 0.917 [0.817, 0.994] |
| inkgrid-ocr | 0.870 [0.754, 0.969] | 0.756 [0.576, 0.929] | 0.809 [0.673, 0.928] | 0.796 [0.626, 0.987] | 0.750 [0.558, 0.940] |

| Difference | Regions P | Regions R | Regions F | Regions P (pooled) | Regions R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.039 [-0.176, +0.247] | +0.153 [-0.017, +0.358] | +0.104 [-0.041, +0.287] | -0.006 [-0.123, +0.100] | +0.192 [-0.056, +0.452] |
| inkgrid - pymupdf | -0.013 [-0.220, +0.184] | +0.086 [-0.024, +0.230] | +0.042 [-0.072, +0.168] | -0.057 [-0.151, +0.016] | +0.128 [-0.067, +0.366] |
| inkgrid - camelot | -0.004 [-0.236, +0.249] | +0.163 [-0.022, +0.399] | +0.093 [-0.034, +0.277] | +0.135 [-0.134, +0.444] | +0.167 [-0.027, +0.413] |
| inkgrid - docling | -0.056 [-0.169, +0.041] | -0.099 [-0.211, -0.016] * | -0.078 [-0.140, -0.027] * | -0.122 [-0.283, +0.072] | -0.100 [-0.199, -0.012] * |
| inkgrid - docling-ocr | -0.020 [-0.101, +0.057] | -0.068 [-0.216, +0.057] | -0.044 [-0.121, +0.027] | -0.074 [-0.155, +0.062] | -0.097 [-0.207, +0.002] |
| inkgrid - marker | -0.108 [-0.283, +0.011] | +0.027 [-0.203, +0.275] | -0.032 [-0.228, +0.155] | -0.061 [-0.176, +0.016] | +0.023 [-0.130, +0.217] |
| inkgrid - unstructured | -0.072 [-0.264, +0.073] | -0.101 [-0.263, +0.046] | -0.087 [-0.241, +0.036] | -0.092 [-0.240, +0.065] | -0.070 [-0.205, +0.079] |
| inkgrid - inkgrid-ocr | -0.034 [-0.163, +0.082] | +0.044 [-0.055, +0.157] | +0.009 [-0.097, +0.116] | +0.005 [-0.124, +0.100] | +0.097 [-0.026, +0.219] |

Check, the ground truth read as a tool:

| Tool | Regions P | Regions R | Regions F | Regions P (pooled) | Regions R (pooled) |
| --- | --- | --- | --- | --- | --- |
| ground-truth | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |

### Binding (the access paths)

| Tool | Bound | Leaf-bound | Value recall |
| --- | --- | --- | --- |
| inkgrid | 0.579 [0.363, 0.793] | 0.584 [0.370, 0.799] | 0.704 [0.451, 0.899] |
| pdfplumber | 0.320 [0.105, 0.592] | 0.320 [0.105, 0.592] | 0.343 [0.113, 0.622] |
| pymupdf | 0.320 [0.105, 0.592] | 0.320 [0.105, 0.592] | 0.343 [0.113, 0.622] |
| camelot | 0.350 [0.114, 0.627] | 0.350 [0.114, 0.627] | 0.357 [0.115, 0.641] |
| docling | 0.743 [0.593, 0.865] | 0.814 [0.669, 0.912] | 0.932 [0.834, 0.988] |
| docling-ocr | 0.772 [0.592, 0.892] | 0.786 [0.606, 0.901] | 0.923 [0.817, 0.983] |
| marker | 0.153 [0.047, 0.272] | 0.195 [0.092, 0.314] | 0.459 [0.249, 0.647] |
| unstructured | 0.082 [0.017, 0.175] | 0.130 [0.046, 0.244] | 0.612 [0.388, 0.810] |
| inkgrid-ocr | 0.136 [0.028, 0.305] | 0.153 [0.043, 0.327] | 0.468 [0.291, 0.650] |

| Difference | Bound | Leaf-bound | Value recall |
| --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.259 [+0.079, +0.431] * | +0.264 [+0.088, +0.435] * | +0.362 [+0.081, +0.631] * |
| inkgrid - pymupdf | +0.259 [+0.079, +0.431] * | +0.264 [+0.088, +0.435] * | +0.362 [+0.081, +0.631] * |
| inkgrid - camelot | +0.230 [+0.012, +0.438] * | +0.235 [+0.025, +0.442] * | +0.348 [+0.027, +0.636] * |
| inkgrid - docling | -0.163 [-0.423, +0.157] | -0.230 [-0.481, +0.085] | -0.228 [-0.489, -0.003] * |
| inkgrid - docling-ocr | -0.193 [-0.455, +0.138] | -0.202 [-0.469, +0.138] | -0.219 [-0.459, -0.007] * |
| inkgrid - marker | +0.426 [+0.142, +0.709] * | +0.390 [+0.109, +0.663] * | +0.245 [-0.020, +0.547] |
| inkgrid - unstructured | +0.497 [+0.237, +0.725] * | +0.454 [+0.181, +0.672] * | +0.092 [-0.186, +0.357] |
| inkgrid - inkgrid-ocr | +0.443 [+0.246, +0.614] * | +0.431 [+0.237, +0.593] * | +0.237 [+0.070, +0.367] * |

Check, the ground truth read as a tool:

| Tool | Bound | Leaf-bound | Value recall |
| --- | --- | --- | --- |
| ground-truth | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |

### Cell character error rate

| Tool | Cell CER (lower is better) |
| --- | --- |
| inkgrid | 0.098 [0.029, 0.240] |
| pdfplumber | 0.520 [0.241, 0.760] |
| pymupdf | 0.477 [0.222, 0.703] |
| camelot | 0.308 [0.097, 0.635] |
| docling | 0.024 [0.003, 0.055] |
| docling-ocr | 0.035 [0.011, 0.083] |
| marker | 0.465 [0.273, 0.618] |
| unstructured | 0.259 [0.147, 0.352] |
| inkgrid-ocr | 0.144 [0.071, 0.265] |

| Difference | Cell CER (lower is better) |
| --- | --- |
| inkgrid - pdfplumber | -0.422 [-0.673, -0.109] * |
| inkgrid - pymupdf | -0.378 [-0.616, -0.080] * |
| inkgrid - camelot | -0.209 [-0.496, -0.023] * |
| inkgrid - docling | +0.074 [+0.001, +0.205] * |
| inkgrid - docling-ocr | +0.063 [-0.003, +0.179] |
| inkgrid - marker | -0.366 [-0.559, -0.099] * |
| inkgrid - unstructured | -0.160 [-0.301, +0.057] |
| inkgrid - inkgrid-ocr | -0.046 [-0.122, +0.025] |

Cell CER counts a tool's glyph errors on the sampled cells (spec 16 section 5), each cell against the closest cell of the tool's table matched to its table: it counts misread characters and cell boundaries that cut or join text, but text that recurs in a table is not checked for its place, and pooling over glyphs weighs a long cell more. Lower is better, so a negative difference favours inkgrid.

Check, the ground truth read as a tool:

| Tool | Cell CER (lower is better) |
| --- | --- |
| ground-truth | 0.000 [0.000, 0.000] |

### Speed

| Tool | Seconds per page |
| --- | --- |
| inkgrid | 0.294 [0.211, 0.434] |
| pdfplumber | 0.096 [0.080, 0.113] |
| pymupdf | 0.070 [0.058, 0.086] |
| camelot | 0.284 [0.263, 0.326] |
| docling | 10.158 [9.054, 11.836] |
| docling-ocr | 18.404 [12.969, 22.064] |
| marker | 0.566 [0.489, 0.732] |
| unstructured | 5.327 [4.824, 6.194] |
| inkgrid-ocr | 1.681 [1.575, 1.912] |

| Difference | Seconds per page |
| --- | --- |
| inkgrid - pdfplumber | +0.198 [+0.113, +0.339] * |
| inkgrid - pymupdf | +0.224 [+0.139, +0.364] * |
| inkgrid - camelot | +0.010 [-0.056, +0.113] |
| inkgrid - docling | -9.864 [-11.489, -8.729] * |
| inkgrid - docling-ocr | -18.110 [-21.809, -12.577] * |
| inkgrid - marker | -0.273 [-0.358, -0.161] * |
| inkgrid - unstructured | -5.033 [-5.812, -4.574] * |
| inkgrid - inkgrid-ocr | -1.387 [-1.563, -1.270] * |

Check, the ground truth read as a tool:

| Tool | Seconds per page |
| --- | --- |
| ground-truth | 0.000 [0.000, 0.000] |

## Crashes and timeouts (each scored as no tables)

| Tool | Dataset | Documents |
| --- | --- | --- |
| camelot | heldout | 1: tfex-usd (playa.exceptions.PDFTextExtractionNotAllowed: Text extraction is not allowed: /tmp/camelot-4_p_b0lx.pdf) |

## inkgrid's verifier on these documents (spec 11 section 5)

| Dataset | Documents with defects | Defects by class |
| --- | --- | --- |
| heldout | 1 | text 8 |
