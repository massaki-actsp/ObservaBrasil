const mapElement = document.querySelector("#map");
let map = null;
let focusLayer = null;
let drawnItems = null;

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

function popup(foco) {
  return `
    <strong>${fmt(foco.municipio)} - ${fmt(foco.estado)}</strong><br>
    Bioma: ${fmt(foco.bioma)}<br>
    Satélite: ${fmt(foco.satelite)}<br>
    Data: ${fmt(foco.data_hora_gmt)}<br>
    FRP: ${fmt(foco.frp)}<br>
    Risco: ${fmt(foco.risco_fogo)}<br>
    Precipitação: ${fmt(foco.precipitacao)}<br>
    Dias sem chuva: ${fmt(foco.numero_dias_sem_chuva)}<br>
    Lat/Lon: ${foco.lat}, ${foco.lon}
  `;
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
  const params = buildParams();
  const [summaryRes, focusRes] = await Promise.all([
    fetch(`/api/queimadas/resumo?${params}`),
    fetch(`/api/queimadas?${params}`)
  ]);
  const summary = await summaryRes.json();
  const focus = await focusRes.json();
  if (!summary.sucesso || !focus.sucesso) {
    document.querySelector("#source-status").textContent = summary.erro || focus.erro || "Falha ao consultar fontes.";
    const status = document.querySelector("#map-data-status");
    if (status) status.textContent = "Focos indisponíveis";
    return;
  }
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
