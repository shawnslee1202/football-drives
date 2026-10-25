# Texas A&M pilot: real-data run

**Exploratory, unadjusted results. This is not a causal conclusion or the completed study.**

The 2023 series contains 11 eligible team-games, with 1 after the November 12 coaching announcement. The planned minimum follow-up is four games; fewer means insufficient follow-up for the proposed study.

## Download and cleaning

| Season | Raw play records |
|---|---:|
| 2022 | 241,277 |
| 2023 | 242,499 |

Exported 2,968 team-game rows across both seasons.

| Cleaning disposition | Records |
|---|---:|
| eligible | 189,800 |
| excluded_or_unmapped_type | 20,880 |
| garbage_time | 8,432 |
| invalid_down | 13,324 |
| kneel_or_spike | 844 |
| no_play | 6,776 |
| non_fbs | 221,591 |
| non_regulation | 656 |
| special_teams_text | 21,473 |

Raw counts include records outside the study scope. Filters are sequential, so each excluded record has one first exclusion reason.

## Texas A&M: 2023

| Game date (UTC) | Opponent | PPA observations | Mean PPA | Beyond 3 sigma | CUSUM alarm | After change |
|---|---|---:|---:|---|---|---|
| 2023-09-02 | New Mexico | 46 | 0.594 | True | False | False |
| 2023-09-09 | Miami | 82 | 0.093 | False | False | False |
| 2023-09-16 | UL Monroe | 60 | 0.548 | True | True | False |
| 2023-09-23 | Auburn | 58 | 0.238 | False | True | False |
| 2023-09-30 | Arkansas | 67 | -0.059 | False | True | False |
| 2023-10-07 | Alabama | 59 | -0.078 | False | False | False |
| 2023-10-14 | Tennessee | 66 | -0.139 | False | False | False |
| 2023-10-28 | South Carolina | 70 | 0.189 | False | False | False |
| 2023-11-04 | Ole Miss | 78 | 0.262 | False | False | False |
| 2023-11-12 | Mississippi State | 49 | 0.391 | False | False | False |
| 2023-11-25 | LSU | 76 | 0.118 | False | False | True |

Fixed baseline: 11 eligible 2022 games. Center = 0.083 PPA; limits = [-0.283, 0.448].

## Interpretation and remaining work

An alarm is a diagnostic flag, not proof of a coaching effect. No alarm does not establish that nothing changed. CUSUM runs across the full target season and retains its accumulated state after an alarm.

Opponent adjustment, baseline stability, sample-size/dependence checks, matched placebo calibration, and a broader intervention sample remain unfinished. Prior-season personnel and staff changes can affect comparability.

Cleaning uses the preceding observed score in game order because sampled scoring records contain post-play scores. Missing records and tied-clock ordering can still affect this reconstruction. Kneels/spikes and special-teams descriptions are filtered with text rules that need broader validation.

Data provided by [CollegeFootballData.com](https://collegefootballdata.com). Intervention source: [Texas A&M announcement](https://12thman.com/news/2023/11/12/texas-am-athletics-announces-change-in-football-leadership).
