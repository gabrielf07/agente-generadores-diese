import sys
import json
import db_manager
import agent

# Asegurar codificación utf-8 para salida en Windows
sys.stdout.reconfigure(encoding='utf-8')

def run_tests():
    db_manager.init_database()
    plantas = db_manager.get_all_plantas()
    print(f"============================================================")
    print(f" INICIANDO BATERÍA DE PRUEBAS DEL AGENTE PARA CADA PLANTA")
    print(f" Total de plantas registradas a evaluar: {len(plantas)}")
    print(f"============================================================\n")

    results = []

    test_queries = {
        1: "¿Qué mantenimiento le corresponde según sus horas y qué filtros Fleetguard de aceite y combustible debo llevar?",
        2: "El motor presenta humo blanco en el arranque en frío. ¿Cuáles son las causas y qué filtros Cat 1R corresponden a este C15?",
        3: "¿Qué aceite, capacidad en litros y filtros Perkins requiere esta máquina para el servicio preventivo de 250h?",
        4: "¿Qué filtros Fleetguard LF y FS requiere este motor Cummins QST30 V12 y cuáles son las protecciones de su controlador DSE 8620?"
    }

    for idx, planta in enumerate(plantas, 1):
        p_id = planta["id"]
        p_nombre = planta["nombre"]
        p_motor = f"{planta.get('motor_marca', '')} {planta.get('motor_modelo', '')}".strip()
        p_gen = f"{planta.get('generador_marca', '')} {planta.get('generador_modelo', '')}".strip()
        p_ctrl = f"{planta.get('controlador_marca', '')} {planta.get('controlador_modelo', '')}".strip()
        
        query = test_queries.get(p_id, f"¿Qué especificaciones y mantenimiento requiere la planta {p_nombre}?")

        print(f"▶ [PRUEBA {idx}/{len(plantas)}] Planta #{p_id}: {p_nombre}")
        print(f"   Motor: {p_motor} | Gen: {p_gen} | Ctrl: {p_ctrl}")
        print(f"   Pregunta: '{query}'")
        
        try:
            res = agent.ask_agent(query=query, planta_id=p_id)
            resp_text = res.get("response", "")
            
            # Validaciones de calidad y contextualización
            has_response = len(resp_text) > 200
            has_plant_name = (planta.get("motor_marca", "").lower() in resp_text.lower()) or (planta.get("motor_modelo", "").lower() in resp_text.lower())
            has_checklist = "- [ ]" in resp_text or "CHECKLIST" in resp_text.upper()

            passed = has_response and has_plant_name

            print(f"   -> Longitud de respuesta: {len(resp_text)} caracteres")
            print(f"   -> Menciona componentes de la máquina: {'SÍ' if has_plant_name else 'NO'}")
            print(f"   -> Incluye checklist estructurado: {'SÍ' if has_checklist else 'NO'}")
            print(f"   -> RESULTADO: {'✅ EXITOSO (APROBADO)' if passed else '❌ FALLÓ'}")
            print("-" * 60)

            results.append({
                "planta_id": p_id,
                "nombre": p_nombre,
                "passed": passed,
                "length": len(resp_text),
                "preview": resp_text[:180] + "..."
            })
        except Exception as e:
            print(f"   -> RESULTADO: ❌ ERROR: {e}")
            results.append({
                "planta_id": p_id,
                "nombre": p_nombre,
                "passed": False,
                "error": str(e)
            })

    total_passed = sum(1 for r in results if r["passed"])
    print(f"\n============================================================")
    print(f" RESUMEN DE PRUEBAS DEL AGENTE IA")
    print(f" Aprobadas: {total_passed} de {len(plantas)}")
    print(f"============================================================")

    for r in results:
        status_icon = "✅" if r["passed"] else "❌"
        print(f"{status_icon} Planta #{r['planta_id']}: {r['nombre']} ({'OK' if r['passed'] else r.get('error', 'Fallo de validación')})")

    if total_passed == len(plantas):
        print("\n🎯 ¡TODAS LAS PRUEBAS FUERON 100% EXITOSAS!")
        sys.exit(0)
    else:
        print("\n⚠️ AL MENOS UNA PRUEBA NO PASÓ.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
