import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
import * as THREE from 'three';
const source=readFileSync(new URL('../src/sceneModel.ts',import.meta.url),'utf8').replace("'three'",JSON.stringify(import.meta.resolve('three')));
const output=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText;
const {createBench,orientRig}=await import(`data:text/javascript;base64,${Buffer.from(output).toString('base64')}`);
test('rendered rotor normals produce the physical yaw torque for both thrust signs',()=>{
  const scene=new THREE.Scene(),{plant,estimate}=createBench(scene);
  for(const model of [plant,estimate]) for(const elevation of [-45,0,45]) for(const roll of [-20,20]) for(const yaw of [-45,0,45]) {
    const a=THREE.MathUtils.degToRad(elevation),r=THREE.MathUtils.degToRad(roll);
    orientRig(model,[a,0,r,0,THREE.MathUtils.degToRad(yaw),0]);scene.updateMatrixWorld(true);
    for(const collective of [-1,1]) {
      const torque=new THREE.Vector3();
      for(const rotor of model.rotors) {
        const arm=rotor.getWorldPosition(new THREE.Vector3());
        const force=new THREE.Vector3(0,0,1).transformDirection(rotor.matrixWorld).multiplyScalar(collective/2);
        torque.add(arm.cross(force));
      }
      assert.ok(Math.abs(torque.z+collective*Math.cos(a)*Math.sin(r))<1e-12);
    }
  }
});
