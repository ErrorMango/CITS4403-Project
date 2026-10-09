"""Figures from saved runs only"""
import gzip
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image, ImageDraw
from utils.io import load_map

BLUE, ORANGE = '#2466a0', '#c96729'


def load_demo(root):
    """Load the portable analysis inputs"""
    def read(name):
        with gzip.open(root/'data/demo'/name, 'rt') as f:
            return json.load(f)
    return read('results.json.gz'), read('config.json.gz')


def save_figure(fig, folder, name):
    fig.savefig(folder/(name+'.png'), dpi=160, bbox_inches='tight')
    return fig


def map_figure(root):
    fig, axs = plt.subplots(2, 2, figsize=(10, 7), layout='constrained')
    for i, name in enumerate(('M1','M2')):
        fuel, height = load_map(root, name)
        a = axs[i,0].imshow(fuel, vmin=0, vmax=1.5, cmap='YlGn', origin='upper')
        b = axs[i,1].imshow(height*90, vmin=125, vmax=375, cmap='terrain', origin='upper')
        axs[i,0].set_title(f'{name}: relative fuel')
        axs[i,1].set_title(f'{name}: elevation (m)')
        for ax in axs[i]:
            ax.set_xlabel('Column (west to east)'); ax.set_ylabel('Row (north to south)')
            ax.axvline(32.5, color='black', ls='--', lw=1)
    fig.colorbar(a, ax=axs[:,0], label='Relative fuel')
    fig.colorbar(b, ax=axs[:,1], label='Elevation (m)')
    return fig


def layout_figure():
    fig, axs = plt.subplots(1,3,figsize=(11,3.5),layout='constrained')
    for ax, gap in zip(axs,(0,1,15)):
        ax.set(xlim=(0,100), ylim=(100,0), aspect='equal', xlabel='Column', ylabel='Row')
        ax.axvspan(0,33,color='#e4ebed',label='Ignition zone')
        ax.axvspan(55,100,color='#d8e9d3',label='Protected region')
        bands=[(33,6)] if gap==0 else [(33,3),(36+gap,3)]
        for c,w in bands:ax.add_patch(Rectangle((c,0),w,100,facecolor='#d5a130'))
        ax.plot(15,50,'r*',ms=10)
        ax.set_title('Single: width 6' if gap==0 else f'Double: 3 + 3, gap {gap}')
    return fig


def area_figure(summary):
    fig,axs=plt.subplots(1,2,figsize=(10,4),sharey=True,layout='constrained')
    for ax,m in zip(axs,('M1','M2')):
        for layout,label,color in [('single','Single',BLUE),('gap_1','Double: gap 1',ORANGE),('gap_15','Double: gap 15','#52946c')]:
            y=[np.mean([s['total_fuel_burned'] for s in summary if s['group'].startswith(m+'_') and s['group'].endswith(f'_a{area}') and s['layout']==layout]) for area in (2,4,6)]
            ax.plot([2,4,6],y,'o-',label=label,color=color)
        ax.set(title=m,xlabel='Treated area (%)',xticks=[2,4,6]);ax.grid(alpha=.2)
    axs[0].set_ylabel('Mean fuel consumed by step 100 (model units)')
    axs[1].legend(fontsize=9)
    return fig


def gap_figure(pairs):
    lookup={(x['group'],x['layout']):x for x in pairs}
    winds=('none','E','S','W','N')
    matrices=[]
    for m in ('M1','M2'):
        matrices.append(np.array([[lookup[(f'{m}_{w}_a{a}',f'gap_{g}')]['total_fuel_burned']['mean'] for g in range(1,16)] for a in (2,4,6) for w in winds]))
    extent=max(abs(x).max() for x in matrices)
    fig,axs=plt.subplots(1,2,figsize=(11,6),layout='constrained')
    labels=[f'{a}% / {w}' for a in (2,4,6) for w in winds]
    for ax,m,z in zip(axs,('M1','M2'),matrices):
        im=ax.imshow(z,cmap='RdBu_r',vmin=-extent,vmax=extent,aspect='auto')
        ax.set(title=m,xlabel='Untreated gap (cells)',xticks=range(15),xticklabels=range(1,16),yticks=range(15),yticklabels=labels)
        for y in (4.5,9.5):ax.axhline(y,color='white',lw=2)
    fig.colorbar(im,ax=axs,label='Mean fuel difference: double − single (model units)',shrink=.85)
    return fig


