import streamlit as st
import numpy as np
import pandas as pd
import math
import matplotlib.pyplot as plt
from anastruct import SystemElements

# Configuración de página
st.set_page_config(page_title="Software de Vigas Profesional NTC 2023", layout="wide")

st.title("🏗️ Suite de Ingeniería de Vigas Continuas y Bastones - NTC 2023")
st.caption("Versión de Despacho: Optimización Comercial, Control de Congestión, Branson Exacto y Reglas de Habilitado en Obra")

# Diccionario comercial de varillas en México
VARILLAS = {
    "#3 (3/8\")": {"diametro": 0.95, "area": 0.71, "peso": 0.56},
    "#4 (1/2\")": {"diametro": 1.27, "area": 1.27, "peso": 0.99},
    "#5 (5/8\")": {"diametro": 1.59, "area": 1.98, "peso": 1.55},
    "#6 (3/4\")": {"diametro": 1.91, "area": 2.85, "peso": 2.23},
    "#8 (1\")": {"diametro": 2.54, "area": 5.07, "peso": 3.97}
}

# --- BARRA LATERAL: ENTRADA DE DATOS ---
st.sidebar.header("1. Parámetros de Materiales y Sismo")
fc = st.sidebar.number_input("f'c - Resistencia Concreto (kg/cm²)", value=250, step=50)
fy = st.sidebar.number_input("fy - Acero Longitudinal (kg/cm²)", value=4200, step=100)
fyv = st.sidebar.number_input("fyv - Acero de Estribos (kg/cm²)", value=4200, step=100)

# REQUERIMIENTO: Factor de Comportamiento Sísmico Q
Q_sismo = st.sidebar.selectbox("Factor de Comportamiento Sísmico (Q)", [2, 3, 4], index=0)

FR_flexion = 0.90
FR_cortante = 0.75

st.sidebar.header("2. Geometría Homogénea")
b = st.sidebar.number_input("Base de la viga, b (cm)", value=30, step=5)
h = st.sidebar.number_input("Peralte total, h (cm)", value=50, step=5)
rec = st.sidebar.number_input("Recubrimiento mecánico, d' (cm)", value=5, step=1)
L_total = st.sidebar.number_input("Longitud Total de la Viga (m)", value=6.0, step=0.5)
d = h - rec

st.sidebar.header("3. Cargas por Componente (Servicio)")
w_cm = st.sidebar.number_input("Carga Muerta No Facturada (ton/m)", value=1.5, step=0.5)
w_cv = st.sidebar.number_input("Carga Viva No Facturada (ton/m)", value=0.8, step=0.2)

# Combinación Reglamentaria NTC 2023
w_facturada = (1.3 * w_cm) + (1.5 * w_cv)
st.sidebar.success(f"📋 Carga de Diseño Facturada: {w_facturada:.2f} ton/m")

# --- SELECCIÓN COMERCIAL ---
st.sidebar.header("4. Refuerzo Base Longitudinal")
col_as1, col_as2 = st.sidebar.columns(2)
v_inf_tipo = col_as1.selectbox("Varilla Inferior Base", list(VARILLAS.keys()), index=2) 
v_inf_num = col_as2.number_input("Cantidad Inf Base (Máx 3)", value=2, min_value=1, max_value=3, step=1)

col_as3, col_as4 = st.sidebar.columns(2)
v_sup_tipo = col_as3.selectbox("Varilla Superior Base", list(VARILLAS.keys()), index=1) 
v_sup_num = col_as4.number_input("Cantidad Sup Base (Máx 3)", value=2, min_value=1, max_value=3, step=1)

