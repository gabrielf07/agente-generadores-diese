import os
import shutil
import glob
import pickle
import time
from dotenv import load_dotenv
import pdfplumber
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

MANUALS_DIR = "./Manuales"
VECTOR_DB_DIR = "./chroma_db"
BM25_DOCS_PATH = "./bm25_docs.pkl"
EMBEDDING_MODEL = "models/gemini-embedding-001"

def load_pdf_documents():
    """
    Carga todos los archivos PDF del directorio de manuales usando pdfplumber,
    extrayendo texto estructurado y tablas de manera limpia.
    """
    pdf_files = glob.glob(os.path.join(MANUALS_DIR, "*.pdf"))
    if not pdf_files:
        print(f"¡ATENCIÓN! No se encontraron archivos PDF dentro de '{MANUALS_DIR}'.")
        return []

    documents = []
    print(f"1. Encontrados {len(pdf_files)} manuales en '{MANUALS_DIR}'. Extrayendo contenido...")

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        print(f"   -> Procesando: {filename}")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # 1. Extraer texto base
                    text = page.extract_text(layout=True) or ""
                    
                    # 2. Extraer tablas si existen para no perder checklists ni especificaciones
                    tables = page.extract_tables()
                    table_texts = []
                    for table in tables:
                        if not table:
                            continue
                        rows = []
                        for row in table:
                            cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                            if any(cleaned_row):
                                rows.append(" | ".join(cleaned_row))
                        if rows:
                            table_texts.append("\n[TABLA DE DATOS / CHECKLIST]:\n" + "\n".join(rows))

                    combined_text = text.strip()
                    if table_texts:
                        combined_text += "\n\n" + "\n\n".join(table_texts)

                    if combined_text.strip():
                        doc = Document(
                            page_content=f"[Manual: {filename} | Página: {page_num}]\n{combined_text}",
                            metadata={"source": filename, "page": page_num}
                        )
                        documents.append(doc)
        except Exception as e:
            print(f"      [Error al leer {filename}]: {e}")

    print(f"   Total de páginas procesadas: {len(documents)}")
    return documents

def build_vector_store():
    documents = load_pdf_documents()
    if not documents:
        print("No hay documentos para procesar.")
        return

    print("\n2. Dividiendo documentos en fragmentos optimizados...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=250,
        separators=["\n\n", "\n", "---", ". ", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"   Total de fragmentos generados: {len(chunks)}")

    # Guardar fragmentos serializados para el recuperador BM25 (palabras clave)
    print("\n3. Guardando fragmentos para el buscador de palabras clave (BM25)...")
    with open(BM25_DOCS_PATH, "wb") as f:
        pickle.dump(chunks, f)
    print(f"   Guardado exitosamente en: {BM25_DOCS_PATH}")

    # Limpiar base de datos anterior
    if os.path.exists(VECTOR_DB_DIR):
        print("\n4. Limpiando base de datos Chroma previa...")
        try:
            shutil.rmtree(VECTOR_DB_DIR)
        except Exception as e:
            print(f"   Aviso al limpiar: {e}")

    print(f"\n5. Generando Embeddings con {EMBEDDING_MODEL} e indexando en Chroma...")
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
    
    # Inicializar base de datos Chroma
    vectorstore = Chroma(
        persist_directory=VECTOR_DB_DIR,
        embedding_function=embeddings
    )

    # Insertar en lotes de 60 fragmentos con pausas controladas para respetar la cuota
    BATCH_SIZE = 60
    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        batch_idx = (i // BATCH_SIZE) + 1
        print(f"   Indexando lote {batch_idx}/{total_batches} ({len(batch)} fragmentos)...", end="", flush=True)
        
        retries = 3
        while retries > 0:
            try:
                vectorstore.add_documents(batch)
                print(" OK")
                break
            except Exception as err:
                retries -= 1
                if "429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
                    print(" [Límite de tasa alcanzado, esperando 10s]...", end="", flush=True)
                    time.sleep(10)
                else:
                    print(f" [Error: {err}]")
                    if retries == 0:
                        raise err
                    time.sleep(3)
        
        # Pausa leve de 1 segundo entre lotes para una ingesta suave
        time.sleep(1.0)

    print(f"\n¡Indexación completada con éxito! Base de datos lista en '{VECTOR_DB_DIR}'.")

if __name__ == "__main__":
    build_vector_store()