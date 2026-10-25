import unittest
import numpy as np
import pandas as pd
from study import weco, control, classify, first_alarm, Adjuster

class StudyTests(unittest.TestCase):
    def test_weco_four_rules(self):
        self.assertTrue(weco([3.1])[-1,0])
        self.assertTrue(weco([2.2,-0.1,2.1])[-1,1])
        self.assertTrue(weco([1.1,1.2,-0.1,1.3,1.2])[-1,2])
        self.assertTrue(weco([0.1]*8)[-1,3])
        self.assertFalse(weco([0.2,-0.2]*8).any())

    def test_cusum_accumulates_and_does_not_backdate(self):
        chart,_=control([-0.564,0.564]*6,[1.0]*12)
        self.assertEqual(first_alarm(chart,'cusum_alarm'),10)

    def test_preexisting_is_not_new_and_short_window_is_ineligible(self):
        chart,_=control([-0.564,0.564]*6,[4.0]+[0.0]*11)
        self.assertTrue(classify(chart,3)['preexisting_alarm'])
        self.assertFalse(classify(chart,3)['new_alarm'])
        self.assertFalse(classify(chart,10)['main_eligible'])
        fresh,_=control([-0.564,0.564]*6,[0.0]*3+[4.0]+[0.0]*8)
        self.assertTrue(classify(fresh,3)['new_alarm'])

    def test_adjustment_never_trains_on_target_or_focal_offense(self):
        rows=[]
        for offense in range(4):
            for defense in range(4):
                if offense==defense:
                    continue
                for home in [-1,1]:
                    rows.append(dict(season=2021,team_id=offense,opponent_id=defense,home_indicator=home,ppa_n=60,mean_ppa=0.1*offense-0.05*defense+0.02*home,chart_eligible=True))
        frame=pd.DataFrame(rows)
        fitted=Adjuster(frame).fit(2022,0)
        mutated=frame.copy()
        mutated.loc[mutated.team_id==0,'mean_ppa']=999
        target=mutated.copy(); target['season']=2022; target['mean_ppa']=-999
        other=Adjuster(pd.concat([mutated,target])).fit(2022,0)
        self.assertAlmostEqual(fitted['home'],0.02,places=8)
        self.assertAlmostEqual(fitted['effects'][2]-fitted['effects'][1],-0.05,places=8)
        self.assertEqual(fitted,other)

if __name__=='__main__':
    unittest.main()
