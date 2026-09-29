# inkgrid benchmark: the M5b baseline

Measured on 2026-09-29 at commit `b33b3cb` by `bench/inkgrid_bench/run.py`, under the pre-registered protocol of `docs/specs/12-benchmark.md`. **inkgrid's numbers are its baseline**: its reading as of M4, before any fix for the reading errors found on these documents (DR-0023); the one change since, from M5a, stops a crash on a Camelot table with no cells. Later runs are labelled as tuned on these documents.

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
| inkgrid | 0.907 [0.860, 0.948] | 0.890 [0.826, 0.945] | 0.898 [0.850, 0.939] | 0.792 [0.669, 0.917] | 0.766 [0.640, 0.903] |
| pdfplumber | 0.899 [0.825, 0.958] | 0.714 [0.611, 0.812] | 0.796 [0.721, 0.861] | 0.813 [0.654, 0.953] | 0.419 [0.258, 0.653] |
| pymupdf | 0.932 [0.881, 0.975] | 0.782 [0.681, 0.873] | 0.850 [0.784, 0.906] | 0.919 [0.845, 0.974] | 0.463 [0.288, 0.710] |
| camelot | 0.931 [0.872, 0.978] | 0.749 [0.645, 0.845] | 0.830 [0.755, 0.893] | 0.914 [0.823, 0.982] | 0.456 [0.283, 0.702] |

| Difference | Regions P | Regions R | Regions F | Regions P (pooled) | Regions R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.009 [-0.055, +0.078] | +0.176 [+0.093, +0.263] * | +0.103 [+0.049, +0.163] * | -0.021 [-0.193, +0.164] | +0.347 [+0.190, +0.485] * |
| inkgrid - pymupdf | -0.025 [-0.080, +0.031] | +0.108 [+0.036, +0.186] * | +0.048 [+0.005, +0.097] * | -0.127 [-0.253, +0.005] | +0.303 [+0.134, +0.449] * |
| inkgrid - camelot | -0.024 [-0.072, +0.024] | +0.141 [+0.064, +0.227] * | +0.068 [+0.018, +0.129] * | -0.123 [-0.250, +0.007] | +0.309 [+0.143, +0.454] * |

Check, the ICDAR ground truth read as a tool:

| Tool | Regions P | Regions R | Regions F | Regions P (pooled) | Regions R (pooled) |
| --- | --- | --- | --- | --- | --- |
| ground-truth | 0.992 [0.977, 1.000] | 0.968 [0.925, 1.000] | 0.980 [0.954, 1.000] | 0.986 [0.952, 1.000] | 0.845 [0.628, 1.000] |

### Soric et al.'s protocol

| Tool | F1-bbox | F1-GriTS-Top | F1-GriTS-Con | F1-TEDS |
| --- | --- | --- | --- | --- |
| inkgrid | 0.744 [0.572, 0.905] | 0.688 [0.523, 0.847] | 0.629 [0.471, 0.783] | 0.612 [0.455, 0.767] |
| pdfplumber | 0.635 [0.510, 0.748] | 0.499 [0.373, 0.619] | 0.450 [0.324, 0.573] | 0.416 [0.287, 0.545] |
| pymupdf | 0.781 [0.667, 0.872] | 0.617 [0.494, 0.722] | 0.557 [0.427, 0.670] | 0.519 [0.384, 0.639] |
| camelot | 0.776 [0.659, 0.870] | 0.702 [0.576, 0.803] | 0.637 [0.509, 0.745] | 0.624 [0.494, 0.735] |

| Difference | F1-bbox | F1-GriTS-Top | F1-GriTS-Con | F1-TEDS |
| --- | --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.109 [-0.050, +0.278] | +0.189 [+0.036, +0.356] * | +0.179 [+0.036, +0.334] * | +0.196 [+0.051, +0.352] * |
| inkgrid - pymupdf | -0.037 [-0.183, +0.116] | +0.071 [-0.074, +0.231] | +0.071 [-0.064, +0.221] | +0.093 [-0.045, +0.246] |
| inkgrid - camelot | -0.032 [-0.178, +0.126] | -0.014 [-0.152, +0.136] | -0.008 [-0.136, +0.133] | -0.012 [-0.136, +0.128] |

Check, the ICDAR ground truth read as a tool:

| Tool | F1-bbox | F1-GriTS-Top | F1-GriTS-Con | F1-TEDS |
| --- | --- | --- | --- | --- |
| ground-truth | 0.938 [0.860, 1.000] | 0.926 [0.846, 0.987] | 0.893 [0.811, 0.960] | 0.890 [0.807, 0.957] |

### Speed

| Tool | Seconds per page |
| --- | --- |
| inkgrid | 0.343 [0.301, 0.390] |
| pdfplumber | 0.082 [0.073, 0.093] |
| pymupdf | 0.075 [0.066, 0.085] |
| camelot | 0.285 [0.269, 0.300] |

| Difference | Seconds per page |
| --- | --- |
| inkgrid - pdfplumber | +0.261 [+0.224, +0.303] * |
| inkgrid - pymupdf | +0.267 [+0.229, +0.311] * |
| inkgrid - camelot | +0.058 [+0.017, +0.101] * |