# --- BASTONES INFERIORES Y SUPERIORES ---
st.sidebar.header("5. Configuración de Bastones Extras")
activar_bastones_sup = st.sidebar.checkbox("¿Añadir Bastones Superiores (Momento Negativo)?")
as_bastones_sup = 0.0
v_bast_sup_tipo = "#4 (1/2\")"
v_bast_sup_num = 0
if activar_bastones_sup:
    col_bs1, col_bs2 = st.sidebar.columns(2)
    v_bast_sup_tipo = col_bs1.selectbox("Varilla Bastón Sup", list(VARILLAS.keys()), index=2, key="bsup")
    v_bast_sup_num = col_bs2.number_input("Cant. Bastones Sup", value=2, min_value=1, max_value=3, step=1, key="nbsup")
    as_bastones_sup = VARILLAS[v_bast_sup_tipo]["area"] * v_bast_sup_num

activar_bastones_inf = st.sidebar.checkbox("¿Añadir Bastones Inferiores (Momento Positivo)?")
as_bastones_inf = 0.0
v_bast_inf_tipo = "#4 (1/2\")"
v_bast_inf_num = 0
if activar_bastones_inf:
    col_bi1, col_bi2 = st.sidebar.columns(2)
    v_bast_inf_tipo = col_bi1.selectbox("Varilla Bastón Inf", list(VARILLAS.keys()), index=2, key="binf")
    v_bast_inf_num = col_bi2.number_input("Cant. Bastones Inf", value=2, min_value=1, max_value=3, step=1, key="nbinf")
    as_bastones_inf = VARILLAS[v_bast_inf_tipo]["area"] * v_bast_inf_num

# Totales colocados de acero manuales
as_inf_total_colocado = (VARILLAS[v_inf_tipo]["area"] * v_inf_num) + as_bastones_inf
as_sup_total_colocado = (VARILLAS[v_sup_tipo]["area"] * v_sup_num) + as_bastones_sup

# --- CONFIGURACIÓN DE APOYOS ---
st.sidebar.header("6. Configuración de Apoyos")
if 'apoyos' not in st.session_state:
    st.session_state.apoyos = [{"posicion": 0.0, "tipo": "Fijo/Rodillo"}, {"posicion": L_total, "tipo": "Fijo/Rodillo"}]

col_ap_b1, col_ap_b2 = st.sidebar.columns(2)
if col_ap_b1.button("➕ Apoyo"): st.session_state.apoyos.append({"posicion": L_total, "tipo": "Fijo/Rodillo"})
if col_ap_b2.button("❌ Apoyo"): st.session_state.apoyos.pop()

apoyos_procesados = []
for idx, ap in enumerate(st.session_state.apoyos):
    c_a1, c_a2 = st.sidebar.columns(2)
    pos = c_a1.number_input(f"X (m) Apoyo {idx+1}", value=float(ap["posicion"]), min_value=0.0, max_value=float(L_total), key=f"pos_ap_{idx}")
    tipo = c_a2.selectbox(f"Tipo Apoyo {idx+1}", ["Fijo/Rodillo", "Empotrado"], key=f"tipo_ap_{idx}")
    apoyos_procesados.append({"posicion": pos, "tipo": tipo})


# --- SOLVER ESTRUCTURAL MATRICIAL ---
puntos_sistema = sorted(list(set([0.0, L_total] + [ap["posicion"] for ap in apoyos_procesados])))
ss = SystemElements()
for i in range(len(puntos_sistema)-1):
    ss.add_element(location=[[puntos_sistema[i], 0], [puntos_sistema[i+1], 0]])

for ap in apoyos_procesados:
    n_id = ss.find_node_id([ap["posicion"], 0])
    if n_id:
        if ap["tipo"] == "Empotrado": ss.add_support_fixed(node_id=n_id)
        else: ss.add_support_hinged(node_id=n_id)

for el_id in range(1, len(puntos_sistema)):
    ss.q_load(q=-w_facturada, element_id=el_id)

ss.solve()

Mu_max = max(abs(np.array(ss.get_element_results(element_id=1)['M']))) * 100000 
Vu_max = max(abs(np.array(ss.get_element_results(element_id=1)['Q']))) * 1000   


