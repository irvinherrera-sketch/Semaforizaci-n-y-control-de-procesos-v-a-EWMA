# SDS Analytics – Semaforización EWMA y Diagnóstico Dimensional para METALSA

Sistema automatizado de análisis estadístico y diagnóstico dimensional para procesos de **Try Out de chasis automotriz**, desarrollado para **METALSA**.

El proyecto transforma reportes dimensionales complejos en información accionable mediante:
- **Semaforización EWMA en tiempo real**
- **Detección de patrones de desviación**
- **Análisis de correlaciones físicas y estadísticas**
- **Visualización 3D interactiva**
- **Integración directa con Microsoft Excel mediante VBA**

---

## 📌 Objetivo

Reducir el tiempo de diagnóstico y retrabajo durante la fase de **Try Out**, identificando:

- puntos fuera de tolerancia
- tendencias preventivas antes de falla
- relaciones entre puntos de control
- posibles causas raíz en estaciones o herramentales

Todo desde una interfaz familiar para ingeniería: **Excel + Python**.

---

## ⚙️ Tecnologías utilizadas

### Python
- pandas
- numpy
- scipy
- scikit-learn
- networkx
- plotly

### Microsoft Excel
- VBA (Visual Basic for Applications)

### Métodos estadísticos
- EWMA (Exponentially Weighted Moving Average)
- Grid Search
- Simulación Monte Carlo
- Ledoit-Wolf Shrinkage
- Correlación de Pearson
- Teoría de grafos

---

## 🧠 Metodología

## 1. Semaforización EWMA

Cada punto de control se evalúa automáticamente y clasifica en:

| Estado | Descripción |
|---|---|
| 🟢 Verde | Proceso estable |
| 🟡 Amarillo | Tendencia preventiva |
| 🔴 Rojo (Estadístico) | Riesgo de salida de especificación |
| 🔴 Rojo (Tolerancia) | Valor fuera de LSL/USL |

---

## 2. Optimización de hiperparámetros

Se ejecutó:

- **Monte Carlo Simulation**
- **Grid Search** sobre 480 combinaciones

Escenarios evaluados:

- Proceso ideal
- Proceso ruidoso
- Shift brusco
- Drift gradual

Configuración seleccionada:

```txt
L = 3.92
λ = 0.2667
α = 0.2
Umbral amarillo = 0.825
Factor rojo = 0.65
```

Resultados:

- ✅ 100% detección de drift
- ✅ 100% detección de shift
- ✅ 7% falsos positivos en escenario ideal

---

## 3. Identificación de grupos de influencia

Para encontrar relaciones entre puntos:

### Estadística

- Correlación de Pearson
- Ledoit-Wolf (n << p)

### Restricciones físicas

- Distancia euclidiana máxima:
```txt
600 unidades
```

### Resultado

Agrupación automática de puntos correlacionados:

- misma zona de ensamble
- misma estación
- posible origen común de falla

---

## 4. Reportes 3D interactivos

Se generan archivos HTML independientes.

Incluyen:

- rotación libre
- hover con información detallada
- gravedad proporcional al tamaño del punto
- top 3 correlaciones
- color por estado

Esquema visual:

| Color | Significado |
|---|---|
| Gris | Punto base |
| Salmón | Punto con error |
| Azul | Punto influenciado |
| Morado | Error aislado |

---

## 🖥️ Integración con Excel (Windows)

El flujo está dividido en dos macros:

### 1. Ejecutar análisis

Lanza Python desde VBA:

```vb
EjecutarPython_Windows()
```

Acciones:

- abre terminal
- ejecuta motor estadístico
- procesa Excel
- genera resultados temporales

---

### 2. Importar resultados

```vb
ImportarResultados_Windows()
```

Acciones:

- importa resultados al libro
- crea hoja nueva
- limpia archivos temporales

---

## 🚀 Flujo de uso

1. Abrir archivo `.xlsm`
2. Cargar reportes FARO / Frame Assy
3. Presionar:

```txt
Ejecutar análisis
```

4. Esperar procesamiento
5. Presionar:

```txt
Importar semáforo
```

6. Revisar:
   - hoja de resultados EWMA
   - reporte HTML 3D

---

## 📈 Beneficios

- reducción de tiempos de respuesta
- menor retrabajo
- diagnóstico objetivo
- trazabilidad estadística
- visualización accesible
- integración con flujo actual de planta

---

## 🏭 Aplicación

Proyecto desarrollado como herramienta de apoyo para:

**METALSA**
Control dimensional y optimización de procesos de ensamble de chasis automotriz.

---

## 👨‍💻 Autor

Tu nombre aquí

GitHub:
```txt
https://github.com/irvinherrera-sketch
```

---
