import streamlit as st
import numpy as np
import pandas as pd
import math
import matplotlib.pyplot as plt

# Configuración de página
st.set_page_config(page_title="Diseño Profesional de Vigas NTC 2023", layout="wide")

st.title("🏗️ Plataforma de Diseño de Vigas de Concreto - NTC 2023")
st.caption("Módulo Avanzado: Flexión, Cortante Dinámico, Deflexiones y Detallado Sísmico (Zonas Confinadas)")

# --- BARRA LATERAL: ENTRADA DE DATOS ---
st.sidebar.header("1. Materiales y Factores")
fc = st.sidebar.number_input("f'c - Concreto (kg/cm²)", value=250, step=50)
fy = st.sidebar.number_input("fy - Acero Longitudinal (kg/cm²)", value=4200, step=100)
fyv = st.sidebar.number_input("fyv - Acero de Estribos (kg/cm²)", value=4200, step=100)

FR_flexion = 0.90
FR_cortante = 0.75

st.sidebar.header("2. Geometría")
b = st.sidebar.number_input("Base, b (cm)", value=30, step=5)
h = st.sidebar.number_input("Peralte total, h (cm)", value=50, step=5)
rec = st.sidebar.number_input("Recubrimiento centroide, d' (cm)", value=5, step=1)
L = st.sidebar.number_input("Claro de la viga, L (m)", value=6.0, step=0.5)
d = h - rec # Peralte efectivo

st.sidebar.header("3. Cargas de Diseño")
Mu = st.sidebar.number_input("Momento Último Actuante, Mu (ton-m)", value=12.0, step=1.0) * 100000 
Vu = st.sidebar.number_input("Cortante Último en el Apoyo, Vu (ton)", value=10.0, step=1.0) * 1000     
W_servicio = st.sidebar.number_input("Carga de Servicio (ton/m)", value=2.0, step=0.2) * 10 

# --- REQUERIMIENTO 1: ACERO INFERIOR Y SUPERIOR PROPUESTO ---
st.sidebar.header("4. Refuerzo Longitudinal Propuesto")
as_inf_prop = st.sidebar.number_input("Acero Inferior (Tracción), As (cm²)", value=12.0, step=1.0)
as_sup_prop = st.sidebar.number_input("Acero Superior (Compresión), As' (cm²)", value=4.0, step=1.0)

st.sidebar.header("5. Refuerzo Transversal Propuesto")
av_estribo = st.sidebar.number_input("Área de estribo (ej. 2 ramas No. 3 = 1.42 cm²)", value=1.42, step=0.1)

# --- NÚCLEO DE CÁLCULO E INGENIERÍA ---
# Beta 1 para bloque de Whitney
beta1 = 0.85 if fc <= 280 else max(0.85 - 0.05 * ((fc - 280) / 70), 0.65)

# REQUERIMIENTO 3: INDICADORES DE ACERO MÍNIMO Y MÁXIMO
rho_min = 0.7 * math.sqrt(fc) / fy
as_min = rho_min * b * d
rho_b = (beta1 * 0.85 * fc / fy) * (6000 / (6000 + fy))
rho_max = 0.75 * rho_b # Ductilidad comercial estándar
as_max = rho_max * b * d

# REQUERIMIENTO 6: CÁLCULO AUTOMÁTICO REQUERIDO (MÉTODO INVERSO)
# Acero longitudinal teórico para Mu
if Mu > 0:
    # Solución de la ecuación cuadrática de flexión simple
    rn = Mu / (FR_flexion * b * d**2 * 0.85 * fc)
    if rn < 0.25: # Límite de falla por flexión simple
        rho_req = 0.85 * fc / fy * (1 - math.sqrt(1 - 2 * rn))
        as_long_req = max(rho_req * b * d, as_min)
    else:
        as_long_req = as_max # Requiere doble refuerzo de diseño obligatoriamente
else:
    as_long_req = as_min

# Cortante a una distancia 'd' del apoyo (Optimización de Cortante a medio peralte efectivo / peralte efectivo)
# Suponiendo distribución hiperbólica o lineal, reducimos el cortante actuante en el nodo crítico:
Vu_diseno = max(Vu * (1 - (d / (L * 100 / 2))), 0.5 * Vu) 
Vcr = FR_cortante * 0.5 * math.sqrt(fc) * b * d
vsr_necesario = max(Vu_diseno - Vcr, 0)
if vsr_necesario > 0:
    s_trans_req = (FR_cortante * av_estribo * fyv * d) / vsr_necesario
