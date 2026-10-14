import streamlit as st
from datetime import datetime
from agent import get_expert_agent, add_field_case, get_all_cases, increment_case_utility

# 1. Configuración de la página web optimizada para móviles (PWA Ready)
st.set_page_config(
    page_title="Asistente de Campo: Generadores Diésel",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Inyección de Meta Tags para comportamiento de App Nativa Móvil (PWA)
st.markdown("""
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#0e1117">
</head>
""", unsafe_allow_html=True)

# Estilos CSS avanzados para experiencia móvil de alta gama
st.markdown("""
<style>
    /* Contenedor principal con espaciado móvil ergonómico */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 5.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 860px !important;
    }

    /* Tipografía y títulos */
    h1 {
        font-size: clamp(1.4rem, 4.5vw, 2.1rem) !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        margin-bottom: 0.2rem !important;
    }
    
    .stCaption {
        font-size: 0.9rem !important;
        color: #8892b0 !important;
        margin-bottom: 1rem !important;
    }

    /* Pestañas de navegación superiores estilo App Móvil */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(255, 255, 255, 0.04);
        padding: 6px;
        border-radius: 12px;
        margin-bottom: 1rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.88rem;
        padding: 0 14px;
        color: #cbd5e1;
    }

    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
    }

    /* Tarjetas de Casos de Campo */
    .case-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(8px);
        transition: transform 0.15s ease, border-color 0.15s ease;
    }

    .case-card:hover {
        border-color: #3b82f6;
    }

    .case-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 6px;
    }

    .badge-model {
        background-color: #1e3a8a;
        color: #93c5fd;
    }

    .badge-tech {
        background-color: #065f46;
        color: #6ee7b7;
    }

    .badge-id {
        background-color: #374151;
        color: #e5e7eb;
    }

    /* Mensajes de chat */
    [data-testid="stChatMessage"] {
        padding: 0.85rem 1rem !important;
        border-radius: 14px !important;
        margin-bottom: 0.8rem !important;
        word-break: break-word !important;
    }

    /* Botones táctiles optimizados para pulgar en móviles */
    .stButton button {
        border-radius: 10px !important;
        min-height: 44px !important;
        font-weight: 600 !important;
    }

    /* Tablas técnicas con scroll suave en pantallas estrechas */
    .stMarkdown table {
        width: 100% !important;
        display: block !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        border-collapse: collapse !important;
        margin: 1rem 0 !important;
        font-size: 0.88rem !important;
    }

    .stMarkdown th, .stMarkdown td {
        padding: 0.5rem 0.75rem !important;
        border: 1px solid rgba(128, 128, 128, 0.25) !important;
    }
</style>
""", unsafe_allow_html=True)

# 2. Inicializar el agente de LangChain en caché
@st.cache_resource
def load_agent():
    return get_expert_agent()

agente = load_agent()

# Encabezado principal
st.title("⚡ Asistente Técnico & Bitácora IG")
st.caption("Diagnóstico inteligente, checklists de campo y memoria de fallas de grupos electrógenos.")

# Navegación por Pestañas Principales
tab_chat, tab_bitacora, tab_registro = st.tabs([
    "💬 Diagnóstico & Chat",
    "📖 Bitácora de Casos",
    "➕ Registrar Nueva Falla"
])

# =========================================================================
# PESTAÑA 1: DIAGNÓSTICO INTERACTIVO Y CHAT DE CAMPO
# =========================================================================
with tab_chat:
    # Inicializar historial de mensajes
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "👋 **Hola, soy el Especialista Técnico en Grupos Electrógenos.**\n\n"
                    "Describe la falla, síntoma o código de error que observas en la planta. "
                    "Revisaré tanto nuestros **precedentes de intervenciones anteriores** como los **manuales de servicio** "
                    "para entregarte un checklist de descarte paso a paso."
                )
            }
        ]

    # Mostrar historial de conversación
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Barra inferior de captura de consulta
    if prompt := st.chat_input("Escribe el síntoma o falla aquí (ej: 'no arranca', 'código 143')..."):
        # Agregar pregunta del técnico
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generar respuesta con el agente experto
        with st.chat_message("assistant"):
            with st.spinner("Consultando precedentes de campo y manuales..."):
                try:
                    response = agente.invoke(prompt)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.session_state.last_query = prompt
                except Exception as e:
                    error_msg = (
                        "⚠️ Los servidores del modelo experimentan alta demanda momentánea. "
                        "Por favor, intenta enviar tu consulta nuevamente en unos segundos."
                    )
                    st.warning(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

    # Sección interactiva de Feedback si hay al menos una consulta generada
    if len(st.session_state.messages) > 1 and st.session_state.messages[-1]["role"] == "assistant":
        st.write("")
        st.markdown("---")
        st.markdown("##### 🎯 ¿Te sirvieron estas sugerencias en campo?")
        
        col_feedback1, col_feedback2 = st.columns(2)
        with col_feedback1:
            if st.button("🟢 Sí, encontré la falla", use_container_width=True, key="btn_solved"):
                st.success("🎉 ¡Excelente trabajo en campo! La experiencia ha sido validada para respaldar futuros casos.")
                st.balloons()
        with col_feedback2:
            if st.button("🔴 No, fue otra causa", use_container_width=True, key="btn_different_cause"):
                st.info("💡 ¡Perfecto! Ve a la pestaña **'➕ Registrar Nueva Falla'** arriba para documentar la causa real y que el agente aprenda de esta experiencia.")

# =========================================================================
# PESTAÑA 2: BITÁCORA DE CASOS REALES Y PRECEDENTES
# =========================================================================
with tab_bitacora:
    st.subheader("📚 Memoria Técnica de la Empresa")
    st.write(
        "Aquí se registran todas las experiencias reales resueltas en campo por los técnicos. "
        "El agente consulta estos precedentes antes de sugerir cualquier descarte."
    )

    cases = get_all_cases()
    
    # Buscador rápido en la bitácora
    search_term = st.text_input("🔍 Buscar en la bitácora:", placeholder="Buscar por modelo, síntoma o solución...")
    
    if search_term:
        cases = [
            c for c in cases
            if search_term.lower() in c["planta_modelo"].lower()
            or search_term.lower() in c["sintoma"].lower()
            or search_term.lower() in c["causa_raiz"].lower()
            or search_term.lower() in c["solucion"].lower()
            or search_term.lower() in c["tecnico"].lower()
        ]

    st.write(f"Mostrando **{len(cases)}** precedentes técnicos registrados:")

    if not cases:
        st.info("No se encontraron casos que coincidan con la búsqueda.")
    else:
        for c in cases:
            with st.container():
                st.markdown(f"""
                <div class="case-card">
                    <span class="case-badge badge-id">Caso #{c['id']}</span>
                    <span class="case-badge badge-model">{c['planta_modelo']}</span>
                    <span class="case-badge badge-tech">Técnico: {c['tecnico']}</span>
                    <h4 style="margin-top: 0.5rem; margin-bottom: 0.3rem; color: #f8fafc;">⚠️ {c['sintoma']}</h4>
                    <p style="margin-bottom: 0.4rem; font-size: 0.9rem;"><strong>🔍 Causa Raíz Real:</strong> <span style="color: #fca5a5;">{c['causa_raiz']}</span></p>
                    <p style="margin-bottom: 0.4rem; font-size: 0.9rem;"><strong>🛠️ Solución Aplicada:</strong> <span style="color: #86efac;">{c['solucion']}</span></p>
                    {f'<p style="margin-bottom: 0.2rem; font-size: 0.85rem; color: #cbd5e1;"><strong>💡 Consejo de Campo:</strong> {c["consejo_campo"]}</p>' if c.get("consejo_campo") else ''}
                    <div style="margin-top: 0.6rem; font-size: 0.78rem; color: #94a3b8;">
                        📅 Registrado: {c.get('timestamp', 'Fecha desconocida')} &nbsp;|&nbsp; 👍 Utilidad confirmada: {c.get('utilidad_count', 1)} veces
                    </div>
                </div>
                """, unsafe_allow_html=True)

# =========================================================================
# PESTAÑA 3: FORMULARIO PARA REGISTRAR NUEVA FALLA (APRENDER DE LA FALLA)
# =========================================================================
with tab_registro:
    st.subheader("➕ Registrar Nueva Experiencia en Campo")
    st.caption("Al guardar este caso, el agente lo indexará de inmediato para advertir a futuros técnicos que enfrenten síntomas similares.")

    with st.form("form_nuevo_caso", clear_on_submit=True):
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            tecnico_input = st.text_input("👨‍🔧 Nombre del Técnico:", placeholder="Ej: Gabriel F. / Juan P.")
        with col_t2:
            planta_input = st.text_input("⚙️ Marca / Modelo / Capacidad:", placeholder="Ej: Cummins 150 kVA / Perkins / Generac")

        sintoma_input = st.text_area(
            "🚨 Síntoma o Falla Presentada:",
            placeholder="¿Qué hacía o qué no hacía la planta? (Ej: No arrancaba, no daba marcha, controlador apagado...)",
            height=85
        )

        descartes_input = st.text_area(
            "🔍 ¿Qué revisaste primero que SÍ estaba bueno? (Descartes previos):",
            placeholder="Ej: Se probó batería con multímetro y estaba bien, fusibles intactos, no era el solenoide...",
            height=75
        )

        causa_input = st.text_area(
            "🎯 ¿Cuál fue la CAUSA RAÍZ REAL comprobada en campo?:",
            placeholder="Ej: El breaker del cargador auxiliar de baterías estaba bajado en el tablero del cliente / Falso contacto en relé...",
            height=85
        )

        solucion_input = st.text_area(
            "🛠️ Solución Aplicada y Procedimiento Paso a Paso:",
            placeholder="Ej: Se rearmó el breaker, se midieron 27.4V de carga de flote y se colocó precinto al tablero...",
            height=90
        )

        consejo_input = st.text_input(
            "💡 Consejo / Lección Aprendida para otros técnicos:",
            placeholder="Ej: Revisar siempre el breaker AC del cargador antes de desarmar el motor de arranque"
        )

        submitted = st.form_submit_button("🚀 Guardar Caso y Alimentar al Agente", use_container_width=True)

        if submitted:
            if not tecnico_input.strip() or not planta_input.strip() or not sintoma_input.strip() or not causa_input.strip() or not solucion_input.strip():
                st.error("⚠️ Por favor completa los campos principales (Técnico, Planta, Síntoma, Causa Raíz y Solución).")
            else:
                with st.spinner("Indexando nuevo caso en la base de conocimientos..."):
                    try:
                        new_id = add_field_case(
                            tecnico=tecnico_input.strip(),
                            planta_modelo=planta_input.strip(),
                            sintoma=sintoma_input.strip(),
                            causa_raiz=causa_input.strip(),
                            solucion=solucion_input.strip(),
                            descartes_previos=descartes_input.strip(),
                            consejo_campo=consejo_input.strip()
                        )
                        st.success(f"✅ ¡Caso #{new_id} guardado e indexado exitosamente! El agente ya aprendió esta solución para futuras consultas.")
                        st.balloons()
                    except Exception as ex:
                        st.error(f"Error al guardar el caso: {ex}")