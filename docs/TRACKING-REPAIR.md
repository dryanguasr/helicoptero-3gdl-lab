# Reparación del seguimiento tras el cambio de convención

29 de septiembre de 2026. Base sincronizada: `b4526e3`.

## Fallo reproducido

La configuración publicada seleccionaba una ganancia lineal fija, sintetizada
en elevación interna +15° (β = −15°), para una ruta que cruza por empuje cero
y cambia su signo. Ejecutando sus puntos durante 60 s, el controlador `state`
salía del dominio angular a los 5,60 s. Además, la ruta almacenaba los valores
anteriores de elevación: A/B quedaban en β = +45° y C en β = −45°, al contrario
de los botones. La duración inicial de 25 s truncaba los seis tramos.

## Corrección

- El experimento inicial usa la asignación no lineal existente, estados exactos,
  planta nominal, inicio en D, semilla 2026, Δt = 0,02 s y duración 60 s.
- La ruta D → A → D → B → D → C → D usa A/B en β = −45°, γ = ∓45°,
  y C en β = +45°, γ = 0°. Los botones obtienen sus coordenadas de esta misma ruta.
- Un botón carga este experimento completo. Otro carga un ensayo local de 25 s
  con precompensador, β = −15° constante y transición de γ = 0° a 20°.
  Cada botón reinicia la corrida y restablece todas las condiciones nominales.
- Las leyes lineales siguen disponibles, con una advertencia sobre su alcance.
  Seleccionar multipunto amplía la duración a la de todos sus segmentos.
- El worker revalida los módulos Python al cargar, para evitar reutilizar por
  frescura de caché una configuración anterior después de actualizar el sitio.

No se cambian las ecuaciones, ganancias ni signos internos del controlador.
En JSON v1 se conserva `[nombre, yaw, elevación positiva arriba]` para los puntos
y `[elevación, yaw]` para setpoints. No se invierten archivos antiguos al importarlos.
Las pruebas contra el cuaderno usan explícitamente su ruta original; por tanto
siguen comprobando la equivalencia sin confundirla con la nueva ruta del curso.

## Evidencia numérica

Ruta completa predeterminada: 3000 pasos, final 60,00 s, RMSE β = 0,04979°,
RMSE γ = 0,43698°, saturación 0 %. El mayor error absoluto de llegada entre
ambos ejes y los seis destinos es 0,95035°.

Con condiciones iniciales internas `[1.5, 0, 3, 0, -2, 0]` grados también
completa la ruta: RMSE β = 0,14070°, RMSE γ = 0,49381°.

Las pruebas automáticas exigen terminar ambas corridas, RMSE β < 0,2°,
RMSE γ < 0,75°, error de llegada < 1,1° y actitud final cerca de D. También
comprueban la correspondencia entre botones y puntos, compatibilidad del JSON,
restablecimiento de los experimentos y duración completa al elegir la ruta.
El despliegue ejecuta además la ruta predeterminada en Chromium con Pyodide
y comprueba sus errores a partir del CSV exportado, antes de publicar.

Las ganancias lineales locales no se convierten en un controlador global por
cambiarles un signo: su región de validez permanece limitada. Estas cifras
corresponden al experimento ideal; no garantizan seguimiento para combinaciones
arbitrarias de perturbaciones, observadores, referencias o parámetros.
