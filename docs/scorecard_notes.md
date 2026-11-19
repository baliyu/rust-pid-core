# Scorecard notes

Predictions are scored from the pasted output of each run. A prediction whose check never ran is left out of docs/scorecard.csv.

Left out so far:

- BY, BZ, CA, CB (step 16): the first Feather build failed at the linker, so the image checks never ran. They were re-predicted as CE, CF, CG, CH after the fix.
- CN (step 18) and CU (step 20): the LED prediction needs a flash, and none happened in those runs. CZ (step 21) is the scored version.
