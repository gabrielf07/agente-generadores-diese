import os
import pickle
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Importar el gestor de experiencias de campo y el gestor de base de datos
import cases_manager
import db_manager

load_dotenv()

VECTOR_DB_DIR = "./chroma_db"
BM25_DOCS_PATH = "./bm25_docs.pkl"
EMBEDDING_MODEL = "models/gemini-embedding-001"
PRIMARY_LLM_MODEL = "gemini-flash-lite-latest"
FALLBACK_LLM_MODEL = "gemini-3.5-flash-lite"

_retrievers_cache = {}

def get_retrievers():
    """Inicializa y almacena en caché los recuperadores de manuales y casos."""
    if "manuals_retriever" in _retrievers_cache and "cases_retriever" in _retrievers_cache:
        return _retrievers_cache["manuals_retriever"], _retrievers_cache["cases_retriever"]

    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)

    # 1. Recuperador de manuales
    manuals_vectorstore = Chroma(
        persist_directory=VECTOR_DB_DIR,
        collection_name="langchain",
        embedding_function=embeddings
    )
    manuals_vector_retriever = manuals_vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 8}
    )

    if os.path.exists(BM25_DOCS_PATH):
        try:
            with open(BM25_DOCS_PATH, "rb") as f:
                bm25_chunks = pickle.load(f)
            bm25_retriever = BM25Retriever.from_documents(bm25_chunks)
            bm25_retriever.k = 8
            manuals_retriever = EnsembleRetriever(
                retrievers=[manuals_vector_retriever, bm25_retriever],
                weights=[0.5, 0.5]
            )
        except Exception as e:
            print(f"[Advertencia] Error al cargar BM25: {e}")
            manuals_retriever = manuals_vector_retriever
    else:
        manuals_retriever = manuals_vector_retriever

    # 2. Recuperador de casos de campo
    cases_vectorstore = Chroma(
        persist_directory=VECTOR_DB_DIR,
        collection_name="field_cases",
        embedding_function=embeddings
    )
    cases_retriever = cases_vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )

    _retrievers_cache["manuals_retriever"] = manuals_retriever
    _retrievers_cache["cases_retriever"] = cases_retriever
    return manuals_retriever, cases_retriever

def format_combined_context(cases_docs, manuals_docs, plant_context=""):
    """Formatea el contexto uniendo la ficha de la planta, precedentes y manuales."""
    sections = []

    # 0. Ficha específica de la planta si está seleccionada
    if plant_context:
        sections.append(plant_context)

    # 1. Casos de campo registrados por los técnicos
    if cases_docs:
        cases_text = []
        for i, doc in enumerate(cases_docs, 1):
            cases_text.append(f"--- [PRECEDENTE DE CAMPO #{i}] ---\n{doc.page_content.strip()}")
        sections.append(
            "========================================================================\n"
            "   SECCIÓN: EXPERIENCIAS Y PRECEDENTES REALES DE NUESTRO EQUIPO EN CAMPO\n"
            "   (¡PRIORIDAD MÁXIMA! Fallas reales y soluciones comprobadas por nuestros técnicos)\n"
            "========================================================================\n" +
            "\n\n".join(cases_text)
        )
    else:
        sections.append(
            "========================================================================\n"
            "   SECCIÓN: EXPERIENCIAS Y PRECEDENTES REALES EN CAMPO\n"
            "========================================================================\n"
            "[No se encontraron precedentes específicos coincidentes en la bitácora de la empresa.]"
        )

    # 2. Fragmentos de los manuales oficiales de servicio
    if manuals_docs:
        manuals_text = []
        for i, doc in enumerate(manuals_docs, 1):
            source = doc.metadata.get("source", "Manual")
            page = doc.metadata.get("page", "?")
            content = doc.page_content.strip()
            if content.startswith(f"[Manual: {source} | Página: {page}]"):
                content = content[len(f"[Manual: {source} | Página: {page}]"):].strip()
            manuals_text.append(f"--- [MANUAL TÉCNICO #{i} | {source} | Pág. {page}] ---\n{content}")
        sections.append(
            "========================================================================\n"
            "   SECCIÓN: INFORMACIÓN TÉCNICA Y ESPECIFICACIONES DE MANUALES DE SERVICIO\n"
            "========================================================================\n" +
            "\n\n".join(manuals_text)
        )

    return "\n\n".join(sections)

