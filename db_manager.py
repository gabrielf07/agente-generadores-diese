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

        conn.commit()

        # Sembrar Sedes iniciales si está vacío
        cursor.execute("SELECT COUNT(*) as cnt FROM sedes")
        if cursor.fetchone()["cnt"] == 0:
            _seed_initial_data(conn)

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
                titulo, descripcion, repuestos_utilizados, observaciones, fotos_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("planta_id"),
            data.get("fecha") or datetime.now().strftime("%Y-%m-%d"),
            data.get("tipo_trabajo", "Mantenimiento Preventivo"),
            data.get("horas_horometro", 0.0),
            data.get("tecnico", "Personal Técnico"),
            data.get("titulo", "Servicio Técnico"),
            data.get("descripcion", ""),
            data.get("repuestos_utilizados", ""),
            data.get("observaciones", ""),
            fotos_json
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

if __name__ == "__main__":
    init_database()
