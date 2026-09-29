import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import type {Row} from './types';
import {createBench,tipPosition} from './sceneModel';
import {deg} from './reporting';
import './learning.css';

type View='iso'|'front'|'top';
export default function Viewer({row,observer,rows=[]}:{row?:Row;observer:string;rows?:Row[]}) {
  const mount=useRef<HTMLDivElement>(null);
  const [error,setError]=useState('');
  const [ghost,setGhost]=useState(false),[trail,setTrail]=useState(true),[lightweight,setLightweight]=useState(false);
  const data=useRef({row,observer,rows,ghost,trail,lightweight});data.current={row,observer,rows,ghost,trail,lightweight};
  const redraw=useRef<()=>void>(()=>{}), view=useRef<(v:View)=>void>(()=>{});
  useEffect(()=>{
    const el=mount.current!;let renderer:THREE.WebGLRenderer;
    try {renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'low-power'});}
    catch {setError('WebGL no disponible. La simulación, las tablas y las gráficas siguen operativas.');return;}
    el.appendChild(renderer.domElement);
    renderer.domElement.setAttribute('aria-label','Banco didáctico de dos rotores: planta simulada, referencia y estimación opcional');
    renderer.domElement.setAttribute('role','img');
    renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.5));
    renderer.setClearColor(0x0e2433,0);
    const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(39,1,.05,30);
    camera.up.set(0,0,1);
    const controls=new OrbitControls(camera,renderer.domElement);
    controls.enableDamping=true;controls.minDistance=1.5;controls.maxDistance=7;
    const invalidate=()=>{if(!frame && visible && !document.hidden)frame=requestAnimationFrame(render);};
    let frame=0,visible=true;
    view.current=(v)=>{
      controls.target.set(.22,0,-.16);
      if(v==='iso')camera.position.set(2.3,-3.0,1.55);
      if(v==='front')camera.position.set(.3,-3.5,.2);
      if(v==='top')camera.position.set(.2,-.001,3.6);
      controls.update();invalidate();
    };
    const bench=createBench(scene);
    scene.add(new THREE.HemisphereLight(0xe7f7ff,0x34475d,2.3));
    const key=new THREE.DirectionalLight(0xffffff,2.6);key.position.set(2,-3,4);scene.add(key);
    const fill=new THREE.DirectionalLight(0x84c9e3,1.3);fill.position.set(-3,2,1);scene.add(fill);
    const target=new THREE.Mesh(new THREE.SphereGeometry(.027,12,8),new THREE.MeshBasicMaterial({color:0xffffff}));scene.add(target);
    const targetRing=new THREE.Mesh(new THREE.TorusGeometry(.055,.005,4,24),new THREE.MeshBasicMaterial({color:0xffffff}));target.add(targetRing);
    const capacity=900,positions=new Float32Array(capacity*3);
    const geometry=new THREE.BufferGeometry();const attribute=new THREE.BufferAttribute(positions,3);attribute.setUsage(THREE.DynamicDrawUsage);geometry.setAttribute('position',attribute);geometry.setDrawRange(0,0);
    const path=new THREE.Line(geometry,new THREE.LineBasicMaterial({color:0x64dfcd,transparent:true,opacity:.55}));path.frustumCulled=false;scene.add(path);
    const triad=new THREE.AxesHelper(.22);triad.position.set(-.35,-.28,-.92);scene.add(triad);
    let lastRows:Row[]|undefined,lastT:number|undefined,lastLight:boolean|undefined;
    const resize=()=>{const w=Math.max(1,el.clientWidth),h=Math.max(1,el.clientHeight);renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();invalidate();};
    function render(){
      frame=0;if(!visible||document.hidden)return;
      const d=data.current,r=d.row;
      if(lastLight!==d.lightweight){renderer.setPixelRatio(Math.min(window.devicePixelRatio,d.lightweight?1:1.5));bench.plant.details.visible=!d.lightweight;lastLight=d.lightweight;resize();}
      bench.estimate.yaw.visible=d.ghost&&d.observer!=='exact';path.visible=d.trail;
      if(r){
        for(const [model,x] of [[bench.plant,r.x],[bench.estimate,r.hat]] as const){
          model.yaw.rotation.z=x[4];model.pitch.rotation.y=-x[0];model.roll.rotation.x=x[2];
          model.rotors.forEach((rotor,i)=>{rotor.rotation.z=r.t*18*(i?1:-1);});
        }
        target.position.copy(tipPosition(r.ref[0],r.ref[1]));targetRing.quaternion.copy(camera.quaternion);
        if(d.rows!==lastRows||r.t!==lastT){
          let end=d.rows.length-1;while(end>=0&&d.rows[end].t>r.t+1e-9)end--;
          const count=Math.min(capacity,end+1);
          for(let j=0;j<count;j++){const i=count<=1?0:Math.floor(j*end/(count-1));tipPosition(d.rows[i].x[0],d.rows[i].x[4]).toArray(positions,j*3);}
          attribute.needsUpdate=true;geometry.setDrawRange(0,count);lastRows=d.rows;lastT=r.t;
        }
      }
      controls.update();renderer.render(scene,camera);
      el.dataset.drawCalls=String(renderer.info.render.calls);el.dataset.triangles=String(renderer.info.render.triangles);el.dataset.geometries=String(renderer.info.memory.geometries);el.dataset.quality=d.lightweight?'lightweight':'balanced';
    }
    controls.addEventListener('change',invalidate);
    const observerSize=new ResizeObserver(resize);observerSize.observe(el);
    const observerView=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(visible)invalidate();});observerView.observe(el);
    document.addEventListener('visibilitychange',invalidate);redraw.current=invalidate;view.current('iso');resize();
    return()=>{cancelAnimationFrame(frame);redraw.current=()=>{};observerSize.disconnect();observerView.disconnect();document.removeEventListener('visibilitychange',invalidate);controls.removeEventListener('change',invalidate);controls.dispose();const geometries=new Set<THREE.BufferGeometry>(),materials=new Set<THREE.Material>();scene.traverse(object=>{const mesh=object as THREE.Mesh;if(mesh.geometry)geometries.add(mesh.geometry);if(mesh.material)(Array.isArray(mesh.material)?mesh.material:[mesh.material]).forEach(m=>materials.add(m));});geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());renderer.dispose();renderer.domElement.remove();};
  },[]);
  useEffect(()=>{redraw.current();},[row,observer,rows,ghost,trail,lightweight]);
  return <section className="viewer card lab-viewer">
    <div className="viewer-head"><div><span className="eyebrow">BANCO DIDÁCTICO · DOS ROTORES</span><h2>Del control al movimiento</h2></div><span className="badge dark">{observer==='exact'?'ESTADOS EXACTOS':observer.toUpperCase()}</span></div>
    <div className="scene" ref={mount}>{error&&<p className="webgl-error">{error}</p>}
      <div className="scene-top"><span><i className="dot teal"/> Planta simulada <i className="dot white"/> Referencia {ghost&&observer!=='exact'&&<><i className="dot amber"/> Estimación</>}</span></div>
      <div className="camera-controls" aria-label="Vistas de cámara">{[['iso','3D'],['front','Frontal'],['top','Superior']].map(([id,label])=><button key={id} onClick={()=>view.current(id as View)}>{label}</button>)}</div>
      <div className="time-overlay">{(row?.t??0).toFixed(2)}<small> s</small></div>
      <div className="scene-help">Arrastra para orbitar · rueda para acercar · Z hacia arriba</div>
    </div>
    <div className="visual-options"><label><input type="checkbox" checked={trail} onChange={e=>setTrail(e.target.checked)}/> Rastro</label><label><input type="checkbox" checked={ghost} disabled={observer==='exact'} onChange={e=>setGhost(e.target.checked)}/> Estimación</label><label><input type="checkbox" checked={lightweight} onChange={e=>setLightweight(e.target.checked)}/> Modo ligero</label></div>
    <div className="telemetry">{[['α · roll',row?.x[2]],['β · pitch',row?.x[0]===undefined?undefined:-row.x[0]],['γ · yaw',row?.x[4]],['α interno',row?.theta]].map(([label,value])=><div key={label}><span>{label}</span><strong>{value===undefined?'—':deg(Number(value)).toFixed(1)}<small>°</small></strong></div>)}</div>
    <div className="viewer-note">Geometría ilustrativa, no CAD calibrado. Hélices sin RPM modeladas.<br/>α interno: asignación en cascada; 0° de equilibrio en control lineal.</div>
  </section>;
}