else:
    s_trans_req = d * 0.5 # Por reglamento por cuantía mínima

# REQUERIMIENTO 4: SEPARACIÓN MÁXIMA SÍSMICA NTC 2023 (Cercano a nodos vs Central)
# Cercano a nodos (Confinamiento): Mínimo de (d/4, 8 veces diám varilla menor, 24 diám estribo, o 10cm)
s_max_nodo = min(d / 4, 10.0) 
# Zona Central: Mínimo de (d/2 o 25 cm)
s_max_central = min(d / 2, 25.0)

# Flexión real con acero propuesto (Considerando aporte a compresión simplificado)
a_real = ((as_inf_prop - as_sup_prop) * fy) / (0.85 * fc * b)
MR = FR_flexion * (as_inf_prop - as_sup_prop) * fy * (d - a_real / 2) + FR_flexion * as_sup_prop * fy * (d - rec)

# Deflexiones
Ig = (b * h**3) / 12
E_c = 14000 * math.sqrt(fc)
L_cm = L * 100
flecha_inst = (5 * W_servicio * L_cm**4) / (384 * E_c * Ig)
# Factor de flujo plástico afectado por el acero superior (NTC 2023: \xi / (1 + 50*rho'))
rho_prime = as_sup_prop / (b * d)
lambda_intermedio = 2.0 / (1 + 50 * rho_prime)
flecha_total = flecha_inst * (1 + lambda_intermedio)
flecha_permisible = L_cm / 240

# --- DISEÑO DE LAS PESTAÑAS (TABS) ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Cuadro de Control y Estatus", "📈 Diagramas Estructurales", "📐 Cálculo Teórico (Requerido)", "🧱 Detalles del Armado (2D)"])

# --- PESTAÑA 1: CONTROL ---
with tab1:
    st.header("Indicadores de Cumplimiento")
    
    # Render de Requerimiento 3 en formato Métricas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Acero Mínimo NTC", f"{as_min:.2f} cm²", "Límite Inferior")
    col2.metric("Acero Máximo NTC", f"{as_max:.2f} cm²", "Límite de Ductilidad")
    col3.metric("Momento Resistente Real", f"{MR/100000:.2f} T-m", f"Demandado: {Mu/100000:.1f} T-m")
    col4.metric("Deflexión a Largo Plazo", f"{flecha_total:.2f} cm", f"Límite: {flecha_permisible:.2f} cm")
    
    st.subheader("Hojas de Validación")
    res_df = pd.DataFrame({
        "Criterio": ["Flexión (Momento)", "Deflexión Máxima", "Cuantía de Acero Inferior"],
        "Propuesto / Calculado": [f"{MR/100000:.2f} ton-m", f"{flecha_total:.2f} cm", f"{as_inf_prop:.2f} cm²"],
        "Restricción Reglamentaria": [f"≥ {Mu/100000:.2f} ton-m", f"≤ {flecha_permisible:.2f} cm", f"Entre {as_min:.1f} y {as_max:.1f} cm²"],
        "Estado": ["✅ OK" if MR >= Mu else "❌ INSUFICIENTE",
                   "✅ OK" if flecha_total <= flecha_permisible else "❌ EXCEDE",
                   "✅ OK" if as_min <= as_inf_prop <= as_max else "⚠️ FUERA DE RANGO"]
    })
    st.dataframe(res_df, use_container_width=True)