def build_plant_context(planta_id: int) -> tuple[str, str]:
    """
    Construye el texto enriquecido de la ficha técnica de la planta y palabras clave para RAG.
    Retorna (plant_context_text, search_keywords).
    """
    planta = db_manager.get_planta_by_id(planta_id)
    if not planta:
        return "", ""

    trabajos = db_manager.get_trabajos_by_planta(planta_id)
    trabajos_recientes = []
    for t in trabajos[:3]:
        trabajos_recientes.append(
            f"• Fecha: {t.get('fecha')} | Tipo: {t.get('tipo_trabajo')} | Horas: {t.get('horas_horometro')}h | Técnico: {t.get('tecnico')}\n"
            f"  Detalle: {t.get('titulo')}: {t.get('descripcion')}\n"
            f"  Repuestos utilizados: {t.get('repuestos_utilizados') or 'Ninguno'}"
        )
    trabajos_str = "\n\n".join(trabajos_recientes) if trabajos_recientes else "Sin mantenimientos previos registrados en el sistema."

    text = f"""
========================================================================
   FICHA TÉCNICA OFICIAL Y ESPECIFICACIONES EXACTAS DE LA PLANTA EN CONSULTA
   (¡OBLIGATORIO! Ajusta todas tus respuestas a estos componentes exactos)
========================================================================
📍 SEDE: {planta.get('sede_nombre')} [{planta.get('sede_codigo')}] - {planta.get('sede_direccion', '')}
⚙️ PLANTA: {planta.get('nombre')} (Código: {planta.get('codigo')})
🏭 ENSAMBLADORA: {planta.get('ensambladora')} | CAPACIDAD: {planta.get('capacidad_kva')} kVA ({planta.get('capacidad_kw')} kW)
⏱️ HORÓMETRO ACTUAL: {planta.get('horas_operacion')} Horas | ESTADO: {planta.get('estado')} | UBICACIÓN: {planta.get('ubicacion_interna')}

🔧 1. CARACTERÍSTICAS DEL MOTOR:
- Marca y Modelo: {planta.get('motor_marca')} {planta.get('motor_modelo')} (Serial: {planta.get('motor_serial')})
- Configuración: {planta.get('motor_cilindros')} | Potencia: {planta.get('motor_potencia_hp')} HP
- Aspiración: {planta.get('motor_aspiracion')} | Combustible: {planta.get('motor_tipo_combustible')}
- Sistema de Inyección / Gobernador: {planta.get('motor_gobernador')}
- Capacidad y Tipo de Aceite: {planta.get('motor_capacidad_aceite')} | Viscosidad recomendada: {planta.get('motor_viscosidad_aceite')}
- Sistema de Enfriamiento: {planta.get('motor_capacidad_refrigerante')} ({planta.get('motor_tipo_refrigerante')})
- FILTROS REQUERIDOS EXACTOS:
  * Filtro de Aceite Lubricante: {planta.get('motor_filtro_aceite')}
  * Filtro Combustible Primario (Separador Agua): {planta.get('motor_filtro_combustible_primario')}
  * Filtro Combustible Secundario: {planta.get('motor_filtro_combustible_secundario')}
  * Filtro de Aire: {planta.get('motor_filtro_aire')}
  * Filtro de Agua / Refrigerante: {planta.get('motor_filtro_agua_refrigerante')}
- Sistema Eléctrico DC: {planta.get('motor_sistema_electrico_dc')} | Baterías: {planta.get('motor_baterias')}
- Notas del Motor: {planta.get('motor_notas')}

⚡ 2. CARACTERÍSTICAS DEL GENERADOR (ALTERNADOR):
- Marca y Modelo: {planta.get('generador_marca')} {planta.get('generador_modelo')} (Serial: {planta.get('generador_serial')})
- Potencia: {planta.get('generador_kva')} kVA / {planta.get('generador_kw')} kW | Frecuencia: {planta.get('generador_frecuencia')} @ {planta.get('generador_rpm')} RPM
- Tensión y Fases: {planta.get('generador_voltaje')} ({planta.get('generador_fases')}) | F.P.: {planta.get('generador_factor_potencia')}
- Corriente Nominal: {planta.get('generador_amperaje_nominal')} Amperios
- Regulador de Voltaje (AVR): {planta.get('generador_modelo_avr')} | Excitación: {planta.get('generador_tipo_excitacion')}
- Aislamiento: {planta.get('generador_clase_aislamiento')}
- Notas Alternador: {planta.get('generador_notas')}

🎛️ 3. CARACTERÍSTICAS DEL CONTROLADOR Y DISPAROS DE SEGURIDAD:
- Marca y Modelo: {planta.get('controlador_marca')} {planta.get('controlador_modelo')} (Firmware: {planta.get('controlador_firmware')})
- Modo de Operación Actual: {planta.get('controlador_modo')}
- Umbrales de Disparo y Parada de Emergencia:
  * Disparo por Baja Presión de Aceite: {planta.get('controlador_umbral_baja_presion_aceite')}
  * Disparo por Alta Temperatura de Refrigerante: {planta.get('controlador_umbral_alta_temperatura')}
  * Disparo por Sobrevelocidad: {planta.get('controlador_umbral_sobrevelocidad')}
  * Sub/Sobrevoltaje: {planta.get('controlador_umbral_subvoltaje')} / {planta.get('controlador_umbral_sobrevoltaje')}
- Sensor Pick-up Magnético (MPU): {planta.get('controlador_pick_up_dientes')}
- Configuración de Entradas / Salidas: {planta.get('controlador_config_io')}
- Notas Controlador: {planta.get('controlador_notas')}

📋 4. PLAN DE MANTENIMIENTO ASIGNADO:
{planta.get('plan_mantenimiento_texto')}

🛠️ 5. HISTORIAL DE INTERVENCIONES Y REPARACIONES RECIENTES EN ESTA PLANTA:
{trabajos_str}
"""
    search_keywords = f"{planta.get('motor_marca', '')} {planta.get('motor_modelo', '')} {planta.get('generador_marca', '')} {planta.get('controlador_marca', '')} {planta.get('controlador_modelo', '')}"
    return text.strip(), search_keywords.strip()

