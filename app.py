import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import plotly.graph_objects as go
import plotly.express as px

# 0. Creamos una barra superior con dos columnas compactas: Estado y Botón
col_estado, col_btn = st.columns([5, 1], vertical_alignment="center")

with col_estado:
    # Aquí va tu indicador actual de que la app está viva / conectada
    st.markdown("🟢 **Estado:** App Activa y conectada")

with col_btn:
    # Botón pequeño para forzar la actualización
    if st.button("🔄 Actualizar", help="Forzar recarga de datos desde Drive"):
        st.cache_data.clear()  # Limpia la caché para obligar a leer de nuevo
        st.rerun()             # Recarga la aplicación inmediatamente

# 1. Configuración de la página (ideal para vista móvil)
st.set_page_config(page_title="Mis Finanzas", layout="centered", initial_sidebar_state="collapsed")
st.title("📊 Mi Tablero Financiero")

# 2. Cargar los datos desde Google Sheets
# Usamos caché con tiempo de expiración (ttl) para que se actualice solo
@st.cache_data(ttl=300)
def cargar_datos():
    sheet_url = "https://docs.google.com/spreadsheets/d/127OcNwAVYwsR6CZY-oIimSWT9mSpSjy6/edit?usp=sharing&ouid=117083243035701965898&rtpof=true&sd=true"
    csv_url = sheet_url.replace("/edit?usp=sharing", "/export?format=csv")
    
    df = pd.read_csv(csv_url)
    
    # Limpiamos la columna Importe por si Pandas la lee como texto
    if 'Importe' in df.columns:
        df['Importe'] = df['Importe'].astype(str).str.replace('$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Importe'] = pd.to_numeric(df['Importe'], errors='coerce').fillna(0)
        
    # Convertimos la fecha correctamente
    if 'MesAnio' in df.columns:
        df['MesAnio'] = pd.to_datetime(df['MesAnio'], format='%d/%m/%Y', errors='coerce')
        
    return df

df = cargar_datos()

# 3. Filtros
meses_disponibles = df['MesAnio'].dropna().dt.strftime('%Y-%m').unique()
mes_seleccionado = st.selectbox("Seleccionar Mes", sorted(meses_disponibles, reverse=True))

# Filtrar la base de datos según el mes elegido
df_mes = df[df['MesAnio'].dt.strftime('%Y-%m') == mes_seleccionado]

# 4. Cálculos de Indicadores (KPIs)
ingresos = df_mes[df_mes['Condición'] == 'Ingreso']['Importe'].sum()
gastos = df_mes[df_mes['Condición'] == 'Gasto']['Importe'].sum()
margen_neto = ingresos - gastos

# Indicador del Porcentaje de Margen respecto a lo cobrado
porcentaje_margen = (margen_neto / ingresos) * 100 if ingresos > 0 else 0

# Cálculo del Disponible Diario Real (Contemplando supermercado)
gasto_super = df_mes[(df_mes['Condición'] == 'Gasto') & (df_mes['Item'].str.contains('super', case=False, na=False))]['Importe'].sum()
diaria_real = margen_neto / 30 if margen_neto > 0 else 0

# 5. Interfaz Visual
col1, col2, col3 = st.columns(3)
col1.metric("Ingresos", f"${ingresos:,.0f}")
col2.metric("Gastos", f"${gastos:,.0f}")
col3.metric("Margen Neto", f"${margen_neto:,.0f}", f"{porcentaje_margen:.1f}%")

# Semáforo Financiero (Regla del 20%)
if porcentaje_margen >= 20:
    st.success(f"✅ ¡Excelente! Retuviste el {porcentaje_margen:.1f}% de tus ingresos. Tienes margen para invertir.")
elif porcentaje_margen > 0:
    st.warning(f"⚠️ Margen del {porcentaje_margen:.1f}%. El objetivo financiero recomendado es superar el 20%.")
else:
    st.error("🚨 Margen negativo. Los gastos superaron los ingresos este mes.")

st.info(f"💡 Caja chica diaria para extras: **${diaria_real:,.0f}** *(Compras fuertes de super ya cubiertas por ${gasto_super:,.0f})*")

# 6. Gráfico de gastos por rubro ordenado de mayor a menor gasto de izquierda a derecha
st.subheader("Gastos por Rubro")

df_gastos = df_mes[df_mes['Condición'] == 'Gasto'].copy()

# Calculamos el total por rubro para ordenar los rubros de mayor a menor
totales_rubro = df_gastos.groupby('Rubro', as_index=False)['Importe'].sum()
totales_rubro = totales_rubro.sort_values(by='Importe', ascending=False)
orden_rubros = totales_rubro['Rubro'].tolist()

