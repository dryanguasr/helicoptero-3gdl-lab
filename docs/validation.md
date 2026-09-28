# Validación de la versión 1

Fecha: 28 de septiembre de 2026.

## Motor numérico

18 pruebas aprobadas en Python 3.12, NumPy 2.5.3 y SciPy 1.18.1. Cubren retardo 0/4 pasos, zona muerta e inversa, estado exacto, ausencia de acceso a verdad en observadores, continuidad de trayectoria, estabilizabilidad, estabilización de cuatro controladores, colectivo firmado, límite de roll, anti-windup y recuperación, observadores con ruido, reproducción idéntica, ruido común entre corridas, equilibrio, validación de entrada y dominio.

Se compararon directamente dinámica, integración RK4 y asignación no lineal contra las celdas revisadas del cuaderno original en seis instantes. Las mismas muestras están conservadas en `tests/notebook_reference.json` para CI. La comprobación directa opcional requiere `SOURCE_NOTEBOOK`; las muestras guardadas siempre se comprueban.

Cada preset completa 3000 pasos (60 s a 50 Hz):

| Nivel | RMSE α [°] | RMSE ψ [°] | Saturación [%] | Esfuerzo ∫u²dt |
|---|---:|---:|---:|---:|
| 1 · Perfecto | 0.140 | 0.498 | 0.0 | 33.741 |
| 2 · Controladores, no lineal inicial | 0.003 | 0.228 | 0.0 | 13.195 |
| 3 · Actuadores | 1.804 | 1.596 | 3.6 | 31.113 |
| 4 · Incertidumbre | 1.702 | 1.776 | 2.1 | 40.724 |
| 5 · EKF sin compensación | 2.212 | 1.700 | 9.4 | 49.280 |
| 6 · Compensado | 0.741 | 1.441 | 11.6 | 56.002 |

Estas cifras describen los presets, no una garantía de estabilidad para configuraciones arbitrarias. El nivel 2 tiene una referencia local distinta y no se compara directamente con la trayectoria multipunto. El nivel 6 reduce error respecto al 5 pero incrementa esfuerzo y saturación.

## Interfaz y navegador

- Compilación TypeScript y Vite de producción: aprobada.
- Carga real de Python, NumPy y SciPy en Web Worker: comprobada.
- Visor WebGL: geometría visible, estado real/estimado, instante y referencias.
- Un paso: avanza exactamente 0.02 s.
- LQI: selector, parámetros y síntesis operativos en navegador.
- EKF compensado: corrida de 3 s completada; guardado y reproducción produjeron las mismas métricas visibles (RMSE α 1.39°, ψ 2.48°, saturación 40.0%, esfuerzo 2.22).
- Guardado IndexedDB, selección y superposición de corridas: comprobados.
- Importación de `public/examples/lqi-local.json`: recupera la etapa de controladores.
- Enlace compartido: copiado y abierto en otra pestaña; recupera el experimento con su registro de cambios.
- Vista móvil de 390 × 844: diseño en una columna; visor primero; sin desbordamiento horizontal. Vista de escritorio de tres columnas revisada visualmente.
- Controles numéricos, selectores y botones tienen nombres accesibles; navegación con teclado y acceso al inicio comprobados.
- Consola durante la simulación revisada sin errores.

## Límites de esta validación

La revisión de navegador se realizó en el navegador integrado Chromium. No sustituye pruebas exhaustivas en Safari, Firefox, dispositivos físicos o hardware de helicóptero. La carga inicial requiere conexión para los recursos fijados de Pyodide. La compilación avisa del tamaño del paquete de gráficas; esto afecta descarga inicial, no el paso de integración.
