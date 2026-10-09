"""Metrics reconstructed from saved states"""
import numpy as np


def measure(demo):
    n=demo['n'];state=np.zeros(n*n,dtype=np.uint8);ir,ic=demo['ignition']
    bands=demo['bands'];contact=[None]*len(bands);cross=[None]*len(bands)
    arrival=None;curve=[];previous=0
    for t,changes in enumerate(demo['frames']):
        for v in changes:state[abs(v)-1]=1 if v>0 else 2
        grid=state.reshape(n,n);ever=grid>0;count=int(ever.sum())
        if arrival is None and ever[:,55].any():arrival=t
        for i,(col,width) in enumerate(bands):
            if contact[i] is None and ever[:,col-1].any():contact[i]=t
            if cross[i] is None and ever[:,col+width].any():cross[i]=t
        # Initial ignition is not a spread event
        curve.append(dict(step=t,total_cells=count,new_cells=count-previous if t else 0))
        previous=count
    rr,cc=np.nonzero(ever)
    return dict(max_distance=float(np.hypot(rr-ir,cc-ic).max()) if len(rr) else 0.,
        burned_cells=count,east_distance=max(0,int(cc.max())-ic) if len(cc) else 0,
        protected_fraction=float(ever[:,55:].mean()),arrival_step=arrival,
        total_fuel_burned=demo['history'][-1]['total_burned'],
        fuel_removed=demo['result']['fuel_removed'],active_cells=int((state==1).sum()),
        contact_steps=contact,cross_steps=cross,curve=curve)
