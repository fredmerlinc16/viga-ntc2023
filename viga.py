import streamlit as st
import numpy as np
import pandas as pd
import math
import matplotlib.pyplot as plt
from anastruct import SystemElements

# 1. Configuración de Página
st.set_page_config(page_title="Software de Vigas Profesional NTC 2023", layout="wide")

st.title("🏗️ Suite de Ingeniería de Vigas Continuas y Bastones - NTC 2023")
st.caption("Análisis hiperestático en tiempo real con motor visual de cargas, Branson exacto y reglas constructivas")

VARILLAS = {
    "#3 (3/8\")": {"diametro": 0.95, "area": 0.71, "peso": 0.56},
    "#4 (1/2\")": {"diametro": 1.27, "area": 1.27, "peso": 0.99},
    "#5 (5/8\")": {"diametro": 1.59, "area": 1.98, "peso": 1.55},
    "#6 (3/4\")": {"diametro": 1.91, "area": 2.85, "peso": 2.23},
    "#8 (1\")": {"diametro": 2.54, "area": 5.07, "peso": 3.97}
}

# --- BARRA LATERAL: ENTRADAS ---
st.sidebar.header("1. Materiales y Sismo")
fc = st.sidebar.number_input("f'c - Concreto (kg/cm²)", value=250, step=50)
fy = st.sidebar.number_input("fy - Acero Long. (kg/cm²)", value=4200, step=100)
fyv = st.sidebar.number_input("fyv - Estribos (kg/cm²)", value=4200, step=100)
Q_sismo = st.sidebar.selectbox("Factor de Comportamiento Sísmico (Q)", [2, 3, 4], index=0)

st.sidebar.header("2. Geometría")
b = st.sidebar.number_input("Base, b (cm)", value=30, step=5)
h = st.sidebar.number_input("Peralte, h (cm)", value=50, step=5)
rec = st.sidebar.number_input("Recubrimiento mecánico, d' (cm)", value=5, step=1)
L_total = st.sidebar.number_input("Longitud Total (m)", value=6.0, step=0.5)
d = h - rec

st.sidebar.header("3. Cargas Distribuidas (Servicio)")
w_cm = st.sidebar.number_input("w Muerta (ton/m)", value=1.5, step=0.5)
w_cv = st.sidebar.number_input("w Viva (ton/m)", value=0.8, step=0.2)
w_facturada = (1.3 * w_cm) + (1.5 * w_cv)

# --- NUEVO: CARGAS PUNTUALES ---
st.sidebar.header("4. Cargas Puntuales (Servicio)")
if 'cargas_p' not in st.session_state:
    st.session_state.cargas_p = []

col_cp1, col_cp2 = st.sidebar.columns(2)
if col_cp1.button("➕ Puntual"): st.session_state.cargas_p.append({"pos": round(L_total/2, 2), "cm": 1.0, "cv": 0.5})
if col_cp2.button("❌ Puntual"): 
    if st.session_state.cargas_p: st.session_state.cargas_p.pop()

cargas_p_procesadas = []
for i, cp in enumerate(st.session_state.cargas_p):
    st.sidebar.caption(f"Carga Puntual #{i+1}")
    c1, c2, c3 = st.sidebar.columns(3)
    pos_val = min(float(cp["pos"]), float(L_total))
    pos_p = c1.number_input("X (m)", value=pos_val, min_value=0.0, max_value=float(L_total), key=f"cp_x_{i}")
    cm_p  = c2.number_input("CM (t)", value=float(cp["cm"]), min_value=0.0, step=0.5, key=f"cp_cm_{i}")
    cv_p  = c3.number_input("CV (t)", value=float(cp["cv"]), min_value=0.0, step=0.5, key=f"cp_cv_{i}")
    cargas_p_procesadas.append({"posicion": pos_p, "cm": cm_p, "cv": cv_p})

st.sidebar.header("5. Configuración de Apoyos")
if 'apoyos' not in st.session_state:
    st.session_state.apoyos = [{"posicion": 0.0, "tipo": "Fijo/Rodillo"}, {"posicion": L_total, "tipo": "Fijo/Rodillo"}]

col_ap1, col_ap2 = st.sidebar.columns(2)
if col_ap1.button("➕ Apoyo"): st.session_state.apoyos.append({"posicion": L_total, "tipo": "Fijo/Rodillo"})
if col_ap2.button("❌ Apoyo"): 
    if len(st.session_state.apoyos) > 1: st.session_state.apoyos.pop()

