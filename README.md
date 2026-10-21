# Práctica 2: Esquema estrella de ventas

Transformación de 500 operaciones en un esquema estrella con pandas y numpy. El modelo contiene las dimensiones Cliente, Producto y Tiempo, y la tabla de hechos Fact_Ventas.

Dim_Tiempo incluye el día de la semana y un indicador de fin de semana. El programa valida las relaciones entre tablas y exporta los resultados en CSV y SQL.

## Ejecución

En PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe practica2.py todo
```

También se puede ejecutar cada etapa con `origen`, `dimensiones`, `hechos` o `validar`.

## Archivos

- `practica2.py`: generación, transformación y validación.
- `salidas/`: tablas, resúmenes y script para PostgreSQL.
- `modelo_estrella.png`: diagrama del modelo.
- `modelo_estrella.mmd`: diagrama editable.

El procesamiento se realiza localmente. El SQL se genera para una base PostgreSQL vacía.