# --- LÍMITES DE ACERO DINÁMICOS POR SISMICIDAD Q (NTC 2023) ---
beta1 = 0.85 if fc <= 280 else max(0.85 - 0.05 * ((fc - 280) / 70), 0.65)
rho_min = 0.7 * math.sqrt(fc) / fy
as_min_formula = rho_min * b * d

# Afectación de Q en la cuantía balanceada máxima permitida
rho_b = (beta1 * 0.85 * fc / fy) * (6000 / (6000 + fy))
if Q_sismo == 2:
    rho_max = 0.75 * rho_b
elif Q_sismo == 3:
    rho_max = 0.50 * rho_b  
else:
    rho_max = 0.35 * rho_b  

as_max = rho_max * b * d


# --- MOMENTO RESISTENTE REAL ---
a_real = ((as_inf_total_colocado - as_sup_total_colocado) * fy) / (0.85 * fc * b)
MR = 0.90 * ((as_inf_total_colocado - as_sup_total_colocado) * fy * (d - a_real / 2) + as_sup_total_colocado * fy * (d - rec))


# --- REQUERIMIENTO EXCEPCIÓN DE ACERO MÍNIMO (1.33 * Mu) ---
excepcion_133_aplica = False
if as_inf_total_colocado < as_min_formula:
    if MR >= 1.33 * Mu_max:
        excepcion_133_aplica = True
        as_min_final = as_inf_total_colocado 
    else:
        as_min_final = as_min_formula
else:
    as_min_final = as_min_formula


# --- OPTIMIZACIÓN AUTOMÁTICA CON FILTRO Q Y REGLA DE 3 VARILLAS ---
opciones_validas = []
for nombre_varilla, prop in VARILLAS.items():
    for n_barras in range(1, 4): 
        as_prueba = prop["area"] * n_barras
        a_p = (as_prueba * fy) / (0.85 * fc * b)
        MR_p = 0.90 * as_prueba * fy * (d - a_p / 2)
        
        cumple_min = as_prueba >= as_min_formula or MR_p >= 1.33 * Mu_max
        cumple_max = as_prueba <= as_max
        
        if cumple_min and cumple_max and MR_p >= Mu_max:
            opciones_validas.append({
                "Configuración": f"{n_barras} Var. {nombre_varilla}",
                "Área (cm²)": as_prueba,
                "MR (ton-m)": MR_p / 100000,
                "Peso (kg/m)": prop["peso"] * n_barras
            })

df_optimo = pd.DataFrame(opciones_validas)
if not df_optimo.empty:
    df_optimo = df_optimo.sort_values(by="Peso (kg/m)").reset_index(drop=True)
    mejor_armado_texto = df_optimo.iloc[0]["Configuración"]
else:
    mejor_armado_texto = "Ajustar dimensiones. El factor Q restringe la cuantía máxima."


# --- LONGITUD DE DESARROLLO NORMATIVA (ld) Y CORTE DE PLANOS DE OBRA ---
db_bast_sup = VARILLAS[v_bast_sup_tipo]["diametro"] if activar_bastones_sup else 1.0
ld_sup = max((0.06 * db_bast_sup * fy) / math.sqrt(fc), 0.004 * db_bast_sup * fy, 30.0)
# Regla de los cuartos constructiva en taller para momento negativo + gancho estándar a 90° si es empotrado exterior
longitud_plano_sup = max((L_total / 4) * 100, ld_sup)

db_bast_inf = VARILLAS[v_bast_inf_tipo]["diametro"] if activar_bastones_inf else 1.0
ld_inf = max((0.06 * db_bast_inf * fy) / math.sqrt(fc), 0.004 * db_bast_inf * fy, 30.0)
# Regla constructiva para momento positivo central (60% del claro)
longitud_plano_inf = max((L_total * 0.60) * 100, ld_inf)


# --- DEFLEXIÓN DE BRANSON CON RESOLUCIÓN DE EJE NEUTRO EXACTO ---
Ig = (b * h**3) / 12
fr = 2.0 * math.sqrt(fc)
yt = h / 2
Mcr = (fr * Ig) / yt
Ma = Mu_max / 1.3