apoyos_procesados = []
for idx, ap in enumerate(st.session_state.apoyos):
    ca1, ca2 = st.sidebar.columns(2)
    pos_ap_val = min(float(ap["posicion"]), float(L_total))
    pos = ca1.number_input(f"X Apoyo {idx+1}", value=pos_ap_val, min_value=0.0, max_value=float(L_total), key=f"ap_x_{idx}")
    tipo = ca2.selectbox(f"Tipo {idx+1}", ["Fijo/Rodillo", "Empotrado"], key=f"ap_t_{idx}")
    apoyos_procesados.append({"posicion": pos, "tipo": tipo})

st.sidebar.header("6. Refuerzo Longitudinal")
col_as1, col_as2 = st.sidebar.columns(2)
v_inf_tipo = col_as1.selectbox("Varilla Inf Base", list(VARILLAS.keys()), index=2) 
v_inf_num = col_as2.number_input("Cant. Inf", value=2, min_value=1, max_value=4)

col_as3, col_as4 = st.sidebar.columns(2)
v_sup_tipo = col_as3.selectbox("Varilla Sup Base", list(VARILLAS.keys()), index=1) 
v_sup_num = col_as4.number_input("Cant. Sup", value=2, min_value=1, max_value=4)

activar_bast_sup = st.sidebar.checkbox("Bastones Superiores")
as_bast_sup = 0.0
v_bs_tipo = "#4 (1/2\")"
v_bs_num = 0
if activar_bast_sup:
    cb1, cb2 = st.sidebar.columns(2)
    v_bs_tipo = cb1.selectbox("Varilla Bast. Sup", list(VARILLAS.keys()), index=2)
    v_bs_num = cb2.number_input("Cant. Bast. Sup", value=2, min_value=1, max_value=3)
    as_bast_sup = VARILLAS[v_bs_tipo]["area"] * v_bs_num

activar_bast_inf = st.sidebar.checkbox("Bastones Inferiores")
as_bast_inf = 0.0
v_bi_tipo = "#4 (1/2\")"
v_bi_num = 0
if activar_bast_inf:
    cb3, cb4 = st.sidebar.columns(2)
    v_bi_tipo = cb3.selectbox("Varilla Bast. Inf", list(VARILLAS.keys()), index=2)
    v_bi_num = cb4.number_input("Cant. Bast. Inf", value=2, min_value=1, max_value=3)
    as_bast_inf = VARILLAS[v_bi_tipo]["area"] * v_bi_num

as_inf_colocado = (VARILLAS[v_inf_tipo]["area"] * v_inf_num) + as_bast_inf
as_sup_colocado = (VARILLAS[v_sup_tipo]["area"] * v_sup_num) + as_bast_sup


# --- SOLVER MATRICIAL ANASTRUCT ---
puntos_criticos = [0.0, float(L_total)]
for ap in apoyos_procesados: puntos_criticos.append(round(float(ap["posicion"]), 4))
for cp in cargas_p_procesadas: puntos_criticos.append(round(float(cp["posicion"]), 4))

puntos_sistema = sorted(list(set(puntos_criticos)))
ss = SystemElements()

for i in range(len(puntos_sistema)-1):
    ss.add_element(location=[[puntos_sistema[i], 0], [puntos_sistema[i+1], 0]])

for ap in apoyos_procesados:
    n_id = ss.find_node_id([round(float(ap["posicion"]), 4), 0])
    if n_id:
        if ap["tipo"] == "Empotrado": ss.add_support_fixed(node_id=n_id)
        else: ss.add_support_hinged(node_id=n_id)

for el_id in range(1, len(puntos_sistema)):
    ss.q_load(q=-w_facturada, element_id=el_id)

# Acumular cargas puntuales por si caen en la misma coordenada exacta
cargas_nodo = {}
for cp in cargas_p_procesadas:
    px = round(float(cp["posicion"]), 4)
    pu = (1.3 * cp["cm"]) + (1.5 * cp["cv"])
    cargas_nodo[px] = cargas_nodo.get(px, 0.0) + pu

for px, pu_tot in cargas_nodo.items():
    n_id = ss.find_node_id([px, 0])
    if n_id and pu_tot > 0:
        ss.point_load(node_id=n_id, Fx=0, Fy=-pu_tot)

ss.solve()

f_momento = [0.0]
f_cortante = [0.0]
for el_id in range(1, len(puntos_sistema)):
    res = ss.get_element_results(element_id=el_id)
    if res:
        if res.get('M') is not None: f_momento.extend(res['M'])
        if res.get('Q') is not None: f_cortante.extend(res['Q'])

Mu_max = max(abs(np.array(f_momento))) * 100000
Vu_max = max(abs(np.array(f_cortante))) * 1000