def ask_agent(query: str, planta_id: int | None = None) -> dict:
    """
    Función principal para consultar al Agente Experto.
    Si se suministra planta_id, inyecta toda la ficha técnica y enfoca la respuesta al equipo.
    """
    # 0. Asegurar bases de datos
    db_manager.init_database()
    cases_manager.init_cases_manager()

    manuals_retriever, cases_retriever = get_retrievers()

    # 1. Extraer contexto de la planta si aplica
    plant_context_text = ""
    keywords = ""
    planta_info = None

    if planta_id:
        planta_info = db_manager.get_planta_by_id(planta_id)
        if planta_info:
            plant_context_text, keywords = build_plant_context(planta_id)

    # 2. Búsqueda RAG en casos y manuales
    search_query = f"{query} {keywords}".strip()
    try:
        cases_docs = cases_retriever.invoke(search_query)
    except Exception as e:
        print(f"[Advertencia] Error al buscar casos: {e}")
        cases_docs = []

    try:
        manuals_docs = manuals_retriever.invoke(search_query)
    except Exception as e:
        print(f"[Advertencia] Error al buscar manuales: {e}")
        manuals_docs = []

    full_context = format_combined_context(cases_docs, manuals_docs, plant_context_text)

    # 3. Modelos LLM con fallback
    primary_llm = ChatGoogleGenerativeAI(
        model=PRIMARY_LLM_MODEL,
        temperature=0.1,
        max_retries=2
    )
    fallback_llm = ChatGoogleGenerativeAI(
        model=FALLBACK_LLM_MODEL,
        temperature=0.1,
        max_retries=2
    )
    llm = primary_llm.with_fallbacks([fallback_llm])

    # 4. Prompt para el asistente
    if planta_info:
        spec_instruction = (
            f"ESTÁS ASISTIENDO EN TIEMPO REAL PARA LA PLANTA: '{planta_info.get('nombre')}' "
            f"(Sede {planta_info.get('sede_nombre')}).\n"
            f"- Motor: {planta_info.get('motor_marca')} {planta_info.get('motor_modelo')}\n"
            f"- Alternador: {planta_info.get('generador_marca')} {planta_info.get('generador_modelo')} ({planta_info.get('generador_voltaje')})\n"
            f"- Controlador: {planta_info.get('controlador_marca')} {planta_info.get('controlador_modelo')}\n\n"
            "REGLA MANDATORIA DE AJUSTE A LA MÁQUINA:\n"
            "Tus respuestas deben ajustarse ESTRICTA Y ESPECÍFICAMENTE a esta planta. "
            "Cita siempre los números de parte de filtros exactos (aceite, combustible primario/secundario, aire, refrigerante), "
            "los volúmenes de aceite en litros y galones, las calibraciones de válvulas, los potenciómetros del AVR y los bornes/parámetros del controlador "
            "según la ficha suministrada en el contexto.\n"
        )
    else:
        spec_instruction = (
            "Estás en modo General de Diagnóstico de Plantas Eléctricas Diésel. "
            "Si el usuario no ha especificado un modelo, entrega los procedimientos estándar para marcas industriales (Cummins, Caterpillar, Perkins, Deep Sea, Stamford)."
        )

    system_prompt = (
        "Eres un Ingeniero Especialista y Experto Técnico de Campo en Grupos Electrógenos, Motores Diésel y Sistemas de Transferencia Automática.\n"
        f"{spec_instruction}\n\n"
        "REGLA DE PRECEDENTES DE CAMPO (MÁXIMA PRIORIDAD):\n"
        "- Si en la sección de antecedentes de campo del contexto hay un caso que coincida con la consulta o síntoma, "
        "comienza tu respuesta mencionándolo de inmediato bajo el título '🚨 PRECEDENTE DE CAMPO EN NUESTRA EMPRESA'. "
        "Advierte al técnico sobre lo que ocurrió en ese caso previo para evitar diagnósticos erróneos en sitio.\n\n"
        "ESTRUCTURA DE RESPUESTA REQUERIDA:\n"
        "1. 🚨 PRECEDENTE EN CAMPO (si aplica a la falla o síntoma)\n"
        "2. 📋 CHECKLIST INTERACTIVO DE INSPECCIÓN RÁPIDA (con casillas '- [ ] ' para verificar visualmente fusibles, niveles, cargador de flote, selectores)\n"
        "3. 🔍 MEDICIONES CON MULTÍMETRO Y PUNTOS DE PRUEBA (con casillas '- [ ] ', especificando terminales exactos y voltajes/resistencias esperadas)\n"
        "4. ⚙️ CAUSA RAÍZ Y PROCEDIMIENTO DE SOLUCIÓN PASO A PASO (específico para el motor, AVR o controlador involucrado)\n"
        "5. 📦 INSUMOS / REPUESTOS / NÚMEROS DE PARTE RECOMENDADOS (códigos OEM de filtros, aceites y componentes aplicables)\n\n"
        "REGLAS TÉCNICAS FUNDAMENTALES:\n"
        "- ENTREGA EL PROCEDIMIENTO TÉCNICO DIRECTO: Prohibido decir 'consulte el manual en la página tal'. Explica tú mismo el procedimiento con claridad.\n"
        "- Sé profesional, conciso y de alto valor técnico para el ingeniero o técnico que está frente a la máquina.\n\n"
        "Contexto Técnico Integral:\n"
        "{context}\n\n"
        "Consulta o Falla Planteada por el Técnico: {question}"
    )

    prompt = ChatPromptTemplate.from_template(system_prompt)
    chain = prompt | llm | StrOutputParser()

    response_text = chain.invoke({"context": full_context, "question": query})

    return {
        "response": response_text,
        "planta_id": planta_id,
        "planta_nombre": planta_info.get("nombre") if planta_info else "Modo General",
        "sede_nombre": planta_info.get("sede_nombre") if planta_info else "Todas las Sedes",
        "cases_found": len(cases_docs),
        "manuals_found": len(manuals_docs)
    }

def get_expert_agent():
    """Retorna una función invocable con compatibilidad retroactiva hacia app.py."""
    class AgentWrapper:
        def invoke(self, query: str):
            res = ask_agent(query)
            return res["response"]
    return AgentWrapper()

# Exponer funciones del gestor de casos para compatibilidad
add_field_case = cases_manager.add_field_case
get_all_cases = cases_manager.get_all_cases
increment_case_utility = cases_manager.increment_case_utility
search_field_cases = cases_manager.search_field_cases

if __name__ == "__main__":
    print("Probando agente con Planta 1 (Cummins 500 kVA Torre Capriles)...")
    ans = ask_agent("¿Qué mantenimiento le corresponde a las 1500 horas y qué filtros de aceite y combustible debo llevar?", planta_id=1)
    print("\n--- RESPUESTA GENERADA ---")
    print(ans["response"])