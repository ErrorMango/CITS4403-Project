import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path

WINDS = {'none': (0, 0), 'E': (0, 1), 'W': (0, -1), 'N': (-1, 0), 'S': (1, 0)}

# Calculate the probability of igniting a neighboring cell in the current step for a burning cell.
# 计算正在燃烧格子的邻格燃烧概率
def spread_chance(target_fuel, dr, dc, p0=.55, wind='E', wind_strength=.5,
                  height_difference=0., slope_strength=1.):
    wr, wc = WINDS[wind]
    distance = math.hypot(dr, dc)
    if distance == 0:
        raise ValueError('Spread needs two different cells')
    # Wind vectors have unit length; none uses (0, 0), giving factor 1.
    cosine = (dr*wr + dc*wc) / distance
    factor = math.exp(wind_strength * cosine)
    # Height and horizontal cell width share model length units (cell width = 1).
    # Positive height difference means the target is uphill. Angle is in radians.
    slope_angle = math.atan2(height_difference, distance)
    base = p0 * target_fuel * factor / distance
    if base <= 0:
        return 0.
    exponent = slope_strength * slope_angle
    # Clip before exp for very large positive exponents; flat terrain keeps the V1 calculation.
    if exponent > 0 and exponent >= -math.log(base):
        return 1.
    return min(1., base * math.exp(exponent))

# The terrain of the entire map is generated, with the main parameter being slope.
# 生成地形，目前只有坡度参数
def terrain_grid(n, slope_angle=10.):
    """Planar ground rising eastward; degrees in, model-length heights out."""
    if not math.isfinite(slope_angle) or not 0 <= slope_angle < 90:
        raise ValueError('slope-angle must be finite and in [0,90) degrees')
    rise = math.tan(math.radians(slope_angle))
    return [[c * rise for c in range(n)] for _ in range(n)]

# Define the position offsets of the eight neighbors around each cell.
# 定义每个格子周围八个格子的位置偏移
NEIGHBOURS = [(dr, dc) for dr in (-1, 0, 1)
              for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]

