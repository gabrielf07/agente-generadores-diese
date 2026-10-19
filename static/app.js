/* =========================================================================
   DIESELGEN INTELLIGENCE - SPA ENGINE (UI/UX MINIMALISTA & RESPONSIVE)
   Features: Hash Routing (F5 Persistence), Plant CRUD (Create, Edit, Delete),
   Lightbox Viewer, Multi-Sede Hierarchy & Contextual AI Agent
   ========================================================================= */

// --- Estado Global de la Aplicación ---
const state = {
  currentView: 'sedes',
  sedes: [],
  currentSede: null,
  currentPlanta: null,
  allPlantas: [],
  allCases: [],
  chatPlantaId: null,
  plantaToDeleteId: null
};

// =========================================================================
// INICIALIZACIÓN Y ENRUTAMIENTO PERSISTENTE (HASH ROUTER)
// =========================================================================

document.addEventListener('DOMContentLoaded', async () => {
  await loadInitialData();
  setDefaultJobDate();

  // Escuchar cambios de hash para navegación y persistencia F5
  window.addEventListener('hashchange', handleHashRouting);
  
  // Procesar hash inicial en la carga de la página
  if (window.location.hash) {
    handleHashRouting();
  } else {
    navigateToHash('#/sedes');
  }
});

function setDefaultJobDate() {
  const dateInput = document.getElementById('input-trabajo-fecha');
  if (dateInput) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
  }
}

