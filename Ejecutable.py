# In[Librerias]
#libreria para la obtencion de la data necesaria a partir de excel 
import pandas as pd

#Libreria para extraer columnas prototipos y ordenarlas dinamicamente
import re

#librerias para la regularizacion y calculo de la matriz de correlaciones
from sklearn.covariance import LedoitWolf
import numpy as np

#Libreria para el grafo
import networkx as nx
import matplotlib.pyplot as plt
from scipy.spatial.distance import euclidean

#Libreria grafico chasis 3d
import plotly.express as px

#Libreria coordinar ejecutable desde excel
import sys
import os 

# In[Carga de datos - SDS]

# Forzar a Python a trabajar en la carpeta del script
ruta_del_script = os.path.dirname(os.path.abspath(__file__))
os.chdir(ruta_del_script)

# 1. Capturamos la ruta enviada por Excel
# sys.argv[1] será la ruta del archivo que Excel le pase al script
if len(sys.argv) > 1:
    archivo = sys.argv[1]

# Ahora usamos la variable 'archivo' dinámicamente
excel_file = pd.ExcelFile(archivo)

def CreateData(archivo):

    # ================================
    # 1. HOJA FARO
    # ================================
    df_faro = pd.read_excel(
        archivo,
        sheet_name='FARO'
    )

    df_faro.columns = df_faro.columns.str.strip()

    columnas_necesarias = ['Feature', 'Property', 'Nominal' ,'Low Tol', 'Up Tol']
    
    df1 = df_faro[columnas_necesarias].copy()

    # FILTRO CLAVE: quitar Header Data
    df1 = df1[df1['Feature'] != 'Header Data'].reset_index(drop=True)

    # ================================
    # 2. HOJA FRAME
    # ================================
    df_frame = pd.read_excel(
        archivo,
        sheet_name='Frame Assy Inspection sheet ',
        header=4  # fila 5 (BSN)
    )

    df_frame.columns = df_frame.columns.astype(str).str.strip()

    # Quitar fila de metadata (fecha, etc.)
    df_frame = df_frame.iloc[1:].reset_index(drop=True)

    # ================================
    # 3. SOLO COLUMNAS BSN
    # ================================
    columnas_bsn = [col for col in df_frame.columns if col.startswith('BSN')]
    df2 = df_frame[columnas_bsn].copy()

    # ================================
    # 4. CORTAR CUANDO APARECE TEXTO
    # ================================
    df2_num = df2.apply(pd.to_numeric, errors='coerce')

    # Detectar hasta dónde hay datos reales
    filas_validas = df2_num.notna().any(axis=1)

    if not filas_validas.any():
        raise ValueError("No se encontraron datos numéricos en Frame")

    ultima_fila = filas_validas[filas_validas].index[-1]

    df2 = df2.iloc[:ultima_fila + 1].reset_index(drop=True)

    # Convertir definitivamente a numérico
    df2 = df2.apply(pd.to_numeric, errors='coerce')

    # ================================
    # 5. UNIR
    # ================================
    df = pd.concat([df1, df2], axis=1)

    # ================================
    # 6. PUNTO DE CONTROL
    # ================================
    df['Feature'] = df['Feature'].astype(str)
    df['Property'] = df['Property'].astype(str)

    df['Punto de control'] = df['Feature'] + '_' + df['Property']

    df = df.drop(columns=['Feature', 'Property'])

    cols = ['Punto de control'] + [col for col in df.columns if col != 'Punto de control']
    df = df[cols]

    df = df.set_index('Punto de control')
    
    # ================================
    # LIMPIEZA DE NANs
    # ================================
    
    # Quitar columnas completamente vacías
    df = df.dropna(axis=1, how='all')
    
    # Quitar filas con algun nan por agregar informacion fuera de los limites de los puntos de control
    df = df.dropna(axis=0, how='any')

    return df

#Obtenemos base de datos a partir de la funcion anterior
df = CreateData(archivo)

# In[detectar columnas de forma dinamica]

def obtener_columnas_prototipos(df):
    prototipos = [col for col in df.columns if str(col).startswith('BSN')]
    
    # Ordenar por el número dentro del nombre
    prototipos_ordenados = sorted(
        prototipos,
        key=lambda x: int(re.search(r'\d+', str(x)).group())
    )
    
    return prototipos_ordenados

# In[Función para el cálculo de la matriz de correlaciones]