# Determining which cells on the map need to undergo fuel reduction treatment.
# 选择地图上哪些格子需要进行减燃料处理
def treatment_mask(n, layout, fraction, seed):
    """Select exactly round(n*n*fraction) cells. Strips remain vertical."""
    if n < 10 or not 0 <= fraction <= 1:
        raise ValueError('size >= 10; treatment fraction in [0,1] required')
    if layout not in ('untreated', 'strips', 'spaced'):
        raise ValueError('Unknown layout')
    k = 0 if layout == 'untreated' else round(n*n*fraction)
    # seed is retained for API compatibility; these layouts are deterministic.
    if k == 0:
        return [[False]*n for _ in range(n)]
    if layout == 'strips':
        # Alternate equal-width layers between two separate vertical bands.
        # If k is not divisible by 2*n, the last layer has partial columns.
        centres = (n // 3, 2*n // 3)
        left = sorted(range(n//2), key=lambda c: (abs(c-centres[0]), c))
        right = sorted(range(n//2,n), key=lambda c: (abs(c-centres[1]), c))
        order = []
        for depth in range(max(len(left),len(right))):
            for r in range(n):
                if depth < len(left): order.append((r,left[depth]))
                if depth < len(right): order.append((r,right[depth]))
    else:
        # Compact tiles for the spaced layout.
        # A tile side scales with grid size; edge tiles may be smaller.
        b = max(2, n // 20)
        blocks = [(r,c) for r in range(0,n,b) for c in range(0,n,b)]
        # First choose separated checkerboard tiles, then fill other tiles if needed.
        blocks.sort(key=lambda x: ((x[0]//b + x[1]//b) % 2, x[1], x[0]))
        first = [x for x in blocks if (x[0]//b+x[1]//b)%2 == 0]
        second = [x for x in blocks if x not in set(first)]
        # Spatially spread selections deterministically, rather than filling one edge.
        def spread(items):
            out=[]
            while items:
                if not out: idx=len(items)//2
                else: idx=max(range(len(items)), key=lambda i:min((items[i][0]-a)**2+(items[i][1]-b_)**2 for a,b_ in out))
                out.append(items.pop(idx))
            return out
        blocks = spread(first) + spread(second)
        order = [(rr,cc) for r,c in blocks for rr in range(r,min(r+b,n)) for cc in range(c,min(c+b,n))]
    chosen=set(order[:k])
    return [[(r,c) in chosen for c in range(n)] for r in range(n)]

# For a specific processing layout, a simulation of a wildfire process from the onset of fire to the completion at a specified number of steps is carried out, and all data related to this process are returned.
# 针对一种处理布局，完成一次从起火到指定步数结束的山火模拟，并返回全过程数据
def simulate(n=100, steps=100, layout='strips', fraction=.04, residual=.2,
             p0=.55, consumption=.2, seed=7, map_seed=10, fuel_seed=42, ignition=None, wind='E', wind_strength=.5,
             slope_angle=10., slope_strength=1.):
    if steps<1 or consumption<=0 or not 0<=p0<=1 or not 0<=residual<=1:
        raise ValueError('Invalid parameters')
    if wind not in WINDS or not math.isfinite(wind_strength) or wind_strength<0:
        raise ValueError('Invalid wind settings')
    if not math.isfinite(slope_strength) or slope_strength < 0:
        raise ValueError('slope-strength must be finite and nonnegative')
    height_grid=terrain_grid(n,slope_angle)
    mask=treatment_mask(n,layout,fraction,map_seed)
    rng=random.Random(fuel_seed)
    original_grid=[[rng.choice((.5,1.,1.5)) for _ in range(n)] for _ in range(n)]
    fuel=[[original_grid[r][c]*(residual if mask[r][c] else 1.) for c in range(n)] for r in range(n)]
    initial_grid=[row[:] for row in fuel]
    state=[[0]*n for _ in range(n)]
    ignition=ignition or (n//2,n//2)
    r,c=ignition
    if not (0<=r<n and 0<=c<n): raise ValueError('Ignition outside grid')
    if fuel[r][c]>0: state[r][c]=1
    initial=sum(map(sum,fuel)); original=sum(map(sum,original_grid))
    cumulative=0.; history=[]; snapshots=[]
    def record(t,loss,new_cells):
        remaining=sum(map(sum,fuel))
        unignited=sum(fuel[r][c] for r in range(n) for c in range(n) if state[r][c]==0)
        burned=sum(v==2 for row in state for v in row)
        burning=sum(v==1 for row in state for v in row)
        history.append(dict(step=t,remaining_fuel=remaining,unignited_fuel=unignited,
            remaining_fraction=remaining/initial if initial else 0,
            cumulative_burnt_fuel=cumulative,new_burnt_fuel=loss,
            average_burn_rate=cumulative/t if t else 0,new_burnt_cells=new_cells,
            cumulative_burnt_cells=burned,burning_cells=burning,
            unignited_cells=n*n-burned-burning))
        snapshots.append([row[:] for row in state])
    record(0,0.,0)
    for t in range(1,steps+1):
        survival={}; new=[row[:] for row in state]; loss=0.; completed=0
        for r in range(n):
            for c in range(n):
                if state[r][c]!=1: continue
                # Every cell burning at the start of this step attempts spread,
                # including its final burning step. New ignitions wait until next step.
                for dr,dc in NEIGHBOURS:
                    rr,cc=r+dr,c+dc
                    if not (0<=rr<n and 0<=cc<n) or state[rr][cc]!=0: continue
                    p=spread_chance(fuel[rr][cc],dr,dc,p0,wind,wind_strength,
                        height_grid[rr][cc]-height_grid[r][c],slope_strength)
                    survival[rr,cc]=survival.get((rr,cc),1.)*(1-p)
                used=min(fuel[r][c],consumption); fuel[r][c]-=used;loss+=used
                if fuel[r][c]<1e-12: fuel[r][c]=0.;new[r][c]=2;completed+=1
        rng=random.Random(seed*1000003+t)
        for r in range(n):
            for c in range(n):
                u=rng.random()
                if u<1-survival.get((r,c),1.): new[r][c]=1
        state=new;cumulative+=loss;record(t,loss,completed)
    return dict(config=dict(n=n,steps=steps,layout=layout,fraction=fraction,residual=residual,
        p0=p0,consumption=consumption,seed=seed,map_seed=map_seed,fuel_seed=fuel_seed,
        ignition=ignition,wind=wind,wind_strength=wind_strength,
        slope_angle=slope_angle,slope_strength=slope_strength,uphill_direction='E',
        cell_width=1.,slope_angle_unit='radians internally; degrees input',
        neighbourhood='eight',distance_rule='inverse_distance',model_version='v1_eight_100_slope'),original_fuel=original,initial_fuel=initial,
        treatment_removed=original-initial,treated_cells=sum(map(sum,mask)),mask=mask,
        original_grid=original_grid,initial_grid=initial_grid,final_grid=fuel,height_grid=height_grid,
        history=history,snapshots=snapshots)

# Save a set of dictionary data as a CSV file with headers.
# 把一组字典数据保存成带表头的CSV文件
def write_csv(path, rows):
    with open(path,'w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)

# Summarize all the repeated simulation results, calculate the mean value and standard deviation, as well as the paired differences between bands and interband patches.
# 把所有重复模拟的结果汇总，计算平均值、标准差，以及条带与间隔斑块之间的配对差值
def summarize_runs(summaries, histories):
    """Summarize repeats without retaining their large map snapshots.

    Paired differences use repeat IDs, not row ordering. SD is sample SD.
    """
    def stats(values):
        return statistics.mean(values), statistics.stdev(values) if len(values)>1 else None
    aggregate=[]; curves=[]
    for layout in ('untreated','strips','spaced'):
        rows=[r for r in summaries if r['layout']==layout]
        if not rows: raise ValueError('Missing layout: '+layout)
        item=dict(layout=layout,runs=len(rows))
        metrics={
            'fuel_burned':[r['cumulative_burnt_fuel'] for r in rows],
            'fuel_left':[r['remaining_fuel'] for r in rows],
            'fuel_removed':[r['treatment_removed'] for r in rows],
            'ignited_fraction':[(r['burning_cells']+r['cumulative_burnt_cells'])/(r['n']**2) for r in rows]}
        for key,values in metrics.items():
            item['mean_'+key],item['sd_'+key]=stats(values)
        aggregate.append(item)
        runs=histories[layout]
        if len(runs)!=len(rows) or len({len(h) for h in runs})!=1:
            raise ValueError('History lengths or repeat counts do not match')
        for t in range(len(runs[0])):
            if any(h[t]['step']!=t for h in runs): raise ValueError('Unaligned history steps')
            mean,sd=stats([h[t]['new_burnt_fuel'] for h in runs])
            curves.append(dict(layout=layout,step=t,runs=len(runs),mean_rate=mean,sd_rate=sd))
    paired={}
    for r in summaries:
        rep=paired.setdefault(r['repeat'],{})
        if r['layout'] in rep: raise ValueError('Duplicate repeat/layout')
        rep[r['layout']]=r
    differences=[]
    for rep,group in sorted(paired.items()):
        a,b=group['strips'],group['spaced']
        for key in ('seed','fuel_seed','ignition','n','steps','p0','fraction','residual',
                    'wind','wind_strength','consumption','slope_angle','slope_strength'):
            if a[key]!=b[key]: raise ValueError('Unmatched pair: '+key)
        differences.append(dict(repeat=rep,seed=a['seed'],
            strips_fuel_burned=a['cumulative_burnt_fuel'],
            spaced_fuel_burned=b['cumulative_burnt_fuel'],
            difference=a['cumulative_burnt_fuel']-b['cumulative_burnt_fuel']))
    values=[r['difference'] for r in differences]
    mean,sd=stats(values)
    pair_stats=dict(pairs=len(values),mean_difference=mean,sd_difference=sd,
        strips_lower=sum(x < -1e-9 for x in values),spaced_lower=sum(x > 1e-9 for x in values),
        ties=sum(abs(x)<=1e-9 for x in values))
    return dict(aggregate=aggregate,curves=curves,pairs=differences,pair_stats=pair_stats)

# Generate the pre-calculated simulation results and statistical data into a comparison.html file that can be opened in a browser.
# 把已经算好的模拟结果和统计数据，生成可在浏览器打开的comparison.htm
def report(results,path,analysis):
    data=json.dumps(results)
    html='''<!doctype html><meta charset="utf-8"><title>Bushfire CA — first model</title>
<style>body{font:16px system-ui;max-width:1250px;margin:32px auto;background:#f6f7f3;color:#20362b}h1{margin-bottom:8px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.card{background:white;padding:20px;border-radius:14px}canvas{width:100%;image-rendering:pixelated}input{width:65%}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px;border-bottom:1px solid #ddd;text-align:left}.note{color:#53645a}button{padding:8px 18px}.rate-chart{image-rendering:auto}.card{margin-bottom:16px}#legend{display:flex;gap:24px;flex-wrap:wrap;margin:14px 0}#legend span{display:inline-flex;align-items:center;gap:8px}#legend i{width:24px;height:4px;display:inline-block}@media(max-width:900px){.grid{grid-template-columns:1fr}}</style>
<h1>Bushfire V1</h1><p>Fixed wind. Planar terrain; uphill direction is east (right) when slope is nonzero. Eight nearby cells. No spotting. This is a simple model, not a real fire forecast.</p>
<p>Green: Unburned | Yellow: Treated | Orange: Burning | Grey: Burned</p>
<button id="play">Play / Pause</button> <input id="time" type="range" min="0" value="0"><b id="label"></b>
<div class="grid" id="cards"></div>
<h2>Rate Comparison</h2><p>Three groups, one scale per chart. First run only. Dashed line: selected step.</p>
<div id="legend"></div>
<section class="card"><h2>Fuel Burned per Step</h2><canvas class="rate-chart" id="step-rate" width="1200" height="380"></canvas></section>
<section class="card"><h2>Mean Fuel Burned per Step</h2><p>Total fuel burned / elapsed steps. This is not the mean across repeated runs.</p><canvas class="rate-chart" id="mean-rate" width="1200" height="380"></canvas></section>
<p class="note">Fuel Left includes fuel still in burning cells. Fuel Removed is separate from Fuel Burned. Mean Rate = total fuel burned / steps. Maps and charts above show the first run only. The sections below summarize all repeats.</p>
<section class="card"><h2>Average Fuel Burned per Step — Across Runs</h2><p>Lines: repeat means at each step. Shading: +/- 1 sample SD (lower edge clipped at zero), not a confidence interval. No shading for a single run.</p><div id="all-legend"></div><canvas class="rate-chart" id="average-runs" width="1200" height="420"></canvas></section>
<section class="card"><h2>Paired Fuel Loss Difference</h2><p>Each bar compares the same repeat: Strips minus Spaced Patches. Negative: Strips lost less fuel. Positive: Spaced Patches lost less fuel. Dashed line: mean difference.</p><p id="pair-stats"></p><canvas class="rate-chart" id="paired-runs" width="1200" height="420"></canvas></section>
<script>const analysis=ANALYSIS;const results=DATA;const names={untreated:'No Treatment',strips:'Strips',spaced:'Spaced Patches'};
document.querySelector('h1').insertAdjacentHTML('afterend', `<p>Wind toward: ${results[0].config.wind} | Wind strength: ${results[0].config.wind_strength} | Slope: ${results[0].config.slope_angle} degrees uphill toward E | Slope strength: ${results[0].config.slope_strength} | Grid: ${results[0].config.n} x ${results[0].config.n} | Steps: ${results[0].config.steps} | Treated area: ${(100*results[1].treated_cells/(results[1].config.n**2)).toFixed(1)}% | Fuel kept: ${results[0].config.residual*100}% | Fuel used per burning cell per step: ${results[0].config.consumption}</p>`);
const slider=document.querySelector('#time'); slider.max=results[0].config.steps;
document.querySelector('#cards').innerHTML=results.map((r,i)=>`<section class="card"><h2>${names[r.config.layout]}</h2><canvas id="c${i}" width="400" height="400"></canvas><p id="m${i}"></p></section>`).join('');
function draw(){let t=+slider.value;document.querySelector('#label').textContent=`Step ${t}`;results.forEach((r,i)=>{let n=r.config.n,ctx=document.querySelector('#c'+i).getContext('2d'),s=400/n;for(let a=0;a<n;a++)for(let b=0;b<n;b++){let v=r.snapshots[t][a][b];ctx.fillStyle=v===2?'#69736d':v===1?'#ef782e':r.mask[a][b]?'#d4c779':'#39734e';ctx.fillRect(b*s,a*s,s,s)}let h=r.history[t];document.querySelector('#m'+i).textContent=`Fuel Left ${h.remaining_fuel.toFixed(1)} | Fuel Burned ${h.cumulative_burnt_fuel.toFixed(1)} | Burning Cells ${h.burning_cells}`;
})
 drawRateChart('step-rate','new_burnt_fuel',t);
 drawRateChart('mean-rate','average_burn_rate',t);
}
const lineColors={untreated:'#222222',strips:'#0072B2',spaced:'#009E73'};
const lineDashes={untreated:[],strips:[10,4],spaced:[12,4,3,4]};
document.querySelector('#legend').innerHTML=results.map(r=>`<span><i style="background:${lineColors[r.config.layout]}"></i>${names[r.config.layout]}</span>`).join('');
function drawRateChart(id,key,t){
 const ctx=document.getElementById(id).getContext('2d');
 const left=85,top=35,width=1080,height=280;
 const end=Math.max(...results.map(r=>r.config.steps));
 const max=Math.max(1,...results.flatMap(r=>r.history.map(h=>h[key])))*1.05;
 ctx.clearRect(0,0,1200,380);ctx.font='16px system-ui';ctx.lineWidth=1;
 ctx.fillStyle='#33443b';ctx.textAlign='left';ctx.fillText('Fuel units / step',left,20);
 for(let k=0;k<=5;k++){
  let y=top+height-k*height/5;
  ctx.strokeStyle='#e0e6e1';ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(left+width,y);ctx.stroke();
  ctx.fillStyle='#33443b';ctx.textAlign='right';ctx.fillText((max*k/5).toFixed(1),left-10,y+5);
  let x=left+k*width/5;ctx.textAlign='center';ctx.fillText((end*k/5).toFixed(0),x,top+height+26);
 }
 ctx.fillText('Step',left+width/2,365);
 results.forEach(r=>{
  ctx.strokeStyle=lineColors[r.config.layout];ctx.lineWidth=2.5;ctx.setLineDash(lineDashes[r.config.layout]);ctx.beginPath();
  r.history.forEach((h,j)=>{const x=left+h.step/end*width,y=top+height-h[key]/max*height;j?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke();
 });
 ctx.setLineDash([5,5]);ctx.lineWidth=1;ctx.strokeStyle='#737d76';ctx.beginPath();ctx.moveTo(left+t/end*width,top);ctx.lineTo(left+t/end*width,top+height);ctx.stroke();ctx.setLineDash([]);
}

const number=(v,d=2)=>v===null?'N/A':Number(v).toFixed(d);
document.querySelector('#all-legend').innerHTML=analysis.aggregate.map(a=>`<span style="display:inline-block;margin-right:20px;color:${lineColors[a.layout]}">${names[a.layout]}</span>`).join('');
function statsAxes(ctx,low,high,xLabel,units){
 const left=100,top=40,w=1060,h=290;
 ctx.clearRect(0,0,1200,420);ctx.font='16px system-ui';ctx.lineWidth=1;ctx.setLineDash([]);
 ctx.fillStyle='#33443b';ctx.textAlign='left';ctx.fillText(units,left,22);
 for(let k=0;k<=5;k++){let y=top+h-k*h/5;ctx.strokeStyle='#e0e6e1';ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(left+w,y);ctx.stroke();ctx.textAlign='right';ctx.fillText(number(low+(high-low)*k/5,1),left-10,y+5)}
 ctx.textAlign='center';ctx.fillText(xLabel,left+w/2,402);
 return {left,top,w,h,y:v=>top+h-(v-low)/(high-low)*h};
}
function drawAverageRuns(){
 const ctx=document.getElementById('average-runs').getContext('2d');let high=1;
 for(const c of analysis.curves)high=Math.max(high,c.mean_rate+(c.sd_rate===null?0:c.sd_rate));
 const axis=statsAxes(ctx,0,high*1.05,'Step','Fuel units / step');
 const end=results[0].config.steps,x=t=>axis.left+t/end*axis.w;
 for(let k=0;k<=5;k++)ctx.fillText(number(end*k/5,0),x(end*k/5),axis.top+axis.h+26);
 for(const a of analysis.aggregate){
  const rows=analysis.curves.filter(c=>c.layout===a.layout);
  if(a.runs>1){ctx.fillStyle=lineColors[a.layout];ctx.globalAlpha=.13;ctx.beginPath();
   rows.forEach((r,i)=>{let xx=x(r.step),yy=axis.y(r.mean_rate+r.sd_rate);i?ctx.lineTo(xx,yy):ctx.moveTo(xx,yy)});
   [...rows].reverse().forEach(r=>ctx.lineTo(x(r.step),axis.y(Math.max(0,r.mean_rate-r.sd_rate))));ctx.closePath();ctx.fill();ctx.globalAlpha=1;}
 }
 for(const a of analysis.aggregate){const rows=analysis.curves.filter(c=>c.layout===a.layout);
  ctx.strokeStyle=lineColors[a.layout];ctx.lineWidth=2.5;ctx.setLineDash(lineDashes[a.layout]);ctx.beginPath();
  rows.forEach((r,i)=>{let xx=x(r.step),yy=axis.y(r.mean_rate);i?ctx.lineTo(xx,yy):ctx.moveTo(xx,yy)});ctx.stroke();}
 ctx.setLineDash([]);
}
function drawPairedRuns(){
 const p=analysis.pair_stats;
 document.querySelector('#pair-stats').textContent=`Pairs: ${p.pairs} | Mean difference: ${number(p.mean_difference)} | SD: ${number(p.sd_difference)} | Strips lower: ${p.strips_lower} | Spaced lower: ${p.spaced_lower} | Ties: ${p.ties}`;
 const ctx=document.getElementById('paired-runs').getContext('2d');let extent=1;
 for(const r of analysis.pairs)extent=Math.max(extent,Math.abs(r.difference));extent*=1.1;
 const a=statsAxes(ctx,-extent,extent,'Repeat (starting at 1)','Fuel difference (units)');
 const slot=a.w/analysis.pairs.length;
 analysis.pairs.forEach((r,i)=>{let x=a.left+(i+.5)*slot,y=a.y(r.difference),zero=a.y(0);
  ctx.fillStyle=r.difference<0?lineColors.strips:lineColors.spaced;ctx.fillRect(x-slot*.3,Math.min(y,zero),slot*.6,Math.abs(y-zero));
  if(Math.abs(r.difference)<1e-9){ctx.fillStyle='#555';ctx.fillRect(x-2,zero-2,4,4)}
  if(analysis.pairs.length<=25||i%Math.ceil(analysis.pairs.length/20)===0){ctx.fillStyle='#33443b';ctx.fillText(String(r.repeat+1),x,a.top+a.h+26)}
 });
 ctx.lineWidth=1.5;ctx.strokeStyle='#555';ctx.beginPath();ctx.moveTo(a.left,a.y(0));ctx.lineTo(a.left+a.w,a.y(0));ctx.stroke();
 ctx.setLineDash([8,5]);ctx.strokeStyle='#9c3c68';ctx.beginPath();ctx.moveTo(a.left,a.y(p.mean_difference));ctx.lineTo(a.left+a.w,a.y(p.mean_difference));ctx.stroke();ctx.setLineDash([]);
}
drawAverageRuns();drawPairedRuns();

slider.oninput=draw;let timer;document.querySelector('#play').onclick=()=>{if(timer){clearInterval(timer);timer=null}else timer=setInterval(()=>{slider.value=(+slider.value+1)%(+slider.max+1);draw()},150)};draw();</script>'''
    path.write_text(html.replace('ANALYSIS',json.dumps(analysis,allow_nan=False)).replace('DATA',data),encoding='utf-8')

# Read the input parameters, schedule the simulation, save the results, and finally generate a comparison web page.
# 读取输入的参数，安排模拟，保存结果，最后生成 comparison 网页
def main():
    p=argparse.ArgumentParser(description='Wind CA with random fuel and gradual consumption')
    p.add_argument('--size',type=int,default=100);p.add_argument('--steps',type=int,default=100)
    p.add_argument('--fraction',type=float,default=.04);p.add_argument('--residual',type=float,default=.2)
    p.add_argument('--consumption',type=float,default=.2);p.add_argument('--p0',type=float,default=.55)
    p.add_argument('--seed',type=int,default=7);p.add_argument('--map-seed',type=int,default=10,help='Legacy option; current layouts are deterministic')
    p.add_argument('--fuel-seed',type=int,default=42);p.add_argument('--repeats',type=int,default=1)
    p.add_argument('--wind',choices=WINDS,default='E',help='Direction the wind blows toward; none for no wind')
    p.add_argument('--wind-strength',type=float,default=.5,help='Model coefficient, not a measured wind speed')
    p.add_argument('--slope-angle',type=float,default=10.,help='Eastward uphill angle in degrees; 0 restores flat ground')
    p.add_argument('--slope-strength',type=float,default=1.,help='Uncalibrated coefficient applied to slope angles in radians; 0 disables slope effect')
    p.add_argument('--out',type=Path,default=Path(__file__).parent.parent/'modelv1')
    a=p.parse_args()
    if a.repeats<1:p.error('repeats >= 1 required')
    if not math.isfinite(a.slope_angle) or not 0 <= a.slope_angle < 90:
        p.error('slope-angle must be finite and in [0,90) degrees')
    if not math.isfinite(a.slope_strength) or a.slope_strength < 0:
        p.error('slope-strength must be finite and nonnegative')
    a.out.mkdir(parents=True,exist_ok=True);summaries=[];demos=[];histories={l:[] for l in ('untreated','strips','spaced')}
    for rep in range(a.repeats):
        layouts=('untreated','strips','spaced')
        masks=[treatment_mask(a.size,l,a.fraction,a.map_seed+rep) for l in layouts]
        eligible=[(r,c) for r in range(a.size) for c in range(a.size) if not any(m[r][c] for m in masks)]
        if not eligible:p.error('No shared untreated ignition; reduce treatment fraction')
        ignition=random.Random(a.seed+rep).choice(eligible)
        for layout in layouts:
            r=simulate(a.size,a.steps,layout,a.fraction,a.residual,a.p0,a.consumption,
                a.seed+rep,a.map_seed+rep,a.fuel_seed+rep,ignition,a.wind,a.wind_strength,a.slope_angle,a.slope_strength)
            stem=f'{layout}_{rep:03d}'
            write_csv(a.out/(stem+'.csv'),r['history'])
            (a.out/(stem+'_config.json')).write_text(json.dumps(r['config'],indent=2))
            for key in ('original_grid','initial_grid','final_grid','mask','height_grid'):
                with (a.out/(stem+'_'+key+'.csv')).open('w',newline='') as f:csv.writer(f).writerows(r[key])
            histories[layout].append(r['history'])
            summaries.append(dict(**r['config'],repeat=rep,treated_cells=r['treated_cells'],original_fuel=r['original_fuel'],
                initial_fuel=r['initial_fuel'],treatment_removed=r['treatment_removed'],**r['history'][-1]))
            if rep==0:demos.append(r)
    analysis=summarize_runs(summaries,histories)
    write_csv(a.out/'summary.csv',summaries)
    write_csv(a.out/'aggregate.csv',analysis['aggregate'])
    write_csv(a.out/'mean_curve.csv',analysis['curves'])
    write_csv(a.out/'paired_differences.csv',analysis['pairs'])
    report(demos,a.out/'comparison.html',analysis)
    print(f'Saved {len(summaries)} runs to {a.out.resolve()}')
if __name__=='__main__':main()
