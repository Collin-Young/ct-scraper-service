const API_INPUT = document.getElementById("api-base");
const REFRESH_BTN = document.getElementById("refresh");
const STATUS = document.getElementById("status");
const TABLE_BODY = document.getElementById("cases-body");
const COUNTY_FILTER = document.getElementById("county-filter");
const TOWN_FILTER = document.getElementById("town-filter");
const DATE_FROM = document.getElementById("date-from");
const DATE_TO = document.getElementById("date-to");
const APPLY_FILTERS = document.getElementById("apply-filters");
const CLEAR_FILTERS = document.getElementById("clear-filters");
const LAST_UPDATED = document.getElementById("last-updated");
const MAP_CONTAINER = document.getElementById("map");

const DEFAULT_API = `${window.location.origin.replace(/\/$/, "")}/api`;
const STORAGE_KEY = "ct-scraper-api-base";
const HOURS_LOOKBACK = 24;
const LIMIT = 100;
let cachedCases = [];
let map;
let markersLayer;

// Town to county mapping
const TOWN_TO_COUNTY = {
  "Andover": "Tolland", "Ansonia": "New Haven", "Ashford": "Windham", "Avon": "Hartford",
  "Barkhamsted": "Litchfield", "Beacon Falls": "New Haven", "Berlin": "Hartford", "Bethany": "New Haven",
  "Bethel": "Fairfield", "Bethlehem": "Litchfield", "Bloomfield": "Hartford", "Bolton": "Tolland",
  "Bozrah": "New London", "Branford": "New Haven", "Bridgeport": "Fairfield", "Bridgewater": "Litchfield",
  "Bristol": "Hartford", "Brookfield": "Fairfield", "Brooklyn": "Windham", "Burlington": "Hartford",
  "Canaan": "Litchfield", "Canterbury": "Windham", "Canton": "Hartford", "Chaplin": "Windham",
  "Cheshire": "New Haven", "Chester": "Middlesex", "Clinton": "Middlesex", "Colchester": "New London",
  "Colebrook": "Litchfield", "Columbia": "Tolland", "Cornwall": "Litchfield", "Coventry": "Tolland",
  "Cromwell": "Middlesex", "Danbury": "Fairfield", "Darien": "Fairfield", "Deep River": "Middlesex",
  "Derby": "New Haven", "Durham": "Middlesex", "Eastford": "Windham", "East Granby": "Hartford",
  "East Haddam": "Middlesex", "East Hampton": "Middlesex", "East Hartford": "Hartford", "East Haven": "New Haven",
  "East Lyme": "New London", "Easton": "Fairfield", "East Windsor": "Hartford", "Ellington": "Tolland",
  "Enfield": "Hartford", "Essex": "Middlesex", "Fairfield": "Fairfield", "Farmington": "Hartford",
  "Franklin": "New London", "Glastonbury": "Hartford", "Goshen": "Litchfield", "Granby": "Hartford",
  "Greenwich": "Fairfield", "Griswold": "New London", "Groton": "New London", "Guilford": "New Haven",
  "Haddam": "Middlesex", "Hamden": "New Haven", "Hampton": "Windham", "Hartford": "Hartford",
  "Hartland": "Hartford", "Harwinton": "Litchfield", "Hebron": "Tolland", "Kent": "Litchfield",
  "Killingly": "Windham", "Killingworth": "Middlesex", "Lebanon": "New London", "Ledyard": "New London",
  "Lisbon": "New London", "Litchfield": "Litchfield", "Lyme": "New London", "Madison": "New Haven",
  "Manchester": "Hartford", "Mansfield": "Tolland", "Marlborough": "Hartford", "Meriden": "New Haven",
  "Middlebury": "New Haven", "Middlefield": "Middlesex", "Middletown": "Middlesex", "Milford": "New Haven",
  "Monroe": "Fairfield", "Montville": "New London", "Morris": "Litchfield", "Naugatuck": "New Haven",
  "New Britain": "Hartford", "New Canaan": "Fairfield", "New Fairfield": "Fairfield", "New Hartford": "Litchfield",
  "New Haven": "New Haven", "Newington": "Hartford", "New London": "New London", "New Milford": "Litchfield",
  "Newtown": "Fairfield", "Norfolk": "Litchfield", "North Branford": "New Haven", "North Canaan": "Litchfield",
  "North Haven": "New Haven", "North Stonington": "New London", "Norwalk": "Fairfield", "Norwich": "New London",
  "Old Lyme": "New London", "Old Saybrook": "Middlesex", "Orange": "New Haven", "Oxford": "New Haven",
  "Plainfield": "Windham", "Plainville": "Hartford", "Plymouth": "Litchfield", "Pomfret": "Windham",
  "Portland": "Middlesex", "Preston": "New London", "Prospect": "New Haven", "Putnam": "Windham",
  "Redding": "Fairfield", "Ridgefield": "Fairfield", "Rocky Hill": "Hartford", "Roxbury": "Litchfield",
  "Salem": "New London", "Salisbury": "Litchfield", "Scotland": "Windham", "Seymour": "New Haven",
  "Sharon": "Litchfield", "Shelton": "Fairfield", "Sherman": "Fairfield", "Simsbury": "Hartford",
  "Somers": "Tolland", "Southbury": "New Haven", "Southington": "Hartford", "South Windsor": "Hartford",
  "Sprague": "New London", "Stafford": "Tolland", "Stamford": "Fairfield", "Sterling": "Windham",
  "Stonington": "New London", "Stratford": "Fairfield", "Suffield": "Hartford", "Thomaston": "Litchfield",
  "Thompson": "Windham", "Tolland": "Tolland", "Torrington": "Litchfield", "Trumbull": "Fairfield",
  "Union": "Tolland", "Vernon": "Tolland", "Voluntown": "New London", "Wallingford": "New Haven",
  "Warren": "Litchfield", "Washington": "Litchfield", "Waterbury": "New Haven", "Waterford": "New London",
  "Watertown": "Litchfield", "Westbrook": "Middlesex", "West Hartford": "Hartford", "West Haven": "New Haven",
  "Weston": "Fairfield", "Westport": "Fairfield", "Wethersfield": "Hartford", "Willington": "Tolland",
  "Wilton": "Fairfield", "Winchester": "Litchfield", "Windham": "Windham", "Windsor": "Hartford",
  "Windsor Locks": "Hartford", "Wolcott": "New Haven", "Woodbridge": "New Haven", "Woodbury": "Litchfield",
  "Woodstock": "Windham"
};

