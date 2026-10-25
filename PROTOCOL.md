# Analysis protocol, version 1

Recorded October 22, 2026, before computing the expanded ten-case study. This is a retrospective analysis plan, not a preregistration: the Texas A&M pilot has already been inspected. Cases were chosen by documented coaching-change dates and availability in 2022–2023, not by observed post-change efficiency. This is a convenience sample, not every coaching change in those years. Sources are in interventions.csv.

## Scope

Three seasons, 2021–2023. Use 2021 and 2022 as prior-season baselines for the 2022 and 2023 interventions respectively. FBS-vs-FBS regular-season games, regulation only. The source document permits scope adjustment; eleven seasons are not necessary to answer the selected question. Primary question is process change; tempo/bottlenecks are descriptive secondary outputs. Monte Carlo is optional and out of this implementation.

## Data and exclusions

Use seasonal CFBD FBS team IDs, game IDs and chronological timestamps. Normalize offensive/defensive names to the home/away game IDs; fail on unmapped names. Order plays by period, descending game clock, drive number and play number. Retain a reconciliation audit of joins, game coverage, unknown types, missing fields and missing PPA.

Exclude overtime, FCS games, kneels/spikes, penalties/no-play records, special teams and unknown offensive types. Garbage time is fourth-quarter absolute score margin >28, using the preceding observed score before filtering. Test scored plays near the cutoff. Score reconstruction may be affected by missing records and tied-clock ordering, a disclosed limitation. Do not impute missing PPA as zero. Require >=20 measured plays and >=90% PPA coverage for a chart game.

## Opponent adjustment

For each focal team-season, fit a weighted additive model on the previous season only: mean offensive PPA ~ offense fixed effects + defense fixed effects + home-field indicator. Weight by measured plays. EXCLUDE all focal team's offensive observations from this fit; these become an out-of-fit Phase I baseline. Subtract the fitted defense and home contributions from focal baseline and target games. No target-season outcomes train this model. Opponents unseen in training are excluded and counted. This avoids future-outcome leakage but assumes defensive strength persists across years. Compare unadjusted results as a sensitivity check. Prior-year defense adjustment is not a causal identification strategy.

## SPC and interpretation

At least eight prior-season games. Center = unweighted mean of adjusted per-game PPA. Sigma = mean consecutive moving range / 1.128. Include an MR chart with UCL=3.267*mean MR, LCL=0. Baseline WECO alarms are reported, never iteratively removed. A flagged Phase I is an unstable reference, and any target-season alarm is provisional.

Apply four Western Electric rules to standardized game averages: one point beyond 3 sigma; two of three beyond 2 sigma on the same side; four of five beyond 1 sigma on the same side; eight consecutive points on the same side. Do not apply these run rules to CUSUM values.

Run two-sided standardized CUSUM, k=0.5, h=5, from target-season game one without an intervention date. Record the FIRST threshold crossing and retain the accumulation thereafter. The alarm date is not an estimated change date. Compare with the first affected game afterward; report detection delay and whether the first alarm falls in the first affected game or within one eligible game on either side.

Primary window = first four eligible games after the announcement. At least four games are needed for the main comparison; shorter cases remain in the table marked insufficient follow-up. Use local America/Chicago calendar dates for announcement comparisons to avoid UTC midnight shifting a Saturday game into Sunday. Cases in this sample have no same-day post-announcement games; verify using the schedule.

A NEW combined alarm requires the first WECO or CUSUM alarm of the target season to occur within the four-game window, with neither detector having alarmed before the change. Record preexisting signals separately. This operational definition is a diagnostic, not a significance test or proof of a causal effect. Report each detector separately. Compute adjusted change = four-game mean minus prior-season baseline mean, with a percentile bootstrap over games (2,000 resamples); these exploratory intervals do not account for all model uncertainty or serial dependence.

## Placebo dates and sensitivity

Sample 50 distinct non-case team-season units using a fixed seed, matching each to a real eligible case's season and number of pre-change eligible games (within one). Require eight baseline games and a four-game follow-up. Apply the identical prior-year fit, baseline, whole-season scanning and new-alarm definition. Do not select placebos by their observed outcomes. Exclude the ten study team-seasons; unrecorded real changes can remain among controls. Report the rate as a PLACEBO ALARM RATE, not a known true false-positive rate. Include an approximate Wilson interval and disclose team reuse across seasons/dependence. Matching is for timing, not for the decision process leading to a firing; no causal comparison follows.

Sensitivity outputs: unadjusted chart; sample-SD rather than MR sigma; CUSUM h=4 and h=6; >=40 measured plays; first-four-game vs all-follow-up mean difference. No selective replacement of the primary result.

## Secondary drive analysis

Join drive records to cleaned plays. Use only regulation drives with at least one eligible offensive snap; exclude drives containing garbage-time snaps. For a consistent tempo/points sample, require positive valid elapsed time and known drive outcome. Points = 6 for offensive TD, 3 for made field goal, 0 otherwise; exclude conversions from the points measure and label this explicitly. Never count defensive return TDs as offensive points.

Headline tempo = eligible offensive snaps / possession minutes (drive elapsed time includes clock consumed by excluded administrative/special-teams events; disclose). Also report within-drive adjacent snap intervals and a conservative in-bounds run/completed-pass subset; these are game-clock pace, not wall-clock speed. Exclude intervals crossing halves or containing excluded intervening events.

Bottleneck conversion = first down or offensive TD on the current eligible snap, conditional on down/distance/field zone. Use yards gained >= yards to gain or offensive TD, with turnover outcomes forced to failure. This is next-snap conversion, not probability of eventual drive survival. Compare with leave-team-out same-season FBS rates, show counts, and suppress cells with fewer than 20 snaps. Rank top 10 and bottom 50 by observed points/drive, without calling that an opponent-adjusted ranking.

## Deliverables and sources

Reproducible scripts, schema/views, notebook, derived tables, charts, two-page PDF, three truthful resume bullets, and a local dashboard plus Tableau handoff. Public publishing requires the user's account. Never publish .env, raw plays or the SQLite database. The final status checklist must distinguish native Tableau validation/publishing from local dashboard completion.

Method references: [NIST WECO discussion](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc32.htm), [NIST CUSUM](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm), [CFBD documentation](https://api.collegefootballdata.com/getting-started).
