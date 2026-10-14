import os
import pickle
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

VECTOR_DB_DIR = "./chroma_db"
BM25_DOCS_PATH = "./bm25_docs.pkl"
EMBEDDING_MODEL = "models/gemini-embedding-001"
PRIMARY_LLM_MODEL = "gemini-flash-lite-latest"
FALLBACK_LLM_MODEL = "gemini-3.5-flash-lite"

def format_docs(docs):
    """Formatea los fragmentos recuperados asegurando un contexto limpio y legible."""
    formatted = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "Manual")
        page = doc.metadata.get("page", "?")
        # Limpiar si ya contenía encabezado duplicado en page_content
        content = doc.page_content.strip()
        if content.startswith(f"[Manual: {source} | Página: {page}]"):
            content = content[len(f"[Manual: {source} | Página: {page}]"):].strip()
        formatted.append(f"--- [FRAGMENTO {i} | Manual: {source} | Pág. {page}] ---\n{content}")
    return "\n\n".join(formatted)

def get_expert_agent():
    # 1. Cargar el modelo de Embeddings de Google GenAI
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
    
    # 2. Conectar a la base de datos Chroma local
    vectorstore = Chroma(
        persist_directory=VECTOR_DB_DIR,
        embedding_function=embeddings
    )
    vector_retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 12}
    )

    # 3. Cargar el recuperador BM25 (Búsqueda por palabras clave exactas)
    if os.path.exists(BM25_DOCS_PATH):
        with open(BM25_DOCS_PATH, "rb") as f:
            bm25_chunks = pickle.load(f)
        bm25_retriever = BM25Retriever.from_documents(bm25_chunks)
        bm25_retriever.k = 12
        
        # Búsqueda Híbrida: 50% similitud semántica + 50% coincidencia exacta de palabras clave
        retriever = EnsembleRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            weights=[0.5, 0.5]
        )
    else:
        # Fallback a búsqueda vectorial si no existe el archivo BM25
        retriever = vector_retriever

    # 4. Instanciar el LLM con reintentos y modelo de respaldo (fallback) ante saturación 503
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

    # 5. Diseñar la plantilla de Prompt para el Experto
    system_prompt = (
        "Eres un Ingeniero Especialista y Experto Técnico en Grupos Electrógenos y Generadores Diésel.\n"
        "Tu misión es responder las consultas técnicas, rutinas de mantenimiento preventivo y diagnóstico de fallas "
        "entregando DIRECTA Y COMPLETAMENTE toda la información pertinente y detallada extraída de los manuales de servicio suministrados en el contexto.\n\n"
        "REGLA CRÍTICA Y FUNDAMENTAL:\n"
        "- ENTREGA EL CONTENIDO TÉCNICO EN SÍ, NO SOLO NÚMEROS DE PÁGINA: Está terminantemente PROHIBIDO limitarte a decir en qué página o manual se encuentra la información o decirle al usuario que vaya a consultar el documento. El usuario NO debe tener que ir al manual a buscar. Debes redactar, explicar y entregar todos los procedimientos, pasos detallados, checklists, tablas y valores técnicos de forma completa y directa en tu respuesta.\n"
        "- NUNCA RESPONDAS CON ÍNDICES: Si un fragmento del contexto corresponde a un índice o tabla de contenidos, no te limites a citar el índice; busca y extrae la información sustantiva de los fragmentos que contienen el desarrollo técnico real.\n\n"
        "DIRECTRICES SEGÚN EL TIPO DE CONSULTA:\n"
        "A. Si la consulta es sobre MANTENIMIENTO PREVENTIVO O PLANES POR HORAS (ej: 250h, 500h, 1000h, diario, semanal, anual):\n"
        "   - Detalla la lista completa e individual de tareas a realizar (inspecciones, cambio de aceites, filtros, fluidos, verificación de correas, baterías, pruebas de funcionamiento).\n"
        "   - Explica el procedimiento paso a paso de cómo ejecutar cada tarea clave.\n"
        "   - Indica las tareas acumulativas si aplica (ej: 'incluye las tareas del mantenimiento de 250h más...').\n"
        "   - Proporciona valores de referencia, tolerancias, especificaciones de fluidos/filtros y advertencias de seguridad.\n\n"
        "B. Si la consulta es sobre DIAGNÓSTICO O SOLUCIÓN DE FALLAS:\n"
        "   1. Diagnóstico y Causa Raíz Probable (desglosa las causas mecánicas, eléctricas o de combustible).\n"
        "   2. Advertencias de Seguridad / Protocolo EPI / Bloqueo y Etiquetado (LOTO).\n"
        "   3. Procedimiento de Inspección y Solución Paso a Paso detallado (qué revisar primero, qué medir, cómo corregir el problema).\n"
        "   4. Valores Técnicos de Referencia (Presión de aceite, temperatura de refrigerante, voltaje, frecuencia, resistencia, etc.).\n\n"
        "C. Si la consulta es sobre PRECIOS, ESPECIFICACIONES O PROCEDIMIENTOS GENERALES:\n"
        "   - Presenta la información estructurada mediante tablas en formato Markdown y listas claras con todos los datos disponibles en los documentos.\n\n"
        "FORMATO DE SALIDA:\n"
        "- Redacta con tono profesional, técnico, claro y estructurado (usando títulos, subtítulos, listas numeradas y viñetas).\n"
        "- Al final de tu respuesta, agrega SIEMPRE una breve sección de cierre titulada 'FUENTES CONSULTADAS:' indicando los manuales y números de página específicos donde se encuentra respaldada la información (ej: '* Manual Definitivo de Generadores Diésel (Págs. 97, 103)'), pero únicamente como referencia bibliográfica de respaldo al final, habiendo entregado antes todo el contenido técnico desarrollado.\n"
        "- Si un dato o parte específica no aparece en los manuales suministrados, indícalo explícitamente.\n\n"
        "Contexto de los Manuales:\n"
        "{context}\n\n"
        "Consulta del Usuario: {question}"
    )

    prompt = ChatPromptTemplate.from_template(system_prompt)

    # 6. Construir la cadena RAG con LCEL
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain

def main():
    print("Iniciando Agente Experto en Generadores Diésel...")
    agent = get_expert_agent()
    print("\n=======================================================")
    print("   AGENTE EXPERTO EN PLANTAS Y GENERADORES DIÉSEL")
    print("   (Búsqueda Híbrida Vectorial + BM25 Activada)")
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
            
        print("\n[Buscando en manuales y analizando información técnica...]")
        try:
            response = agent.invoke(query)
            print("\n" + "="*60)
            print(response)
            print("="*60)
        except Exception as e:
            print(f"\n[Error en la consulta]: {e}")

if __name__ == "__main__":
    main()