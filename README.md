# AutomataStudio

Herramienta educativa de escritorio para crear, editar, convertir, simular y
analizar Autómatas Finitos Deterministas (AFD) y No Deterministas (AFND),
con interfaz gráfica moderna en PyQt6.

## Características

- Editor visual de estados, alfabeto y transiciones (con transiciones épsilon).
- Lienzo interactivo: arrastrar estados, zoom con la rueda del mouse, auto-organizar.
- Simulación de cadenas paso a paso (AFD y AFND), con resaltado en el diagrama.
- Conversión AFND → AFD por construcción de subconjuntos (con tabla de subconjuntos).
- Conversión AFD → AFND equivalente.
- Minimización de AFD (particiones mostradas iteración por iteración).
- Análisis de propiedades: determinista, completo, conexo, estados inaccesibles y muertos.
- Guardar/abrir proyectos en JSON, exportar diagrama a PNG y reporte completo a PDF.
- Historial de simulaciones y conversiones recientes.
- Deshacer/rehacer, modo oscuro, ejemplos precargados, validaciones con mensajes claros.

## Estructura del proyecto

```
AutomataStudio/
├── main.py                 # Punto de entrada
├── requirements.txt
├── models/                 # Modelo de datos del autómata (Automaton)
├── algorithms/              # Simulación, subset construction, minimización, propiedades
├── controllers/             # Mediador entre modelo, algoritmos y vistas (undo/redo)
├── views/                   # Ventana principal, paneles, lienzo gráfico
├── utils/                   # Validadores, historial, import/export, temas
├── resources/                # Ejemplos precargados
└── tests/                    # Pruebas de humo (algoritmos y GUI)
```

## Instalación

Requiere Python 3.10+ (probado con 3.14).

```bash
cd AutomataStudio
pip install -r requirements.txt
```

## Ejecución

```bash
python main.py
```

## Pruebas

```bash
python tests/test_algorithms.py   # Pruebas de los algoritmos (simulación, conversión, minimización)
python tests/smoke_gui.py         # Prueba de extremo a extremo de la interfaz (usa QT_QPA_PLATFORM=offscreen si no hay pantalla)
```

## Uso rápido

1. **Estados**: pestaña "Estados" del panel izquierdo → "+ Agregar". Seleccione un
   estado y use "Marcar inicial" o "Alternar aceptación".
2. **Alfabeto**: pestaña "Alfabeto" → agregue los símbolos que usará el autómata.
3. **Transiciones**: pestaña "Transiciones" → elija origen, símbolo (incluye ε) y
   destino, luego "+ Agregar transición".
4. **Dibujo**: el autómata se dibuja automáticamente en el panel central. Arrastre
   los estados para reorganizarlos; use la rueda del mouse para hacer zoom.
5. **Simular**: escriba una cadena en el panel inferior y presione "Simular". Use
   los controles Anterior/Siguiente/Auto para recorrer la simulación paso a paso.
6. **Convertir/minimizar**: panel derecho → "AFND → AFD", "Minimizar AFD" o
   "AFD → AFND". Cada operación muestra el proceso antes de aplicarse con el botón
   "Usar como autómata actual".
7. **Propiedades**: pestaña "Propiedades" del panel derecho.
8. **Guardar/exportar**: menú Archivo → Guardar (JSON), Exportar imagen (PNG) o
   Exportar reporte (PDF).
9. **Ejemplos**: menú Ejemplos → autómatas precargados de práctica.

## Notas de arquitectura

- `models/automaton.py` contiene una única clase `Automaton` que representa tanto
  AFD como AFND: un AFND es simplemente un autómata cuya función de transición
  puede mapear a más de un estado destino, y/o usar transiciones épsilon.
- Los algoritmos (`algorithms/`) son puros: reciben un `Automaton` y devuelven un
  resultado con los pasos intermedios, sin depender de Qt.
- `controllers/automaton_controller.py` es el único punto de mutación del modelo;
  registra cada cambio en el historial de deshacer/rehacer y emite la señal Qt
  `model_changed` para que todas las vistas se actualicen.