function initMap() {
  if (!MAP_CONTAINER) return;
  map = L.map(MAP_CONTAINER, {
    center: [41.6032, -73.0877],
    zoom: 8,
    scrollWheelZoom: false,
  });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(map);
  markersLayer = L.layerGroup().addTo(map);
}

function loadBaseUrl() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved && saved.startsWith("http")) {
    if (saved.includes("157.230.11.23")) {
      API_INPUT.value = DEFAULT_API;
      saveBaseUrl(DEFAULT_API);
    } else {
      API_INPUT.value = saved;
    }
  } else {
    API_INPUT.value = DEFAULT_API;
  }
}

function saveBaseUrl(value) {
  localStorage.setItem(STORAGE_KEY, value);
}

async function fetchCases() {
  let base = API_INPUT.value.trim();
  if (!base) {
    STATUS.textContent = "Provide a valid API base URL.";
    return;
  }
  base = base.replace(/\/$/, "");
  saveBaseUrl(base);

  const params = new URLSearchParams({ limit: LIMIT.toString() });

  // Add filter parameters
  const countyValue = COUNTY_FILTER.value.trim();
  if (countyValue) {
    params.set("county", countyValue);
  }

  const townValue = TOWN_FILTER.value.trim();
  if (townValue) {
    params.set("town", townValue);
  }

  const dateFromValue = DATE_FROM.value;
  if (dateFromValue) {
    params.set("date_from", dateFromValue);
  }

  const dateToValue = DATE_TO.value;
  if (dateToValue) {
    params.set("date_to", dateToValue);
  }

  STATUS.textContent = "Loading cases...";
  TABLE_BODY.innerHTML = "";

  try {
    const resp = await fetch(`${base}/cases?${params.toString()}`);
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    const data = await resp.json();
    cachedCases = Array.isArray(data) ? data : [];
    renderRows();
    STATUS.textContent = `Showing ${cachedCases.length} case(s) (max ${LIMIT})`;
    LAST_UPDATED.textContent = `Last updated ${new Date().toLocaleString()}`;
  } catch (err) {
    console.error(err);
    STATUS.textContent = `Error loading cases: ${err.message}`;
    cachedCases = [];
    TABLE_BODY.innerHTML = "<tr><td colspan='7'>No data available.</td></tr>";
    if (markersLayer) markersLayer.clearLayers();
  }
}

