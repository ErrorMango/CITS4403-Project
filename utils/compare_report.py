"""Paired metrics, curves and heatmaps"""
import html
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from utils.metrics import measure
from utils.repeat_stats import summarize


def report(folder):
    config=json.loads((folder/'config.json').read_text())
    rows=json.loads((folder/'results.json').read_text())
    # Upgrade old output from its animation states; no model invocation.
    if any('curve' not in r for r in rows):
        rows=[]
        for g in config['groups']:
            s=(folder/'animations'/f'{g["id"]}.html').read_text()
            demos,_=json.JSONDecoder().raw_decode(s[s.index('const runs=')+11:])
            for d in demos:rows.append(dict(group=g['id'],layout=d['label'].split(' / ')[0],**measure(d)))
    raw=rows
    rows,pairs=summarize(raw)
    pair_lookup={(r['group'],r['layout']):r for r in pairs}
    lookup={(r['group'],r['layout']):r for r in rows}
    text='<!doctype html><meta charset="utf-8"><title>100-step band comparison</title><style>body{font:15px system-ui;margin:28px;color:#20362b;background:#f5f7f3}table{border-collapse:collapse;background:white}td,th{padding:8px;border-bottom:1px solid #ddd;white-space:nowrap}th{background:#e8eee8}iframe{width:100%;height:820px;border:0;background:white}select{padding:8px}canvas{width:100%;max-width:1000px;background:white}h2{margin-top:30px}</style><h1>100-step band comparison</h1>'
    maps_label=', '.join(dict.fromkeys(g['map'] for g in config['groups']))
    text+='<p>'+html.escape(maps_label)+', real terrain, 2/4/6%, wind toward none/E/S/W/N, repeated paired runs. All first bands start at column 33. Protected region: columns 55–99.</p><select id="group">'+''.join(f'<option value="{g["id"]}">{g["id"]} — first ignition {g["ignition"]}</option>' for g in config['groups'])+'</select><h2>Animation</h2><iframe id="animation" title="Animation"></iframe>'
    text+='<h2>Fire progression — selected group</h2><label>Compare single with <select id="gap">'+''.join(f'<option value="gap_{g}">Double gap {g}</option>' for g in range(1,16))+'</select></label><p>Blue: single. Orange: double. Shading: ±1 sample SD (clipped at zero), not a confidence interval. Contact lines are omitted because timing differs across repeats. Whole-map slowdown alone does not prove a band effect.</p><h3>Cumulative burned cells</h3><canvas id="total" width="1000" height="330"></canvas><h3>Newly ignited cells per step</h3><canvas id="new" width="1000" height="330"></canvas>'
    text+='<h2>Protected area difference — double minus single</h2><p>Percentage points. Blue: double protects more; orange: single protects more. Common colour scale across all panels. Mean paired difference per cell. Hover for a paired bootstrap 95% CI. These intervals are not corrected for multiple comparisons.</p>'
    differences=[100*(r['protected_fraction']-lookup[(r['group'],'single')]['protected_fraction']) for r in rows if r['layout']!='single'];extent=max(1,max(map(abs,differences)))
    for m in dict.fromkeys(g['map'] for g in config['groups']):
        for wind in ('none','E','S','W','N'):
            gs=[g for g in config['groups'] if g['map']==m and g['wind']==wind]
            if not gs:continue
            text+=f'<h3>{m} / {wind}</h3><svg viewBox="0 0 1020 180" role="img" aria-label="Protected area difference heatmap" style="width:100%;max-width:1100px;background:white">'
            for gap in range(1,16):text+=f'<text x="{90+(gap-1)*60}" y="22" text-anchor="middle">{gap}</text>'
            for i,g in enumerate(gs):
                text+=f'<text x="15" y="{57+i*40}">{g["area"]}%</text>'
                for gap in range(1,16):
                    v=100*(lookup[(g['id'],f'gap_{gap}')]['protected_fraction']-lookup[(g['id'],'single')]['protected_fraction'])
                    rgb='40,115,180' if v<0 else '218,130,40';alpha=.05+.7*abs(v)/extent
                    ci=pair_lookup[(g['id'],f'gap_{gap}')]['protected_fraction']
                    tip='95% CI unavailable' if ci['low'] is None else f"95% CI: {100*ci['low']:.2f} to {100*ci['high']:.2f} pp"
                    text+=f'<g><title>{tip}</title><rect x="{61+(gap-1)*60}" y="{32+i*40}" width="58" height="38" fill="rgba({rgb},{alpha})"/><text x="{90+(gap-1)*60}" y="{57+i*40}" text-anchor="middle">{v:+.1f}</text></g>'
            text+='<text x="480" y="175" text-anchor="middle">Gap (cells); rows = treated area</text></svg>'
    text+='<h2>Paired differences — selected group</h2><p>Double minus single. Negative favours double. Bootstrap 95% CIs resample matched repeats (2000 resamples); exploratory with ten repeats.</p><h3>Protected area difference (percentage points)</h3><canvas id="pair-protected" width="1000" height="510"></canvas><h3>Fuel loss difference</h3><canvas id="pair-fuel" width="1000" height="510"></canvas><h3>Burned cell difference</h3><canvas id="pair-cells" width="1000" height="510"></canvas>'
    text+='<p>Uncertainty includes random ignition and spread variation. Wind/area comparisons also change ignition; use within-group paired comparisons. Farther distance can reflect north/south spread, not barrier crossing.</p>'
    script=Path(__file__).with_name('compare_charts.js').read_text()
    text+='<script>'+script.replace('/*DATA*/',json.dumps(rows,separators=(',',':'))).replace('/*PAIRS*/',json.dumps(pairs,separators=(',',':')))+'</script>'
    (folder/'comparison.html').write_text(text)
    (folder/'metrics.json').write_text(json.dumps(raw,separators=(',',':')))
    (folder/'summary.json').write_text(json.dumps(rows,separators=(',',':')))
    (folder/'paired.json').write_text(json.dumps(pairs,separators=(',',':')))

if __name__=='__main__':report(Path(sys.argv[1]))