n_rel = 2000000 / (14000 * math.sqrt(fc))
rho_real_inf = as_inf_total_colocado / (b * d)

# Solución analítica cuadrática del eje neutro agrietado (k)
k_exacto = math.sqrt((rho_real_inf * n_rel)**2 + 2 * rho_real_inf * n_rel) - (rho_real_inf * n_rel)
Icr_exacto = (b * (k_exacto * d)**3) / 3 + n_rel * as_inf_total_colocado * (d - k_exacto * d)**2

Ie = min(((Mcr / Ma)**3) * Ig + (1 - (Mcr / Ma)**3) * Icr_exacto, Ig) if Ma > Mcr else Ig
flecha_servicio_inst = (5 * ((w_cm + w_cv)*10) * (L_total*100)**4) / (384 * (14000 * math.sqrt(fc)) * Ie)
flecha_diferida_total = flecha_servicio_inst * (1 + (2.0 / (1 + 50 * (as_sup_total_colocado/(b*d)))))
flecha_permisible = (L_total * 100) / 240


# --- REVISIÓN CORTANTE Y RESTRICCIONES SÍSMICAS DE ESTRIBOS SEGÚN Q ---
if Q_sismo == 2:
    s_max_confinado = min(d / 4, 10.0)
    s_max_central = min(d / 2, 25.0)
elif Q_sismo == 3:
    s_max_confinado = min(d / 4, 8 * VARILLAS[v_inf_tipo]["diametro"], 10.0)
    s_max_central = min(d / 3, 20.0)
else: 
    s_max_confinado = min(d / 4, 6 * VARILLAS[v_inf_tipo]["diametro"], 10.0)
    s_max_central = min(d / 4, 15.0)


# --- VALIDACIÓN CONSTRUCTIVA: ESPACIO LIBRE PARA CONCRETO (GRAVA 3/4") ---
num_varillas_capa_inf = v_inf_num + (v_bast_inf_num if activar_bastones_inf else 0)
espacio_disponible = b - (2 * rec) - (2 * 0.95) # Restando recubrimientos y estribos de 3/8"
diametro_varilla_max_inf = VARILLAS[v_inf_tipo]["diametro"]

if num_varillas_capa_inf > 1:
    espacio_libre_inf = (espacio_disponible - (num_varillas_capa_inf * diametro_varilla_max_inf)) / (num_varillas_capa_inf - 1)
else:
    espacio_libre_inf = espacio_disponible


# --- UI PESTAÑAS ---
t1, t2, t3 = st.tabs(["🚀 Control Sísmico y Criterio 1.33Mu", "📈 Análisis de Canales", "🧱 Detalle y Bastones Dobles"])

with t1:
    st.subheader(f"Evaluación de Ductilidad para Sismo (Q = {Q_sismo})")
    
    # Renderizado de Alerta de Constructibilidad/Vibrado en Pantalla Principal
    if espacio_libre_inf < 2.5:
        st.error(f"⚠️ **Alerta de Congestión Constructiva:** El espacio libre entre varillas inferiores es de {espacio_libre_inf:.1f} cm (Menor a 2.5 cm). La grava de 3/4\" se va a atorar y provocará panales. Aumenta la base de la viga, disminuye el número de barras o colócalas en una segunda capa.")
    else:
        st.success(f"📶 **Validación de Colado:** Espacio libre entre barras de {espacio_libre_inf:.1f} cm. Adecuado para un correcto vibrado y flujo del concreto.")

    if excepcion_133_aplica:
        st.info("💡 **Excepción NTC Aplica:** El acero colocado es menor al mínimo reglamentario por fórmula, pero se aprueba legalmente porque el Momento Resistente excede 1.33 veces al Momento Último de diseño.")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Acero Mínimo Final", f"{as_min_final:.2f} cm²", f"Fórmula: {as_min_formula:.1f} cm²")
    c2.metric("Acero Máximo Dúctil (Q)", f"{as_max:.2f} cm²", f"Límite Restringido")
    c3.metric("Tu Acero Inferior Total", f"{as_inf_total_colocado:.2f} cm²")

    st.subheader("Combinaciones de Optimización Comercial Ordenadas por Economía")
    if not df_optimo.empty:
        st.dataframe(df_optimo, use_container_width=True)

