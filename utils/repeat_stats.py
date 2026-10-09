"""Repeat means, sample SD and paired bootstrap"""
import numpy as np
FIELDS=('max_distance','burned_cells','east_distance','protected_fraction','total_fuel_burned','fuel_removed','active_cells')


def summarize(raw):
    groups={}
    for row in raw:groups.setdefault((row['group'],row['layout']),[]).append(row)
    summaries=[];pairs=[]
    for (group,layout),rows in groups.items():
        ids=[r.get('repeat',0) for r in rows]
        if len(set(ids))!=len(ids):raise ValueError('Duplicate repeat')
        item=dict(group=group,layout=layout,runs=len(rows),sd={})
        for key in FIELDS:
            values=[r[key] for r in rows]
            item[key]=float(np.mean(values))
            item['sd'][key]=float(np.std(values,ddof=1)) if len(rows)>1 else None
        arrived=[r['arrival_step'] for r in rows if r['arrival_step'] is not None]
        item['arrived']=len(arrived)
        item['arrival_step']=float(np.mean(arrived)) if arrived else None
        item['arrival_sd']=float(np.std(arrived,ddof=1)) if len(arrived)>1 else None
        # Contact/cross averages are conditional on observing each event.
        for key in ('contact_steps','cross_steps'):
            item[key]=[];item[key+'_counts']=[]
            for i in range(len(rows[0][key])):
                v=[r[key][i] for r in rows if r[key][i] is not None]
                item[key].append(float(np.mean(v)) if v else None);item[key+'_counts'].append(len(v))
        if len({len(r['curve']) for r in rows})!=1:raise ValueError('Unequal trajectory lengths')
        item['curve']=[]
        for t in range(len(rows[0]['curve'])):
            point=dict(step=t)
            for key in ('total_cells','new_cells'):
                v=[r['curve'][t][key] for r in rows]
                point[key]=float(np.mean(v));point[key+'_sd']=float(np.std(v,ddof=1)) if len(v)>1 else 0.
            item['curve'].append(point)
        summaries.append(item)
        if layout=='single':continue
        ref={r.get('repeat',0):r for r in groups[(group,'single')]}
        if set(ids)!=set(ref):raise ValueError('Unmatched repeat IDs')
        for r in rows:
            for key in ('seed','ignition'):
                if r.get(key)!=ref[r.get('repeat',0)].get(key):raise ValueError('Unmatched '+key)
        output=dict(group=group,layout=layout,runs=len(rows))
        for field in ('protected_fraction','total_fuel_burned','burned_cells'):
            values=np.array([r[field]-ref[r.get('repeat',0)][field] for r in rows])
            low=high=None
            if len(values)>1:
                rng=np.random.default_rng(2026)
                draws=values[rng.integers(len(values),size=(2000,len(values)))].mean(axis=1)
                low,high=map(float,np.quantile(draws,[.025,.975]))
            output[field]=dict(mean=float(values.mean()),low=low,high=high,
                median=float(np.median(values)),double_wins=int((values < -1e-9).sum()),
                single_wins=int((values>1e-9).sum()),ties=int((np.abs(values)<=1e-9).sum()))
        pairs.append(output)
    return summaries,pairs
