import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

#Prueba de app
st.write("🟢 ¡La app está viva!")

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

# 6. Gráfico simple de gastos por rubro
st.subheader("Gastos por Rubro")
gastos_rubro = df_mes[df_mes['Condición'] == 'Gasto'].groupby('Rubro')['Importe'].sum().reset_index()
fig = px.bar(gastos_rubro, x='Rubro', y='Importe', text='Importe')
fig.update_traces(texttemplate='%{text:$.2s}', textposition='outside')
st.plotly_chart(fig, use_container_width=True)
