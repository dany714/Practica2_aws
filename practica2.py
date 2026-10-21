"""Práctica 2: construir un esquema estrella con pandas y numpy, sin conexión AWS.

Grano de Fact_Ventas: una fila por id_transaccion (una operación de un producto).
Las claves son válidas para esta carga completa; no implementan cargas incrementales.
"""
import argparse
from pathlib import Path
import sys
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
SALIDA = BASE / 'salidas'
DIAS = {0:'Lunes', 1:'Martes', 2:'Miércoles', 3:'Jueves', 4:'Viernes', 5:'Sábado', 6:'Domingo'}


def generar_operativo():
    """Reproduce el generador de 500 operaciones del código base de la práctica."""
    rng = np.random.RandomState(101)
    n = 500
    return pd.DataFrame({
        'id_transaccion': range(1000,1000+n),
        'fecha_hora': pd.date_range(start='2026-01-01',periods=n,freq='h'),
        'cliente_nombre': rng.choice(['Juan Pérez','María Gómez','Carlos Ruiz'],n),
        'cliente_ciudad': rng.choice(['Puebla','CDMX','Guadalajara'],n),
        'producto_nombre': rng.choice(['Laptop Dell','Mouse Logi','Monitor LG'],n),
        'categoria_prod': rng.choice(['Cómputo','Accesorios','Pantallas'],n),
        'precio_unitario': rng.choice([15000.0,350.0,4500.0],n),
        'cantidad': rng.randint(1,5,n),
    })


def construir_modelo(df):
    """Deduplica combinaciones de atributos y asigna claves subrogadas enteras."""
    cliente_cols = ['cliente_nombre','cliente_ciudad']
    producto_cols = ['producto_nombre','categoria_prod','precio_unitario']
    cliente = df[cliente_cols].drop_duplicates().reset_index(drop=True)
    cliente.insert(0,'id_cliente_sk',np.arange(1,len(cliente)+1))
    producto = df[producto_cols].drop_duplicates().reset_index(drop=True)
    producto.insert(0,'id_producto_sk',np.arange(1,len(producto)+1))
    tiempo = pd.DataFrame({'fecha_completa':sorted(df.fecha_hora.dt.normalize().unique())})
    tiempo.insert(0,'id_tiempo_sk',np.arange(1,len(tiempo)+1))
    tiempo['anio'] = tiempo.fecha_completa.dt.year
    tiempo['mes'] = tiempo.fecha_completa.dt.month
    tiempo['dia'] = tiempo.fecha_completa.dt.day
    tiempo['dia_semana'] = tiempo.fecha_completa.dt.dayofweek.map(DIAS)
    tiempo['es_fin_semana'] = tiempo.fecha_completa.dt.dayofweek.ge(5)
    # many_to_one evita que una dimensión duplicada multiplique operaciones.
    ventas = df.merge(cliente,on=cliente_cols,how='left',validate='many_to_one')
    ventas = ventas.merge(producto,on=producto_cols,how='left',validate='many_to_one')
    ventas['fecha_completa'] = ventas.fecha_hora.dt.normalize()
    ventas = ventas.merge(tiempo,on='fecha_completa',how='left',validate='many_to_one')
    ventas['monto_total'] = (ventas.cantidad * ventas.precio_unitario).round(2)
    hechos = ventas[['id_transaccion','id_cliente_sk','id_producto_sk','id_tiempo_sk','cantidad','monto_total']].copy()
    return cliente,producto,tiempo,hechos


def validar(df,cliente,producto,tiempo,hechos):
    """Verifica grano, integridad referencial y conservación de medidas."""
    checks = {'500 operaciones conservadas':len(df)==len(hechos)==500,
              'Una fila por transacción':hechos.id_transaccion.is_unique,
              'Sin valores nulos en hechos':not hechos.isna().any().any(),
              'Cantidad conservada':int(df.cantidad.sum())==int(hechos.cantidad.sum()),
              'Monto conservado':bool(np.isclose((df.cantidad*df.precio_unitario).sum(),hechos.monto_total.sum())),
              'Monto correcto por transacción':bool(np.allclose(
                  df.set_index('id_transaccion').eval('cantidad * precio_unitario').sort_index(),
                  hechos.set_index('id_transaccion').monto_total.sort_index()))}
    for key,dim in [('id_cliente_sk',cliente),('id_producto_sk',producto),('id_tiempo_sk',tiempo)]:
        checks[f'PK única y no nula: {key}'] = dim[key].is_unique and not dim[key].isna().any()
        checks[f'FK válida: {key}'] = hechos[key].isin(dim[key]).all()
    checks['Atributos de fin de semana consistentes'] = (
        tiempo.es_fin_semana == tiempo.fecha_completa.dt.dayofweek.ge(5)).all()
    if not all(checks.values()):
        raise ValueError('Validación fallida: '+', '.join(k for k,v in checks.items() if not v))
    return checks


def resumenes(hechos,producto,tiempo):
    """Agregaciones OLAP que conservan las medidas de la tabla de hechos."""
    ventas = hechos.merge(producto,on='id_producto_sk',validate='many_to_one')
    por_categoria = ventas.groupby('categoria_prod',as_index=False).agg(
        operaciones=('id_transaccion','count'),unidades=('cantidad','sum'),ventas_totales=('monto_total','sum'))
    por_dia = hechos.merge(tiempo,on='id_tiempo_sk',validate='many_to_one').groupby(
        'fecha_completa',as_index=False).agg(operaciones=('id_transaccion','count'),ventas_totales=('monto_total','sum'))
    return por_categoria,por_dia


