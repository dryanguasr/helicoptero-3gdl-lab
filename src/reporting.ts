import type {Config, Experiment, Row} from './types';

export const deg = (radians: number) => radians * 180 / Math.PI;
/** Engine v1: [elevation-up, elev_dot, roll, roll_dot, yaw, yaw_dot].
 * Course: [alpha-roll, alpha_dot, beta-pitch-positive-down, beta_dot, gamma-yaw, gamma_dot]. */
export const courseState = (x: number[]) => [x[2], x[3], -x[0], -x[1], x[4], x[5]];
export const AXES = [
  {symbol:'α',name:'Roll',index:2,measured:1,sign:1},
  {symbol:'β',name:'Pitch / elevación',index:0,measured:0,sign:-1},
  {symbol:'γ',name:'Yaw',index:4,measured:2,sign:1},
] as const;
export const TOLERANCE_DEG=5;export const HOLD_SECONDS=3;
export const courseAngle=(row:Row,index:number)=>index===0?-deg(row.x[0]):index===2?deg(row.x[2]):deg(row.x[4]);
export const courseReference=(row:Row,j:number)=>j===0?-deg(row.ref[0]):deg(row.ref[1]);

export function assessHold(rows:Row[],target:number[],since=0,tolerance=TOLERANCE_DEG,required=HOLD_SECONDS){
 let entered:number|null=null,firstArrival:number|null=null,confirmed:number|null=null,longest=0,current=0,previous=-Infinity;
 for(const row of rows){if(row.t<since)continue;const state=courseState(row.x);const angles=[deg(state[0]),deg(state[2]),deg(state[4])];const inside=angles.every((v,i)=>Math.abs(v-target[i])<=tolerance+1e-9);
  if(!inside||row.t<=previous||row.t-previous>.075)entered=null;if(inside){if(entered===null)entered=row.t;current=row.t-entered;longest=Math.max(longest,current);if(confirmed===null&&current+1e-9>=required){firstArrival=entered;confirmed=row.t;}}else current=0;previous=row.t;}
 return{firstArrival,confirmed,longest,current,passed:confirmed!==null};
}
const referenceKey=(c:Config)=>JSON.stringify([c.reference,c.setpoint,c.waypoints,c.segmentDuration,c.transitionDuration]);
export function activeTarget(experiment:Experiment,until:number){let config=experiment.config,since=0;for(const event of experiment.events){if(event.time>until+1e-9)break;if(referenceKey(config)!==referenceKey(event.config))since=event.time;config=event.config;}return{config,since,target:[0,-config.setpoint[0],config.setpoint[1]]};}

export function summarize(rows:Row[]){if(rows.length<2)return null;const integral=[0,0],iae=[0,0];let duration=0,saturation=0,allocation=0,effort=0,maxRoll=0;rows.forEach(r=>{maxRoll=Math.max(maxRoll,Math.abs(deg(r.x[2])));});for(let i=1;i<rows.length;i++){const p=rows[i-1],r=rows[i],dt=r.t-p.t;if(dt<=0)continue;duration+=dt;[0,4].forEach((index,j)=>{const sign=j===0?-1:1;const a=deg(sign*(p.ref[j]-p.x[index]));const b=deg(sign*(r.ref[j]-r.x[index]));integral[j]+=.5*(a*a+b*b)*dt;iae[j]+=.5*(Math.abs(a)+Math.abs(b))*dt;});saturation+=Number(r.saturated)*dt;allocation+=Number(r.limited)*dt;effort+=r.effective.reduce((s,u)=>s+u*u,0)*dt;}const end=rows.at(-1)?.t??0;const tail=rows.filter(r=>r.t>=Math.max(0,end-3));const steadyError=[0,1].map(j=>tail.length?tail.reduce((sum,r)=>{const sign=j===0?-1:1;const index=j===0?0:4;return sum+deg(sign*(r.ref[j]-r.x[index]));},0)/tail.length:0);return duration>0?{duration,rmse:integral.map(s=>Math.sqrt(s/duration)),iae,saturation:100*saturation/duration,allocation:100*allocation/duration,effort,maxRoll,steadyError}:null;}

export function signalCSV(rows:Row[]){const stateNames=['alpha_roll_rad','alpha_dot_rad_s','beta_pitch_rad','beta_dot_rad_s','gamma_yaw_rad','gamma_dot_rad_s'];const header=['t_s',...['plant','estimate'].flatMap(prefix=>stateNames.map(name=>`${prefix}_${name}`)),'measured_alpha_roll_rad','measured_beta_pitch_rad','measured_gamma_yaw_rad','reference_beta_pitch_rad','reference_gamma_yaw_rad','internal_alpha_roll_rad','error_beta_pitch_rad','error_gamma_yaw_rad',...['controller','pre_saturation','post_saturation','effective'].flatMap(stage=>[`${stage}_uc_normalized`,`${stage}_ud_normalized`]),'actuator_saturated','allocation_limited'];return[header.join(','),...rows.map(r=>{const beta=-r.x[0],betaHat=-r.hat[0],betaMeas=-r.y[0],betaRef=-r.ref[0];return[r.t,r.x[2],r.x[3],beta,-r.x[1],r.x[4],r.x[5],r.hat[2],r.hat[3],betaHat,-r.hat[1],r.hat[4],r.hat[5],r.y[1],betaMeas,r.y[2],betaRef,r.ref[1],r.theta,betaRef-beta,r.ref[1]-r.x[4],...r.u,...r.pre,...r.sat,...r.effective,Number(r.saturated),Number(r.limited)].join(',');})].join('\n');}

export function plotIndices(rows:Row[],channels:((r:Row)=>number)[],budget=1800){if(rows.length<=budget)return rows.map((_,i)=>i);const perBucket=Math.max(2,2*channels.length);const width=Math.ceil(rows.length/Math.max(1,Math.floor(budget/perBucket)));const keep=new Set<number>([0,rows.length-1]);for(let start=0;start<rows.length;start+=width){const end=Math.min(rows.length,start+width);for(const value of channels){let lo=start,hi=start;for(let i=start+1;i<end;i++){if(value(rows[i])<value(rows[lo]))lo=i;if(value(rows[i])>value(rows[hi]))hi=i;}keep.add(lo);keep.add(hi);}}return[...keep].sort((a,b)=>a-b);}
