import os
import shutil
import uuid
from typing import Optional, List
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db_manager
import agent

app = FastAPI(
    title="DieselGen Intelligence - Central de Gestión y Asistente Técnico",
    version="2.0.0",
    description="Sistema Centralizado de Plantas Eléctricas Multi-Sede y Asistente Experto IA"
)

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")
TRABAJOS_UPLOADS_DIR = os.path.join(UPLOADS_DIR, "trabajos")
MANUALS_DIR = os.path.join(BASE_DIR, "Manuales")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(TRABAJOS_UPLOADS_DIR, exist_ok=True)
os.makedirs(MANUALS_DIR, exist_ok=True)

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
def on_startup():
    db_manager.init_database()

# =========================================================================
# RUTAS HTML PRINCIPALES
# =========================================================================

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>Iniciando interfaz...</h1>", status_code=200)

# =========================================================================
# API STATS & DASHBOARD
# =========================================================================

@app.get("/api/stats")
async def get_stats():
    return db_manager.get_system_stats()

@app.get("/api/dashboard/analytics")
async def get_dashboard_analytics_endpoint(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    sede_id: Optional[int] = Query(None),
    tipo_trabajo: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None)
):
    return db_manager.get_dashboard_analytics(
        year=year,
        month=month,
        sede_id=sede_id,
        tipo_trabajo=tipo_trabajo,
        categoria=categoria
    )

class DashboardAIAnalysisRequest(BaseModel):
    year: Optional[int] = None
    month: Optional[int] = None
    sede_id: Optional[int] = None
    tipo_trabajo: Optional[str] = None
    categoria: Optional[str] = None

@app.post("/api/dashboard/ai-analysis")
async def generate_dashboard_ai_analysis(payload: DashboardAIAnalysisRequest):
    analytics = db_manager.get_dashboard_analytics(
        year=payload.year,
        month=payload.month,
        sede_id=payload.sede_id,
        tipo_trabajo=payload.tipo_trabajo,
        categoria=payload.categoria
    )
    kpis = analytics["kpis"]
    periodo_str = f"Mes: {payload.month} / Año: {analytics['filter_applied']['year']}" if payload.month else f"Año Completo {analytics['filter_applied']['year']}"

    top_sedes = ", ".join([f"{s['nombre']} ({s['total_servicios']} servicios, {s['total_fallas']} fallas)" for s in analytics["sedes_ranking"][:3]])
    top_fallas = ", ".join([f"{f['categoria']} ({f['cantidad']} casos - {f['porcentaje']}%)" for f in analytics["fallas_por_categoria"][:3]])

    prompt = f"""
Actúa como el Ingeniero Consultor Senior y Jefe de Mantenimiento de Plantas Eléctricas Diésel del SENIAT.
Genera un INFORME EJECUTIVO TÉCNICO Y FINANCIERO conciso, directo y estructurado para la Gerencia de Infraestructura y Administración.

DATOS DEL PERÍODO ({periodo_str}):
• Cobertura: {kpis['total_sedes']} Sedes SENIAT analizadas, {kpis['total_plantas']} Grupos Electrógenos ({kpis['total_kva']} kVA total).
• Disponibilidad Operativa: {kpis['disponibilidad_pct']}% ({kpis['plantas_operativas']} operativas, {kpis['plantas_alerta']} en alerta/mantenimiento).
• Servicios Realizados: {kpis['total_servicios']} total ({kpis['total_preventivos']} Preventivos, {kpis['total_fallas']} Correctivos/Fallas).
• Ejecución Presupuestaria:
  - Presupuesto Proyectado: ${kpis['costo_proyectado']:,.2f}
  - Gasto Real Ejecutado: ${kpis['costo_real']:,.2f}
  - Balance/Ahorro: ${kpis['diferencia']:,.2f} ({kpis['variacion_pct']}% de variación favorable).
• Sedes con mayor actividad y fallas: {top_sedes}.
• Principales fallas y sistemas afectados: {top_fallas}.

ESTRUCTURA DEL INFORME:
1. 📌 **Diagnóstico General de la Flota**: Evaluación del % de disponibilidad y cumplimiento del plan.
2. 🚨 **Puntos Críticos por Sede**: Dónde se concentran las fallas y por qué (salitre en aduanas, horas de uso en centro de datos, etc.).
3. 💰 **Evaluación de Costos y Eficiencia**: Análisis del ahorro o variaciones detectadas.
4. 🛠️ **Plan de Acción y Recomendaciones**: 3 recomendaciones técnicas prioritarias (repuestos a almacenar, medidas preventivas).
Usa formato markdown limpio, profesional y directo.
"""
    try:
        response_text = agent.ask_agent(query=prompt).get("response", "")
        return {
            "status": "success",
            "periodo": periodo_str,
            "kpis": kpis,
            "report_markdown": response_text
        }
    except Exception as e:
        return {
            "status": "partial",
            "periodo": periodo_str,
            "kpis": kpis,
            "report_markdown": f"### 📊 Informe Ejecutivo Local ({periodo_str})\n\n- **Disponibilidad de la Flota**: {kpis['disponibilidad_pct']}%\n- **Total Servicios**: {kpis['total_servicios']} ({kpis['total_preventivos']} Preventivos, {kpis['total_fallas']} Correctivos)\n- **Balance Presupuestario**: Gasto Real ${kpis['costo_real']:,.2f} vs Proyectado ${kpis['costo_proyectado']:,.2f} (Ahorro de ${kpis['diferencia']:,.2f})\n\n*Nota: El servicio de IA externa reporta alta demanda, datos consolidados directamente desde la base de datos operativa.*"
        }


