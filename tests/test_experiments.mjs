import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
const source=readFileSync(new URL('../src/experiments.ts',import.meta.url),'utf8');
const output=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText;
const {coursePoints,preparedExperiment,selectReference}=await import(`data:text/javascript;base64,${Buffer.from(output).toString('base64')}`);
const base={controller:'nonlinear',reference:'multipoint',duration:60,initial:[0,0,0,0,0,0],segmentDuration:10,waypoints:[['D',0,0],['A',-45,45],['D',0,0],['B',45,45],['D',0,0],['C',0,-45],['D',0,0]]};
test('point buttons derive signs and coordinates from engine route',()=>{
  assert.deepEqual(coursePoints(base),[['D',-0,0],['A',-45,-45],['B',-45,45],['C',45,0]]);
});
test('local experiment has trim-consistent initial state and reference',()=>{
  const local=preparedExperiment(base,'local');
  assert.equal(local.controller,'prefilter');assert.equal(local.trim,15);
  assert.deepEqual(local.initial,[15,0,0,0,0,0]);assert.deepEqual(local.setpoint,[15,20]);
  assert.equal(local.reference,'smooth');assert.equal(base.reference,'multipoint');
});
test('tracking preset returns independent complete baseline',()=>{
  const tracking=preparedExperiment(base,'tracking');assert.deepEqual(tracking,base);
  tracking.initial[0]=30;assert.equal(base.initial[0],0);
});
test('switching from local experiment to route includes every segment',()=>{
  const local=preparedExperiment(base,'local');selectReference(local,'multipoint');
  assert.equal(local.duration,60);assert.equal(local.controller,'prefilter');
  local.duration=100;selectReference(local,'multipoint');assert.equal(local.duration,100);
});
