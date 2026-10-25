# Derived data dictionary

CSVs use UTF-8, comma separators, empty unavailable values and True/False flags. IDs are CFBD identifiers. Rates are fractions unless suffixed `_pp` (percentage points).

| File | Grain | Important fields |
|---|---|---|
| team_game_metrics.csv | Team-game | eligible_plays, ppa_n, ppa_coverage, mean_ppa, ppa_sd; home_indicator=+1 home/-1 away/0 neutral; local_date in America/Chicago |
| case_results.csv | Intervention | main_eligible requires four post games; new_alarm is first combined alarm within first four post games; preexisting_alarm is before change; adjusted_delta is post-window mean minus baseline; CI omitted below four post games |
| control_chart_points.csv | Case-game | adjusted_ppa, z, center/sigma/lcl/ucl; we1-we4; two CUSUMs; MR/limits; primary_window and post_change |
| baseline_points.csv | Case-baseline-game | Focal observations excluded from model training; baseline WECO flags |
| placebo_results.csv | Fake-change unit | Matched case, team-season, fake first post date and identical classification; 50 rows |
| sensitivity.csv | Case-variant | raw, sample_sd, cusum_h4, cusum_h6, min40 |
| team_game_drives.csv | Team-game | Valid drives/snaps/possession seconds/points; starting yards-to-goal; tempo and points/drive |
| team_season_metrics.csv | Team-season | Sum-based ratios, observed rank/group and sparse clean interval summaries |
| bottlenecks.csv | Team-season-state | Snap/conversion counts; rate, leave-team-out FBS comparator, gap_pp, display_eligible |
| bottleneck_cohorts.csv | Season-state-group | Pooled top-10/middle/bottom-50 counts and rates |
| quality_audit.csv | Season-exclusion-type | First exclusion reason, counts and missing PPA |
| games_missing_plays.csv | Missing expected game | Empty in this run |
| data_audit.json | Run | Coverage/reconciliation and drive exclusions |
| study_summary.json | Run | Case/placebo counts, Wilson interval, seed |
| tempo_model.json/.txt | Model | Slope, clustered interval, N and model summary |
| input_manifest.json | Cached API call | Endpoint, parameters, byte count and SHA-256; no raw rows/credentials |
| runtime_versions.json | Environment | Python and library versions |

- **points_per_drive:** 6 for explicit offensive TDs and 3 for made field goals per valid drive; no conversions. Defensive return TDs earn the offense zero.
- **plays_per_minute:** 60 × eligible snaps / summed elapsed drive clock; denominator includes administrative/special-teams clock. Not real-time tempo.
- **clean_seconds_per_snap:** consecutive eligible same-team/drive/period intervals after an explicitly tackled run/completed pass, excluding first-down/out-of-bounds/scoring wording. Sparse, nonrepresentative subset.
- **conversion:** first down by yards gained or offensive TD on this snap; turnover outcomes forced to failure. Distance 1-3/4-6/7-10/11+; yards-to-goal <=20 red zone, 21-50 opponent half, >50 own half.
- **adjusted_ppa:** PPA minus prior-season fitted defense/home contributions. Case models have different intercept references; compare changes or z-scores across cases, not absolute adjusted levels.
- **cusum_delay_games:** first crossing index minus first affected game index. Negative means before change; blank means no crossing. Alarm date is not an estimated causal onset date.
- **first_alarm_index:** zero-based target-series position. Chart game_index is one-based.
- **mr_ucl:** 3.267 × prior mean consecutive moving range. Target MR does not bridge seasons.

Raw responses and intermediate per-drive rows stay private. Tableau CSVs reshape only derived aggregates.
