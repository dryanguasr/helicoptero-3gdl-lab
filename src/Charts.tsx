import {useEffect,useRef,useState} from 'react';
// @ts-ignore Distribution bundle shares the official Plotly API.
import Plotly from 'plotly.js-dist-min';
import type {Row,Run} from './types';
const deg=(x:number)=>x*180/Math.PI;
export default function Charts({rows,runs,cursor,onCursor}:{rows:Row[];runs:Run[];cursor:number;onCursor:(n:number)=>void}){
 const[tab,setTab]=useState('tracking');const el=useRef<HTMLDivElement>(null);
 useEffect(()=>{if(!el.current||!rows.length)return;const d:any[]=[];const colors=['#0c9c98','#d99140','#647cda','#ba6783'];
  function trace(name:string,x:number[],y:number[],color:string,dash='solid',axis='y'){d.push({name,x,y,type:'scatter',mode:'lines',line:{color,width:2,dash},yaxis:axis});}
  const t=rows.map(r=>r.t);
  if(tab==='tracking'){
   for(const [i,label,j] of [[0,'Elevación α',0],[4,'Yaw ψ',1]] as const){trace(label,t,rows.map(r=>deg(r.x[i])),colors[j]);trace(`${label} · referencia`,t,rows.map(r=>deg(r.ref[j])),colors[j],'dot');}
   runs.forEach((run,i)=>{trace(run.name+' · α',run.rows.map(r=>r.t),run.rows.map(r=>deg(r.x[0])),colors[(i+2)%4],'dash');trace(run.name+' · ψ',run.rows.map(r=>r.t),run.rows.map(r=>deg(r.x[4])),colors[(i+2)%4],'dot');});
  }else if(tab==='path'){
   trace('Referencia',rows.map(r=>deg(r.ref[1])),rows.map(r=>deg(r.ref[0])),'#8b9aab','dot');trace('Real',rows.map(r=>deg(r.x[4])),rows.map(r=>deg(r.x[0])),colors[0]);runs.forEach((run,i)=>trace(run.name,run.rows.map(r=>deg(r.x[4])),run.rows.map(r=>deg(r.x[0])),colors[(i+1)%4],'dash'));
  }else if(tab==='control'){
   for(const [j,label] of ['Colectivo','Diferencial'].entries()){trace(`${label} · solicitado`,t,rows.map(r=>r.pre[j]),colors[j],'dot');trace(`${label} · efectivo`,t,rows.map(r=>r.effective[j]),colors[j]);}
  }else if(tab==='roll'){
   trace('Roll real',t,rows.map(r=>deg(r.x[2])),colors[0]);trace('Roll asignado',t,rows.map(r=>deg(r.theta)),colors[1],'dot');trace('Roll estimado',t,rows.map(r=>deg(r.hat[2])),colors[2],'dash');
  }else{
   const ids=tab==='velocity'?[1,3,5]:[0,2,4];ids.forEach((j,i)=>{trace(['α','θ','ψ'][i]+' real',t,rows.map(r=>deg(r.x[j])),colors[i]);trace(['α','θ','ψ'][i]+' estimado',t,rows.map(r=>deg(r.hat[j])),colors[i],'dash');if(tab==='estimate')d.push({name:['α','θ','ψ'][i]+' medido',x:t,y:rows.map(r=>deg(r.y[i])),mode:'markers',marker:{color:colors[i],size:2,opacity:.3}});});
  }
  Plotly.react(el.current,d,{autosize:true,height:320,margin:{l:55,r:20,t:15,b:45},paper_bgcolor:'transparent',plot_bgcolor:'transparent',font:{family:'Inter, system-ui',color:'#647484',size:11},legend:{orientation:'h',y:1.16},xaxis:{title:{text:tab==='path'?'Yaw ψ [°]':'Tiempo [s]'},gridcolor:'#e9eeee',zerolinecolor:'#ccd8d9'},yaxis:{title:{text:tab==='control'?'Acción de control':tab==='velocity'?'Velocidad [°/s]':tab==='path'?'Elevación α [°]':'Ángulo [°]'},gridcolor:'#e9eeee',zerolinecolor:'#ccd8d9'},uirevision:tab,shapes:tab==='path'?[]:[{type:'line',x0:rows[cursor]?.t??t[t.length-1],x1:rows[cursor]?.t??t[t.length-1],y0:0,y1:1,yref:'paper',line:{color:'#9bb5b7',dash:'dot',width:1}}]}, {responsive:true,displaylogo:false,modeBarButtonsToRemove:['lasso2d','select2d']});
 },[rows,runs,tab,cursor]);
 useEffect(()=>{const node=el.current;const ro=new ResizeObserver(()=>{if(node)Plotly.Plots.resize(node);});if(node)ro.observe(node);return()=>{ro.disconnect();if(node)Plotly.purge(node);};},[]);
 return <><div className="chart-tabs" role="tablist" aria-label="Gráficas">{[['tracking','Seguimiento'],['path','Plano yaw–pitch'],['roll','Roll'],['control','Actuadores'],['estimate','Estimación'],['velocity','Velocidades']].map(([id,label])=><button role="tab" aria-selected={tab===id} key={id} className={tab===id?'active':''} onClick={()=>setTab(id)}>{label}</button>)}</div><div ref={el} aria-label="Gráfica de resultados"/><label className="scrubber">Inspeccionar instante <input aria-label="Instante de la simulación" type="range" min={0} max={Math.max(0,rows.length-1)} value={Math.min(cursor,Math.max(0,rows.length-1))} onChange={e=>onCursor(+e.target.value)}/><span>{(rows[cursor]?.t||0).toFixed(2)} s</span></label></>;
}