# --- PESTAÑA 2: DIAGRAMAS (REQUERIMIENTO 2) ---
with tab2:
    st.header("Diagramas de Elementos Mecánicos (Viga Simplemente Apoyada)")
    
    x = np.linspace(0, L, 100)
    # Momento: M(x) = (w * x / 2) * (L - x) + Ajustado para simular el Mu máximo en centro
    w_equiv = (8 * (Mu/100000)) / (L**2)
    momento_x = (w_equiv * x / 2) * (L - x)
    # Cortante: V(x) = w * (L/2 - x) aproximado al Vu de apoyo
    cortante_x = (2 * (Vu/1000) / L) * (L/2 - x)
    # Deflexión aproximada x
    deflexion_x = (flecha_total) * (16/5) * ((x/L)**4 - 2*(x/L)**3 + (x/L))

    fig, axs = plt.subplots(3, 1, figsize=(10, 8))
    
    # Gráfica de Momento
    axs[0].plot(x, momento_x, color='darkred', lw=2)
    axs[0].fill_between(x, momento_x, color='salmon', alpha=0.3)
    axs[0].set_title(f"Diagrama de Momentos Flectores (Máx: {Mu/100000:.2f} ton-m)")
    axs[0].set_ylabel("M [ton-m]")
    axs[0].grid(True)
    
    # Gráfica de Cortante
    axs[1].plot(x, cortante_x, color='navy', lw=2)
    axs[1].fill_between(x, cortante_x, color='lightblue', alpha=0.3)
    axs[1].set_title(f"Diagrama de Fuerzas Cortantes (Máx en Apoyo: {Vu/1000:.2f} ton)")
    axs[1].set_ylabel("V [ton]")
    axs[1].grid(True)
    
    # Gráfica de Deflexión
    axs[2].plot(x, deflexion_x, color='green', lw=2)
    axs[2].fill_between(x, deflexion_x, color='lightgreen', alpha=0.3)
    axs[2].set_title(f"Perfil de Deflexiones Totales Diferidas (Máx: {flecha_total:.2f} cm)")
    axs[2].set_xlabel("Longitud de la viga [m]")
    axs[2].set_ylabel("$\delta$ [cm]")
    axs[2].invert_yaxis()
    axs[2].grid(True)
    
    plt.tight_layout()
    st.pyplot(fig)

# --- PESTAÑA 3: CÁLCULO TEÓRICO (REQUERIMIENTO 6 Y 4) ---
with tab3:
    st.header("Dimensionamiento Requerido Automatizado")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Refuerzo Longitudinal Sugerido")
        st.info(f"📐 **Acero Longitudinal Requerido por Flexión:** {as_long_req:.2f} cm²")
        st.write(f"- Acero Mínimo por Norma: **{as_min:.2f} cm²**")
        st.write(f"- Acero Propuesto Inferior actual: **{as_inf_prop:.2f} cm²**")
        
    with c2:
        st.subheader("Distribución Arbitrada de Estribos (NTC 2023)")
        st.warning(f"⚡ **Separación Máxima en Zona de Nodos (Confinada):** {s_max_nodo:.1f} cm")
        st.success(f"🍃 **Separación Máxima en Zona Central:** {s_max_central:.1f} cm")
        st.write(f"- Cortante reducido a distancia *d*: **{Vu_diseno/1000:.2f} ton** (Optimización de apoyo)")
        st.write(f"- Separación teórica estricta por cálculo: **{s_trans_req:.1f} cm**")

# --- PESTAÑA 4: GRÁFICO DE ARMADO (REQUERIMIENTO 5) ---
with tab4:
    st.header("Representación Visual del Armado Propuesto (Corte Transversal)")
    
    fig_sect, ax_s = plt.subplots(figsize=(4, 5))
    # Contorno de la sección de concreto
    ax_s.rect = plt.Rectangle((0, 0), b, h, color="lightgrey", alpha=0.7, label="Concreto")
    ax_s.add_patch(ax_s.rect)
    
    # Dibujar Estribo perimeter
    estribo_rec = plt.Rectangle((2.5, 2.5), b-5, h-5, fill=False, edgecolor="blue", linewidth=3, label=f"Estribo de Refuerzo")
    ax_s.add_patch(estribo_rec)
    
    # Dibujar acero longitudinal inferior (Puntos rojos)
    ax_s.scatter([5, b/2, b-5], [5, 5, 5], color="red", s=180, zorder=5, label=f"As Inf ({as_inf_prop} cm²)")
    # Dibujar acero longitudinal superior (Puntos rojos huecos/más chicos)
    ax_s.scatter([5, b-5], [h-5, h-5], color="darkred", s=140, zorder=5, label=f"As Sup ({as_sup_prop} cm²)")
    
    ax_s.set_xlim(-5, b+5)
    ax_s.set_ylim(-5, h+5)
    ax_s.set_xlabel("Base (cm)")
    ax_s.set_ylabel("Peralte (cm)")
    ax_s.set_title(f"Sección Típica de la Viga {b}x{h}")
    ax_s.grid(True, linestyle="--", alpha=0.5)
    ax_s.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    st.pyplot(fig_sect)
    
    st.caption("Nota: La separación física longitudinal recomendada de estribos en los extremos (zonas confinadas) debe ser menor o igual a los límites de confinamiento calculados en la pestaña anterior.")