Check, the ICDAR ground truth read as a tool:

| Tool | Seconds per page |
| --- | --- |
| ground-truth | 0.005 [0.004, 0.005] |

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
| inkgrid | 0.873 [0.820, 0.921] | 0.892 [0.821, 0.953] | 0.882 [0.830, 0.929] | 0.920 [0.870, 0.956] | 0.924 [0.846, 0.978] |
| pdfplumber | 0.783 [0.673, 0.883] | 0.585 [0.467, 0.699] | 0.670 [0.571, 0.755] | 0.435 [0.275, 0.714] | 0.457 [0.304, 0.636] |
| pymupdf | 0.870 [0.775, 0.947] | 0.599 [0.477, 0.717] | 0.709 [0.603, 0.800] | 0.907 [0.799, 0.975] | 0.485 [0.321, 0.668] |
| camelot | 0.940 [0.881, 0.983] | 0.664 [0.543, 0.785] | 0.778 [0.686, 0.857] | 0.882 [0.699, 0.990] | 0.700 [0.527, 0.850] |

| Difference | Regions P | Regions R | Regions F | Regions P (pooled) | Regions R (pooled) |
| --- | --- | --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.090 [-0.003, +0.192] | +0.307 [+0.200, +0.417] * | +0.213 [+0.134, +0.302] * | +0.485 [+0.213, +0.633] * | +0.467 [+0.287, +0.624] * |
| inkgrid - pymupdf | +0.003 [-0.089, +0.104] | +0.294 [+0.178, +0.411] * | +0.173 [+0.089, +0.271] * | +0.013 [-0.067, +0.118] | +0.439 [+0.258, +0.605] * |
| inkgrid - camelot | -0.067 [-0.125, -0.013] * | +0.228 [+0.132, +0.332] * | +0.104 [+0.042, +0.181] * | +0.038 [-0.079, +0.200] | +0.224 [+0.095, +0.383] * |

Check, the ICDAR ground truth read as a tool:

| Tool | Regions P | Regions R | Regions F | Regions P (pooled) | Regions R (pooled) |
| --- | --- | --- | --- | --- | --- |
| ground-truth | 1.000 [1.000, 1.000] | 0.971 [0.928, 1.000] | 0.985 [0.963, 1.000] | 1.000 [1.000, 1.000] | 0.977 [0.944, 0.999] |

### Binding (the access paths)

| Tool | Bound | Leaf-bound | Value recall |
| --- | --- | --- | --- |
| inkgrid | 0.309 [0.188, 0.469] | 0.351 [0.217, 0.527] | 0.563 [0.385, 0.750] |
| pdfplumber | 0.172 [0.093, 0.280] | 0.175 [0.095, 0.284] | 0.292 [0.173, 0.451] |
| pymupdf | 0.239 [0.135, 0.382] | 0.245 [0.139, 0.390] | 0.301 [0.177, 0.464] |
| camelot | 0.251 [0.142, 0.393] | 0.258 [0.147, 0.404] | 0.301 [0.176, 0.467] |

| Difference | Bound | Leaf-bound | Value recall |
| --- | --- | --- | --- |
| inkgrid - pdfplumber | +0.137 [+0.044, +0.260] * | +0.176 [+0.066, +0.318] * | +0.271 [+0.101, +0.457] * |
| inkgrid - pymupdf | +0.070 [+0.014, +0.147] * | +0.107 [+0.025, +0.222] * | +0.262 [+0.092, +0.448] * |
| inkgrid - camelot | +0.058 [+0.012, +0.120] * | +0.093 [+0.020, +0.201] * | +0.262 [+0.094, +0.450] * |

Check, the ICDAR ground truth read as a tool:

| Tool | Bound | Leaf-bound | Value recall |
| --- | --- | --- | --- |
| ground-truth | 0.868 [0.764, 0.944] | 0.925 [0.856, 0.971] | 0.982 [0.949, 1.000] |

### Speed

| Tool | Seconds per page |
| --- | --- |
| inkgrid | 0.392 [0.342, 0.448] |
| pdfplumber | 0.105 [0.084, 0.136] |
| pymupdf | 0.076 [0.066, 0.088] |
| camelot | 0.321 [0.310, 0.335] |

| Difference | Seconds per page |
| --- | --- |
| inkgrid - pdfplumber | +0.287 [+0.246, +0.333] * |
| inkgrid - pymupdf | +0.316 [+0.269, +0.366] * |
| inkgrid - camelot | +0.070 [+0.025, +0.119] * |

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
| inkgrid | 0.549 [0.482, 0.616] |
| pdfplumber | 0.138 [0.111, 0.173] |
| pymupdf | 0.104 [0.091, 0.119] |
| camelot | 0.375 [0.351, 0.399] |

| Difference | Seconds per page |
| --- | --- |
| inkgrid - pdfplumber | +0.411 [+0.351, +0.472] * |
| inkgrid - pymupdf | +0.445 [+0.384, +0.506] * |
| inkgrid - camelot | +0.175 [+0.116, +0.234] * |

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
