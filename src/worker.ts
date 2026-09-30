import {loadPyodide} from 'pyodide';
let runtime:Awaited<ReturnType<typeof loadPyodide>>;
const ready=(async()=>{
  runtime=await loadPyodide({indexURL:'https://cdn.jsdelivr.net/pyodide/v0.29.5/full/'});
  await runtime.loadPackage(['numpy','scipy']);
  for(const file of ['plant','trajectory','control','engine']){
    const res=await fetch(new URL(`../python/${file}.py`, self.location.href),{cache:'no-cache'});
    if(!res.ok)throw new Error(`No se pudo cargar ${file}: ${res.status}`);
    runtime.FS.writeFile(`/home/pyodide/${file}.py`,await res.text());
  }
  await runtime.runPythonAsync('from engine import dispatch');
})();
let queue=Promise.resolve();
self.onmessage=({data})=>{queue=queue.then(async()=>{
  try{await ready;runtime.globals.set('_message',JSON.stringify(data.message));
    const result=await runtime.runPythonAsync('dispatch(_message)');
    self.postMessage({id:data.id,result:JSON.parse(result)});
  }catch(error){const lines=String(error).trim().split('\n');const last=lines.at(-1)||'Error del motor';self.postMessage({id:data.id,error:last.replace(/^(ValueError|Error|PythonError):\s*/, '')});}
});};
