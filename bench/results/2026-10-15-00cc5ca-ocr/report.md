# inkgrid on OCR benchmarks: born-digital text and tables, the M7a baseline

Measured on 2026-10-15 at commit `00cc5ca` by `bench/inkgrid_bench/run.py --datasets ocr`, under the pre-registered protocol of `docs/specs/18-ocr-benchmarks.md`. **Only born-digital pages and the benchmarks' text and table tests are scored**: a census taken before any tool read a page leaves out every page with almost no visible text, with as much invisible text as visible (an OCR layer over a scan), or with one image covering nine tenths of it, and the benchmarks' formula, chart and handwriting tests are not run, so no number here stands for a benchmark as a whole. Of the documents fetched (the categories and tracks spec 18 names), the census found 603 of olmOCR-bench's 747, 620 of OmniDocBench's 981, 827 of ParseBench's 1,009 (819 of them in a group scored here) and 196 of DP-Bench's 200 born-digital. **inkgrid's numbers are its baseline**: its reading as released in 0.1.0, before any fix designed from these benchmarks' failures (DR-0023). Later runs are labelled tuned. inkgrid, pymupdf4llm, markitdown and liteparse read the PDF's text layer; docling read it, with OCR only for a page's regions without text; marker read it with OCR off; docling-ocr, unstructured and inkgrid-ocr read the pages with OCR. `inkgrid-ocr` is inkgrid with Tesseract's words for its own. The heavy tools' seconds are a warm process's, its models loaded.

Each cell is the point estimate and its 95% interval from 10,000 resamples of documents (seed 20260928). A difference is inkgrid's number minus the tool's; one marked `*` has an interval that excludes 0, and only those are findings.

## The census

| Benchmark | Documents | Born-digital | No text | Image-backed | OCR layer | Scored |
| --- | --- | --- | --- | --- | --- | --- |
| olmOCR-bench | 747 | 603 | 125 | 14 | 5 | 603 |
| OmniDocBench | 981 | 620 | 264 | 97 | 0 | 620 |
| ParseBench | 1,009 | 827 | 159 | 22 | 1 | 819 |
| DP-Bench | 200 | 196 | 1 | 3 | 0 | 196 |

## olmOCR-bench (603 documents)

### Pass rates (587 documents)

| Tool | Headers and footers | Multi-column | Tables | Born-digital macro | Baseline tests |
| --- | --- | --- | --- | --- | --- |
| inkgrid | 0.286 [0.243, 0.333] | 0.615 [0.560, 0.671] | 0.547 [0.473, 0.622] | 0.483 [0.449, 0.517] | 0.997 [0.991, 1.000] |
| pymupdf4llm | 0.911 [0.880, 0.940] | 0.758 [0.716, 0.801] | 0.752 [0.691, 0.808] | 0.807 [0.781, 0.833] | 0.995 [0.988, 1.000] |
| markitdown | 0.338 [0.293, 0.386] | 0.447 [0.393, 0.501] | 0.275 [0.221, 0.331] | 0.353 [0.324, 0.383] | 0.986 [0.976, 0.995] |
| liteparse | 0.518 [0.470, 0.567] | 0.731 [0.685, 0.776] | 0.596 [0.531, 0.658] | 0.615 [0.584, 0.646] | 0.998 [0.995, 1.000] |
| docling | 0.899 [0.862, 0.933] | 0.789 [0.747, 0.830] | 0.767 [0.714, 0.817] | 0.818 [0.792, 0.843] | 0.997 [0.991, 1.000] |
| marker | 0.953 [0.925, 0.974] | 0.749 [0.705, 0.791] | 0.505 [0.436, 0.571] | 0.735 [0.707, 0.763] | 0.985 [0.974, 0.993] |
| docling-ocr | 0.914 [0.879, 0.946] | 0.734 [0.689, 0.777] | 0.753 [0.696, 0.805] | 0.800 [0.774, 0.826] | 0.983 [0.971, 0.992] |
| unstructured | 0.499 [0.455, 0.545] | 0.607 [0.561, 0.654] | 0.419 [0.361, 0.480] | 0.509 [0.480, 0.538] | 0.998 [0.995, 1.000] |
| inkgrid-ocr | 0.383 [0.343, 0.424] | 0.441 [0.391, 0.493] | 0.336 [0.279, 0.394] | 0.387 [0.358, 0.416] | 0.998 [0.995, 1.000] |

| Difference | Headers and footers | Multi-column | Tables | Born-digital macro | Baseline tests |
| --- | --- | --- | --- | --- | --- |
| inkgrid - pymupdf4llm | -0.625 [-0.673, -0.575] * | -0.143 [-0.195, -0.093] * | -0.204 [-0.277, -0.132] * | -0.324 [-0.358, -0.290] * | +0.002 [-0.003, +0.009] |
| inkgrid - markitdown | -0.052 [-0.083, -0.021] * | +0.169 [+0.098, +0.239] * | +0.273 [+0.190, +0.358] * | +0.130 [+0.092, +0.169] * | +0.010 [+0.002, +0.021] * |
| inkgrid - liteparse | -0.231 [-0.278, -0.184] * | -0.116 [-0.169, -0.064] * | -0.048 [-0.126, +0.033] | -0.132 [-0.167, -0.096] * | -0.002 [-0.007, +0.003] |
| inkgrid - docling | -0.613 [-0.669, -0.555] * | -0.174 [-0.226, -0.124] * | -0.219 [-0.297, -0.139] * | -0.335 [-0.372, -0.298] * | +0.000 [-0.007, +0.007] |
| inkgrid - marker | -0.666 [-0.713, -0.618] * | -0.134 [-0.184, -0.084] * | +0.043 [-0.029, +0.117] | -0.252 [-0.286, -0.219] * | +0.012 [+0.003, +0.022] * |
| inkgrid - docling-ocr | -0.628 [-0.683, -0.571] * | -0.119 [-0.180, -0.055] * | -0.206 [-0.290, -0.116] * | -0.317 [-0.357, -0.277] * | +0.014 [+0.003, +0.026] * |
| inkgrid - unstructured | -0.213 [-0.257, -0.170] * | +0.008 [-0.054, +0.070] | +0.128 [+0.034, +0.221] * | -0.026 [-0.065, +0.014] | -0.002 [-0.007, +0.003] |
| inkgrid - inkgrid-ocr | -0.096 [-0.141, -0.052] * | +0.174 [+0.118, +0.232] * | +0.211 [+0.152, +0.272] * | +0.096 [+0.065, +0.128] * | -0.002 [-0.007, +0.003] |

Each category's pass rate pools its tests; the born-digital macro is the mean of the headers-and-footers, multi-column and table rates. A headers-and-footers test checks only that a page's furniture is absent, so an empty page passes it; the benchmark's baseline test, one a page, fails a page with no text, one ending in repeated words, or one with characters the benchmark disallows.

### Long tiny text, reported apart (16 documents)

| Tool | Long tiny text | Baseline tests |
| --- | --- | --- |
| inkgrid | 0.421 [0.250, 0.612] | 1.000 [1.000, 1.000] |
| pymupdf4llm | 0.776 [0.679, 0.875] | 1.000 [1.000, 1.000] |
| markitdown | 0.383 [0.159, 0.630] | 1.000 [1.000, 1.000] |
| liteparse | 0.168 [0.071, 0.286] | 1.000 [1.000, 1.000] |
| docling | 0.916 [0.868, 0.962] | 1.000 [1.000, 1.000] |
| marker | 0.533 [0.357, 0.697] | 1.000 [1.000, 1.000] |
| docling-ocr | 0.879 [0.825, 0.934] | 0.938 [0.812, 1.000] |
| unstructured | 0.439 [0.263, 0.642] | 1.000 [1.000, 1.000] |
| inkgrid-ocr | 0.299 [0.195, 0.415] | 1.000 [1.000, 1.000] |

| Difference | Long tiny text | Baseline tests |
| --- | --- | --- |
| inkgrid - pymupdf4llm | -0.355 [-0.528, -0.200] * | +0.000 [+0.000, +0.000] |
| inkgrid - markitdown | +0.037 [-0.207, +0.240] | +0.000 [+0.000, +0.000] |
| inkgrid - liteparse | +0.252 [+0.058, +0.469] * | +0.000 [+0.000, +0.000] |
| inkgrid - docling | -0.495 [-0.670, -0.315] * | +0.000 [+0.000, +0.000] |
| inkgrid - marker | -0.112 [-0.420, +0.225] | +0.000 [+0.000, +0.000] |
| inkgrid - docling-ocr | -0.458 [-0.626, -0.288] * | +0.062 [+0.000, +0.188] |
| inkgrid - unstructured | -0.019 [-0.152, +0.092] | +0.000 [+0.000, +0.000] |
| inkgrid - inkgrid-ocr | +0.121 [+0.000, +0.284] | +0.000 [+0.000, +0.000] |

### Speed (603 documents)

| Tool | Seconds per page |
| --- | --- |
| inkgrid | 0.369 [0.339, 0.399] |
| pymupdf4llm | 0.548 [0.519, 0.580] |
| markitdown | 0.421 [0.402, 0.441] |
| liteparse | 0.021 [0.021, 0.022] |
| docling | 11.242 [10.302, 12.208] |
| marker | 0.630 [0.609, 0.659] |
| docling-ocr | 23.942 [22.921, 25.052] |
| unstructured | 22.236 [20.334, 24.654] |
| inkgrid-ocr | 13.151 [12.441, 13.909] |

| Difference | Seconds per page |
| --- | --- |
| inkgrid - pymupdf4llm | -0.180 [-0.211, -0.149] * |
| inkgrid - markitdown | -0.052 [-0.082, -0.021] * |
| inkgrid - liteparse | +0.347 [+0.318, +0.378] * |
| inkgrid - docling | -10.873 [-11.835, -9.939] * |
| inkgrid - marker | -0.261 [-0.300, -0.226] * |
| inkgrid - docling-ocr | -23.574 [-24.671, -22.558] * |
| inkgrid - unstructured | -21.867 [-24.276, -19.972] * |
| inkgrid - inkgrid-ocr | -12.782 [-13.536, -12.076] * |

Lower is better for seconds per page, so a negative difference favours inkgrid; a document a tool crashed or timed out on has no seconds.

## OmniDocBench v1.0, primary stratum: born-digital pages with no masked area (393 documents)

### Text, English pages (190 documents)

| Tool | Text Edit distance |
| --- | --- |
| inkgrid | 0.297 [0.256, 0.341] |
| pymupdf4llm | 0.125 [0.091, 0.163] |
| markitdown | 0.443 [0.389, 0.498] |
| liteparse | 0.236 [0.198, 0.277] |
| docling | 0.059 [0.037, 0.085] |
| marker | 0.077 [0.053, 0.105] |
| docling-ocr | 0.132 [0.103, 0.164] |
| unstructured | 0.136 [0.108, 0.167] |
| inkgrid-ocr | 0.339 [0.303, 0.376] |

| Difference | Text Edit distance |
| --- | --- |
| inkgrid - pymupdf4llm | +0.172 [+0.135, +0.212] * |
| inkgrid - markitdown | -0.146 [-0.207, -0.085] * |
| inkgrid - liteparse | +0.061 [+0.012, +0.111] * |
| inkgrid - docling | +0.238 [+0.195, +0.282] * |
| inkgrid - marker | +0.220 [+0.179, +0.264] * |
| inkgrid - docling-ocr | +0.165 [+0.116, +0.214] * |
| inkgrid - unstructured | +0.161 [+0.114, +0.210] * |
| inkgrid - inkgrid-ocr | -0.042 [-0.082, +0.001] |

Lower is better for an Edit distance, so a negative difference favours inkgrid; a page whose truth holds nothing of this kind is left out.

### Text, Chinese pages (195 documents)

