const mapElement = document.querySelector("#map");
const selector = document.querySelector("#cyclone");
const metadata = document.querySelector("#metadata");
const controls = document.querySelector("#layer-controls");
const featureVector = document.querySelector("#feature-vector");
const layerColors = { rainfall: "#2563eb", elevation: "#15803d", population: "#9333ea" };
let currentTrack, currentLocations, activeLayers = new Set();

function layerColor(layerId) { return layerColors[layerId] || "#475569"; }
function allCoordinates(track, locations) {
  return [...track.features.filter(feature => feature.geometry.type === "Point").map(feature => feature.geometry.coordinates), ...locations.features.flatMap(feature => feature.geometry.coordinates[0])];
}

function coordinateFallback(track, locations) {
  const coordinates = allCoordinates(track, locations), width = 900, height = 520, padding = 45;
  const longitudes = coordinates.map(point => point[0]), latitudes = coordinates.map(point => point[1]);
  const minLon = Math.min(...longitudes), maxLon = Math.max(...longitudes), minLat = Math.min(...latitudes), maxLat = Math.max(...latitudes);
  const x = value => padding + ((value - minLon) / (maxLon - minLon || 1)) * (width - 2 * padding);
  const y = value => height - (padding + ((value - minLat) / (maxLat - minLat || 1)) * (height - 2 * padding));
  const points = track.features.filter(feature => feature.geometry.type === "Point");
  const trackPath = points.map(point => `${x(point.geometry.coordinates[0])},${y(point.geometry.coordinates[1])}`).join(" ");
  const polygons = locations.features.flatMap(location => [...activeLayers].map(layerId => `<polygon data-location="${location.properties.location_id}" points="${location.geometry.coordinates[0].map(point => `${x(point[0])},${y(point[1])}`).join(" ")}" fill="${layerColor(layerId)}" fill-opacity="0.18" stroke="${layerColor(layerId)}" stroke-width="2"><title>${location.properties.name}: ${layerId} ${location.properties.feature_values[layerId]}</title></polygon>`)).join("");
  mapElement.innerHTML = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="100%" role="img" aria-label="Coordinate plot of observed cyclone track and selected contextual layers"><rect width="100%" height="100%" fill="#edf5fb"/>${polygons}<polyline points="${trackPath}" fill="none" stroke="#b62727" stroke-width="4"/>${points.map(point => `<circle cx="${x(point.geometry.coordinates[0])}" cy="${y(point.geometry.coordinates[1])}" r="6" fill="#b62727"><title>${point.properties.timestamp}</title></circle>`).join("")}<text x="20" y="30" fill="#48576a">Coordinate-map fallback (set up a browser-restricted Google Maps key for basemap tiles)</text></svg>`;
  mapElement.querySelectorAll("[data-location]").forEach(element => element.addEventListener("click", () => showFeatureVector(element.dataset.location)));
}

function googleMap(track, locations) {
  const points = track.features.filter(feature => feature.geometry.type === "Point");
  const coordinates = points.map(point => ({ lng: point.geometry.coordinates[0], lat: point.geometry.coordinates[1] }));
  const map = new google.maps.Map(mapElement, { center: coordinates[Math.floor(coordinates.length / 2)], zoom: 5, mapTypeControl: false });
  new google.maps.Polyline({ path: coordinates, map, strokeColor: "#b62727", strokeWeight: 4 });
  coordinates.forEach((position, index) => new google.maps.Marker({ position, map, title: points[index].properties.timestamp }));
  locations.features.forEach(location => [...activeLayers].forEach(layerId => {
    const polygon = new google.maps.Polygon({ paths: location.geometry.coordinates[0].map(([lng, lat]) => ({ lng, lat })), map, fillColor: layerColor(layerId), fillOpacity: 0.18, strokeColor: layerColor(layerId), strokeWeight: 2 });
    polygon.addListener("click", () => showFeatureVector(location.properties.location_id));
  }));
}

function renderMap() { window.google?.maps ? googleMap(currentTrack, currentLocations) : coordinateFallback(currentTrack, currentLocations); }
function renderControls(layers) {
  controls.replaceChildren();
  layers.forEach(layer => {
    activeLayers.add(layer.layer_id);
    const label = document.createElement("label"), checkbox = document.createElement("input"), detail = document.createElement("div");
    checkbox.type = "checkbox"; checkbox.checked = true;
    checkbox.addEventListener("change", () => { checkbox.checked ? activeLayers.add(layer.layer_id) : activeLayers.delete(layer.layer_id); renderMap(); });
    label.append(checkbox, ` ${layer.name} (${layer.unit})`); detail.className = "metadata"; detail.textContent = `${layer.source}; ${layer.observed_at}; ${layer.resolution}`;
    controls.append(label, detail);
  });
}

async function showFeatureVector(locationId) {
  const response = await fetch(`/locations/${encodeURIComponent(locationId)}/features?cyclone_id=${encodeURIComponent(selector.value)}`), vector = await response.json();
  if (!response.ok) { featureVector.textContent = vector.error; return; }
  featureVector.replaceChildren(); const title = document.createElement("strong"), list = document.createElement("ul"); title.textContent = vector.location.name;
  vector.features.forEach(feature => { const item = document.createElement("li"); item.textContent = `${feature.name}: ${feature.value} ${feature.unit} — ${feature.source}; ${feature.observed_at}; ${feature.resolution}`; list.append(item); });
  featureVector.append(title, list);
}

async function selectCyclone() {
  const event = JSON.parse(selector.selectedOptions[0].dataset.event);
  metadata.textContent = `${event.name} | ${event.basin} | source: ${event.source} | data timestamp: ${event.observed_at}`;
  [currentTrack, currentLocations] = await Promise.all([fetch(`/cyclones/${encodeURIComponent(event.cyclone_id)}/track`).then(response => response.json()), fetch(`/cyclones/${encodeURIComponent(event.cyclone_id)}/locations`).then(response => response.json())]);
  const layers = await fetch(`/cyclones/${encodeURIComponent(event.cyclone_id)}/layers`).then(response => response.json());
  activeLayers = new Set(); renderControls(layers); renderMap();
}

async function start() {
  const mapConfig = await fetch("/map-config").then(response => response.json());
  if (mapConfig.google_maps_api_key) await new Promise((resolve, reject) => { const script = document.createElement("script"); script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(mapConfig.google_maps_api_key)}`; script.onload = resolve; script.onerror = reject; document.head.append(script); });
  const cyclones = await fetch("/cyclones").then(response => response.json());
  cyclones.forEach(event => { const option = new Option(event.name, event.cyclone_id); option.dataset.event = JSON.stringify(event); selector.add(option); });
  selector.addEventListener("change", selectCyclone); await selectCyclone();
}
start().catch(error => { mapElement.textContent = `Unable to load historical tracks and contextual layers: ${error.message}`; });
