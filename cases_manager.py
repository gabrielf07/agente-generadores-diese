import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "field_cases.db")
VECTOR_DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
CASES_COLLECTION_NAME = "field_cases"
EMBEDDING_MODEL = "models/gemini-embedding-001"

def get_db_connection():
    """Retorna una conexión a la base de datos SQLite con formato de diccionario."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_cases_vectorstore():
    """Inicializa y retorna la colección de Chroma dedicada a casos de campo."""
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
    return Chroma(
        persist_directory=VECTOR_DB_DIR,
        collection_name=CASES_COLLECTION_NAME,
        embedding_function=embeddings
    )

def init_cases_manager():
    """Crea la tabla en SQLite y si está vacía agrega el caso semilla inicial."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                tecnico TEXT NOT NULL,
                planta_modelo TEXT NOT NULL,
                sintoma TEXT NOT NULL,
                descartes_previos TEXT,
                causa_raiz TEXT NOT NULL,
                solucion TEXT NOT NULL,
                consejo_campo TEXT,
                utilidad_count INTEGER DEFAULT 1
            )
        """)
        conn.commit()

        # Comprobar si ya hay casos registrados
        cursor.execute("SELECT COUNT(*) as count FROM field_cases")
        row = cursor.fetchone()
        if row and row["count"] == 0:
            print("Inicializando base de datos de casos con precedente semilla...")
            # Sembrar el caso real mencionado por el usuario
            add_field_case(
                tecnico="Personal Técnico IG",
                planta_modelo="Planta Eléctrica Diésel (General / Todos los modelos)",
                sintoma="La planta no arrancaba en absoluto. No da marcha, sin respuesta en el arranque o baterías totalmente agotadas tras parada prolongada.",
                descartes_previos="Se comprobó el controlador (estaba en orden o apagado por falta de DC), fusibles principales y secundarios intactos, pero la batería no tenía carga a pesar de que el grupo debía estar en stand-by.",
                causa_raiz="El breaker termomagnético que alimenta al cargador auxiliar de baterías de flote estaba bajado/apagado en el tablero eléctrico de alimentación externa. La planta estuvo sin suministro auxiliar durante días, descargando la batería por completo.",
                solucion="1. Subir y rearmar el breaker termomagnético de alimentación del cargador auxiliar.\n2. Medir con multímetro que lleguen los 120V/220V AC al cargador de baterías.\n3. Verificar salida DC de carga de flote (13.6V - 13.8V para sistema 12V, o 27.2V - 27.6V para sistema 24V).\n4. Recargar o sustituir batería si sufrió sulfatación severa por descarga profunda.\n5. Señalizar o colocar bloqueo/precinto al breaker en el tablero del cliente para evitar desconexiones accidentales.",
                consejo_campo="Antes de asumir que la batería o el controlador están dañados, SIEMPRE verificar el led testigo del cargador de flote y comprobar que su breaker de alimentación AC en el tablero del cliente no haya sido bajado por error."
            )

def _build_case_document(case_id: int, tecnico: str, planta_modelo: str, sintoma: str,
                         causa_raiz: str, solucion: str, descartes_previos: str = "",
                         consejo_campo: str = "") -> Document:
    """Construye un documento de LangChain con formato optimizado para RAG semántico."""
    content = (
        f"[CASO REAL DE CAMPO - PRECEDENTE #{case_id}]\n"
        f"Equipo / Modelo: {planta_modelo}\n"
        f"Síntoma o Falla Reportada: {sintoma}\n"
        f"Descartes Iniciales Realizados: {descartes_previos or 'No especificado'}\n"
        f"Causa Raíz Real Comprobada en Campo: {causa_raiz}\n"
        f"Solución Aplicada y Procedimiento: {solucion}\n"
        f"Consejo Práctico de Campo: {consejo_campo or 'No especificado'}\n"
        f"Registrado por Técnico: {tecnico}\n"
    )
    metadata = {
        "source": "Experiencia de Campo",
        "case_id": case_id,
        "planta": planta_modelo,
        "tecnico": tecnico,
        "type": "field_case"
    }
    return Document(page_content=content, metadata=metadata)

def add_field_case(tecnico: str, planta_modelo: str, sintoma: str, causa_raiz: str,
                   solucion: str, descartes_previos: str = "", consejo_campo: str = "") -> int:
    """
    Registra un caso nuevo en SQLite y lo indexa de inmediato en la base vectorial de Chroma.
    Retorna el ID del caso recién creado.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO field_cases (
                tecnico, planta_modelo, sintoma, descartes_previos,
                causa_raiz, solucion, consejo_campo, utilidad_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (tecnico, planta_modelo, sintoma, descartes_previos, causa_raiz, solucion, consejo_campo))
        conn.commit()
        case_id = cursor.lastrowid

    # Indexar en Chroma Vectorstore de inmediato
    doc = _build_case_document(
        case_id=case_id,
        tecnico=tecnico,
        planta_modelo=planta_modelo,
        sintoma=sintoma,
        causa_raiz=causa_raiz,
        solucion=solucion,
        descartes_previos=descartes_previos,
        consejo_campo=consejo_campo
    )
    vectorstore = get_cases_vectorstore()
    vectorstore.add_documents([doc], ids=[f"case_{case_id}"])
    print(f"Caso #{case_id} indexado exitosamente en ChromaDB (Experiencias de Campo).")
    return case_id

def get_all_cases() -> list:
    """Retorna todos los casos registrados en orden descendente de fecha."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM field_cases ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_case_by_id(case_id: int):
    """Retorna un caso por su ID numérico."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM field_cases WHERE id = ?", (case_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def increment_case_utility(case_id: int):
    """Suma +1 al contador de utilidad de un caso cuando un técnico valida que le sirvió."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE field_cases 
            SET utilidad_count = utilidad_count + 1 
            WHERE id = ?
        """, (case_id,))
        conn.commit()

def search_field_cases(query: str, k: int = 3):
    """Busca directamente casos de campo similares a la consulta del técnico."""
    try:
        vectorstore = get_cases_vectorstore()
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        return retriever.invoke(query)
    except Exception as e:
        print(f"Error al buscar casos de campo: {e}")
        return []