def paired_figure(pairs, group='M1_none_a6'):
    fig,axs=plt.subplots(1,3,figsize=(12,5.5),sharey=True,layout='constrained')
    p={x['layout']:x for x in pairs if x['group']==group}
    for ax,field,label,scale in zip(axs,('total_fuel_burned','burned_cells','protected_fraction'),('Fuel consumed (model units)','Ever-ignited cells','Protected area (percentage points)'),(1,1,100)):
        for gap in range(1,16):
            v=p[f'gap_{gap}'][field];mean=v['mean']*scale
            ax.errorbar(mean,gap,xerr=np.array([[mean-v['low']*scale],[v['high']*scale-mean]]),fmt='o',color=ORANGE,ms=4,capsize=2)
        ax.axvline(0,color='black',lw=1);ax.grid(alpha=.2,axis='x');ax.set_xlabel(label)
    axs[0].set(yticks=range(1,16),ylabel='Double-band gap (cells)',ylim=(15.7,.3))
    fig.suptitle(f'{group}: double minus single; mean and pointwise 95% bootstrap CI')
    return fig


def curve_figure(summary, group='M1_none_a6', gap=6):
    lookup={(s['group'],s['layout']):s for s in summary}
    fig,axs=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for layout,label,color in [('single','Single',BLUE),(f'gap_{gap}',f'Double: gap {gap}',ORANGE)]:
        c=lookup[(group,layout)]['curve'];t=[p['step'] for p in c]
        for ax,field in zip(axs,('total_cells','new_cells')):
            y=np.array([p[field] for p in c]);sd=np.array([p[field+'_sd'] for p in c])
            ax.plot(t,y,label=label,color=color)
            ax.fill_between(t,np.maximum(0,y-sd),y+sd,color=color,alpha=.12)
    for ax,title in zip(axs,('Cumulative ever-ignited cells','Newly ignited cells per step')):
        ax.set(title=title,xlabel='Step',ylabel='Cells');ax.grid(alpha=.2);ax.legend()
    return fig


def saved_animation(root, output):
    """Render recorded states as GIF; no simulator call"""
    with gzip.open(root/'data/demo/animation_M1_none_a6.json.gz','rt') as f:runs=json.load(f)
    states=[np.zeros((100,100),dtype=np.uint8) for _ in runs];frames=[]
    for t in range(101):
        frame=Image.new('RGB',(820,455),'white');draw=ImageDraw.Draw(frame)
        draw.text((10,5),f'M1 / no wind / 6% / repeat 0 / step {t}',fill='black')
        for i,(run,state) in enumerate(zip(runs,states)):
            for v in run['frames'][t]:state.flat[abs(v)-1]=1 if v>0 else 2
            rgb=np.full((100,100,3),(60,111,78),dtype=np.uint8)
            for col,width in run['bands']:rgb[:,col:col+width]=(215,188,85)
            rgb.reshape(-1,3)[run['empty']]=(245,245,245)
            rgb[state==1]=(245,121,36);rgb[state==2]=(105,111,108)
            x=10+410*i
            frame.paste(Image.fromarray(rgb).resize((390,390),Image.Resampling.NEAREST),(x,48))
            draw.text((x,28),'Single wide band' if i==0 else 'Two narrow bands: gap 6',fill='black')
        frames.append(frame)
    frames[0].save(output,save_all=True,append_images=frames[1:],duration=120,loop=0)
    return output