# --- MOTOR GRÁFICO DEL ESQUEMA FÍSICO DE LA VIGA ---
def generar_esquema_visual(L, apoyos, w_dist, cargas_p):
    fig, ax = plt.subplots(figsize=(10, 2.2))
    ax.plot([0, L], [0, 0], color='#1E293B', linewidth=9, zorder=3)
    
    for ap in apoyos:
        x = ap['posicion']
        if ap['tipo'] == 'Empotrado':
            ax.plot([x, x], [-0.35, 0.35], color='#0F172A', linewidth=5, zorder=4)
            for dy in np.linspace(-0.3, 0.3, 6):
                ax.plot([x, x - (0.18 if x > L/2 else -0.18)], [dy, dy - 0.1], color='#64748B', linewidth=1.5)
        else:
            ax.plot(x, -0.05, marker='^', markersize=15, color='#059669', zorder=4)
            ax.plot(x, -0.22, marker='s', markersize=7, color='#059669', zorder=4)

    if w_dist > 0:
        yt = 0.55
        ax.plot([0, L], [yt, yt], color='#2563EB', linewidth=1.5)
        for x_fl in np.linspace(0.1, L-0.1, max(int(L*2.2), 4)):
            ax.annotate('', xy=(x_fl, 0.06), xytext=(x_fl, yt),
                        arrowprops=dict(arrowstyle="->", color='#3B82F6', lw=1.2))
        ax.text(L/2, yt + 0.08, f"wu = {w_dist:.2f} t/m", ha='center', va='bottom', 
                color='#1D4ED8', fontweight='bold', fontsize=9.5, 
                bbox=dict(boxstyle='round,pad=0.2', facecolor='#EFF6FF', edgecolor='#BFDBFE'))

    for cp in cargas_p:
        xp = cp['posicion']
        pu_val = (1.3 * cp['cm']) + (1.5 * cp['cv'])
        ax.annotate('', xy=(xp, 0.06), xytext=(xp, 1.1),
                    arrowprops=dict(facecolor='#DC2626', edgecolor='#B91C1C', width=3, headwidth=8), zorder=6)
        ax.text(xp, 1.15, f"Pu={pu_val:.2f}t\n({xp}m)", ha='center', va='bottom', 
                color='#991B1B', fontweight='bold', fontsize=8.5,
                bbox=dict(boxstyle='round,pad=0.2', facecolor='#FEF2F2', edgecolor='#FECACA'))

    ax.set_xlim(-L*0.06, L*1.06)
    ax.set_ylim(-0.45, 1.6)
    ax.axis('off')
    plt.tight_layout()
    return fig


# --- DASHBOARD PRINCIPAL (VISTA INMEDIATA) ---
k1, k2, k3, k4 = st.columns(4)
k1.metric("Momento Máximo de Diseño", f"{Mu_max/100000:.2f} ton·m")
k2.metric("Cortante Máximo de Diseño", f"{Vu_max/1000:.2f} ton")
k3.metric("Carga Distribuida (wu)", f"{w_facturada:.2f} ton/m")
k4.metric("Cargas Puntuales Activas", f"{len(cargas_p_procesadas)}")

st.subheader("📍 Esquema del Sistema Estructural")
st.pyplot(generar_esquema_visual(L_total, apoyos_procesados, w_facturada, cargas_p_procesadas))

st.subheader("📊 Diagramas de Esfuerzos Internos")
try:
    fig_diag, (ax_m, ax_v) = plt.subplots(2, 1, figsize=(11, 6.5))
    ss.plot_bending_moment(ax=ax_m, scale=0.07, font_size=8.5)
    ax_m.set_title("Diagrama de Momentos Flectores (ton·m)", fontsize=10, fontweight='bold', pad=12)
    
    ss.plot_shear_force(ax=ax_v, scale=0.07, font_size=8.5)
    ax_v.set_title("Diagrama de Fuerzas Cortantes (ton)", fontsize=10, fontweight='bold', pad=12)
    
    plt.tight_layout(pad=2.5)
    st.pyplot(fig_diag)
except Exception:
    st.error("Error al renderizar diagramas. Verifica que la distancia de los apoyos no genere inestabilidad.")


# --- CÁLCULOS NORMATIVOS COMPLEMENTARIOS ---
beta1 = 0.85 if fc <= 280 else max(0.85 - 0.05 * ((fc - 280) / 70), 0.65)
as_min_form = (0.7 * math.sqrt(fc) / fy) * b * d

rho_b = (beta1 * 0.85 * fc / fy) * (6000 / (6000 + fy))
rho_max = rho_b * (0.75 if Q_sismo == 2 else (0.50 if Q_sismo == 3 else 0.35))
as_max = rho_max * b * d

