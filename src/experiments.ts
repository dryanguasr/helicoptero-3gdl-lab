import type {Config} from './types';

// Read targets from the engine's canonical course route; v1 stores [name, yaw, elevation-up].
export function coursePoints(base:Config):[string,number,number][] {
  return [...new Map(base.waypoints.map(([name,yaw,elevation])=>
    [name,[name,-elevation,yaw] as [string,number,number]])).values()];
}

export function preparedExperiment(base:Config,kind:'tracking'|'local'):Config {
  const c=structuredClone(base);
  if(kind==='local') Object.assign(c,{
    controller:'prefilter',reference:'smooth',duration:25,
    initial:[15,0,0,0,0,0],setpoint:[15,20],trim:15,
  });
  return c;
}

export function selectReference(c:Config,reference:string):void {
  c.reference=reference;
  if(reference==='multipoint') c.duration=Math.max(c.duration,(c.waypoints.length-1)*c.segmentDuration);
}
