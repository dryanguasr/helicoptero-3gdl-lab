import type {Config, Experiment, Row} from './types';

export const deg = (radians: number) => radians * 180 / Math.PI;
/** The v1 engine keeps its notebook convention. Never reorder its stored arrays. */
export const courseState = (x: number[]) => [x[2], x[3], x[0], x[1], x[4], x[5]];
export const AXES = [
  {symbol: 'α', name: 'Roll', index: 2, measured: 1},
  {symbol: 'β', name: 'Elevación / pitch', index: 0, measured: 0},
  {symbol: 'γ', name: 'Yaw', index: 4, measured: 2},
] as const;
export const TOLERANCE_DEG = 5;
export const HOLD_SECONDS = 3;

/** No angle wrapping: yaw is a limited travel coordinate, not an unrestricted heading. */
export function assessHold(rows: Row[], target: number[], since = 0,
  tolerance = TOLERANCE_DEG, required = HOLD_SECONDS) {
  let entered: number | null = null;
  let firstArrival: number | null = null;
  let confirmed: number | null = null;
  let longest = 0;
  let current = 0;
  let previous = -Infinity;
  for (const row of rows) {
    if (row.t < since) continue;
    const inside = AXES.every((axis, i) => Math.abs(deg(row.x[axis.index]) - target[i]) <= tolerance + 1e-9);
    // Engine dt is at most .05 s. A gap or backwards timestamp cannot prove continuity.
    if (!inside || row.t <= previous || row.t - previous > .075) entered = null;
    if (inside) {
      if (entered === null) entered = row.t;
      current = row.t - entered;
      longest = Math.max(longest, current);
      if (confirmed === null && current + 1e-9 >= required) {
        firstArrival = entered;
        confirmed = row.t;
      }
    } else current = 0;
    previous = row.t;
  }
  return {firstArrival, confirmed, longest, current, passed: confirmed !== null};
}

const referenceKey = (c: Config) => JSON.stringify([c.reference, c.setpoint, c.waypoints, c.segmentDuration, c.transitionDuration]);
export function activeTarget(experiment: Experiment, until: number) {
  let config = experiment.config;
  let since = 0;
  for (const event of experiment.events) {
    if (event.time > until + 1e-9) break;
    if (referenceKey(config) !== referenceKey(event.config)) since = event.time;
    config = event.config;
  }
  return {config, since, target: [0, config.setpoint[0], config.setpoint[1]]};
}

/** Evidence uses every sample. Only plot rendering may downsample. */
export function summarize(rows: Row[]) {
  if (rows.length < 2) return null;
  const integral = [0, 0], iae = [0, 0];
  let duration = 0, saturation = 0, allocation = 0, effort = 0;
  let maxRoll = 0;
  rows.forEach(r => {maxRoll = Math.max(maxRoll, Math.abs(deg(r.x[2])));});
  for (let i = 1; i < rows.length; i++) {
    const previous = rows[i - 1], r = rows[i], dt = r.t - previous.t;
    if (dt <= 0) continue;
    duration += dt;
    [0, 4].forEach((index, j) => {
      const a = deg(previous.ref[j] - previous.x[index]);
      const b = deg(r.ref[j] - r.x[index]);
      integral[j] += .5 * (a*a + b*b) * dt;
      iae[j] += .5 * (Math.abs(a) + Math.abs(b)) * dt;
    });
    saturation += Number(r.saturated) * dt;
    allocation += Number(r.limited) * dt;
    // Input at t_k acts on (t_{k-1},t_k], unlike the sampled state at t_k.
    effort += r.effective.reduce((s, u) => s + u*u, 0) * dt;
  }
  return duration > 0 ? {duration, rmse: integral.map(s => Math.sqrt(s / duration)), iae,
    saturation: 100*saturation/duration, allocation: 100*allocation/duration, effort, maxRoll} : null;
}

/** CSV v2: explicit course convention, physical units and complete actuator chain. */
export function signalCSV(rows: Row[]) {
  const stateNames = ['alpha_roll_rad','alpha_dot_rad_s','beta_pitch_rad','beta_dot_rad_s','gamma_yaw_rad','gamma_dot_rad_s'];
  const header = ['t_s', ...['plant','estimate'].flatMap(prefix => stateNames.map(name => `${prefix}_${name}`)),
    'measured_alpha_roll_rad','measured_beta_pitch_rad','measured_gamma_yaw_rad',
    'reference_beta_pitch_rad','reference_gamma_yaw_rad','assigned_alpha_roll_rad',
    'error_beta_pitch_rad','error_gamma_yaw_rad',
    ...['controller','pre_saturation','post_saturation','effective'].flatMap(stage => [`${stage}_uc_normalized`,`${stage}_ud_normalized`]),
    'actuator_saturated','allocation_limited'];
  return [header.join(','), ...rows.map(r => [r.t, ...courseState(r.x), ...courseState(r.hat),
    r.y[1],r.y[0],r.y[2],...r.ref,r.theta,r.ref[0]-r.x[0],r.ref[1]-r.x[4],
    ...r.u,...r.pre,...r.sat,...r.effective,Number(r.saturated),Number(r.limited)].join(','))].join('\n');
}

/** Extrema-preserving time decimation: keeps spikes, endpoints and transitions. */
export function plotIndices(rows: Row[], channels: ((r: Row) => number)[], budget = 1800) {
  if (rows.length <= budget) return rows.map((_, i) => i);
  const perBucket = Math.max(2, 2 * channels.length);
  const width = Math.ceil(rows.length / Math.max(1, Math.floor(budget / perBucket)));
  const keep = new Set<number>([0, rows.length - 1]);
  for (let start = 0; start < rows.length; start += width) {
    const end = Math.min(rows.length, start + width);
    for (const value of channels) {
      let lo = start, hi = start;
      for (let i = start+1; i < end; i++) {
        if (value(rows[i]) < value(rows[lo])) lo = i;
        if (value(rows[i]) > value(rows[hi])) hi = i;
      }
      keep.add(lo); keep.add(hi);
    }
  }
  return [...keep].sort((a,b) => a-b);
}