df_gastos = df_gastos.sort_values(by=['Rubro', 'Importe'], ascending=[True, False])

paletas_rubro = {
    'Depto': px.colors.sequential.Reds,
    'Auto': px.colors.sequential.Blues,
    'Comida': px.colors.sequential.Greens,
    'Juan': px.colors.sequential.Tealgrn,
    'Salud': px.colors.sequential.Oranges,
    'Monotributo': px.colors.sequential.Purples,
    'Creditos': px.colors.sequential.YlOrBr,
    'Otros': px.colors.sequential.Greys,
    'Servicios': px.colors.sequential.PuBu,
    'Subscripción': px.colors.sequential.RdPu
}

color_map = {}
for rubro, grupo in df_gastos.groupby('Rubro'):
    items = grupo['Item'].unique()
    n = len(items)
    paleta = paletas_rubro.get(rubro, px.colors.sequential.Viridis)
    for i, item in enumerate(items):
        if n == 1:
            idx = len(paleta) // 2
        else:
            idx = int((n - 1 - i) * (len(paleta) - 1) / (n - 1))
        color_map[item] = paleta[idx]

fig = px.bar(
    df_gastos, 
    x='Rubro', 
    y='Importe', 
    color='Item',
    barmode='stack',
    text='Importe',
    color_discrete_map=color_map,
    category_orders={'Rubro': orden_rubros}
)

fig.update_traces(
    texttemplate='%{text:$.2s}', 
    textposition='inside',
    insidetextanchor='middle'
)

fig.add_trace(
    go.Scatter(
        x=totales_rubro['Rubro'],
        y=totales_rubro['Importe'],
        text=[f"${val:,.0f}" if val < 1000 else f"${val/1000:.0f}k" for val in totales_rubro['Importe']],
        mode='text',
        textposition='top center',
        textfont=dict(size=11, color='white'),
        showlegend=False,
        hoverinfo='skip'
    )
)

