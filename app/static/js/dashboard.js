const mapElement = document.querySelector("#map");
let map = null;
let focusLayer = null;
let drawnItems = null;
let manualLocationMarker = null;

function showMapError(message) {
  if (!mapElement) return;
  mapElement.innerHTML = `<div class="map-error">${message}</div>`;
}

function initMap() {
  if (!mapElement) return;
  if (typeof L === "undefined") {
    showMapError("Mapa indisponível: biblioteca Leaflet não carregada.");
    return;
  }

  map = L.map("map").setView([-14.2, -51.9], 4);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap"
  }).addTo(map);
  L.control.scale({ imperial: false }).addTo(map);

  focusLayer = L.markerClusterGroup ? L.markerClusterGroup() : L.layerGroup();
  map.addLayer(focusLayer);

  drawnItems = new L.FeatureGroup();
  map.addLayer(drawnItems);

  if (L.Control?.Draw && L.Draw?.Event?.CREATED) {
    new L.Control.Draw({
      draw: { marker: false, circle: false, circlemarker: false, rectangle: true, polygon: true, polyline: false },
      edit: { featureGroup: drawnItems }
    }).addTo(map);

    map.on(L.Draw.Event.CREATED, async (event) => {
      drawnItems.clearLayers();
      drawnItems.addLayer(event.layer);
      const geojson = event.layer.toGeoJSON();
      await fetch("/api/areas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome: "Área desenhada", geometria: geojson })
      });
    });
  }
}

let lastFocos = [];
let chartState = null;
let chartBiome = null;
let lastSummary = null;
let loadProgressTimer = null;
let loadProgressValue = 0;

function isNarrowScreen() {
  return window.matchMedia("(max-width: 640px)").matches;
}

function buildParams() {
  const params = new URLSearchParams(new FormData(document.querySelector("#filters")));
  params.set("limite", "1200");
  for (const [key, value] of [...params.entries()]) {
    if (!value) params.delete(key);
  }
  return params;
}

function fmt(value) {
  return value === null || value === undefined ? "--" : value;
}

function setLoadProgress(value, label) {
  const progress = document.querySelector("#load-progress");
  const bar = document.querySelector("#load-progress-bar");
  const percent = document.querySelector("#load-progress-percent");
  const text = document.querySelector("#load-progress-label");
  const track = progress?.querySelector(".load-progress-track");
  if (!progress || !bar || !percent || !text || !track) return;
  loadProgressValue = Math.max(0, Math.min(100, Math.round(value)));
  progress.hidden = false;
  progress.classList.remove("error", "complete");
  bar.style.width = `${loadProgressValue}%`;
  percent.textContent = `${loadProgressValue}%`;
  text.textContent = label;
  track.setAttribute("aria-valuenow", String(loadProgressValue));
}

function startLoadProgress(label = "Consultando base de dados...") {
  const button = document.querySelector("#update-dashboard");
  if (button) {
    button.disabled = true;
    button.textContent = "Atualizando...";
  }
  clearInterval(loadProgressTimer);
  setLoadProgress(8, label);
  loadProgressTimer = setInterval(() => {
    const next = loadProgressValue < 55 ? loadProgressValue + 7 : loadProgressValue < 86 ? loadProgressValue + 3 : loadProgressValue;
    setLoadProgress(Math.min(next, 88), "Baixando e processando dados...");
  }, 500);
}

function finishLoadProgress(label = "Dados atualizados.") {
  clearInterval(loadProgressTimer);
  setLoadProgress(100, label);
  document.querySelector("#load-progress")?.classList.add("complete");
  const button = document.querySelector("#update-dashboard");
  if (button) {
    button.disabled = false;
    button.textContent = "Atualizar painel";
  }
  setTimeout(() => {
    const progress = document.querySelector("#load-progress");
    if (progress) progress.hidden = true;
  }, 1200);
}

function failLoadProgress(label = "Falha ao atualizar dados.") {
  clearInterval(loadProgressTimer);
  setLoadProgress(100, label);
  document.querySelector("#load-progress")?.classList.add("error");
  const button = document.querySelector("#update-dashboard");
  if (button) {
    button.disabled = false;
    button.textContent = "Atualizar painel";
  }
}

function popup(foco) {
  return `
    <strong>${fmt(foco.municipio)} - ${fmt(foco.estado)}</strong><br>
    Bioma: ${fmt(foco.bioma)}<br>
    Satélite: ${fmt(foco.satelite)}<br>
    Fonte: ${fmt(foco.fonte)}<br>
    Data: ${fmt(foco.data_hora_gmt)}<br>
    FRP: ${fmt(foco.frp)}<br>
    Risco: ${fmt(foco.risco_fogo)}<br>
    Precipitação: ${fmt(foco.precipitacao)}<br>
    Dias sem chuva: ${fmt(foco.numero_dias_sem_chuva)}<br>
    Lat/Lon: ${foco.lat}, ${foco.lon}
  `;
}

