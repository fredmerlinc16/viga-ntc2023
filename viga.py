import streamlit as st
import numpy as np
import pandas as pd
import math

# Configuración de la página de Streamlit
st.set_page_config(page_title="Diseño de Vigas NTC 2023", layout="wide")

st.title("🏗️ Diseñador de Vigas de Concreto Reforzado")
st.subheader("Cumplimiento con las Normas Técnicas Complementarias (NTC - Concreto 2023)")

# --- BARRA LATERAL: ENTRADA DE DATOS ---
st.sidebar.header("1. Materiales")
fc = st.sidebar.number_input("f'c - Resistencia del Concreto (kg/cm²)", value=250, step=50)
fy = st.sidebar.number_input("fy - Fluencia del Acero (kg/cm²)", value=4200, step=100)

# Factores de resistencia según NTC 2023
FR_flexion = 0.90
FR_cortante = 0.75

st.sidebar.header("2. Geometría de la Viga")
b = st.sidebar.number_input("Base, b (cm)", value=30, step=5)
h = st.sidebar.number_input("Peralte total, h (cm)", value=50, step=5)
rec = st.sidebar.number_input("Recubrimiento al centroide, d' (cm)", value=5, step=1)
L = st.sidebar.number_input("Longitud del claro, L (m)", value=6.0, step=0.5)

d = h - rec  # Peralte efectivo

st.sidebar.header("3. Cargas de Diseño (Facturadas)")
Mu = st.sidebar.number_input("Momento Último, Mu (ton-m)", value=12.0, step=1.0) * 100000  # Convertir a kg-cm
Vu = st.sidebar.number_input("Cortante Último, Vu (ton)", value=8.0, step=1.0) * 1000       # Convertir a kg
W_servicio = st.sidebar.number_input("Carga Lineal de Servicio (ton/m)", value=2.0, step=0.2) * 10 # Convertir a kg/cm

st.sidebar.header("4. Refuerzo Propuesto")
as_propuesto = st.sidebar.number_input("Área de acero longitudinal colocada, As (cm²)", value=12.0, step=1.0)
av_estribo = st.sidebar.number_input("Área de 1 estribo (2 ramas de No. 3 = 1.42 cm²)", value=1.42, step=0.1)
s_estribo = st.sidebar.number_input("Separación de estribos, s (cm)", value=15, step=5)

# --- PROCESAMIENTO Y CÁLCULOS ---

# 1. REVISIÓN POR FLEXIÓN
# Factor beta1 para el bloque de esfuerzos de Whitney (NTC 2023)
if fc <= 280:
    beta1 = 0.85
else:
    beta1 = max(0.85 - 0.05 * ((fc - 280) / 70), 0.65)

# Cuantías límite
rho_min = 0.7 * math.sqrt(fc) / fy
rho_balanceada = (beta1 * 0.85 * fc / fy) * (6000 / (6000 + fy))
rho_max = 0.9 * rho_balanceada  # Límite reglamentario aproximado para ductilidad alta

rho_actual = as_propuesto / (b * d)

# Momento Resistente (MR)
# Bloque de esfuerzos: a = (As * fy) / (0.85 * f'c * b)
a = (as_propuesto * fy) / (0.85 * fc * b)
Mn = as_propuesto * fy * (d - a / 2)
MR = FR_flexion * Mn

# 2. REVISIÓN POR CORTANTE
# Resistencia del concreto elemental Vcr (NTC 2023 simplificado para vigas ordinarias)
# Vcr = FR * 0.5 * sqrt(f'c) * b * d
Vcr = FR_cortante * 0.5 * math.sqrt(fc) * b * d

# Resistencia aportada por los estribos Vsr
Vsr = FR_cortante * (av_estribo * fy * d) / s_estribo
VR = Vcr + Vsr

# 3. REVISIÓN DE DEFLEXIONES (MÉTODO SIMPLIFICADO)
# Momento de Inercia Grueso (Ig) e Inercia Agrietada (Icr) aproximada
Ig = (b * h**3) / 12
# Deflexión inmediata estimada bajo carga uniforme de servicio (5wL^4 / 384EI)
E_concreto = 14000 * math.sqrt(fc)  # Modulo de elasticidad aproximado en kg/cm²
L_cm = L * 100
deflexion_inmediata = (5 * W_servicio * L_cm**4) / (384 * E_concreto * Ig)

# Factor a largo plazo (NTC considera un multiplicador por flujo plástico, usualmente ~2.0 si no hay acero de compresión)
deflexion_largo_plazo = deflexion_inmediata * 2.0
deflexion_total = deflexion_inmediata + deflexion_largo_plazo

# Límite admisible clásico (L / 240)
deflexion_permisible = L_cm / 240

# --- MOSTRAR RESULTADOS EN INTERFAZ UI ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Momento de Diseño (MR)", value=f"{MR/100000:.2f} ton-m")
    if MR >= Mu:
        st.success("✅ FLEXIÓN APROBADA")
    else:
        st.error("❌ FLEXIÓN INSUFICIENTE")

with col2:
    st.metric(label="Cortante de Diseño (VR)", value=f"{VR/1000:.2f} ton")
    if VR >= Vu:
        st.success("✅ CORTANTE APROBADO")
    else:
        st.error("❌ CORTANTE INSUFICIENTE")

with col3:
    st.metric(label="Deflexión Estimada Total", value=f"{deflexion_total:.2f} cm")
    if deflexion_total <= deflexion_permisible:
        st.success("✅ DEFLEXIÓN PERMISIBLE OK")
    else:
        st.error("❌ EXCEDE DEFLEXIÓN LÍMITE")

# --- TABLA DETALLADA ---
st.write("### Resumen Técnico de Revisiones")

estatus_flexion = "APROBADO" if MR >= Mu else "RECHAZADO"
estatus_cortante = "APROBADO" if VR >= Vu else "RECHAZADO"
estatus_flecha = "APROBADO" if deflexion_total <= deflexion_permisible else "RECHAZADO"

df_resultados = pd.DataFrame({
    "Concepto de Revisión": ["Flexión (Momento)", "Cortante (Estribos)", "Estado Límite de Servicio (Flecha)"],
    "Demanda (Actuante)": [f"{Mu/100000:.2f} ton-m", f"{Vu/1000:.2f} ton", f"{deflexion_total:.2f} cm"],
    "Capacidad (Límite)": [f"{MR/100000:.2f} ton-m", f"{VR/1000:.2f} ton", f"{deflexion_permisible:.2f} cm"],
    "Estatus": [estatus_flexion, estatus_cortante, estatus_flecha]
})

st.dataframe(df_resultados, use_container_width=True)

# Alertas extras de cuantía de acero
st.write("### Chequeos Reglamentarios de Acero")
if rho_actual < rho_min:
    st.warning(f"⚠️ Alerta: La cuantía propuesta ({rho_actual:.4f}) es MENOR que la mínima reglamentaria ({rho_min:.4f}). Agrega más varillas.")
elif rho_actual > rho_max:
    st.error(f"🚨 Alerta: La cuantía propuesta ({rho_actual:.4f}) es MAYOR que la máxima permitida ({rho_max:.4f}). La viga podría tener una falla frágil. Aumenta la sección de concreto.")
else:
    st.success(f"👍 Cuantía de acero balanceada y en rango óptimo: {rho_actual:.4f} (Mín: {rho_min:.4f} | Máx: {rho_max:.4f})")