| Tool | Text Edit distance |
| --- | --- |
| inkgrid | 0.510 [0.454, 0.566] |
| pymupdf4llm | 0.362 [0.312, 0.413] |
| markitdown | 0.589 [0.533, 0.645] |
| liteparse | 0.441 [0.390, 0.494] |
| docling | 0.182 [0.148, 0.218] |
| marker | 0.220 [0.178, 0.266] |
| docling-ocr | 0.193 [0.162, 0.226] |
| unstructured | 0.415 [0.364, 0.469] |
| inkgrid-ocr | 0.959 [0.949, 0.968] |

| Difference | Text Edit distance |
| --- | --- |
| inkgrid - pymupdf4llm | +0.148 [+0.089, +0.206] * |
| inkgrid - markitdown | -0.080 [-0.140, -0.022] * |
| inkgrid - liteparse | +0.068 [+0.013, +0.122] * |
| inkgrid - docling | +0.327 [+0.262, +0.392] * |
| inkgrid - marker | +0.289 [+0.218, +0.359] * |
| inkgrid - docling-ocr | +0.317 [+0.256, +0.377] * |
| inkgrid - unstructured | +0.094 [+0.038, +0.149] * |
| inkgrid - inkgrid-ocr | -0.449 [-0.503, -0.395] * |

Lower is better for an Edit distance, so a negative difference favours inkgrid; a page whose truth holds nothing of this kind is left out.
As OmniDocBench reports text by language, pages in mixed English and Chinese count in neither language's text; they count in the tables and the reading order.
inkgrid on Tesseract's words and unstructured OCR in English only, and Docling's image-only run in its default OCR languages, so they misread other scripts by design; the text-layer tools read whatever characters the PDF encodes.

### Tables (393 documents)

| Tool | Table TEDS | Table Edit distance |
| --- | --- | --- |
| inkgrid | 0.542 [0.472, 0.613] | 0.427 [0.357, 0.497] |
| pymupdf4llm | 0.786 [0.742, 0.827] | 0.175 [0.140, 0.214] |
| markitdown | 0.103 [0.071, 0.138] | 0.799 [0.774, 0.825] |
| liteparse | 0.491 [0.428, 0.553] | 0.689 [0.663, 0.717] |
| docling | 0.738 [0.682, 0.792] | 0.230 [0.183, 0.283] |
| marker | 0.405 [0.345, 0.464] | 0.487 [0.428, 0.546] |
| docling-ocr | 0.728 [0.669, 0.785] | 0.251 [0.198, 0.308] |
| unstructured | 0.420 [0.367, 0.474] | 0.450 [0.398, 0.501] |
| inkgrid-ocr | 0.344 [0.290, 0.397] | 0.581 [0.520, 0.640] |

| Difference | Table TEDS | Table Edit distance |
| --- | --- | --- |
| inkgrid - pymupdf4llm | -0.244 [-0.310, -0.178] * | +0.252 [+0.187, +0.321] * |
| inkgrid - markitdown | +0.439 [+0.364, +0.513] * | -0.372 [-0.442, -0.300] * |
| inkgrid - liteparse | +0.051 [-0.023, +0.126] | -0.261 [-0.328, -0.195] * |
| inkgrid - docling | -0.196 [-0.283, -0.111] * | +0.197 [+0.113, +0.280] * |
| inkgrid - marker | +0.137 [+0.045, +0.230] * | -0.060 [-0.150, +0.029] |
| inkgrid - docling-ocr | -0.186 [-0.269, -0.104] * | +0.176 [+0.094, +0.258] * |
| inkgrid - unstructured | +0.122 [+0.029, +0.213] * | -0.022 [-0.109, +0.066] |
| inkgrid - inkgrid-ocr | +0.198 [+0.144, +0.254] * | -0.153 [-0.205, -0.103] * |

A page's TEDS is the mean over its truth's tables, and each number is the mean over the pages with a table in their truth, as OmniDocBench averages them. Lower is better for a table Edit distance, so there a negative difference favours inkgrid.

### Reading order (393 documents)

| Tool | Reading-order Edit distance |
| --- | --- |
| inkgrid | 0.274 [0.238, 0.312] |
| pymupdf4llm | 0.234 [0.201, 0.268] |
| markitdown | 0.391 [0.353, 0.429] |
| liteparse | 0.243 [0.211, 0.275] |
| docling | 0.152 [0.127, 0.179] |
| marker | 0.228 [0.196, 0.262] |
| docling-ocr | 0.215 [0.189, 0.244] |
| unstructured | 0.268 [0.233, 0.303] |
| inkgrid-ocr | 0.380 [0.341, 0.419] |

| Difference | Reading-order Edit distance |
| --- | --- |
| inkgrid - pymupdf4llm | +0.041 [+0.010, +0.072] * |
| inkgrid - markitdown | -0.116 [-0.158, -0.075] * |
| inkgrid - liteparse | +0.032 [-0.001, +0.065] |
| inkgrid - docling | +0.122 [+0.086, +0.158] * |
| inkgrid - marker | +0.046 [+0.010, +0.082] * |
| inkgrid - docling-ocr | +0.059 [+0.024, +0.094] * |
| inkgrid - unstructured | +0.007 [-0.028, +0.043] |
| inkgrid - inkgrid-ocr | -0.106 [-0.140, -0.071] * |

Lower is better for an Edit distance, so a negative difference favours inkgrid; a page whose truth holds nothing of this kind is left out.

## OmniDocBench v1.0, every born-digital page (620 documents)

### Text, English pages (260 documents)

| Tool | Text Edit distance |
| --- | --- |
| inkgrid | 0.276 [0.243, 0.310] |
| pymupdf4llm | 0.109 [0.082, 0.139] |
| markitdown | 0.412 [0.367, 0.459] |
| liteparse | 0.240 [0.207, 0.275] |
| docling | 0.063 [0.044, 0.085] |
| marker | 0.072 [0.053, 0.094] |
| docling-ocr | 0.127 [0.103, 0.154] |
| unstructured | 0.123 [0.101, 0.148] |
| inkgrid-ocr | 0.317 [0.287, 0.348] |

| Difference | Text Edit distance |
| --- | --- |
| inkgrid - pymupdf4llm | +0.167 [+0.135, +0.199] * |
| inkgrid - markitdown | -0.136 [-0.187, -0.084] * |
| inkgrid - liteparse | +0.036 [-0.004, +0.076] |
| inkgrid - docling | +0.213 [+0.176, +0.250] * |
| inkgrid - marker | +0.203 [+0.169, +0.239] * |
| inkgrid - docling-ocr | +0.149 [+0.108, +0.188] * |
| inkgrid - unstructured | +0.153 [+0.115, +0.191] * |
| inkgrid - inkgrid-ocr | -0.041 [-0.074, -0.008] * |

Lower is better for an Edit distance, so a negative difference favours inkgrid; a page whose truth holds nothing of this kind is left out.

### Text, Chinese pages (350 documents)

| Tool | Text Edit distance |
| --- | --- |
| inkgrid | 0.444 [0.398, 0.488] |
| pymupdf4llm | 0.300 [0.263, 0.338] |
| markitdown | 0.536 [0.493, 0.579] |
| liteparse | 0.385 [0.346, 0.424] |
| docling | 0.134 [0.111, 0.158] |
| marker | 0.158 [0.130, 0.187] |
| docling-ocr | 0.157 [0.135, 0.180] |
| unstructured | 0.366 [0.324, 0.408] |
| inkgrid-ocr | 0.962 [0.955, 0.968] |

| Difference | Text Edit distance |
| --- | --- |
| inkgrid - pymupdf4llm | +0.143 [+0.104, +0.182] * |
| inkgrid - markitdown | -0.092 [-0.136, -0.048] * |
| inkgrid - liteparse | +0.059 [+0.020, +0.098] * |
| inkgrid - docling | +0.310 [+0.263, +0.357] * |
| inkgrid - marker | +0.286 [+0.236, +0.336] * |
| inkgrid - docling-ocr | +0.286 [+0.243, +0.331] * |
| inkgrid - unstructured | +0.078 [+0.039, +0.115] * |
| inkgrid - inkgrid-ocr | -0.518 [-0.563, -0.475] * |

Lower is better for an Edit distance, so a negative difference favours inkgrid; a page whose truth holds nothing of this kind is left out.
As OmniDocBench reports text by language, pages in mixed English and Chinese count in neither language's text; they count in the tables and the reading order.
inkgrid on Tesseract's words and unstructured OCR in English only, and Docling's image-only run in its default OCR languages, so they misread other scripts by design; the text-layer tools read whatever characters the PDF encodes.

### Tables (620 documents)

| Tool | Table TEDS | Table Edit distance |
| --- | --- | --- |
| inkgrid | 0.558 [0.505, 0.610] | 0.410 [0.358, 0.462] |
| pymupdf4llm | 0.772 [0.736, 0.806] | 0.195 [0.166, 0.227] |
| markitdown | 0.142 [0.112, 0.175] | 0.799 [0.780, 0.819] |
| liteparse | 0.460 [0.413, 0.509] | 0.707 [0.687, 0.728] |
| docling | 0.754 [0.713, 0.794] | 0.217 [0.182, 0.254] |
| marker | 0.470 [0.424, 0.518] | 0.431 [0.386, 0.474] |
| docling-ocr | 0.746 [0.704, 0.788] | 0.233 [0.194, 0.272] |
| unstructured | 0.426 [0.388, 0.464] | 0.436 [0.399, 0.473] |
| inkgrid-ocr | 0.342 [0.304, 0.380] | 0.579 [0.537, 0.622] |

| Difference | Table TEDS | Table Edit distance |
| --- | --- | --- |
| inkgrid - pymupdf4llm | -0.214 [-0.262, -0.166] * | +0.214 [+0.165, +0.265] * |
| inkgrid - markitdown | +0.416 [+0.357, +0.473] * | -0.390 [-0.443, -0.336] * |
| inkgrid - liteparse | +0.098 [+0.040, +0.156] * | -0.297 [-0.347, -0.247] * |
| inkgrid - docling | -0.196 [-0.254, -0.139] * | +0.193 [+0.135, +0.250] * |
| inkgrid - marker | +0.088 [+0.021, +0.155] * | -0.021 [-0.086, +0.043] |
| inkgrid - docling-ocr | -0.189 [-0.246, -0.133] * | +0.177 [+0.119, +0.235] * |
| inkgrid - unstructured | +0.132 [+0.071, +0.194] * | -0.026 [-0.086, +0.034] |
| inkgrid - inkgrid-ocr | +0.216 [+0.176, +0.256] * | -0.169 [-0.206, -0.134] * |

A page's TEDS is the mean over its truth's tables, and each number is the mean over the pages with a table in their truth, as OmniDocBench averages them. Lower is better for a table Edit distance, so there a negative difference favours inkgrid.

### Reading order (620 documents)

| Tool | Reading-order Edit distance |
| --- | --- |
| inkgrid | 0.263 [0.234, 0.293] |
| pymupdf4llm | 0.217 [0.192, 0.243] |
| markitdown | 0.371 [0.341, 0.402] |
| liteparse | 0.247 [0.221, 0.273] |
| docling | 0.150 [0.130, 0.170] |
| marker | 0.232 [0.206, 0.259] |
| docling-ocr | 0.205 [0.184, 0.227] |
| unstructured | 0.273 [0.243, 0.302] |
| inkgrid-ocr | 0.416 [0.384, 0.449] |

| Difference | Reading-order Edit distance |
| --- | --- |
| inkgrid - pymupdf4llm | +0.046 [+0.024, +0.069] * |
| inkgrid - markitdown | -0.108 [-0.138, -0.077] * |
| inkgrid - liteparse | +0.017 [-0.009, +0.043] |
| inkgrid - docling | +0.114 [+0.087, +0.140] * |
| inkgrid - marker | +0.031 [+0.004, +0.058] * |
| inkgrid - docling-ocr | +0.058 [+0.033, +0.083] * |
| inkgrid - unstructured | -0.009 [-0.034, +0.016] |
| inkgrid - inkgrid-ocr | -0.153 [-0.181, -0.125] * |

Lower is better for an Edit distance, so a negative difference favours inkgrid; a page whose truth holds nothing of this kind is left out.