def CorreRegularizada(df):
    "Función para calcular la matriz de correlaciones regularizada en caso de que el "
    "número de prototipos sea menor que el número de puntos de control"
    
    # Calcular covarianza regularizada
    prototipos = obtener_columnas_prototipos(df)
    X = df[prototipos]
    X = X.T
    #Convertimos las entradas de la matriz X a numero
    X = X.astype(float)
    
    #Hcemos calculo de la matriz de covarianzas regularizadas
    lw = LedoitWolf().fit(X)
    cov_mat = lw.covariance_

    # Convertir a Correlación de Pearson
    d = np.sqrt(np.diag(cov_mat))
    corr_mat = cov_mat / np.outer(d, d)

    # Crear un DataFrame con los nombres de los puntos para que sea legible
    df_corr = pd.DataFrame(corr_mat, index=X.columns, columns=X.columns)
    
    return df_corr

df_corre = CorreRegularizada(df)

# In[Funcion para detectar Puntos de control con errores]

def detectar_puntos_con_error(df, col_limite_inf, col_limite_sup):
    """
    Detecta puntos de control con al menos una desviación fuera de límites.
    
    Args:
        df: DataFrame con los puntos como índice.
        col_limite_inf: Nombre de la columna de límite inferior.
        col_limite_sup: Nombre de la columna de límite superior.
        col_inicial: Nombre de la columna donde incial prototipos
        col_final: Nombre de la columna donde terminanr los prototipos
        
    Returns:
        df_error: DataFrame filtrado solo con los puntos que tienen errores.
        puntos_criticos: Lista de nombres de puntos con error.
    """
    
    # 1. Extraemos los datos de los prototipos usando .loc para asegurar el rango
    # Esto selecciona todas las filas (:) y el rango de columnas específico
    # Seleccionamos prototipos
    prototipos = obtener_columnas_prototipos(df)
    datos_prototipos = df[prototipos]
    
    # Forzamos a que los límites sean series con el mismo índice exacto
    lim_sup = df[col_limite_sup].astype(float)
    lim_inf = df[col_limite_inf].astype(float)

    # Realizamos la comparación
    mask = datos_prototipos.apply(lambda col: (col > lim_sup) | (col < lim_inf), axis=0)
    
    filas_con_error = mask.any(axis=1)
    df_error = df[filas_con_error].copy()
    
    return df_error, df_error.index.tolist()

df_error, puntos_criticos = detectar_puntos_con_error(df, col_limite_inf='Low Tol', col_limite_sup = 'Up Tol')

# In[Función para realizar grafo]

def generar_grafo_influencia_dist(df, df_corr, puntos_con_error, umbral=0.82, dist_max=600):
    """
    Usa la columna 'Nominal' para calcular distancias físicas y filtrar el grafo.
    """
    # 1. Crear un diccionario de coordenadas reales (X, Y, Z) por cada Punto base
    # Agrupamos por el nombre antes del punto (ej. 'DIAM UPPER COMP LH_Center')
    coords_dict = {}
    puntos_base = set(idx.rsplit('.', 1)[0] for idx in df.index)
    
    for pb in puntos_base:
        try:
            x = df.loc[f"{pb}.x", 'Nominal']
            y = df.loc[f"{pb}.y", 'Nominal']
            z = df.loc[f"{pb}.z", 'Nominal']
            coords_dict[pb] = np.array([x, y, z])
        except KeyError:
            # Por si algún punto no tiene las 3 coordenadas
            continue

    # 2. Expandir lista de puntos con error y sus vecinos válidos
    puntos_relacionados = set(puntos_con_error)
    
    for p_error in puntos_con_error:
        # Nombre base del punto con error (sin .x, .y, .z)
        base_error = p_error.rsplit('.', 1)[0]
        if base_error not in coords_dict: continue
        
        # Candidatos de la matriz de correlación
        candidatos = df_corr.index[df_corr[p_error].abs() >= umbral].tolist()
        
        for cand in candidatos:
            base_cand = cand.rsplit('.', 1)[0]
            if base_cand not in coords_dict or cand == p_error: continue
            
            # Cálculo de distancia física usando la columna Nominal
            distancia = euclidean(coords_dict[base_error], coords_dict[base_cand])
            
            # FILTRO: Solo si están cerca o si la correlación es "inevitable" (>0.97)
            if distancia <= dist_max or abs(df_corr.loc[p_error, cand]) > 0.97:
                puntos_relacionados.add(cand)

    lista_final = list(puntos_relacionados)
    G = nx.Graph()

    # 3. Construir aristas con doble validación
    for i in range(len(lista_final)):
        for j in range(i + 1, len(lista_final)):
            p1, p2 = lista_final[i], lista_final[j]
            corr = df_corr.loc[p1, p2]
            
            base1, base2 = p1.rsplit('.', 1)[0], p2.rsplit('.', 1)[0]
            
            if base1 in coords_dict and base2 in coords_dict:
                d_fisica = euclidean(coords_dict[base1], coords_dict[base2])
                
                if abs(corr) >= umbral and (d_fisica <= dist_max or abs(corr) > 0.97):
                    G.add_edge(p1, p2, weight=round(corr, 2), dist=d_fisica)

    # 4. Visualización (Tu lógica de colores)
    G.remove_nodes_from(list(nx.isolates(G)))
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G, k=0.7)
    
    nx.draw_networkx_nodes(G, pos, nodelist=[n for n in G.nodes if n in puntos_con_error], 
                           node_color='salmon', node_size=600, label='Error')
    nx.draw_networkx_nodes(G, pos, nodelist=[n for n in G.nodes if n not in puntos_con_error], 
                           node_color='skyblue', node_size=400, label='Influencia')
    
    nx.draw_networkx_labels(G, pos, font_size=7)
    nx.draw_networkx_edges(G, pos, alpha=0.3, width=2)
    
    plt.title(f"Influencia Física (Filtro: {dist_max}mm | Corr: {umbral})")
    plt.legend()
    #plt.show()
    
    return G

