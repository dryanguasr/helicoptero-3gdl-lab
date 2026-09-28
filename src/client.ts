const worker=new Worker(new URL('./worker.ts',import.meta.url),{type:'module'});
let sequence=0;
const pending=new Map<number,{resolve:(v:any)=>void;reject:(e:Error)=>void}>();
worker.onmessage=({data})=>{const p=pending.get(data.id);if(p){pending.delete(data.id);data.error?p.reject(new Error(data.error)):p.resolve(data.result);}};
worker.onerror=(e)=>{for(const p of pending.values())p.reject(new Error(e.message||'El motor no pudo cargarse.'));pending.clear();};
export function request<T=any>(message:object):Promise<T>{return new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});worker.postMessage({id,message});});}
export function download(name:string,content:string,type='application/json'){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([content],{type}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
export async function storage(op:'load'|'put'|'delete',value?:any):Promise<any>{
  const db=await new Promise<IDBDatabase>((resolve,reject)=>{const r=indexedDB.open('helicoptero-lab',1);r.onupgradeneeded=()=>r.result.createObjectStore('runs',{keyPath:'id'});r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
  try{return await new Promise((resolve,reject)=>{const tx=db.transaction('runs',op==='load'?'readonly':'readwrite');const s=tx.objectStore('runs');const r=op==='load'?s.getAll():op==='put'?s.put(value):s.delete(value);let result:any;r.onsuccess=()=>{result=r.result};tx.oncomplete=()=>resolve(result);tx.onerror=()=>reject(tx.error);});}finally{db.close();}
}
