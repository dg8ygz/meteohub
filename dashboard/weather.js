'use strict';
const $=s=>document.querySelector(s),NS='http://www.w3.org/2000/svg';
let data=null,range='24h',selected='',busy=false,lastFetch=0,chartMetric=null,selection=0,fetchFailed=false,freshnessKey='';
const format=(v,d=1)=>v==null?'—':Number(v).toLocaleString('de-DE',{maximumFractionDigits:d,minimumFractionDigits:d});
const clock=t=>new Date(t*1000).toLocaleTimeString('de-DE',{timeZone:'Europe/Berlin',hour:'2-digit',minute:'2-digit'});
const date=t=>new Date(t*1000).toLocaleDateString('de-DE',{timeZone:'Europe/Berlin',day:'2-digit',month:'2-digit'});
const age=t=>t<0?'Zeitabweichung':t<60?`${Math.floor(t)} s`:t<3600?`${Math.floor(t/60)} min`:`${Math.floor(t/3600)} h`;
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function pick(field,preferred=[]){if(!data)return null;const rows=data.metrics.filter(m=>m.field===field);return preferred.map(id=>rows.find(m=>m.sensor===id)).find(Boolean)||rows.sort((a,b)=>b.ts-a.ts)[0]||null;}
function label(m){const extra={t2:'Außen',t1:'Zusatzsensor',thb0:'Kombisensor',wind0:'Windmesser',sol0:'Solar',uv0:'UV'};return `${m.label} · ${extra[m.sensor]||m.sensor}`;}
function elapsed(m){return m?Date.now()/1000-m.ts:Infinity;}
function fresh(m){return m&&elapsed(m)<(m.max_age||180)&&elapsed(m)>=-5;}
function svgEl(name,attrs={},text){let e=document.createElementNS(NS,name);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;}
function card(title,symbol,m,opts={}){
 const stale=m&&!fresh(m);const value=m&&!stale?m.value:null,unit=m?m.unit:(opts.unit||'');
 let foot=m?`<span class="${stale?'stale':''}">${stale?'Veraltet · ':''}vor ${age(elapsed(m))}</span>`:'<span>Keine Messung verfügbar</span>';
 if(stale)foot+=`<span>Zuletzt ${format(m.value)} ${escape(unit)}</span>`;
 if(m&&m.today.count)foot+=`<span>Heute ${format(m.today.min)} / ${format(m.today.max)} ${escape(unit)}</span>`;
 if(opts.secondary)foot+=`<span>${escape(opts.secondary)}</span>`;
 return `<article class="card ${opts.primary?'primary':''}"><div class="card-head"><span>${escape(title)}</span><span class="card-symbol" aria-hidden="true">${symbol}</span></div><div class="reading">${format(value,opts.decimals??1)}<span class="unit">${escape(unit)}</span></div><div class="card-foot">${foot}</div></article>`;
}
function render(){
 freshnessKey=data.metrics.map(m=>m.id+':'+Boolean(fresh(m))).join('|');
 const t=pick('temperature',['t2','th0']),w=pick('speed',['wind0']),g=pick('gust',['wind0']),p=pick('sea_pressure',['thb0'])||pick('pressure',['thb0']),r=pick('rain_rate',['rain0']),s=pick('solar',['sol0']),u=pick('uv',['uv0']);
 $('#cards').innerHTML=card('Außentemperatur','°',t,{primary:true})+card('Windgeschwindigkeit','↗',w,{secondary:g?`Böen ${format(g.value)} ${g.unit}`:''})+card(p?.field==='pressure'?'Stationsluftdruck':'Luftdruck','◎',p,{unit:'hPa'})+card('Regenrate','☂',r,{unit:'mm/h'})+card('Solarstrahlung','☼',s,{decimals:0,unit:'W/m²'})+card('UV-Index','◇',u,{unit:''});
 const opts=data.metrics.filter(m=>m.field!=='direction'&&m.field!=='rain_total');
 if(!opts.some(m=>m.id===selected))selected=t?.id||opts[0]?.id||'';
 const select=$('#metric');select.replaceChildren();for(const m of opts){let o=document.createElement('option');o.value=m.id;o.textContent=label(m);select.append(o);}select.value=selected;
 const dir=pick('direction',['wind0']);const names=['N','NNO','NO','ONO','O','OSO','SO','SSO','S','SSW','SW','WSW','W','WNW','NW','NNW'];

 $('#windDirection').textContent=fresh(dir)?`${names[Math.round(dir.value/22.5)%16]} · ${format(dir.value,0)}°`:'—';
 $('#windDetail').textContent=fresh(dir)?`Messung von ${clock(dir.ts)} Uhr`:dir?`Letzte Messung vor ${age(elapsed(dir))}`:'Keine aktuelle Windmessung';
 const sensors=new Map();for(const m of data.metrics){if(!sensors.has(m.sensor)||sensors.get(m.sensor).ts<m.ts)sensors.set(m.sensor,m);}
 $('#sensors').innerHTML=[...sensors.values()].map(m=>`<div class="sensor-row"><span class="sensor-dot ${fresh(m)?'':'stale'}"></span><div>${escape(m.sensor)}<small>${fresh(m)?'vor ':'Veraltet · '}${age(elapsed(m))}</small></div></div>`).join('')||'<p>Noch keine Sensordaten</p>';
 updateStatus();draw();drawWind();
}
function updateStatus(){
 $('#date').textContent=new Date().toLocaleDateString('de-DE',{timeZone:'Europe/Berlin',weekday:'long',day:'numeric',month:'long',year:'numeric'});
 if(!data)return;
 const current=data.metrics.filter(fresh),indexAge=Date.now()/1000-(data.index.last_success||0),networkAge=(Date.now()-lastFetch)/1000;
 const good=current.length>0&&indexAge<60&&networkAge<45&&!fetchFailed&&!data.index.error;
 $('#connection').textContent=good?'Stationsdaten aktuell':'Daten nicht aktuell';$('#connection').classList.toggle('stale',!good);
 $('#updated').textContent=`Abgerufen ${clock(lastFetch/1000)} Uhr`;
 $('#notice').textContent=fetchFailed||networkAge>45?'Die Verbindung zur Wetterstation ist unterbrochen. Angezeigte Messwerte werden nicht aktualisiert.':data.index.error||indexAge>=60?'Die Aufbereitung der Messdaten ist verzögert. Die Anzeige kann veraltet sein.':!current.length?'Zurzeit liegen keine aktuellen Sensormessungen vor.':data.index.history_importing?'Ältere Messwerte werden noch eingelesen. Historische Verläufe und Tagesextrema sind bis dahin unvollständig.':'';
}
function drawWind(){
 const host=$('#windRadar');host.replaceChildren();const values=data?.wind_vector||[];
 $('#windPeriod').textContent=range==='1h'?'1 Stunde':range==='24h'?'24 Stunden':range==='7d'?'7 Tage':'30 Tage';
 if(!values.length){host.innerHTML='<div class="chart-empty">Keine Windmessungen im Zeitraum</div>';return;}
 const names=['N','NO','O','SO','S','SW','W','NW'],W=280,H=190,cx=140,cy=94,radius=68,max=Math.max(5,Math.ceil(Math.max(...values.map(v=>v[2]))/5)*5),sectors=new Map(values.map(v=>[v[0],v]));
 const point=(i,value,extra=0)=>[cx+Math.sin(i*Math.PI/4)*(radius*value/max+extra),cy-Math.cos(i*Math.PI/4)*(radius*value/max+extra)];
 const svg=svgEl('svg',{viewBox:`0 0 ${W} ${H}`});
 for(let j=1;j<=4;j++){let coords=names.map((_,i)=>point(i,max*j/4).join(',')).join(' ');svg.append(svgEl('polygon',{points:coords,class:'radar-grid'}));}
 names.forEach((name,i)=>{let pt=point(i,max),text=point(i,max,14);svg.append(svgEl('path',{d:`M${cx},${cy}L${pt}`,class:'radar-grid'}));svg.append(svgEl('text',{x:text[0],y:text[1]+4,'text-anchor':'middle'},name));});
 for(let j=1;j<=4;j++)svg.append(svgEl('text',{x:cx+5,y:cy-radius*j/4+3,class:'radar-scale'},format(max*j/4,0)+(j===4?' km/h':'')));
 for(const [column,cls] of [[2,'radar-gust'],[1,'radar-speed']]){
  // Missing sectors have no measured value. Split the line at each absent sector.
  const points=names.map((_,i)=>sectors.has(i)?point(i,sectors.get(i)[column]):null);
  if(points.every(Boolean))svg.append(svgEl('polygon',{points:points.map(p=>p.join(',')).join(' '),class:cls}));
  else for(let i=0;i<8;i++)if(points[i]){let next=points[(i+1)%8];if(next)svg.append(svgEl('path',{d:`M${cx},${cy}L${points[i]}L${next}Z`,class:cls}));svg.append(svgEl('circle',{cx:points[i][0],cy:points[i][1],r:2.5,class:cls}));}
 }
 names.forEach((name,i)=>{let pt=point(i,max);let dot=svgEl('circle',{cx:pt[0],cy:pt[1],r:12,fill:'transparent',tabindex:'0'});let v=sectors.get(i);dot.append(svgEl('title',{},v?`${name}: Mittel ${format(v[1])} km/h, maximale Böe ${format(v[2])} km/h (${v[3]} Messungen)`:`${name}: keine Messung`));svg.append(dot);});
 host.append(svg);host.setAttribute('aria-label',values.map(v=>`${names[v[0]]}: Mittel ${format(v[1])}, Böen ${format(v[2])} km/h`).join('; '));
}
function draw(){
 const host=$('#chart');host.replaceChildren();chartMetric=data?.metrics.find(m=>m.id===selected)||null;const m=chartMetric;
 if(!m||!m.series.length){host.innerHTML='<div class="chart-empty">Für diesen Zeitraum liegen keine Messwerte vor.</div>';$('#chartSummary').textContent='';return;}
 const rows=m.series.filter(x=>x.slice(0,4).every(Number.isFinite)),W=Math.max(300,host.clientWidth),H=host.clientHeight,L=55,R=15,T=23,B=35;
 let lo=Math.min(...rows.map(x=>x[2])),hi=Math.max(...rows.map(x=>x[3]));const pad=(hi-lo||Math.max(1,Math.abs(hi)*.1))*.15;lo-=pad;hi+=pad;
 const x=t=>L+(t-data.since)/(data.at-data.since)*(W-L-R),y=v=>T+(hi-v)/(hi-lo)*(H-T-B);
 const svg=svgEl('svg',{viewBox:`0 0 ${W} ${H}`});svg.append(svgEl('title',{},`${label(m)} im Zeitraum ${range}`));
 for(let i=0;i<=4;i++){let v=lo+(hi-lo)*i/4,Y=y(v);svg.append(svgEl('path',{d:`M${L} ${Y}H${W-R}`,class:'grid'}));svg.append(svgEl('text',{x:L-9,y:Y+4,'text-anchor':'end'},format(v,hi-lo<5?1:0)));}
 for(let i=0;i<=4;i++){let t=data.since+(data.at-data.since)*i/4;svg.append(svgEl('text',{x:x(t),y:H-9,'text-anchor':i===0?'start':i===4?'end':'middle'},range==='1h'||range==='24h'?clock(t):date(t)));}
 let groups=[],group=[];for(const row of rows){if(group.length&&row[0]-group.at(-1)[0]>data.step*1.8){groups.push(group);group=[];}group.push(row);}if(group.length)groups.push(group);
 for(const group of groups){svg.append(svgEl('path',{class:'band',d:'M'+group.map(r=>`${x(r[0])},${y(r[3])}`).join('L')+'L'+[...group].reverse().map(r=>`${x(r[0])},${y(r[2])}`).join('L')+'Z'}));svg.append(svgEl('path',{class:'series-line',d:'M'+group.map(r=>`${x(r[0])},${y(r[1])}`).join('L')}));if(group.length===1)svg.append(svgEl('circle',{cx:x(group[0][0]),cy:y(group[0][1]),r:2,class:'dot'}));}
 const guide=svgEl('path',{class:'crosshair',visibility:'hidden'}),dot=svgEl('circle',{r:4,class:'dot',visibility:'hidden'});svg.append(guide,dot);host.append(svg);
 const tip=document.createElement('div');tip.className='tooltip';tip.hidden=true;host.append(tip);
 function show(index){selection=Math.max(0,Math.min(rows.length-1,index));const r=rows[selection];guide.setAttribute('d',`M${x(r[0])} ${T}V${H-B}`);guide.setAttribute('visibility','visible');dot.setAttribute('cx',x(r[0]));dot.setAttribute('cy',y(r[1]));dot.setAttribute('visibility','visible');tip.textContent=`${date(r[0])} ${clock(r[0])} · ${format(r[1])} ${m.unit} · Min ${format(r[2])} / Max ${format(r[3])}`;tip.hidden=false;}
 host.onpointermove=e=>{const t=data.since+(e.clientX-host.getBoundingClientRect().left-L)/(W-L-R)*(data.at-data.since);let idx=0;for(let i=1;i<rows.length;i++)if(Math.abs(rows[i][0]-t)<Math.abs(rows[idx][0]-t))idx=i;show(idx);};
 host.onpointerleave=()=>{guide.setAttribute('visibility','hidden');dot.setAttribute('visibility','hidden');tip.hidden=true;};
 host.onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();show(e.key==='Home'?0:e.key==='End'?rows.length-1:selection+(e.key==='ArrowRight'?1:-1));}};
 let total=rows.reduce((n,r)=>n+r[4],0),mean=rows.reduce((n,r)=>n+r[1]*r[4],0)/total;
 $('#chartSummary').innerHTML=`<span>Minimum <strong>${format(Math.min(...rows.map(r=>r[2])))} ${escape(m.unit)}</strong></span><span>Mittel <strong>${format(mean)} ${escape(m.unit)}</strong></span><span>Maximum <strong>${format(Math.max(...rows.map(r=>r[3])))} ${escape(m.unit)}</strong></span>`;
 host.setAttribute('aria-label',`${label(m)}. Minimum ${format(Math.min(...rows.map(r=>r[2])))}; Mittel ${format(mean)}; Maximum ${format(Math.max(...rows.map(r=>r[3])))} ${m.unit}. Mit Pfeiltasten Werte erkunden.`);
}
async function load(){if(busy)return;busy=true;const requested=range;try{const r=await fetch('/cgi-bin/weather-api.cgi?range='+requested,{cache:'no-store',signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error(r.status);const incoming=await r.json();if(!Array.isArray(incoming.metrics))throw Error('format');if(requested!==range)return;data=incoming;lastFetch=Date.now();fetchFailed=false;render();}catch(e){fetchFailed=true;$('#notice').textContent='Messdaten können gerade nicht abgerufen werden. Ein neuer Versuch erfolgt automatisch.';$('#connection').textContent='Verbindung unterbrochen';$('#connection').classList.add('stale');}finally{busy=false;if(requested!==range)load();}}
document.querySelectorAll('[data-range]').forEach(b=>b.addEventListener('click',()=>{range=b.dataset.range;document.querySelectorAll('[data-range]').forEach(x=>{x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',String(x===b));});load();}));
$('#metric').addEventListener('change',e=>{selected=e.target.value;draw();});
$('#theme').addEventListener('click',()=>{document.body.classList.toggle('light');try{localStorage.setItem('meteo-theme',document.body.classList.contains('light')?'light':'dark');}catch(e){}draw();});
try{if(localStorage.getItem('meteo-theme')==='light')document.body.classList.add('light');}catch(e){}
$('#download').addEventListener('click',()=>{if(!chartMetric)return;const lines=['Zeit_UTC;Mittel;Minimum;Maximum;Anzahl;Einheit',...chartMetric.series.map(r=>[new Date(r[0]*1000).toISOString(),r[1],r[2],r[3],r[4],chartMetric.unit].join(';'))];const u=URL.createObjectURL(new Blob(['\ufeff'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=u;a.download=`wetter-${chartMetric.id}-${range}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);});
let resize;window.addEventListener('resize',()=>{clearTimeout(resize);resize=setTimeout(draw,100);});
load();setInterval(()=>{if(!document.hidden)load();},15000);setInterval(()=>{if(data&&data.metrics.map(m=>m.id+':'+Boolean(fresh(m))).join('|')!==freshnessKey)render();else updateStatus();},5000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)load();});
