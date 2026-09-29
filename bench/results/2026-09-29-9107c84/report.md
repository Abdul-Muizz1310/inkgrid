# inkgrid benchmark: the M5b baseline

Measured on 2026-09-29 at commit `9107c84` by `bench/inkgrid_bench/run.py`, under the pre-registered protocol of `docs/specs/12-benchmark.md`. **inkgrid's numbers are its baseline**: its reading before any fix for errors found on these documents (DR-0023); later runs are labelled as tuned on them.

Each cell is the point estimate and its 95% interval from 10,000 resamples of documents (seed 20260928). A difference marked `*` has an interval that excludes 0; only those are findings. `ground-truth` is the ICDAR ground truth read as a tool: a check on the pipeline and on each metric's ceiling, not a competitor.

## ICDAR-2013 competition (67 documents)

### Structure (the competition's DAR)

| Tool | Structure P | Structure R | Structure F | Structure P (pooled) | Structure R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid | 0.821 [0.756, 0.881] | 0.738 [0.646, 0.827] | 0.777 [0.700, 0.850] | 0.794 [0.652, 0.921] | 0.627 [0.475, 0.769] |
| pdfplumber | 0.691 [0.596, 0.782] | 0.516 [0.413, 0.620] | 0.591 [0.493, 0.683] | 0.822 [0.718, 0.893] | 0.234 [0.115, 0.425] |
| pymupdf | 0.697 [0.600, 0.785] | 0.544 [0.437, 0.646] | 0.611 [0.512, 0.702] | 0.829 [0.732, 0.895] | 0.244 [0.122, 0.443] |
| camelot | 0.744 [0.645, 0.839] | 0.556 [0.444, 0.666] | 0.637 [0.531, 0.735] | 0.934 [0.876, 0.965] | 0.254 [0.127, 0.461] |

| Difference | Structure P | Structure R | Structure F | Structure P (pooled) | Structure R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.130 [+0.056, +0.207] * | +0.222 [+0.147, +0.303] * | +0.186 [+0.122, +0.256] * | -0.028 [-0.166, +0.123] | +0.393 [+0.203, +0.552] * |
| inkgrid - pymupdf | +0.124 [+0.051, +0.202] * | +0.194 [+0.124, +0.273] * | +0.166 [+0.105, +0.235] * | -0.035 [-0.173, +0.112] | +0.384 [+0.189, +0.544] * |
| inkgrid - camelot | +0.077 [+0.006, +0.154] * | +0.182 [+0.108, +0.266] * | +0.141 [+0.078, +0.214] * | -0.141 [-0.272, -0.010] * | +0.374 [+0.175, +0.536] * |

Check, the ICDAR ground truth read as a tool:

| Tool | Structure P | Structure R | Structure F | Structure P (pooled) | Structure R (pooled) |
| --- | --- | --- | --- | --- | --- |
| ground-truth | 0.993 [0.978, 1.000] | 0.977 [0.939, 1.000] | 0.985 [0.961, 1.000] | 0.989 [0.962, 1.000] | 0.832 [0.580, 1.000] |

### Regions

| Tool | Regions P | Regions R | Regions F | Regions P (pooled) | Regions R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid | 0.896 [0.844, 0.942] | 0.877 [0.809, 0.937] | 0.887 [0.832, 0.932] | 0.781 [0.657, 0.906] | 0.749 [0.624, 0.886] |
| pdfplumber | 0.884 [0.807, 0.950] | 0.701 [0.597, 0.800] | 0.782 [0.704, 0.850] | 0.792 [0.634, 0.934] | 0.401 [0.245, 0.624] |
| pymupdf | 0.918 [0.861, 0.967] | 0.769 [0.668, 0.862] | 0.837 [0.766, 0.897] | 0.900 [0.817, 0.964] | 0.445 [0.277, 0.686] |
| camelot | 0.917 [0.852, 0.969] | 0.736 [0.631, 0.834] | 0.816 [0.737, 0.883] | 0.895 [0.800, 0.971] | 0.439 [0.272, 0.678] |

