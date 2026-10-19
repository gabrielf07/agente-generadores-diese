/* =========================================================================
   DIESELGEN INTELLIGENCE - JAVASCRIPT APPLICATION CORE
   SPA Router, Plant Dossier Renderer, Photo Lightbox & Contextual AI Agent
   ========================================================================= */

// --- Global Application State ---
const state = {
  currentView: 'sedes',
  sedes: [],
  currentSede: null,
  currentPlanta: null,
  allPlantas: [],
  allCases: [],
  chatPlantaId: null,
  chatMessages: []
};

// =========================================================================
// INITIALIZATION
// =========================================================================

document.addEventListener('DOMContentLoaded', () => {
  loadInitialData();
  setDefaultJobDate();
});

function setDefaultJobDate() {
  const dateInput = document.getElementById('input-trabajo-fecha');
  if (dateInput) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
  }
}

async function loadInitialData() {
  try {
    await Promise.all([
      fetchStats(),
      fetchSedes(),
      fetchAllPlantas()
    ]);
  } catch (err) {
    console.error('Error inicializando datos:', err);
  }
}

// =========================================================================
// API CALLS
// =========================================================================

async function fetchStats() {
  try {
    const res = await fetch('/api/stats');
    if (res.ok) {
      const stats = await res.json();
      document.getElementById('stat-sedes-count').textContent = stats.total_sedes;
      document.getElementById('stat-plantas-count').textContent = `${stats.operativas}/${stats.total_plantas}`;
      document.getElementById('stat-kva-count').textContent = `${stats.total_kva.toLocaleString()} kVA`;
      document.getElementById('stat-casos-count').textContent = `${stats.total_casos} casos`;
    }
  } catch (e) {
    console.warn('Error al obtener estadísticas:', e);
  }
}

async function fetchSedes() {
  try {
    const res = await fetch('/api/sedes');
    if (res.ok) {
      state.sedes = await res.json();
      renderSedesGrid(state.sedes);
      updateModalSedeOptions();
    }
  } catch (e) {
    console.error('Error al cargar sedes:', e);
  }
}

async function fetchAllPlantas() {
  try {
    const res = await fetch('/api/plantas');
    if (res.ok) {
      state.allPlantas = await res.json();
      updateChatPlantSelector();
    }
  } catch (e) {
    console.error('Error al cargar plantas:', e);
  }
}

// =========================================================================
// VIEW ROUTING
// =========================================================================

function navigateTo(viewName) {
  state.currentView = viewName;
  document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));

  if (viewName === 'sedes') {
    document.getElementById('view-sedes').classList.add('active');
    fetchSedes();
  } else if (viewName === 'sede-plantas') {
    document.getElementById('view-sede-plantas').classList.add('active');
  } else if (viewName === 'planta-detail') {
    document.getElementById('view-planta-detail').classList.add('active');
  } else if (viewName === 'cases') {
    document.getElementById('view-cases').classList.add('active');
    fetchCases();
  } else if (viewName === 'manuals') {
    document.getElementById('view-manuals').classList.add('active');
    fetchManuals();
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function returnToCurrentSede() {
  if (state.currentSede) {
    openSede(state.currentSede.id);
  } else {
    navigateTo('sedes');
  }
}

// =========================================================================
// VISTA 1: SEDES HUB
// =========================================================================

function renderSedesGrid(sedes) {
  const container = document.getElementById('sedes-container');
  if (!container) return;

  if (sedes.length === 0) {
    container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-dim); padding: 3rem;">No hay sedes registradas aún.</div>`;
    return;
  }

  container.innerHTML = sedes.map(sede => `
    <div class="sede-card" onclick="openSede(${sede.id})">
      <div>
        <div class="sede-card-header">
          <div class="sede-icon">${sede.icono || '🏢'}</div>
          <span class="badge-code">${sede.codigo}</span>
        </div>
        <h3>${sede.nombre}</h3>
        <div class="sede-address">
          <span>📍</span> ${sede.direccion || sede.ciudad}
        </div>
        <p style="font-size: 0.85rem; color: var(--text-dim); margin-bottom: 1rem; line-height: 1.4;">
          ${sede.notas || 'Sede operativa de generación eléctrica.'}
        </p>
      </div>

      <div>
        <div class="sede-metrics">
          <div class="metric-item">
            <div class="metric-label">Plantas</div>
            <div class="metric-val cyan">${sede.total_plantas}</div>
          </div>
          <div class="metric-item">
            <div class="metric-label">Operativas</div>
            <div class="metric-val green">${sede.plantas_operativas}</div>
          </div>
          <div class="metric-item">
            <div class="metric-label">Total kVA</div>
            <div class="metric-val">${(sede.total_kva || 0).toLocaleString()}</div>
          </div>
        </div>

        <div class="sede-card-footer">
          <span>Ver Grupos Electrógenos</span>
          <span>➔</span>
        </div>
      </div>
    </div>
  `).join('');
}