### Speed (620 documents)

| Tool | Seconds per page |
| --- | --- |
| inkgrid | 0.567 [0.519, 0.618] |
| pymupdf4llm | 0.733 [0.674, 0.803] |
| markitdown | 0.502 [0.470, 0.536] |
| liteparse | 0.034 [0.032, 0.037] |
| docling | 14.632 [13.528, 15.810] |
| marker | 0.749 [0.717, 0.783] |
| docling-ocr | 48.168 [45.294, 51.105] |
| unstructured | 33.266 [25.193, 42.384] |
| inkgrid-ocr | 15.640 [13.355, 18.274] |

| Difference | Seconds per page |
| --- | --- |
| inkgrid - pymupdf4llm | -0.165 [-0.225, -0.112] * |
| inkgrid - markitdown | +0.065 [+0.027, +0.105] * |
| inkgrid - liteparse | +0.533 [+0.486, +0.582] * |
| inkgrid - docling | -14.065 [-15.229, -12.984] * |
| inkgrid - marker | -0.182 [-0.214, -0.148] * |
| inkgrid - docling-ocr | -47.601 [-50.507, -44.747] * |
| inkgrid - unstructured | -32.699 [-41.789, -24.648] * |
| inkgrid - inkgrid-ocr | -15.072 [-17.694, -12.795] * |

Lower is better for seconds per page, so a negative difference favours inkgrid; a document a tool crashed or timed out on has no seconds.

## ParseBench (819 documents)

### Tables (495 documents)

| Tool | GTRM | GriTS-Con | TableRecordMatch |
| --- | --- | --- | --- |
| inkgrid | 0.517 [0.485, 0.548] | 0.658 [0.626, 0.689] | 0.344 [0.307, 0.381] |
| pymupdf4llm | 0.722 [0.694, 0.750] | 0.815 [0.789, 0.840] | 0.602 [0.565, 0.639] |
| markitdown | 0.159 [0.141, 0.178] | 0.245 [0.220, 0.271] | 0.056 [0.041, 0.073] |
| liteparse | 0.429 [0.401, 0.456] | 0.596 [0.566, 0.626] | 0.235 [0.204, 0.269] |
| docling | 0.697 [0.665, 0.728] | 0.774 [0.743, 0.803] | 0.605 [0.568, 0.641] |
| marker | 0.414 [0.386, 0.441] | 0.558 [0.527, 0.590] | 0.248 [0.218, 0.278] |
| docling-ocr | 0.667 [0.635, 0.698] | 0.744 [0.712, 0.775] | 0.575 [0.539, 0.611] |
| unstructured | 0.363 [0.343, 0.383] | 0.542 [0.516, 0.567] | 0.154 [0.133, 0.175] |
| inkgrid-ocr | 0.325 [0.302, 0.350] | 0.475 [0.446, 0.505] | 0.143 [0.121, 0.166] |

| Difference | GTRM | GriTS-Con | TableRecordMatch |
| --- | --- | --- | --- |
| inkgrid - pymupdf4llm | -0.206 [-0.242, -0.169] * | -0.157 [-0.192, -0.122] * | -0.258 [-0.303, -0.214] * |
| inkgrid - markitdown | +0.358 [+0.321, +0.393] * | +0.413 [+0.374, +0.452] * | +0.288 [+0.249, +0.328] * |
| inkgrid - liteparse | +0.088 [+0.053, +0.123] * | +0.061 [+0.022, +0.100] * | +0.109 [+0.071, +0.147] * |
| inkgrid - docling | -0.180 [-0.220, -0.140] * | -0.116 [-0.155, -0.075] * | -0.261 [-0.307, -0.214] * |
| inkgrid - marker | +0.103 [+0.060, +0.146] * | +0.099 [+0.054, +0.144] * | +0.096 [+0.050, +0.143] * |
| inkgrid - docling-ocr | -0.150 [-0.190, -0.109] * | -0.086 [-0.128, -0.045] * | -0.231 [-0.278, -0.184] * |
| inkgrid - unstructured | +0.154 [+0.116, +0.191] * | +0.116 [+0.075, +0.156] * | +0.191 [+0.148, +0.233] * |
| inkgrid - inkgrid-ocr | +0.191 [+0.168, +0.215] * | +0.183 [+0.159, +0.206] * | +0.202 [+0.173, +0.231] * |

GTRM is ParseBench's headline table metric: the mean of GriTS-Con and TableRecordMatch, or GriTS-Con alone for a table ParseBench cannot match by its records. Every page is scored, a page whose reading has no table at 0.

### Text (simple, multi-column, misc, dense, sparse) (286 documents)

| Tool | Content faithfulness | Text correctness | Order |
| --- | --- | --- | --- |
| inkgrid | 0.846 [0.825, 0.867] | 0.889 [0.874, 0.903] | 0.758 [0.717, 0.798] |
| pymupdf4llm | 0.847 [0.826, 0.866] | 0.868 [0.851, 0.882] | 0.810 [0.775, 0.843] |
| markitdown | 0.864 [0.844, 0.884] | 0.899 [0.884, 0.912] | 0.796 [0.758, 0.832] |
| liteparse | 0.860 [0.840, 0.878] | 0.889 [0.875, 0.902] | 0.800 [0.766, 0.833] |
| docling | 0.854 [0.833, 0.873] | 0.870 [0.852, 0.885] | 0.827 [0.796, 0.857] |
| marker | 0.812 [0.787, 0.836] | 0.837 [0.815, 0.857] | 0.774 [0.740, 0.808] |
| docling-ocr | 0.803 [0.785, 0.820] | 0.847 [0.833, 0.861] | 0.717 [0.687, 0.747] |
| unstructured | 0.875 [0.859, 0.889] | 0.889 [0.877, 0.901] | 0.848 [0.820, 0.874] |
| inkgrid-ocr | 0.805 [0.784, 0.826] | 0.855 [0.840, 0.868] | 0.706 [0.664, 0.747] |

| Difference | Content faithfulness | Text correctness | Order |
| --- | --- | --- | --- |
| inkgrid - pymupdf4llm | -0.001 [-0.017, +0.017] | +0.022 [+0.012, +0.033] * | -0.051 [-0.086, -0.018] * |
| inkgrid - markitdown | -0.018 [-0.034, -0.002] * | -0.009 [-0.020, +0.000] | -0.037 [-0.071, -0.004] * |
| inkgrid - liteparse | -0.013 [-0.030, +0.002] | +0.000 [-0.011, +0.010] | -0.042 [-0.075, -0.010] * |
| inkgrid - docling | -0.007 [-0.025, +0.010] | +0.020 [+0.009, +0.032] * | -0.069 [-0.103, -0.035] * |
| inkgrid - marker | +0.034 [+0.012, +0.058] * | +0.053 [+0.037, +0.071] * | -0.016 [-0.056, +0.023] |
| inkgrid - docling-ocr | +0.043 [+0.019, +0.067] * | +0.042 [+0.026, +0.058] * | +0.041 [-0.004, +0.085] |
| inkgrid - unstructured | -0.028 [-0.047, -0.010] * | +0.000 [-0.014, +0.013] | -0.089 [-0.126, -0.054] * |
| inkgrid - inkgrid-ocr | +0.041 [+0.022, +0.060] * | +0.034 [+0.021, +0.047] * | +0.052 [+0.017, +0.088] * |

### Text, multilingual (38 documents)

| Tool | Content faithfulness | Text correctness | Order |
| --- | --- | --- | --- |
| inkgrid | 0.666 [0.576, 0.751] | 0.720 [0.651, 0.785] | 0.558 [0.418, 0.693] |
| pymupdf4llm | 0.638 [0.551, 0.721] | 0.691 [0.624, 0.754] | 0.533 [0.398, 0.664] |
| markitdown | 0.639 [0.544, 0.729] | 0.699 [0.627, 0.769] | 0.519 [0.375, 0.656] |
| liteparse | 0.629 [0.543, 0.712] | 0.703 [0.636, 0.767] | 0.481 [0.352, 0.608] |
| docling | 0.611 [0.517, 0.698] | 0.674 [0.601, 0.743] | 0.484 [0.347, 0.614] |
| marker | 0.602 [0.508, 0.691] | 0.661 [0.580, 0.735] | 0.484 [0.355, 0.610] |
| docling-ocr | 0.493 [0.417, 0.571] | 0.598 [0.538, 0.658] | 0.284 [0.171, 0.399] |
| unstructured | 0.644 [0.554, 0.730] | 0.687 [0.620, 0.753] | 0.557 [0.416, 0.691] |
| inkgrid-ocr | 0.410 [0.345, 0.481] | 0.533 [0.479, 0.591] | 0.163 [0.070, 0.267] |

| Difference | Content faithfulness | Text correctness | Order |
| --- | --- | --- | --- |
| inkgrid - pymupdf4llm | +0.028 [+0.004, +0.053] * | +0.029 [+0.013, +0.044] * | +0.025 [-0.026, +0.089] |
| inkgrid - markitdown | +0.027 [-0.004, +0.068] | +0.020 [-0.004, +0.051] | +0.039 [-0.018, +0.114] |
| inkgrid - liteparse | +0.037 [+0.015, +0.062] * | +0.017 [+0.002, +0.032] * | +0.077 [+0.029, +0.134] * |
| inkgrid - docling | +0.055 [+0.014, +0.103] * | +0.046 [+0.023, +0.074] * | +0.074 [-0.012, +0.170] |
| inkgrid - marker | +0.064 [+0.022, +0.109] * | +0.059 [+0.030, +0.097] * | +0.074 [-0.008, +0.156] |
| inkgrid - docling-ocr | +0.173 [+0.097, +0.252] * | +0.122 [+0.065, +0.183] * | +0.274 [+0.150, +0.408] * |
| inkgrid - unstructured | +0.022 [+0.005, +0.041] * | +0.033 [+0.015, +0.054] * | +0.001 [-0.030, +0.031] |
| inkgrid - inkgrid-ocr | +0.256 [+0.182, +0.332] * | +0.187 [+0.136, +0.239] * | +0.395 [+0.264, +0.530] * |

inkgrid on Tesseract's words and unstructured OCR in English only, and Docling's image-only run in its default OCR languages, so they misread other scripts by design; the text-layer tools read whatever characters the PDF encodes.

### Speed (819 documents)

| Tool | Seconds per page |
| --- | --- |
| inkgrid | 0.498 [0.447, 0.560] |
| pymupdf4llm | 1.079 [0.991, 1.182] |
| markitdown | 0.558 [0.477, 0.691] |
| liteparse | 0.022 [0.021, 0.022] |
| docling | 18.437 [16.872, 20.069] |
| marker | 0.624 [0.610, 0.638] |
| docling-ocr | 47.151 [44.312, 50.026] |
| unstructured | 21.324 [19.831, 22.963] |
| inkgrid-ocr | 10.731 [9.661, 11.970] |

| Difference | Seconds per page |
| --- | --- |
| inkgrid - pymupdf4llm | -0.580 [-0.663, -0.505] * |
| inkgrid - markitdown | -0.060 [-0.201, +0.044] |
| inkgrid - liteparse | +0.477 [+0.426, +0.538] * |
| inkgrid - docling | -17.938 [-19.565, -16.393] * |
| inkgrid - marker | -0.126 [-0.173, -0.068] * |
| inkgrid - docling-ocr | -46.653 [-49.518, -43.824] * |
| inkgrid - unstructured | -20.826 [-22.427, -19.366] * |
| inkgrid - inkgrid-ocr | -10.233 [-11.440, -9.191] * |

Lower is better for seconds per page, so a negative difference favours inkgrid; a document a tool crashed or timed out on has no seconds.

## DP-Bench (196 documents)

### Text, tables and headings (196 documents)

