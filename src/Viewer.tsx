import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import type {Row} from './types';
const degrees=(v:number)=>v*180/Math.PI;
export default function Viewer({row,observer}:{row?:Row;observer:string}){
 const mount=useRef<HTMLDivElement>(null);const current=useRef(row);current.current=row;
 const reset=useRef<()=>void>(()=>{});const[error,setError]=useState('');
 useEffect(()=>{
  const el=mount.current!;let renderer:THREE.WebGLRenderer;
  try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});}catch{setError('WebGL no está disponible. La simulación y las gráficas siguen activas.');return;}
  renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));el.appendChild(renderer.domElement);
  renderer.domElement.setAttribute('aria-label','Helicóptero 3D: arrastra para orbitar y usa la rueda para acercar');renderer.domElement.setAttribute('role','img');
  const scene=new THREE.Scene();const camera=new THREE.PerspectiveCamera(42,1,.01,100);camera.up.set(0,0,1);camera.position.set(2.6,-3.3,2.3);
  const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(.1,0,.1);controls.enableDamping=true;
  reset.current=()=>{camera.position.set(2.6,-3.3,2.3);controls.target.set(.1,0,.1);controls.update();};
  scene.add(new THREE.HemisphereLight(0xe0fcff,0x243443,3));const light=new THREE.DirectionalLight(0xffffff,4);light.position.set(2,-2,5);scene.add(light);
  const grid=new THREE.GridHelper(4,20,0x355867,0x213647);grid.rotation.x=Math.PI/2;grid.position.z=-.45;scene.add(grid);
  const base=new THREE.Mesh(new THREE.CylinderGeometry(.23,.3,.1,32),new THREE.MeshStandardMaterial({color:0x3d5367,metalness:.6,roughness:.4}));base.rotation.x=Math.PI/2;base.position.z=-.39;scene.add(base);
  const pole=new THREE.Mesh(new THREE.CylinderGeometry(.035,.05,.36,16),new THREE.MeshStandardMaterial({color:0x8298a6}));pole.rotation.x=Math.PI/2;pole.position.z=-.18;scene.add(pole);
  scene.add(new THREE.AxesHelper(.45));
  function helicopter(color:number,ghost=false){
   const yaw=new THREE.Group(),pitch=new THREE.Group(),roll=new THREE.Group();yaw.add(pitch);pitch.add(roll);scene.add(yaw);
   const mat=new THREE.MeshStandardMaterial({color,metalness:.35,roughness:.35,transparent:ghost,opacity:ghost?.3:1,wireframe:ghost});
   function box(size:number[],pos:number[],parent:THREE.Group){const m=new THREE.Mesh(new THREE.BoxGeometry(...size as [number,number,number]),mat);m.position.set(...pos as [number,number,number]);parent.add(m);return m;}
   box([1.45,.045,.05],[.28,0,0],pitch);box([.2,.2,.16],[-.43,0,0],pitch);box([.12,.62,.08],[1,0,0],roll);
   const rotors:THREE.Group[]=[];
   for(const y of [-.29,.29]){box([.13,.12,.12],[1,y,0],roll);const rotor=new THREE.Group();rotor.position.set(1,y,.09);roll.add(rotor);box([.4,.035,.018],[0,0,0],rotor);box([.035,.4,.018],[0,0,0],rotor);rotors.push(rotor);}
   return {yaw,pitch,roll,rotors};
  }
  const real=helicopter(0x31d6c8),est=helicopter(0xf4ba68,true);
  const target=new THREE.Mesh(new THREE.SphereGeometry(.035,16,16),new THREE.MeshBasicMaterial({color:0xf5f9ff}));scene.add(target);
  const trailGeometry=new THREE.BufferGeometry();const trail=new THREE.Line(trailGeometry,new THREE.LineBasicMaterial({color:0x329b9f,transparent:true,opacity:.55}));scene.add(trail);let points:THREE.Vector3[]=[];let lastT=-1;
  const resize=new ResizeObserver(()=>{const w=el.clientWidth,h=el.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();});resize.observe(el);
  let frame:number;
  function render(){const r=current.current;
   if(r){for(const [model,x] of [[real,r.x],[est,r.hat]] as const){model.yaw.rotation.z=x[4];model.pitch.rotation.y=-x[0];model.roll.rotation.x=x[2];model.rotors.forEach(rotor=>{rotor.rotation.z=r.t*18;});}
    target.position.set(Math.cos(r.ref[1])*Math.cos(r.ref[0]),Math.sin(r.ref[1])*Math.cos(r.ref[0]),Math.sin(r.ref[0]));
    if(r.t<lastT)points=[];
    if(r.t!==lastT){points.push(new THREE.Vector3(Math.cos(r.x[4])*Math.cos(r.x[0]),Math.sin(r.x[4])*Math.cos(r.x[0]),Math.sin(r.x[0])));if(points.length>1500)points.shift();trailGeometry.setFromPoints(points);lastT=r.t;}
   }
   controls.update();renderer.render(scene,camera);frame=requestAnimationFrame(render);
  }render();
  return()=>{cancelAnimationFrame(frame);resize.disconnect();controls.dispose();scene.traverse(obj=>{const mesh=obj as THREE.Mesh;mesh.geometry?.dispose();if(mesh.material){(Array.isArray(mesh.material)?mesh.material:[mesh.material]).forEach(m=>m.dispose());}});renderer.dispose();el.removeChild(renderer.domElement);};
 },[]);
 return <section className="viewer card"><div className="viewer-head"><div><span className="eyebrow">MODELO DINÁMICO · 3 GDL</span><h2>Gemelo de simulación</h2></div><span className="badge dark">{observer==='exact'?'ESTADOS EXACTOS':observer.toUpperCase()}</span></div><div className="scene" ref={mount}>{error&&<p className="webgl-error">{error}</p>}<div className="scene-top"><span><i className="dot teal"/> Real <i className="dot amber"/> Estimado <i className="dot white"/> Objetivo</span><button onClick={()=>reset.current()}>Vista isométrica</button></div><div className="time-overlay">{(row?.t||0).toFixed(2)}<small> s</small></div><div className="scene-help">Arrastra para orbitar · rueda para acercar</div></div><div className="telemetry">{[['α',row?.x[0]],['θ',row?.x[2]],['ψ',row?.x[4]],['θ deseado',row?.theta]].map(([name,value])=><div key={name}><span>{name}</span><strong>{degrees(Number(value||0)).toFixed(1)}<small>°</small></strong></div>)}</div><div className="viewer-note">Dos entradas, tres grados de libertad. El roll coordina el movimiento de yaw.</div></section>;
}
