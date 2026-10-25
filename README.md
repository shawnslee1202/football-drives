# Drives as a Production Line

**One of eight coaching changes with four-game follow-up produced a new nominal control-chart alarm, versus seven of 50 matched placebo dates (14%).** The sole case alarm is sensitive to the baseline variance estimate. This study does not establish a reliable causal coaching effect.

The project evaluates ten documented mid-season coaching changes in 2022–2023, using 2021–2022 prior-season baselines. It treats plays as operations, drives as production runs, game-clock pace as throughput, and points as output. The primary question is whether the process changed, not whether a coach deserves credit or blame.

## Results and artifacts

[View the published Tableau dashboard](https://public.tableau.com/app/profile/shawn.lee1439/viz/football-drives/Footballproductionline).

- [Two-page study](football-drives-study.pdf): visually verified PDF.
- [Offline dashboard](dashboard.html): case-level I-MR/CUSUM charts, tempo scatter and team bottleneck heatmap. Keep it alongside `charts/` and `derived/`. Selector logic is tested; browser visual rendering remains unverified here.
- [Executed notebook](analysis.ipynb): actual derived results, placebos, sensitivities and data audit.
- [Protocol](PROTOCOL.md), [quality notes](QUALITY_NOTES.md), [intervention sources](interventions.csv), [data dictionary](DATA_DICTIONARY.md).
- [Resume bullets](resume-bullets.md): supported numbers and the published dashboard.
- [Tableau workbook](tableau/football-drives.twbx): three charts and native extracts, opened and visually checked in Tableau Public 2026.3. See [handoff](tableau/README.md).
- [Completion checklist](STATUS.md): finished local work versus native-app review and publishing.

| Primary study outcome | Result |
|---|---:|
| Documented changes | 10 |
| Changes with four eligible follow-up games | 8 |
| New alarm within four games | 1 / 8 (12.5%) |
| Placebo new alarms | 7 / 50 (14%; approximate 95% Wilson interval 7%-26%) |
| Baselines with WECO flags | 0 / 10; small samples limit this check |
| First CUSUM crossing within one eligible game of change | 0 / 10 |

Nebraska's new alarm is downward and disappears under a sample-SD baseline. Charlotte had an alarm before its change. Texas A&M and Boise State have one and three eligible post-change games and do not enter the four-game comparison. The >=40-measured-play sensitivity produces two new alarms; raw and adjusted charts flag different teams. These variations prevent a robust coaching-effect claim.

The study uses I-MR charts on mean PPA, all four WECO rules and date-blind standardized CUSUM. Opponent/home effects are trained exclusively on prior-season games, excluding the focal offense. Placebos use the same procedure and matched season/timing. These are diagnostic alarms, not calibrated causal tests.

## Secondary findings and coverage

The descriptive tempo model uses 4,294 team-games from 2,166 games. One additional eligible snap per possession minute is associated with **-0.039 points/drive**, 95% game-clustered interval **[-0.127, +0.049]**, controlling for offense, defense, season, starting field position and home field. The interval includes zero. Bottlenecks measure next-snap conversion, not eventual drive survival; cells below 20 snaps are suppressed. Top-10/bottom-50 groups use observed points/drive.

634,546 raw plays across three seasons; 285,315 eligible offensive plays, 284,804 with PPA. All 2,216 expected completed FBS-vs-FBS games have records. Drive metrics retain 48,692 drives. Raw counts include out-of-scope records.

Season-specific FBS membership and team IDs; regulation only. Exclude kneels/spikes, penalties/no-play records, special teams, unknown types, and fourth-quarter preceding-score margins above 28. Game coverage does not prove every play is complete or correct. **Points per drive uses offensive TD=6 and FG=3, excluding conversions.** Pace uses the game clock, not wall time. Possession duration includes clock consumed by administrative/special-teams events; the clean in-bounds subset is small and conservatively text-filtered.

Data provided by [CollegeFootballData.com](https://collegefootballdata.com). API base/authentication follow [current documentation](https://api.collegefootballdata.com/getting-started). Check account limits through [usage and access](https://api.collegefootballdata.com/usage-and-access), rather than the proposal's historical quota figures.

## Reproduce

Python 3.12 was used. Install `requirements.txt`; actual final-run versions are in `derived/runtime_versions.json`. An API key is needed only for uncached downloads.

Node.js is also required for the release validator's dashboard logic checks. Put `node` on PATH or set `NODE_EXE` to its executable. These checks exercise selectors and data rendering logic; they do not verify browser appearance.

```powershell
python -m pip install -r requirements.txt
# Create .env beside pipeline.py with CFBD_API_KEY=your_key
python pipeline.py pull --seasons 2021 2022 2023
python pipeline.py drives --seasons 2021 2022 2023
python build_tables.py
python study.py
python secondary.py
python make_deliverables.py
python make_tableau.py
python validate_release.py
python -m unittest -v
```

Or run `run-study.ps1 -PythonExe 'C:\path\to\python.exe'` after dependency installation; add `-Download` to retrieve uncached inputs. Downloads are sequential and cached. An environment key takes precedence over `.env`; neither is embedded in output.

| Component | Purpose |
|---|---|
| pipeline.py | Authenticated cache, raw SQLite schema, pilot CLI |
| views.sql | Classified/clean plays and game/audit SQL views |
| build_tables.py | Stable team IDs, coverage audit, clean drive table/view, pace/bottlenecks |
| study.py | Prior-season adjustment, I-MR/WECO/CUSUM, 50 placebos, sensitivity |
| secondary.py | Tempo regression with game-clustered uncertainty |
| make_deliverables.py | Charts, PDF, executed notebook, offline dashboard |
| make_tableau.py | Tableau workbook, native extracts and structural checks |
| validate_release.py | Data/artifact integrity, runtime/input manifests and clean ZIP |
| test_pipeline.py / test_study.py | Seven tests of cleaning, score timing, signals and training isolation |

`raw/` and `local/` hold private cached responses/SQLite/intermediate rows and are gitignored, as is `.env`. `derived/` holds aggregates. `pilot-results.md`, `report.py`, `run-pilot.ps1` and `demo/` preserve the earlier pilot and are superseded by this study; synthetic values are not evidence.

## Limitations and completion

Retrospective convenience sample, not preregistered: the Texas A&M pilot was inspected first. Prior-season defense strength and roster/staff changes limit comparability. Game-average precision varies; plays are dependent. Bootstrap intervals omit adjustment uncertainty and serial dependence. Placebos are not known to be change-free, and matching does not reproduce the decision to fire a coach. No multiple-testing-controlled discovery claim is made.

The local analysis and research artifacts are complete for the declared three-season scope. **Native Tableau rendering and the Texas A&M control selector have been verified. The Tableau dashboard and GitHub repository are published.** The optional Monte Carlo simulation is not implemented. The published Tableau link above is live; [GitHub repository](https://github.com/shawnslee1202/football-drives); completion details are tracked in STATUS.md.
