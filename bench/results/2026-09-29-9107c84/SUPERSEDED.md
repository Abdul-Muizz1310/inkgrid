# Superseded

This first scoring is kept as a record; its numbers are not the baseline. The final review found two
harness defects, both fixed test-first before the run was repeated in full:

- boxes on the five pages turned by `/Rotate` (competition eu-015; practice eu-014, eu-015, eu-018)
  went to the ICDAR jar's region mode and to Soric et al.'s evaluator in the unrotated frame, while
  their ground truth measures such a page as it displays;
- the practice set's access paths were misread in four files (eu-020 separates its fields with
  semicolons; us-007, us-008 and us-009 pad their table ids), so binding counted 5,053 checkable
  paths instead of 5,603.

The spec records both as dated amendments (`docs/specs/12-benchmark.md` sections 0, 3.2, 4.4). The
repeated run is `bench/results/latest.md`.
