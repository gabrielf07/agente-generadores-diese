import os
import sqlite3
import json
from datetime import datetime

SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "field_cases.db")

def get_db_connection():
    """Retorna una conexión a SQLite con soporte de diccionario (Row)."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Inicializa todas las tablas de la base de datos local y carga datos semilla si está vacía."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Tabla de Sedes (Torre Capriles, Mata de Coco, Bunker, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sedes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL UNIQUE,
                nombre TEXT NOT NULL,
                ciudad TEXT DEFAULT 'Caracas',
                direccion TEXT,
                contacto_nombre TEXT,
                contacto_telefono TEXT,
                contacto_cargo TEXT,
                notas TEXT,
                icono TEXT DEFAULT '🏢',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Tabla de Plantas Eléctricas (Generadores)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plantas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sede_id INTEGER NOT NULL REFERENCES sedes(id) ON DELETE CASCADE,
                codigo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                ensambladora TEXT,
                capacidad_kva REAL NOT NULL,
                capacidad_kw REAL NOT NULL,
                ubicacion_interna TEXT,
                horas_operacion REAL DEFAULT 0.0,
                estado TEXT DEFAULT 'Operativa',
                prioridad TEXT DEFAULT 'Crítica',
                
                -- MOTOR
                motor_marca TEXT,
                motor_modelo TEXT,
                motor_serial TEXT,
                motor_cilindros TEXT,
                motor_aspiracion TEXT,
                motor_potencia_hp REAL,
                motor_tipo_combustible TEXT DEFAULT 'Diésel #2',
                motor_gobernador TEXT,
                motor_capacidad_aceite TEXT,
                motor_viscosidad_aceite TEXT DEFAULT '15W-40 CI-4 / CK-4',
                motor_capacidad_refrigerante TEXT,
                motor_tipo_refrigerante TEXT DEFAULT '50/50 Etilenglicol con aditivo DCA4',
                motor_filtro_aceite TEXT,
                motor_filtro_combustible_primario TEXT,
                motor_filtro_combustible_secundario TEXT,
                motor_filtro_aire TEXT,
                motor_filtro_agua_refrigerante TEXT,
                motor_sistema_electrico_dc TEXT DEFAULT '24V DC',
                motor_baterias TEXT,
                motor_notas TEXT,

                -- GENERADOR / ALTERNADOR
                generador_marca TEXT,
                generador_modelo TEXT,
                generador_serial TEXT,
                generador_kva REAL,
                generador_kw REAL,
                generador_voltaje TEXT,
                generador_frecuencia TEXT DEFAULT '60 Hz',
                generador_rpm INTEGER DEFAULT 1800,
                generador_fases TEXT DEFAULT 'Trifásico (4 Hilos)',
                generador_factor_potencia REAL DEFAULT 0.8,
                generador_amperaje_nominal REAL,
                generador_modelo_avr TEXT,
                generador_tipo_excitacion TEXT DEFAULT 'Brushless (Sin escobillas)',
                generador_clase_aislamiento TEXT DEFAULT 'Clase H / IP23',
                generador_notas TEXT,

                -- CONTROLADOR
                controlador_marca TEXT,
                controlador_modelo TEXT,
                controlador_firmware TEXT,
                controlador_modo TEXT DEFAULT 'Auto',
                controlador_umbral_baja_presion_aceite TEXT,
                controlador_umbral_alta_temperatura TEXT,
                controlador_umbral_sobrevelocidad TEXT,
                controlador_umbral_subvoltaje TEXT,
                controlador_umbral_sobrevoltaje TEXT,
                controlador_pick_up_dientes TEXT,
                controlador_config_io TEXT,
                controlador_notas TEXT,

                -- PLAN DE MANTENIMIENTO
                plan_mantenimiento_texto TEXT,
                proximo_mantenimiento_horas REAL,
                proximo_mantenimiento_tipo TEXT,
                manual_pdf_filename TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. Tabla de Trabajos de Mantenimiento e Intervenciones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trabajos_mantenimiento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                planta_id INTEGER NOT NULL REFERENCES plantas(id) ON DELETE CASCADE,
                fecha TEXT NOT NULL,
                tipo_trabajo TEXT NOT NULL,
                horas_horometro REAL,
                tecnico TEXT NOT NULL,
                titulo TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                repuestos_utilizados TEXT,
                observaciones TEXT,
                fotos_json TEXT DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Tabla de Manuales y Guías
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manuales_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                titulo TEXT NOT NULL,
                categoria TEXT DEFAULT 'General',
                tamano_mb REAL,
                planta_id INTEGER REFERENCES plantas(id),
                fecha_subida DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Asegurar tabla field_cases (compatibilidad previa)
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

        # Migración dinámica de columnas para dashboard ejecutivo en trabajos_mantenimiento
        cursor.execute("PRAGMA table_info(trabajos_mantenimiento)")
        existing_cols = [r["name"] for r in cursor.fetchall()]
        if "costo_proyectado" not in existing_cols:
            cursor.execute("ALTER TABLE trabajos_mantenimiento ADD COLUMN costo_proyectado REAL DEFAULT 0.0")
        if "costo_real" not in existing_cols:
            cursor.execute("ALTER TABLE trabajos_mantenimiento ADD COLUMN costo_real REAL DEFAULT 0.0")
        if "categoria_falla" not in existing_cols:
            cursor.execute("ALTER TABLE trabajos_mantenimiento ADD COLUMN categoria_falla TEXT DEFAULT 'Lubricación y Filtros'")
        if "estado_servicio" not in existing_cols:
            cursor.execute("ALTER TABLE trabajos_mantenimiento ADD COLUMN estado_servicio TEXT DEFAULT 'Completado'")

        conn.commit()

        # Sembrar Sedes iniciales si está vacío
        cursor.execute("SELECT COUNT(*) as cnt FROM sedes")
        if cursor.fetchone()["cnt"] == 0:
            _seed_initial_data(conn)

        # Asegurar enriquecimiento de sedes, plantas e histórico 2026 para el Dashboard
        _ensure_rich_powerbi_data(conn)

def _seed_initial_data(conn):
    """Inserta las sedes de SENIAT, plantas con fichas completas y mantenimientos con fotos."""
    cursor = conn.cursor()

    # --- SEDE 1: TORRE CAPRILES ---
    cursor.execute("""
        INSERT INTO sedes (codigo, nombre, ciudad, direccion, contacto_nombre, contacto_telefono, contacto_cargo, notas, icono)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "SENIAT-TC",
        "SENIAT - Torre Capriles",
        "Caracas",
        "Plaza Venezuela, Av. Abraham Lincoln, Torre Capriles",
        "Ing. Coordinador de Infraestructura SENIAT",
        "+58 414-2345678",
        "Jefe de Mantenimiento e Instalaciones",
        "Sede administrativa principal con alto flujo operativo. Posee dos grupos electrógenos en sala de máquinas sótano 2.",
        "🏢"
    ))
    sede_tc_id = cursor.lastrowid

    # --- SEDE 2: MATA DE COCO ---
    cursor.execute("""
        INSERT INTO sedes (codigo, nombre, ciudad, direccion, contacto_nombre, contacto_telefono, contacto_cargo, notas, icono)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "SENIAT-MC",
        "SENIAT - Mata de Coco",
        "Caracas",
        "Av. Blandín, Centro Comercial Mata de Coco, Chacao",
        "Lic. Operaciones y Servicios Generales",
        "+58 412-9876543",
        "Supervisor de Guardia",
        "Sede de atención y recaudación tributaria metropolitana. Grupo en caseta insonorizada en patio posterior.",
        "🏛️"
    ))
    sede_mc_id = cursor.lastrowid

    # --- SEDE 3: EL BÚNKER ---
    cursor.execute("""
        INSERT INTO sedes (codigo, nombre, ciudad, direccion, contacto_nombre, contacto_telefono, contacto_cargo, notas, icono)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "SENIAT-BK",
        "SENIAT - El Búnker",
        "Caracas",
        "Complejo Tecnológico y Centro de Datos SENIAT",
        "Ing. Sistemas y Energía Ininterrumpida",
        "+58 416-5551234",
        "Gerente de Continuidad Operativa",
        "Centro de datos y servidores fiscales críticos. Esquema de generación redundante N+1 con generadores pesados.",
        "🛡️"
    ))
    sede_bk_id = cursor.lastrowid

    # =========================================================================
    # PLANTAS PARA TORRE CAPRILES
    # =========================================================================
    plan_cummins_tc = (
        "📋 PLAN DE MANTENIMIENTO PREVENTIVO - MOTOR CUMMINS QSL9 / GENERADOR STAMFORD:\n\n"
        "• SERVICIO DIARIO / PRE-ARRANQUE:\n"
        "  - Inspección visual de fugas de aceite, refrigerante y combustible.\n"
        "  - Comprobar nivel de aceite en varilla (debe estar entre marcas ADD y FULL).\n"
        "  - Comprobar nivel de refrigerante en tanque de expansión (mínimo 2 pulgadas bajo cuello de llenado).\n"
        "  - Verificar que el calentador de camisa (block heater) mantenga el motor tibio (40°C - 50°C).\n"
        "  - Verificar voltaje de baterías en controlador DSE (mínimo 25.4V DC en flote).\n\n"
        "• SERVICIO 'A' (CADA 250 HORAS O 6 MESES):\n"
        "  - Drenar y cambiar aceite de motor (26.5 Litros SAE 15W-40 CI-4/CK-4).\n"
        "  - Reemplazar filtro de aceite lubricante de flujo total: Fleetguard LF9009 (o equivalente).\n"
        "  - Reemplazar filtro separador de agua/combustible: Fleetguard FS1000.\n"
        "  - Reemplazar filtro secundario de combustible: Fleetguard FF5612.\n"
        "  - Drenar agua y sedimentos del fondo del tanque diario de gasoil.\n"
        "  - Verificar y ajustar tensión de correas de ventilador y alternador de carga (deflexión 10 mm).\n"
        "  - Limpieza de bornes de baterías de arranque y aplicación de grasa dieléctrica.\n\n"
        "• SERVICIO 'B' (CADA 500 HORAS O 1 AÑO):\n"
        "  - Realizar todos los puntos del Servicio 'A'.\n"
        "  - Reemplazar elemento de filtro de aire principal: Fleetguard AF26173.\n"
        "  - Reemplazar filtro de agua/refrigerante con aditivo inhibidor de corrosión: Fleetguard WF2071.\n"
        "  - Limpieza exterior de panal de radiador con desengrasante y agua a baja presión.\n"
        "  - Reapriete de pernos de base anti-vibratoria y acople motor-generador.\n"
        "  - Revisión y ajuste de terminales de potencia en caja del alternador y breaker motorizado.\n\n"
        "• SERVICIO MAYOR (CADA 1000 HORAS O 2 AÑOS):\n"
        "  - Realizar todos los puntos de Servicios 'A' y 'B'.\n"
        "  - Calibración de holgura de válvulas de motor e inyectores (Admisión: 0.30 mm / Escape: 0.58 mm).\n"
        "  - Calibración y prueba dinámica del regulador de voltaje Stamford AS440.\n"
        "  - Prueba de disparo y respuesta de protecciones en controlador Deep Sea DSE 7320 MKII.\n"
        "  - Prueba operativa con banco de carga resistiva al 100% durante 2 horas continuas."
    )

    cursor.execute("""
        INSERT INTO plantas (
            sede_id, codigo, nombre, ensambladora, capacidad_kva, capacidad_kw,
            ubicacion_interna, horas_operacion, estado, prioridad,
            motor_marca, motor_modelo, motor_serial, motor_cilindros, motor_aspiracion,
            motor_potencia_hp, motor_tipo_combustible, motor_gobernador,
            motor_capacidad_aceite, motor_viscosidad_aceite, motor_capacidad_refrigerante,
            motor_tipo_refrigerante, motor_filtro_aceite, motor_filtro_combustible_primario,
            motor_filtro_combustible_secundario, motor_filtro_aire, motor_filtro_agua_refrigerante,
            motor_sistema_electrico_dc, motor_baterias, motor_notas,
            generador_marca, generador_modelo, generador_serial, generador_kva, generador_kw,
            generador_voltaje, generador_frecuencia, generador_rpm, generador_fases,
            generador_factor_potencia, generador_amperaje_nominal, generador_modelo_avr,
            generador_tipo_excitacion, generador_clase_aislamiento, generador_notas,
            controlador_marca, controlador_modelo, controlador_firmware, controlador_modo,
            controlador_umbral_baja_presion_aceite, controlador_umbral_alta_temperatura,
            controlador_umbral_sobrevelocidad, controlador_umbral_subvoltaje, controlador_umbral_sobrevoltaje,
            controlador_pick_up_dientes, controlador_config_io, controlador_notas,
            plan_mantenimiento_texto, proximo_mantenimiento_horas, proximo_mantenimiento_tipo,
            manual_pdf_filename
        ) VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?
        )
    """, (
        sede_tc_id, "GEN-TC-01", "Planta Principal Cummins 500 kVA - Sede Torre Capriles",
        "Cummins Power Generation", 500.0, 400.0,
        "Sótano 2 - Sala de Máquinas A (Cubículo 1)", 1410.0, "Operativa", "Crítica",
        # Motor
        "Cummins", "QSL9-G5", "46892341", "6 cilindros en línea (8.9 Litros)", "Turboalimentado y Posenfriado Aire-Aire (Charge Air Cooled)",
        450.0, "Diésel #2", "Electrónico ECM Quantum / Bosch High Pressure Common Rail",
        "26.5 Litros (7.0 Galones US)", "SAE 15W-40 API CK-4 / CI-4 Plus", "30 Litros en circuito de motor y radiador",
        "50/50 Etilenglicol con aditivo suplementario DCA4 Fleetguard",
        "Fleetguard LF9009 (Flujo pleno + derivación en un solo cuerpo)",
        "Fleetguard FS1000 (Separador de agua 10 micras con sensor y purga)",
        "Fleetguard FF5612 (Filtro fino de alta eficiencia 2 micras)",
        "Fleetguard AF26173 (RadialSeal de alto flujo)",
        "Fleetguard WF2071 (Filtro con pastilla química de aditivo)",
        "24V DC con alternador de carga Delco Remy 24SI (45 Amp)",
        "2 baterías de plomo-ácido 12V 1000 CCA conectadas en serie (24V)",
        "Bomba de elevación eléctrica y cebador manual. Mantener calentador de camisa de 2000W conectado a 208V AC.",
        # Generador
        "Stamford", "HCI534C", "0245678/001", 500.0, 400.0,
        "208/120V Trifásico", "60 Hz", 1800, "Trifásico (4 Hilos reconectable)",
        0.8, 1388.0, "AS440 (Regulador de Voltaje Automático)",
        "Sin escobillas (Brushless) con excitatriz giratoria y diodos de potencia",
        "Clase H (IP23)", "Resistencias anticondensación conectadas a 120V cuando el grupo está en reposo.",
        # Controlador
        "Deep Sea Electronics", "DSE 7320 MKII", "v3.2.1", "Auto (Vinculado a ATS ASCO 7000)",
        "18 PSI (1.2 bar) - Disparo instantáneo con apagado de emergencia",
        "102 °C (215 °F) - Disparo con 2 minutos de enfriamiento",
        "2070 RPM (69 Hz) - Disparo inmediato",
        "180 V Fase-Neutro (-15%)", "240 V Fase-Neutro (+15%)",
        "126 dientes en la cremallera del volante (Sensor MPU 5/8-18 UNF)",
        "Output 1: Solenoide combustible; Output 2: Motor arranque; Input 1: Nivel refrigerante; Input 2: Falla ATS",
        "Puerto RS485 activo para monitoreo centralizado Modbus RTU.",
        # Plan
        plan_cummins_tc, 1500.0, "Mantenimiento Preventivo A (250h)",
        "Manual Definitivo de Generadores Diésel.pdf"
    ))
    planta_tc1_id = cursor.lastrowid

    # Planta 2 Torre Capriles: Caterpillar C15 500 kVA
    plan_cat_tc = (
        "📋 PLAN DE MANTENIMIENTO PREVENTIVO - MOTOR CATERPILLAR C15 ACERT:\n\n"
        "• DIARIO: Nivel de aceite motor (Varilla graduada), drenar tazón de combustible primario, verificar refrigerante Cat ELC.\n"
        "• CADA 250 HORAS: Cambio de aceite Cat DEO-ULS 15W-40 (38 Litros). Cambio de filtro de aceite 1R-1808. Reemplazo de filtros de combustible primario 1R-0770 y secundario 1R-0749.\n"
        "• CADA 500 HORAS: Cambio de filtros de aire de motor 110-6326. Inspección de mangueras de turbocompresor y abrazaderas de par constante.\n"
        "• CADA 1000 HORAS / ANUAL: Inspección y calibración de holgura de válvulas e inyectores unitarios electrónicos MEUI. Análisis de aceite SOS. Prueba de funcionamiento del calentador de camisa."
    )

    cursor.execute("""
        INSERT INTO plantas (
            sede_id, codigo, nombre, ensambladora, capacidad_kva, capacidad_kw,
            ubicacion_interna, horas_operacion, estado, prioridad,
            motor_marca, motor_modelo, motor_serial, motor_cilindros, motor_aspiracion,
            motor_potencia_hp, motor_tipo_combustible, motor_gobernador,
            motor_capacidad_aceite, motor_viscosidad_aceite, motor_capacidad_refrigerante,
            motor_tipo_refrigerante, motor_filtro_aceite, motor_filtro_combustible_primario,
            motor_filtro_combustible_secundario, motor_filtro_aire, motor_filtro_agua_refrigerante,
            motor_sistema_electrico_dc, motor_baterias, motor_notas,
            generador_marca, generador_modelo, generador_serial, generador_kva, generador_kw,
            generador_voltaje, generador_frecuencia, generador_rpm, generador_fases,
            generador_factor_potencia, generador_amperaje_nominal, generador_modelo_avr,
            generador_tipo_excitacion, generador_clase_aislamiento, generador_notas,
            controlador_marca, controlador_modelo, controlador_firmware, controlador_modo,
            controlador_umbral_baja_presion_aceite, controlador_umbral_alta_temperatura,
            controlador_umbral_sobrevelocidad, controlador_umbral_subvoltaje, controlador_umbral_sobrevoltaje,
            controlador_pick_up_dientes, controlador_config_io, controlador_notas,
            plan_mantenimiento_texto, proximo_mantenimiento_horas, proximo_mantenimiento_tipo,
            manual_pdf_filename
        ) VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?
        )
    """, (
        sede_tc_id, "GEN-TC-02", "Planta Respaldo Caterpillar C15 500 kVA - Sede Torre Capriles",
        "Caterpillar Inc.", 500.0, 400.0,
        "Sótano 2 - Sala de Máquinas A (Cubículo 2 - Respaldo)", 980.0, "Operativa", "Alta",
        # Motor
        "Caterpillar", "C15 ACERT", "FSE01984", "6 en línea (15.2 Litros)", "Turboalimentado con enfriador ATAAC",
        540.0, "Diésel #2", "ECM ADEM A4 Caterpillar",
        "38 Litros (10 Galones)", "Cat DEO 15W-40 CI-4", "45 Litros",
        "Cat ELC (Extended Life Coolant) Larga Duración Rojo",
        "Cat 1R-1808 (Filtro de aceite avanzado)",
        "Cat 1R-0770 (Separador agua/combustible)",
        "Cat 1R-0749 (Filtro secundario de combustible 2 micras)",
        "Cat 110-6326 (Elemento primario de aire)",
        "N/A (Utiliza refrigerante de larga vida Cat ELC sin pastilla)",
        "24V DC con alternador Cat 55 Amp",
        "2x Baterías Cat Premium High Output 1400 CCA",
        "Calentador de bloque de 2.5 kW. Purgador manual de combustible tipo émbolo.",
        # Generador
        "Leroy Somer", "TAL 0473", "LS-45892", 500.0, 400.0,
        "208/120V Trifásico", "60 Hz", 1800, "Trifásico (4 Hilos)",
        0.8, 1388.0, "R450 (Regulador de Voltaje con Diodo Limitador LAM)",
        "Shunt / PMG Opcional", "Clase H", "Régimen Standby de emergencia.",
        # Controlador
        "ComAp", "InteliLite 4 AMF 25", "v1.4.0", "Auto",
        "20 PSI (1.37 bar)", "104 °C (220 °F)", "2070 RPM",
        "180 V L-N", "240 V L-N", "113 dientes", "Configurado con módulos de expansión BIN8 y BOUT8",
        "Display gráfico a color con historial de 350 eventos.",
        plan_cat_tc, 1000.0, "Servicio Mayor 1000 Horas",
        "Manual Definitivo de Generadores Diésel.pdf"
    ))

    # =========================================================================
    # PLANTAS PARA MATA DE COCO
    # =========================================================================
    plan_perkins_mc = (
        "📋 PLAN DE MANTENIMIENTO - MOTOR PERKINS 1306C-E87TAG6 / GENERADOR LEROY SOMER:\n\n"
        "• Cada 250 Horas: Aceite 15W-40 (27 L), filtro aceite Perkins 2654407, filtros combustible Perkins 26560201.\n"
        "• Cada 500 Horas: Filtro aire Perkins 26510342, limpieza radiador, prueba de aislamiento megado generador (>5 Megaohmios).\n"
        "• Anual: Inspección de mangueras, limpieza de tanque de gasoil, verificación de calibración AVR R250."
    )

    cursor.execute("""
        INSERT INTO plantas (
            sede_id, codigo, nombre, ensambladora, capacidad_kva, capacidad_kw,
            ubicacion_interna, horas_operacion, estado, prioridad,
            motor_marca, motor_modelo, motor_serial, motor_cilindros, motor_aspiracion,
            motor_potencia_hp, motor_tipo_combustible, motor_gobernador,
            motor_capacidad_aceite, motor_viscosidad_aceite, motor_capacidad_refrigerante,
            motor_tipo_refrigerante, motor_filtro_aceite, motor_filtro_combustible_primario,
            motor_filtro_combustible_secundario, motor_filtro_aire, motor_filtro_agua_refrigerante,
            motor_sistema_electrico_dc, motor_baterias, motor_notas,
            generador_marca, generador_modelo, generador_serial, generador_kva, generador_kw,
            generador_voltaje, generador_frecuencia, generador_rpm, generador_fases,
            generador_factor_potencia, generador_amperaje_nominal, generador_modelo_avr,
            generador_tipo_excitacion, generador_clase_aislamiento, generador_notas,
            controlador_marca, controlador_modelo, controlador_firmware, controlador_modo,
            controlador_umbral_baja_presion_aceite, controlador_umbral_alta_temperatura,
            controlador_umbral_sobrevelocidad, controlador_umbral_subvoltaje, controlador_umbral_sobrevoltaje,
            controlador_pick_up_dientes, controlador_config_io, controlador_notas,
            plan_mantenimiento_texto, proximo_mantenimiento_horas, proximo_mantenimiento_tipo,
            manual_pdf_filename
        ) VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?
        )
    """, (
        sede_mc_id, "GEN-MC-01", "Planta FG Wilson Perkins 250 kVA - Sede Mata de Coco",
        "FG Wilson", 250.0, 200.0,
        "Caseta Insonorizada - Patio Exterior", 745.0, "Operativa", "Alta",
        "Perkins", "1306C-E87TAG6", "WS51234N", "6 en línea (8.7 Litros)", "Turboalimentado Intercooled",
        260.0, "Diésel #2", "Electrónico ECM Perkins",
        "27.0 Litros", "15W-40 CI-4", "24.0 Litros", "50/50 Agua desmineralizada con glicol",
        "Perkins 2654407", "Perkins 26560201", "Perkins 26561117", "Perkins 26510342", "N/A",
        "24V DC", "2x 12V 800 CCA", "Insonorización a 72 dB(A) a 7 metros.",
        "Leroy Somer", "LL5014F", "LS-98213", 250.0, 200.0,
        "208/120V Trifásico", "60 Hz", 1800, "Trifásico 4 Hilos",
        0.8, 694.0, "R250", "Brushless Shunt", "Clase H", "Bobinado auxiliar.",
        "Deep Sea Electronics", "DSE 7320", "v2.8", "Auto",
        "16 PSI", "103 °C", "2070 RPM", "180 V", "240 V",
        "136 dientes", "Salidas para alarma estroboscópica y sirena.", "Controlador robusto.",
        plan_perkins_mc, 750.0, "Mantenimiento Preventivo A (250h)",
        "Checklist_Mantenimiento+(1).pdf"
    ))

    # =========================================================================
    # PLANTAS PARA EL BÚNKER (CENTRO DE DATOS)
    # =========================================================================
    plan_cummins_bk = (
        "📋 PLAN DE MANTENIMIENTO PESADO - CUMMINS QST30-G4 (1000 kVA):\n\n"
        "• DIARIO: Inspección visual integral, presiones de combustible, precalentadores de camisa de 4kW.\n"
        "• 250 HORAS: Cambio de 154 Litros de aceite 15W-40. Reemplazo de 3 filtros de aceite LF9000. Reemplazo de 2 filtros Fleetguard FS1006 y 2 filtros secundarios FF5488.\n"
        "• 500 HORAS: 2x Filtros de aire de doble elemento AF25544. Reemplazo de 2 filtros de refrigerante WF2075. Muestreo de aceite y refrigerante.\n"
        "• ANUAL: Prueba de sincronismo automático con DSE 8620 y banco de carga."
    )

    cursor.execute("""
        INSERT INTO plantas (
            sede_id, codigo, nombre, ensambladora, capacidad_kva, capacidad_kw,
            ubicacion_interna, horas_operacion, estado, prioridad,
            motor_marca, motor_modelo, motor_serial, motor_cilindros, motor_aspiracion,
            motor_potencia_hp, motor_tipo_combustible, motor_gobernador,
            motor_capacidad_aceite, motor_viscosidad_aceite, motor_capacidad_refrigerante,
            motor_tipo_refrigerante, motor_filtro_aceite, motor_filtro_combustible_primario,
            motor_filtro_combustible_secundario, motor_filtro_aire, motor_filtro_agua_refrigerante,
            motor_sistema_electrico_dc, motor_baterias, motor_notas,
            generador_marca, generador_modelo, generador_serial, generador_kva, generador_kw,
            generador_voltaje, generador_frecuencia, generador_rpm, generador_fases,
            generador_factor_potencia, generador_amperaje_nominal, generador_modelo_avr,
            generador_tipo_excitacion, generador_clase_aislamiento, generador_notas,
            controlador_marca, controlador_modelo, controlador_firmware, controlador_modo,
            controlador_umbral_baja_presion_aceite, controlador_umbral_alta_temperatura,
            controlador_umbral_sobrevelocidad, controlador_umbral_subvoltaje, controlador_umbral_sobrevoltaje,
            controlador_pick_up_dientes, controlador_config_io, controlador_notas,
            plan_mantenimiento_texto, proximo_mantenimiento_horas, proximo_mantenimiento_tipo,
            manual_pdf_filename
        ) VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?
        )
    """, (
        sede_bk_id, "GEN-BK-01", "Planta Centro de Datos Búnker #1 - Cummins 1000 kVA",
        "Cummins Power Generation", 1000.0, 800.0,
        "Sala de Energía Blindada - Planta Baja", 620.0, "Operativa", "Crítica",
        "Cummins", "QST30-G4", "37190823", "V12 Cilindros en V (30.5 Litros)", "Turboalimentado doble y post-enfriado",
        1050.0, "Diésel #2", "Bosch Electronic Fuel System con control G-Drive",
        "154 Litros (40.7 Galones)", "SAE 15W-40 CK-4 Heavy Duty", "140 Litros",
        "Fleetguard Compleat 50/50 premix",
        "3x Fleetguard LF9000 (Combinados de flujo total)",
        "2x Fleetguard FS1006 (Separadores de agua de alto flujo)",
        "2x Fleetguard FF5488 (Filtros de combustible alta presión)",
        "2x Fleetguard AF25544 (Aire para trabajo pesado)",
        "2x Fleetguard WF2075 con aditivos DCA4",
        "24V DC con 2 motores de arranque en paralelo Delco Remy 39MT",
        "4x Baterías 12V 1300 CCA (2 en serie, 2 ramas en paralelo)",
        "Calentadores duales de 4 kW para arranque inmediato bajo 10 segundos.",
        "Stamford", "HVSI804R", "0199482/01", 1000.0, 800.0,
        "480/277V Trifásico", "60 Hz", 1800, "Trifásico 4 Hilos",
        0.8, 1202.0, "MX321 con excitación PMG permanente",
        "PMG (Permanent Magnet Generator) de alta inmunidad armónica", "Clase H",
        "Transformadores de corriente de protección 1500/5A instalados.",
        "Deep Sea Electronics", "DSE 8620 MKII", "v4.1.0", "Auto (Sincronismo automático)",
        "22 PSI (1.5 bar)", "102 °C (215 °F)", "2070 RPM", "415 V", "520 V",
        "159 dientes", "Comandos de cierre de interruptor motorizado ABB Emax2",
        "Conectado a SCADA central mediante Ethernet TCP/IP.",
        plan_cummins_bk, 750.0, "Mantenimiento Preventivo A (250h)",
        "Generadores Diésel Las 50 Fallas Más Comunes--y--Sus--Soluciones.pdf"
    ))

    # =========================================================================
    # HISTORIAL DE TRABAJOS DE MANTENIMIENTO INICIALES (CON FOTOS REALES)
    # =========================================================================
    # Trabajo 1: Mantenimiento 250h en Cummins 500 kVA Torre Capriles
    fotos_t1 = json.dumps(["/static/uploads/sample/cummins_filters_service.jpg"])
    cursor.execute("""
        INSERT INTO trabajos_mantenimiento (
            planta_id, fecha, tipo_trabajo, horas_horometro, tecnico,
            titulo, descripcion, repuestos_utilizados, observaciones, fotos_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        planta_tc1_id,
        "2026-09-15",
        "Mantenimiento Preventivo A (250h)",
        1250.0,
        "Gabriel F.",
        "Mantenimiento Preventivo 250 Horas: Aceite y Tren de Filtración Completo",
        "Se ejecutó mantenimiento preventivo de acuerdo al manual OEM Cummins QSL9. Drenaje completo de aceite lubricante en caliente, desmontaje y reemplazo de filtro de aceite Fleetguard LF9009, reemplazo de filtro separador de combustible primario FS1000 y secundario FF5612. Se realizó purga del circuito de combustible y cebado. Limpieza de panal de radiador con aire comprimido. Se verificó tensión de correa del alternador de carga auxiliar (deflexión correcta de 10 mm). Prueba de arranque en modo manual con toma de lecturas: Presión de aceite estable en 45 PSI a 1800 RPM, temperatura de refrigerante en 82°C. Posteriormente se transfirió la carga del edificio durante 45 minutos trabajando al 65% de capacidad nominal sin caída de frecuencia ni temperatura anormal.",
        "1x Filtro de Aceite Fleetguard LF9009, 1x Filtro Separador FS1000, 1x Filtro Fino FF5612, 7 Galones Aceite Mobil Delvac 15W-40 CI-4, 1x O-ring de tapón de drenaje.",
        "Se recomienda al personal de custodia mantener el breaker del cargador de flote cerrado en todo momento. Nivel de combustible en tanque diario al 90%.",
        fotos_t1
    ))

    # Trabajo 2: Calibración y Mantenimiento de Alternador Stamford
    fotos_t2 = json.dumps(["/static/uploads/sample/stamford_avr_sx460.jpg"])
    cursor.execute("""
        INSERT INTO trabajos_mantenimiento (
            planta_id, fecha, tipo_trabajo, horas_horometro, tecnico,
            titulo, descripcion, repuestos_utilizados, observaciones, fotos_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        planta_tc1_id,
        "2026-10-02",
        "Calibración y Pruebas Eléctricas",
        1310.0,
        "Gabriel F.",
        "Inspección de Caja de Conexiones y Calibración de Estabilidad en Regulador AVR",
        "Se atendió reporte de leve fluctuación de voltaje (±7 VAC) en vacío. Se retiró la tapa superior de la caja de terminales del alternador Stamford HCI534C. Se realizó limpieza con desengrasante dieléctrico de la tarjeta AVR Stamford AS440. Se comprobaron los puentes de selección de frecuencia (60 Hz habilitado), se reajustó el potenciómetro de estabilidad (STABILITY) para amortiguar oscilaciones dinámicas y se calibró el voltaje de salida en exactamente 208.0 VAC entre fases y 120.2 VAC fase a neutro. Se comprobaron los diodos de la rueda giratoria de excitatriz y el varistor de protección contra picos transitorios, encontrándose en valores normales. Terminales de cobre L1, L2, L3 y N torquedos a especificación con torquímetro.",
        "Limpiador de contactos dieléctrico CRC, 4x terminales de compresión de señal 16 AWG sustituidos por sulfatación preventiva.",
        "Voltaje totalmente estabilizado. Se realizaron 3 ciclos de corte y transferencia con respuesta en menos de 0.8 segundos sin sobretensión.",
        fotos_t2
    ))

    # Trabajo 3: Revisión de Controlador DSE 7320 y Sensores
    fotos_t3 = json.dumps(["/static/uploads/sample/dse7320_multimeter_check.jpg"])
    cursor.execute("""
        INSERT INTO trabajos_mantenimiento (
            planta_id, fecha, tipo_trabajo, horas_horometro, tecnico,
            titulo, descripcion, repuestos_utilizados, observaciones, fotos_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        planta_tc1_id,
        "2026-10-12",
        "Inspección y Diagnóstico",
        1410.0,
        "Personal Técnico IG",
        "Verificación de Señales Analógicas, MPU Pick-up y Tiempos de Conmutación ATS",
        "Chequeo preventivo semestral de cableado de control y potencia en gabinete de mando. Con multímetro digital se midió alimentación en bornes 1 y 2 del controlador DSE 7320 (26.8 VDC de flote constante). Se midió la resistencia del sensor magnético pick-up (MPU) en cremallera (145 Ohmios, señal AC pico de 3.2 VAC al girar con motor de arranque). Verificación de disparo de parada de emergencia remota y prueba de corte de fase simulando pérdida de red en tablero ATS ASCO. El controlador detectó la falla en 1.5 segundos, activó la orden de marcha, alcanzó frecuencia de 60 Hz en 4.2 segundos y cerró el contactor de generador a los 7.8 segundos.",
        "1x Relé encapsulado Omron MY4N 24VDC de control de marcha sustituido por precaución de horas de uso.",
        "Sistema 100% operativo y en modo 'AUTO'. Próxima intervención preventiva programada a las 1500 horas.",
        fotos_t3
    ))

    # Registrar metadatos de los manuales que ya están en la carpeta Manuales
    manuals_seed = [
        ("Manual Definitivo de Generadores Diésel.pdf", "Manual Definitivo de Generadores Diésel", "General", 60.2),
        ("Generadores Diésel Las 50 Fallas Más Comunes--y--Sus--Soluciones.pdf", "Las 50 Fallas Más Comunes y Sus Soluciones en Grupos Electrógenos", "Fallas y Soluciones", 2.1),
        ("Checklist_Mantenimiento+(1).pdf", "Checklist de Mantenimiento Integral de Plantas", "Mantenimiento", 0.05),
        ("tabla+precificacion+30+servicios+generadores+diesel.pdf", "Tabla de Procedimientos y Servicios Diésel", "Procedimientos", 0.01)
    ]
    for fn, tit, cat, sz in manuals_seed:
        cursor.execute("""
            INSERT OR IGNORE INTO manuales_meta (filename, titulo, categoria, tamano_mb)
            VALUES (?, ?, ?, ?)
        """, (fn, tit, cat, sz))

    conn.commit()
    print("¡Base de datos local inicializada exitosamente con Sedes, Plantas, Fichas Técnicas, Mantenimientos y Fotos!")

# Funciones de consulta para la API y la interfaz

def get_all_sedes():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, 
                   COUNT(p.id) as total_plantas,
                   SUM(CASE WHEN p.estado = 'Operativa' THEN 1 ELSE 0 END) as plantas_operativas,
                   SUM(CASE WHEN p.estado != 'Operativa' THEN 1 ELSE 0 END) as plantas_alerta,
                   COALESCE(SUM(p.capacidad_kva), 0) as total_kva
            FROM sedes s
            LEFT JOIN plantas p ON s.id = p.sede_id
            GROUP BY s.id
            ORDER BY s.id ASC
        """)
        return [dict(r) for r in cursor.fetchall()]

