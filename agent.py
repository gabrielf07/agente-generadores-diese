import os
import pickle
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

# Importar el gestor de experiencias de campo
import cases_manager

load_dotenv()

VECTOR_DB_DIR = "./chroma_db"
BM25_DOCS_PATH = "./bm25_docs.pkl"
EMBEDDING_MODEL = "models/gemini-embedding-001"
PRIMARY_LLM_MODEL = "gemini-flash-lite-latest"
FALLBACK_LLM_MODEL = "gemini-3.5-flash-lite"

def format_combined_context(cases_docs, manuals_docs):
    """
    Formatea el contexto en dos secciones jerarquizadas:
    1. Precedentes y experiencias reales de campo (Prioridad máxima de aprendizaje).
    2. Procedimientos técnicos y especificaciones de los manuales de servicio.
    """
    sections = []
    
    # 1. Casos de campo registrados por los técnicos
    if cases_docs:
        cases_text = []
        for i, doc in enumerate(cases_docs, 1):
            cases_text.append(f"--- [PRECEDENTE DE CAMPO #{i}] ---\n{doc.page_content.strip()}")
        sections.append(
            "========================================================================\n"
            "   SECCIÓN 1: EXPERIENCIAS Y PRECEDENTES REALES DE NUESTRO EQUIPO EN CAMPO\n"
            "   (¡PRIORIDAD MÁXIMA! Fallas reales y soluciones comprobadas por nuestros técnicos)\n"
            "========================================================================\n" +
            "\n\n".join(cases_text)
        )
    else:
        sections.append(
            "========================================================================\n"
            "   SECCIÓN 1: EXPERIENCIAS Y PRECEDENTES REALES EN CAMPO\n"
            "========================================================================\n"
            "[No se encontraron precedentes previos idénticos registrados en la bitácora de la empresa.]"
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
            manuals_text.append(f"--- [MANUAL #{i} | {source} | Pág. {page}] ---\n{content}")
        sections.append(
            "========================================================================\n"
            "   SECCIÓN 2: INFORMACIÓN TÉCNICA Y ESPECIFICACIONES DE MANUALES DE SERVICIO\n"
            "========================================================================\n" +
            "\n\n".join(manuals_text)
        )
        
    return "\n\n".join(sections)

def get_expert_agent():
    # 0. Asegurar que la base de datos de casos de campo esté inicializada
    cases_manager.init_cases_manager()

    # 1. Cargar el modelo de Embeddings de Google GenAI
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
    
    # 2. Conectar a la base de datos Chroma de Manuales (colección default: 'langchain')
    manuals_vectorstore = Chroma(
        persist_directory=VECTOR_DB_DIR,
        collection_name="langchain",
        embedding_function=embeddings
    )
    manuals_vector_retriever = manuals_vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 10}
    )

    # 3. Cargar el recuperador BM25 de Manuales
    if os.path.exists(BM25_DOCS_PATH):
        with open(BM25_DOCS_PATH, "rb") as f:
            bm25_chunks = pickle.load(f)
        bm25_retriever = BM25Retriever.from_documents(bm25_chunks)
        bm25_retriever.k = 10
        manuals_retriever = EnsembleRetriever(
            retrievers=[manuals_vector_retriever, bm25_retriever],
            weights=[0.5, 0.5]
        )
    else:
        manuals_retriever = manuals_vector_retriever

    # 4. Conectar a la base de datos Chroma de Casos de Campo (colección: 'field_cases')
    cases_vectorstore = Chroma(
        persist_directory=VECTOR_DB_DIR,
        collection_name="field_cases",
        embedding_function=embeddings
    )
    cases_retriever = cases_vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )

    # 5. Función de recuperación dual (Casos de Campo + Manuales)
    def retrieve_expert_context(query: str):
        try:
            cases_docs = cases_retriever.invoke(query)
        except Exception as e:
            print(f"[Advertencia] Error al consultar casos de campo: {e}")
            cases_docs = []

        try:
            manuals_docs = manuals_retriever.invoke(query)
        except Exception as e:
            print(f"[Advertencia] Error al consultar manuales: {e}")
            manuals_docs = []

        return format_combined_context(cases_docs, manuals_docs)

    # 6. Instanciar el LLM con reintentos y modelo de respaldo ante saturación 503
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

    # 7. Diseñar la plantilla de Prompt para el Asistente Técnico y Diagnóstico con Checklist
    system_prompt = (
        "Eres un Ingeniero Especialista y Experto Técnico en Grupos Electrógenos y Generadores Diésel.\n"
        "Tu misión es asistir al personal técnico en campo durante el diagnóstico, solución de fallas y mantenimiento preventivo, "
        "combinando las EXPERIENCIAS PREVIAS REALES DE LA EMPRESA con los MANUALES DE SERVICIO OFICIALES.\n\n"
        "REGLA DE PRECEDENTES DE CAMPO (MÁXIMA IMPORTANCIA):\n"
        "- Si en la 'SECCIÓN 1' del contexto se proporciona un PRECEDENTE DE CAMPO coincidente con la consulta o síntoma, "
        "debes mencionarlo de inmediato en tu respuesta bajo el título '🚨 PRECEDENTE DE CAMPO EN NUESTRA EMPRESA'. "
        "Advierte al técnico sobre lo que ocurrió en ese caso previo para evitar que pierda tiempo descartando piezas que no son.\n\n"
        "ESTRUCTURA OBLIGATORIA DE RESPUESTA PARA DIAGNÓSTICO Y FALLAS:\n"
        "Organiza tu respuesta con un enfoque de CHECKLIST INTERACTIVO y práctico para el técnico:\n\n"
        "1. 🚨 PRECEDENTES REALES DE LA EMPRESA (si aplica):\n"
        "   - Cita la experiencia previa relevante (ej: 'En casos anteriores registrados por nuestros técnicos con este síntoma, la causa no fue el controlador ni la batería, sino el breaker del cargador de baterías bajado en el tablero del cliente...').\n\n"
        "2. 📋 CHECKLIST DE DESCARTE RÁPIDO (Visual y Básico - Sin desarmar):\n"
        "   - Lista con casillas tipo checklist: '- [ ] Paso a verificar'\n"
        "   - Verifica interruptores, selectores, paradas de emergencia, alimentación de cargadores de flote, fusibles, niveles de fluidos y fugas.\n\n"
        "3. 🔍 CHECKLIST DE MEDICIONES Y PRUEBAS CON MULTÍMETRO:\n"
        "   - Lista con casillas tipo checklist: '- [ ] Medición o prueba'\n"
        "   - Indica los puntos exactos de medición y los valores técnicos esperados (ej: voltaje DC en reposo >12.6V, caída en arranque >9.6V, voltaje AC de alimentación, salidas de relé de marcha y combustible).\n\n"
        "4. ⚙️ CAUSAS RAÍZ PROBABLES Y PROCEDIMIENTO DE SOLUCIÓN PASO A PASO:\n"
        "   - Explica de forma completa y directa cómo solucionar cada posible causa raíz identificada.\n"
        "   - Advertencias de seguridad y protocolo de bloqueo si aplica.\n\n"
        "5. 📚 FUENTES Y ANTECEDENTES CONSULTADOS:\n"
        "   - Indica al final qué precedentes de campo y qué manuales/páginas respaldan tu respuesta.\n\n"
        "REGLAS TÉCNICAS FUNDAMENTALES:\n"
        "- ENTREGA EL CONTENIDO TÉCNICO EN SÍ: Está terminantemente PROHIBIDO limitarte a decir en qué manual o página está la información. Explica todo directamente.\n"
        "- NUNCA RESPONDAS CON ÍNDICES O GENERALIDADES VACÍAS.\n\n"
        "Contexto Técnico Suministrado:\n"
        "{context}\n\n"
        "Consulta o Falla Reportada por el Técnico: {question}"
    )

    prompt = ChatPromptTemplate.from_template(system_prompt)

    # 8. Construir la cadena RAG con LCEL
    rag_chain = (
        {"context": RunnableLambda(retrieve_expert_context), "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain

# Exponer funciones del gestor de casos para fácil importación en la app
add_field_case = cases_manager.add_field_case
get_all_cases = cases_manager.get_all_cases
increment_case_utility = cases_manager.increment_case_utility
search_field_cases = cases_manager.search_field_cases

def main():
    print("Iniciando Agente Experto con Base de Casos de Campo...")
    agent = get_expert_agent()
    print("\n=======================================================")
    print("   AGENTE EXPERTO EN PLANTAS Y GENERADORES DIÉSEL")
    print("   (RAG Híbrido: Experiencias de Campo + Manuales PDF)")
    print("=======================================================")
    print("Escribe 'salir' o 'exit' para finalizar.\n")
    
    while True:
        try:
            query = input("\n[Técnico/Usuario] Consulta o falla: ")
        except (KeyboardInterrupt, EOFError):
            print("\nFinalizando sesión...")
            break

        if not query.strip():
            continue
            
        if query.strip().lower() in ["salir", "exit", "quit"]:
            print("Cerrando asistente. ¡Buen trabajo en campo!")
            break
            
        print("\n[Consultando precedentes de campo y manuales técnicos...]")
        try:
            response = agent.invoke(query)
            print("\n" + "="*60)
            print(response)
            print("="*60)
        except Exception as e:
            print(f"\n[Error en la consulta]: {e}")

if __name__ == "__main__":
    main()