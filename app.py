import streamlit as st
# Importamos la función que crea tu agente desde tu archivo original
from agent import get_expert_agent 

# 1. Configuración de la página web
st.set_page_config(
    page_title="Asistente de Generadores Diésel",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Estilos CSS avanzados para asegurar diseño 100% Responsive en móviles, tablets y escritorio
st.markdown("""
<style>
    /* Ajuste responsivo del contenedor principal */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 6rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 860px !important;
    }

    /* Tipografía y encabezados responsivos */
    h1 {
        font-size: clamp(1.5rem, 4vw, 2.2rem) !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        margin-bottom: 0.3rem !important;
    }
    
    .stCaption {
        font-size: clamp(0.85rem, 2vw, 0.95rem) !important;
        color: #6c757d;
        margin-bottom: 1.5rem !important;
    }

    /* Burbujas de chat responsivas */
    [data-testid="stChatMessage"] {
        padding: 0.85rem 1rem !important;
        border-radius: 12px !important;
        margin-bottom: 0.75rem !important;
        word-break: break-word !important;
        overflow-wrap: break-word !important;
    }

    /* Tablas técnicas responsivas con scroll horizontal suave en pantallas pequeñas */
    .stMarkdown table {
        width: 100% !important;
        display: block !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        border-collapse: collapse !important;
        margin: 1rem 0 !important;
        font-size: 0.9rem !important;
    }

    .stMarkdown th, .stMarkdown td {
        padding: 0.5rem 0.75rem !important;
        border: 1px solid rgba(128, 128, 128, 0.25) !important;
    }

    /* Bloques de código y checklists responsivos */
    pre, code {
        max-width: 100% !important;
        white-space: pre-wrap !important;
        word-break: break-word !important;
    }

    /* Adaptaciones específicas para pantallas móviles (< 768px) */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
            padding-top: 1.2rem !important;
            padding-bottom: 5.5rem !important;
        }

        [data-testid="stChatMessage"] {
            padding: 0.7rem 0.8rem !important;
        }

        [data-testid="stChatInput"] {
            padding-bottom: 0.5rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Asistente Técnico: Generadores Diésel")
st.caption("Consulta fallas, códigos de error y procedimientos de mantenimiento.")

# 2. Inicializar el agente experto de LangChain (solo una vez por sesión)
@st.cache_resource
def load_agent():
    return get_expert_agent()

agente = load_agent()

# 3. Inicializar el historial de chat en la memoria de la sesión
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hola. Soy el Ingeniero Especialista en Mantenimiento. ¿Describe la falla o consulta técnica del grupo electrógeno?"}
    ]

# 4. Mostrar el historial de chat en la pantalla
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Capturar la nueva pregunta del usuario (la barra inferior estilo WhatsApp)
if prompt := st.chat_input("Escribe tu consulta aquí..."):
    # Mostrar la pregunta del usuario en la pantalla
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Mostrar un indicador de "escribiendo..." mientras el agente piensa
    with st.chat_message("assistant"):
        with st.spinner("Consultando manuales..."):
            # Llamar al agente de LangChain
            response = agente.invoke(prompt)
            st.markdown(response)
            
    # Guardar la respuesta del agente en el historial
    st.session_state.messages.append({"role": "assistant", "content": response})