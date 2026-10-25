# Completion against the brief

| Requirement | Status / evidence |
|---|---|
| Primary question | Complete: coaching-change process study |
| Data scope | Complete for adjusted 2021–2023 scope; not all 2015–2025 seasons |
| Cache and SQLite | Complete locally; 634,546 raw plays |
| Cleaning and SQL views | Complete with documented limitations and audit |
| 8–10 changes including Texas A&M | Complete: ten sources and first affected game/week |
| Opponent adjustment | Complete: prior-year fixed effects, focal offense excluded from fit |
| SPC/CUSUM/WECO | Complete: I-MR, four rules, blind first CUSUM crossing |
| Fifty fake dates | Complete: 50 matched distinct team-season units |
| Tempo/bottlenecks | Complete descriptively: tables, model, charts/heatmap |
| Notebook and finding-first README | Complete |
| Two-page write-up | Complete: both PDF pages visually checked |
| Resume bullets | Complete: supported numbers and published Tableau dashboard |
| Local dashboard | Built; selector logic verified in isolated DOM tests; browser rendering unverified due environment restrictions |
| Native Tableau/Power BI dashboard | Native checked: three charts render in Tableau Public 2026.3; Texas A&M control selector verified |
| GitHub publication | Published: https://github.com/shawnslee1202/football-drives |
| Tableau Public/Power BI publication | Published October 23, 2026: https://public.tableau.com/app/profile/shawn.lee1439/viz/football-drives/Footballproductionline |
| Monte Carlo | Optional; not implemented |

The required deliverables are complete for the declared 2021-2023 scope, including GitHub and Tableau Public publication. The original 2015-2025 span is not covered; optional Monte Carlo is not implemented.

## Publication (October 25, 2026)

GitHub repository: https://github.com/shawnslee1202/football-drives. Tableau Public publication and native rendering are verified. Release includes code, aggregate data, notebook, PDF, charts and packaged Tableau workbook. API credentials, raw responses and private SQLite data are excluded.

The release now explicitly includes `interventions.csv`, the dated coaching changes and their citations. The release validator runs the isolated dashboard logic harness on every invocation instead of relying on an earlier result.
