import json
import sqlite3
from pathlib import Path
import tempfile
import unittest
from pipeline import database, export, signals

class PipelineTests(unittest.TestCase):
    def test_touchdown_uses_preceding_score(self):
        conn = sqlite3.connect(':memory:')
        conn.executescript('CREATE TABLE games(id,season,body); CREATE TABLE teams(season,id,body); CREATE TABLE plays(id,season,body);')
        conn.executemany('INSERT INTO teams VALUES(2023,?,?)',[(1,'{}'),(2,'{}')])
        conn.execute('INSERT INTO games VALUES(1,2023,?)',(json.dumps(dict(homeId=1,awayId=2,homeTeam='A',seasonType='regular')),))
        for i, score in enumerate([28,35,35]):
            play = dict(gameId=1,offense='A',defense='B',period=4,down=1,playType='Rush',offenseScore=score,defenseScore=0,clock={'minutes':10-i,'seconds':0},ppa=0.2)
            conn.execute('INSERT INTO plays VALUES(?,2023,?)',(str(i),json.dumps(play)))
        conn.executescript((Path(__file__).parent/'views.sql').read_text())
        self.assertEqual(conn.execute('SELECT disposition FROM classified_plays ORDER BY play_id').fetchall(), [('eligible',),('eligible',),('garbage_time',)])
        conn.close()

    def test_shift_and_insufficient_baseline(self):
        baseline = [0.05, 0.15]*12
        rows = signals(baseline, [0.1]*8 + [0.8]*8)
        self.assertFalse(any(r['cusum_signal'] for r in rows[:8]))
        self.assertTrue(rows[-1]['cusum_signal'])
        self.assertTrue(rows[-1]['outside_3sigma'])
        with self.assertRaises(ValueError):
            signals([1]*3, [2])
        with self.assertRaises(ValueError):
            signals([1]*8, [2])

    def test_sql_filters_and_missing_ppa_denominator(self):
        scratch = Path(__file__).resolve().parent / 'local'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            root = Path(temp)
            conn = database(root/'test.sqlite')
            for i in [1,2]:
                conn.execute('INSERT INTO teams VALUES(?,?,?)',(2023,i,'{}'))
            game = {'homeId':1,'awayId':2,'homeTeam':'A','seasonType':'regular','startDate':'2023-09-01T12:00:00Z'}
            conn.execute('INSERT INTO games VALUES(?,?,?)',(10,2023,json.dumps(game)))
            base = dict(gameId=10,offense='A',defense='B',period=1,down=1,playType='Rush',offenseScore=0,defenseScore=0,ppa=0.2)
            variants = [{}, {'ppa':None}, {'period':5}, {'playType':'Punt'}, {'offenseScore':None},
                        {'playText':'Quarterback kneels at the 20'},
                        {'playText':'Quarterback spikes the ball'},
                        {'playType':'Fumble Recovery (Opponent)','playText':'Punt muffed and recovered'},
                        {'playText':'Penalty NO PLAY'},
                        {'period':4,'offenseScore':35,'playType':'End Period'},
                        {'period':4,'offenseScore':35}]
            for i, patch in enumerate(variants):
                conn.execute('INSERT INTO plays VALUES(?,?,?)',(str(i),2023,json.dumps(base|{'clock':{'minutes':14,'seconds':59-i},'driveNumber':1,'playNumber':i}|patch)))
            export(conn,root/'exports')
            row = conn.execute('SELECT * FROM team_game_metrics').fetchone()
            self.assertEqual(row['eligible_plays'],2)
            self.assertEqual(row['ppa_n'],1)
            self.assertAlmostEqual(row['mean_ppa'],0.2)
            self.assertEqual(conn.execute('SELECT sum(records) FROM quality_audit').fetchone()[0],11)
            self.assertEqual(conn.execute("SELECT count(*) FROM classified_plays WHERE disposition='garbage_time'").fetchone()[0],1)
            conn.close()

if __name__ == '__main__':
    unittest.main()