async function openSede(sedeId) {
  try {
    const res = await fetch(`/api/sedes/${sedeId}`);
    if (!res.ok) throw new Error('Error al cargar sede');
    const data = await res.json();

    state.currentSede = data.sede;
    document.getElementById('breadcrumb-sede-name').textContent = data.sede.nombre;

    // Render Sede Banner
    document.getElementById('sede-banner-info').innerHTML = `
      <div class="sede-banner-info">
        <h2>${data.sede.icono || '🏢'} ${data.sede.nombre} <span class="badge-code">${data.sede.codigo}</span></h2>
        <p>${data.sede.notas || 'Gestión centralizada de generadores diésel en esta sede.'}</p>
        <div class="sede-banner-contact">
          <span>📍 ${data.sede.direccion || data.sede.ciudad}</span>
          ${data.sede.contacto_nombre ? `<span>👤 ${data.sede.contacto_nombre} (${data.sede.contacto_cargo || 'Supervisor'})</span>` : ''}
          ${data.sede.contacto_telefono ? `<span>📞 ${data.sede.contacto_telefono}</span>` : ''}
        </div>
      </div>
      <div>
        <span class="badge-code" style="font-size: 0.95rem; padding: 0.4rem 0.8rem;">
          ${data.plantas.length} Generadores Registrados
        </span>
      </div>
    `;

    renderPlantasGrid(data.plantas);
    navigateTo('sede-plantas');
  } catch (err) {
    alert('Error al abrir la sede: ' + err.message);
  }
}

// =========================================================================
// VISTA 2: PLANTAS GRID
// =========================================================================