# =========================================================================
# API SEDES
# =========================================================================

@app.get("/api/sedes")
async def list_sedes():
    return db_manager.get_all_sedes()

class SedeCreateSchema(BaseModel):
    codigo: str
    nombre: str
    ciudad: Optional[str] = "Caracas"
    direccion: Optional[str] = ""
    contacto_nombre: Optional[str] = ""
    contacto_telefono: Optional[str] = ""
    contacto_cargo: Optional[str] = ""
    notas: Optional[str] = ""
    icono: Optional[str] = "🏢"

@app.post("/api/sedes")
async def create_sede(payload: SedeCreateSchema):
    try:
        sede_id = db_manager.create_sede(payload.dict())
        return {"status": "success", "id": sede_id, "message": "Sede creada exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/sedes/{sede_id}")
async def get_sede_detail(sede_id: int):
    sede = db_manager.get_sede_by_id(sede_id)
    if not sede:
        raise HTTPException(status_code=404, detail="Sede no encontrada")
    plantas = db_manager.get_plantas_by_sede(sede_id)
    return {
        "sede": sede,
        "plantas": plantas
    }

# =========================================================================
# API PLANTAS
# =========================================================================

@app.get("/api/plantas")
async def list_plantas(sede_id: Optional[int] = Query(None)):
    if sede_id:
        return db_manager.get_plantas_by_sede(sede_id)
    return db_manager.get_all_plantas()

@app.get("/api/plantas/{planta_id}")
async def get_planta_detail(planta_id: int):
    planta = db_manager.get_planta_by_id(planta_id)
    if not planta:
        raise HTTPException(status_code=404, detail="Planta no encontrada")
    trabajos = db_manager.get_trabajos_by_planta(planta_id)
    return {
        "planta": planta,
        "trabajos": trabajos
    }

@app.post("/api/plantas")
async def create_planta(payload: dict):
    try:
        planta_id = db_manager.create_planta(payload)
        return {"status": "success", "id": planta_id, "message": "Planta registrada exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/plantas/{planta_id}")
async def update_planta(planta_id: int, payload: dict):
    try:
        db_manager.update_planta(planta_id, payload)
        return {"status": "success", "message": "Planta actualizada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/plantas/{planta_id}")