def get_sede_by_id(sede_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sedes WHERE id = ?", (sede_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_sede(data: dict) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sedes (codigo, nombre, ciudad, direccion, contacto_nombre, contacto_telefono, contacto_cargo, notas, icono)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("codigo", "").strip().upper(),
            data.get("nombre", "").strip(),
            data.get("ciudad", "Caracas").strip(),
            data.get("direccion", "").strip(),
            data.get("contacto_nombre", "").strip(),
            data.get("contacto_telefono", "").strip(),
            data.get("contacto_cargo", "").strip(),
            data.get("notas", "").strip(),
            data.get("icono", "🏢").strip()
        ))
        conn.commit()
        return cursor.lastrowid

def get_plantas_by_sede(sede_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, s.nombre as sede_nombre,
                   (SELECT COUNT(*) FROM trabajos_mantenimiento tm WHERE tm.planta_id = p.id) as total_mantenimientos,
                   (SELECT MAX(fecha) FROM trabajos_mantenimiento tm WHERE tm.planta_id = p.id) as ultima_fecha_mantenimiento
            FROM plantas p
            JOIN sedes s ON p.sede_id = s.id
            WHERE p.sede_id = ?
            ORDER BY p.id ASC
        """, (sede_id,))
        return [dict(r) for r in cursor.fetchall()]

def get_all_plantas():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, s.nombre as sede_nombre, s.codigo as sede_codigo,
                   (SELECT COUNT(*) FROM trabajos_mantenimiento tm WHERE tm.planta_id = p.id) as total_mantenimientos,
                   (SELECT MAX(fecha) FROM trabajos_mantenimiento tm WHERE tm.planta_id = p.id) as ultima_fecha_mantenimiento
            FROM plantas p
            JOIN sedes s ON p.sede_id = s.id
            ORDER BY p.sede_id ASC, p.id ASC
        """)
        return [dict(r) for r in cursor.fetchall()]