| Difference | Regions P | Regions R | Regions F | Regions P (pooled) | Regions R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.012 [-0.050, +0.081] | +0.176 [+0.094, +0.263] * | +0.105 [+0.050, +0.165] * | -0.011 [-0.182, +0.173] | +0.347 [+0.191, +0.485] * |
| inkgrid - pymupdf | -0.022 [-0.076, +0.034] | +0.108 [+0.036, +0.186] * | +0.050 [+0.006, +0.099] * | -0.119 [-0.244, +0.013] | +0.303 [+0.134, +0.449] * |
| inkgrid - camelot | -0.021 [-0.068, +0.027] | +0.141 [+0.063, +0.227] * | +0.070 [+0.019, +0.131] * | -0.114 [-0.240, +0.015] | +0.309 [+0.143, +0.454] * |

Check, the ICDAR ground truth read as a tool:

| Tool | Regions P | Regions R | Regions F | Regions P (pooled) | Regions R (pooled) |
| --- | --- | --- | --- | --- | --- |
| ground-truth | 0.992 [0.977, 1.000] | 0.968 [0.925, 1.000] | 0.980 [0.954, 1.000] | 0.986 [0.952, 1.000] | 0.845 [0.628, 1.000] |

### Soric et al.'s protocol

| Tool | F1-bbox | F1-GriTS-Top | F1-GriTS-Con | F1-TEDS |
| --- | --- | --- | --- | --- |
| inkgrid | 0.722 [0.550, 0.891] | 0.669 [0.504, 0.833] | 0.615 [0.456, 0.775] | 0.598 [0.439, 0.759] |
| pdfplumber | 0.610 [0.482, 0.727] | 0.477 [0.353, 0.598] | 0.434 [0.309, 0.562] | 0.399 [0.274, 0.531] |
| pymupdf | 0.753 [0.635, 0.853] | 0.592 [0.467, 0.704] | 0.539 [0.407, 0.657] | 0.501 [0.364, 0.625] |
| camelot | 0.746 [0.623, 0.850] | 0.676 [0.547, 0.784] | 0.618 [0.486, 0.733] | 0.604 [0.470, 0.722] |

| Difference | F1-bbox | F1-GriTS-Top | F1-GriTS-Con | F1-TEDS |
| --- | --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.113 [-0.043, +0.279] | +0.192 [+0.042, +0.356] * | +0.181 [+0.041, +0.334] * | +0.199 [+0.057, +0.352] * |
| inkgrid - pymupdf | -0.030 [-0.172, +0.119] | +0.077 [-0.065, +0.234] | +0.076 [-0.056, +0.223] | +0.097 [-0.037, +0.248] |
| inkgrid - camelot | -0.024 [-0.167, +0.130] | -0.007 [-0.141, +0.141] | -0.003 [-0.129, +0.136] | -0.006 [-0.129, +0.131] |

Check, the ICDAR ground truth read as a tool:

| Tool | F1-bbox | F1-GriTS-Top | F1-GriTS-Con | F1-TEDS |
| --- | --- | --- | --- | --- |
| ground-truth | 0.938 [0.860, 1.000] | 0.926 [0.846, 0.987] | 0.893 [0.811, 0.960] | 0.890 [0.807, 0.957] |

### Speed

| Tool | Seconds per page |
| --- | --- |
| inkgrid | 0.308 [0.271, 0.350] |
| pdfplumber | 0.074 [0.066, 0.085] |
| pymupdf | 0.068 [0.060, 0.077] |
| camelot | 0.263 [0.249, 0.277] |

| Difference | Seconds per page |
| --- | --- |
| inkgrid - pdfplumber | +0.234 [+0.200, +0.272] * |
| inkgrid - pymupdf | +0.240 [+0.205, +0.280] * |
| inkgrid - camelot | +0.045 [+0.007, +0.085] * |