| Tool | NID | TEDS | MHS |
| --- | --- | --- | --- |
| inkgrid | 0.905 [0.887, 0.921] | 0.645 [0.509, 0.772] | 0.673 [0.611, 0.735] |
| pymupdf4llm | 0.903 [0.887, 0.918] | 0.860 [0.772, 0.934] | 0.775 [0.732, 0.814] |
| markitdown | 0.849 [0.824, 0.873] | 0.280 [0.183, 0.380] | 0.000 [0.000, 0.000] |
| liteparse | 0.918 [0.904, 0.931] | 0.827 [0.747, 0.895] | 0.840 [0.796, 0.882] |
| docling | 0.912 [0.899, 0.925] | 0.953 [0.922, 0.979] | 0.838 [0.801, 0.872] |
| marker | 0.865 [0.844, 0.884] | 0.601 [0.492, 0.704] | 0.761 [0.719, 0.801] |
| docling-ocr | 0.880 [0.864, 0.896] | 0.927 [0.892, 0.958] | 0.817 [0.779, 0.852] |
| unstructured | 0.893 [0.874, 0.911] | 0.604 [0.514, 0.690] | 0.759 [0.703, 0.810] |
| inkgrid-ocr | 0.905 [0.887, 0.922] | 0.495 [0.368, 0.619] | 0.390 [0.334, 0.447] |

| Difference | NID | TEDS | MHS |
| --- | --- | --- | --- |
| inkgrid - pymupdf4llm | +0.001 [-0.015, +0.017] | -0.215 [-0.338, -0.098] * | -0.101 [-0.159, -0.046] * |
| inkgrid - markitdown | +0.055 [+0.031, +0.082] * | +0.365 [+0.231, +0.498] * | +0.673 [+0.611, +0.735] * |
| inkgrid - liteparse | -0.013 [-0.023, -0.004] * | -0.182 [-0.318, -0.055] * | -0.167 [-0.230, -0.106] * |
| inkgrid - docling | -0.008 [-0.025, +0.009] | -0.308 [-0.435, -0.193] * | -0.165 [-0.219, -0.112] * |
| inkgrid - marker | +0.040 [+0.019, +0.061] * | +0.044 [-0.089, +0.176] | -0.087 [-0.148, -0.030] * |
| inkgrid - docling-ocr | +0.024 [+0.005, +0.043] * | -0.281 [-0.409, -0.165] * | -0.143 [-0.200, -0.087] * |
| inkgrid - unstructured | +0.011 [-0.005, +0.028] | +0.041 [-0.062, +0.140] | -0.085 [-0.157, -0.010] * |
| inkgrid - inkgrid-ocr | -0.001 [-0.015, +0.014] | +0.150 [+0.082, +0.228] * | +0.284 [+0.202, +0.365] * |

NID scores the page's text in reading order; TEDS only pages whose truth has a table, and MHS only pages whose truth has a heading.

### Speed (196 documents)

| Tool | Seconds per page |
| --- | --- |
| inkgrid | 0.175 [0.143, 0.210] |
| pymupdf4llm | 0.631 [0.600, 0.663] |
| markitdown | 0.344 [0.327, 0.362] |
| liteparse | 0.014 [0.013, 0.015] |
| docling | 5.508 [4.868, 6.168] |
| marker | 0.520 [0.506, 0.535] |
| docling-ocr | 25.710 [24.014, 27.528] |
| unstructured | 10.659 [10.214, 11.113] |
| inkgrid-ocr | 6.492 [6.113, 6.885] |

| Difference | Seconds per page |
| --- | --- |
| inkgrid - pymupdf4llm | -0.456 [-0.493, -0.417] * |
| inkgrid - markitdown | -0.169 [-0.207, -0.128] * |
| inkgrid - liteparse | +0.161 [+0.129, +0.196] * |
| inkgrid - docling | -5.333 [-5.986, -4.700] * |
| inkgrid - marker | -0.345 [-0.379, -0.308] * |
| inkgrid - docling-ocr | -25.535 [-27.352, -23.838] * |
| inkgrid - unstructured | -10.483 [-10.934, -10.046] * |
| inkgrid - inkgrid-ocr | -6.317 [-6.709, -5.943] * |

Lower is better for seconds per page, so a negative difference favours inkgrid; a document a tool crashed or timed out on has no seconds.

## Crashes and timeouts (each scored as an empty page)

| Tool | Benchmark | Documents |
| --- | --- | --- |
| markitdown | olmOCR-bench | 7: multi_column/0225d691d6da96027cb8edd0c41da512dd36_page_2_pg1.pdf (- PdfConverter threw PDFKeyError with message: "PDF stream object 8 does not have attribute 'N'"); multi_column/070ad839eef2587442b064a135bbf8cbea3d_page_4_pg1.pdf (- PdfConverter threw PDFKeyError with message: "PDF stream object 8 does not have attribute 'N'"); multi_column/0845863d27c84b14011e17a388821525e783_page_12_pg1.pdf (- PdfConverter threw PDFKeyError with message: "PDF stream object 108 does not have attribute 'N'"); multi_column/0845863d27c84b14011e17a388821525e783_page_16_pg1.pdf (- PdfConverter threw PDFKeyError with message: "PDF stream object 56 does not have attribute 'N'"); multi_column/0845863d27c84b14011e17a388821525e783_page_4_pg1.pdf (- PdfConverter threw PDFKeyError with message: "PDF stream object 110 does not have attribute 'N'"); multi_column/0845863d27c84b14011e17a388821525e783_page_6_pg1.pdf (- PdfConverter threw PDFKeyError with message: "PDF stream object 70 does not have attribute 'N'"); multi_column/0da8fcaacd0a502c317f9d222a55ffbb81e1_page_7_pg1.pdf (- PdfConverter threw PDFKeyError with message: "PDF stream object 69 does not have attribute 'N'") |
| unstructured | OmniDocBench | 54: newspaper_01f020903d7bc4b3fc69f500f41eb77e_1 (timeout after 900 s); newspaper_028a1dd5500fbd774e4d85df3c460c4d_1 (timeout after 300 s); newspaper_02912feb79994ae24665509d964ad9ce_1 (timeout after 300 s); newspaper_06b975dbc47dc2dc2a3a1468293f6a2c_1 (timeout after 900 s); newspaper_0b1bb8d03b4287eb95f67b68c2cf9f92_1 (timeout after 900 s); newspaper_0b86dae4d8f328a0e79d9ac394000dec_1 (timeout after 900 s); newspaper_0ce88e1e131aef7a59d0533be36870de_1 (timeout after 900 s); newspaper_0cfb8a42b5d4194d8c73dba0cdf6256c_1 (timeout after 900 s); newspaper_14b9d21f7fed39fb42849e9cde233930_1 (timeout after 900 s); newspaper_1cddf9d22ca549f3a86cf1512a3110cc_1 (timeout after 900 s); newspaper_26f4ed67a5e8922e7d42b35d317ebf4b_1 (timeout after 300 s); newspaper_2a645bfcbcd473423581cd9f1ceb778e_1 (timeout after 900 s); newspaper_2c69e142b52dbb30cac2cb11d3eb25e5_1 (timeout after 300 s); newspaper_2de954934f60ac538c5bd5dc40833a61_1 (timeout after 900 s); newspaper_35352f94db65d19e097395380498ec15_1 (timeout after 900 s); newspaper_354720d92a632709eb8e61795b191390_1 (timeout after 900 s); newspaper_35bdaa11dec104ccbdc9e19ac8527d21_1 (timeout after 900 s); newspaper_401c73055b88a62c479edd3d490cea8a_1 (timeout after 900 s); newspaper_41a09cb64841567c220d8cac3c1cc193_1 (timeout after 900 s); newspaper_4790b51e8fa793743699647c09a93ccb_1 (timeout after 900 s); newspaper_5a8b7563a3262beecbecd7ddd3ef8827_1 (timeout after 900 s); newspaper_5aedf678eff04d8ebac3692d54103e19_1 (timeout after 300 s); newspaper_5bba361b0a5ca11745edbef140e2a431_1 (timeout after 300 s); newspaper_5c4e17f22cdc19d414a3c521f631c899_1 (timeout after 900 s); newspaper_5e8bcc55b922fd521a667c6ef01027d5_1 (timeout after 900 s); newspaper_635e4e6a64cf2ccfb2560f9b6dfe24b5_1 (timeout after 300 s); newspaper_73fc8720a9b2798307ba43a8b8e47b5e_1 (timeout after 900 s); newspaper_74fc3b01b2cc4a7e6ca0f1af2b998187_1 (timeout after 900 s); newspaper_75bb60c3be9959e1be400d6b8281fea1_1 (timeout after 300 s); newspaper_7746db2ad2ea24c827eac60244375bbf_1 (timeout after 900 s); newspaper_87769622e073730af94822416c60c710_1 (timeout after 900 s); newspaper_95f2062735b213b3d7d471a48d5ec71b_1 (timeout after 900 s); newspaper_9729b78cbf9f2820b9f257fff7e3171b_1 (timeout after 900 s); newspaper_9eafddb83b0f7f99c42ff364b080e2c1_1 (timeout after 900 s); newspaper_a105e3b0ddb10be6a596f76407c79180_1 (timeout after 900 s); newspaper_a15057349a86850e55b084c235fa2f22_1 (timeout after 900 s); newspaper_a7666484ee01a811247e52f784164cbb_1 (timeout after 900 s); newspaper_b615618f3cdb0f2c13ffb5865dea799c_1 (timeout after 900 s); newspaper_bd75af5f4791aa56ef05ce2443e8a7e0_1 (timeout after 900 s); newspaper_c0794b9574ba55a589418fa1ae160b9a_1 (timeout after 900 s); newspaper_c3c88b76543e2caf044c9f7689f23ec9_1 (timeout after 900 s); newspaper_c9e9b3e7b8a5f5a5b59304a9924c41b9_1 (timeout after 900 s); newspaper_dd99f17cad0992a54fdf424b1c5e86ee_1 (timeout after 300 s); newspaper_e3842a5681ef54c62a58804adec06c3f_1 (timeout after 900 s); newspaper_e567840b2e327602422573ccdc1c4275_1 (timeout after 300 s); newspaper_e62730aaeb9b509119e0c3699ac18201_1 (timeout after 900 s); newspaper_e6ddb0246224fb8bd8788e6cc7839021_1 (timeout after 300 s); newspaper_e7246d706077d2064a6e667dfc73925e_1 (timeout after 900 s); newspaper_e81b9b3561d4d4e865ff6713782fd432_1 (timeout after 900 s); newspaper_eb569707cf5621d4c71d5898216cdb17_1 (timeout after 900 s); newspaper_ef5c785d9cc21ccf6b73d143f231b5c5_1 (timeout after 900 s); newspaper_f1de032fb6a25cf85c85c15cb2d2a63a_1 (timeout after 900 s); newspaper_f36d00fe3544ae72725aac9dc7f19aa8_1 (timeout after 900 s); newspaper_fe2c8b45b2a086cd75984640bb3080e1_1 (timeout after 900 s) |
| inkgrid-ocr | OmniDocBench | 61: newspaper_019d4d5296ba8f1c21277d72fb0cf0db_1 (timeout after 300 s); newspaper_01f020903d7bc4b3fc69f500f41eb77e_1 (timeout after 300 s); newspaper_028a1dd5500fbd774e4d85df3c460c4d_1 (timeout after 300 s); newspaper_02912feb79994ae24665509d964ad9ce_1 (timeout after 300 s); newspaper_06b975dbc47dc2dc2a3a1468293f6a2c_1 (timeout after 300 s); newspaper_0b1bb8d03b4287eb95f67b68c2cf9f92_1 (timeout after 300 s); newspaper_0b86dae4d8f328a0e79d9ac394000dec_1 (timeout after 300 s); newspaper_0ce88e1e131aef7a59d0533be36870de_1 (timeout after 300 s); newspaper_0cfb8a42b5d4194d8c73dba0cdf6256c_1 (timeout after 300 s); newspaper_14b9d21f7fed39fb42849e9cde233930_1 (timeout after 300 s); newspaper_1cddf9d22ca549f3a86cf1512a3110cc_1 (timeout after 300 s); newspaper_26f4ed67a5e8922e7d42b35d317ebf4b_1 (timeout after 300 s); newspaper_2a645bfcbcd473423581cd9f1ceb778e_1 (timeout after 300 s); newspaper_2c69e142b52dbb30cac2cb11d3eb25e5_1 (timeout after 300 s); newspaper_2de954934f60ac538c5bd5dc40833a61_1 (timeout after 300 s); newspaper_35352f94db65d19e097395380498ec15_1 (timeout after 300 s); newspaper_354720d92a632709eb8e61795b191390_1 (timeout after 300 s); newspaper_35bdaa11dec104ccbdc9e19ac8527d21_1 (timeout after 300 s); newspaper_401c73055b88a62c479edd3d490cea8a_1 (timeout after 300 s); newspaper_41a09cb64841567c220d8cac3c1cc193_1 (timeout after 300 s); newspaper_4790b51e8fa793743699647c09a93ccb_1 (timeout after 300 s); newspaper_571a946262006cd89199b67353c408b8_1 (timeout after 300 s); newspaper_5a8b7563a3262beecbecd7ddd3ef8827_1 (timeout after 300 s); newspaper_5bba361b0a5ca11745edbef140e2a431_1 (timeout after 300 s); newspaper_5c4e17f22cdc19d414a3c521f631c899_1 (timeout after 300 s); newspaper_5d4b8e73eacbc6ecac0d7b1396fd01d7_1 (timeout after 300 s); newspaper_5e8bcc55b922fd521a667c6ef01027d5_1 (timeout after 300 s); newspaper_635e4e6a64cf2ccfb2560f9b6dfe24b5_1 (timeout after 300 s); newspaper_73fc8720a9b2798307ba43a8b8e47b5e_1 (timeout after 300 s); newspaper_74fc3b01b2cc4a7e6ca0f1af2b998187_1 (timeout after 300 s); newspaper_75bb60c3be9959e1be400d6b8281fea1_1 (timeout after 300 s); newspaper_7746db2ad2ea24c827eac60244375bbf_1 (timeout after 300 s); newspaper_87769622e073730af94822416c60c710_1 (timeout after 300 s); newspaper_95f2062735b213b3d7d471a48d5ec71b_1 (timeout after 300 s); newspaper_9729b78cbf9f2820b9f257fff7e3171b_1 (timeout after 300 s); newspaper_9bb9e05d38b370251a4b0a8d070d1d55_1 (timeout after 300 s); newspaper_9eafddb83b0f7f99c42ff364b080e2c1_1 (timeout after 300 s); newspaper_a105e3b0ddb10be6a596f76407c79180_1 (timeout after 300 s); newspaper_a15057349a86850e55b084c235fa2f22_1 (timeout after 300 s); newspaper_a7666484ee01a811247e52f784164cbb_1 (timeout after 300 s); newspaper_b615618f3cdb0f2c13ffb5865dea799c_1 (timeout after 300 s); newspaper_bd75af5f4791aa56ef05ce2443e8a7e0_1 (timeout after 300 s); newspaper_c0794b9574ba55a589418fa1ae160b9a_1 (timeout after 300 s); newspaper_c3c88b76543e2caf044c9f7689f23ec9_1 (timeout after 300 s); newspaper_c8e8e00e1b1a70aa44afd1fbdaf59430_1 (timeout after 300 s); newspaper_c9e9b3e7b8a5f5a5b59304a9924c41b9_1 (timeout after 300 s); newspaper_d6cd76e5afe881630173bd4921531a4b_1 (timeout after 300 s); newspaper_d84e38031cf03d3fd4649910cf0ecce1_1 (timeout after 300 s); newspaper_dd99f17cad0992a54fdf424b1c5e86ee_1 (timeout after 300 s); newspaper_e3842a5681ef54c62a58804adec06c3f_1 (timeout after 300 s); newspaper_e567840b2e327602422573ccdc1c4275_1 (timeout after 300 s); newspaper_e6083de4647ef28434cb6a598b073ae4_1 (timeout after 300 s); newspaper_e62730aaeb9b509119e0c3699ac18201_1 (timeout after 300 s); newspaper_e6ddb0246224fb8bd8788e6cc7839021_1 (timeout after 300 s); newspaper_e7246d706077d2064a6e667dfc73925e_1 (timeout after 300 s); newspaper_e81b9b3561d4d4e865ff6713782fd432_1 (timeout after 300 s); newspaper_eb569707cf5621d4c71d5898216cdb17_1 (timeout after 300 s); newspaper_ef5c785d9cc21ccf6b73d143f231b5c5_1 (timeout after 300 s); newspaper_f1de032fb6a25cf85c85c15cb2d2a63a_1 (timeout after 300 s); newspaper_f36d00fe3544ae72725aac9dc7f19aa8_1 (timeout after 300 s); newspaper_fe2c8b45b2a086cd75984640bb3080e1_1 (timeout after 300 s) |

