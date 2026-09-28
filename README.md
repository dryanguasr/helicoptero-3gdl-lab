# Helicóptero 3 GDL · Laboratorio de control

Laboratorio público, en español y sin cuentas. React/TypeScript, Three.js y Plotly; un motor Python con NumPy/SciPy se ejecuta en un Web Worker con Pyodide. El cuaderno de origen es `helicoptero_3gdl_trayectoria_multipunto_pedagogico_ekf_compensado.ipynb`. La referencia visual es MELFA Kinematics Lab.

## Ejecutar

Requiere Node 22 y acceso a Internet para la primera carga de Pyodide y sus paquetes.

```sh
npm ci
npm run dev
```

`npm run build` verifica TypeScript y genera `dist/`. `npm run preview` sirve la compilación. El workflow de GitHub valida el motor y publica `dist/` en GitHub Pages. La URL base es relativa, compatible con un subdirectorio de repositorio. No hay backend ni datos enviados a un servidor de cálculo. Los recursos de Pyodide se descargan desde jsDelivr; la tipografía usa Google Fonts, con alternativa local del sistema.

## Uso

1. Elige una de las seis etapas: modelo perfecto, controladores, actuadores reales, incertidumbre, estados no disponibles y compensaciones.
2. Modifica los setpoints o la ruta multipunto. Inicia, pausa o avanza un paso de integración.
3. Configura por separado planta, controlador, sensores, observador y compensaciones.
4. Guarda una corrida y marca las que quieras superponer. Puedes inspeccionar el pasado con el cursor temporal; el modelo 3D sigue ese mismo instante.
5. Exporta JSON para reproducir el experimento y CSV para analizar las señales. Compartir copia un enlace con la configuración y los cambios; para experimentos muy extensos se descarga JSON.

Los cambios de arquitectura, observador, modelo lineal/no lineal, condición inicial, semilla o paso de integración reinician la corrida. Los demás cambios se aplican en el siguiente paso después de un breve agrupamiento de los movimientos del control. Cada evento guarda el paso exacto y la configuración completa. Editar durante una reproducción conserva el pasado y sustituye los eventos futuros. Los experimentos guardados usan IndexedDB y permanecen solo en el navegador actual.

## Modelo y supuestos

Estados internos: `[α, α̇, θ, θ̇, ψ, ψ̇]`, en radianes y rad/s. Entradas: colectivo firmado `u_c` y diferencial `u_d`. No se impone una tercera referencia independiente para roll. El dibujo es conceptual, no un modelo CAD ni hardware validado. Las unidades de actuación son normalizadas, no voltajes o PWM calibrados.

La planta nominal es no lineal aun en el nivel ideal. Se integra con RK4; la aproximación lineal local es una selección explícita. La saturación física y el límite de asignación de roll son conceptos distintos: el nivel ideal elimina la saturación de actuadores, pero mantiene el límite configurable de roll del controlador.

El PID usa lazos de elevación y yaw, feedforward gravitacional y un lazo interno de roll. Es una arquitectura local: cerca de empuje cero no existe autoridad lineal suficiente de yaw. La integración se congela cuando se satura una entrada o la asignación alcanza su límite.

LQR y LQI se sintetizan en tiempo discreto a partir de la linealización y la discretización exacta del sistema local. Se verifica estabilizabilidad con PBH y se resuelve la ecuación de Riccati. LQI integra errores de elevación y yaw. El experimento preparado usa equilibrio de elevación de 15°; cero se rechaza si el modo de yaw no es estabilizable. Cambiar pesos recalcula las ganancias.

El observador lineal usa asignación de polos y corrección con la medición del siguiente instante. El EKF usa RK4, Jacobiano numérico y forma de Joseph. Ambos reciben solo ángulos y una reconstrucción nominal de la actuación a partir del comando emitido. No leen estados reales ni el búfer real de retardo. Las covarianzas del EKF son independientes del ruido físico. La compensación de fricción y el predictor de entrada constante son heurísticos; no garantizan mejorar el desempeño.

## Diferencias deliberadas respecto al cuaderno

- Retardo corregido: cero devuelve la entrada actual; N pasos devuelve la entrada de k−N. El búfer original agregaba un paso.
- El nivel ideal usa estados exactos y permite eliminar saturación; el escenario llamado ideal en el cuaderno seguía usando EKF y saturación.
- Parámetros nominales y reales se separan explícitamente. La opción de vincularlos mantiene coincidencia exacta.
- Ruido de proceso y de medición tienen secuencias independientes que avanzan incluso al desactivarlos, para comparar corridas con realizaciones comunes.
- Las señales se registran con estados y referencias del mismo instante; las entradas corresponden al intervalo que terminó allí.
- Las transiciones suaves usan quinticas y conservan posición, velocidad y aceleración de la referencia vigente. La trayectoria original conserva perfiles trapezoidales.
- Compensaciones independientes de los efectos reales: se puede estudiar sobrecompensación.
- Las perturbaciones se definen por tiempos absolutos, 24–25 s y 42–48 s; no se reinterpretan los comentarios de tramo del cuaderno.
- Se detiene y conserva el último estado válido si elevación/roll superan ±80°, yaw ±360° o el cálculo deja de ser finito. No hay protección para un equipo físico.

## Estructura y contrato

- `public/python/`: `plant.py`, `trajectory.py`, `control.py`, `engine.py`. Motor sin dependencias de interfaz.
- `src/`: interfaz, visor, gráficas, cliente y worker. `types.ts` define configuración, muestras, cambios y corridas.
- `tests/`: pruebas numéricas. `docs/validation.md`: registro de comprobaciones.

Mensajes al worker: `defaults`, `reset(config, events)`, `advance(n)` y `update(config)`. La interfaz implementa iniciar/pausar mediante solicitudes acotadas de avance, evitando bloquear el worker con una corrida completa. Las respuestas tienen muestras, métricas, estado de terminación y configuración aplicada. El formato JSON de experimento tiene `version:1`, `config` inicial y `events` ordenados por `step`, cada uno con configuración completa. El motor valida los datos antes de usarlos; no ejecuta código procedente del JSON.

La animación es independiente de la integración. Si el equipo no alcanza tiempo real se ralentiza la reproducción sin saltar pasos. La escala de velocidad modifica cuántos pasos se solicitan, no Δt. La primera carga de Python/SciPy es la limitación principal en conexiones lentas.

## Pruebas

```sh
python -m venv .venv
# Activar el entorno según el sistema operativo
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Para contrastar además contra el cuaderno original, define `SOURCE_NOTEBOOK` con su ruta. La prueba ejecuta solo las celdas de parámetros, dinámica, referencia y asignación, previamente revisadas. El archivo original no se modifica. La comparación completa punto a punto con la simulación antigua no sería válida tras corregir retardo, realimentación y secuencias aleatorias; se comparan las funciones compartidas y se prueba por separado cada corrección.

Sin integración con hardware, autenticación ni gestión de alumnos en esta versión.
