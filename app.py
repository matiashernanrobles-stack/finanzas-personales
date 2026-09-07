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