## Documents a scorer did not score as usual

| Tool | Benchmark | What the scorer did | Documents |
| --- | --- | --- | --- |
| inkgrid | OmniDocBench | text matched the simple way after 30 s | newspaper_0b1bb8d03b4287eb95f67b68c2cf9f92_1 |
| pymupdf4llm | OmniDocBench | text matched the simple way after 30 s | newspaper_0b1bb8d03b4287eb95f67b68c2cf9f92_1 |
| docling | OmniDocBench | text matched the simple way after 30 s | newspaper_0b1bb8d03b4287eb95f67b68c2cf9f92_1 |
| docling-ocr | OmniDocBench | text matched the simple way after 30 s | newspaper_0b1bb8d03b4287eb95f67b68c2cf9f92_1 |

## Documents left out

<details><summary>olmOCR-bench: 144 left out</summary>

- No text (125): headers_footers/008086eec0621732163bc07b8aca9fe02e6954af_page_2_processed.pdf, headers_footers/060c2cf840811e4f998ff25f6dae1ab7309fb8b4_page_9_processed.pdf, headers_footers/08404c3b520de340f0b0ed583d2083324c5cbfda_page_10_processed.pdf, headers_footers/11253d83d886378909f8b24d24d8a90412099087_page_4.pdf, headers_footers/1218c2e64afa8cbdcb4880220c7abb6540d38e51_page_3_processed.pdf, headers_footers/13352c55af54b88818a6381e4523a3d0a2b70e0d_page_15_processed.pdf, headers_footers/148c79ae1507bf2a6ee7c11c91559ac6aa2f0556_page_9_processed.pdf, headers_footers/189286dda42dcb3619192d715273a2a5d8ff213f_page_29.pdf, headers_footers/275579590090bf114f27e3f7ce3939cece9a7b25_page_1.pdf, headers_footers/2b0abd9d5f0a599e7a70ae1180fc2eeafe5653bc_page_4.pdf, headers_footers/30bf26b6243e63ec6a2e0531e01a079ba86a026a_page_38.pdf, headers_footers/385c01ed177acfac97735d31b168e8f795cac3e3_page_9.pdf, headers_footers/3e59698077f4a2e70afc371359842898894baf06_page_11.pdf, headers_footers/3f4659b0291c5acbd144111c14668eab984b5ae4_page_1.pdf, headers_footers/451431d13066daad9f4ba592952451dd07f542d9_page_1.pdf, headers_footers/5b419ca6365ed67292e9c4f5a46d733efce69b75_page_1.pdf, headers_footers/62989d7ee556e5ef4919dd5b3f925535c5f9f108_page_12.pdf, headers_footers/7b3ad57e2874674ad6f4aa71c9be495e65dcf449_page_2.pdf, headers_footers/8063d40c50199f37405b48fbc93af2386abe6d09_page_1.pdf, headers_footers/8dcbce41908541abaf65e574b852b0e89445f75f_page_13.pdf, headers_footers/957b896300cbee7e2535a6513f84f09c78a982fe_page_8.pdf, headers_footers/ad08db17adb365b1e5c3954776a45f57f61c24e2_page_7.pdf, headers_footers/c655ed75d1f645f3ddc601f992a7d99c845a5e6f_page_8.pdf, headers_footers/c863e36ed1e5fd97f3330d84a7a25ca034fe20dc_page_1.pdf, headers_footers/d8b9c4cd0ba9b036e09168c8dccccd1d43315ef4_page_1.pdf, headers_footers/f9f5429bf57bd9040fb42fb73dd3cdb1941d90e5_page_5.pdf, long_tiny_text/10a_pg1.pdf, long_tiny_text/10b_pg1.pdf, long_tiny_text/10c_pg1.pdf, long_tiny_text/11_pg145_pg1.pdf, long_tiny_text/11_pg146_pg1.pdf, long_tiny_text/11_pg161_pg1.pdf, long_tiny_text/11_pg186_pg1.pdf, long_tiny_text/11_pg252_pg1.pdf, long_tiny_text/11_pg36_pg1.pdf, long_tiny_text/11_pg375_pg1.pdf, long_tiny_text/11_pg377_pg1.pdf, long_tiny_text/11_pg418_pg1.pdf, long_tiny_text/11_pg421_pg1.pdf, long_tiny_text/11_pg57_pg1.pdf, long_tiny_text/13_pg162_pg1.pdf, long_tiny_text/13_pg165_pg1.pdf, long_tiny_text/13_pg32_pg1.pdf, long_tiny_text/13_pg475_pg1.pdf, long_tiny_text/13_pg501_pg1.pdf, long_tiny_text/13_pg531_pg1.pdf, long_tiny_text/13_pg556_pg1.pdf, long_tiny_text/13_pg566_pg1.pdf, long_tiny_text/13_pg639_pg1.pdf, long_tiny_text/13_pg67_pg1.pdf, long_tiny_text/13_pg811_pg1.pdf, long_tiny_text/13_pg857_pg1.pdf, long_tiny_text/14a_pg1.pdf, long_tiny_text/14b_pg1.pdf, long_tiny_text/14c_pg1.pdf, long_tiny_text/14d_pg1.pdf, long_tiny_text/14e_pg1.pdf, long_tiny_text/15a_pg1.pdf, long_tiny_text/15b_pg1.pdf, long_tiny_text/15c_pg1.pdf, long_tiny_text/15d_pg1.pdf, long_tiny_text/15e_pg1.pdf, long_tiny_text/16a_pg1.pdf, long_tiny_text/16b_pg1.pdf, long_tiny_text/16c_pg1.pdf, long_tiny_text/17_pg17_pg1.pdf, long_tiny_text/17_pg24_pg1.pdf, long_tiny_text/17_pg2_pg1.pdf, long_tiny_text/17_pg33_pg1.pdf, long_tiny_text/17_pg34_pg1.pdf, long_tiny_text/17_pg4_pg1.pdf, long_tiny_text/17_pg86_pg1.pdf, multi_column/0097571b436308f563a5808d45d0232255a2_page_4_pg1.pdf, multi_column/0097571b436308f563a5808d45d0232255a2_page_6_pg1.pdf, multi_column/0097571b436308f563a5808d45d0232255a2_page_7_pg1.pdf, multi_column/00d8a44d3066bbc4bd8df149d0dafb96f423_page_1_pg1.pdf, multi_column/00d8a44d3066bbc4bd8df149d0dafb96f423_page_3_pg1.pdf, multi_column/01119fb525785eb7153ee600241ff1e01959_page_2_pg1.pdf, multi_column/0208fbb5d6b646f972f4702428ad2cede5c5_page_2_pg1.pdf, multi_column/0208fbb5d6b646f972f4702428ad2cede5c5_page_3_pg1.pdf, multi_column/0208fbb5d6b646f972f4702428ad2cede5c5_page_6_pg1.pdf, multi_column/0208fbb5d6b646f972f4702428ad2cede5c5_page_8_pg1.pdf, multi_column/02a3e23da54b82c414d272051b0b5d8f44d8_page_12_pg1.pdf, multi_column/02a3e23da54b82c414d272051b0b5d8f44d8_page_14_pg1.pdf, multi_column/02a3e23da54b82c414d272051b0b5d8f44d8_page_16_pg1.pdf, multi_column/02a3e23da54b82c414d272051b0b5d8f44d8_page_17_pg1.pdf, multi_column/02a3e23da54b82c414d272051b0b5d8f44d8_page_3_pg1.pdf, multi_column/02e31046996b59b4997b8413f09ae163ade5_page_10_pg1.pdf, multi_column/02e31046996b59b4997b8413f09ae163ade5_page_2_pg1.pdf, multi_column/02e31046996b59b4997b8413f09ae163ade5_page_5_pg1.pdf, multi_column/0353b31c0381513a685be1878f8fad7d01d6_page_5_pg1.pdf, multi_column/04e88521bffcae275b79ed2c89e24c1f8855_page_1_pg1.pdf, multi_column/04e88521bffcae275b79ed2c89e24c1f8855_page_2_pg1.pdf, multi_column/06125479b00df48e91fe2fb616292d14116d_page_4_pg1.pdf, multi_column/065d792cf3923fc76a17183cfd13480cd51d_page_1_pg1.pdf, multi_column/065d792cf3923fc76a17183cfd13480cd51d_page_8_pg1.pdf, multi_column/065d792cf3923fc76a17183cfd13480cd51d_page_9_pg1.pdf, multi_column/069577d83be73a2373200ada5599eb824c95_page_2_pg1.pdf, multi_column/07c14b471fd33c56b988cc7a58dae211d16f_page_13_pg1.pdf, multi_column/07c14b471fd33c56b988cc7a58dae211d16f_page_14_pg1.pdf, multi_column/07c14b471fd33c56b988cc7a58dae211d16f_page_9_pg1.pdf, multi_column/0b2e551bbc33b030f810311118e2088d7ae3_page_12_pg1.pdf, multi_column/0b2e551bbc33b030f810311118e2088d7ae3_page_9_pg1.pdf, multi_column/0cf93d937e0f519965d4ff67daec8dd5dea1_page_5_pg1.pdf, multi_column/0d7f2cbc54e1b8e58b42a867c3f7620bcd29_page_6_pg1.pdf, multi_column/0d7f2cbc54e1b8e58b42a867c3f7620bcd29_page_8_pg1.pdf, tables/008d1dbe3c5a5fd2bac6e4f29acc45e711aa_pg8_pg1.pdf, tables/0684e33bd901b116725b6a0e0d21398f7315_pg4_pg1.pdf, tables/11e12a3ddca3b1743f6ec1c22a52cdbf9ffe_pg8_pg1.pdf, tables/2d0e0586cd437f8741b3e8280d2f5e43fcbc_pg373.pdf, tables/2e5fbee1a02ad5dde299c81b1c11c16ad8c9_pg5.pdf, tables/30c92c35171cd45479bd3083dbf574b31c9a_pg44.pdf, tables/35a3f1c2f69f57fe3ca6da3ef2a1a2f59812_pg53.pdf, tables/426df27cf990a3426b9e0731ad346f28184f_pg9.pdf, tables/4db371aebdbbfa28531a816f9bf26ed0a028_pg52_pg1.pdf, tables/533600ba1ea641b726c0942b913f18529719_pg20_pg1.pdf, tables/6130975d8b7c4f5bf39f0afa041776f8e07f_pg11.pdf, tables/77895f72f448c6110497d01cdc5bbc18a143_pg1.pdf, tables/7b9b73157809310ba970693297b7b998ee1c_pg19.pdf, tables/8097792c7266cdd2875e30cdf31ddcde348b_pg1.pdf, tables/9e6a5b213e4fd5906842ebe6b0c5538e9e7b_pg12.pdf, tables/d896f9ae5405c8d6b147ae9c9c20a0abb6c4_pg4_pg1.pdf, tables/df96e707adf064658b570d4cf4b6f98b4890_pg6_pg1.pdf, tables/f2ad0cd06b93fce98f2f354699cfc7b0a8df_pg1_pg1.pdf, tables/fcb362aa304b7b0bedec37f6c74f8ce3751a_pg2.pdf
- Image-backed (14): headers_footers/04085752de6b0603b2021d4cacd8c178fc9bfc28_page_1_processed.pdf, headers_footers/0722235b45282fd9c4b9d92efc9dbf6e9704d798_page_2_processed.pdf, headers_footers/39e0e582e2aeb751d615308c4486e5d9422a37db_page_2.pdf, headers_footers/47fdbae48c015f00edee32f742d9f1b3e4a43a22_page_32.pdf, headers_footers/b329b8083ee2abe62999617011b888e980924905_page_3.pdf, headers_footers/d660c61fbcb505d9f6e8ae38f435bed6822bd23b_page_12.pdf, headers_footers/fe8c6edb71bea08b67e7f8cdca813a0bbba04e6e_page_3.pdf, multi_column/081875a1035e34dee439b9a2a3a55e319405_page_47_pg1.pdf, multi_column/0d7f2cbc54e1b8e58b42a867c3f7620bcd29_page_9_pg1.pdf, tables/5fd60eb18fec22bca5781bf1df90d601f0c6_pg15_pg1.pdf, tables/6d48ac024cd71f0899fed96626b2b175c909_pg9.pdf, tables/b773892dc3e755672b9e085e9eeb8ad18690_pg1_pg1.pdf, tables/bfbadac12e1f83721b97b9787c5613fb4665_pg1_pg1.pdf, tables/f1774abde9c6d1cae0f05bb2c6992e9cca85_pg4.pdf
- OCR layer (5): headers_footers/4b91e05fb0fe865391f0f25c41a83c9c5fd37c08_page_1.pdf, headers_footers/e7f89d27e9cc33c4e86d92c27cc578a95a323b24_page_1.pdf, multi_column/0208fbb5d6b646f972f4702428ad2cede5c5_page_1_pg1.pdf, tables/0091c5b23fe54b3a7cbe5b0b8c26057b7d70_pg3_pg1.pdf, tables/26076dc369efd78b3087643cc7153509bd18_pg3_pg1.pdf