def generar_dataframe_grupos(G, puntos_con_error, df_corr):
    """
    Versión mejorada: Incluye el Top 3 de variables correlacionadas con signo.
    """
    componentes = list(nx.connected_components(G))
    datos_resumen = []

    for i, nodos_grupo in enumerate(componentes):
        sub_G = G.subgraph(nodos_grupo)
        grados = dict(sub_G.degree())
        nodo_principal = max(grados, key=grados.get)
        
        for nodo in nodos_grupo:
            estado = "ERROR" if nodo in puntos_con_error else "INFLUENCIA (OK)"
            
            # --- NUEVO: Obtener Top 3 Correlaciones con signo ---
            # Filtramos la fila del nodo en la matriz de correlación original
            correlaciones_nodo = df_corr.loc[nodo].drop(labels=[nodo])
            # Obtenemos los 3 valores absolutos más altos pero conservamos el valor real (con signo)
            top_3_indices = correlaciones_nodo.abs().nlargest(3).index
            top_3_list = []
            for idx in top_3_indices:
                val = correlaciones_nodo[idx]
                signo = "+" if val > 0 else "" # El menos ya viene en el número
                top_3_list.append(f"{idx} ({signo}{val:.2f})")
            
            datos_resumen.append({
                'ID_Grupo': f"Grupo {i+1}",
                'Punto_de_Control': nodo,
                'Estado_Punto': estado,
                'Es_Punto_Principal': "SÍ" if nodo == nodo_principal else "No",
                'Top_3_Relaciones': " | ".join(top_3_list)
            })

    df_resumen = pd.DataFrame(datos_resumen)
    return df_resumen

# 1. Generar el grafo base (el que ya tienes)
#G = generar_grafo_influencia_total(df_corre, puntos_criticos, umbral=0.82)
G = generar_grafo_influencia_dist(df, df_corre, puntos_criticos, umbral=0.82, dist_max=600)

# 3. Crear el Excel para los ingenieros
df_reporte = generar_dataframe_grupos(G, puntos_criticos, df_corre)
#df_reporte.to_excel("Reporte_de_Correccion.xlsx", index=False)

# In[Graficas de 3d de cada prototipo BSN]

def preparar_datos_chasis(df):
    # 1. Creamos una copia para no afectar el original
    df_temp = df.copy()
    
    # 2. Separamos el nombre del punto de la componente (.x, .y, .z)
    # Esto crea dos columnas nuevas a partir del índice
    nombres_split = df_temp.index.str.rsplit('.', n=1, expand=True)
    df_temp['Punto_Base'] = nombres_split.get_level_values(0)
    df_temp['Eje'] = nombres_split.get_level_values(1)
    
    # 3. Pivotamos: Queremos que 'Punto_Base' sea el índice y 'x', 'y', 'z' sean columnas
    # Usamos la columna 'Nominal' que es la que contiene la coordenada ideal
    df_pivot = df_temp.pivot(index='Punto_Base', columns='Eje', values='Nominal')
    
    # Limpiamos nombres de columnas (pasar de 'x' a 'X')
    df_pivot.columns = [col.upper() for col in df_pivot.columns]
    
    return df_pivot

