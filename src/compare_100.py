"""M1 and M2 selection, repeated paired runs, 100 steps"""
import argparse
import hashlib
import random
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.model import simulate
from utils.io import load_map,write_json,map_file
from utils.animation import Frames,save_animation
from utils.compare_report import report
from utils.metrics import measure
WINDS=('none','E','S','W','N')


def layout_specs(area):
    """Same near edge, exact area"""
    return [('single',[(33,area)])]+[(f'gap_{gap}',[(33,area//2),(33+area//2+gap,area//2)]) for gap in range(1,16)]


def make_plan(seed, repeats=1):
    """Each map/wind/area shares a start across all 16 layouts.
    All 16 layouts share each repeat's ignition and seed; groups use different starts.
    """
    rng=random.Random(seed);plan=[]
    for name in ('M1','M2'):
        fuel,_=load_map(ROOT,name)
        eligible=[(r,c) for r in range(100) for c in range(33) if fuel[r,c]>0]
        if len(eligible)<15:raise ValueError('Not enough left-side ignition cells')
        starts=iter(rng.sample(eligible,15))
        for wind in WINDS:
            for area in (2,4,6):
                plan.append(dict(id=f'{name}_{wind}_a{area}',map=name,wind=wind,area=area,
                                 ignition=next(starts),seed=rng.randrange(1,2**31)))
    if repeats < 1: raise ValueError('Repeats must be positive')
    # Keep repeat zero compatible with earlier experiments
    for group in plan:
        fuel,_=load_map(ROOT,group['map'])
        eligible=[(r,c) for r in range(100) for c in range(33) if fuel[r,c]>0]
        group['runs']=[dict(repeat=0,ignition=group['ignition'],seed=group['seed'])]
        for rep in range(1,repeats):
            group['runs'].append(dict(repeat=rep,ignition=rng.choice(eligible),seed=rng.randrange(1,2**31)))
    return plan


def spatial_metrics(flat_state,ignition,n=100):
    """Ever ignited includes active and burnt cells"""
    rr,cc=np.nonzero(np.asarray(flat_state).reshape(n,n)>0)
    farthest=float(np.hypot(rr-ignition[0],cc-ignition[1]).max()) if len(rr) else 0.
    return dict(max_distance=farthest,burned_cells=int(len(rr)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repeats',type=int,default=1)
    p.add_argument('--seed',type=int,default=7)
    p.add_argument('--plan-only',action='store_true')
    p.add_argument('--out',type=Path,default=ROOT/'data/results/compare_100')
    a=p.parse_args()
    if a.repeats<1:p.error('--repeats must be positive')
    plan=make_plan(a.seed,a.repeats)
    print(f'30 groups x 16 layouts x {a.repeats} repeats = {480*a.repeats} runs; 100 steps.')
    if a.plan_only:
        for group in plan:print(group)
        return
    if a.out.exists() and any(a.out.iterdir()):p.error('Output exists; choose a new --out')
    a.out.mkdir(parents=True);(a.out/'animations').mkdir()
    config=dict(steps=100,repeats=a.repeats,master_seed=a.seed,terrain='real',height_divisor=90,
                p0=.2,residual=.2,consumption=.2,wind_strength=.5,slope_strength=1.,
                left_ignition_columns=[0,32],first_band_column=33,
                distance='Maximum Euclidean centre-to-centre distance from ignition to any ever-ignited cell; model cell units',
                burned_cells='Ever ignited by step 100, including initial ignition and still-burning cells',groups=plan)
    files=[ROOT/'src/compare_100.py',ROOT/'src/model.py',ROOT/'utils/compare_report.py',ROOT/'utils/animation.py',ROOT/'utils/animation.html',ROOT/'utils/io.py',ROOT/'utils/metrics.py',ROOT/'utils/compare_charts.js',ROOT/'utils/repeat_stats.py']
    files += [map_file(ROOT,name,f) for name in ('M1','M2') for f in ('base_relative_fuel.csv','height_grid.csv')]
    config['sha256']={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    write_json(a.out/'config.json',config);results=[]
    for group in plan:
        fuel,height=load_map(ROOT,group['map']);demos=[]
        for entry in group['runs']:
            for label,bands in layout_specs(group['area']):
                assert sum(w for c,w in bands)*100==group['area']*100
                frames=Frames(100)
                result,history=simulate(fuel,height,0,tuple(entry['ignition']),entry['seed'],group['wind'],100,
                    edge=33,bands=bands,frame_callback=frames)
                metrics=spatial_metrics(frames.previous,entry['ignition'])

                # Early extinction is frozen through step 100
                for t in range(len(history),101):
                    history.append(dict(history[-1],step=t));frames.frames.append([])
                demo=dict(map=group['map'],wind=group['wind'],width=group['area'],bands=bands,
                    label=f"{label} / {group['area']}%",n=100,edge=33,seed=entry['seed'],ignition=entry['ignition'],
                    empty=np.flatnonzero(fuel.ravel()==0).tolist(),frames=frames.frames,history=history,result=result)
                if entry['repeat']==0:demos.append(demo)
                results.append(dict(group=group['id'],layout=label,repeat=entry['repeat'],ignition=entry['ignition'],seed=entry['seed'],**measure(demo)))
        page=a.out/'animations'/f"{group['id']}.html"
        save_animation(page,demos)
        text=page.read_text().replace('Treatment layout: first run','Treatment layout: 100 steps')
        text=text.replace('Each width uses the same map, ignition and spread seed. First repeat only; see the summary for all five repeats.',
            'First repeat shown. Summary and curves average all repeats. Within each repeat layouts share ignition and spread seed. Extinct states are held through step 100.')
        page.write_text(text)
        write_json(a.out/'results.json',results)
        print(group['id'],'complete',flush=True)
    report(a.out)
    print('Open',a.out/'comparison.html')

if __name__=='__main__':main()
