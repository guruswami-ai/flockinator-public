<!-- TEMPLATE (not a result). Contributor-drafted via Meta API (muse-spark-1.3-contributor), supervisor-reviewed. Fill only from a scored device journal. -->

# Panel-policy canary — results record

# Canary results record — <FILL:GATE_AND_DATE>
- **Gate:** <FILL:GATE_A_OR_B>
- **Activity:** Compare host-twin reference log vs panel-device log for the panel policy (SEARCH / DOUBLE_CHECK / WAIT)
- **Contract:** docs/experiments/canary-contract-v1.md (v1.1)
- **Scorer command:** <FILL:EXACT_COMMAND_LINE>

## File Checksums
| file | role | sha256 checksum |
|---|---|---|
| <FILL:REFERENCE_FILENAME> | laptop reference | <FILL:REFERENCE_SHA256> |
| <FILL:BOARD_FILENAME_1> | display board | <FILL:BOARD_SHA256_1> |
| <FILL:BOARD_FILENAME_2> | display board | <FILL:BOARD_SHA256_2> |

## Comparison Results
| run id | lines compared | exact matches | missing lines | result |
|---|---|---|---|---|
| <FILL:RUN_ID_1> | <FILL:LINES_COMPARED_1> | <FILL:EXACT_MATCHES_1> | <FILL:MISSING_LINES_1> | <FILL:RESULT_1> |
| <FILL:RUN_ID_2> | <FILL:LINES_COMPARED_2> | <FILL:EXACT_MATCHES_2> | <FILL:MISSING_LINES_2> | <FILL:RESULT_2> |
| <FILL:RUN_ID_3> | <FILL:LINES_COMPARED_3> | <FILL:EXACT_MATCHES_3> | <FILL:MISSING_LINES_3> | <FILL:RESULT_3> |

## Runs That Did Not Match — Honest Report
<FILL:SUMMARY_OF_NON_MATCHES_OR_STATE_NONE_FOUND>

- **Run id:** <FILL:NON_MATCH_RUN_ID>
- **Difference seen:** <FILL:DIFFERENCE_DESCRIPTION>
- **Suspected cause:** <FILL:SUSPECTED_CAUSE_OR_UNKNOWN>
- **Retest / action:** <FILL:RETEST_ACTION>

## What This Activity Does Not Prove
- <FILL:NOT_PROVEN_1>
- <FILL:NOT_PROVEN_2>
- <FILL:NOT_PROVEN_3>

## Commands Used to Compare Logs
```sh
sha256sum <FILL:REFERENCE_LOG> <FILL:BOARD_LOG>
diff -u <FILL:REFERENCE_LOG> <FILL:BOARD_LOG> > <FILL:DIFF_OUTPUT_FILE>
wc -l <FILL:REFERENCE_LOG> <FILL:BOARD_LOG>
```