def preparar_datos_chasis_individual(df_original, df_resumen, chasis_id, 
                                     col_limite_inf, col_limite_sup):
    """
    Versión con Gravedad de Error: Calcula cuánto se aleja cada punto de su límite
    para escalar el tamaño en el gráfico 3D.
    """
    # 1. Coordenadas Base
    df_coords = preparar_datos_chasis(df_original)
    
    # 2. Análisis de errores y magnitudes exclusivo de ESTE chasis
    detalles_error = {}
    magnitudes_error = {} # Nueva estructura para guardar la distancia al límite
    datos_columna = df_original[chasis_id]
    
    for punto_idx in df_original.index:
        nombre_base = punto_idx.split('.')[0]
        eje = punto_idx.split('.')[-1].upper()
        
        valor = datos_columna.loc[punto_idx]
        sup = df_original.loc[punto_idx, col_limite_sup]
        inf = df_original.loc[punto_idx, col_limite_inf]
        
        tipo_falla = ""
        distancia = 0.0
        
        # MODIFICACIÓN AQUÍ: Agregamos la distancia al texto descriptivo
        if valor > sup: 
            distancia = valor - sup
            tipo_falla = f"Superior (Eje {eje}): {distancia:.3f} mm"
        elif valor < inf: 
            distancia = inf - valor
            tipo_falla = f"Inferior (Eje {eje}): {distancia:.3f} mm"
        
        if tipo_falla:
            # Guardar descripción (ahora ya incluye el eje y su magnitud)
            if nombre_base not in detalles_error: detalles_error[nombre_base] = []
            detalles_error[nombre_base].append(tipo_falla)
            
            # Mantenemos esta parte intacta porque Plotly necesita el valor máximo 
            # para calcular el tamaño (Size_Dinamico) de la burbuja
            if nombre_base not in magnitudes_error: magnitudes_error[nombre_base] = 0.0
            if distancia > magnitudes_error[nombre_base]:
                magnitudes_error[nombre_base] = distancia

    # 3. Vincular con la estructura de grupos
    df_resumen_limpio = df_resumen.copy()
    df_resumen_limpio['Punto_Base'] = df_resumen_limpio['Punto_de_Control'].apply(lambda p: p.split('.')[0])
    
    df_estructura_grupos = df_resumen_limpio.groupby('Punto_Base').agg({
        'ID_Grupo': 'first',
        'Top_3_Relaciones': 'first'
    })

    df_unido = pd.merge(df_coords, df_estructura_grupos, left_index=True, right_index=True, how='left')
    
    # 4. Inyectar detalles, estados y GRAVEDAD
    df_unido['Detalle_Falla'] = df_unido.index.map(lambda x: ", ".join(detalles_error.get(x, ["N/A"])))
    df_unido['Gravedad_Absoluta'] = df_unido.index.map(lambda x: magnitudes_error.get(x, 0.0))
    
    def asignar_estado_real(row):
        if row['Detalle_Falla'] != "N/A":
            return 'ERROR'
        elif pd.notna(row['ID_Grupo']) and row['ID_Grupo'] != 'Base':
            return 'INFLUENCIA (OK)'
        else:
            return 'Base'

    df_unido['Estado_Visual'] = df_unido.apply(asignar_estado_real, axis=1)
    
    # Limpieza final
    df_unido['ID_Grupo'] = df_unido['ID_Grupo'].fillna('Base')
    df_unido['Top_3_Relaciones'] = df_unido['Top_3_Relaciones'].fillna("Sin relaciones fuertes")

    return df_unido


def generar_reportes_individuales_3d(df, df_reporte, col_li='Low Tol', col_ls='Up Tol', umbral_info=0.82):
    """
    Orquestador de reportes: Genera archivos HTML individuales en la carpeta del proyecto.
    """
    # 1. Obtener la ruta base (donde está el Excel que procesamos)
    # Suponiendo que 'archivo' es la variable que recibes por sys.argv[1]
    ruta_base = os.path.dirname(os.path.abspath(archivo))
    
    # 2. Definir la carpeta de salida (crearla si no existe)
    carpeta_graficos = os.path.join(ruta_base, "Graficos 3D - individuales")
    if not os.path.exists(carpeta_graficos):
        os.makedirs(carpeta_graficos)

    prototipos = obtener_columnas_prototipos(df)
    df_prototipos = df[prototipos]
    lista_chasis = df_prototipos.columns.tolist()
    
    for chasis_id in lista_chasis:
        df_plot = preparar_datos_chasis_individual(df, df_reporte, chasis_id, col_li, col_ls)
        fig = crear_figura_3d_individual(df_plot, chasis_id, umbral_info)
        
        # 3. Construir nombre de archivo de forma dinámica
        nombre_archivo = os.path.join(carpeta_graficos, f"Analisis_3D_{chasis_id}.html")
        
        fig.write_html(nombre_archivo)
        print(f"Reporte generado: {nombre_archivo}")