def get_planta_by_id(planta_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, s.nombre as sede_nombre, s.codigo as sede_codigo, s.direccion as sede_direccion,
                   s.contacto_nombre as sede_contacto, s.contacto_telefono as sede_telefono
            FROM plantas p
            JOIN sedes s ON p.sede_id = s.id
            WHERE p.id = ?
        """, (planta_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_planta(data: dict) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        fields = [
            "sede_id", "codigo", "nombre", "ensambladora", "capacidad_kva", "capacidad_kw",
            "ubicacion_interna", "horas_operacion", "estado", "prioridad",
            "motor_marca", "motor_modelo", "motor_serial", "motor_cilindros", "motor_aspiracion",
            "motor_potencia_hp", "motor_tipo_combustible", "motor_gobernador",
            "motor_capacidad_aceite", "motor_viscosidad_aceite", "motor_capacidad_refrigerante",
            "motor_tipo_refrigerante", "motor_filtro_aceite", "motor_filtro_combustible_primario",
            "motor_filtro_combustible_secundario", "motor_filtro_aire", "motor_filtro_agua_refrigerante",
            "motor_sistema_electrico_dc", "motor_baterias", "motor_notas",
            "generador_marca", "generador_modelo", "generador_serial", "generador_kva", "generador_kw",
            "generador_voltaje", "generador_frecuencia", "generador_rpm", "generador_fases",
            "generador_factor_potencia", "generador_amperaje_nominal", "generador_modelo_avr",
            "generador_tipo_excitacion", "generador_clase_aislamiento", "generador_notas",
            "controlador_marca", "controlador_modelo", "controlador_firmware", "controlador_modo",
            "controlador_umbral_baja_presion_aceite", "controlador_umbral_alta_temperatura",
            "controlador_umbral_sobrevelocidad", "controlador_umbral_subvoltaje", "controlador_umbral_sobrevoltaje",
            "controlador_pick_up_dientes", "controlador_config_io", "controlador_notas",
            "plan_mantenimiento_texto", "proximo_mantenimiento_horas", "proximo_mantenimiento_tipo",
            "manual_pdf_filename"
        ]
        values = [data.get(f) for f in fields]
        placeholders = ", ".join(["?"] * len(fields))
        cols = ", ".join(fields)
        cursor.execute(f"INSERT INTO plantas ({cols}) VALUES ({placeholders})", values)
        conn.commit()
        return cursor.lastrowid

def update_planta(planta_id: int, data: dict):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        allowed_keys = [
            "codigo", "nombre", "ensambladora", "capacidad_kva", "capacidad_kw",
            "ubicacion_interna", "horas_operacion", "estado", "prioridad",
            "motor_marca", "motor_modelo", "motor_serial", "motor_cilindros", "motor_aspiracion",
            "motor_potencia_hp", "motor_tipo_combustible", "motor_gobernador",
            "motor_capacidad_aceite", "motor_viscosidad_aceite", "motor_capacidad_refrigerante",
            "motor_tipo_refrigerante", "motor_filtro_aceite", "motor_filtro_combustible_primario",
            "motor_filtro_combustible_secundario", "motor_filtro_aire", "motor_filtro_agua_refrigerante",
            "motor_sistema_electrico_dc", "motor_baterias", "motor_notas",
            "generador_marca", "generador_modelo", "generador_serial", "generador_kva", "generador_kw",
            "generador_voltaje", "generador_frecuencia", "generador_rpm", "generador_fases",
            "generador_factor_potencia", "generador_amperaje_nominal", "generador_modelo_avr",
            "generador_tipo_excitacion", "generador_clase_aislamiento", "generador_notas",
            "controlador_marca", "controlador_modelo", "controlador_firmware", "controlador_modo",
            "controlador_umbral_baja_presion_aceite", "controlador_umbral_alta_temperatura",
            "controlador_umbral_sobrevelocidad", "controlador_umbral_subvoltaje", "controlador_umbral_sobrevoltaje",
            "controlador_pick_up_dientes", "controlador_config_io", "controlador_notas",
            "plan_mantenimiento_texto", "proximo_mantenimiento_horas", "proximo_mantenimiento_tipo",
            "manual_pdf_filename"
        ]
        updates = []
        vals = []
        for k in allowed_keys:
            if k in data:
                updates.append(f"{k} = ?")
                vals.append(data[k])
        if not updates:
            return
        vals.append(planta_id)
        cursor.execute(f"UPDATE plantas SET {', '.join(updates)} WHERE id = ?", vals)
        conn.commit()

def delete_planta(planta_id: int) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trabajos_mantenimiento WHERE planta_id = ?", (planta_id,))
        cursor.execute("DELETE FROM plantas WHERE id = ?", (planta_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_trabajos_by_planta(planta_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM trabajos_mantenimiento
            WHERE planta_id = ?
            ORDER BY fecha DESC, id DESC
        """, (planta_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["fotos"] = json.loads(d.get("fotos_json") or "[]")
            except Exception:
                d["fotos"] = []
            result.append(d)
        return result

def create_trabajo(data: dict) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        fotos = data.get("fotos", [])
        if isinstance(fotos, list):
            fotos_json = json.dumps(fotos)
        else:
            fotos_json = "[]"

        cursor.execute("""
            INSERT INTO trabajos_mantenimiento (
                planta_id, fecha, tipo_trabajo, horas_horometro, tecnico,
                titulo, descripcion, repuestos_utilizados, observaciones, fotos_json,
                costo_proyectado, costo_real, categoria_falla, estado_servicio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("planta_id"),
            data.get("fecha") or datetime.now().strftime("%Y-%m-%d"),
            data.get("tipo_trabajo", "Mantenimiento Preventivo"),
            float(data.get("horas_horometro", 0.0) or 0.0),
            data.get("tecnico", "Personal Técnico"),
            data.get("titulo", "Servicio Técnico"),
            data.get("descripcion", ""),
            data.get("repuestos_utilizados", ""),
            data.get("observaciones", ""),
            fotos_json,
            float(data.get("costo_proyectado", 0.0) or 0.0),
            float(data.get("costo_real", 0.0) or 0.0),
            data.get("categoria_falla", "Lubricación y Filtros"),
            data.get("estado_servicio", "Completado")
        ))
        trabajo_id = cursor.lastrowid

        # Si el horómetro registrado en el trabajo es mayor, actualizar el horómetro de la planta
        horas = data.get("horas_horometro")
        if horas and float(horas) > 0:
            cursor.execute("""
                UPDATE plantas 
                SET horas_operacion = MAX(horas_operacion, ?) 
                WHERE id = ?
            """, (float(horas), data.get("planta_id")))

        conn.commit()
        return trabajo_id

def get_all_manuals():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM manuales_meta ORDER BY id ASC")
        return [dict(r) for r in cursor.fetchall()]

def get_system_stats():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM sedes")
        total_sedes = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count, COALESCE(SUM(capacidad_kva), 0) as kva FROM plantas")
        p_row = cursor.fetchone()
        total_plantas = p_row["count"]
        total_kva = p_row["kva"]

        cursor.execute("SELECT COUNT(*) as count FROM plantas WHERE estado = 'Operativa'")
        operativas = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM trabajos_mantenimiento")
        total_trabajos = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM field_cases")
        total_casos = cursor.fetchone()["count"]

        return {
            "total_sedes": total_sedes,
            "total_plantas": total_plantas,
            "total_kva": total_kva,
            "operativas": operativas,
            "en_alerta": total_plantas - operativas,
            "total_trabajos": total_trabajos,
            "total_casos": total_casos
        }

def get_dashboard_analytics(year=None, month=None, sede_id=None, tipo_trabajo=None, categoria=None):
    """
    Retorna métricas ejecutivas estilo Power BI para el Dashboard Principal:
    KPIs consolidados, evolución mensual proyectado vs real, ranking de sedes con más fallas,
    distribución por subsistema y detalle tabular interactivo con variaciones.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Años disponibles
        cursor.execute("SELECT DISTINCT CAST(strftime('%Y', fecha) AS INTEGER) as y FROM trabajos_mantenimiento WHERE fecha IS NOT NULL ORDER BY y DESC")
        available_years = [r["y"] for r in cursor.fetchall() if r["y"]]
        if not available_years:
            available_years = [2026]

        cursor.execute("SELECT id, codigo, nombre, icono FROM sedes ORDER BY id ASC")
        available_sedes = [dict(r) for r in cursor.fetchall()]

        available_tipos = [
            "Todos",
            "Mantenimiento Preventivo",
            "Mantenimiento Correctivo",
            "Calibración y Pruebas"
        ]

        available_categorias = [
            "Todas",
            "Lubricación y Filtros",
            "Sistema de Combustible",
            "Sistema Eléctrico / AVR",
            "Baterías y Arranque",
            "Refrigeración / Temperatura",
            "Controlador y Sensores DSE"
        ]

        months_names = [
            {"num": 1, "short": "Ene", "name": "Enero"},
            {"num": 2, "short": "Feb", "name": "Febrero"},
            {"num": 3, "short": "Mar", "name": "Marzo"},
            {"num": 4, "short": "Abr", "name": "Abril"},
            {"num": 5, "short": "May", "name": "Mayo"},
            {"num": 6, "short": "Jun", "name": "Junio"},
            {"num": 7, "short": "Jul", "name": "Julio"},
            {"num": 8, "short": "Ago", "name": "Agosto"},
            {"num": 9, "short": "Sep", "name": "Septiembre"},
            {"num": 10, "short": "Oct", "name": "Octubre"},
            {"num": 11, "short": "Nov", "name": "Noviembre"},
            {"num": 12, "short": "Dic", "name": "Diciembre"}
        ]

        # Año objetivo: por defecto el más reciente (2026) si no se especifica
        target_year = int(year) if year else 2026

        # Construir filtros para la consulta detallada
        where_clauses = ["strftime('%Y', t.fecha) = ?"]
        params = [str(target_year)]

        if month is not None and int(month) > 0:
            where_clauses.append("CAST(strftime('%m', t.fecha) AS INTEGER) = ?")
            params.append(int(month))

        if sede_id is not None and int(sede_id) > 0:
            where_clauses.append("p.sede_id = ?")
            params.append(int(sede_id))

        if tipo_trabajo and tipo_trabajo != "Todos":
            where_clauses.append("t.tipo_trabajo LIKE ?")
            params.append(f"%{tipo_trabajo}%")

        if categoria and categoria != "Todas":
            where_clauses.append("t.categoria_falla = ?")
            params.append(categoria)

        where_sql = " AND ".join(where_clauses)

        query_jobs = f"""
            SELECT 
                t.*,
                p.codigo as planta_codigo,
                p.nombre as planta_nombre,
                p.capacidad_kva as planta_kva,
                p.estado as planta_estado,
                s.id as sede_id,
                s.codigo as sede_codigo,
                s.nombre as sede_nombre,
                s.icono as sede_icono
            FROM trabajos_mantenimiento t
            JOIN plantas p ON p.id = t.planta_id
            JOIN sedes s ON s.id = p.sede_id
            WHERE {where_sql}
            ORDER BY t.fecha DESC, t.id DESC
        """
        cursor.execute(query_jobs, params)
        matched_jobs = []
        for r in cursor.fetchall():
            item = dict(r)
            c_proy = float(item.get("costo_proyectado") or 0.0)
            c_real = float(item.get("costo_real") or 0.0)
            diff = c_proy - c_real
            item["diferencia"] = round(diff, 2)
            item["variacion_pct"] = round((diff / c_proy * 100), 1) if c_proy > 0 else 0.0
            try:
                item["fotos"] = json.loads(item.get("fotos_json") or "[]")
            except Exception:
                item["fotos"] = []
            matched_jobs.append(item)

        # Flota general
        if sede_id and int(sede_id) > 0:
            cursor.execute("SELECT COUNT(*) as cnt, SUM(capacidad_kva) as kva FROM plantas WHERE sede_id = ?", (int(sede_id),))
            p_row = cursor.fetchone()
            total_plantas = p_row["cnt"] or 0
            total_kva = p_row["kva"] or 0
            cursor.execute("SELECT COUNT(*) as cnt FROM plantas WHERE sede_id = ? AND estado = 'Operativa'", (int(sede_id),))
            plantas_operativas = cursor.fetchone()["cnt"] or 0
            total_sedes_active = 1
        else:
            cursor.execute("SELECT COUNT(*) as cnt FROM sedes")
            total_sedes_active = cursor.fetchone()["cnt"] or 0
            cursor.execute("SELECT COUNT(*) as cnt, SUM(capacidad_kva) as kva FROM plantas")
            p_row = cursor.fetchone()
            total_plantas = p_row["cnt"] or 0
            total_kva = p_row["kva"] or 0
            cursor.execute("SELECT COUNT(*) as cnt FROM plantas WHERE estado = 'Operativa'")
            plantas_operativas = cursor.fetchone()["cnt"] or 0

        disponibilidad_pct = round((plantas_operativas / total_plantas * 100), 1) if total_plantas > 0 else 100.0
        plantas_alerta = total_plantas - plantas_operativas

        # Totales calculados a partir de los trabajos filtrados
        total_servicios = len(matched_jobs)
        sum_proyectado = sum(float(j.get("costo_proyectado") or 0.0) for j in matched_jobs)
        sum_real = sum(float(j.get("costo_real") or 0.0) for j in matched_jobs)
        sum_diferencia = sum_proyectado - sum_real

        total_fallas = sum(1 for j in matched_jobs if "Correctivo" in (j.get("tipo_trabajo") or "") or "Falla" in (j.get("tipo_trabajo") or "") or "Falla" in (j.get("titulo") or ""))
        total_preventivos = total_servicios - total_fallas

        kpis = {
            "total_sedes": total_sedes_active,
            "total_plantas": total_plantas,
            "total_kva": round(total_kva, 1),
            "total_servicios": total_servicios,
            "total_fallas": total_fallas,
            "total_preventivos": total_preventivos,
            "costo_proyectado": round(sum_proyectado, 2),
            "costo_real": round(sum_real, 2),
            "diferencia": round(sum_diferencia, 2),
            "variacion_pct": round((sum_diferencia / sum_proyectado * 100), 1) if sum_proyectado > 0 else 0.0,
            "disponibilidad_pct": disponibilidad_pct,
            "plantas_operativas": plantas_operativas,
            "plantas_alerta": plantas_alerta
        }

        # Tendencia Mensual (12 Meses)
        trend_clauses = ["strftime('%Y', t.fecha) = ?"]
        trend_params = [str(target_year)]
        if sede_id and int(sede_id) > 0:
            trend_clauses.append("p.sede_id = ?")
            trend_params.append(int(sede_id))
        if tipo_trabajo and tipo_trabajo != "Todos":
            trend_clauses.append("t.tipo_trabajo LIKE ?")
            trend_params.append(f"%{tipo_trabajo}%")
        if categoria and categoria != "Todas":
            trend_clauses.append("t.categoria_falla = ?")
            trend_params.append(categoria)

        trend_where = " AND ".join(trend_clauses)
        trend_query = f"""
            SELECT 
                CAST(strftime('%m', t.fecha) AS INTEGER) as mes,
                COUNT(*) as servicios,
                COALESCE(SUM(t.costo_proyectado), 0) as costo_proyectado,
                COALESCE(SUM(t.costo_real), 0) as costo_real,
                SUM(CASE WHEN t.tipo_trabajo LIKE '%Correctivo%' OR t.tipo_trabajo LIKE '%Falla%' OR t.titulo LIKE '%Falla%' THEN 1 ELSE 0 END) as fallas
            FROM trabajos_mantenimiento t
            JOIN plantas p ON p.id = t.planta_id
            WHERE {trend_where}
            GROUP BY mes
            ORDER BY mes ASC
        """
        cursor.execute(trend_query, trend_params)
        trend_by_month = {r["mes"]: dict(r) for r in cursor.fetchall()}

        trend_monthly = []
        for m in months_names:
            num = m["num"]
            data_m = trend_by_month.get(num, {"servicios": 0, "costo_proyectado": 0.0, "costo_real": 0.0, "fallas": 0})
            c_proy = float(data_m.get("costo_proyectado") or 0.0)
            c_real = float(data_m.get("costo_real") or 0.0)
            trend_monthly.append({
                "mes": num,
                "short": m["short"],
                "name": m["name"],
                "servicios": data_m.get("servicios", 0),
                "fallas": data_m.get("fallas", 0),
                "preventivos": data_m.get("servicios", 0) - data_m.get("fallas", 0),
                "costo_proyectado": round(c_proy, 2),
                "costo_real": round(c_real, 2),
                "diferencia": round(c_proy - c_real, 2),
                "is_selected": (month == num)
            })

        # Ranking de Sedes del SENIAT con más intervenciones y fallas
        sedes_breakdown = []
        for s in available_sedes:
            s_jobs = [j for j in matched_jobs if j["sede_id"] == s["id"]]
            s_fallas = sum(1 for j in s_jobs if "Correctivo" in (j.get("tipo_trabajo") or "") or "Falla" in (j.get("tipo_trabajo") or "") or "Falla" in (j.get("titulo") or ""))
            s_real = sum(float(j.get("costo_real") or 0.0) for j in s_jobs)
            s_proy = sum(float(j.get("costo_proyectado") or 0.0) for j in s_jobs)
            sedes_breakdown.append({
                "sede_id": s["id"],
                "codigo": s["codigo"],
                "nombre": s["nombre"],
                "icono": s.get("icono", "🏢"),
                "total_servicios": len(s_jobs),
                "total_fallas": s_fallas,
                "total_preventivos": len(s_jobs) - s_fallas,
                "costo_real": round(s_real, 2),
                "costo_proyectado": round(s_proy, 2),
                "diferencia": round(s_proy - s_real, 2)
            })
        sedes_breakdown.sort(key=lambda x: (x["total_servicios"], x["total_fallas"]), reverse=True)

        # Distribución de fallas por categoría / subsistema
        cat_counts = {c: {"count": 0, "costo": 0.0} for c in available_categorias if c != "Todas"}
        for j in matched_jobs:
            c = j.get("categoria_falla") or "Lubricación y Filtros"
            if c not in cat_counts:
                cat_counts[c] = {"count": 0, "costo": 0.0}
            cat_counts[c]["count"] += 1
            cat_counts[c]["costo"] += float(j.get("costo_real") or 0.0)

        fallas_por_categoria = []
        for cat_name, val in cat_counts.items():
            fallas_por_categoria.append({
                "categoria": cat_name,
                "cantidad": val["count"],
                "costo": round(val["costo"], 2),
                "porcentaje": round((val["count"] / total_servicios * 100), 1) if total_servicios > 0 else 0.0
            })
        fallas_por_categoria.sort(key=lambda x: x["cantidad"], reverse=True)

        return {
            "status": "success",
            "filter_applied": {
                "year": target_year,
                "month": int(month) if month else None,
                "sede_id": int(sede_id) if sede_id else None,
                "tipo_trabajo": tipo_trabajo or "Todos",
                "categoria": categoria or "Todas"
            },
            "available_years": available_years,
            "available_months": months_names,
            "available_sedes": available_sedes,
            "available_tipos": available_tipos,
            "available_categorias": available_categorias,
            "kpis": kpis,
            "trend_monthly": trend_monthly,
            "sedes_ranking": sedes_breakdown,
            "fallas_por_categoria": fallas_por_categoria,
            "servicios_detalle": matched_jobs
        }

def _ensure_rich_powerbi_data(conn):
    """
    Asegura que la base de datos contenga un ecosistema multi-sede completo del SENIAT
    y un historial distribuido en todos los meses de 2026 para alimentar el Dashboard estilo Power BI.
    """
    cursor = conn.cursor()

    # 1. Actualizar registros existentes para que tengan costos y categorías realistas
    cursor.execute("""
        UPDATE trabajos_mantenimiento 
        SET costo_proyectado = 2800.0, costo_real = 2450.0, categoria_falla = 'Lubricación y Filtros', estado_servicio = 'Completado' 
        WHERE id = 1 AND (costo_proyectado IS NULL OR costo_proyectado = 0.0)
    """)
    cursor.execute("""
        UPDATE trabajos_mantenimiento 
        SET costo_proyectado = 1900.0, costo_real = 1450.0, categoria_falla = 'Sistema Eléctrico / AVR', estado_servicio = 'Completado' 
        WHERE id = 2 AND (costo_proyectado IS NULL OR costo_proyectado = 0.0)
    """)
    cursor.execute("""
        UPDATE trabajos_mantenimiento 
        SET costo_proyectado = 1500.0, costo_real = 1100.0, categoria_falla = 'Controlador y Sensores DSE', estado_servicio = 'Completado' 
        WHERE id = 3 AND (costo_proyectado IS NULL OR costo_proyectado = 0.0)
    """)

    # 2. Sedes adicionales del SENIAT
    sedes_extra = [
        ("SENIAT-LG", "SENIAT - Aduana Principal Marítima de La Guaira", "La Guaira", "Av. Soublette, Puerto de La Guaira", "Ing. Roberto Silva", "+58 412-4455667", "Superintendente de Mantenimiento", "Sede estratégica marítima con alta exposición a salitre. Dos generadores dedicados a sistemas de rayos X y servidores fiscales.", "⚓"),
        ("SENIAT-PC", "SENIAT - Aduana Principal de Puerto Cabello", "Puerto Cabello", "Zona Portuaria, Muelle 12, Terminal Especializado", "Ing. Marcos Rivas", "+58 414-8899001", "Jefe de Operaciones Técnicas", "Sede aduanera de carga de mayor volumen del país. Respaldo continuo 24/7.", "🚢"),
        ("SENIAT-LR", "SENIAT - Gerencia Regional Tributos Internos Los Ruices", "Caracas", "Av. Francisco de Miranda, Edif. SENIAT Los Ruices", "Lic. Carmen Gómez", "+58 424-3322114", "Administradora de Sede", "Sede metropolitana de recaudación y fiscalización tributaria. Grupos en terraza y sótano.", "🏛️")
    ]

    for cod, nom, ciu, dir_, c_nom, c_tel, c_car, nots, ico in sedes_extra:
        cursor.execute("SELECT id FROM sedes WHERE codigo = ?", (cod,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO sedes (codigo, nombre, ciudad, direccion, contacto_nombre, contacto_telefono, contacto_cargo, notas, icono)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cod, nom, ciu, dir_, c_nom, c_tel, c_car, nots, ico))

    conn.commit()

    # Mapeo de IDs de sedes
    cursor.execute("SELECT id, codigo FROM sedes")
    sede_map = {r["codigo"]: r["id"] for r in cursor.fetchall()}

    # 3. Plantas para las sedes nuevas
    plantas_extra = [
        # La Guaira
        ("SENIAT-LG", "GEN-LG-01", "Planta Principal Cummins KTA19 600 kVA - Aduana La Guaira", "Cummins Power Generation", 600.0, 480.0, "Sala Técnica Marítima - Muelle 5", 1680.0, "Operativa", "Crítica",
         "Cummins", "KTA19-G4", "37184920", "6 cilindros en línea (18.9 L)", "Turboalimentado", 680.0, "Diésel #2", "Electrónico", "38 Litros", "15W-40 CI-4", "45 Litros", "50/50 ELC", "LF9009", "FS1000", "FF5612", "AF25544", "WF2071", "24V DC", "2x 12V 1100 CCA", "Tropicalizada ambiente salino",
         "Stamford", "HCI534E", "0245678", 600.0, 480.0, "208/120V Trifásico", "60 Hz", 1800, "Trifásico (4 Hilos)", 0.8, 1665.0, "AS440", "Brushless", "Clase H / IP23", "Resistencia de caldeo",
         "Deep Sea Electronics", "DSE 7320 MKII", "v3.2", "Auto", "18 PSI", "102 °C", "2070 RPM", "180 V", "240 V", "126 dientes", "Control de transferencias ATS", "En red"),
        
        ("SENIAT-LG", "GEN-LG-02", "Planta Respaldo Caterpillar 3406C 350 kVA - Aduana La Guaira", "Caterpillar Inc.", 350.0, 280.0, "Patio de Rayos X y Contenedores", 2150.0, "En Mantenimiento", "Alta",
         "Caterpillar", "3406C DITA", "4CK02914", "6 en línea (14.6 L)", "Turbo posenfriado", 420.0, "Diésel #2", "Gobernador Mecánico Hydra-Mechanical", "34 Litros", "Cat DEO 15W-40", "40 Litros", "Cat ELC", "1R-1808", "1R-0770", "1R-0749", "110-6326", "N/A", "24V DC", "2x Cat 1400 CCA", "En servicio de reemplazo de mangueras",
         "Leroy Somer", "LSA 47.2", "LS-9912", 350.0, 280.0, "208/120V Trifásico", "60 Hz", 1800, "Trifásico", 0.8, 971.0, "R450", "AREP", "Clase H", "Bobinado protegido contra corrosión marina",
         "ComAp", "InteliLite 4 AMF 25", "v1.4", "Manual", "20 PSI", "104 °C", "2070 RPM", "180 V", "240 V", "113 dientes", "Configurado para arranque por contacto seco", "Inspección activa"),

        # Puerto Cabello
        ("SENIAT-PC", "GEN-PC-01", "Planta Perkins 2506C 500 kVA - Aduana Puerto Cabello", "FG Wilson", 500.0, 400.0, "Sala Eléctrica Subestación Central", 1840.0, "Operativa", "Crítica",
         "Perkins", "2506C-E15TAG2", "MGB150029", "6 en línea (15.0 L)", "Turbo y Postenfriado", 540.0, "Diésel #2", "ECM Perkins MEUI", "62 Litros", "15W-40 CI-4", "58 Litros", "Perkins Extended Life", "2654407", "26560201", "26561117", "26510342", "WF2075", "24V DC", "2x 12V 1000 CCA", "Operando en paralelo",
         "Leroy Somer", "TAL 0473", "LS-88412", 500.0, 400.0, "480/277V Trifásico", "60 Hz", 1800, "Trifásico 4 Hilos", 0.8, 601.0, "R250", "Shunt", "Clase H", "Tensión industrial",
         "Deep Sea Electronics", "DSE 7320", "v2.8", "Auto", "18 PSI", "102 °C", "2070 RPM", "415 V", "520 V", "136 dientes", "Vinculado a interruptor Abb Emax", "Excelente estado"),

        ("SENIAT-PC", "GEN-PC-02", "Planta FG Wilson P400P5 400 kVA - Terminal Contenedores", "FG Wilson", 400.0, 320.0, "Patio Operativo Grúas Pórtico", 1220.0, "Operativa", "Alta",
         "Perkins", "2206A-E13TAG3", "TGB130044", "6 en línea (12.5 L)", "Turboalimentado", 440.0, "Diésel #2", "Electrónico", "40 Litros", "15W-40", "42 Litros", "50/50 Glicol", "2654403", "26560143", "26560145", "26510214", "N/A", "24V DC", "2x 12V 950 CCA", "Caseta insonorizada IP55",
         "Leroy Somer", "LL5014J", "LS-73192", 400.0, 320.0, "480/277V Trifásico", "60 Hz", 1800, "Trifásico", 0.8, 481.0, "R438", "PMG", "Clase H", "Excitatriz PMG",
         "PowerWizard", "PW 2.1", "v1.1", "Auto", "20 PSI", "103 °C", "2070 RPM", "415 V", "520 V", "126 dientes", "Protección por sobrecarga activa", "En línea"),

        # Los Ruices
        ("SENIAT-LR", "GEN-LR-01", "Planta Kohler 250REOZJE 250 kVA - Sede Los Ruices", "Kohler Power Systems", 250.0, 200.0, "Terraza Nivel 4 - Caseta Acústica", 890.0, "Operativa", "Media",
         "John Deere", "6090HF484", "RG6090L01928", "6 en línea (9.0 L)", "Turbocharged Charge Air Cooled", 315.0, "Diésel #2", "John Deere JDEC", "32 Litros", "John Deere Plus-50 II 15W-40", "36 Litros", "Cool-Gard II", "RE509672", "RE529643", "RE522878", "RE516335", "N/A", "12V DC", "1x 12V 1000 CCA", "Operativa para cargas administrativas",
         "Kohler", "4UA13", "K-83729", 250.0, 200.0, "208/120V Trifásico", "60 Hz", 1800, "Trifásico", 0.8, 694.0, "Decision-Maker 3000", "Digital", "Clase H", "Aislamiento superior",
         "Kohler", "Decision-Maker 3000", "v2.0", "Auto", "18 PSI", "102 °C", "2070 RPM", "180 V", "240 V", "129 dientes", "Comando a ATS Kohler MPAC", "Operativa"),

        ("SENIAT-LR", "GEN-LR-02", "Planta Doosan DP158LC 500 kVA - Respaldo Servidores Los Ruices", "Doosan Infracore", 500.0, 400.0, "Sótano 1 - Sala de Transferencia", 1450.0, "Alerta", "Alta",
         "Doosan", "DP158LC", "DP158019482", "V8 Cilindros (14.6 L)", "Twin Turbo y Enfriador Aire-Aire", 530.0, "Diésel #2", "Bosch In-line Governor", "35 Litros", "15W-40 CI-4", "48 Litros", "50/50 Etilenglicol", "65.05510-5020", "65.12503-5011", "65.12503-5016", "474-00040", "N/A", "24V DC", "2x 12V 1000 CCA", "Alerta leve por desgaste en diodos de excitatriz",
         "Stamford", "HCI534C", "0294820", 500.0, 400.0, "208/120V Trifásico", "60 Hz", 1800, "Trifásico", 0.8, 1388.0, "AS440", "Brushless", "Clase H", "Requiere calibración de voltaje",
         "Deep Sea Electronics", "DSE 7420", "v1.5", "Auto", "18 PSI", "102 °C", "2070 RPM", "180 V", "240 V", "160 dientes", "Registro de fluctuación de voltaje reciente", "Revisión técnica programada")
    ]

    for p in plantas_extra:
        sede_cod = p[0]
        p_cod = p[1]
        sede_id = sede_map.get(sede_cod)
        if not sede_id:
            continue
        cursor.execute("SELECT id FROM plantas WHERE codigo = ?", (p_cod,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO plantas (
                    sede_id, codigo, nombre, ensambladora, capacidad_kva, capacidad_kw,
                    ubicacion_interna, horas_operacion, estado, prioridad,
                    motor_marca, motor_modelo, motor_serial, motor_cilindros, motor_aspiracion,
                    motor_potencia_hp, motor_tipo_combustible, motor_gobernador,
                    motor_capacidad_aceite, motor_viscosidad_aceite, motor_capacidad_refrigerante,
                    motor_tipo_refrigerante, motor_filtro_aceite, motor_filtro_combustible_primario,
                    motor_filtro_combustible_secundario, motor_filtro_aire, motor_filtro_agua_refrigerante,
                    motor_sistema_electrico_dc, motor_baterias, motor_notas,
                    generador_marca, generador_modelo, generador_serial, generador_kva, generador_kw,
                    generador_voltaje, generador_frecuencia, generador_rpm, generador_fases,
                    generador_factor_potencia, generador_amperaje_nominal, generador_modelo_avr,
                    generador_tipo_excitacion, generador_clase_aislamiento, generador_notas,
                    controlador_marca, controlador_modelo, controlador_firmware, controlador_modo,
                    controlador_umbral_baja_presion_aceite, controlador_umbral_alta_temperatura,
                    controlador_umbral_sobrevelocidad, controlador_umbral_subvoltaje, controlador_umbral_sobrevoltaje,
                    controlador_pick_up_dientes, controlador_config_io, controlador_notas,
                    plan_mantenimiento_texto, proximo_mantenimiento_horas, proximo_mantenimiento_tipo, manual_pdf_filename
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?
                )
            """, (
                sede_id, p_cod, p[2], p[3], p[4], p[5],
                p[6], p[7], p[8], p[9],
                p[10], p[11], p[12], p[13], p[14],
                p[15], p[16], p[17],
                p[18], p[19], p[20],
                p[21], p[22], p[23],
                p[24], p[25], p[26],
                p[27], p[28], p[29],
                p[30], p[31], p[32], p[33], p[34],
                p[35], p[36], p[37], p[38],
                p[39], p[40], p[41],
                p[42], p[43], p[44],
                p[45], p[46], p[47], p[48],
                p[49], p[50],
                p[51], p[52], p[53],
                p[54], p[55], p[56],
                "📋 PLAN DE MANTENIMIENTO PREVENTIVO OEM:\n• Cada 250h: Aceite y filtros.\n• Cada 500h: Filtros de aire y refrigerante.\n• Anual: Calibración y megado.",
                p[7] + 250.0, "Mantenimiento Preventivo A", "Manual Definitivo de Generadores Diésel.pdf"
            ))

    conn.commit()

    # Mapeo de IDs de plantas
    cursor.execute("SELECT id, codigo FROM plantas")
    plantas_map = {r["codigo"]: r["id"] for r in cursor.fetchall()}

    # 4. Sembrar historial de trabajos enriquecido 2026 (si hay menos de 15 trabajos)
    cursor.execute("SELECT COUNT(*) as cnt FROM trabajos_mantenimiento")
    if cursor.fetchone()["cnt"] < 15:
        historical_jobs = [
            # ENERO 2026
            ("GEN-TC-01", "2026-01-10", "Mantenimiento Preventivo A (250h)", 1250.0, "Gabriel F.",
             "Mantenimiento Preventivo 250h: Filtros Fleetguard y Aceite 15W-40",
             "Drenado de cárter en caliente, sustitución de filtro de aceite LF9009, separador FS1000 y secundario FF5612. Purga y cebado de riel común. Ajuste de correas.",
             "Filtros LF9009, FS1000, FF5612, 28L Mobil Delvac 15W-40", "Parámetros normales: 46 PSI, 82°C en prueba con carga.",
             2800.0, 2450.0, "Lubricación y Filtros", "Completado"),

            ("GEN-LG-02", "2026-01-18", "Mantenimiento Correctivo / Falla", 2010.0, "Ing. R. Silva",
             "Atención de Falla: Falla de Arranque por Sulfatación Severa en Bornes",
             "El grupo no logró marcha durante corte de Corpoelec en muelle. Se encontró sulfatación extrema en bornes de baterías de 24V con caída a 14V al dar marcha. Limpieza con bicarbonato, cambio de terminales de cobre y reapriete.",
             "4x Terminales de compresión 2/0 AWG, grasa dieléctrica para bornes", "Se programó sustitución de cargador de flote auxiliar.",
             1200.0, 980.0, "Baterías y Arranque", "Completado"),

            ("GEN-BK-01", "2026-01-27", "Mantenimiento Preventivo Semestral", 580.0, "Personal Técnico IG",
             "Servicio Semestral Programado y Prueba ATS Centro de Datos",
             "Inspección de 50 puntos según checklist OEM Cummins QST30. Análisis espectrométrico de aceite SOS y prueba de conmutación en tablero de transferencia ASCO 7000 en 1.8 segundos.",
             "Kits de filtros Fleetguard LF9000, FS1006, FF5488, grasa de acople", "Generador principal en óptimo estado de disponibilidad.",
             6500.0, 5800.0, "Lubricación y Filtros", "Completado"),

            # FEBRERO 2026
            ("GEN-PC-01", "2026-02-05", "Mantenimiento Correctivo / Falla", 1720.0, "Ing. M. Rivas",
             "Atención a Falla: Saturación por Condensación y Agua en Filtro Separador",
             "Alarma de pérdida de potencia bajo carga alta en Aduana Puerto Cabello. Se detectó agua acumulada y sedimentos en tazón de filtro racor 26560201. Purga de fondo de tanque diario y reemplazo de cartuchos.",
             "2x Filtros Perkins 26560201, 1x Aditivo biocida para diésel marino", "Se recomendó purga semanal obligatoria por alta humedad en zona de muelles.",
             1800.0, 1450.0, "Sistema de Combustible", "Completado"),

            ("GEN-TC-02", "2026-02-14", "Calibración y Pruebas Eléctricas", 920.0, "Gabriel F.",
             "Calibración de Gobernador Electrónico y Regulación de Frecuencia 60 Hz",
             "Desviación de velocidad (62.5 Hz en vacío y caída a 57.8 Hz con carga). Con herramienta Cat ET se recalibró la ganancia proporcional de ECM ADEM A4 y estabilidad de gobernador.",
             "Software Cat ET, limpieza de arnés de control", "Frecuencia regulada a 60.0 Hz ±0.2% en todo el rango de potencia.",
             1500.0, 1150.0, "Sistema Eléctrico / AVR", "Completado"),

            ("GEN-MC-01", "2026-02-22", "Mantenimiento Preventivo B (500h)", 840.0, "Personal Técnico IG",
             "Servicio 500 Horas: Reemplazo Integral de Fluidos y Filtro de Aire",
             "Cambio de 27L de aceite motor 15W-40, filtro Perkins 2654407, elemento de aire 26510342 y refrigerante Perkins Extended Life. Desengrase de motor y soplado de radiador.",
             "Aceite 15W-40 CI-4, filtro aire 26510342, 30L refrigerante 50/50", "Planta lista para temporada de alta demanda fiscal.",
             3200.0, 2750.0, "Lubricación y Filtros", "Completado"),

            # MARZO 2026
            ("GEN-LR-02", "2026-03-08", "Mantenimiento Correctivo / Falla", 1380.0, "Lic. C. Gómez",
             "Atención de Emergencia: Alarma de Alta Temperatura por Fisura en Manguera",
             "Parada de emergencia en Doosan 500 kVA durante racionamiento eléctrico. Se detectó rotura en manguera superior de radiador con fuga de refrigerante y disparo a 104°C. Reemplazo inmediato de manguera de silicona y purga de aire.",
             "1x Manguera de silicona alta temperatura 3 pulgadas, 40L refrigerante 50/50", "Sobrecosto por adquisición urgente fuera de horario.",
             2100.0, 2350.0, "Refrigeración / Temperatura", "Completado"),

            ("GEN-LG-01", "2026-03-15", "Mantenimiento Preventivo A", 1550.0, "Ing. R. Silva",
             "Mantenimiento Programado y Lavado Químico Anti-Salitre de Panal",
             "Mantenimiento regular 250h en Cummins KTA19. Lavado de radiador con compuesto desincrustante biodegradable para remover depósito salino costero. Verificación de terminales Stamford.",
             "Filtros LF9009, FS1000, químico desengrasante marítimo", "Radiador con 100% de flujo de aire restituido.",
             3400.0, 2890.0, "Lubricación y Filtros", "Completado"),

            ("GEN-BK-01", "2026-03-24", "Mantenimiento Preventivo", 610.0, "Gabriel F.",
             "Sustitución de Empacaduras de Tapa de Válvulas y Torques OEM",
             "Se atendió leve rezume de aceite sobre el múltiple de escape de bancada izquierda en motor QST30. Reemplazo de empacaduras de elastómero y apriete con torquímetro.",
             "2x Empacaduras Cummins OEM de tapa de válvulas", "Motor sellado y completamente limpio sin rezumes.",
             1600.0, 1250.0, "Lubricación y Filtros", "Completado"),

            # ABRIL 2026
            ("GEN-TC-01", "2026-04-04", "Mantenimiento Correctivo / Falla", 1310.0, "Personal Técnico IG",
             "Falla de Lectura de RPM y Sustitución de Sensor Magnético MPU",
             "Alarma en DSE 7320: 'Loss of MPU signal'. El motor arrancaba pero cortaba por sobrevelocidad falsa. Se retiró sensor pick-up en corona dentada, encontrándose virutas metálicas en la punta magnética. Sustitución y calibración a 1/2 vuelta.",
             "1x Sensor MPU 5/8-18 UNF magnético Deep Sea", "Lectura de RPM exacta y lectura en controlador verificada.",
             950.0, 780.0, "Controlador y Sensores DSE", "Completado"),

            ("GEN-PC-02", "2026-04-16", "Mantenimiento Preventivo A", 1150.0, "Ing. M. Rivas",
             "Servicio Preventivo 250h en FG Wilson P400P5",
             "Reemplazo de tren de filtración Perkins y aceite motor. Inspección de caja de conexiones de alternador Leroy Somer.",
             "Filtros 2654403, 26560143, 26560145, 38L lubricante 15W-40", "Equipo trabajando sin novedades al 70% de carga.",
             2600.0, 2200.0, "Lubricación y Filtros", "Completado"),

            ("GEN-BK-01", "2026-04-29", "Mantenimiento Preventivo Especial", 640.0, "Gabriel F.",
             "Reemplazo Preventivo de Banco de Baterías de Arranque 24V",
             "Cumplimiento de ciclo de vida de 2 años en banco de baterías del centro de datos. Instalación de 4 unidades selladas 12V 1300 CCA de ciclado profundo en esquema serie-paralelo.",
             "4x Baterías Heavy Duty 12V 1300 CCA, cables puente 4/0 AWG", "Prueba de arranque en frío bajo 2.1 segundos.",
             4200.0, 3900.0, "Baterías y Arranque", "Completado"),

            # MAYO 2026
            ("GEN-LG-02", "2026-05-11", "Mantenimiento Correctivo / Falla", 2080.0, "Ing. R. Silva",
             "Falla de Regulación de Voltaje por Falla en Tarjeta Reguladora AVR R450",
             "El grupo presentaba sobretensión intermitente (245 VAC fase-neutro) provocando disparo del interruptor. Se diagnosticó varistor quemado en tarjeta Leroy Somer R450. Instalación de nuevo AVR y calibración de LAM.",
             "1x Regulador de Voltaje Leroy Somer R450 original", "Voltaje estabilizado en 208/120V.",
             1750.0, 1320.0, "Sistema Eléctrico / AVR", "Completado"),

            ("GEN-LR-01", "2026-05-20", "Mantenimiento Preventivo A", 780.0, "Lic. C. Gómez",
             "Mantenimiento 250h en Generador Kohler John Deere",
             "Servicio de cambio de aceite John Deere Plus-50 II y filtros de combustible. Verificación de pantalla Decision-Maker 3000.",
             "Filtros Donaldson / John Deere RE509672, RE529643, 30L aceite", "Presión en 50 PSI a 1800 RPM.",
             2400.0, 1980.0, "Lubricación y Filtros", "Completado"),

            ("GEN-TC-02", "2026-05-28", "Inspección y Pruebas Eléctricas", 960.0, "Gabriel F.",
             "Reapriete de Barras de Potencia y Limpieza con Dieléctrico",
             "Termografía infrarroja en breaker ABB motorizado y bornes de alternador TAL 0473. No se detectaron puntos calientes. Reapriete general de pernos.",
             "Spray dieléctrico CRC, precintos de seguridad", "Termografía dentro de rango permisible (<45°C).",
             1200.0, 950.0, "Sistema Eléctrico / AVR", "Completado"),

            # JUNIO 2026
            ("GEN-PC-01", "2026-06-03", "Mantenimiento Correctivo / Falla", 1780.0, "Ing. M. Rivas",
             "Atención a Falla: Fuga de Gasoil en Manguera de Retorno de Inyectores",
             "Detección de goteo de diésel sobre el colector de escape durante inspección visual rutinaria en Puerto Cabello. Sustitución preventiva de manguera de baja presión para prevenir riesgo de conflagración.",
             "Manguera Gates diésel 3/8 y abrazaderas de acero inoxidable", "Prueba de 30 minutos sin fugas.",
             800.0, 650.0, "Sistema de Combustible", "Completado"),

            ("GEN-TC-01", "2026-06-18", "Servicio Mayor Anual", 1370.0, "Gabriel F.",
             "Servicio Mayor Semestral: Calibración de Válvulas y Megado de Alternador",
             "Ajuste de luz de válvulas de admisión (0.30mm) y escape (0.58mm) en motor Cummins QSL9. Prueba de aislamiento con megóhmetro (55 Megaohmios en estator y rotor).",
             "Juntas de tapa balancines, filtros completos Fleetguard", "Respuesta motriz y eficiencia de combustión optimizadas.",
             5200.0, 4100.0, "Lubricación y Filtros", "Completado"),

            ("GEN-MC-01", "2026-06-27", "Mantenimiento Correctivo / Falla", 890.0, "Personal Técnico IG",
             "Falla en Solenoide de Parada de Combustible",
             "El grupo no se detenía tras pulsar botón de paro en controlador DSE. Desarme y reemplazo de solenoide de corte por bobina recalentada en Mata de Coco.",
             "1x Solenoide de combustible Woodward 24V DC", "Parada instantánea verificada.",
             1100.0, 920.0, "Sistema de Combustible", "Completado"),

            # JULIO 2026
            ("GEN-LG-01", "2026-07-09", "Mantenimiento Preventivo", 1620.0, "Ing. R. Silva",
             "Limpieza Profunda de Radiador y Lavado Químico Anti-Incrustante",
             "Remoción de suciedad acumulada por vientos marinos en Aduana La Guaira. Soplado inverso de panal y cambio de filtro de agua con pastilla inhibidora Fleetguard WF2071.",
             "1x Filtro químico WF2071, desengrasante cítrico industrial", "Temperatura de operación estabilizada en 84°C.",
             2900.0, 2450.0, "Refrigeración / Temperatura", "Completado"),

            ("GEN-BK-01", "2026-07-21", "Mantenimiento Correctivo / Falla", 690.0, "Personal Técnico IG",
             "Desincronismo en Módulo DSE 8620 con Red Corpoelec",
             "Alarma 'Phase angle error' durante retorno de red comercial. Se reconfiguraron los umbrales de sincronismo (ventana de ±5V, ±0.2 Hz) y se actualizó firmware.",
             "Cable USB de programación DSE-P810, licencia software DSE", "Transferencias suaves sin microcortes.",
             3500.0, 2800.0, "Controlador y Sensores DSE", "Completado"),

            ("GEN-LR-02", "2026-07-30", "Mantenimiento Preventivo", 1410.0, "Lic. C. Gómez",
             "Sustitución Preventiva de Termostato Motor Doosan",
             "Reemplazo preventivo de par de termostatos de 82°C para evitar fallas por fatiga térmica en sala de máquinas sótano.",
             "2x Termostatos Doosan OEM, juntas tóricas", "Apertura simétrica y temperatura uniforme en ambas culatas.",
             1400.0, 1150.0, "Refrigeración / Temperatura", "Completado"),

            # AGOSTO 2026
            ("GEN-TC-02", "2026-08-04", "Mantenimiento Correctivo / Falla", 1010.0, "Gabriel F.",
             "Sustitución de Calentador de Camisa de Bloque (Block Heater 2.5 kW)",
             "Detección de motor frío (22°C en reposo). Resistencia interna del calentador abierta por sarro. Se instaló nuevo calefactor con termostato incorporado a 45°C.",
             "1x Calentador Hotstart 2500W 208V con termostato", "Motor tibio garantizando arranque inmediato bajo carga.",
             1400.0, 1150.0, "Sistema Eléctrico / AVR", "Completado"),

            ("GEN-PC-02", "2026-08-16", "Mantenimiento Preventivo A", 1200.0, "Ing. M. Rivas",
             "Servicio 250h en FG Wilson Puerto Cabello",
             "Filtros de aceite y combustible Perkins. Ajuste de fajas de ventilador.",
             "Kits de filtros 2654403, 26560143, aceite 15W-40", "Equipo 100% operativo.",
             2800.0, 2300.0, "Lubricación y Filtros", "Completado"),

            ("GEN-LR-02", "2026-08-28", "Mantenimiento Correctivo / Falla", 1430.0, "Personal Técnico IG",
             "Alarma de Baja Presión de Aceite por Obstrucción Prematura de Filtros",
             "Disparo a 19 PSI en Doosan Los Ruices. Se comprobó que el lote de aceite anterior se degradó por hollín excesivo. Cambio inmediato de aceite de alta detergencia y doble filtro.",
             "2x Filtros de aceite Doosan, 35L lubricante Mobil Delvac CK-4", "Presión normalizada en 48 PSI en caliente.",
             1300.0, 1050.0, "Lubricación y Filtros", "Completado"),

            # SEPTIEMBRE 2026
            ("GEN-TC-01", "2026-09-08", "Mantenimiento Preventivo A (250h)", 1410.0, "Gabriel F.",
             "Mantenimiento Preventivo 250h Programado Cummins QSL9",
             "Mantenimiento regular de manual. Reemplazo de filtros Fleetguard LF9009, FS1000, FF5612 y aceite 15W-40. Limpieza de borne de carga auxiliar.",
             "Tren completo Fleetguard, 28L aceite Mobil Delvac", "Operativo 100%.",
             3100.0, 2600.0, "Lubricación y Filtros", "Completado"),

            ("GEN-LG-02", "2026-09-17", "Mantenimiento Correctivo / Falla", 2120.0, "Ing. R. Silva",
             "Purga de Entrada de Aire en Riel Común y Reemplazo de Bomba Manual",
             "El motor no lograba encendido tras permanecer 4 días en reposo. Se encontró fisura en membrana de cebador manual de combustible permitiendo entrada de aire. Sustitución de bomba de mano y purga de inyectores.",
             "1x Bomba de cebado manual Caterpillar 1375541", "Arranque en menos de 3 segundos verificado.",
             1450.0, 1200.0, "Sistema de Combustible", "Completado"),

            ("GEN-BK-01", "2026-09-29", "Calibración y Pruebas Eléctricas", 720.0, "Gabriel F.",
             "Calibración de Tarjeta Reguladora AVR MX321 y Excitación PMG",
             "Verificación de diodos giratorios en alternador Stamford HVSI804R del Centro de Datos. Calibración de estabilidad y factor de caída de voltaje droop para paralelismo.",
             "Diodos de repuesto SKN/SKR, aerosol dieléctrico", "Curva de voltaje estable a carga plena.",
             3800.0, 2950.0, "Sistema Eléctrico / AVR", "Completado"),

            # OCTUBRE 2026
            ("GEN-MC-01", "2026-10-06", "Mantenimiento Correctivo / Falla", 940.0, "Personal Técnico IG",
             "Sustitución de Manguera de Retorno de Enfriador de Aceite",
             "Atención de goteo en manguera hidráulica de enfriador en Mata de Coco. Instalación de manguera R6 con mallado textil resistente a temperatura.",
             "Manguera SAE 100 R6 1/2 pulgada y abrazaderas de torque constante", "Equipo listo para soporte operativo.",
             1250.0, 1100.0, "Refrigeración / Temperatura", "Completado"),

            ("GEN-LR-01", "2026-10-14", "Mantenimiento Preventivo A", 890.0, "Lic. C. Gómez",
             "Mantenimiento Preventivo A Kohler 250 kVA Sede Los Ruices",
             "Cambio de filtros y aceite. Comprobación de tensión en cargador de flote estático 12V 10A.",
             "Filtros John Deere, 30L aceite 15W-40", "Excelente respuesta dinámica.",
             2300.0, 1850.0, "Lubricación y Filtros", "Completado"),

            ("GEN-TC-01", "2026-10-20", "Calibración y Pruebas Especiales", 1430.0, "Gabriel F.",
             "Prueba con Banco de Carga Resistiva al 100% de Capacidad (400 kW)",
             "Prueba anual de descarbonización con banco resistivo externo durante 2 horas continuas al 100% de potencia nominal. Presión de aceite estable en 44 PSI, temperatura en 88°C, sin caída de frecuencia.",
             "Servicio de banco de carga y combustible diésel para la prueba", "Eliminación completa de depósitos de carbonilla en escape.",
             2700.0, 2150.0, "Sistema Eléctrico / AVR", "Completado")
        ]

        for h in historical_jobs:
            p_cod = h[0]
            planta_id = plantas_map.get(p_cod)
            if not planta_id:
                continue
            cursor.execute("""
                INSERT INTO trabajos_mantenimiento (
                    planta_id, fecha, tipo_trabajo, horas_horometro, tecnico,
                    titulo, descripcion, repuestos_utilizados, observaciones, fotos_json,
                    costo_proyectado, costo_real, categoria_falla, estado_servicio
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                planta_id, h[1], h[2], h[3], h[4],
                h[5], h[6], h[7], h[8], "[]",
                h[9], h[10], h[11], h[12]
            ))

        conn.commit()
        print("¡Historial multi-mes 2026 y sedes enriquecidas exitosamente para el Dashboard!")

if __name__ == "__main__":
    init_database()

