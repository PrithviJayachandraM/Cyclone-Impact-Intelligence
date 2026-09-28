const mapElement = document.querySelector("#map");
const selector = document.querySelector("#cyclone");
const metadata = document.querySelector("#metadata");
const controls = document.querySelector("#layer-controls");
const riskDetail = document.querySelector("#risk-detail");
const layerColors = { rainfall: "#2563eb", elevation: "#15803d", population: "#9333ea" };
const bandColors = { low: "#22c55e", medium: "#f59e0b", high: "#dc2626" };
let currentTrack, currentLocations, currentRisk, activeLayers = new Set(), showRisk = true;

function layerColor(layerId) { return layerColors[layerId] || "#475569"; }
function riskFor(locationId) { return currentRisk.features.find(feature => feature.properties.location_id === locationId); }
function allCoordinates() { return [...currentTrack.features.filter(feature => feature.geometry.type === "Point").map(feature => feature.geometry.coordinates), ...currentLocations.features.flatMap(feature => feature.geometry.coordinates[0])]; }
function polygonPoints(location, x, y) { return location.geometry.coordinates[0].map(point => `${x(point[0])},${y(point[1])}`).join(" "); }

function coordinateFallback() {
  const coordinates = allCoordinates(), width = 900, height = 520, padding = 45;
  const longitudes = coordinates.map(point => point[0]), latitudes = coordinates.map(point => point[1]);
  const minLon = Math.min(...longitudes), maxLon = Math.max(...longitudes), minLat = Math.min(...latitudes), maxLat = Math.max(...latitudes);
  const x = value => padding + ((value - minLon) / (maxLon - minLon || 1)) * (width - 2 * padding);
  const y = value => height - (padding + ((value - minLat) / (maxLat - minLat || 1)) * (height - 2 * padding));
  const points = currentTrack.features.filter(feature => feature.geometry.type === "Point");
  const trackPath = points.map(point => `${x(point.geometry.coordinates[0])},${y(point.geometry.coordinates[1])}`).join(" ");
  const contextual = currentLocations.features.flatMap(location => [...activeLayers].map(layerId => `<polygon points="${polygonPoints(location, x, y)}" fill="${layerColor(layerId)}" fill-opacity="0.12" stroke="${layerColor(layerId)}" stroke-width="1"/>`)).join("");
  const heatmap = showRisk ? currentLocations.features.map(location => { const risk = riskFor(location.properties.location_id); return `<polygon data-location="${location.properties.location_id}" points="${polygonPoints(location, x, y)}" fill="${bandColors[risk.properties.band]}" fill-opacity="0.38" stroke="${bandColors[risk.properties.band]}" stroke-width="3"><title>${location.properties.name}: ${risk.properties.risk_score}/100 (${risk.properties.band})</title></polygon>`; }).join("") : "";
  mapElement.innerHTML = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="100%" role="img" aria-label="Coordinate plot of observed cyclone track and risk heatmap"><rect width="100%" height="100%" fill="#edf5fb"/>${contextual}${heatmap}<polyline points="${trackPath}" fill="none" stroke="#b62727" stroke-width="4"/>${points.map(point => `<circle cx="${x(point.geometry.coordinates[0])}" cy="${y(point.geometry.coordinates[1])}" r="6" fill="#b62727"><title>${point.properties.timestamp}</title></circle>`).join("")}<text x="20" y="30" fill="#48576a">Coordinate-map fallback (set up a browser-restricted Google Maps key for basemap tiles)</text></svg>`;
  mapElement.querySelectorAll("[data-location]").forEach(element => element.addEventListener("click", () => showRiskDetail(element.dataset.location)));
}

function googleMap() {
  const points = currentTrack.features.filter(feature => feature.geometry.type === "Point"), coordinates = points.map(point => ({ lng: point.geometry.coordinates[0], lat: point.geometry.coordinates[1] }));
  const map = new google.maps.Map(mapElement, { center: coordinates[Math.floor(coordinates.length / 2)], zoom: 5, mapTypeControl: false });
  new google.maps.Polyline({ path: coordinates, map, strokeColor: "#b62727", strokeWeight: 4 });
  coordinates.forEach((position, index) => new google.maps.Marker({ position, map, title: points[index].properties.timestamp }));
  currentLocations.features.forEach(location => {
    const risk = riskFor(location.properties.location_id), paths = location.geometry.coordinates[0].map(([lng, lat]) => ({ lng, lat }));
    [...activeLayers].forEach(layerId => new google.maps.Polygon({ paths, map, fillColor: layerColor(layerId), fillOpacity: 0.12, strokeColor: layerColor(layerId), strokeWeight: 1 }));
    if (showRisk) { const polygon = new google.maps.Polygon({ paths, map, fillColor: bandColors[risk.properties.band], fillOpacity: 0.38, strokeColor: bandColors[risk.properties.band], strokeWeight: 3 }); polygon.addListener("click", () => showRiskDetail(location.properties.location_id)); }
  });
}

function renderMap() { window.google?.maps ? googleMap() : coordinateFallback(); }
function checkbox(labelText, checked, change) { const label = document.createElement("label"), input = document.createElement("input"); input.type = "checkbox"; input.checked = checked; input.addEventListener("change", () => change(input.checked)); label.append(input, ` ${labelText}`); return label; }
function renderControls(layers) {
  controls.replaceChildren();
  controls.append(checkbox("Baseline risk heatmap", true, checked => { showRisk = checked; renderMap(); }));
  layers.forEach(layer => { activeLayers.add(layer.layer_id); controls.append(checkbox(`${layer.name} (${layer.unit})`, true, checked => { checked ? activeLayers.add(layer.layer_id) : activeLayers.delete(layer.layer_id); renderMap(); })); const detail = document.createElement("div"); detail.className = "metadata"; detail.textContent = `${layer.source}; ${layer.observed_at}; ${layer.resolution}`; controls.append(detail); });
}

async function showRiskDetail(locationId) {
  const response = await fetch(`/locations/${encodeURIComponent(locationId)}/risk?cyclone_id=${encodeURIComponent(selector.value)}`), risk = await response.json();
  if (!response.ok) { riskDetail.textContent = risk.error; return; }
  riskDetail.replaceChildren(); const title = document.createElement("strong"), note = document.createElement("p"), list = document.createElement("ul");
  title.textContent = `Risk score: ${risk.risk_score}/100`; note.innerHTML = `<span class="band">${risk.band}</span> baseline risk; model ${risk.model_version}; valid ${risk.valid_time}.`;
  risk.feature_contributions.forEach(contribution => { const item = document.createElement("li"); item.textContent = `${contribution.name}: ${contribution.raw_value}; normalised ${contribution.normalised_value}; weight ${contribution.weight}; ${contribution.score_points} score points`; list.append(item); });
  riskDetail.append(title, note, list);
}

async function selectCyclone() {
  const event = JSON.parse(selector.selectedOptions[0].dataset.event); metadata.textContent = `${event.name} | ${event.basin} | source: ${event.source} | data timestamp: ${event.observed_at}`;
  [currentTrack, currentLocations, currentRisk] = await Promise.all([fetch(`/cyclones/${encodeURIComponent(event.cyclone_id)}/track`).then(response => response.json()), fetch(`/cyclones/${encodeURIComponent(event.cyclone_id)}/locations`).then(response => response.json()), fetch(`/cyclones/${encodeURIComponent(event.cyclone_id)}/risk`).then(response => response.json())]);
  const layers = await fetch(`/cyclones/${encodeURIComponent(event.cyclone_id)}/layers`).then(response => response.json()); activeLayers = new Set(); showRisk = true; renderControls(layers); renderMap();
}

async function start() {
  const mapConfig = await fetch("/map-config").then(response => response.json());
  if (mapConfig.google_maps_api_key) await new Promise((resolve, reject) => { const script = document.createElement("script"); script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(mapConfig.google_maps_api_key)}`; script.onload = resolve; script.onerror = reject; document.head.append(script); });
  const cyclones = await fetch("/cyclones").then(response => response.json()); cyclones.forEach(event => { const option = new Option(event.name, event.cyclone_id); option.dataset.event = JSON.stringify(event); selector.add(option); }); selector.addEventListener("change", selectCyclone); await selectCyclone();
}
start().catch(error => { mapElement.textContent = `Unable to load cyclone risk data: ${error.message}`; });