def crear_figura_3d_individual(df_plot, chasis_id, umbral):
    """
    Genera el gráfico 3D con tamaños dinámicos para resaltar la gravedad del error.
    """
    # 1. Definir Leyendas
    def definir_leyenda(row):
        if row['Estado_Visual'] == 'ERROR':
            return f"Punto con Error ({row['ID_Grupo']})"
        elif row['Estado_Visual'] == 'INFLUENCIA (OK)':
            return f"Punto OK - Influencia ({row['ID_Grupo']})"
        else:
            return "Punto Base (Sin Error / Sin Relación)"

    df_plot['Leyenda_3D'] = df_plot.apply(definir_leyenda, axis=1)

    # 2. Mapa de Colores
    color_map = {"Punto Base (Sin Error / Sin Relación)": "lightgrey"}
    grupos_presentes = df_plot['ID_Grupo'].unique()
    for g in grupos_presentes:
        if g != 'Base':
            color_map[f"Punto con Error ({g})"] = "salmon"
            color_map[f"Punto OK - Influencia ({g})"] = "skyblue"

    # 3. Lógica de Tamaños Dinámicos
    # Los puntos OK se quedan pequeños (size=7), los de error crecen según la gravedad.
    # El multiplicador '* 20' es ajustable según qué tan grandes quieras ver las fallas.
    def calcular_tamano(row):
        if row['Estado_Visual'] == 'ERROR':
            return 12 + (row['Gravedad_Absoluta'] * 20) 
        elif row['Estado_Visual'] == 'INFLUENCIA (OK)':
            return 8
        else:
            return 5

    df_plot['Size_Dinamico'] = df_plot.apply(calcular_tamano, axis=1)

    # 4. Construcción del Gráfico
    fig = px.scatter_3d(
        df_plot, 
        x='X', y='Y', z='Z',
        color='Leyenda_3D', 
        symbol='ID_Grupo',
        size='Size_Dinamico', # Columna con tamaños variables
        size_max=40,          # Limita el tamaño máximo para que no sea ilegible
        text=df_plot.index,
        color_discrete_map=color_map,
        title=f"Estado de Calidad: {chasis_id} | Umbral Influencia: {umbral}",
        custom_data=['ID_Grupo', 'Detalle_Falla', 'Top_3_Relaciones', 'Gravedad_Absoluta']
    )

    # 5. Configuración del Hover (Ajustado para mostrar múltiples magnitudes)
    fig.update_traces(
        hovertemplate="<b>Punto: %{text}</b><br>" +
                      "Grupo: %{customdata[0]}<br>" +
                      "<b>Detalle de Falla(s):</b> %{customdata[1]}<br>" + 
                      "Error Máximo (Escala visual): %{customdata[3]:.3f} mm<br>" +
                      "Top Correlaciones:<br>%{customdata[2]}" +
                      "<extra></extra>"
    )
    
    fig.update_layout(
        scene=dict(aspectmode='data'),
        legend=dict(title_text='Estado y Clúster')
    )
    
    return fig

# In[Ejecutamos graficas]
# 1. Realizar el análisis general (Grafo y Reporte)
df_reporte = generar_dataframe_grupos(G, puntos_criticos, df_corre)

# 2. DISPARAR LA GENERACIÓN DE TODOS LOS HTML INDIVIDUALES
generar_reportes_individuales_3d(
    df = df, 
    df_reporte = df_reporte,
    umbral_info = 0.82
)

# In[EWMA para prototipos]


