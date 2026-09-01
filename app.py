import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

#Prueba de app
st.write("🟢 ¡La app está viva!")

# 1. Configuración de la página (ideal para vista móvil)
st.set_page_config(page_title="Mis Finanzas", layout="centered", initial_sidebar_state="collapsed")
st.title("📊 Mi Tablero Financiero")

# 2. Cargar los datos
# Usamos cache para que no lea el Excel cada vez que tocas un botón
@st.cache_data
def cargar_datos():
    df = pd.read_excel("Libro de cuentas personales.xlsx", sheet_name='Hoja1')
    df['MesAnio'] = pd.to_datetime(df['MesAnio'])
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