function renderMap(cases) {
  if (!map || !markersLayer) return;
  markersLayer.clearLayers();
  const bounds = [];

  cases.forEach((row) => {
    if (row.latitude == null || row.longitude == null) return;
    const marker = L.circleMarker([row.latitude, row.longitude], {
      radius: 6,
      color: "#2563eb",
      weight: 1,
      fillColor: "#3b82f6",
      fillOpacity: 0.85,
    });
    const popupLines = [
      row.docket_no ? `<strong>${row.docket_no}</strong>` : "",
      row.town || "",
      row.property_address || "",
      row.county ? `${row.county} County` : "",
      row.case_type || "",
      row.last_action_date ? `Last action: ${row.last_action_date}` : "",
    ].filter(Boolean);
    if (popupLines.length) {
      marker.bindPopup(popupLines.join("<br/>"), { maxWidth: 260 });
    }
    marker.addTo(markersLayer);
    bounds.push([row.latitude, row.longitude]);
  });

  if (bounds.length > 1) {
    map.fitBounds(bounds, { padding: [40, 40] });
  } else if (bounds.length === 1) {
    map.setView(bounds[0], 12);
  } else {
    map.setView([41.6032, -73.0877], 8);
  }
}

function renderRows() {
  // Since filtering is now done server-side, just display all cachedCases
  const rowsHtml = cachedCases
    .map((row) => {
      const created = row.created_at ? new Date(row.created_at + "Z").toLocaleString() : "";
      const docketLink = row.case_url
        ? `<a href="${row.case_url}" target="_blank" rel="noopener">${row.docket_no}</a>`
        : row.docket_no || "";
      return `<tr>
          <td>${docketLink}</td>
          <td>${row.town || ""}</td>
          <td>${row.county || ""}</td>
          <td>${row.property_address || ""}</td>
          <td>${row.case_type || ""}</td>
          <td>${row.last_action_date || ""}</td>
          <td>${created}</td>
        </tr>`;
    })
    .join("\n");

  TABLE_BODY.innerHTML = rowsHtml || "<tr><td colspan='7'>No cases match your filter.</td></tr>";
  renderMap(cachedCases);
}

function populateTownDropdown(county = null) {
  const towns = Object.keys(TOWN_TO_COUNTY).sort();
  let filteredTowns = towns;

  if (county) {
    filteredTowns = towns.filter(town => TOWN_TO_COUNTY[town] === county);
  }

  TOWN_FILTER.innerHTML = '<option value="">All Towns</option>';
  filteredTowns.forEach(town => {
    const option = document.createElement('option');
    option.value = town;
    option.textContent = town;
    TOWN_FILTER.appendChild(option);
  });
}

function clearFilters() {
  COUNTY_FILTER.value = "";
  TOWN_FILTER.value = "";
  DATE_FROM.value = "";
  DATE_TO.value = "";
  populateTownDropdown(); // Reset to all towns
}

function handleCountyChange() {
  const selectedCounty = COUNTY_FILTER.value;
  populateTownDropdown(selectedCounty);
  // Clear town selection when county changes
  TOWN_FILTER.value = "";
}

REFRESH_BTN.addEventListener("click", fetchCases);
APPLY_FILTERS.addEventListener("click", fetchCases);
CLEAR_FILTERS.addEventListener("click", () => {
  clearFilters();
  fetchCases();
});
COUNTY_FILTER.addEventListener("change", handleCountyChange);
API_INPUT.addEventListener("change", fetchCases);

initMap();
loadBaseUrl();
populateTownDropdown(); // Initialize town dropdown
STATUS.textContent = `Select filters and click Apply Filters to load up to ${LIMIT} cases.`;