fig.update_layout(
    xaxis_title="Rubro",
    yaxis_title="Importe ($)",
    uniformtext_minsize=8,
    uniformtext_mode='hide',
    margin=dict(t=60),
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

# 7. Evolución Histórica Reciente con Resumen Ajustado y Gráfico Espaciado
st.subheader("Evolución Histórica Reciente")

meses_todos = sorted(df['MesAnio'].dropna().dt.strftime('%Y-%m').unique(), reverse=True)

meses_hist_seleccionados = st.multiselect(
    "Seleccionar meses a incluir en la evolución:",
    options=meses_todos,
    default=meses_todos[:12] if len(meses_todos) >= 12 else meses_todos
)

if meses_hist_seleccionados:
    df_evolucion = df[df['MesAnio'].dt.strftime('%Y-%m').isin(meses_hist_seleccionados)].copy()
    df_evolucion['Mes_Str'] = df_evolucion['MesAnio'].dt.strftime('%Y-%m')
    df_resumen_hist = df_evolucion.groupby(['Mes_Str', 'Condición'], as_index=False)['Importe'].sum()
    
    df_pivot = df_resumen_hist.pivot(index='Mes_Str', columns='Condición', values='Importe').reset_index()
    if 'Ingreso' not in df_pivot.columns: df_pivot['Ingreso'] = 0
    if 'Gasto' not in df_pivot.columns: df_pivot['Gasto'] = 0
    
    df_pivot['Diferencia'] = df_pivot['Ingreso'] - df_pivot['Gasto']
    df_pivot['Porcentaje'] = (df_pivot['Diferencia'] / df_pivot['Ingreso']) * 100
    df_pivot['Porcentaje'] = df_pivot['Porcentaje'].fillna(0)
    
    tot_ingresos = df_pivot['Ingreso'].sum()
    tot_gastos = df_pivot['Gasto'].sum()
    tot_dif = tot_ingresos - tot_gastos
    tot_porc = (tot_dif / tot_ingresos * 100) if tot_ingresos > 0 else 0
    
    st.markdown("##### 📌 Resumen acumulado del período seleccionado")
    
    # Tarjetas con HTML/Markdown para asegurar que los números grandes entren sin cortarse
    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    with col_r1:
        st.markdown(f"<p style='margin:0; font-size:14px; color:gray;'>Total Ingresos</p><h3 style='margin:0; font-size:20px;'>${tot_ingresos:,.0f}</h3>", unsafe_allow_html=True)
    with col_r2:
        st.markdown(f"<p style='margin:0; font-size:14px; color:gray;'>Total Gastos</p><h3 style='margin:0; font-size:20px;'>${tot_gastos:,.0f}</h3>", unsafe_allow_html=True)
    with col_r3:
        st.markdown(f"<p style='margin:0; font-size:14px; color:gray;'>Diferencia Total</p><h3 style='margin:0; font-size:20px;'>${tot_dif:,.0f}</h3>", unsafe_allow_html=True)
    with col_r4:
        st.markdown(f"<p style='margin:0; font-size:14px; color:gray;'>Margen % Total</p><h3 style='margin:0; font-size:20px;'>{tot_porc:.1f}%</h3>", unsafe_allow_html=True)
    
    st.markdown("---")

    def formatear_etiqueta(val):
        if val >= 1_000_000:
            return f"${val/1_000_000:.1f}M"
        elif val >= 1_000:
            return f"${val/1_000:.0f}k"
        else:
            return f"${val:,.0f}"

    fig_evolucion = go.Figure()

    # Línea de Ingresos
    fig_evolucion.add_trace(go.Scatter(
        x=df_pivot['Mes_Str'],
        y=df_pivot['Ingreso'],
        mode='lines+markers+text',
        name='Ingreso',
        line=dict(color='#2ecc71', width=3),
        text=[formatear_etiqueta(v) for v in df_pivot['Ingreso']],
        textposition='top center',
        textfont=dict(size=10, color='#2ecc71')
    ))

    # Línea de Gastos
    fig_evolucion.add_trace(go.Scatter(
        x=df_pivot['Mes_Str'],
        y=df_pivot['Gasto'],
        mode='lines+markers+text',
        name='Gasto',
        line=dict(color='#e74c3c', width=3),
        text=[formatear_etiqueta(v) for v in df_pivot['Gasto']],
        textposition='bottom center',
        textfont=dict(size=10, color='#e74c3c')
    ))

    # Texto central en dos renglones (Diferencia arriba, porcentaje abajo)
    df_pivot['Y_Mid'] = (df_pivot['Ingreso'] + df_pivot['Gasto']) / 2
    df_pivot['Texto_Dif'] = df_pivot.apply(
        lambda r: f"Δ {formatear_etiqueta(r['Diferencia'])}<br>({r['Porcentaje']:.1f}%)", axis=1
    )

    fig_evolucion.add_trace(go.Scatter(
        x=df_pivot['Mes_Str'],
        y=df_pivot['Y_Mid'],
        mode='text',
        name='Diferencia / Margen',
        text=df_pivot['Texto_Dif'],
        textfont=dict(size=10, color='#f1c40f', family='sans-serif'),
        showlegend=False,
        hoverinfo='skip'
    ))

    # Calculamos un rango con margen vertical extra para que los textos no se choquen
    max_val = max(df_pivot['Ingreso'].max(), df_pivot['Gasto'].max()) * 1.15
    min_val = min(df_pivot['Ingreso'].min(), df_pivot['Gasto'].min()) * 0.85

    fig_evolucion.update_layout(
        xaxis_title="Mes",
        yaxis_title="Importe ($)",
        yaxis=dict(range=[min_val, max_val]), # Expande el eje Y verticalmente
        margin=dict(t=40, b=20),
        legend_title="Concepto",
        hovermode='x unified'
    )

    st.plotly_chart(fig_evolucion, use_container_width=True)
else:
    st.info("Seleccione al menos un mes para visualizar la evolución histórica.")

# 8. Tabla de gastos fijos de Papi para el mes seleccionado
st.subheader(f"Gastos del mes ({mes_seleccionado})")

# Nos aseguramos de tratar la columna Fijo como numérica para filtrar bien el '1'
df_mes['Fijo_num'] = pd.to_numeric(df_mes['Fijo'], errors='coerce')

# Filtramos por Gasto, Fijo == 1 y que el detalle mencione a Papi
df_papi = df_mes[
    (df_mes['Condición'] == 'Gasto') & 
    (df_mes['Fijo_num'] == 1) & 
    (df_mes['Detalle fijo'].str.contains('Papi', case=False, na=False))
].copy()

if not df_papi.empty:
    df_tabla_papi = df_papi[['Item', 'Importe']].copy()
    
    total_papi = df_tabla_papi['Importe'].sum()
    
    df_tabla_papi['Importe'] = df_tabla_papi['Importe'].apply(lambda x: f"${x:,.0f}")
    
    df_total_row = pd.DataFrame({'Item': ['TOTAL'], 'Importe': [f"${total_papi:,.0f}"]})
    df_tabla_papi = pd.concat([df_tabla_papi, df_total_row], ignore_index=True)
    
    st.dataframe(df_tabla_papi, hide_index=True, use_container_width=True)
else:
    st.info(f"No se registraron gastos fijos de Papi en el período {mes_seleccionado}.")