def ejecutar_ewma_semaforo_metalsa(df, col_li='Low Tol', col_ls='Up Tol', 
                                   n_calentamiento=3, lambda_val=0.266667, alpha_sigma=0.2,
                                   L=3.92, umbral_amarillo=0.825, factor_rojo=0.65):
    """
    EWMA con Sigma Adaptativa y Semaforización de 4 niveles.
    Optimizado para 3 piezas de calentamiento y reducción de Error Tipo 2.
    """
    prototipos = obtener_columnas_prototipos(df)
    df_prototipos = df[prototipos]
    prototipos = df_prototipos.columns.tolist()
    resultados_finales = []

    for variable in df.index:
        serie_cruda = df.loc[variable, prototipos].values.astype(float)
        t_sup = df.loc[variable, col_ls]
        t_inf = df.loc[variable, col_li]
        
        # 1. Inicialización de Sigma (Ingeniería como respaldo)
        sigma_ing = (t_sup - t_inf) / 6
        base = serie_cruda[:n_calentamiento]
        sigma_base = np.std(base, ddof=1) if len(base) > 1 and np.std(base) > 0 else sigma_ing
        sigma_adapt = sigma_base

        # 2. Parámetros del EWMA
        z = 0.0 # Objetivo nominal 0
        
        estado = "Verde"
        prototipo_falla = "N/A"
        falla_confirmada = False

        for i, x_real in enumerate(serie_cruda):
            # --- A. ROJO (TOLERANCIA) ---
            if (x_real > t_sup or x_real < t_inf) and not falla_confirmada:
                if i >= n_calentamiento:
                    estado = "Rojo (Tolerancia)"
                    prototipo_falla = prototipos[i]
                    falla_confirmada = True

            # --- B. EVOLUCIÓN EWMA ---
            # Z_i = lambda * X_i + (1 - lambda) * Z_{i-1}
            z = lambda_val * x_real + (1 - lambda_val) * z

            # --- C. SIGMA ADAPTATIVA ---
            if i >= n_calentamiento:
                ventana = serie_cruda[max(0, i-3):i+1]
                sigma_local = np.std(ventana, ddof=1) if len(ventana) > 1 else sigma_base
                sigma_adapt = (1 - alpha_sigma) * sigma_adapt + alpha_sigma * sigma_local

            # --- D. EVALUACIÓN DE LÍMITES DINÁMICOS ---
            # Desviación estándar del EWMA:
            sigma_z = sigma_adapt * np.sqrt((lambda_val/(2-lambda_val)) * (1-(1-lambda_val)**(2*(i+1))))
            limite_ewma = L * sigma_z

            # --- E. SEMAFORIZACIÓN HÍBRIDA ---
            if i >= n_calentamiento and not falla_confirmada:
                dist_limite = min(abs(t_sup - x_real), abs(x_real - t_inf))
                
                # ROJO ESTADÍSTICO: El promedio móvil es alto Y el valor actual está cerca del límite
                if abs(z) > limite_ewma:
                    if dist_limite < (sigma_adapt * factor_rojo): # Umbral de riesgo inminente
                        estado = "Rojo (Estadístico)"
                        prototipo_falla = prototipos[i]
                        falla_confirmada = True
                    else:
                        estado = "Amarillo (Tendencia Crítica)"
                
                # AMARILLO PREVENTIVO: Movimiento estadístico significativo
                elif abs(z) > (umbral_amarillo * limite_ewma):
                    estado = "Amarillo (Tendencia)"

        resultados_finales.append({
            'Variable': variable,
            'Semaforo': estado,
            'Origen_Falla': prototipo_falla
            #'Valor_EWMA': round(z, 4),
            #'Sigma_Final': round(sigma_adapt, 4),
            #'Dist_al_Limite': round(dist_limite, 3) if 'dist_limite' in locals() else 0
        })

    return pd.DataFrame(resultados_finales)

df_ewma = ejecutar_ewma_semaforo_metalsa(df, col_li='Low Tol', col_ls='Up Tol', n_calentamiento=3)

# In[Guardamos el nuevo data frame en la hoja ejecutada de excel]


# 1. Definir rutas para el intercambio
# Importante: Estas rutas deben coincidir EXACTAMENTE con las de VBA
ruta_temp_excel = archivo.replace(".xlsm", "_TEMP_RESULT.xlsx")
ruta_flag = archivo.replace(".xlsm", "_FINALIZADO.flag")

# 2. Guardar el DataFrame en el archivo temporal
# Esto SIEMPRE funciona porque es un archivo nuevo que no está abierto
df_ewma.to_excel(ruta_temp_excel, index=False)

# 3. Crear el archivo bandera
with open(ruta_flag, "w") as f:
    f.write("listo")

print(f"Proceso completado. Datos listos para importar.")