Check, the ICDAR ground truth read as a tool:

| Tool | Seconds per page |
| --- | --- |
| ground-truth | 0.004 [0.004, 0.005] |

## ICDAR-2013 practice (58 documents)

### Structure (the competition's DAR)

| Tool | Structure P | Structure R | Structure F | Structure P (pooled) | Structure R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid | 0.704 [0.619, 0.787] | 0.628 [0.520, 0.734] | 0.664 [0.569, 0.756] | 0.831 [0.738, 0.897] | 0.546 [0.385, 0.716] |
| pdfplumber | 0.580 [0.465, 0.695] | 0.329 [0.230, 0.438] | 0.420 [0.314, 0.527] | 0.772 [0.680, 0.850] | 0.237 [0.144, 0.362] |
| pymupdf | 0.603 [0.486, 0.716] | 0.368 [0.262, 0.480] | 0.457 [0.346, 0.568] | 0.799 [0.704, 0.876] | 0.272 [0.161, 0.417] |
| camelot | 0.684 [0.577, 0.789] | 0.393 [0.280, 0.511] | 0.499 [0.381, 0.611] | 0.848 [0.767, 0.908] | 0.294 [0.179, 0.443] |

| Difference | Structure P | Structure R | Structure F | Structure P (pooled) | Structure R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.124 [+0.013, +0.237] * | +0.299 [+0.199, +0.401] * | +0.244 [+0.148, +0.344] * | +0.059 [-0.045, +0.155] | +0.309 [+0.161, +0.476] * |
| inkgrid - pymupdf | +0.101 [-0.008, +0.216] | +0.260 [+0.162, +0.363] * | +0.206 [+0.115, +0.306] * | +0.032 [-0.074, +0.133] | +0.274 [+0.124, +0.446] * |
| inkgrid - camelot | +0.020 [-0.042, +0.092] | +0.235 [+0.141, +0.339] * | +0.165 [+0.087, +0.257] * | -0.017 [-0.093, +0.059] | +0.252 [+0.103, +0.426] * |

Check, the ICDAR ground truth read as a tool:

| Tool | Structure P | Structure R | Structure F | Structure P (pooled) | Structure R (pooled) |
| --- | --- | --- | --- | --- | --- |
| ground-truth | 0.963 [0.929, 0.991] | 0.937 [0.886, 0.980] | 0.950 [0.911, 0.982] | 0.974 [0.944, 0.994] | 0.956 [0.914, 0.986] |

### Regions

| Tool | Regions P | Regions R | Regions F | Regions P (pooled) | Regions R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid | 0.864 [0.806, 0.915] | 0.873 [0.797, 0.938] | 0.868 [0.810, 0.918] | 0.916 [0.863, 0.953] | 0.905 [0.821, 0.964] |
| pdfplumber | 0.770 [0.660, 0.871] | 0.565 [0.452, 0.680] | 0.652 [0.555, 0.738] | 0.423 [0.265, 0.700] | 0.438 [0.289, 0.615] |
| pymupdf | 0.856 [0.760, 0.936] | 0.579 [0.459, 0.697] | 0.691 [0.585, 0.784] | 0.896 [0.783, 0.967] | 0.466 [0.307, 0.645] |
| camelot | 0.925 [0.862, 0.975] | 0.645 [0.524, 0.763] | 0.760 [0.666, 0.841] | 0.875 [0.689, 0.986] | 0.682 [0.508, 0.833] |

| Difference | Regions P | Regions R | Regions F | Regions P (pooled) | Regions R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.094 [+0.002, +0.195] * | +0.307 [+0.200, +0.417] * | +0.216 [+0.137, +0.306] * | +0.493 [+0.224, +0.638] * | +0.467 [+0.287, +0.624] * |
| inkgrid - pymupdf | +0.008 [-0.083, +0.108] | +0.294 [+0.178, +0.411] * | +0.177 [+0.093, +0.274] * | +0.020 [-0.060, +0.128] | +0.439 [+0.258, +0.605] * |
| inkgrid - camelot | -0.061 [-0.118, -0.007] * | +0.228 [+0.132, +0.332] * | +0.108 [+0.046, +0.187] * | +0.041 [-0.077, +0.203] | +0.224 [+0.095, +0.383] * |

