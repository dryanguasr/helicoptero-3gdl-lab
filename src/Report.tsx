import {useMemo} from 'react';
import type {Experiment, Row, Run} from './types';
import {activeTarget, assessHold, AXES, deg, summarize} from './reporting';
import {download} from './client';

type Props = {rows: Row[]; row?: Row; experiment: Experiment; runs: Run[]};
const fmt = (v: number | null | undefined, digits = 2) => v == null || !Number.isFinite(v) ? '—' : v.toFixed(digits);
export default function Report({rows, row, experiment, runs}: Props) {
  const summary = useMemo(() => summarize(rows), [rows]);
  const end = rows.at(-1)?.t ?? 0;
  const active = activeTarget(experiment, end);
  const hold = useMemo(() => assessHold(rows, active.target, active.since), [rows, active.target.join(','), active.since]);
  const multipoint = active.config.reference === 'multipoint';
  const stateFeedback = ['lqr','lqi'].includes(active.config.controller);
  const protocolKeys = ['initial','dt','seed','reference','setpoint','waypoints','segmentDuration','duration'] as const;
  const mismatch = runs.some(run => protocolKeys.some(key => JSON.stringify(run.experiment.config[key]) !== JSON.stringify(experiment.config[key])) || Math.abs((run.rows.at(-1)?.t ?? 0)-end)>.051);
  function exportReport() {
    const c = active.config;
    const lines = ['# Informe de simulación · Helicóptero 3 GDL', '',
      'Convención del curso: α = roll, β = elevación/pitch, γ = yaw. JSON v1 conserva el orden original del motor.',
      'Modelo didáctico; no es una validación de hardware ni un gemelo calibrado.', '',
      `Ventana analizada: 0–${fmt(end)} s. Muestras: ${rows.length}. Δt: ${c.dt} s. Semilla: ${c.seed}.`,
      `Control: ${c.controller}. Realimentación: ${c.observer}. Planta: ${c.plantModel}. Cambios registrados: ${experiment.events.length}.`, '',
      '## Evidencia cuantitativa',
      stateFeedback ? 'LQR/LQI: el roll interno mostrado es el equilibrio de 0°, no una consigna de lazo en cascada. El controlador incluye precompensación nominal de referencia; LQI añade integración del error.' : 'Control en cascada/asignación: el roll interno mostrado es calculado por el controlador para producir yaw.',
      '| Indicador | Valor |', '|---|---:|',
      `| RMSE temporal de seguimiento β | ${fmt(summary?.rmse[0])} ° |`,
      `| RMSE temporal de seguimiento γ | ${fmt(summary?.rmse[1])} ° |`,
      `| IAE β | ${fmt(summary?.iae[0])} °·s |`, `| IAE γ | ${fmt(summary?.iae[1])} °·s |`,
      `| Saturación física | ${fmt(summary?.saturation)} % del tiempo |`,
      `| Límite de asignación | ${fmt(summary?.allocation)} % del tiempo |`,
      `| Máximo absoluto de roll | ${fmt(summary?.maxRoll)} ° |`,
      `| ∫(uc²+ud²)dt efectivo | ${fmt(summary?.effort)} u.n.²·s (no energía física) |`, '',
      'RMSE e IAE usan integración trapezoidal del error con todas las muestras. La actuación usa el intervalo que termina en cada muestra.', '',
      '## Criterio de llegada',
      multipoint ? 'No evaluado como permanencia: la ruta multipunto no programa 3 s de espera en cada punto. El error de cruce no acredita llegada estable.' :
      `Objetivo final (α, β, γ): (${active.target.join(', ')})°. Desde t=${fmt(active.since)} s. Criterio: ±5° simultáneamente, durante ≥3 s consecutivos. ${hold.passed ? `Permanencia confirmada a t=${fmt(hold.confirmed)} s; entrada de ese intervalo: t=${fmt(hold.firstArrival)} s.` : 'Permanencia todavía no demostrada en la ventana observada.'}`,
      'La comprobación es sobre muestras; no demuestra estabilidad matemática ni comportamiento entre muestras. Roll cero es un criterio final, no una tercera consigna independiente.', '',
      '## Interpretación del estudiante',
      'Hipótesis antes del ensayo: [completar]', 'Única modificación respecto a la línea base: [completar]',
      'Evidencia que apoya o contradice la hipótesis: [completar con valores y tiempos]',
      'Compromiso entre seguimiento, actuación y estimación: [completar]',
      'Limitaciones y siguiente experimento: [completar]', '',
      '## Reproducción', 'Guardar también JSON de configuración/eventos y CSV de señales. Mantener horizonte, condiciones iniciales, referencia, Δt y semilla al comparar.',
      '', '```json', JSON.stringify(experiment, null, 2), '```'];
    download('informe-helicoptero.md', lines.join('\n'), 'text/markdown;charset=utf-8');
  }
  return <div className="learning-report">
    <div className="report-heading"><div><span className="eyebrow">LEER ANTES DE CONCLUIR</span><h3>¿Qué demuestra esta corrida?</h3></div><button onClick={exportReport} disabled={!summary}>↓ Informe guiado</button></div>
    <div className="report-cards">
      <article><span>Seguimiento · toda la corrida</span><strong>β {fmt(summary?.rmse[0])}° <small>/ γ {fmt(summary?.rmse[1])}°</small></strong><p>RMSE temporal contra la referencia móvil. Ventana 0–{fmt(end)} s; no cambia al mover el cursor.</p></article>
      <article><span>Restricciones · tiempo activo</span><strong>{fmt(summary?.saturation,1)}% <small>saturación</small></strong><p>Asignación limitada: {fmt(summary?.allocation,1)}%. Son restricciones distintas, no dos nombres del mismo efecto.</p></article>
      <article className={!multipoint && hold.passed ? 'criterion-confirmed' : ''}><span>Objetivo final · ±5° / 3 s</span><strong>{multipoint ? 'No evaluado' : hold.passed ? 'Confirmado' : 'No demostrado'}</strong><p>{multipoint ? 'La ruta no incluye espera de 3 s. Usa un punto A, B, C o D para evaluar permanencia.' : <>Objetivo (α, β, γ) = ({active.target.join(', ')})°. Permanencia actual: {fmt(hold.current,1)} s.{hold.passed && <> Confirmación: t = {fmt(hold.confirmed)} s.</>}</>}</p></article>
    </div>
    <details><summary>Estado, medición y estimación · instante inspeccionado t = {fmt(row?.t)} s</summary>
      <div className="table-scroll"><table><thead><tr><th>Variable</th><th>Planta x [°]</th><th>Medición y [°]</th><th>Estimación x̂ [°]</th><th>Referencia [°]</th><th>Error r − x [°]</th></tr></thead><tbody>{AXES.map(a => {
        const reference = row ? (a.index === 2 ? row.theta : row.ref[a.index === 0 ? 0 : 1]) : undefined;
        return <tr key={a.symbol}><td>{a.symbol} · {a.name}{a.index===2?(stateFeedback?' (equilibrio interno)':' (asignación interna)'):''}</td><td>{fmt(row && deg(row.x[a.index]))}</td><td>{fmt(row && deg(row.y[a.measured]))}</td><td>{fmt(row && deg(row.hat[a.index]))}</td><td>{fmt(reference === undefined ? undefined : deg(reference))}</td><td>{fmt(row && reference !== undefined ? deg(reference-row.x[a.index]) : undefined)}</td></tr>;
      })}</tbody></table></div>
      <p>El error de seguimiento r − x y el error de estimación x − x̂ responden preguntas distintas. La planta simulada es conocida para evaluar; un equipo físico no entrega necesariamente esos seis estados.</p>
    </details>
    <details><summary>Convenciones, unidades y límites del modelo</summary><p><b>Curso:</b> α = roll, β = elevación/pitch, γ = yaw. <b>Motor/JSON v1:</b> alpha = elevación, theta = roll, psi = yaw; su vector sigue [β, β̇, α, α̇, γ, γ̇] en la notación del curso. No permutes archivos antiguos.</p><p>Dos entradas virtuales firmadas: colectivo u_c y diferencial u_d. No son voltajes, PWM ni fuerzas calibradas de dos motores. En PID/no lineal, el roll se asigna para conseguir yaw. En LQR/LQI, el valor interno de roll representa el equilibrio de 0°, no una consigna en cascada. No se impone una tercera referencia independiente. La geometría no determina las inercias del modelo.</p><p>LQR y LQI incluyen precompensación nominal de referencia; LQI añade estados integrales. La señal interna de roll (theta en el motor; assigned_alpha_roll_rad en CSV v2) distingue asignación en cascada de equilibrio local: no se debe interpretar igual en las cuatro arquitecturas.</p><p>∫(u_c² + u_d²)dt es un índice de esfuerzo normalizado, no joules. No se reporta sobreimpulso porcentual ni tiempo de establecimiento convencional para una ruta móvil. La prueba ±5°/3 s es un criterio operativo sobre las muestras, no una demostración de estabilidad.</p></details>
    {mismatch && <p className="warning">Comparación no pareada: cambian referencia, condiciones iniciales, Δt, semilla u horizonte. No atribuyas la diferencia solamente al controlador.</p>}
    <p className="report-prompt"><b>Antes → después:</b> escribe una hipótesis, modifica un solo factor y justifica el resultado con seguimiento, restricciones y estimación. Guarda JSON + CSV junto con el informe.</p>
  </div>;
}
