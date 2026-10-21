# Práctica 2 — Esquema estrella de ventas

Transformación de 500 operaciones OLTP a tres dimensiones y una tabla de hechos.
Implementación con pandas y numpy. La persistencia real en PostgreSQL/EC2 es
opcional en el enunciado: esta versión genera CSV y un script DDL/DML para una
base PostgreSQL vacía; no necesita servidor ni credenciales.

## Visual Studio Code en Windows

Extrae el ZIP y abre la carpeta `practica2_esquema_estrella`, donde está
`practica2.py`, desde Archivo > Abrir carpeta. Abre una terminal PowerShell.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si `py` no existe pero `python --version` funciona, usa `python -m venv .venv`.
No hay que activar el entorno ni cambiar permisos de PowerShell.

## Pasos y capturas

Ejecuta por separado:

```powershell
.\.venv\Scripts\python.exe practica2.py origen
.\.venv\Scripts\python.exe practica2.py dimensiones
.\.venv\Scripts\python.exe practica2.py hechos
.\.venv\Scripts\python.exe practica2.py validar
```

1. **Origen:** captura 500 filas x 8 columnas y los primeros registros.
2. **Dimensiones:** captura Dim_Cliente (9 x 3), Dim_Producto (27 x 4) y
   Dim_Tiempo (21 x 7). Usa dos capturas si es necesario. Deben verse las SK
   y los atributos `dia_semana` y `es_fin_semana`, con sábados y domingos.
3. **Hechos:** captura Fact_Ventas (500 x 6), las 1237 unidades, el monto total
   8160000.00 y el resumen por categoría. Puedes separar la tabla y el resumen.
4. **Validar:** captura las comprobaciones OK y la generación del SQL.

Cada paso reconstruye el mismo modelo con semilla 101 y exporta sus resultados;
no depende de haber ejecutado antes otro paso. `todo` muestra todas las salidas.
Amplía la terminal para que las tablas sean legibles. Las fechas son fijas
(del 1 al 21 de enero de 2026) y los resultados reproducibles.

`modelo_estrella.png` es el diagrama listo para insertar en el reporte.
`modelo_estrella.mmd` conserva su definición editable en Mermaid.

## Construcción del modelo

- Grano: una operación de un producto por id_transaccion.
- Dim_Cliente: combina nombre y ciudad, elimina duplicados y asigna SK desde 1.
- Dim_Producto: combina producto, categoría y precio, elimina duplicados y asigna SK.
- Dim_Tiempo: una fila por fecha; SK secuencial desde 1, año, mes, día y ampliación.
- Fact_Ventas: tres FK, identificador de operación, cantidad y monto_total.
- `monto_total = cantidad * precio_unitario`.
- Cruces con `how='left'` y `validate='many_to_one'`: validación posterior
  comprueba nulos y que no se pierdan ni multipliquen operaciones.

Se reproduce el generador del docente: producto, categoría y precio se eligen
independientemente. Por eso hay 27 combinaciones de producto, no solo 3.
Cada combinación recibe una SK; no se impone un catálogo comercial adicional.
La fecha YYYYMMDD del ejemplo se sustituye por una SK secuencial de tiempo,
para separar la clave técnica de sus atributos de calendario.
Las SK se reconstruyen en esta carga completa; no hay carga incremental.

## Ampliación requerida

`dia_semana` muestra el nombre en español sin depender del idioma del sistema.
`es_fin_semana` es True para sábado y domingo. Estos dos atributos cubren la
ampliación de la práctica sin agregar dimensiones innecesarias.
Se incluyen agregaciones OLAP por categoría y fecha.

## Archivos exportados

La carpeta `salidas` contiene operativo.csv, dim_cliente.csv, dim_producto.csv,
dim_tiempo.csv, fact_ventas.csv, ventas_por_categoria.csv, ventas_por_dia.csv
(escritos en UTF-8 con BOM para facilitar apertura en Excel) y esquema_estrella.sql.

El SQL crea las tablas con PK, FK, restricciones e inserta dimensiones antes de
hechos, dentro de una transacción. No contiene DROP ni borra tablas existentes.
Debe ejecutarse en una base vacía; repetirlo en una base ya cargada genera un
error porque las tablas existen. Solo genera el archivo: no conecta a PostgreSQL.

Opcional, si tienes PostgreSQL configurado en cualquier equipo:

```bash
psql -h HOST -U USUARIO -d BASE -f salidas/esquema_estrella.sql
```

HOST, USUARIO y BASE se sustituyen por los datos reales. No pongas contraseñas
en el código ni en el repositorio.

## Repositorio

Subir practica2.py, requirements.txt, .gitignore, README.md, modelo_estrella.png,
modelo_estrella.mmd y salidas/. La carpeta .vscode es opcional. No subir .venv.
No es necesario usar el repositorio de la práctica 1; prepara uno independiente.

## Ubuntu/Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python practica2.py origen
.venv/bin/python practica2.py dimensiones
.venv/bin/python practica2.py hechos
.venv/bin/python practica2.py validar
```
