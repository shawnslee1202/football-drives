-- Keep original JSON locally so normalization is reproducible.
DROP VIEW IF EXISTS team_game_metrics;
DROP VIEW IF EXISTS quality_audit;
DROP VIEW IF EXISTS clean_plays;
DROP VIEW IF EXISTS classified_plays;
CREATE VIEW classified_plays AS
WITH extracted AS (
 SELECT p.id AS play_id, p.season,
 json_extract(p.body,'$.gameId') AS game_id,
 json_extract(p.body,'$.driveId') AS drive_id,
 json_extract(g.body,'$.week') AS week,
 json_extract(g.body,'$.startDate') AS game_date,
 json_extract(g.body,'$.homeTeam') AS home_team,
 json_extract(g.body,'$.awayTeam') AS away_team,
 CASE WHEN json_extract(p.body,'$.offense')=json_extract(g.body,'$.homeTeam') THEN json_extract(g.body,'$.homeId')
 WHEN json_extract(p.body,'$.offense')=json_extract(g.body,'$.awayTeam') THEN json_extract(g.body,'$.awayId') END AS team_id,
 CASE WHEN json_extract(p.body,'$.defense')=json_extract(g.body,'$.homeTeam') THEN json_extract(g.body,'$.homeId')
 WHEN json_extract(p.body,'$.defense')=json_extract(g.body,'$.awayTeam') THEN json_extract(g.body,'$.awayId') END AS opponent_id,
 CASE WHEN json_extract(g.body,'$.neutralSite')=1 THEN 0
 WHEN json_extract(p.body,'$.offense')=json_extract(g.body,'$.homeTeam') THEN 1 ELSE -1 END AS home_indicator,
 json_extract(p.body,'$.driveNumber') AS drive_number,
 json_extract(p.body,'$.playNumber') AS play_number,
 json_extract(p.body,'$.clock.minutes')*60+json_extract(p.body,'$.clock.seconds') AS clock_s,
 json_extract(p.body,'$.offense') AS team,
 json_extract(p.body,'$.defense') AS opponent,
 json_extract(p.body,'$.ppa') AS ppa,
 json_extract(p.body,'$.period') AS period,
 json_extract(p.body,'$.down') AS down,
 json_extract(p.body,'$.distance') AS distance,
 json_extract(p.body,'$.yardsToGoal') AS yards_to_goal,
 json_extract(p.body,'$.yardsGained') AS yards_gained,
 json_extract(p.body,'$.playType') AS play_type,
 lower(coalesce(json_extract(p.body,'$.playText'),'')) AS play_text,
 json_extract(p.body,'$.offenseScore') AS offense_score,
 json_extract(p.body,'$.defenseScore') AS defense_score,
 EXISTS(SELECT 1 FROM teams t WHERE t.season=p.season AND t.id=json_extract(g.body,'$.homeId'))
 AND EXISTS(SELECT 1 FROM teams t WHERE t.season=p.season AND t.id=json_extract(g.body,'$.awayId')) AS fbs_game
 FROM plays p JOIN games g ON g.id=json_extract(p.body,'$.gameId')
 WHERE json_extract(g.body,'$.seasonType')='regular'
), ordered AS (
 SELECT *,
 lag(CASE WHEN team=home_team THEN offense_score ELSE defense_score END,1,0)
 OVER (PARTITION BY game_id ORDER BY period,clock_s DESC,drive_number,play_number,play_id) AS pre_home_score,
 lag(CASE WHEN team=home_team THEN defense_score ELSE offense_score END,1,0)
 OVER (PARTITION BY game_id ORDER BY period,clock_s DESC,drive_number,play_number,play_id) AS pre_away_score
 FROM extracted
)
SELECT *, CASE
 WHEN NOT fbs_game THEN 'non_fbs'
 WHEN period IS NULL OR period NOT BETWEEN 1 AND 4 THEN 'non_regulation'
 WHEN offense_score IS NULL OR defense_score IS NULL OR pre_home_score IS NULL OR pre_away_score IS NULL THEN 'missing_score'
 WHEN period=4 AND abs(pre_home_score-pre_away_score)>28 THEN 'garbage_time'
 WHEN down IS NULL OR down NOT BETWEEN 1 AND 4 THEN 'invalid_down'
 WHEN play_text LIKE '%kneel%' OR play_text LIKE '%spikes the ball%'
 OR play_text LIKE '%spiked the ball%' OR play_text LIKE '%spike the ball%' THEN 'kneel_or_spike'
 WHEN play_text LIKE '%no play%' THEN 'no_play'
 WHEN play_text LIKE '%punt%' OR play_text LIKE '%kickoff%'
 OR play_text LIKE '%field goal%' THEN 'special_teams_text'
 WHEN play_type NOT IN ('Rush','Pass Reception','Pass Incompletion','Passing Touchdown',
 'Rushing Touchdown','Sack','Interception','Interception Return Touchdown','Pass Interception Return','Safety',
 'Fumble Recovery (Opponent)','Fumble Recovery (Own)','Fumble Return Touchdown')
 OR play_type IS NULL THEN 'excluded_or_unmapped_type'
 ELSE 'eligible' END AS disposition
FROM ordered;
CREATE VIEW clean_plays AS SELECT * FROM classified_plays WHERE disposition='eligible';
CREATE VIEW team_game_metrics AS
SELECT season, game_id, game_date, team, opponent, count(*) AS eligible_plays,
count(ppa) AS ppa_n, avg(ppa) AS mean_ppa,
1.0*count(ppa)/count(*) AS ppa_coverage
FROM clean_plays GROUP BY season,game_id,game_date,team,opponent;
CREATE VIEW quality_audit AS
SELECT season, disposition, play_type, count(*) AS records,
sum(CASE WHEN ppa IS NULL THEN 1 ELSE 0 END) AS missing_ppa
FROM classified_plays GROUP BY season,disposition,play_type;
