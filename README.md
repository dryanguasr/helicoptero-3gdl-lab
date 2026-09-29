# Helicóptero 3 GDL · Laboratorio de control

**[Abrir el laboratorio público](https://dryanguasr.github.io/helicoptero-3gdl-lab/)** · [Código y versiones](https://github.com/dryanguasr/helicoptero-3gdl-lab)

Laboratorio público en React/TypeScript + Three.js/Plotly. El motor Python corre en un Web Worker mediante Pyodide. La interfaz se mantiene compacta; teoría, protocolos y preguntas viven en docs/guia-pedagogica.md. npm run dev y npm run build generan public/guia-helicoptero-3gdl.pdf.

## Convención

Sistema dextrógiro: x adelante, y izquierda, z arriba.

- α: roll sobre +x.
- β: pitch sobre +y; **β positivo baja el extremo de los motores**.
- γ: yaw sobre +z.

El motor heredado conserva elevación positiva hacia arriba por compatibilidad JSON v1. La interfaz aplica β = −elevación_interna.

## Controladores

El diseño de K (LQR o polos) se separa de la arquitectura servo:

- u = u_e + K(x_d−x): error de estado sin feedforward adicional.
- u = u_e − Kδx + N̄δr: precompensador nominal.
- ξ_dot = r−y; u = u_e − Kδx + K_iξ: integral.
- SMC en cascada con capa límite sat(s/φ).
- PID y asignación no lineal como referencias.

## No idealidades

Coulomb con adherencia, desbalance, perturbación constante, ráfagas, saturación, zona muerta, retardo y discrepancia modelo-planta. Son magnitudes didácticas.

## Ejecutar

    npm ci
    npm run dev

Validación:

    pip install -r requirements.txt
    python -m unittest discover -s tests -v
    npm run build

El build genera también la guía PDF. GitHub Actions publica dist/ tras un push a main.

## Filosofía

Compara de forma pareada: misma referencia, condición inicial, punto de operación, Δt, semilla y horizonte; cambia un solo factor. RMSE resume la corrida y el error medio de los últimos 3 s ayuda a identificar offset.

Yaw puede mostrar comportamiento integrador alrededor de un punto con autoridad; cambiar β puede exigir una nueva entrada estacionaria. El precompensador usa el equilibrio nominal; integral y SMC aportan mecanismos distintos ante sesgos e incertidumbre.

## Compatibilidad y límites

- JSON sigue en version 1; lqr antiguo migra a prefilter y lqi a integral.
- El modelo 3D es ilustrativo.
- u_c y u_d no son PWM ni fuerzas calibradas.
- Robustez no reemplaza controlabilidad.
- Sin integración de hardware ni gestión de estudiantes.

## Estructura

- public/python/: planta, trayectoria, control y motor.
- src/: interfaz, visor, gráficas y worker.
- docs/guia-pedagogica.md: material docente.
- scripts/generate-guide.mjs: PDF ligero para Pages.
- tests/: pruebas numéricas, reporte y navegador.
