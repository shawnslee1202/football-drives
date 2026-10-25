# Tableau workbook

The packaged workbook includes three native Hyper extracts and aggregate CSVs. It was opened and visually inspected in Tableau Public 2026.3 on October 23, 2026. The tempo scatter renders 394 team-season marks, the bottleneck heatmap displays conversion gaps, and the control chart includes the coaching-change line. Selecting Texas A&M 2023 was verified to update the control chart. Evidence and workbook hash: `NATIVE_REVIEW.json`.

Open `football-drives.twbx`. Maximize Tableau to see the 1300 × 850 dashboard. The left case selector controls the control chart; the right selector controls the heatmap. Choose one case, not All. Some state headings truncate; hover the marks for full details. Heatmap values are percentage-point gaps versus other FBS teams; negative values are worse and cells below 20 snaps are omitted. Control-chart blue is adjusted PPA in baseline standard deviations, with center zero, limits ±3, and a red intervention marker at -0.5; zero on the x axis is the first affected game. This is retrospective and noncausal.

## Rebuild and extract provenance

`make_tableau.py` builds the workbook from derived tables and packaged native extracts. `Data/extract_manifest.json` binds each extract to its source CSV hash. If source data change, refresh extracts before packaging; the generator deliberately rejects stale extracts.

To refresh without the Hyper API, open each generated CSV in Tableau Public, enter a worksheet to trigger native extraction, and save the temporary workbook locally. Its extract connections identify the generated Hyper files. Copy the matching files into Data and regenerate the source/extract hash manifest after verifying the table counts. The original native imports had 394 tempo rows, 3,645 bottleneck rows and 468 control rows. A Hyper API startup attempt failed in this execution environment; native Tableau import succeeded.

Data provided by CollegeFootballData.com. Only aggregates are included. API keys and raw API records are excluded.
