import type {Config} from './types';
export const lessons=[
 ['Modelo perfecto','Conoce la dinámica','Parámetros conocidos y acceso exacto a los seis estados. Sigue la ruta D–A–D–B–D–C–D y observa cómo el roll permite producir yaw.','¿Por qué el roll cambia de signo aunque no tenga un setpoint independiente?'],
 ['Controladores','Compara estrategias','Parte del equilibrio de elevación de 15°. Compara PID, LQR, LQI y asignación no lineal con cambios pequeños antes de ampliar el recorrido.','¿Qué cambia al exigir una maniobra lejos del equilibrio de diseño?'],
 ['Actuadores reales','Descubre los límites','Se añaden saturación, zona muerta y retardo. Desactiva un efecto por vez y conserva la corrida como referencia.','¿La respuesta mejora aumentando ganancias cuando los actuadores ya saturan?'],
 ['Incertidumbre','Pon a prueba el modelo','La planta tiene fricción, perturbaciones y un 15% menos de autoridad que el modelo interno. Las ráfagas ocurren a 24–25 s y 42–48 s.','¿Qué error puedes atribuir a una discrepancia de parámetros?'],
 ['Estados no disponibles','Reconstruye lo invisible','El controlador recibe una estimación a partir de ángulos medidos. Compara derivada filtrada, observador local y EKF.','¿Cómo se transforma el ruido angular en error de velocidad?'],
 ['Sistema compensado','Mejora con evidencia','Activa compensaciones de zona muerta y fricción. El predictor de retardo es experimental y permanece apagado inicialmente.','¿Cada compensación reduce el error sin elevar demasiado el esfuerzo?']
];
export function preset(base:Config,level:number):Config{
 const c=structuredClone(base);c.level=level;
 if(level===2){c.reference='smooth';c.setpoint=[17,5];c.initial=[15,0,0,0,0,0];}
 if(level>=3)Object.assign(c.flags,{saturation:true,deadzone:true,delay:true});
 if(level>=4){Object.assign(c.flags,{coulomb:true,disturbance:true});c.linked=false;c.params.a_alpha*=.85;c.params.a_psi*=.85;}
 if(level>=5){Object.assign(c.flags,{measurement:true,process:true});c.observer='ekf';}
 if(level>=6)Object.assign(c.flags,{compensateDeadzone:true,compensateFriction:true});
 return c;
}