</details>

<details><summary>OmniDocBench: 361 left out</summary>

- No text (264): docstructbench_llm-raw-scihub-o.O-bf00151572.pdf_3, docstructbench_llm-raw-scihub-o.O-bf00326833.pdf_3, docstructbench_llm-raw-scihub-o.O-s001280000131.pdf_5, docstructbench_llm-raw-scihub-o.O-s0362-546x%2897%2900070-9.pdf_7, eastmoney_f72b162baf25f1a2060e4ce877071ec27e490ab16e9de1a2b18572b596d2bde8.pdf_2, jiaocai_f32828acecb4282c87eaa554d2e1db74e418cd6845843012463a3324028bdd9d.pdf_9, jiaocaineedrop_2005_QP.pdf_5, jiaocaineedrop_5f9c4ab08cac7457e9111a30e4664920607ea2c115a1433d7be98e97e64244ca.pdf_2, jiaocaineedrop_624b60c58c9d8bfb6ff1886c2fd605d2adeb6ea4da576068201b6c6958ce93f4.pdf_8, jiaocaineedrop_bde81e42743067b574946698491d7f19.pdf_14, jiaocaineedrop_jiaocai_needrop_en_101, jiaocaineedrop_jiaocai_needrop_en_108, jiaocaineedrop_jiaocai_needrop_en_1118, jiaocaineedrop_jiaocai_needrop_en_1141, jiaocaineedrop_jiaocai_needrop_en_1175, jiaocaineedrop_jiaocai_needrop_en_1249, jiaocaineedrop_jiaocai_needrop_en_1253, jiaocaineedrop_jiaocai_needrop_en_1276, jiaocaineedrop_jiaocai_needrop_en_1290, jiaocaineedrop_jiaocai_needrop_en_13, jiaocaineedrop_jiaocai_needrop_en_1308, jiaocaineedrop_jiaocai_needrop_en_1344, jiaocaineedrop_jiaocai_needrop_en_1349, jiaocaineedrop_jiaocai_needrop_en_1358, jiaocaineedrop_jiaocai_needrop_en_1363, jiaocaineedrop_jiaocai_needrop_en_1381, jiaocaineedrop_jiaocai_needrop_en_1408, jiaocaineedrop_jiaocai_needrop_en_1449, jiaocaineedrop_jiaocai_needrop_en_1458, jiaocaineedrop_jiaocai_needrop_en_1478, jiaocaineedrop_jiaocai_needrop_en_1509, jiaocaineedrop_jiaocai_needrop_en_1523, jiaocaineedrop_jiaocai_needrop_en_1539, jiaocaineedrop_jiaocai_needrop_en_1544, jiaocaineedrop_jiaocai_needrop_en_155, jiaocaineedrop_jiaocai_needrop_en_1564, jiaocaineedrop_jiaocai_needrop_en_16, jiaocaineedrop_jiaocai_needrop_en_1608, jiaocaineedrop_jiaocai_needrop_en_1719, jiaocaineedrop_jiaocai_needrop_en_1751, jiaocaineedrop_jiaocai_needrop_en_1776, jiaocaineedrop_jiaocai_needrop_en_1836, jiaocaineedrop_jiaocai_needrop_en_188, jiaocaineedrop_jiaocai_needrop_en_1898, jiaocaineedrop_jiaocai_needrop_en_194, jiaocaineedrop_jiaocai_needrop_en_1959, jiaocaineedrop_jiaocai_needrop_en_1972, jiaocaineedrop_jiaocai_needrop_en_2036, jiaocaineedrop_jiaocai_needrop_en_206, jiaocaineedrop_jiaocai_needrop_en_2124, jiaocaineedrop_jiaocai_needrop_en_2198, jiaocaineedrop_jiaocai_needrop_en_2211, jiaocaineedrop_jiaocai_needrop_en_2263, jiaocaineedrop_jiaocai_needrop_en_2272, jiaocaineedrop_jiaocai_needrop_en_2360, jiaocaineedrop_jiaocai_needrop_en_237, jiaocaineedrop_jiaocai_needrop_en_2374, jiaocaineedrop_jiaocai_needrop_en_2399, jiaocaineedrop_jiaocai_needrop_en_2444, jiaocaineedrop_jiaocai_needrop_en_250, jiaocaineedrop_jiaocai_needrop_en_2509, jiaocaineedrop_jiaocai_needrop_en_2518, jiaocaineedrop_jiaocai_needrop_en_2604, jiaocaineedrop_jiaocai_needrop_en_2623, jiaocaineedrop_jiaocai_needrop_en_2652, jiaocaineedrop_jiaocai_needrop_en_2732, jiaocaineedrop_jiaocai_needrop_en_276, jiaocaineedrop_jiaocai_needrop_en_2825, jiaocaineedrop_jiaocai_needrop_en_2839, jiaocaineedrop_jiaocai_needrop_en_2893, jiaocaineedrop_jiaocai_needrop_en_2901, jiaocaineedrop_jiaocai_needrop_en_3009, jiaocaineedrop_jiaocai_needrop_en_3173, jiaocaineedrop_jiaocai_needrop_en_3222, jiaocaineedrop_jiaocai_needrop_en_3274, jiaocaineedrop_jiaocai_needrop_en_3303, jiaocaineedrop_jiaocai_needrop_en_3313, jiaocaineedrop_jiaocai_needrop_en_3341, jiaocaineedrop_jiaocai_needrop_en_3361, jiaocaineedrop_jiaocai_needrop_en_3428, jiaocaineedrop_jiaocai_needrop_en_3458, jiaocaineedrop_jiaocai_needrop_en_349, jiaocaineedrop_jiaocai_needrop_en_3713, jiaocaineedrop_jiaocai_needrop_en_3738, jiaocaineedrop_jiaocai_needrop_en_3747, jiaocaineedrop_jiaocai_needrop_en_3751, jiaocaineedrop_jiaocai_needrop_en_377, jiaocaineedrop_jiaocai_needrop_en_383, jiaocaineedrop_jiaocai_needrop_en_3937, jiaocaineedrop_jiaocai_needrop_en_3984, jiaocaineedrop_jiaocai_needrop_en_4065, jiaocaineedrop_jiaocai_needrop_en_439, jiaocaineedrop_jiaocai_needrop_en_443, jiaocaineedrop_jiaocai_needrop_en_467, jiaocaineedrop_jiaocai_needrop_en_482, jiaocaineedrop_jiaocai_needrop_en_546, jiaocaineedrop_jiaocai_needrop_en_574, jiaocaineedrop_jiaocai_needrop_en_601, jiaocaineedrop_jiaocai_needrop_en_620, jiaocaineedrop_jiaocai_needrop_en_625, jiaocaineedrop_jiaocai_needrop_en_678, jiaocaineedrop_jiaocai_needrop_en_693, jiaocaineedrop_jiaocai_needrop_en_715, jiaocaineedrop_jiaocai_needrop_en_769, jiaocaineedrop_jiaocai_needrop_en_809, jiaocaineedrop_jiaocai_needrop_en_835, jiaocaineedrop_jiaocai_needrop_en_85, jiaocaineedrop_jiaocai_needrop_en_854, jiaocaineedrop_jiaocai_needrop_en_887, jiaocaineedrop_jiaocai_needrop_en_909, jiaocaineedrop_jiaocai_needrop_en_913, jiaocaineedrop_jiaocai_needrop_en_922, jiaocaineedrop_jiaocai_needrop_en_942, jiaocaineedrop_jiaocai_needrop_en_952, jiaocaineedrop_jiaocai_needrop_en_961, jiaocaineedrop_jiaocai_needrop_en_980, jiaocaineedrop_jiaocai_needrop_en_999, notes_1ba14cb325bc448f7201b20502ecf2b5_10, notes_1ba14cb325bc448f7201b20502ecf2b5_100, notes_1ba14cb325bc448f7201b20502ecf2b5_101, notes_1ba14cb325bc448f7201b20502ecf2b5_102, notes_1ba14cb325bc448f7201b20502ecf2b5_103, notes_1ba14cb325bc448f7201b20502ecf2b5_104, notes_1ba14cb325bc448f7201b20502ecf2b5_11, notes_1ba14cb325bc448f7201b20502ecf2b5_118, notes_1ba14cb325bc448f7201b20502ecf2b5_119, notes_1ba14cb325bc448f7201b20502ecf2b5_12, notes_1ba14cb325bc448f7201b20502ecf2b5_120, notes_1ba14cb325bc448f7201b20502ecf2b5_121, notes_1ba14cb325bc448f7201b20502ecf2b5_122, notes_1ba14cb325bc448f7201b20502ecf2b5_123, notes_1ba14cb325bc448f7201b20502ecf2b5_124, notes_1ba14cb325bc448f7201b20502ecf2b5_125, notes_1ba14cb325bc448f7201b20502ecf2b5_126, notes_1ba14cb325bc448f7201b20502ecf2b5_13, notes_1ba14cb325bc448f7201b20502ecf2b5_14, notes_1ba14cb325bc448f7201b20502ecf2b5_15, notes_1ba14cb325bc448f7201b20502ecf2b5_16, notes_1ba14cb325bc448f7201b20502ecf2b5_30, notes_1ba14cb325bc448f7201b20502ecf2b5_31, notes_1ba14cb325bc448f7201b20502ecf2b5_32, notes_1ba14cb325bc448f7201b20502ecf2b5_33, notes_1ba14cb325bc448f7201b20502ecf2b5_34, notes_1ba14cb325bc448f7201b20502ecf2b5_35, notes_1ba14cb325bc448f7201b20502ecf2b5_36, notes_1ba14cb325bc448f7201b20502ecf2b5_37, notes_1ba14cb325bc448f7201b20502ecf2b5_38, notes_1ba14cb325bc448f7201b20502ecf2b5_52, notes_1ba14cb325bc448f7201b20502ecf2b5_53, notes_1ba14cb325bc448f7201b20502ecf2b5_54, notes_1ba14cb325bc448f7201b20502ecf2b5_55, notes_1ba14cb325bc448f7201b20502ecf2b5_56, notes_1ba14cb325bc448f7201b20502ecf2b5_57, notes_1ba14cb325bc448f7201b20502ecf2b5_58, notes_1ba14cb325bc448f7201b20502ecf2b5_59, notes_1ba14cb325bc448f7201b20502ecf2b5_60, notes_1ba14cb325bc448f7201b20502ecf2b5_74, notes_1ba14cb325bc448f7201b20502ecf2b5_75, notes_1ba14cb325bc448f7201b20502ecf2b5_76, notes_1ba14cb325bc448f7201b20502ecf2b5_77, notes_1ba14cb325bc448f7201b20502ecf2b5_78, notes_1ba14cb325bc448f7201b20502ecf2b5_79, notes_1ba14cb325bc448f7201b20502ecf2b5_8, notes_1ba14cb325bc448f7201b20502ecf2b5_80, notes_1ba14cb325bc448f7201b20502ecf2b5_81, notes_1ba14cb325bc448f7201b20502ecf2b5_82, notes_1ba14cb325bc448f7201b20502ecf2b5_9, notes_1ba14cb325bc448f7201b20502ecf2b5_96, notes_1ba14cb325bc448f7201b20502ecf2b5_97, notes_1ba14cb325bc448f7201b20502ecf2b5_98, notes_1ba14cb325bc448f7201b20502ecf2b5_99, notes_9e951846094758afac08c620144e3a76_10, notes_9e951846094758afac08c620144e3a76_11, notes_9e951846094758afac08c620144e3a76_12, notes_9e951846094758afac08c620144e3a76_13, notes_9e951846094758afac08c620144e3a76_14, notes_9e951846094758afac08c620144e3a76_15, notes_9e951846094758afac08c620144e3a76_16, notes_9e951846094758afac08c620144e3a76_17, notes_9e951846094758afac08c620144e3a76_9, notes_f7f010b78016aeebd76e56d9283eb67f_111, notes_f7f010b78016aeebd76e56d9283eb67f_112, notes_f7f010b78016aeebd76e56d9283eb67f_113, notes_f7f010b78016aeebd76e56d9283eb67f_114, notes_f7f010b78016aeebd76e56d9283eb67f_115, notes_f7f010b78016aeebd76e56d9283eb67f_116, notes_f7f010b78016aeebd76e56d9283eb67f_117, notes_f7f010b78016aeebd76e56d9283eb67f_118, notes_f7f010b78016aeebd76e56d9283eb67f_119, notes_f7f010b78016aeebd76e56d9283eb67f_2, notes_f7f010b78016aeebd76e56d9283eb67f_23, notes_f7f010b78016aeebd76e56d9283eb67f_24, notes_f7f010b78016aeebd76e56d9283eb67f_25, notes_f7f010b78016aeebd76e56d9283eb67f_26, notes_f7f010b78016aeebd76e56d9283eb67f_27, notes_f7f010b78016aeebd76e56d9283eb67f_28, notes_f7f010b78016aeebd76e56d9283eb67f_29, notes_f7f010b78016aeebd76e56d9283eb67f_3, notes_f7f010b78016aeebd76e56d9283eb67f_30, notes_f7f010b78016aeebd76e56d9283eb67f_31, notes_f7f010b78016aeebd76e56d9283eb67f_4, notes_f7f010b78016aeebd76e56d9283eb67f_45, notes_f7f010b78016aeebd76e56d9283eb67f_46, notes_f7f010b78016aeebd76e56d9283eb67f_47, notes_f7f010b78016aeebd76e56d9283eb67f_48, notes_f7f010b78016aeebd76e56d9283eb67f_49, notes_f7f010b78016aeebd76e56d9283eb67f_5, notes_f7f010b78016aeebd76e56d9283eb67f_50, notes_f7f010b78016aeebd76e56d9283eb67f_51, notes_f7f010b78016aeebd76e56d9283eb67f_52, notes_f7f010b78016aeebd76e56d9283eb67f_53, notes_f7f010b78016aeebd76e56d9283eb67f_6, notes_f7f010b78016aeebd76e56d9283eb67f_67, notes_f7f010b78016aeebd76e56d9283eb67f_68, notes_f7f010b78016aeebd76e56d9283eb67f_69, notes_f7f010b78016aeebd76e56d9283eb67f_7, notes_f7f010b78016aeebd76e56d9283eb67f_70, notes_f7f010b78016aeebd76e56d9283eb67f_71, notes_f7f010b78016aeebd76e56d9283eb67f_72, notes_f7f010b78016aeebd76e56d9283eb67f_73, notes_f7f010b78016aeebd76e56d9283eb67f_74, notes_f7f010b78016aeebd76e56d9283eb67f_75, notes_f7f010b78016aeebd76e56d9283eb67f_8, notes_f7f010b78016aeebd76e56d9283eb67f_89, notes_f7f010b78016aeebd76e56d9283eb67f_9, notes_f7f010b78016aeebd76e56d9283eb67f_90, notes_f7f010b78016aeebd76e56d9283eb67f_91, notes_f7f010b78016aeebd76e56d9283eb67f_92, notes_f7f010b78016aeebd76e56d9283eb67f_93, notes_f7f010b78016aeebd76e56d9283eb67f_94, notes_f7f010b78016aeebd76e56d9283eb67f_95, notes_f7f010b78016aeebd76e56d9283eb67f_96, notes_f7f010b78016aeebd76e56d9283eb67f_97, yanbaopptmerge_11eeaa31ab6171a9d1ea55aeb0b167e51bffeaa8a83a97cb5e2c3fb7963bf1bf.pdf_7, yanbaopptmerge_e3b48594d5a2a6dc86b51244737f24867a0c1781e9f0e4fb52d96bbc6f9d95c7.pdf_3, yanbaopptmerge_m3_Unit_1_Where_did_you_go.pdf_5, yanbaopptmerge_yanbaoPPT_1015, yanbaopptmerge_yanbaoPPT_1220, yanbaopptmerge_yanbaoPPT_1235, yanbaopptmerge_yanbaoPPT_150, yanbaopptmerge_yanbaoPPT_1625, yanbaopptmerge_yanbaoPPT_1685, yanbaopptmerge_yanbaoPPT_1735, yanbaopptmerge_yanbaoPPT_2845, yanbaopptmerge_yanbaoPPT_4150, yanbaopptmerge_yanbaoPPT_4245, yanbaopptmerge_yanbaoPPT_4330, yanbaopptmerge_yanbaoPPT_4710, yanbaopptmerge_yanbaoPPT_495, yanbaopptmerge_yanbaoPPT_520, yanbaopptmerge_yanbaoPPT_5300, yanbaopptmerge_yanbaoPPT_5305, yanbaopptmerge_yanbaoPPT_5345, yanbaopptmerge_yanbaoPPT_5620, yanbaopptmerge_yanbaoPPT_5885, yanbaopptmerge_yanbaoPPT_5940, yanbaopptmerge_yanbaoPPT_620, yanbaopptmerge_yanbaoPPT_745, yanbaopptmerge_yanbaoPPT_750, yanbaopptmerge_yanbaoPPT_770, yanbaopptmerge_yanbaoPPT_90, yanbaor2_yanbaoPPT_2098, yanbaor2_yanbaoPPT_2432, yanbaor2_yanbaoPPT_5877
- Image-backed (97): docstructbench_dianzishu_zhongwenzaixian-o.O-63677793.pdf_332, docstructbench_dianzishu_zhongwenzaixian-o.O-63710614.pdf_149, docstructbench_llm-raw-the-eye-o.O-Something%27s%20Cooking.pdf_4, eastmoney_59cde7e939acc3124df9d3f2c85b5a0ec41b9da1157d5be38e098672022b47cb.pdf_11, eastmoney_d09a006aa02ddc09299bbb9a1b5efa0d77408191f0c1ff1fca8c80bd6150f806.pdf_17, jiaocai_jiaocai_en_595, jiaocaineedrop_eng_gls.pdf_6, jiaocaineedrop_jiaocai_needrop_en_1496, jiaocaineedrop_jiaocai_needrop_en_1669, jiaocaineedrop_jiaocai_needrop_en_2193, jiaocaineedrop_jiaocai_needrop_en_3375, jiaocaineedrop_jiaocai_needrop_en_541, yanbaopptmerge_SE05.pdf_7, yanbaopptmerge_SE14.pdf_1, yanbaopptmerge_SE17.pdf_10, yanbaopptmerge_SE20.pdf_2, yanbaopptmerge_yanbaoPPT_1020, yanbaopptmerge_yanbaoPPT_1120, yanbaopptmerge_yanbaoPPT_120, yanbaopptmerge_yanbaoPPT_1375, yanbaopptmerge_yanbaoPPT_145, yanbaopptmerge_yanbaoPPT_1465, yanbaopptmerge_yanbaoPPT_1475, yanbaopptmerge_yanbaoPPT_1615, yanbaopptmerge_yanbaoPPT_1695, yanbaopptmerge_yanbaoPPT_1710, yanbaopptmerge_yanbaoPPT_1745, yanbaopptmerge_yanbaoPPT_1810, yanbaopptmerge_yanbaoPPT_1820, yanbaopptmerge_yanbaoPPT_1835, yanbaopptmerge_yanbaoPPT_2400, yanbaopptmerge_yanbaoPPT_2460, yanbaopptmerge_yanbaoPPT_2545, yanbaopptmerge_yanbaoPPT_2825, yanbaopptmerge_yanbaoPPT_3125, yanbaopptmerge_yanbaoPPT_3150, yanbaopptmerge_yanbaoPPT_3215, yanbaopptmerge_yanbaoPPT_3290, yanbaopptmerge_yanbaoPPT_3930, yanbaopptmerge_yanbaoPPT_4000, yanbaopptmerge_yanbaoPPT_4010, yanbaopptmerge_yanbaoPPT_4020, yanbaopptmerge_yanbaoPPT_4050, yanbaopptmerge_yanbaoPPT_4095, yanbaopptmerge_yanbaoPPT_4125, yanbaopptmerge_yanbaoPPT_4185, yanbaopptmerge_yanbaoPPT_4285, yanbaopptmerge_yanbaoPPT_4380, yanbaopptmerge_yanbaoPPT_455, yanbaopptmerge_yanbaoPPT_4565, yanbaopptmerge_yanbaoPPT_4570, yanbaopptmerge_yanbaoPPT_4615, yanbaopptmerge_yanbaoPPT_4630, yanbaopptmerge_yanbaoPPT_4635, yanbaopptmerge_yanbaoPPT_4660, yanbaopptmerge_yanbaoPPT_4750, yanbaopptmerge_yanbaoPPT_4770, yanbaopptmerge_yanbaoPPT_4820, yanbaopptmerge_yanbaoPPT_485, yanbaopptmerge_yanbaoPPT_4900, yanbaopptmerge_yanbaoPPT_4975, yanbaopptmerge_yanbaoPPT_5070, yanbaopptmerge_yanbaoPPT_5175, yanbaopptmerge_yanbaoPPT_5205, yanbaopptmerge_yanbaoPPT_5245, yanbaopptmerge_yanbaoPPT_5350, yanbaopptmerge_yanbaoPPT_5435, yanbaopptmerge_yanbaoPPT_5540, yanbaopptmerge_yanbaoPPT_5555, yanbaopptmerge_yanbaoPPT_5560, yanbaopptmerge_yanbaoPPT_5675, yanbaopptmerge_yanbaoPPT_5685, yanbaopptmerge_yanbaoPPT_5930, yanbaopptmerge_yanbaoPPT_5945, yanbaopptmerge_yanbaoPPT_5980, yanbaopptmerge_yanbaoPPT_6025, yanbaopptmerge_yanbaoPPT_6070, yanbaopptmerge_yanbaoPPT_6170, yanbaopptmerge_yanbaoPPT_685, yanbaopptmerge_yanbaoPPT_70, yanbaopptmerge_yanbaoPPT_725, yanbaopptmerge_yanbaoPPT_805, yanbaopptmerge_yanbaoPPT_820, yanbaopptmerge_yanbaoPPT_870, yanbaopptmerge_yanbaoPPT_935, yanbaopptmerge_yanbaoPPT_985, yanbaor2_1cb2b2a2c6e3a1157a6f2876205bbeaa4d3958d0482e9cdc88dd2c002ed1ffc1.pdf_61, yanbaor2_323ab38d3b3b9a44837779e3c7b4a2f7088d9e0eb6c966d4d596faf6c01011a6.pdf_2, yanbaor2_a6b1184da1f8167144544b92fff11726f5218e5ca106c86dc00436c14725d7b9.pdf_5, yanbaor2_bc193526614fd5857f7b5254e67bced76222cf3396b01e516303b92609a20075.pdf_14, yanbaor2_bedda45af71c9703274cf8b2c62a772e6be615c355d2b255d9408b1b40b606de.pdf_3, yanbaor2_d2326887a8905dfa7f5745e04a3a526735a59d741feac1923a0c0926e48ed691.pdf_130, yanbaor2_d599e33e54376640020110ac1733ccdde8c6323d5d5f0c3ca8cb395dc6e46cf5.pdf_7, yanbaor2_ey-political-guidelines-next-commission.pdf_14, yanbaor2_yanbaoPPT_1760, yanbaor2_yanbaoPPT_5846, yanbaor2_yanbaoPPT_916