Check, the ICDAR ground truth read as a tool:

| Tool | Regions P | Regions R | Regions F | Regions P (pooled) | Regions R (pooled) |
| --- | --- | --- | --- | --- | --- |
| ground-truth | 1.000 [1.000, 1.000] | 0.971 [0.928, 1.000] | 0.985 [0.963, 1.000] | 1.000 [1.000, 1.000] | 0.977 [0.944, 0.999] |

### Binding (the access paths)

| Tool | Bound | Leaf-bound | Value recall |
| --- | --- | --- | --- |
| inkgrid | 0.341 [0.212, 0.499] | 0.388 [0.247, 0.558] | 0.515 [0.351, 0.707] |
| pdfplumber | 0.191 [0.104, 0.303] | 0.194 [0.107, 0.307] | 0.324 [0.197, 0.479] |
| pymupdf | 0.265 [0.151, 0.409] | 0.271 [0.156, 0.417] | 0.332 [0.201, 0.493] |
| camelot | 0.278 [0.161, 0.419] | 0.286 [0.167, 0.433] | 0.333 [0.202, 0.494] |

| Difference | Bound | Leaf-bound | Value recall |
| --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.150 [+0.048, +0.281] * | +0.194 [+0.073, +0.340] * | +0.191 [+0.076, +0.339] * |
| inkgrid - pymupdf | +0.076 [+0.014, +0.158] * | +0.117 [+0.027, +0.235] * | +0.183 [+0.065, +0.330] * |
| inkgrid - camelot | +0.063 [+0.012, +0.129] * | +0.102 [+0.020, +0.216] * | +0.182 [+0.068, +0.326] * |

Check, the ICDAR ground truth read as a tool:

| Tool | Bound | Leaf-bound | Value recall |
| --- | --- | --- | --- |
| ground-truth | 0.854 [0.745, 0.937] | 0.916 [0.844, 0.968] | 0.980 [0.944, 1.000] |

### Speed

| Tool | Seconds per page |
| --- | --- |
| inkgrid | 0.363 [0.317, 0.415] |
| pdfplumber | 0.093 [0.074, 0.122] |
| pymupdf | 0.069 [0.060, 0.080] |
| camelot | 0.293 [0.283, 0.305] |

| Difference | Seconds per page |
| --- | --- |
| inkgrid - pdfplumber | +0.270 [+0.232, +0.313] * |
| inkgrid - pymupdf | +0.294 [+0.251, +0.341] * |
| inkgrid - camelot | +0.070 [+0.030, +0.114] * |

Check, the ICDAR ground truth read as a tool:

| Tool | Seconds per page |
| --- | --- |
| ground-truth | 0.004 [0.003, 0.005] |

## olmOCR-bench tables, all PDFs (188 documents)

### Table tests

| Tool | All tests | Heading tests | Neighbour tests |
| --- | --- | --- | --- |
| inkgrid | 0.481 [0.410, 0.552] | 0.429 [0.344, 0.514] | 0.504 [0.428, 0.579] |
| pdfplumber | 0.294 [0.231, 0.361] | 0.263 [0.191, 0.341] | 0.308 [0.239, 0.381] |
| pymupdf | 0.321 [0.256, 0.390] | 0.299 [0.223, 0.380] | 0.330 [0.258, 0.405] |
| camelot | 0.273 [0.213, 0.338] | 0.237 [0.169, 0.312] | 0.288 [0.223, 0.357] |

