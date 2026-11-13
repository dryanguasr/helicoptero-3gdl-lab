<div align="center">

# Helicóptero 3 GDL · Laboratorio interactivo de control
### Experimenta con regulación, seguimiento y no idealidades desde el navegador

**React · TypeScript · Three.js · Plotly · Python / Pyodide**

**[Abrir laboratorio web](https://dryanguasr.github.io/helicoptero-3gdl-lab/)** · [Guía pedagógica](docs/guia-pedagogica.md) · [Pruebas](tests/) · [Referencia técnica completa](README_TECHNICAL.md)

</div>

## Qué puedes aprender

Explorar un helicóptero didáctico de tres grados de libertad, cambiar el esquema de control y observar cómo evoluciona el seguimiento ante perturbaciones y límites del actuador. La visualización 3D **ilustra el modelo**; no representa una planta física calibrada.

| Tema | Experimentos disponibles |
| --- | --- |
| Estado y seguimiento | Regulación por LQR/polos, precompensación e integral |
| Robustez | SMC de capa límite, PID y opciones de asignación no lineal |
| No idealidades | Saturación, fricción, zona muerta, retardo, desbalance y ráfagas |
| Evidencia | Gráficas, métricas de error y comparaciones pareadas |

## Un laboratorio, dos capas

```text
Interfaz web (React / TypeScript)
          │ parámetros, resultados
          ▼
       Web Worker
          ▼
Python (planta, control, trayectoria, motor)
          ▼
    Gráficas + escena 3D
```

El motor Python se ejecuta en el navegador mediante **Pyodide**, con dependencia de recursos externos durante su inicialización. Las convenciones se definen expresamente: **x adelante, y izquierda, z arriba**; roll α, pitch β y yaw γ. La interfaz usa β positivo hacia abajo para el extremo de motores.

## Ejecutar localmente

```bash
npm ci
npm run dev
```

Validar antes de publicar:

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
npm run build
```

El proyecto incluye comprobaciones numéricas y de navegador y un flujo de publicación en GitHub Pages. La documentación señala qué experimentos son **didácticos** y qué parámetros no deben interpretarse como PWM ni fuerzas calibradas.

## Para profundizar

[Guía de aprendizaje](docs/guia-pedagogica.md) · [Auditoría técnica](docs/audit-2026-09-28.md) · [Convenciones](docs/ROLL-CONVENTION.md) · [Referencia técnica anterior, íntegra](README_TECHNICAL.md).

> **Límites:** sin validación de hardware ni certificación de estabilidad/robustez física. Los experimentos comparan modelos y escenarios definidos; el lector debe revisar sus supuestos.