</details>

<details><summary>ParseBench: 190 left out</summary>

- No text (159): table/2023-conocophillips-aim-presentation (1)_page7, table/BSC-Hospital-List-by-County (2)_page1, table/Layout with Boxes and text_page1, table/SERFF_CA_random_pages 1_page2600, table/SERFF_CA_random_pages 1_page275, table/SERFF_CA_random_pages 1_page748, table/SERFF_TX_random_pages 1_page298, text/text_dense__baoutou, text/text_dense__japanese, text/text_handwritting__address, text/text_handwritting__contract, text/text_handwritting__decla, text/text_handwritting__degraded, text/text_handwritting__handwritting, text/text_handwritting__impossible, text/text_handwritting__jp, text/text_handwritting__list, text/text_handwritting__manualunderline, text/text_handwritting__math, text/text_handwritting__math2, text/text_handwritting__signatures, text/text_misc__censored, text/text_misc__colorprofile, text/text_misc__marks, text/text_misc__missing, text/text_misc__redacted, text/text_misc__redacted3, text/text_misc__skew3, text/text_multicolumns__2pages, text/text_multicolumns__3colsbeluga, text/text_multicolumns__4colimg, text/text_multicolumns__document_001, text/text_multicolumns__ethbottens, text/text_multicolumns__heirloom, text/text_multicolumns__hydro, text/text_multicolumns__paperchem, text/text_multilang__cnnm, text/text_multilang__enfr, text/text_multilang__german2, text/text_multilang__japanese, text/text_multilang__mandarin3, text/text_multilang__russian3, text/text_ocr__ blockoftext, text/text_ocr__012-25, text/text_ocr__069, text/text_ocr__1182_Xerox Scan003, text/text_ocr__162774-266456-358050-153368146-663163649, text/text_ocr__2pages, text/text_ocr__3rd, text/text_ocr__9, text/text_ocr__File0021, text/text_ocr__File_002-Lembar-Pernyataan-Keaslian-Tugas-Akhir, text/text_ocr__MS201File81, text/text_ocr__RdZJGPSwfucvMonBwC15855594373897, text/text_ocr__abstract, text/text_ocr__adm, text/text_ocr__admnh, text/text_ocr__archive, text/text_ocr__article, text/text_ocr__article1col, text/text_ocr__attendence, text/text_ocr__blurry, text/text_ocr__blurry2, text/text_ocr__bold, text/text_ocr__bolditalix, text/text_ocr__canada, text/text_ocr__cert_of_assistanvce, text/text_ocr__christmass, text/text_ocr__clearmont, text/text_ocr__code, text/text_ocr__contract, text/text_ocr__contrast, text/text_ocr__convenzione, text/text_ocr__cramer, text/text_ocr__cyber, text/text_ocr__das, text/text_ocr__data, text/text_ocr__dhaka, text/text_ocr__diesel, text/text_ocr__diseeas, text/text_ocr__document-001, text/text_ocr__eller, text/text_ocr__email, text/text_ocr__energy, text/text_ocr__ens, text/text_ocr__eu, text/text_ocr__fpl, text/text_ocr__ger, text/text_ocr__german, text/text_ocr__glitch, text/text_ocr__glitch2, text/text_ocr__ikea, text/text_ocr__inr, text/text_ocr__italian, text/text_ocr__italian2, text/text_ocr__klein, text/text_ocr__letter, text/text_ocr__letter2, text/text_ocr__letterhead, text/text_ocr__link, text/text_ocr__lowq, text/text_ocr__mag, text/text_ocr__mix, text/text_ocr__mutlilang, text/text_ocr__newspaperonecol, text/text_ocr__ord-4000, text/text_ocr__orientedtex, text/text_ocr__p4013, text/text_ocr__paperpenline, text/text_ocr__parent, text/text_ocr__phd, text/text_ocr__plow, text/text_ocr__plowlist, text/text_ocr__pol, text/text_ocr__polish, text/text_ocr__polishlike, text/text_ocr__postit, text/text_ocr__pretest, text/text_ocr__protest, text/text_ocr__redacted, text/text_ocr__redacted2, text/text_ocr__rep, text/text_ocr__roosvelt, text/text_ocr__routier, text/text_ocr__russina2, text/text_ocr__scanbook, text/text_ocr__scaninfile, text/text_ocr__secretaria, text/text_ocr__sharon, text/text_ocr__simple, text/text_ocr__simpleletter, text/text_ocr__skew, text/text_ocr__skew2, text/text_ocr__skew3, text/text_ocr__skewGazette, text/text_ocr__skewc, text/text_ocr__sup, text/text_ocr__tata, text/text_ocr__tridimensional, text/text_ocr__ups, text/text_ocr__wnd, text/text_ocr__wooby, text/text_ocr__yellowtype, text/text_ocr__zaposlitve, text/text_simple__adhoc, text/text_simple__censored, text/text_simple__grayson, text/text_simple__landfill, text/text_simple__letter3, text/text_simple__mvab, text/text_simple__myctophidae, text/text_simple__protoskol, text/text_simple__templated, text/text_sparse__agenda, text/text_sparse__cover, text/text_sparse__cover2, text/text_sparse__guide, text/text_sparse__note, text/text_sparse__notes
- Image-backed (22): table/SERFF_TX_random_pages 1_page1293, text/text_misc__012-headline-certificate-fluidpower-group-uk-limited, text/text_misc__lightblue, text/text_misc__yellow, text/text_multicolumns__coorp, text/text_multicolumns__tableOfContent8col, text/text_multilang__arabic, text/text_multilang__discrimination, text/text_multilang__khazak, text/text_ocr__Declination-to-Proceed-Before-a-U.S.-Magistrate-Judge, text/text_ocr__Just-Security-Carroll-v-Trump-Memo-endorsement-of-Carroll-reponse-accepting-Trump-motion-approve-supersedeas-bond-91630000-stay-execution-judgment-pending-appeal-March-11-2024, text/text_ocr__courtSignature, text/text_ocr__doubletext, text/text_ocr__guyana, text/text_ocr__paper8col, text/text_ocr__ref, text/text_ocr__sigpae, text/text_ocr__underline, text/text_simple__1colmit.test, text/text_simple__baoutocert, text/text_simple__concession, text/text_sparse__mcdo
- OCR layer (1): text/text_ocr__strikeout
- Born-digital, in a group not scored (8): text/text_handwritting__filling (text_handwritting), text/text_ocr__arabic (text_ocr), text/text_ocr__bg (text_ocr), text/text_ocr__kr (text_ocr), text/text_ocr__mariage (text_ocr), text/text_ocr__nato (text_ocr), text/text_ocr__santacruz (text_ocr), text/text_ocr__skewmac (text_ocr)

</details>

<details><summary>DP-Bench: 4 left out</summary>

- No text (1): 01030000000141
- Image-backed (3): 01030000000198, 01030000000199, 01030000000200

</details>