async def delete_planta(planta_id: int):
    try:
        deleted = db_manager.delete_planta(planta_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Planta no encontrada")
        return {"status": "success", "message": "Planta eliminada exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =========================================================================
# API TRABAJOS DE MANTENIMIENTO & FOTOS
# =========================================================================

@app.get("/api/plantas/{planta_id}/trabajos")
async def get_trabajos_planta(planta_id: int):
    return db_manager.get_trabajos_by_planta(planta_id)

@app.post("/api/plantas/{planta_id}/trabajos")
async def add_trabajo(
    planta_id: int,
    fecha: str = Form(...),
    tipo_trabajo: str = Form(...),
    horas_horometro: float = Form(0.0),
    tecnico: str = Form(...),
    titulo: str = Form(...),
    descripcion: str = Form(...),
    repuestos_utilizados: Optional[str] = Form(""),
    observaciones: Optional[str] = Form(""),
    costo_proyectado: float = Form(0.0),
    costo_real: float = Form(0.0),
    categoria_falla: Optional[str] = Form("Lubricación y Filtros"),
    estado_servicio: Optional[str] = Form("Completado"),
    fotos: List[UploadFile] = File([])
):
    try:
        guardadas = []
        for file in fotos:
            if file.filename:
                ext = os.path.splitext(file.filename)[1].lower()
                if ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    unique_name = f"trabajo_{planta_id}_{uuid.uuid4().hex[:8]}{ext}"
                    filepath = os.path.join(TRABAJOS_UPLOADS_DIR, unique_name)
                    with open(filepath, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)
                    guardadas.append(f"/static/uploads/trabajos/{unique_name}")

        trabajo_data = {
            "planta_id": planta_id,
            "fecha": fecha,
            "tipo_trabajo": tipo_trabajo,
            "horas_horometro": horas_horometro,
            "tecnico": tecnico,
            "titulo": titulo,
            "descripcion": descripcion,
            "repuestos_utilizados": repuestos_utilizados,
            "observaciones": observaciones,
            "costo_proyectado": costo_proyectado,
            "costo_real": costo_real,
            "categoria_falla": categoria_falla,
            "estado_servicio": estado_servicio,
            "fotos": guardadas
        }
        trabajo_id = db_manager.create_trabajo(trabajo_data)
        return {
            "status": "success",
            "id": trabajo_id,
            "fotos": guardadas,
            "message": "Trabajo de mantenimiento registrado exitosamente con fotos"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =========================================================================
# API CHAT AGENTE CONTEXTUAL
# =========================================================================

class ChatRequest(BaseModel):
    message: str
    planta_id: Optional[int] = None

@app.post("/api/chat")
async def chat_with_agent(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    try:
        result = agent.ask_agent(
            query=payload.message.strip(),
            planta_id=payload.planta_id
        )
        return result
    except Exception as e:
        print(f"[Error en Chat Agente]: {e}")
        return {
            "response": (
                "⚠️ En este momento los servidores del modelo experimentan alta demanda. "
                "Por favor, intenta enviar tu consulta nuevamente en unos segundos o verifica la conexión."
            ),
            "error": str(e),
            "planta_id": payload.planta_id,
            "planta_nombre": "Error de conexión"
        }

# =========================================================================
# API BITÁCORA DE CASOS (MEMORIA TÉCNICA)
# =========================================================================

@app.get("/api/cases")
async def list_cases():
    return agent.get_all_cases()

class FieldCaseCreate(BaseModel):
    tecnico: str
    planta_modelo: str
    sintoma: str
    causa_raiz: str
    solucion: str
    descartes_previos: Optional[str] = ""
    consejo_campo: Optional[str] = ""

@app.post("/api/cases")
async def create_field_case(payload: FieldCaseCreate):
    try:
        case_id = agent.add_field_case(
            tecnico=payload.tecnico.strip(),
            planta_modelo=payload.planta_modelo.strip(),
            sintoma=payload.sintoma.strip(),
            causa_raiz=payload.causa_raiz.strip(),
            solucion=payload.solucion.strip(),
            descartes_previos=payload.descartes_previos.strip(),
            consejo_campo=payload.consejo_campo.strip()
        )
        return {"status": "success", "id": case_id, "message": "Caso registrado y aprendido por el agente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/cases/{case_id}/utility")
async def increment_case_utility(case_id: int):
    agent.increment_case_utility(case_id)
    return {"status": "success", "message": "Utilidad incrementada"}

# =========================================================================
# API MANUALES Y DOCUMENTOS TÉCNICOS
# =========================================================================

@app.get("/api/manuals")
async def list_manuals():
    return db_manager.get_all_manuals()

@app.post("/api/manuals/upload")
async def upload_manual(
    file: UploadFile = File(...),
    titulo: str = Form(...),
    categoria: str = Form("General"),
    planta_id: Optional[int] = Form(None)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos en formato PDF.")

    save_path = os.path.join(MANUALS_DIR, file.filename)
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size_mb = round(os.path.getsize(save_path) / (1024 * 1024), 2)

    with db_manager.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO manuales_meta (filename, titulo, categoria, tamano_mb, planta_id)
            VALUES (?, ?, ?, ?, ?)
        """, (file.filename, titulo, categoria, size_mb, planta_id))
        conn.commit()

    return {
        "status": "success",
        "filename": file.filename,
        "titulo": titulo,
        "tamano_mb": size_mb,
        "message": "Manual subido e indexado exitosamente"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8501))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
