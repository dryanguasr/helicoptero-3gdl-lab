import {useEffect,useMemo,useRef,useState} from 'react';
// @ts-ignore Distribution bundle shares the official Plotly API.
import Plotly from 'plotly.js-dist-min';
import type {Row,Run} from './types';
import {AXES,deg,plotIndices} from './reporting';
const colors=['#098c86','#5876cf','#cc7054','#a77a26'];
const hints:Record<string,string>={
 tracking:'Compara planta y referencia. β usa la convención del curso: positivo cuando baja el extremo de los motores.',
 error:'Error de seguimiento r − y en la convención del curso. La banda ±5° es una referencia visual, no una prueba de estabilidad.',
 path:'Plano angular γ–β. No es una trayectoria cartesiana.',
 roll:'El roll α es una variable interna clave para producir yaw; en los controladores lineales su valor deseado de equilibrio es 0°.',
 control:'Muestra la cadena de actuación. Las entradas son normalizadas, no voltajes ni PWM calibrados.',
 estimate:'Planta x, estimación x̂ y medición y. Medir ángulos no equivale a conocer velocidades.',
 estimatorError:'Error de estimación x − x̂, distinto del error de seguimiento.',
 velocity:'Velocidades angulares en °/s con la convención α, β, γ del curso.',
};
export default function Charts({rows,runs,cursor,onCursor}:{rows:Row[];runs:Run[];cursor:number;onCursor:(n:number)=>void}){
 const[tab,setTab]=useState('tracking');const el=useRef<HTMLDivElement>(null);
 const chart=useMemo(()=>{const d:any[]=[];function trace(name:string,source:Row[],value:(r:Row)=>number,color:string,dash='solid',xValue=(r:Row)=>r.t,shape='linear'){const ids=plotIndices(source,[value,xValue]);d.push({name,x:ids.map(i=>xValue(source[i])),y:ids.map(i=>value(source[i])),type:'scatter',mode:'lines',line:{color,width:2,dash,shape},hovertemplate:'%{x:.3f}, %{y:.3f}<extra>%{fullData.name}</extra>'});}
  if(tab==='tracking'||tab==='error'){
   for(const [index,label,j,sign] of [[0,'β · pitch',0,-1],[4,'γ · yaw',1,1]] as const){trace(label,rows,r=>deg(sign*(tab==='error'?r.ref[j]-r.x[index]:r.x[index])),colors[j]);if(tab==='tracking')trace(`${label} · referencia`,rows,r=>deg(sign*r.ref[j]),colors[j],'dot');runs.forEach((run,i)=>trace(`${run.name} · ${label}`,run.rows,r=>deg(sign*(tab==='error'?r.ref[j]-r.x[index]:r.x[index])),colors[(i+2)%4],j?'dashdot':'dash'));}
  }else if(tab==='path'){
   trace('Referencia',rows,r=>-deg(r.ref[0]),'#8796a7','dot',r=>deg(r.ref[1]));trace('Planta simulada',rows,r=>-deg(r.x[0]),colors[0],'solid',r=>deg(r.x[4]));runs.forEach((run,i)=>trace(run.name,run.rows,r=>-deg(r.x[0]),colors[(i+1)%4],'dash',r=>deg(r.x[4])));
  }else if(tab==='control'){
   for(const [j,label] of ['u_c · colectivo','u_d · diferencial'].entries()){trace(`${label} · antes del límite`,rows,r=>r.pre[j],colors[j],'dot',undefined,'vh');trace(`${label} · saturado`,rows,r=>r.sat[j],colors[j],'dash',undefined,'vh');trace(`${label} · efectivo`,rows,r=>r.effective[j],colors[j],'solid',undefined,'vh');}
  }else if(tab==='roll'){
   trace('α · planta',rows,r=>deg(r.x[2]),colors[2]);trace('α · interno',rows,r=>deg(r.theta),colors[1],'dot');trace('α · estimación',rows,r=>deg(r.hat[2]),colors[3],'dash');
  }else{
   AXES.forEach((axis,i)=>{const index=axis.index+(tab==='velocity'?1:0);const sign=axis.sign;trace(axis.symbol+(tab==='velocity'?'̇':'')+(tab==='estimatorError'?' · x − x̂':' · planta'),rows,r=>deg(sign*(tab==='estimatorError'?r.x[index]-r.hat[index]:r.x[index])),colors[i]);if(tab!=='estimatorError')trace(axis.symbol+' · estimación',rows,r=>deg(sign*r.hat[index]),colors[i],'dash');if(tab==='estimate'){const ids=plotIndices(rows,[r=>r.y[axis.measured]],700);d.push({name:axis.symbol+' · medición',x:ids.map(i=>rows[i].t),y:ids.map(i=>deg(sign*rows[i].y[axis.measured])),type:'scatter',mode:'markers',marker:{color:colors[i],size:3,opacity:.35}});}});
  }return d;},[rows,runs,tab]);
 useEffect(()=>{if(!el.current||!rows.length)return;const current=rows[cursor]??rows.at(-1)!;const shapes:any[]=tab==='path'?[]:[{type:'line',x0:current.t,x1:current.t,y0:0,y1:1,yref:'paper',line:{color:'#819ca0',dash:'dot',width:1}}];if(tab==='error')shapes.push({type:'rect',xref:'paper',x0:0,x1:1,y0:-5,y1:5,fillcolor:'rgba(17,158,154,.07)',line:{width:0},layer:'below'});const data=tab==='path'?[...chart,{name:'Instante inspeccionado',x:[deg(current.x[4])],y:[-deg(current.x[0])],type:'scatter',mode:'markers',marker:{size:10,color:colors[2]},showlegend:false}]:chart;void Plotly.react(el.current,data,{autosize:true,height:380,margin:{l:62,r:20,t:65,b:52},paper_bgcolor:'transparent',plot_bgcolor:'transparent',font:{family:'system-ui',color:'#45606e',size:12},legend:{orientation:'h',y:1.2,font:{size:11}},xaxis:{title:{text:tab==='path'?'γ · yaw [°]':'Tiempo [s]'},gridcolor:'#e7edec',zerolinecolor:'#b4c8c8'},yaxis:{title:{text:tab==='control'?'Actuación [u.n.]':tab==='velocity'?'Velocidad [°/s]':tab==='path'?'β · pitch [°]':tab.includes('rror')?'Error [°]':'Ángulo [°]'},gridcolor:'#e7edec',zerolinecolor:'#b4c8c8'},uirevision:tab,shapes,hovermode:tab==='path'?'closest':'x unified'},{responsive:true,displaylogo:false,modeBarButtonsToRemove:['lasso2d','select2d']});},[chart,rows,tab,cursor]);
 useEffect(()=>{const node=el.current;const resize=new ResizeObserver(()=>{if(node&&(node as any)._fullLayout)void Plotly.Plots.resize(node);});if(node)resize.observe(node);return()=>{resize.disconnect();if(node)Plotly.purge(node);};},[]);
 return <><div className="chart-tabs" aria-label="Seleccionar gráfica">{[['tracking','Seguimiento'],['error','Error'],['path','Plano γ–β'],['roll','Roll α'],['control','Actuadores'],['estimate','Estimación'],['estimatorError','Error estimador'],['velocity','Velocidades']].map(([id,label])=><button aria-pressed={tab===id} key={id} className={tab===id?'active':''} onClick={()=>setTab(id)}>{label}</button>)}</div><p className="chart-explanation">{hints[tab]}</p><div ref={el} aria-label="Gráfica de resultados"/><label className="scrubber">Inspeccionar instante <input aria-label="Instante de la simulación" type="range" min={0} max={Math.max(0,rows.length-1)} value={Math.min(cursor,Math.max(0,rows.length-1))} onChange={e=>onCursor(+e.target.value)}/><span>{(rows[cursor]?.t??0).toFixed(2)} s</span></label>{rows.length>1800&&<p className="muted">Vista gráfica reducida; métricas y CSV usan todas las muestras.</p>}</>;
}