with t2:
    st.subheader("Simulación Hiperestática y Deflexión de Branson Exacta")
    col_b1, col_b2 = st.columns(2)
    col_b1.metric("Inercia Efectiva Agrietada (Ie)", f"{Ie:.0f} cm⁴", f"Bruta Ig: {Ig:.0f} cm⁴")
    col_b2.metric("Deflexión Diferida Real", f"{flecha_diferida_total:.2f} cm", f"Límite L/240: {flecha_permisible:.2f} cm")
    
    if flecha_diferida_total <= flecha_permisible:
        st.success("✅ Deflexiones tolerables bajo condiciones de servicio.")
    else:
        st.error("❌ La sección se agrieta en exceso y se cuelga. Incrementa el peralte de concreto (h).")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 4))
    ss.plot_bending_moment(ax=ax1, scale=0.08, font_size=7)
    ss.plot_shear_force(ax=ax2, scale=0.08, font_size=7)
    plt.tight_layout()
    st.pyplot(fig)

with t3:
    st.subheader("Distribución de Refuerzo y Guía de Habilitado para Taller")
    col_g1, col_g2 = st.columns([1, 2])
    
    with col_g1:
        fig_sect, ax_s = plt.subplots(figsize=(4, 5))
        ax_s.add_patch(plt.Rectangle((0, 0), b, h, color="lightgrey", alpha=0.8))
        ax_s.add_patch(plt.Rectangle((2.5, 2.5), b-5, h-5, fill=False, edgecolor="blue", linewidth=2))
        
        # Inferiores Base + Bastones Inf
        x_inf = np.linspace(5, b-5, v_inf_num) if v_inf_num > 1 else [b/2]
        for xc in x_inf: ax_s.scatter(xc, 5, color="red", s=180, zorder=5)
        if activar_bastones_inf:
            x_binf = np.linspace(8, b-8, v_bast_inf_num) if v_bast_inf_num > 1 else [b/2]
            for xc in x_binf: ax_s.scatter(xc, 9, color="orange", s=130, zorder=5, marker="v")

        # Superiores Base + Bastones Sup
        x_sup = np.linspace(5, b-5, v_sup_num) if v_sup_num > 1 else [b/2]
        for xc in x_sup: ax_s.scatter(xc, h-5, color="darkred", s=140, zorder=5)
        if activar_bastones_sup:
            x_bsup = np.linspace(8, b-8, v_bast_sup_num) if v_bast_sup_num > 1 else [b/2]
            for xc in x_bsup: ax_s.scatter(xc, h-9, color="purple", s=130, zorder=5, marker="^")
                
        ax_s.set_xlim(-5, b+5)
        ax_s.set_ylim(-5, h+5)
        st.pyplot(fig_sect)
        
    with col_g2:
        st.subheader("Planilla de Corte y Colocación en Campo")
        st.info(f"📍 **Zona Confinada (Apoyos a Extremos):** Colocar estribos cada **{s_max_confinado:.1f} cm**")
        st.success(f"🍃 **Zona Central de la Viga:** Colocar estribos cada **{s_max_central:.1f} cm**")
        
        if activar_bastones_sup:
            st.warning(f"📐 **Corte de Bastón Superior (Negativo):** Habilitar varillas de **L = {longitud_plano_sup / 100:.2f} m**. "
                       f"Si el apoyo es un empotre exterior, añadir gancho estándar a 90° de {12 * db_bast_sup:.1f} cm.")
        if activar_bastones_inf:
            st.warning(f"📐 **Corte de Bastón Inferior (Positivo):** Habilitar varillas de **L = {longitud_plano_inf / 100:.2f} m** y centrarlas perfectamente a mitad del claro libre.")