function renderPlantasGrid(plantas) {
  const container = document.getElementById('sede-plantas-container');
  if (!container) return;

  if (plantas.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; color: var(--text-dim); padding: 3rem;">
        No hay plantas registradas en esta sede.<br><br>
        <button class="btn btn-primary btn-sm" onclick="openAddPlantaModalForCurrentSede()">➕ Agregar la primera planta</button>
      </div>`;
    return;
  }

  container.innerHTML = plantas.map(p => {
    let statusClass = 'status-operativa';
    if (p.estado === 'En Mantenimiento') statusClass = 'status-mantenimiento';
    else if (p.estado === 'Fuera de Servicio' || p.estado === 'Alerta') statusClass = 'status-falla';

    return `
      <div class="planta-card">
        <div>
          <div class="planta-card-header">
            <span class="planta-status-badge ${statusClass}">
              ● ${p.estado}
            </span>
            <span class="capacity-badge">
              ⚡ ${p.capacidad_kva} kVA (${p.capacidad_kw} kW)
            </span>
          </div>

          <h4>${p.nombre}</h4>
          <div class="planta-location">
            <span>📍</span> ${p.ubicacion_interna || 'Sala de Máquinas'} &nbsp;•&nbsp; <span class="badge-code">${p.codigo}</span>
          </div>

          <div class="horometro-bar">
            <span class="h-label">Horómetro Actual:</span>
            <span class="h-val">${p.horas_operacion.toLocaleString()} hrs</span>
          </div>

          <div class="planta-key-specs">
            <div class="spec-row">
              <span class="spec-name"><span>🔧</span> Motor:</span>
              <span class="spec-val">${p.motor_marca || 'N/D'} ${p.motor_modelo || ''}</span>
            </div>
            <div class="spec-row">
              <span class="spec-name"><span>⚡</span> Alternador:</span>
              <span class="spec-val">${p.generador_marca || 'N/D'} (${p.generador_voltaje || '208/120V'})</span>
            </div>
            <div class="spec-row">
              <span class="spec-name"><span>🎛️</span> Controlador:</span>
              <span class="spec-val">${p.controlador_marca || 'DSE'} ${p.controlador_modelo || ''}</span>
            </div>
            <div class="spec-row">
              <span class="spec-name"><span>📅</span> Último Servicio:</span>
              <span class="spec-val" style="color: var(--accent-cyan);">${p.ultima_fecha_mantenimiento || 'Sin registros'}</span>
            </div>
          </div>
        </div>

        <div class="planta-card-actions">
          <button class="btn btn-primary" onclick="openPlanta(${p.id})">
            📖 Ficha Técnica & Trabajos
          </button>
          <button class="btn btn-secondary btn-icon" title="Consultar Agente IA de esta Planta" onclick="openChatForPlanta(${p.id})">
            🤖
          </button>
        </div>
      </div>
    `;
  }).join('');
}

// =========================================================================
// VISTA 3: FICHA INTEGRAL DE PLANTA (TABS, SPECS & HISTORIAL)
// =========================================================================

async function openPlanta(plantaId) {
  try {
    const res = await fetch(`/api/plantas/${plantaId}`);
    if (!res.ok) throw new Error('Error al obtener datos de la planta');
    const data = await res.json();
    const p = data.planta;
    const trabajos = data.trabajos;

    state.currentPlanta = p;

    // Breadcrumbs
    document.getElementById('breadcrumb-link-sede').textContent = p.sede_nombre;
    document.getElementById('breadcrumb-planta-name').textContent = p.nombre;

    // Enlazar contexto de chat automáticamente a esta planta
    setChatPlantContext(p.id);

    // Summary Header Banner
    let statusClass = 'status-operativa';
    if (p.estado === 'En Mantenimiento') statusClass = 'status-mantenimiento';
    else if (p.estado === 'Fuera de Servicio' || p.estado === 'Alerta') statusClass = 'status-falla';

    document.getElementById('planta-detail-header-card').innerHTML = `
      <div class="planta-detail-top">
        <div class="planta-detail-titles">
          <h2>${p.nombre}</h2>
          <p>Ensambladora: <strong>${p.ensambladora || 'Industrial'}</strong> &nbsp;|&nbsp; Ubicación: <strong>${p.ubicacion_interna || 'Sala de Máquinas'}</strong> &nbsp;|&nbsp; Sede: <strong>${p.sede_nombre}</strong></p>
          <div class="planta-detail-badges">
            <span class="badge-code">${p.codigo}</span>
            <span class="planta-status-badge ${statusClass}">● ${p.estado}</span>
            <span class="capacity-badge">⚡ ${p.capacidad_kva} kVA / ${p.capacidad_kw} kW</span>
            <span class="badge-code" style="color: #cbd5e1;">Prioridad: ${p.prioridad || 'Crítica'}</span>
          </div>
        </div>

        <div class="planta-detail-quick-actions">
          <button class="btn btn-primary" onclick="openChatForCurrentPlanta('Hola, estoy frente a esta planta. Dame un diagnóstico rápido del equipo y el estado de sus mantenimientos.')">
            🤖 Asistente IA de esta Planta
          </button>
          <button class="btn btn-success" onclick="openNewTrabajoModalForPlanta(${p.id})">
            ➕ Registrar Trabajo
          </button>
        </div>
      </div>

      <div class="detail-metrics-row">
        <div class="detail-metric-card">
          <div class="label">Horómetro Actual</div>
          <div class="value" style="color: var(--accent-cyan); font-family: var(--font-mono);">${p.horas_operacion.toLocaleString()} hrs</div>
        </div>
        <div class="detail-metric-card">
          <div class="label">Próximo Mantenimiento</div>
          <div class="value" style="color: var(--accent-amber);">${p.proximo_mantenimiento_horas ? `${p.proximo_mantenimiento_horas}h` : '250h'}</div>
        </div>
        <div class="detail-metric-card">
          <div class="label">Tensión Nominal</div>
          <div class="value">${p.generador_voltaje || '208/120V'}</div>
        </div>
        <div class="detail-metric-card">
          <div class="label">Intervenciones Registradas</div>
          <div class="value">${trabajos.length} trabajos</div>
        </div>
      </div>
    `;

    // Render TAB 1: Plan de Mantenimiento
    document.getElementById('planta-plan-text').textContent = p.plan_mantenimiento_texto || 'No se ha configurado un plan específico para este equipo.';

    // Render TAB 2: Motor Specs
    renderMotorSpecs(p);

    // Render TAB 3: Generador Specs
    renderGeneradorSpecs(p);

    // Render TAB 4: Controlador Specs
    renderControladorSpecs(p);

    // Render TAB 5: Historial de Trabajos y Fotos
    renderTrabajosHistory(trabajos);

    // Switch to first tab
    switchPlantaTab('tab-plan');

    navigateTo('planta-detail');
  } catch (err) {
    alert('Error al abrir la planta: ' + err.message);
  }
}

function switchPlantaTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

  const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
  if (activeBtn) activeBtn.classList.add('active');

  const panel = document.getElementById(tabId);
  if (panel) panel.classList.add('active');
}

function renderMotorSpecs(p) {
  const container = document.getElementById('motor-specs-container');
  container.innerHTML = `
    <!-- Box 1: Identificación y Desempeño Mecánico -->
    <div class="spec-box">
      <div class="spec-box-header">
        <span class="icon">🔧</span>
        <h3>Identificación & Desempeño del Motor</h3>
      </div>
      <table class="spec-table">
        <tr><th>Marca del Motor:</th><td>${p.motor_marca || 'N/D'}</td></tr>
        <tr><th>Modelo del Motor:</th><td><span class="tag-code">${p.motor_modelo || 'N/D'}</span></td></tr>
        <tr><th>Número de Serial:</th><td>${p.motor_serial || 'N/D'}</td></tr>
        <tr><th>Cilindrada y Configuración:</th><td>${p.motor_cilindros || '6 en línea'}</td></tr>
        <tr><th>Aspiración:</th><td>${p.motor_aspiracion || 'Turboalimentado'}</td></tr>
        <tr><th>Potencia Mecánica:</th><td><strong>${p.motor_potencia_hp || 'N/D'} HP</strong></td></tr>
        <tr><th>Sistema de Inyección / Gobernador:</th><td>${p.motor_gobernador || 'ECM Electrónico'}</td></tr>
        <tr><th>Combustible:</th><td>${p.motor_tipo_combustible || 'Diésel #2'}</td></tr>
        <tr><th>Sistema Eléctrico DC:</th><td>${p.motor_sistema_electrico_dc || '24V DC'}</td></tr>
        <tr><th>Baterías de Arranque:</th><td>${p.motor_baterias || '2x 12V 1000 CCA'}</td></tr>
      </table>
    </div>

    <!-- Box 2: Lubricación, Refrigeración y Filtración OEM -->
    <div class="spec-box">
      <div class="spec-box-header">
        <span class="icon">🛢️</span>
        <h3>Fluidos, Lubricación & Tren de Filtración OEM</h3>
      </div>
      <table class="spec-table">
        <tr><th>Capacidad de Aceite:</th><td><strong>${p.motor_capacidad_aceite || 'N/D'}</strong></td></tr>
        <tr><th>Viscosidad Recomendada:</th><td>${p.motor_viscosidad_aceite || 'SAE 15W-40 CI-4/CK-4'}</td></tr>
        <tr><th>Capacidad de Refrigerante:</th><td>${p.motor_capacidad_refrigerante || 'N/D'}</td></tr>
        <tr><th>Tipo de Refrigerante:</th><td>${p.motor_tipo_refrigerante || '50/50 con aditivo DCA4'}</td></tr>
        <tr><th>Filtro de Aceite Lubricante:</th><td><span class="tag-code" style="color: var(--success); background: var(--success-light); border-color: var(--success-border);">${p.motor_filtro_aceite || 'N/D'}</span></td></tr>
        <tr><th>Filtro Combustible Primario (Separador):</th><td><span class="tag-code">${p.motor_filtro_combustible_primario || 'N/D'}</span></td></tr>
        <tr><th>Filtro Combustible Secundario:</th><td><span class="tag-code">${p.motor_filtro_combustible_secundario || 'N/D'}</span></td></tr>
        <tr><th>Filtro de Aire:</th><td><span class="tag-code">${p.motor_filtro_aire || 'N/D'}</span></td></tr>
        <tr><th>Filtro de Agua / Anticorrosivo:</th><td><span class="tag-code">${p.motor_filtro_agua_refrigerante || 'N/A'}</span></td></tr>
        <tr><th>Notas Técnicas:</th><td>${p.motor_notes || p.motor_notas || 'Mantener calentador de camisa energizado.'}</td></tr>
      </table>
    </div>
  `;
}

function renderGeneradorSpecs(p) {
  const container = document.getElementById('generador-specs-container');
  container.innerHTML = `
    <!-- Box 1: Alternador y Parámetros Eléctricos -->
    <div class="spec-box">
      <div class="spec-box-header">
        <span class="icon">⚡</span>
        <h3>Alternador & Parámetros de Generación</h3>
      </div>
      <table class="spec-table">
        <tr><th>Marca del Alternador:</th><td>${p.generador_marca || 'N/D'}</td></tr>
        <tr><th>Modelo:</th><td><span class="tag-code">${p.generador_modelo || 'N/D'}</span></td></tr>
        <tr><th>Serial:</th><td>${p.generador_serial || 'N/D'}</td></tr>
        <tr><th>Potencia Standby:</th><td><strong>${p.generador_kva || p.capacidad_kva} kVA (${p.generador_kw || p.capacidad_kw} kW)</strong></td></tr>
        <tr><th>Tensión Nominal:</th><td><strong>${p.generador_voltaje || '208/120V'}</strong></td></tr>
        <tr><th>Fases & Frecuencia:</th><td>${p.generador_fases || 'Trifásico (4 Hilos)'} @ ${p.generador_frecuencia || '60 Hz'}</td></tr>
        <tr><th>Velocidad de Giro:</th><td>${p.generador_rpm || 1800} RPM</td></tr>
        <tr><th>Factor de Potencia (FP):</th><td>${p.generador_factor_potencia || 0.8}</td></tr>
        <tr><th>Corriente Nominal (Amperios):</th><td><strong>${p.generador_amperaje_nominal || 'N/D'} A</strong></td></tr>
      </table>
    </div>

    <!-- Box 2: Regulación de Voltaje (AVR) y Aislamiento -->
    <div class="spec-box">
      <div class="spec-box-header">
        <span class="icon">🎚️</span>
        <h3>Regulador de Voltaje (AVR) & Excitación</h3>
      </div>
      <table class="spec-table">
        <tr><th>Modelo de AVR:</th><td><span class="tag-code" style="color: var(--warning); background: var(--warning-light); border-color: var(--warning-border);">${p.generador_modelo_avr || 'AS440 / SX460'}</span></td></tr>
        <tr><th>Tipo de Excitación:</th><td>${p.generador_tipo_excitacion || 'Brushless (Sin escobillas)'}</td></tr>
        <tr><th>Clase de Aislamiento:</th><td>${p.generador_clase_aislamiento || 'Clase H / IP23'}</td></tr>
        <tr><th>Resistencias Anticondensación:</th><td>120V AC en reposo</td></tr>
        <tr><th>Notas Eléctricas:</th><td>${p.generador_notas || 'Comprobar calibración de potenciómetro de estabilidad periódicamente.'}</td></tr>
      </table>
    </div>
  `;
}

function renderControladorSpecs(p) {
  const container = document.getElementById('controlador-specs-container');
  container.innerHTML = `
    <!-- Box 1: Identificación y Modos del Panel -->
    <div class="spec-box">
      <div class="spec-box-header">
        <span class="icon">🎛️</span>
        <h3>Controlador de Planta & Operación</h3>
      </div>
      <table class="spec-table">
        <tr><th>Marca del Módulo:</th><td>${p.controlador_marca || 'Deep Sea Electronics'}</td></tr>
        <tr><th>Modelo del Controlador:</th><td><span class="tag-code">${p.controlador_modelo || 'DSE 7320 MKII'}</span></td></tr>
        <tr><th>Versión de Firmware:</th><td>${p.controlador_firmware || 'v3.2'}</td></tr>
        <tr><th>Modo de Operación:</th><td><strong style="color: var(--success);">${p.controlador_modo || 'Auto'}</strong></td></tr>
        <tr><th>Pick-up Magnético (MPU):</th><td>${p.controlador_pick_up_dientes || '126 dientes en cremallera'}</td></tr>
        <tr><th>Configuración I/O:</th><td>${p.controlador_config_io || 'Salida Marcha, Solenoide, Falla Red ATS'}</td></tr>
        <tr><th>Notas del Controlador:</th><td>${p.controlador_notas || 'Monitoreo remoto RS485 activo.'}</td></tr>
      </table>
    </div>

    <!-- Box 2: Umbrales de Seguridad y Disparo -->
    <div class="spec-box">
      <div class="spec-box-header">
        <span class="icon">🚨</span>
        <h3>Parámetros de Disparo & Alarmas de Parada</h3>
      </div>
      <table class="spec-table">
        <tr><th>Baja Presión de Aceite (Disparo):</th><td><span class="tag-code" style="color: var(--danger); background: var(--danger-light); border-color: var(--danger-border);">${p.controlador_umbral_baja_presion_aceite || '18 PSI (1.2 bar)'}</span></td></tr>
        <tr><th>Alta Temperatura Refrigerante:</th><td><span class="tag-code" style="color: var(--danger); background: var(--danger-light); border-color: var(--danger-border);">${p.controlador_umbral_alta_temperatura || '102 °C (215 °F)'}</span></td></tr>
        <tr><th>Sobrevelocidad de Motor:</th><td><span class="tag-code">${p.controlador_umbral_sobrevelocidad || '2070 RPM (69 Hz)'}</span></td></tr>
        <tr><th>Subvoltaje / Sobrevoltaje:</th><td>${p.controlador_umbral_subvoltaje || '-15%'} / ${p.controlador_umbral_sobrevoltaje || '+15%'}</td></tr>
        <tr><th>Tiempos de Transferencia:</th><td>Arranque en 1.5s, toma de carga en 8s</td></tr>
      </table>
    </div>
  `;
}

function renderTrabajosHistory(trabajos) {
  const container = document.getElementById('trabajos-timeline-container');
  if (!container) return;

  if (trabajos.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--text-dim); padding: 3rem; background: var(--bg-card); border-radius: var(--radius-lg); border: 1px solid var(--border-subtle);">
        No hay trabajos de mantenimiento registrados en esta planta.<br><br>
        <button class="btn btn-primary btn-sm" onclick="openModal('modal-nuevo-trabajo')">➕ Registrar el primer trabajo</button>
      </div>`;
    return;
  }

  container.innerHTML = trabajos.map(t => {
    let photosHtml = '';
    if (t.fotos && t.fotos.length > 0) {
      photosHtml = `
        <div style="margin-top: 1rem;">
          <strong style="font-size: 0.82rem; color: var(--text-dim); text-transform: uppercase;">📸 Registro Fotográfico del Trabajo:</strong>
          <div class="trabajo-photos-grid">
            ${t.fotos.map((src, idx) => `
              <div class="photo-thumb" onclick="openLightbox('${src}', '${escapeQuotes(t.titulo)} - Fecha: ${t.fecha} por ${t.tecnico}')">
                <img src="${src}" alt="Foto trabajo ${idx + 1}" loading="lazy">
                <div class="overlay">🔍</div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    return `
      <div class="trabajo-card">
        <div class="trabajo-header">
          <div class="trabajo-meta">
            <span class="date">📅 ${t.fecha}</span>
            <span class="hours">⏱️ ${t.horas_horometro ? t.horas_horometro.toLocaleString() : 'N/D'} hrs</span>
            <span class="tech">👨‍🔧 ${t.tecnico}</span>
          </div>
          <span class="badge-code" style="color: #93c5fd; background: rgba(59, 130, 246, 0.15);">
            ${t.tipo_trabajo}
          </span>
        </div>

        <h4>${t.titulo}</h4>
        <p class="desc">${t.descripcion}</p>

        ${t.repuestos_utilizados ? `
          <div class="trabajo-repuestos-box">
            <strong>Insumos / Repuestos Utilizados:</strong> ${t.repuestos_utilizados}
          </div>
        ` : ''}

        ${t.observaciones ? `
          <div style="font-size: 0.85rem; color: var(--text-dim); margin-bottom: 0.5rem;">
            <em>💡 Recomendaciones:</em> ${t.observaciones}
          </div>
        ` : ''}

        ${photosHtml}
      </div>
    `;
  }).join('');
}

function escapeQuotes(str) {
  if (!str) return '';
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

// =========================================================================
// LIGHTBOX DE FOTOS
// =========================================================================

function openLightbox(src, caption) {
  const modal = document.getElementById('lightbox-modal');
  const img = document.getElementById('lightbox-img');
  const cap = document.getElementById('lightbox-caption');

  img.src = src;
  cap.textContent = caption || 'Fotografía de intervención técnica';
  modal.classList.add('open');
}

function closeLightbox() {
  document.getElementById('lightbox-modal').classList.remove('open');
}

// =========================================================================
// VISTA 4: BITÁCORA DE CASOS
// =========================================================================

async function fetchCases() {
  try {
    const res = await fetch('/api/cases');
    if (res.ok) {
      state.allCases = await res.json();
      renderCases(state.allCases);
    }
  } catch (err) {
    console.error('Error al cargar casos:', err);
  }
}

function renderCases(cases) {
  const container = document.getElementById('cases-list-container');
  if (!container) return;

  if (cases.length === 0) {
    container.innerHTML = `<div style="text-align: center; color: var(--text-dim); padding: 3rem;">No hay casos registrados aún.</div>`;
    return;
  }

  container.innerHTML = cases.map(c => `
    <div class="trabajo-card" style="border-left: 3px solid #3b82f6;">
      <div class="trabajo-header">
        <div class="trabajo-meta">
          <span class="badge-code">Caso #${c.id}</span>
          <span class="tech">👨‍🔧 Técnico: ${c.tecnico}</span>
          <span class="badge-code" style="color: #93c5fd;">${c.planta_modelo}</span>
        </div>
        <div style="font-size: 0.8rem; color: var(--text-dim);">
          📅 ${c.timestamp || 'Fecha previa'}
        </div>
      </div>

      <h4 style="color: var(--danger); margin-top: 0.5rem;">⚠️ Síntoma: ${c.sintoma}</h4>

      ${c.descartes_previos ? `
        <p style="font-size: 0.88rem; color: var(--text-body); margin-bottom: 0.4rem;">
          <strong>🔍 Descartes Previos:</strong> ${c.descartes_previos}
        </p>
      ` : ''}

      <div style="background: var(--danger-light); border-left: 3px solid var(--danger); border-radius: 6px; padding: 0.65rem 0.85rem; margin: 0.6rem 0; font-size: 0.88rem; color: #991b1b;">
        <strong>🎯 Causa Raíz Comprobada:</strong> ${c.causa_raiz}
      </div>

      <div style="background: var(--success-light); border-left: 3px solid var(--success); border-radius: 6px; padding: 0.65rem 0.85rem; margin: 0.6rem 0; font-size: 0.88rem; color: #065f46;">
        <strong>🛠️ Solución Aplicada:</strong> ${c.solucion}
      </div>

      ${c.consejo_campo ? `
        <p style="font-size: 0.85rem; color: var(--text-body); margin-top: 0.5rem;">
          <strong>💡 Consejo Práctico:</strong> ${c.consejo_campo}
        </p>
      ` : ''}

      <div style="margin-top: 0.85rem; display: flex; align-items: center; justify-content: space-between;">
        <span style="font-size: 0.8rem; color: var(--text-dim);">
          👍 Validado útil: <strong>${c.utilidad_count || 1}</strong> veces por técnicos en campo
        </span>
        <button class="btn btn-secondary btn-sm" onclick="upvoteCase(${c.id})">
          👍 Me sirvió esta solución
        </button>
      </div>
    </div>
  `).join('');
}

function filterCases() {
  const query = document.getElementById('input-search-cases').value.toLowerCase().trim();
  if (!query) {
    renderCases(state.allCases);
    return;
  }
  const filtered = state.allCases.filter(c =>
    (c.sintoma && c.sintoma.toLowerCase().includes(query)) ||
    (c.causa_raiz && c.causa_raiz.toLowerCase().includes(query)) ||
    (c.solucion && c.solucion.toLowerCase().includes(query)) ||
    (c.planta_modelo && c.planta_modelo.toLowerCase().includes(query)) ||
    (c.tecnico && c.tecnico.toLowerCase().includes(query))
  );
  renderCases(filtered);
}

async function upvoteCase(caseId) {
  try {
    const res = await fetch(`/api/cases/${caseId}/utility`, { method: 'POST' });
    if (res.ok) {
      alert('¡Gracias! La experiencia ha sido revalidada.');
      fetchCases();
    }
  } catch (e) {
    console.error(e);
  }
}

// =========================================================================
// VISTA 5: MANUALES Y GUÍAS
// =========================================================================

async function fetchManuals() {
  try {
    const res = await fetch('/api/manuals');
    if (res.ok) {
      const manuals = await res.json();
      renderManuals(manuals);
    }
  } catch (err) {
    console.error('Error al cargar manuales:', err);
  }
}

function renderManuals(manuals) {
  const container = document.getElementById('manuals-list-container');
  if (!container) return;

  if (manuals.length === 0) {
    container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-dim); padding: 3rem;">No hay manuales cargados.</div>`;
    return;
  }

  container.innerHTML = manuals.map(m => `
    <div class="sede-card" style="cursor: default;">
      <div class="sede-card-header">
        <div class="sede-icon" style="background: var(--danger-light); color: var(--danger); border-color: var(--danger-border);">📄</div>
        <span class="badge-code">${m.categoria || 'PDF'}</span>
      </div>
      <h3>${m.titulo}</h3>
      <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">
        Archivo: <code>${m.filename}</code> &nbsp;|&nbsp; Tamaño: ${m.tamano_mb || '1.5'} MB
      </p>
      <div class="sede-card-footer">
        <span style="font-size: 0.8rem; color: var(--success); font-weight: 600;">● Indexado en Base Vectorial</span>
        <button class="btn btn-secondary btn-sm" onclick="openChatForCurrentPlanta('Explícame los puntos clave del manual ${escapeQuotes(m.titulo)}')">
          Consultar
        </button>
      </div>
    </div>
  `).join('');
}

// =========================================================================
// BURBUJA FLOTANTE DEL CHAT (EL AGENTE EN LA MANO)
// =========================================================================

function toggleChatWidget() {
  const widget = document.getElementById('chat-widget');
  widget.classList.toggle('open');
  if (widget.classList.contains('open')) {
    setTimeout(() => {
      document.getElementById('chat-user-input').focus();
    }, 200);
  }
}

function updateChatPlantSelector() {
  const selector = document.getElementById('chat-plant-selector');
  if (!selector) return;

  selector.innerHTML = `
    <option value="">⚙️ Modo General (Todas las plantas)</option>
    ${state.allPlantas.map(p => `
      <option value="${p.id}">${p.nombre} (${p.sede_codigo || ''})</option>
    `).join('')}
  `;

  if (state.chatPlantaId) {
    selector.value = state.chatPlantaId;
  }
}

function setChatPlantContext(plantaId) {
  state.chatPlantaId = plantaId;
  const selector = document.getElementById('chat-plant-selector');
  if (selector) selector.value = plantaId || '';

  const label = document.getElementById('chat-plant-name');
  if (label) {
    if (plantaId) {
      const p = state.allPlantas.find(x => x.id === plantaId) || state.currentPlanta;
      label.textContent = p ? p.nombre : 'Planta Seleccionada';
    } else {
      label.textContent = 'Modo General';
    }
  }
}

function onChatPlantChanged() {
  const val = document.getElementById('chat-plant-selector').value;
  setChatPlantContext(val ? parseInt(val) : null);
}

function openChatForPlanta(plantaId) {
  setChatPlantContext(plantaId);
  const widget = document.getElementById('chat-widget');
  if (!widget.classList.contains('open')) {
    widget.classList.add('open');
  }
}

function openChatForCurrentPlanta(initialPrompt) {
  if (state.currentPlanta) {
    setChatPlantContext(state.currentPlanta.id);
  }
  const widget = document.getElementById('chat-widget');
  if (!widget.classList.contains('open')) {
    widget.classList.add('open');
  }
  if (initialPrompt) {
    sendQuickPrompt(initialPrompt);
  }
}

function handleChatKeyDown(event) {
  if (event.key === 'Enter') {
    sendChatMessage();
  }
}

function sendQuickPrompt(promptText) {
  document.getElementById('chat-user-input').value = promptText;
  sendChatMessage();
}

async function sendChatMessage() {
  const input = document.getElementById('chat-user-input');
  const message = input.value.trim();
  if (!message) return;

  // Append user bubble
  appendChatBubble('user', message);
  input.value = '';

  // Append temporary bot typing indicator
  const typingId = appendChatBubble('bot', '<em>🔍 Consultando ficha técnica de la planta, manuales y precedentes de campo...</em>');

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message,
        planta_id: state.chatPlantaId
      })
    });

    if (!res.ok) throw new Error('Error al procesar consulta con el agente');
    const data = await res.json();

    // Replace typing indicator with markdown parsed content
    const botBubble = document.getElementById(typingId);
    if (botBubble) {
      botBubble.innerHTML = marked.parse(data.response || 'Sin respuesta del asistente.');
    }
  } catch (err) {
    const botBubble = document.getElementById(typingId);
    if (botBubble) {
      botBubble.innerHTML = `<span style="color: #f87171;">⚠️ Hubo una dificultad momentánea con la red del modelo. Intenta nuevamente.</span>`;
    }
  }

  // Auto scroll to bottom
  const container = document.getElementById('chat-messages-container');
  container.scrollTop = container.scrollHeight;
}

