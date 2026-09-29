# Laboratorio virtual de Control Avanzado
## Helicóptero de 3 grados de libertad

**Guía pedagógica de modelado, servocontrol, robustez y estimación**

Simulador: https://dryanguasr.github.io/helicoptero-3gdl-lab/

Convención del curso: **α = roll, β = pitch/elevación, γ = yaw**. Sistema dextrógiro: x hacia adelante, y hacia la izquierda, z hacia arriba. Por la regla de la mano derecha, **β positivo baja el extremo de los motores**.

---

# 1. Propósito de la guía

El laboratorio no busca solamente “ganancias que funcionen”. Se pretende identificar qué hipótesis hacen válida una ley de control, qué ocurre al romperlas y qué arquitectura conviene ante error de modelo, fricción, perturbaciones persistentes, saturación o estados no disponibles.

Una simulación que termina sin divergir no demuestra seguimiento, robustez ni estabilidad. Cada conclusión debe asociarse a una hipótesis, una corrida reproducible y una métrica.

## Resultados de aprendizaje

- Relacionar la dinámica no lineal con una representación local en espacio de estados.
- Diseñar K mediante LQR o ubicación de polos, separándolo de la arquitectura servo.
- Comparar error de estado, precompensación e integración.
- Explorar Coulomb, desbalance, perturbaciones constantes, saturación, zona muerta y retardo.
- Interpretar SMC como extensión robusta y reconocer sus límites.
- Usar corridas pareadas y métricas para sustentar conclusiones.

## Regla de trabajo

**Hipótesis → cambia un solo factor → corrida reproducible → mide → interpreta → siguiente experimento.**

---

# 2. Convención geométrica y signos

| Variable | Eje | Signo positivo | Interpretación |
|---|---|---|---|
| α · roll | x | mano derecha sobre +x | inclinación transversal |
| β · pitch | y | mano derecha sobre +y | el extremo +x baja; los motores descienden |
| γ · yaw | z | mano derecha sobre +z | giro en planta |

**Comprobación:** selecciona β = +20° y γ = 0°. El extremo de los motores debe bajar.

El motor heredado conserva internamente elevación positiva hacia arriba. La interfaz aplica β = −elevación interna. Interfaz, gráficas y CSV siguen la convención del curso.

---

# 3. Modelo dinámico no lineal

El modelo tiene seis estados y dos entradas virtuales: colectivo u_c y diferencial u_d. No son PWM, voltajes ni fuerzas calibradas.

En la convención del curso:

- β_ddot = −a_β u_c cos(α) − k_β sin(β) − b_β β_dot
- α_ddot = a_α u_d − k_α sin(α) − b_α α_dot
- γ_ddot = a_γ u_c sin(α) cos(β) − b_γ γ_dot

**x = [α, α_dot, β, β_dot, γ, γ_dot]^T**

## Lectura física

- u_c modifica principalmente β; si α ≠ 0 también produce yaw.
- u_d modifica α.
- α funciona como variable interna para generar yaw.
- γ no tiene término restaurador proporcional a γ: contiene una dinámica integradora.
- β y α sí tienen términos restauradores.

Que una coordenada sea integral de una velocidad no garantiza que cualquier referencia se siga con error estacionario nulo: depende del canal y del equilibrio.

---

# 4. Equilibrio, linealización y autoridad de yaw

Los controladores lineales se diseñan alrededor de:

**δx_dot = A δx + B δu**, **δy = C_r δx**

A y B provienen de Jacobianos; C_r selecciona β y γ. El laboratorio discretiza el modelo local para Δt.

## Por qué β = 0° es delicado

En el modelo, el colectivo de equilibrio puede hacerse cero en β = 0°. Si α = 0°, el término que produce yaw pierde autoridad en la linealización. Aumentar ganancias no crea un canal de actuación inexistente.

**Robustez no sustituye controlabilidad ni autoridad.**

### Diagnóstico

1. Diseña en β_e = −15°.
2. Verifica que el controlador lineal se sintetiza.
3. Lleva β_e a 0°.
4. Interpreta la advertencia antes de aumentar ganancias.

---

# 5. Diseño de K

La arquitectura servo y el procedimiento para obtener K son decisiones separadas.

## LQR

**J = Σ (x_k^T Q x_k + u_k^T R u_k)**

Q mayor penaliza más un estado; R mayor penaliza más actuación. LQR expresa un compromiso.

## Ubicación de polos

Se especifican polos continuos p_i y el laboratorio usa:

**z_i = exp(p_i Δt)**

La asignación depende de controlabilidad. Polos excesivamente rápidos pueden exigir actuación inviable.

**Actividad:** usa la misma arquitectura con LQR y polos, conservando referencia y escenario.

---

# 6. Ley 1 · realimentación del error de estado

**u = u_e + K(x_d − x)**

Se añade la entrada del equilibrio u_e. El estado deseado se obtiene de β y γ, pero no se añade la entrada estacionaria adicional necesaria para sostener un equilibrio nuevo.

