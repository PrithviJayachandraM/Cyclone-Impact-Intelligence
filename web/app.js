const mapElement = document.querySelector("#map");
const selector = document.querySelector("#cyclone");
const metadata = document.querySelector("#metadata");

function coordinateFallback(points) {
  const width = 900, height = 520, padding = 45;
  const longitudes = points.map(point => point.geometry.coordinates[0]);
  const latitudes = points.map(point => point.geometry.coordinates[1]);
  const minLon = Math.min(...longitudes), maxLon = Math.max(...longitudes);
  const minLat = Math.min(...latitudes), maxLat = Math.max(...latitudes);
  const scale = (value, min, max, size) => padding + ((value - min) / (max - min || 1)) * (size - 2 * padding);
  const coordinates = points.map(point => `${scale(point.geometry.coordinates[0], minLon, maxLon, width)},${height - scale(point.geometry.coordinates[1], minLat, maxLat, height)}`).join(" ");
  mapElement.innerHTML = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="100%" role="img" aria-label="Coordinate plot of observed cyclone track"><rect width="100%" height="100%" fill="#edf5fb"/><polyline points="${coordinates}" fill="none" stroke="#b62727" stroke-width="4"/>${points.map(point => { const [lon, lat] = point.geometry.coordinates; return `<circle cx="${scale(lon,minLon,maxLon,width)}" cy="${height - scale(lat,minLat,maxLat,height)}" r="6" fill="#b62727"><title>${point.properties.timestamp}</title></circle>`; }).join("")}<text x="20" y="30" fill="#48576a">Coordinate-map fallback (set up a browser-restricted Google Maps key for basemap tiles)</text></svg>`;
}

function renderTrack(track) {
  const points = track.features.filter(feature => feature.geometry.type === "Point");
  if (!window.google?.maps) return coordinateFallback(points);
  const coordinates = points.map(point => ({ lng: point.geometry.coordinates[0], lat: point.geometry.coordinates[1] }));
  const map = new google.maps.Map(mapElement, { center: coordinates[Math.floor(coordinates.length / 2)], zoom: 5, mapTypeControl: false });
  new google.maps.Polyline({ path: coordinates, map, strokeColor: "#b62727", strokeWeight: 4 });
  coordinates.forEach((position, index) => new google.maps.Marker({ position, map, title: points[index].properties.timestamp }));
}

async function selectCyclone() {
  const event = JSON.parse(selector.selectedOptions[0].dataset.event);
  metadata.textContent = `${event.name} | ${event.basin} | source: ${event.source} | data timestamp: ${event.observed_at}`;
  const track = await fetch(`/cyclones/${encodeURIComponent(event.cyclone_id)}/track`).then(response => response.json());
  renderTrack(track);
}

async function start() {
  const mapConfig = await fetch("/map-config").then(response => response.json());
  if (mapConfig.google_maps_api_key) {
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(mapConfig.google_maps_api_key)}`;
      script.onload = resolve; script.onerror = reject; document.head.append(script);
    });
  }
  const cyclones = await fetch("/cyclones").then(response => response.json());
  cyclones.forEach(event => {
    const option = new Option(event.name, event.cyclone_id);
    option.dataset.event = JSON.stringify(event);
    selector.add(option);
  });
  selector.addEventListener("change", selectCyclone);
  await selectCyclone();
}

start().catch(error => { mapElement.textContent = `Unable to load historical tracks: ${error.message}`; });
