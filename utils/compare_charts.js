// Offline paired charts
(()=>{
const data=/*DATA*/, pairs=/*PAIRS*/, $=id=>document.getElementById(id);
const fmt=v=>v===null?'N/A':Number(v).toFixed(2);
function plot(id,key,rows){
 const ctx=$(id).getContext('2d'),left=80,yTop=25,w=870,h=250;
 const high=Math.max(1,...rows.flatMap(r=>r.curve.map(x=>x[key]+(x[key+"_sd"]||0))))*1.05;
 const end=Math.max(1,...rows.flatMap(r=>r.curve.map(x=>x.step)));
 ctx.clearRect(0,0,1000,330);ctx.font='14px system-ui';ctx.setLineDash([]);
 for(let k=0;k<=5;k++){const y=yTop+h-k*h/5;ctx.strokeStyle='#ddd';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(left+w,y);ctx.stroke();ctx.fillStyle='#20362b';ctx.textAlign='right';ctx.fillText((high*k/5).toFixed(0),left-10,y+5);ctx.textAlign='center';ctx.fillText((end*k/5).toFixed(0),left+w*k/5,300);}
 ctx.fillText('Step',left+w/2,323);
 rows.forEach((r,i)=>{const color=['#2873b4','#d98228'][i];
 if(r.runs>1){ctx.fillStyle=color;ctx.globalAlpha=.15;ctx.beginPath();r.curve.forEach((p,j)=>{const x=left+p.step/end*w,y=yTop+h-(p[key]+p[key+'_sd'])/high*h;j?ctx.lineTo(x,y):ctx.moveTo(x,y);});[...r.curve].reverse().forEach(p=>ctx.lineTo(left+p.step/end*w,yTop+h-Math.max(0,p[key]-p[key+'_sd'])/high*h));ctx.closePath();ctx.fill();ctx.globalAlpha=1;}
 ctx.strokeStyle=color;ctx.lineWidth=2;ctx.setLineDash([]);ctx.beginPath();r.curve.forEach((p,j)=>{const x=left+p.step/end*w,y=yTop+h-p[key]/high*h;j?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();});
}
function charts(){const rs=data.filter(r=>r.group===$('group').value);plot('total','total_cells',[rs.find(r=>r.layout==='single'),rs.find(r=>r.layout===$('gap').value)]);plot('new','new_cells',[rs.find(r=>r.layout==='single'),rs.find(r=>r.layout===$('gap').value)]);}
// Dots are paired mean differences; whiskers are bootstrap CIs.
// Dots show paired means; whiskers show bootstrap confidence intervals.
function pairedPlot(id,key,scale=1){
 const rs=pairs.filter(r=>r.group===$('group').value),ctx=$(id).getContext('2d');
 const values=rs.flatMap(r=>[r[key].mean,r[key].low,r[key].high].filter(v=>v!==null).map(v=>v*scale));
 let lo=Math.min(0,...values),hi=Math.max(0,...values);const pad=Math.max(1,(hi-lo)*.08);lo-=pad;hi+=pad;
 const x=v=>130+(v-lo)/(hi-lo)*810;ctx.clearRect(0,0,1000,510);ctx.font='14px system-ui';ctx.setLineDash([]);
 for(let k=0;k<=5;k++){const v=lo+(hi-lo)*k/5;ctx.strokeStyle='#ddd';ctx.beginPath();ctx.moveTo(x(v),20);ctx.lineTo(x(v),460);ctx.stroke();ctx.fillStyle='#20362b';ctx.textAlign='center';ctx.fillText(v.toFixed(1),x(v),487);}
 ctx.strokeStyle='#555';ctx.setLineDash([4,4]);ctx.beginPath();ctx.moveTo(x(0),20);ctx.lineTo(x(0),460);ctx.stroke();ctx.setLineDash([]);
 rs.forEach((r,i)=>{const v=r[key],y=35+i*29;ctx.fillStyle='#20362b';ctx.textAlign='right';ctx.fillText(r.layout.replace('gap_','Gap '),115,y+5);ctx.strokeStyle=v.mean<0?'#2873b4':'#d98228';ctx.fillStyle=ctx.strokeStyle;ctx.lineWidth=2;if(v.low!==null){ctx.beginPath();ctx.moveTo(x(v.low*scale),y);ctx.lineTo(x(v.high*scale),y);ctx.stroke();}ctx.beginPath();ctx.arc(x(v.mean*scale),y,4,0,2*Math.PI);ctx.fill();});
}
function show(){const id=$('group').value;$('animation').src=`animations/${id}.html`;charts();pairedPlot('pair-protected','protected_fraction',100);pairedPlot('pair-fuel','total_fuel_burned');pairedPlot('pair-cells','burned_cells');}

$('group').onchange=show;$('gap').onchange=charts;show();
})();
