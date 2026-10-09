"""Small rule checks"""
import unittest
import numpy as np
from src.model import simulate


class ModelTests(unittest.TestCase):
    def test_zero_probability(self):
        r,h=simulate(np.ones((10,10)),np.zeros((10,10)),1,(5,2),7,edge=5,p0=0,steps=20)
        self.assertAlmostEqual(r['total_burned'],1.)
        self.assertEqual(r['status'],'not_reached')

    def test_empty_full_band(self):
        r,h=simulate(np.ones((10,10)),np.zeros((10,10)),1,(5,4),7,edge=5,residual=0,p0=1,steps=100)
        self.assertEqual(r['status'],'blocked_extinct')
        self.assertIsNone(r['cross_step'])

    def test_no_treatment_equivalence(self):
        a,ha=simulate(np.ones((10,10)),np.zeros((10,10)),0,(5,2),7,edge=5,steps=15)
        b,hb=simulate(np.ones((10,10)),np.zeros((10,10)),2,(5,2),7,edge=5,residual=1,steps=15)
        self.assertEqual(ha,hb)

    def test_censored_contact(self):
        r,h=simulate(np.ones((10,10)),np.zeros((10,10)),2,(5,4),7,edge=5,p0=0,steps=1)
        self.assertEqual(r['status'],'not_crossed_yet')

if __name__=='__main__':unittest.main()