function appendChatBubble(role, content) {
  const container = document.getElementById('chat-messages-container');
  const bubble = document.createElement('div');
  const id = 'bubble-' + Date.now() + '-' + Math.random().toString(36).substr(2, 4);
  bubble.id = id;
  bubble.className = `chat-bubble ${role}`;
  bubble.innerHTML = content;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
  return id;
}

function clearChat() {
  const container = document.getElementById('chat-messages-container');
  container.innerHTML = `
    <div class="chat-bubble bot">
      👋 <strong>Conversación reiniciada.</strong><br><br>
      Estoy listo para asistirte con el diagnóstico de campo, especificaciones de motor/generador/controlador y checklist de servicio.
    </div>
  `;
}

// =========================================================================
// MODALS MANAGEMENT & FORM HANDLERS
// =========================================================================

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('open');
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('open');
  }
}

function updateModalSedeOptions() {
  const select = document.getElementById('select-modal-planta-sede');
  if (!select) return;
  select.innerHTML = state.sedes.map(s => `
    <option value="${s.id}">${s.nombre} (${s.codigo})</option>
  `).join('');
}

function openAddPlantaModalForCurrentSede() {
  updateModalSedeOptions();
  if (state.currentSede) {
    document.getElementById('select-modal-planta-sede').value = state.currentSede.id;
  }
  openModal('modal-nueva-planta');
}