function setManualStatus(message, type = "") {
  const status = document.querySelector("#manual-status");
  if (!status) return;
  status.textContent = message;
  status.className = `manual-status ${type}`.trim();
}

function manualPayloadFromForm() {
  const form = document.querySelector("#manual-focus-form");
  const data = Object.fromEntries(new FormData(form).entries());
  for (const key of Object.keys(data)) {
    if (data[key] === "") delete data[key];
  }
  return data;
}

function setManualCoordinates(lat, lon) {
  const form = document.querySelector("#manual-focus-form");
  form.elements.lat.value = Number(lat).toFixed(6);
  form.elements.lon.value = Number(lon).toFixed(6);
  if (map && typeof L !== "undefined") {
    const latlng = [Number(lat), Number(lon)];
    if (!manualLocationMarker) {
      manualLocationMarker = L.marker(latlng).addTo(map).bindPopup("Localização capturada");
    } else {
      manualLocationMarker.setLatLng(latlng);
    }
    map.setView(latlng, Math.max(map.getZoom(), 12));
    manualLocationMarker.openPopup();
  }
}

function captureLocation() {
  if (!navigator.geolocation) {
    setManualStatus("Geolocalização não disponível neste navegador.", "error");
    return;
  }
  setManualStatus("Solicitando localização do dispositivo...");
  navigator.geolocation.getCurrentPosition(
    (position) => {
      setManualCoordinates(position.coords.latitude, position.coords.longitude);
      setManualStatus(`Localização capturada com precisão aproximada de ${Math.round(position.coords.accuracy)} m.`, "success");
    },
    (error) => {
      setManualStatus(`Não foi possível capturar a localização: ${error.message}`, "error");
    },
    { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 }
  );
}

async function saveManualFocus(event) {
  event.preventDefault();
  setManualStatus("Salvando foco manual no banco...");
  const response = await fetch("/api/focos/manual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(manualPayloadFromForm())
  });
  const payload = await response.json();
  if (!payload.sucesso) {
    setManualStatus(payload.erro || "Falha ao salvar foco manual.", "error");
    return;
  }
  setManualStatus("Foco manual salvo no PostgreSQL.", "success");
  await loadDashboard();
}

async function cloneCurrentBase() {
  setManualStatus("Clonando base atual para o PostgreSQL...");
  const params = buildParams();
  params.delete("limite");
  const response = await fetch(`/api/queimadas/clonar-base?${params}`, { method: "POST" });
  const payload = await response.json();
  if (!payload.sucesso) {
    setManualStatus(payload.erro || "Falha ao clonar base atual.", "error");
    return;
  }
  setManualStatus(
    `Base clonada: ${payload.dados.criados} novos e ${payload.dados.atualizados} atualizados.`,
    "success"
  );
  await loadDashboard();
}

function renderFocos(focos) {
  if (!map || !focusLayer || typeof L === "undefined") return;
  focusLayer.clearLayers();
  const markerIcon = L.divIcon({
    className: "fire-marker",
    html: "",
    iconSize: [16, 16],
    iconAnchor: [8, 8],
    popupAnchor: [0, -8]
  });
  focos.forEach((foco) => {
    const marker = L.marker([foco.lat, foco.lon], { icon: markerIcon }).bindPopup(popup(foco));
    focusLayer.addLayer(marker);
  });
  const status = document.querySelector("#map-data-status");
  if (status) {
    status.textContent = focos.length === 1 ? "1 foco no mapa" : `${focos.length} focos no mapa`;
  }
}

