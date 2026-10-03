# Corrección de la convención de roll — 2 de octubre de 2026

La revisión 2 del modelo usa roll positivo de mano derecha alrededor del brazo
+x. Con empuje positivo sobre el +z local, la componente lateral de fuerza es
−u_c sin(α). Por tanto, el momento de yaw tiene signo −u_c sin(α) cos(β).
El visor ya empleaba esa orientación; ahora la dinámica coincide con ella.

Se cambia el signo del acoplamiento en `nominal`, de la asignación de roll en
control no lineal y SMC, y de la autoridad de yaw en PID. Las linealizaciones,
LQR/LQI, EKF y predictor usan la dinámica corregida. En ubicación de polos,
la síntesis se realiza en la base anterior y se transforma la ganancia: el
problema MIMO admite varias soluciones y el algoritmo no conserva por sí solo
la solución ante reflexiones de coordenadas. Esto mantiene la ganancia validada
sin retocar polos ni pesos. El diferencial positivo sigue acelerando roll positivo.

La comparación con el cuaderno sigue siendo exacta tras cambiar coordenadas:
S = diag(1, 1, −1, −1, 1, 1), U = diag(1, −1),
x_nuevo = S x_cuaderno, u_nuevo = U u_cuaderno.
Las pruebas comparan dinámica, RK4 y asignación con esta transformación;
no se alteran las muestras originales para hacerlas pasar.

Los JSON nuevos incluyen `modelRevision: 2`. Los JSON sin este campo se aceptan
con los números de ángulo interpretados en la convención física actual y se
marcan como revisión 2. No se promete reproducción idéntica de corridas antiguas
con roll inicial, perturbaciones o ruido distintos de cero. Para comparar datos
del cuaderno se deben transformar roll, su velocidad, diferencial y los canales
correspondientes de ruido/perturbación. Setpoints y coordenadas de trayectoria
mantienen su esquema; no se vuelven a invertir A/B/C.

Las pruebas incluyen el momento calculado independientemente mediante r × F,
ambos signos de empuje y roll, las tres leyes en cascada, los controladores
lineales en ambos equilibrios y métodos de síntesis, observadores con ruido,
la ruta completa y su CSV en Chromium. En D → A, a 1 s, roll debe ser positivo
con colectivo positivo y velocidad de yaw negativa. La guía usa la misma ecuación.