function openNewTrabajoModalForPlanta(plantaId) {
  document.getElementById('input-trabajo-planta-id').value = plantaId;
  if (state.currentPlanta) {
    document.getElementById('input-trabajo-horas').value = state.currentPlanta.horas_operacion;
  }
  setDefaultJobDate();
  openModal('modal-nuevo-trabajo');
}

// 1. Submit Nueva Sede
async function handleCreateSede(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

  try {
    const res = await fetch('/api/sedes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Error al registrar sede');
    closeModal('modal-nueva-sede');
    form.reset();
    await loadInitialData();
    alert('✅ ¡Sede registrada exitosamente!');
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

// 2. Submit Nueva Planta
async function handleCreatePlanta(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

  // Conversión de tipos numéricos
  data.sede_id = parseInt(data.sede_id);
  data.capacidad_kva = parseFloat(data.capacidad_kva);
  data.capacidad_kw = parseFloat(data.capacidad_kw);
  data.horas_operacion = parseFloat(data.horas_operacion || 0);
  if (data.motor_potencia_hp) data.motor_potencia_hp = parseFloat(data.motor_potencia_hp);

  try {
    const res = await fetch('/api/plantas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Error al registrar planta');
    closeModal('modal-nueva-planta');
    form.reset();
    await fetchAllPlantas();
    if (state.currentSede && state.currentSede.id === data.sede_id) {
      openSede(state.currentSede.id);
    } else {
      navigateTo('sedes');
    }
    alert('✅ ¡Grupo electrógeno registrado exitosamente con ficha técnica completa!');
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

// 3. Submit Nuevo Trabajo de Mantenimiento (Con Fotos)
async function handleCreateTrabajo(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const submitBtn = document.getElementById('btn-submit-trabajo');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Subiendo trabajo y fotos...';

  const plantaId = formData.get('planta_id');

  try {
    const res = await fetch(`/api/plantas/${plantaId}/trabajos`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error('Error al guardar trabajo');
    const result = await res.json();

    closeModal('modal-nuevo-trabajo');
    form.reset();
    submitBtn.disabled = false;
    submitBtn.textContent = 'Guardar Trabajo y Fotos';

    alert('✅ ¡Trabajo de mantenimiento y fotografías registrados exitosamente!');
    // Recargar la planta actual para ver el nuevo trabajo en el historial
    openPlanta(plantaId);
  } catch (err) {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Guardar Trabajo y Fotos';
    alert('Error al registrar trabajo: ' + err.message);
  }
}

// 4. Submit Nuevo Caso de Campo
async function handleCreateCase(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

  try {
    const res = await fetch('/api/cases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Error al registrar caso');
    closeModal('modal-nuevo-caso');
    form.reset();
    alert('✅ ¡Caso indexado con éxito! El Asistente IA ya aprendió esta solución para futuras consultas.');
    fetchCases();
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

// 5. Submit Nuevo Manual PDF
async function handleUploadManual(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);

  try {
    const res = await fetch('/api/manuals/upload', {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error('Error al subir manual');
    closeModal('modal-subir-manual');
    form.reset();
    alert('✅ ¡Manual PDF subido e indexado en la base de datos!');
    fetchManuals();
  } catch (err) {
    alert('Error: ' + err.message);
  }
}