## Qué observar

- Un cambio de γ manteniendo β en el punto de operación puede mostrar error final aproximadamente nulo por la dinámica integradora del canal.
- Un cambio de β puede requerir otra entrada estacionaria; el controlador necesita conservar error para producirla y aparece offset.

**El comportamiento tipo 1 se demuestra por canal; no se declara para todo el MIMO.**

---

# 7. Ley 2 · precompensador

**u = u_e − K δx + N_bar δr**

Se resuelve:

**[A B; C_r 0] [N_x; N_u] = [0; I]**

y:

**N_bar = N_u + K N_x**

## Ventaja

En condiciones nominales puede eliminar el error estacionario sin estados integrales.

## Limitación

Si el equilibrio real cambia por desbalance, perturbación o fricción no modelada, N_bar conserva el equilibrio del modelo nominal y puede aparecer offset.

---

# 8. Ley 3 · servosistema integral

**xi_dot = r − y**

**u = u_e − K δx + K_i xi**

Se integran β y γ. α permanece como variable interna.

## Qué aporta

- Rechazo de perturbaciones constantes dentro del rango de actuación.
- Compensación de sesgos de equilibrio desconocidos.
- Corrección de offset residual.

## Riesgos

- Saturación y windup.
- Stick-slip con Coulomb y sintonía agresiva.
- Acumulación integral frente a referencias físicamente imposibles.

Se usa anti-windup condicional ante saturación o límites de asignación.

---

# 9. Extensión · modos deslizantes

**s_q = e_dot_q + λ_q e_q**

El término robusto usa **sat(s_q/φ_q)**. El lazo de yaw genera una referencia interna de roll α_d; los lazos de β y α completan la cascada.

| Parámetro | Efecto |
|---|---|
| λ | rapidez hacia la superficie |
| η | intensidad del término robusto |
| φ | espesor de capa límite |

φ pequeño aproxima sign(s), pero aumenta chatter y sensibilidad al ruido.

SMC no elimina saturación, pérdida de autoridad ni un mal punto de operación.

---

# 10. No idealidades

| Efecto | Representación | Aprendizaje |
|---|---|---|
| Coulomb + adherencia | fricción seca con stiction | offset y stick-slip |
| Contrapeso | aceleración equivalente en β | equilibrio real distinto |
| Perturbación constante | d_α, d_β, d_γ | rechazo de sesgos |
| Ráfagas | perturbaciones temporales | recuperación |
| Saturación | límites de u_c,u_d | autoridad y anti-windup |
| Zona muerta | comandos pequeños anulados | pérdida de precisión |
| Retardo | entrada aplicada N pasos después | degradación de fase |
| Planta ≠ nominal | error paramétrico | sensibilidad del feedforward |

Son magnitudes didácticas, no identificación del prototipo.

---

# 11. Uso rápido

1. Selecciona β_d y γ_d o un punto A–D.
2. Elige la ley.
3. Para leyes lineales, elige LQR o polos.
4. Ejecuta Ideal.
5. Guarda la corrida.
6. Cambia un solo factor.
7. Superpone.
8. Compara RMSE, error medio de los últimos 3 s, saturación y gráficas.
9. Exporta JSON y CSV.

## Puntos del curso

| Punto | α | β | γ |
|---|---:|---:|---:|
| D | 0° | 0° | 0° |
| A | 0° | −45° | −45° |
| B | 0° | −45° | +45° |
| C | 0° | +45° | 0° |

Cruzar un punto no prueba permanencia.

---

# 12. Experimento 0 · verificar signos

**Configuración:** estados exactos, Ideal, β_d=+20°, γ_d=0°.

1. Ejecuta.
2. Confirma que los motores bajan.
3. Repite con β_d=−20°.
4. Comprueba gráfica y CSV.

**Preguntas:** ¿coinciden triedro y animación? ¿Qué signo tiene la elevación interna cuando β es positivo? ¿Qué efecto tendría una inversión de signo en el lazo?

---

# 13. Experimento 1 · canal integrador

**Configuración:** β_e=−15°, γ: 0°→20°, Ideal, u_e+K(x_d−x).

1. Ejecuta y guarda.
2. Observa error final de γ.
3. Repite con precompensador usando el mismo K.

**Preguntas:** ¿cambia mucho el error final? ¿qué estructura lo explica? ¿esto hace tipo 1 a todo el helicóptero?

---

# 14. Experimento 2 · cuándo hace falta N

**Configuración:** β_e=−15°, cambia β_d de −15° a −5°, γ fija, Ideal.

1. Usa error de estado.
2. Repite con precompensador.
3. Conserva K.

**Preguntas:** ¿por qué aparece offset? ¿qué entrada de equilibrio cambió? ¿qué representan N_x y N_u?

---

# 15. Experimento 3 · contrapeso