def sql_valor(value):
    if isinstance(value,(bool,np.bool_)):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value,(pd.Timestamp,np.datetime64)):
        return "'"+pd.Timestamp(value).strftime('%Y-%m-%d')+"'"
    if isinstance(value,(int,np.integer)):
        return str(int(value))
    if isinstance(value,(float,np.floating)):
        return f'{float(value):.2f}'
    return "'"+str(value).replace("'","''")+"'"


def exportar_sql(cliente,producto,tiempo,hechos):
    """DDL/DML para una base PostgreSQL vacía; no abre una conexión real."""
    sql = ['-- Práctica 2. Ejecutar en una base vacía de PostgreSQL.','BEGIN;',
      'CREATE TABLE dim_cliente (id_cliente_sk INTEGER PRIMARY KEY, cliente_nombre VARCHAR(100) NOT NULL, cliente_ciudad VARCHAR(100) NOT NULL, UNIQUE(cliente_nombre,cliente_ciudad));',
      'CREATE TABLE dim_producto (id_producto_sk INTEGER PRIMARY KEY, producto_nombre VARCHAR(100) NOT NULL, categoria_prod VARCHAR(100) NOT NULL, precio_unitario NUMERIC(12,2) NOT NULL CHECK(precio_unitario > 0), UNIQUE(producto_nombre,categoria_prod,precio_unitario));',
      'CREATE TABLE dim_tiempo (id_tiempo_sk INTEGER PRIMARY KEY, fecha_completa DATE NOT NULL UNIQUE, anio INTEGER NOT NULL, mes INTEGER NOT NULL, dia INTEGER NOT NULL, dia_semana VARCHAR(12) NOT NULL, es_fin_semana BOOLEAN NOT NULL);',
      'CREATE TABLE fact_ventas (id_transaccion INTEGER PRIMARY KEY, id_cliente_sk INTEGER NOT NULL REFERENCES dim_cliente(id_cliente_sk), id_producto_sk INTEGER NOT NULL REFERENCES dim_producto(id_producto_sk), id_tiempo_sk INTEGER NOT NULL REFERENCES dim_tiempo(id_tiempo_sk), cantidad INTEGER NOT NULL CHECK(cantidad > 0), monto_total NUMERIC(14,2) NOT NULL CHECK(monto_total >= 0));']
    for name,df in [('dim_cliente',cliente),('dim_producto',producto),('dim_tiempo',tiempo),('fact_ventas',hechos)]:
        for row in df.itertuples(index=False,name=None):
            sql.append(f'INSERT INTO {name} ({", ".join(df.columns)}) VALUES ({", ".join(map(sql_valor,row))});')
    sql.append('COMMIT;')
    sql.append('SELECT COUNT(*) AS operaciones, SUM(cantidad) AS unidades, SUM(monto_total) AS ventas_totales FROM fact_ventas;')
    (SALIDA/'esquema_estrella.sql').write_text('\n'.join(sql)+'\n',encoding='utf-8')


def mostrar(titulo,df,filas=5):
    print('\n'+titulo)
    print(f'Dimensiones: {len(df)} filas x {len(df.columns)} columnas')
    print(df.head(filas).to_string(index=False))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paso',choices=['origen','dimensiones','hechos','validar','todo'])
    args=parser.parse_args(argv)
    try:
        df=generar_operativo()
        c,p,t,h=construir_modelo(df)
        checks=validar(df,c,p,t,h)
        cat,dias=resumenes(h,p,t)
        SALIDA.mkdir(parents=True,exist_ok=True)
        for name,tabla in [('operativo',df),('dim_cliente',c),('dim_producto',p),('dim_tiempo',t),('fact_ventas',h),('ventas_por_categoria',cat),('ventas_por_dia',dias)]:
            tabla.to_csv(SALIDA/(name+'.csv'),index=False,encoding='utf-8-sig')
        exportar_sql(c,p,t,h)
        print('PRÁCTICA 2 | ESQUEMA ESTRELLA CON PANDAS')
        if args.paso in ('origen','todo'):
            mostrar('DATOS OPERATIVOS OLTP | SEMILLA 101',df)
            print('\nGrano: una operación de un producto por id_transaccion.')
            print('Producto, categoría y precio son variables sintéticas independientes, como en el código base.')
        if args.paso in ('dimensiones','todo'):
            mostrar('DIM_CLIENTE | PK id_cliente_sk',c)
            mostrar('DIM_PRODUCTO | PK id_producto_sk',p)
            mostrar('DIM_TIEMPO | PK id_tiempo_sk',t,8)
            print('\nAmpliación: dia_semana y es_fin_semana. SK enteras desde 1.')
        if args.paso in ('hechos','todo'):
            mostrar('FACT_VENTAS | PK id_transaccion; FK a las tres dimensiones',h)
            print(f'\nTotal de operaciones: {len(h)}')
            print(f'Total de unidades: {int(h.cantidad.sum())}')
            print(f'Monto total de ventas: {h.monto_total.sum():,.2f}')
            mostrar('ANÁLISIS OLAP | VENTAS POR CATEGORÍA',cat)
        if args.paso in ('validar','todo'):
            print('\nVALIDACIONES DEL MODELO')
            for label in checks: print('OK | '+label)
            print(f'\nSQL generado: salidas/esquema_estrella.sql')
            print('Incluye PK, FK, DDL y DML. No se realizó conexión a PostgreSQL ni EC2.')
            print('Exportados: operativo, dimensiones, hechos y resúmenes en CSV.')
        print('\nProceso completado correctamente.')
        return 0
    except (OSError,ValueError,pd.errors.MergeError) as error:
        print(f'No se pudo completar el modelo: {error}',file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
