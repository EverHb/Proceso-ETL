import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, IntegrityError

try:
    from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
except ImportError:
    raise SystemExit(
        "Error: no se encontró 'config.py'. Copia 'config.py.example' como "
        "'config.py' y llena tus credenciales reales antes de correr el script."
    )

# ============================================================
# FASE 1: EXTRACCIÓN (Extract)
# ============================================================
print("--- Iniciando Fase 1: Extracción ---")

try:
    df_crudo = pd.read_csv('foods_dataset_.csv', encoding='utf-8')
except FileNotFoundError:
    raise SystemExit("Error: no se encontró 'foods_dataset_.csv'. Verifica la ruta/nombre del archivo.")
except UnicodeDecodeError:
    # Fallback por si el CSV no está en utf-8
    df_crudo = pd.read_csv('foods_dataset_.csv', encoding='latin-1')

print(f"Datos extraídos exitosamente: {df_crudo.shape[0]} registros encontrados.")

# ============================================================
# FASE 2: TRANSFORMACIÓN (Transform)
# ============================================================
print("\n--- Iniciando Fase 2: Transformación ---")

# 1. Limpieza de datos
# Eliminamos filas que no tengan ID de restaurante, nombre de plato o precio (datos basura)
df_limpio = df_crudo.dropna(subset=['restaurant_id', 'dish_name', 'price']).copy()

# 1.1 Validación de precio: debe ser numérico y positivo
df_limpio['price'] = pd.to_numeric(df_limpio['price'], errors='coerce')
filas_antes_precio = len(df_limpio)
df_limpio = df_limpio[df_limpio['price'] > 0]
print(f"Filas descartadas por precio inválido/no numérico: {filas_antes_precio - len(df_limpio)}")

# 2. Estandarización de Fechas
df_limpio['created_at'] = pd.to_datetime(df_limpio['created_at'], format='mixed', dayfirst=True).dt.date

# 3. Lógica de Negocio: Mapeo Relacional
# Transformamos las categorías de texto a los IDs de las tablas creadas en MySQL
map_cuisine = {'Other': 1, 'Chinese': 2, 'Italian': 3, 'Indian': 4}
map_category = {'Main Course': 1, 'Starter': 2, 'Beverage': 3, 'Dessert': 4}
map_food_type = {'Vegan': 1, 'Non-Veg': 2, 'Jain': 3, 'Veg': 4}
map_spice_level = {'Mild': 1, 'Spicy': 2, 'Medium': 3}
map_tax_rate = {0: 1, 5: 2, 12: 3, 18: 4}

# 3.1 Validación previa: mostrar valores únicos que no coinciden con cada mapeo,
# para detectar problemas de mayúsculas/espacios/typos antes de mapear "a ciegas"
def validar_mapeo(serie, mapeo, nombre_columna):
    valores_no_mapeados = set(serie.dropna().unique()) - set(mapeo.keys())
    if valores_no_mapeados:
        print(f"⚠️  Valores en '{nombre_columna}' sin mapeo definido: {valores_no_mapeados}")

validar_mapeo(df_limpio['cuisine_type'], map_cuisine, 'cuisine_type')
validar_mapeo(df_limpio['category'], map_category, 'category')
validar_mapeo(df_limpio['food_type'], map_food_type, 'food_type')
validar_mapeo(df_limpio['spice_level'], map_spice_level, 'spice_level')
validar_mapeo(df_limpio['tax_gst_%'], map_tax_rate, 'tax_gst_%')

# Aplicamos el mapeo para generar las llaves foráneas
df_limpio['cuisine_id'] = df_limpio['cuisine_type'].map(map_cuisine)
df_limpio['category_id'] = df_limpio['category'].map(map_category)
df_limpio['food_type_id'] = df_limpio['food_type'].map(map_food_type)
df_limpio['spice_level_id'] = df_limpio['spice_level'].map(map_spice_level)
df_limpio['tax_rate_id'] = df_limpio['tax_gst_%'].map(map_tax_rate)