| Difference | All tests | Heading tests | Neighbour tests |
| --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.187 [+0.120, +0.254] * | +0.166 [+0.096, +0.240] * | +0.197 [+0.120, +0.273] * |
| inkgrid - pymupdf | +0.161 [+0.094, +0.227] * | +0.130 [+0.053, +0.208] * | +0.174 [+0.100, +0.250] * |
| inkgrid - camelot | +0.209 [+0.151, +0.270] * | +0.192 [+0.126, +0.261] * | +0.216 [+0.152, +0.286] * |

### Speed

| Tool | Seconds per page |
| --- | --- |
| inkgrid | 0.509 [0.447, 0.572] |
| pdfplumber | 0.121 [0.100, 0.149] |
| pymupdf | 0.092 [0.080, 0.105] |
| camelot | 0.347 [0.325, 0.370] |

| Difference | Seconds per page |
| --- | --- |
| inkgrid - pdfplumber | +0.388 [+0.332, +0.444] * |
| inkgrid - pymupdf | +0.417 [+0.359, +0.474] * |
| inkgrid - camelot | +0.163 [+0.108, +0.217] * |

## olmOCR-bench tables, PDFs with a text layer (173 documents)

### Table tests

| Tool | All tests | Heading tests | Neighbour tests |
| --- | --- | --- | --- |
| inkgrid | 0.525 [0.449, 0.598] | 0.463 [0.374, 0.552] | 0.551 [0.473, 0.628] |
| pdfplumber | 0.321 [0.252, 0.393] | 0.284 [0.207, 0.371] | 0.336 [0.264, 0.414] |
| pymupdf | 0.349 [0.278, 0.422] | 0.323 [0.240, 0.410] | 0.361 [0.285, 0.438] |
| camelot | 0.297 [0.230, 0.366] | 0.256 [0.182, 0.335] | 0.315 [0.244, 0.387] |

| Difference | All tests | Heading tests | Neighbour tests |
| --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.204 [+0.133, +0.276] * | +0.179 [+0.104, +0.260] * | +0.215 [+0.132, +0.296] * |
| inkgrid - pymupdf | +0.175 [+0.105, +0.247] * | +0.140 [+0.057, +0.225] * | +0.190 [+0.110, +0.271] * |
| inkgrid - camelot | +0.228 [+0.165, +0.292] * | +0.207 [+0.137, +0.280] * | +0.237 [+0.167, +0.308] * |

## Soric et al.'s released predictions, re-scored here

| Their predictions | F1-bbox here / theirs | F1-GriTS-Top here / theirs | F1-GriTS-Con here / theirs | F1-TEDS here / theirs | Largest gap |
| --- | --- | --- | --- | --- | --- |
| Camelot | 0.6643 / 0.6643 | 0.5645 / 0.5705 | 0.5050 / 0.5064 | 0.4931 / 0.4983 | 0.0060 |
| PyMuPDF | 0.7589 / 0.7589 | 0.5821 / 0.5877 | 0.5053 / 0.5134 | 0.4798 / 0.4898 | 0.0100 |
| pdfplumber | 0.6349 / 0.6349 | 0.4993 / 0.5042 | 0.4322 / 0.4291 | 0.4093 / 0.4098 | 0.0048 |
| Docling | 0.9904 / 0.9904 | 0.9708 / 0.9724 | 0.9089 / 0.8993 | 0.9062 / 0.8984 | 0.0096 |

Within 0.01 of their released results: 15 of 16 (largest gap 0.0100).

## Crashes and timeouts (each scored as no tables)

| Tool | Dataset | Documents |
| --- | --- | --- |
| ground-truth | competition | 1: us-018 (ValueError: could not convert string to float: '26ß') |

## inkgrid's verifier on these documents (spec 11 section 5)

| Dataset | Documents with defects | Defects by class |
| --- | --- | --- |
| competition | 12 | decode 6, doubled 20, hrule 1, invented 1, text 43, vrule 3 |
| practice | 6 | invented 12, lost 5, text 70, vrule 27 |
| olmocr | 16 | decode 6, doubled 30, invented 2, lost 45, text 44, unverified 1, value 2, vrule 5 |