// Notificaciones Toast Minimalistas
function showToast(message, type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.add('toast-show');
  });
  setTimeout(() => {
    toast.classList.remove('toast-show');
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

async function loadInitialData() {
  try {
    await Promise.all([
      fetchStats(),
      fetchSedes(),
      fetchAllPlantas()
    ]);
  } catch (err) {
    console.error('Error al inicializar datos:', err);
  }
}

function handleHashRouting() {
  const hash = window.location.hash || '#/sedes';

  if (hash === '#/sedes' || hash === '') {
    showView('sedes');
    fetchSedes();
  } else if (hash.startsWith('#/sede/')) {
    const sedeId = parseInt(hash.replace('#/sede/', ''));
    if (sedeId) openSede(sedeId, false);
  } else if (hash.startsWith('#/planta/')) {
    const plantaId = parseInt(hash.replace('#/planta/', ''));
    if (plantaId) openPlanta(plantaId, false);
  } else if (hash === '#/cases') {
    showView('cases');
    fetchCases();
  } else if (hash === '#/manuals') {
    showView('manuals');
    fetchManuals();
  }
}

function navigateToHash(hash) {
  if (window.location.hash === hash) {
    handleHashRouting();
  } else {
    window.location.hash = hash;
  }
}

function showView(viewName) {
  state.currentView = viewName;
  document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));

  // Actualizar botones del navbar
  document.querySelectorAll('.nav-actions .btn').forEach(b => b.classList.remove('btn-primary'));
  
  if (viewName === 'sedes') {
    document.getElementById('view-sedes').classList.add('active');
  } else if (viewName === 'sede-plantas') {
    document.getElementById('view-sede-plantas').classList.add('active');
  } else if (viewName === 'planta-detail') {
    document.getElementById('view-planta-detail').classList.add('active');
  } else if (viewName === 'cases') {
    document.getElementById('view-cases').classList.add('active');
  } else if (viewName === 'manuals') {
    document.getElementById('view-manuals').classList.add('active');
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function returnToCurrentSede() {
  if (state.currentPlanta && state.currentPlanta.sede_id) {
    navigateToHash(`#/sede/${state.currentPlanta.sede_id}`);
  } else if (state.currentSede) {
    navigateToHash(`#/sede/${state.currentSede.id}`);
  } else {
    navigateToHash('#/sedes');
  }
}

// =========================================================================
// API CALLS BÁSICAS
// =========================================================================

async function fetchStats() {
  try {
    const res = await fetch('/api/stats');
    if (res.ok) {
      const stats = await res.json();
      document.getElementById('stat-sedes-count').textContent = stats.total_sedes;
      document.getElementById('stat-plantas-count').textContent = `${stats.operativas}/${stats.total_plantas}`;
      document.getElementById('stat-kva-count').textContent = `${stats.total_kva.toLocaleString()} kVA`;
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
// VISTA 1: SEDES HUB
// =========================================================================

function renderSedesGrid(sedes) {
  const container = document.getElementById('sedes-container');
  if (!container) return;

  if (sedes.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 3rem; background: #fff; border-radius: var(--radius-lg); border: 1px solid var(--border-light);">
        No hay sedes registradas aún.<br><br>
        <button class="btn btn-primary" onclick="openModal('modal-nueva-sede')">➕ Registrar la Primera Sede</button>
      </div>`;
    return;
  }

  container.innerHTML = sedes.map(sede => `
    <div class="sede-card" onclick="navigateToHash('#/sede/${sede.id}')">
      <div>
        <div class="sede-card-header">
          <div class="sede-icon">${sede.icono || '🏢'}</div>
          <span class="badge-code">${sede.codigo}</span>
        </div>
        <h3>${sede.nombre}</h3>
        <div class="sede-address">
          <span>📍</span> ${sede.direccion || sede.ciudad}
        </div>
        <p style="font-size: 0.88rem; color: var(--text-body); margin-bottom: 1rem; line-height: 1.4;">
          ${sede.notas || 'Gestión centralizada de grupos electrógenos.'}
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
          <span>Ver Generadores</span>
          <span>➔</span>
        </div>
      </div>
    </div>
  `).join('');
}

async function openSede(sedeId, updateHash = true) {
  if (updateHash) {
    navigateToHash(`#/sede/${sedeId}`);
    return;
  }

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
        <p>${data.sede.notas || 'Gestión centralizada de plantas eléctricas en esta instalación.'}</p>
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
    showView('sede-plantas');
  } catch (err) {
    showToast('Error al abrir la sede: ' + err.message, 'danger');
  }
}

// =========================================================================
// VISTA 2: PLANTAS GRID POR SEDE
// =========================================================================

function renderPlantasGrid(plantas) {
  const container = document.getElementById('sede-plantas-container');
  if (!container) return;

  if (plantas.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 3rem; background: #fff; border-radius: var(--radius-lg); border: 1px solid var(--border-light);">
        No hay plantas registradas en esta sede.<br><br>
        <button class="btn btn-primary" onclick="openAddPlantaModalForCurrentSede()">➕ Registrar la Primera Planta</button>
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
              <span class="spec-name">🔧 Motor:</span>
              <span class="spec-val">${p.motor_marca || 'N/D'} ${p.motor_modelo || ''}</span>
            </div>
            <div class="spec-row">
              <span class="spec-name">⚡ Alternador:</span>
              <span class="spec-val">${p.generador_marca || 'N/D'} (${p.generador_voltaje || '208/120V'})</span>
            </div>
            <div class="spec-row">
              <span class="spec-name">🎛️ Controlador:</span>
              <span class="spec-val">${p.controlador_marca || 'DSE'} ${p.controlador_modelo || ''}</span>
            </div>
            <div class="spec-row">
              <span class="spec-name">📅 Último Servicio:</span>
              <span class="spec-val" style="color: var(--primary);">${p.ultima_fecha_mantenimiento || 'Sin registros'}</span>
            </div>
          </div>
        </div>

        <div style="display: flex; gap: 0.4rem; margin-top: 0.5rem; flex-wrap: wrap;">
          <button class="btn btn-primary btn-sm" style="flex: 1;" onclick="navigateToHash('#/planta/${p.id}')">
            📖 Ficha Técnica
          </button>
          <button class="btn btn-secondary btn-sm" title="Editar Planta" onclick="openEditPlantaModal(${p.id})">
            ✏️ Editar
          </button>
          <button class="btn btn-secondary btn-sm" style="color: var(--danger);" title="Eliminar Planta" onclick="promptDeletePlanta(${p.id}, '${escapeQuotes(p.nombre)}')">
            🗑️
          </button>
          <button class="btn btn-secondary btn-icon btn-sm" title="Consultar Agente IA" onclick="openChatForPlanta(${p.id})">
            🤖
          </button>
        </div>
      </div>
    `;
  }).join('');
}

// =========================================================================
// VISTA 3: FICHA INTEGRAL DE PLANTA (TABS, EDICIÓN & BORRADO)
// =========================================================================

async function openPlanta(plantaId, updateHash = true) {
  if (updateHash) {
    navigateToHash(`#/planta/${plantaId}`);
    return;
  }

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

    // Vincular chat automáticamente
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
            <span class="badge-code" style="color: var(--text-body);">Prioridad: ${p.prioridad || 'Crítica'}</span>
          </div>
        </div>

        <div class="planta-detail-quick-actions">
          <button class="btn btn-secondary btn-sm" onclick="openEditPlantaModal(${p.id})">
            ✏️ Editar Ficha
          </button>
          <button class="btn btn-secondary btn-sm" style="color: var(--danger);" onclick="promptDeletePlanta(${p.id}, '${escapeQuotes(p.nombre)}')">
            🗑️ Eliminar
          </button>
          <button class="btn btn-success btn-sm" onclick="openNewTrabajoModalForPlanta(${p.id})">
            ➕ Registrar Trabajo
          </button>
          <button class="btn btn-primary btn-sm" onclick="openChatForCurrentPlanta('Hola, estoy frente a esta planta. Dame un diagnóstico rápido del equipo.')">
            🤖 Asistente IA
          </button>
        </div>
      </div>

      <div class="detail-metrics-row">
        <div class="detail-metric-card">
          <div class="label">Horómetro Actual</div>
          <div class="value" style="color: var(--primary); font-family: var(--font-mono);">${p.horas_operacion.toLocaleString()} hrs</div>
        </div>
        <div class="detail-metric-card">
          <div class="label">Próximo Mantenimiento</div>
          <div class="value" style="color: var(--warning);">${p.proximo_mantenimiento_horas ? `${p.proximo_mantenimiento_horas}h` : '250h'}</div>
        </div>
        <div class="detail-metric-card">
          <div class="label">Tensión Nominal</div>
          <div class="value">${p.generador_voltaje || '208/120V'}</div>
        </div>
        <div class="detail-metric-card">
          <div class="label">Trabajos Realizados</div>
          <div class="value">${trabajos.length} registros</div>
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

    // Activar pestaña inicial
    switchPlantaTab('tab-plan');

    showView('planta-detail');
  } catch (err) {
    showToast('Error al abrir la planta: ' + err.message, 'danger');
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
    <div class="spec-box">
      <div class="spec-box-header">
        <span class="icon">🔧</span>
        <h3>Identificación & Desempeño Mecánico</h3>
      </div>
      <table class="spec-table">
        <tr><th>Marca del Motor:</th><td>${p.motor_marca || 'N/D'}</td></tr>
        <tr><th>Modelo del Motor:</th><td><span class="tag-code">${p.motor_modelo || 'N/D'}</span></td></tr>
        <tr><th>Número de Serial:</th><td>${p.motor_serial || 'N/D'}</td></tr>
        <tr><th>Cilindros / Configuración:</th><td>${p.motor_cilindros || '6 en línea'}</td></tr>
        <tr><th>Aspiración:</th><td>${p.motor_aspiracion || 'Turboalimentado'}</td></tr>
        <tr><th>Potencia Mecánica:</th><td><strong>${p.motor_potencia_hp || 'N/D'} HP</strong></td></tr>
        <tr><th>Sistema de Inyección / ECM:</th><td>${p.motor_gobernador || 'ECM Electrónico'}</td></tr>
        <tr><th>Combustible:</th><td>${p.motor_tipo_combustible || 'Diésel #2'}</td></tr>
        <tr><th>Sistema Eléctrico DC:</th><td>${p.motor_sistema_electrico_dc || '24V DC'}</td></tr>
        <tr><th>Baterías de Arranque:</th><td>${p.motor_baterias || '2x 12V 1000 CCA'}</td></tr>
      </table>
    </div>

    <div class="spec-box">
      <div class="spec-box-header">
        <span class="icon">🛢️</span>
        <h3>Fluidos & Tren de Filtración OEM</h3>
      </div>
      <table class="spec-table">
        <tr><th>Capacidad de Aceite:</th><td><strong>${p.motor_capacidad_aceite || 'N/D'}</strong></td></tr>
        <tr><th>Viscosidad Recomendada:</th><td>${p.motor_viscosidad_aceite || 'SAE 15W-40 CI-4/CK-4'}</td></tr>
        <tr><th>Capacidad Refrigerante:</th><td>${p.motor_capacidad_refrigerante || 'N/D'}</td></tr>
        <tr><th>Tipo de Refrigerante:</th><td>${p.motor_tipo_refrigerante || '50/50 con aditivo DCA4'}</td></tr>
        <tr><th>Filtro de Aceite Lubricante:</th><td><span class="tag-code" style="color: var(--success); background: var(--success-light); border-color: var(--success-border);">${p.motor_filtro_aceite || 'N/D'}</span></td></tr>
        <tr><th>Filtro Combustible Primario:</th><td><span class="tag-code">${p.motor_filtro_combustible_primario || 'N/D'}</span></td></tr>
        <tr><th>Filtro Combustible Secundario:</th><td><span class="tag-code">${p.motor_filtro_combustible_secundario || 'N/D'}</span></td></tr>
        <tr><th>Filtro de Aire:</th><td><span class="tag-code">${p.motor_filtro_aire || 'N/D'}</span></td></tr>
        <tr><th>Filtro de Agua / Anticorrosivo:</th><td><span class="tag-code">${p.motor_filtro_agua_refrigerante || 'N/A'}</span></td></tr>
        <tr><th>Notas Técnicas:</th><td>${p.motor_notas || 'Mantener calentador de camisa energizado.'}</td></tr>
      </table>
    </div>
  `;
}

function renderGeneradorSpecs(p) {
  const container = document.getElementById('generador-specs-container');
  container.innerHTML = `
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
      <div style="text-align: center; color: var(--text-muted); padding: 3rem; background: #fff; border-radius: var(--radius-lg); border: 1px solid var(--border-light);">
        No hay trabajos de mantenimiento registrados en esta planta.<br><br>
        <button class="btn btn-primary btn-sm" onclick="openModal('modal-nuevo-trabajo')">➕ Registrar el Primer Trabajo</button>
      </div>`;
    return;
  }

  container.innerHTML = trabajos.map(t => {
    let photosHtml = '';
    if (t.fotos && t.fotos.length > 0) {
      photosHtml = `
        <div style="margin-top: 0.85rem;">
          <strong style="font-size: 0.82rem; color: var(--text-muted); text-transform: uppercase;">📸 Fotos del Trabajo:</strong>
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
          <span class="badge-code">
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
          <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">
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
// EDICIÓN Y BORRADO DE PLANTAS (CRUD COMPLETO)
// =========================================================================

async function openEditPlantaModal(plantaId) {
  let p = state.allPlantas.find(x => x.id === plantaId);
  if (!p || !p.motor_marca) {
    try {
      const res = await fetch(`/api/plantas/${plantaId}`);
      if (res.ok) {
        const data = await res.json();
        p = data.planta;
      }
    } catch (e) {
      console.error(e);
    }
  }

  if (!p) {
    showToast('No se pudo cargar la planta para edición.', 'danger');
    return;
  }

  document.getElementById('edit-planta-id').value = p.id;
  document.getElementById('edit-codigo').value = p.codigo || '';
  document.getElementById('edit-nombre').value = p.nombre || '';
  document.getElementById('edit-ensambladora').value = p.ensambladora || '';
  document.getElementById('edit-ubicacion').value = p.ubicacion_interna || '';
  document.getElementById('edit-kva').value = p.capacidad_kva || '';
  document.getElementById('edit-kw').value = p.capacidad_kw || '';
  document.getElementById('edit-horas').value = p.horas_operacion || 0;
  document.getElementById('edit-estado').value = p.estado || 'Operativa';

  document.getElementById('edit-motor-marca').value = p.motor_marca || '';
  document.getElementById('edit-motor-modelo').value = p.motor_modelo || '';
  document.getElementById('edit-motor-hp').value = p.motor_potencia_hp || '';
  document.getElementById('edit-motor-aceite').value = p.motor_capacidad_aceite || '';
  document.getElementById('edit-motor-filtro-aceite').value = p.motor_filtro_aceite || '';
  document.getElementById('edit-motor-filtro-comb').value = p.motor_filtro_combustible_primario || '';

  document.getElementById('edit-gen-marca').value = p.generador_marca || '';
  document.getElementById('edit-gen-modelo').value = p.generador_modelo || '';
  document.getElementById('edit-gen-voltaje').value = p.generador_voltaje || '';
  document.getElementById('edit-gen-avr').value = p.generador_modelo_avr || '';

  document.getElementById('edit-ctrl-marca').value = p.controlador_marca || '';
  document.getElementById('edit-ctrl-modelo').value = p.controlador_modelo || '';
  document.getElementById('edit-ctrl-disparo-aceite').value = p.controlador_umbral_baja_presion_aceite || '';
  document.getElementById('edit-ctrl-disparo-temp').value = p.controlador_umbral_alta_temperatura || '';
  document.getElementById('edit-plan-texto').value = p.plan_mantenimiento_texto || '';

  openModal('modal-editar-planta');
}

async function handleUpdatePlanta(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());
  const plantaId = data.planta_id;
  delete data.planta_id;

  // Conversiones
  data.capacidad_kva = parseFloat(data.capacidad_kva);
  data.capacidad_kw = parseFloat(data.capacidad_kw);
  data.horas_operacion = parseFloat(data.horas_operacion || 0);
  if (data.motor_potencia_hp) data.motor_potencia_hp = parseFloat(data.motor_potencia_hp);

  try {
    const res = await fetch(`/api/plantas/${plantaId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Error al actualizar la planta');

    closeModal('modal-editar-planta');
    await fetchAllPlantas();
    await fetchStats();

    // Si estábamos viendo la planta, recargar su ficha
    if (state.currentView === 'planta-detail') {
      openPlanta(plantaId, false);
    } else if (state.currentView === 'sede-plantas' && state.currentSede) {
      openSede(state.currentSede.id, false);
    }

    showToast('✅ ¡Ficha técnica actualizada en la base de datos!', 'success');
  } catch (err) {
    showToast('Error al actualizar planta: ' + err.message, 'danger');
  }
}

function promptDeletePlanta(plantaId, nombrePlanta) {
  state.plantaToDeleteId = plantaId;
  document.getElementById('delete-planta-nombre').textContent = `"${nombrePlanta}"`;
  openModal('modal-confirmar-eliminar');
}

async function confirmDeletePlanta() {
  const plantaId = state.plantaToDeleteId;
  if (!plantaId) return;

  try {
    const res = await fetch(`/api/plantas/${plantaId}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error('Error al eliminar planta');

    closeModal('modal-confirmar-eliminar');
    state.plantaToDeleteId = null;

    await fetchAllPlantas();
    await fetchStats();

    showToast('🗑️ Planta eliminada de la base de datos.', 'info');

    // Redireccionar a la sede correspondiente
    if (state.currentSede) {
      navigateToHash(`#/sede/${state.currentSede.id}`);
    } else {
      navigateToHash('#/sedes');
    }
  } catch (err) {
    showToast('Error al eliminar planta: ' + err.message, 'danger');
  }
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
    container.innerHTML = `
      <div style="text-align: center; color: var(--text-muted); padding: 3rem; background: #fff; border-radius: var(--radius-lg); border: 1px solid var(--border-light);">
        No hay casos registrados aún.<br><br>
        <button class="btn btn-primary" onclick="openModal('modal-nuevo-caso')">➕ Registrar el Primer Caso</button>
      </div>`;
    return;
  }

  container.innerHTML = cases.map(c => `
    <div class="trabajo-card" style="border-left: 3px solid var(--primary);">
      <div class="trabajo-header">
        <div class="trabajo-meta">
          <span class="badge-code">Caso #${c.id}</span>
          <span class="tech">👨‍🔧 Técnico: ${c.tecnico}</span>
          <span class="badge-code">${c.planta_modelo}</span>
        </div>
        <div style="font-size: 0.8rem; color: var(--text-muted);">
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
        <span style="font-size: 0.8rem; color: var(--text-muted);">
          👍 Validado útil: <strong>${c.utilidad_count || 1}</strong> veces
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
      showToast('👍 ¡Gracias! La experiencia ha sido revalidada.', 'success');
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
    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 3rem; background: #fff; border-radius: var(--radius-lg); border: 1px solid var(--border-light);">
        No hay manuales cargados aún.
      </div>`;
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

  appendChatBubble('user', message);
  input.value = '';

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

    if (!res.ok) throw new Error('Error al procesar consulta');
    const data = await res.json();

    const botBubble = document.getElementById(typingId);
    if (botBubble) {
      botBubble.innerHTML = marked.parse(data.response || 'Sin respuesta.');
    }
  } catch (err) {
    const botBubble = document.getElementById(typingId);
    if (botBubble) {
      botBubble.innerHTML = `<span style="color: var(--danger);">⚠️ Dificultad temporal con el servicio de IA. Intenta nuevamente.</span>`;
    }
  }

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
      Estoy listo para responder en base a las características de motor, alternador, controlador y plan de mantenimiento.
    </div>
  `;
}

// =========================================================================
// MODALES Y FORMULARIOS
// =========================================================================

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('open');
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('open');
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
    showToast('✅ ¡Sede registrada exitosamente en la base de datos!', 'success');
  } catch (err) {
    showToast('Error al registrar sede: ' + err.message, 'danger');
  }
}

// 2. Submit Nueva Planta (GUARDADA DE FORMA PERMANENTE EN BASE DE DATOS)
async function handleCreatePlanta(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

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
    const result = await res.json();
    const newPlantaId = result.id;

    closeModal('modal-nueva-planta');
    form.reset();
    
    // Actualizar datos globales
    await fetchAllPlantas();
    await fetchStats();

    // Redireccionar inmediatamente a la nueva planta para verla persistida
    navigateToHash(`#/planta/${newPlantaId}`);
    showToast('✅ ¡Planta guardada exitosamente en la base de datos!', 'success');
  } catch (err) {
    showToast('Error al registrar planta: ' + err.message, 'danger');
  }
}

// 3. Submit Trabajo con Fotos
async function handleCreateTrabajo(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const submitBtn = document.getElementById('btn-submit-trabajo');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Guardando...';

  const plantaId = formData.get('planta_id');

  try {
    const res = await fetch(`/api/plantas/${plantaId}/trabajos`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error('Error al guardar trabajo');

    closeModal('modal-nuevo-trabajo');
    form.reset();
    submitBtn.disabled = false;
    submitBtn.textContent = 'Guardar Trabajo y Fotos';

    showToast('✅ ¡Trabajo y fotos registrados en la base de datos!', 'success');
    openPlanta(plantaId, false);
  } catch (err) {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Guardar Trabajo y Fotos';
    showToast('Error: ' + err.message, 'danger');
  }
}

// 4. Submit Caso de Campo
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
    showToast('✅ ¡Caso indexado! El Asistente IA ya aprendió esta solución.', 'success');
    fetchCases();
  } catch (err) {
    showToast('Error: ' + err.message, 'danger');
  }
}

// 5. Submit Manual PDF
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
    showToast('✅ ¡Manual PDF subido e indexado!', 'success');
    fetchManuals();
  } catch (err) {
    showToast('Error: ' + err.message, 'danger');
  }
}