function countBy(focos, field) {
  return focos.reduce((acc, foco) => {
    const key = foco[field] || "Não informado";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

function renderChart(canvasId, currentChart, data, color) {
  if (typeof Chart === "undefined") return currentChart;
  const mobile = isNarrowScreen();
  const labels = Object.keys(data).slice(0, mobile ? 8 : 12);
  const values = labels.map((label) => data[label]);
  if (currentChart) currentChart.destroy();
  return new Chart(document.getElementById(canvasId), {
    type: "bar",
    data: { labels, datasets: [{ data: values, backgroundColor: color }] },
    options: {
      indexAxis: mobile ? "y" : "x",
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { intersect: false, mode: "nearest" }
      },
      responsive: true,
      scales: {
        x: {
          beginAtZero: true,
          ticks: {
            maxRotation: mobile ? 0 : 45,
            autoSkip: true,
            font: { size: mobile ? 10 : 12 }
          }
        },
        y: {
          beginAtZero: !mobile,
          ticks: {
            autoSkip: false,
            font: { size: mobile ? 10 : 12 }
          }
        }
      }
    }
  });
}

function renderCharts(summary) {
  chartState = renderChart("chart-state", chartState, summary.por_estado, "#1f7a4a");
  chartBiome = renderChart("chart-biome", chartBiome, summary.por_bioma, "#f97316");
}

function renderTable(focos) {
  const tbody = document.querySelector("#focus-table");
  tbody.innerHTML = focos.slice(0, 80).map((foco) => `
    <tr>
      <td>${fmt(foco.data_hora_gmt)}</td>
      <td>${fmt(foco.municipio)}</td>
      <td>${fmt(foco.estado)}</td>
      <td>${fmt(foco.bioma)}</td>
      <td>${fmt(foco.satelite)}</td>
      <td>${fmt(foco.frp)}</td>
    </tr>
  `).join("");
}

async function loadDashboard() {
  startLoadProgress("Preparando consulta...");
  const params = buildParams();
  try {
    setLoadProgress(18, "Enviando filtros para a API...");
    const summaryPromise = fetch(`/api/queimadas/resumo?${params}`);
    const focusPromise = fetch(`/api/queimadas?${params}`);
    const [summaryRes, focusRes] = await Promise.all([summaryPromise, focusPromise]);
    setLoadProgress(78, "Normalizando focos de calor...");
    const summary = await summaryRes.json();
    const focus = await focusRes.json();
    if (!summary.sucesso || !focus.sucesso) {
      const errorMessage = summary.erro || focus.erro || "Falha ao consultar fontes.";
      document.querySelector("#source-status").textContent = errorMessage;
      const status = document.querySelector("#map-data-status");
      if (status) status.textContent = "Focos indisponíveis";
      failLoadProgress(`Falha: ${errorMessage}`);
      return;
    }
    setLoadProgress(90, "Atualizando mapa, gráficos e tabela...");
    lastSummary = summary.dados;
    lastFocos = focus.dados.focos;
    document.querySelector("#metric-total").textContent = summary.dados.total_focos;
    document.querySelector("#metric-24h").textContent = summary.dados.focos_ultimas_24h;
    document.querySelector("#metric-frp").textContent = summary.dados.frp_medio ? summary.dados.frp_medio.toFixed(2) : "--";
    document.querySelector("#metric-updated").textContent = new Date(summary.dados.ultima_atualizacao).toLocaleString("pt-BR");
    renderFocos(lastFocos);
    renderTable(lastFocos);
    renderCharts(summary.dados);
    if (map) setTimeout(() => map.invalidateSize(), 100);
    finishLoadProgress("Dados atualizados.");
  } catch (error) {
    const errorMessage = error.message || "Falha ao consultar fontes.";
    document.querySelector("#source-status").textContent = errorMessage;
    const status = document.querySelector("#map-data-status");
    if (status) status.textContent = "Focos indisponíveis";
    failLoadProgress(`Falha: ${errorMessage}`);
  }
}

async function loadStatus() {
  const response = await fetch("/api/fontes/status");
  const payload = await response.json();
  if (!payload.sucesso) return;
  const inpe = payload.dados.inpe_bdqueimadas.online ? "INPE online" : "INPE indisponível";
  const bdc = payload.dados.brazil_data_cube.online ? "BDC online" : "BDC indisponível";
  document.querySelector("#source-status").textContent = `${inpe} | ${bdc}`;
}

document.querySelector("#filters").addEventListener("submit", (event) => {
  event.preventDefault();
  loadDashboard();
});

document.querySelector("#capture-location")?.addEventListener("click", captureLocation);
document.querySelector("#manual-focus-form")?.addEventListener("submit", saveManualFocus);
document.querySelector("#clone-current-base")?.addEventListener("click", cloneCurrentBase);

document.querySelector("#export-csv").addEventListener("click", () => {
  const rows = [["data_hora_gmt", "municipio", "estado", "bioma", "satelite", "frp", "lat", "lon"]];
  lastFocos.forEach((f) => rows.push(rows[0].map((key) => f[key] ?? "")));
  const csv = rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "focos_observa_brasil.csv";
  link.click();
  URL.revokeObjectURL(url);
});

let resizeTimer = null;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (map) map.invalidateSize();
    if (lastSummary) renderCharts(lastSummary);
  }, 180);
});

initMap();
loadStatus();
loadDashboard();