# 4. Estructuración Final
# Seleccionamos únicamente las columnas que coinciden con nuestra tabla 'dish' en MySQL
df_final = df_limpio[[
    'restaurant_id', 'dish_name', 'description', 'price',
    'image_url', 'created_at', 'cuisine_id', 'category_id',
    'food_type_id', 'spice_level_id', 'tax_rate_id'
]].copy()

# Eliminamos solo los registros cuyas llaves foráneas (mapeos) fallaron.
# 'description' e 'image_url' quedan libres de este filtro porque son campos
# opcionales y no deben provocar la pérdida de un plato válido.
columnas_criticas = ['cuisine_id', 'category_id', 'food_type_id', 'spice_level_id', 'tax_rate_id']
filas_antes_mapeo = len(df_final)
df_final = df_final.dropna(subset=columnas_criticas)
print(f"Filas descartadas por mapeo fallido en catálogos: {filas_antes_mapeo - len(df_final)}")

print("Transformación completada con precisión. Datos estandarizados.")
print(f"Registros finales listos para cargar: {len(df_final)}")

# ============================================================
# FASE 3: CARGA (Load)
# ============================================================
print("\n--- Iniciando Fase 3: Carga ---")

# --- Conexión a MySQL ---
# Requiere: pip install pymysql sqlalchemy
# IMPORTANTE: la base de datos (schema) indicada en config.py debe existir
# previamente en el servidor MySQL. Este script NO la crea.
# Las tablas de catálogo (cuisine, category, food_type, spice_level, tax_rate)
# también deben existir y estar pobladas (ver crear_tablas.sql), o la carga
# fallará por llaves foráneas.
#
# Las credenciales viven en config.py (NO se sube a git, ver .gitignore).
# Copia config.py.example como config.py y llena tus datos reales.

if not all([DB_USER, DB_PASSWORD, DB_NAME]):
    raise SystemExit(
        "Error: faltan credenciales en config.py. Verifica que DB_USER, "
        "DB_PASSWORD y DB_NAME estén completos."
    )

connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(connection_string)

try:
    # Verificamos que la conexión y la base de datos existan antes de cargar
    with engine.connect() as conexion_prueba:
        print(f"Conexión exitosa a la base de datos '{DB_NAME}'.")

    # IMPORTANTE: la tabla 'etl_platos_procesados' ya debe existir en MySQL
    # (creada con el script crear_tablas.sql), con sus llaves foráneas hacia
    # los catálogos. Por eso usamos if_exists="append" en vez de "replace":
    # "replace" haría DROP TABLE y perderíamos las FKs, porque pandas no
    # las recrea al generar la tabla desde cero.
    #
    # Como este proceso puede correr varias veces (por ejemplo, cada vez que
    # llega un CSV nuevo), primero vaciamos la tabla para no duplicar
    # registros de corridas anteriores, sin perder su estructura ni las FKs.
    with engine.begin() as conexion:
        conexion.execute(text("TRUNCATE TABLE etl_platos_procesados;"))
        print("Tabla vaciada antes de la nueva carga (estructura y FKs se conservan).")

    # Insertar los datos nuevos, respetando la estructura y FKs existentes
    df_final.to_sql(
        name="etl_platos_procesados",
        con=engine,
        if_exists="append",  # Solo inserta filas; NO borra ni recrea la tabla
        index=False
    )

    print("¡Éxito! Datos cargados en MySQL.")
    print(f"Tabla actualizada: etl_platos_procesados en '{DB_NAME}'")

except OperationalError as e:
    print("Error de conexión: verifica que la base de datos exista, "
          "que el servidor MySQL esté corriendo y que las credenciales sean correctas.")
    print(f"Detalle: {e}")

except IntegrityError as e:
    print("Error de llave foránea: algún cuisine_id/category_id/food_type_id/"
          "spice_level_id/tax_rate_id no existe en su tabla de catálogo. "
          "Verifica que crear_tablas.sql se haya ejecutado y que los IDs coincidan.")
    print(f"Detalle: {e}")

except Exception as e:
    print(f"Error durante la carga: {e}")

finally:
    engine.dispose()