1. Línea base con precompensador.
2. Activa +1.5 °/s² de sesgo β.
3. Compara precompensador e integral.
4. Repite con signo contrario.

**Preguntas:** ¿por qué N no corrige completamente? ¿qué acumula el integrador? ¿cuándo K_i grande sería perjudicial?

---

# 16. Experimento 4 · perturbación constante

1. Activa d_β o d_γ constante.
2. Compara error de estado, precompensador e integral.
3. Mantén K y registra error de últimos 3 s.

**Preguntas:** ¿qué controlador contiene un modelo interno de una constante? ¿qué ocurre si la perturbación exige más actuación que la disponible?

---

# 17. Experimento 5 · Coulomb y stiction

1. Usa referencia pequeña.
2. Activa Coulomb + adherencia.
3. Compara precompensador e integral.
4. Explora SMC variando η y φ.

**Preguntas:** ¿aparece una región pegada? ¿cuándo la integral vence la fricción? ¿cómo cambia el chatter al reducir φ?

---

# 18. Experimento 6 · saturación, zona muerta y retardo

1. Activa cada efecto por separado.
2. Usa referencia suficientemente grande.
3. Compara sintonía moderada y agresiva.
4. Inspecciona solicitado → saturado → efectivo.

**Preguntas:** ¿más ganancia siempre acelera? ¿cómo reconocer falta de autoridad? ¿qué ocurre con integral bajo saturación?

---

# 19. Experimento 7 · error de modelo

1. Desactiva “Modelo nominal = planta”.
2. Introduce 10–15% menos autoridad real.
3. Compara precompensador, integral y SMC.

**Preguntas:** ¿qué parte del precompensador depende del modelo? ¿integral corrige todo error de modelo? ¿qué costo acompaña la robustez?

---

# 20. Experimento 8 · estados no disponibles

1. Línea base con estados exactos.
2. Compara derivada filtrada, Luenberger y EKF.
3. Añade ruido solo después.
4. Separa error de estimación y seguimiento.

**Preguntas:** ¿más rapidez del observador siempre ayuda? ¿cómo afecta el ruido a las velocidades? ¿por qué x−x_hat y r−y son errores distintos?

---

# 21. Registro sugerido

| Corrida | Ley | Diseño K | Escenario | RMSE β | RMSE γ | eβ 3 s | eγ 3 s | Saturación | Observación |
|---|---|---|---|---:|---:|---:|---:|---:|---|

Conserva condición inicial, referencia, punto de operación, Δt, semilla y horizonte.

## Conclusión mínima

Incluye: qué cambió; qué métrica cambió; mecanismo propuesto; limitación de la evidencia; siguiente experimento.

---

# 22. Preguntas integradoras

1. ¿Por qué yaw puede parecer tipo 1 mientras β no?
2. ¿En qué sentido N_bar es feedforward y K feedback?
3. ¿Qué información usa N que la integral no necesita conocer explícitamente?
4. ¿Bajo qué condiciones la integral rechaza una perturbación constante?
5. ¿Qué diferencia hay entre robustez y controlabilidad?
6. ¿Cómo distinguir falta de autoridad, error de modelo y error del observador?
7. ¿Qué compromiso existe entre rapidez, saturación y esfuerzo?
8. ¿Por qué comparar con distinta semilla o referencia invalida una conclusión causal?
9. ¿Por qué α es interna para yaw y no una tercera consigna externa?
10. ¿Qué cambia al pasar de entradas virtuales a motores unidireccionales reales?

---

# 23. Errores comunes

- Llamar estable a una corrida solo porque llegó al final.
- Confundir β con la elevación interna.
- Suponer que toda posición como estado implica tipo 1.
- Suponer que el precompensador rechaza perturbaciones desconocidas.
- Interpretar ∫u²dt como energía física.
- Cambiar varios factores a la vez.
- Usar SMC para ignorar saturación o pérdida de autoridad.
- Confundir error de estimación y seguimiento.
- Diseñar en β=0° sin revisar estabilizabilidad de yaw.

---

# 24. Parámetros y trazabilidad

Los parámetros son didácticos. Los coeficientes de autoridad, restauración, fricción viscosa y Coulomb deben registrarse junto con cada corrida. La geometría 3D no calcula las inercias del modelo.

Los JSON conservan version 1. Experimentos antiguos con lqr migran a prefilter y lqi a integral.

---

# 25. Bibliografía mínima

- Ogata, K. Ingeniería de control moderna.
- Arnáez Braschi, E. L. Enfoque práctico del control moderno.
- Åström, K. J. y Murray, R. M. Feedback Systems.
- Slotine, J.-J. E. y Li, W. Applied Nonlinear Control.
- Material del curso sobre espacio de estados, controlabilidad, linealización, realimentación, observadores y Kalman.

**El objetivo no es premiar la curva más bonita, sino explicar por qué cambia el comportamiento cuando cambia la arquitectura o deja de cumplirse una hipótesis.**