a_real = ((as_inf_colocado - as_sup_colocado) * fy) / (0.85 * fc * b) if (as_inf_colocado - as_sup_colocado) > 0 else 0.1
MR = 0.90 * ((as_inf_colocado - as_sup_colocado) * fy * (d - a_real / 2) + as_sup_colocado * fy * (d - rec))

excepcion_133 = False
if as_inf_colocado < as_min_form and MR >= 1.33 * Mu_max:
    excepcion_133 = True
    as_min_final = as_inf_colocado 
else:
    as_min_final = as_min_form

# Branson
Ig = (b * h**3) / 12
Mcr = ((2.0 * math.sqrt(fc)) * Ig) / (h / 2)
Ma = Mu_max / 1.3 if Mu_max > 0 else 0.1
n_rel = 2000000 / (14000 * math.sqrt(fc))
rho_inf = as_inf_colocado / (b * d) if (b * d) > 0 else 0.01
k_br = math.sqrt((rho_inf * n_rel)**2 + 2 * rho_inf * n_rel) - (rho_inf * n_rel)
Icr = (b * (k_br * d)**3) / 3 + n_rel * as_inf_colocado * (d - k_br * d)**2
Ie = min(((Mcr / Ma)**3) * Ig + (1 - (Mcr / Ma)**3) * Icr, Ig) if Ma > Mcr else Ig

flecha_inst = (5 * ((w_cm + w_cv)*10) * (L_total*100)**4) / (384 * (14000 * math.sqrt(fc)) * Ie)
rho_p = as_sup_colocado / (b * d) if (b * d) > 0 else 0.01
flecha_diferida = flecha_inst * (1 + (2.0 / (1 + 50 * rho_p)))
flecha_perm = (L_total * 100) / 240


# --- PESTAÑAS DE REVISIÓN Y DESPIECE ---
st.markdown("---")
t1, t2, t3 = st.tabs(["📋 Despiece de Armado", "⚖️ Revisión Normativa NTC", "📐 Deflexiones e Inercias"])

with t1:
    col_sect, col_det = st.columns([1, 2])
    with col_sect:
        fig_s, ax_s = plt.subplots(figsize=(4, 4.5))
        ax_s.add_patch(plt.Rectangle((0, 0), b, h, color="#E2E8F0"))
        ax_s.add_patch(plt.Rectangle((rec, rec), b-2*rec, h-2*rec, fill=False, ec="#2563EB", lw=2))
        
        x_in = np.linspace(rec, b-rec, v_inf_num) if v_inf_num > 1 else [b/2]
        for xc in x_in: ax_s.scatter(xc, rec, color="#DC2626", s=150, zorder=5)
        
        x_su = np.linspace(rec, b-rec, v_sup_num) if v_sup_num > 1 else [b/2]
        for xc in x_su: ax_s.scatter(xc, h-rec, color="#991B1B", s=120, zorder=5)
        
        ax_s.set_xlim(-4, b+4); ax_s.set_ylim(-4, h+4); ax_s.axis("off")
        st.pyplot(fig_s)
        
    with col_det:
        s_conf = min(d/4, 10.0 if Q_sismo==2 else (8*VARILLAS[v_inf_tipo]["diametro"] if Q_sismo==3 else 6*VARILLAS[v_inf_tipo]["diametro"]))
        s_cent = min(d/2, 25.0) if Q_sismo==2 else (min(d/3, 20.0) if Q_sismo==3 else min(d/4, 15.0))
        st.info(f"📍 **Estribos en Extremos (Confinamiento):** Cada **{s_conf:.1f} cm**")
        st.success(f"🍃 **Estribos en Zona Central:** Cada **{s_cent:.1f} cm**")
        st.write(f"**Acero Colocado:** Inferior = `{as_inf_colocado:.2f} cm²` | Superior = `{as_sup_colocado:.2f} cm²`")

with t2:
    if excepcion_133: st.info("💡 **Excepción 1.33Mu Activa:** Cuantía menor al mínimo permitida por sobreresistencia.")
    m1, m2, m3 = st.columns(3)
    m1.metric("Acero Mínimo NTC", f"{as_min_final:.2f} cm²")
    m2.metric("Acero Máximo (Q={Q_sismo})", f"{as_max:.2f} cm²")
    m3.metric("Estatus Resistencia", "CUMPLE" if MR >= Mu_max else "NO CUMPLE", f"MR: {MR/100000:.2f} t·m")

with t3:
    c_f1, c_f2 = st.columns(2)
    c_f1.metric("Inercia Efectiva Agrietada (Ie)", f"{Ie:.0f} cm⁴", f"Bruta: {Ig:.0f} cm⁴")
    c_f2.metric("Flecha Diferida a Largo Plazo", f"{flecha_diferida:.2f} cm", f"Límite: {flecha_perm:.2f} cm")
