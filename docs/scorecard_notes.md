# Scorecard notes

Predictions are scored from the pasted output of each run. A prediction whose check never ran is left out of docs/scorecard.csv.

Left out so far:

- BY, BZ, CA, CB (step 16): the first Feather build failed at the linker, so the image checks never ran. They were re-predicted as CE, CF, CG, CH after the fix.
- CN (step 18) and CU (step 20): the LED prediction needs a flash, and none happened in those runs. CZ (step 21) is the scored version.
- DB to DF (step 22): all scored as hits when the step ran, but their wording was lost when the working session was compacted, so they are not in the CSV. No miss is involved.
- DM to DR (step 24): the serial read opened no port because Windows could not start the USB device, so no line, rows or cycles arrived over USB. They were re-predicted as EL to ER for the flash route.
- Scoring corrections: DS, DW and DZ (under 50 percent, event did not happen) are hits, and EF (40 percent, event happened) is a miss. They were first announced the wrong way round in the working chat and corrected before being recorded here.

Steps 37 to 41: the first push attempt (FM) stopped at the guard because a remote already existed with the wrong username (baliy instead of baliyu), probably set in an earlier session. FN and FO were predicted again for the second attempt. The calibration figure legend overlapped the n labels and was fixed in step 41.

Steps 42 to 46: the CI workflow was added and pushed. The first run (ci#1, commit 351d31a) completed successfully. GM was predicted at 45 percent and happened, so it is a miss. The workflow has run once, so one green run is all that is claimed.
