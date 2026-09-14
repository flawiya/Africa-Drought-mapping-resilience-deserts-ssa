"""
Last Updated: 2026-06-30
build_bivariate_dashboard.py
Builds the Africa Drought-Accessibility Bivariate Dashboard.
- Converts districts_2sfca_accessibility.gpkg to minified GeoJSON
- Embeds it in a premium dark glassmorphism dashboard
- Interactive 3x3 bivariate matrix with layer toggles
- Catchment distance selector (5km walk vs 50km drive)
- Cross-border anomaly highlighter
- Multiple basemaps and color palettes (Pink-Blue, Magma, RdPu)
"""
from pathlib import Path
import json
import geopandas as gpd
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # repo root
OUTPUT_DIR   = PROJECT_ROOT / "outputs"

DATA_DIR     = PROJECT_ROOT / "data"

_gpkg = DATA_DIR / "districts_2sfca_accessibility.gpkg"
if not _gpkg.exists():
    _gpkg = OUTPUT_DIR / "districts_2sfca_accessibility.gpkg"
GPKG_PATH = _gpkg

OUT_HTML = PROJECT_ROOT / "07_dashboard" / "index.html"

if not GPKG_PATH.exists():
    print(f"Error: {GPKG_PATH} does not exist. Run script_03 first.")
    exit(1)

print("Loading districts geopackage...")
gdf = gpd.read_file(GPKG_PATH).to_crs(4326)

# Standardize column list to export (only what the dashboard needs to keep it small)
# The shapefile/geopackage uses 'dr_XXXX' instead of 'drought_days_XXXX' due to column name length limits.
# We rename them back to 'drought_days_XXXX' for the dashboard to parse properly.
rename_dict = {}
year_cols = []
for c in gdf.columns:
    if c.startswith("dr_") and c[3:].isdigit():
        year_name = f"drought_days_{c[3:]}"
        rename_dict[c] = year_name
        year_cols.append(year_name)

gdf_renamed = gdf.rename(columns=rename_dict)

export_cols = [
    "geometry", "COUNTRY", "ADM_NAME", "spatial_k3", "crop_pct", "maize_pct",
    "access_norm_5km", "access_norm_50km", "crossborder_closer", "nearest_wc_poi_m", "nearest_cb_poi_m"
] + year_cols

gdf_export = gdf_renamed[export_cols].copy()

# Simplify geometries to keep the GeoJSON extremely lightweight (reduces file size from 35MB to ~1.4MB)
print("Simplifying geometries...")
gdf_export["geometry"] = gdf_export["geometry"].simplify(tolerance=0.005, preserve_topology=True)

# Add calculated metrics
gdf_export["mean_drought"] = gdf_export[year_cols].mean(axis=1).round(1)
gdf_export["max_drought"] = gdf_export[year_cols].max(axis=1).round(1)

# Convert to JSON
print("Converting to minified GeoJSON...")
gj_dict = json.loads(gdf_export.to_json())
GJ_INLINE = json.dumps(gj_dict, separators=(",", ":"))

# ── HTML ──────────────────────────────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Africa Drought-Accessibility Bivariate Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{{
  --bg:#080b10;
  --surface:rgba(22,27,34,0.7);
  --surface2:rgba(33,38,45,0.7);
  --border:rgba(48,54,61,0.5);
  --text:#e6edf3;
  --muted:#8b949e;
  --accent:#58a6ff;
  --low:#2ea043;
  --mod:#d29922;
  --high:#da3633;
  --r:12px;
  --blur:blur(12px);
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{
  font-family:'Inter',sans-serif;
  background:radial-gradient(circle at 50% 50%, #0d1622 0%, var(--bg) 100%);
  color:var(--text);
  display:flex;
  flex-direction:column;
  height:100vh;
  overflow:hidden;
}}

header{{
  background:var(--surface);
  backdrop-filter:var(--blur);
  -webkit-backdrop-filter:var(--blur);
  border-bottom:1px solid var(--border);
  padding:10px 18px;
  display:flex;
  align-items:center;
  gap:12px;
  flex-shrink:0;
  z-index:1000;
}}
h1{{font-size:14px;font-weight:600;white-space:nowrap;letter-spacing:-0.2px}}
h1 span{{color:var(--accent)}}
.badge{{
  background:var(--surface2);
  border:1px solid var(--border);
  border-radius:20px;
  padding:3px 9px;
  font-size:11px;
  color:var(--muted);
  white-space:nowrap;
}}
.spacer{{flex:1}}

select, button.t-btn{{
  background:rgba(33,38,45,0.85);
  border:1px solid var(--border);
  color:var(--text);
  border-radius:6px;
  padding:4px 8px;
  font-size:11px;
  font-family:inherit;
  cursor:pointer;
  transition:all 0.2s ease;
}}
select:hover,select:focus, button.t-btn:hover{{
  border-color:var(--accent);
  box-shadow:0 0 6px rgba(88,166,255,0.4);
  outline:none;
}}
button.t-btn.active{{
  background:var(--accent);
  color:#000;
  border-color:var(--accent);
}}
label{{font-size:10px;color:var(--muted);margin-right:2px;font-weight:500}}

.main{{display:flex;flex:1;overflow:hidden}}

aside{{
  width:290px;
  background:var(--surface);
  backdrop-filter:var(--blur);
  -webkit-backdrop-filter:var(--blur);
  border-right:1px solid var(--border);
  display:flex;
  flex-direction:column;
  overflow:hidden;
  flex-shrink:0;
}}
.ph{{
  padding:12px 14px 8px;
  font-size:10px;
  font-weight:700;
  color:var(--muted);
  letter-spacing:.8px;
  text-transform:uppercase;
}}

.control-group{{
  padding:10px 14px;
  border-bottom:1px solid var(--border);
}}

/* 3x3 MATRIX LEGEND */
.matrix-container{{
  display:flex;
  flex-direction:column;
  align-items:center;
  margin:10px 0;
}}
.matrix-row{{
  display:flex;
  gap:4px;
  margin-bottom:4px;
}}
.matrix-cell{{
  width:36px;
  height:36px;
  border-radius:4px;
  border:1px solid rgba(255,255,255,0.2);
  cursor:pointer;
  position:relative;
  transition:transform 0.15s ease, border-color 0.15s ease;
}}
.matrix-cell:hover{{
  transform:scale(1.08);
  border-color:#ffffff;
  z-index:2;
}}
.matrix-cell.off{{
  opacity:0.18;
}}
.matrix-cell-text{{
  position:absolute;
  font-size:8px;
  font-weight:700;
  color:#fff;
  text-shadow:0 1px 2px rgba(0,0,0,0.8);
  bottom:2px;
  right:3px;
}}
.matrix-axis-label{{
  font-size:9px;
  color:var(--muted);
  text-transform:uppercase;
  letter-spacing:0.5px;
}}

.c-border-toggle{{
  display:flex;
  align-items:center;
  gap:8px;
  padding:8px 0;
  font-size:11px;
}}
.c-border-toggle input{{
  accent-color:var(--accent);
  cursor:pointer;
}}

.clist{{
  flex:1;
  overflow-y:auto;
  padding:6px;
}}
.clist::-webkit-scrollbar{{width:4px}}
.clist::-webkit-scrollbar-thumb{{background:var(--border);border-radius:4px}}
.citem{{
  display:flex;
  align-items:center;
  gap:7px;
  padding:6px 8px;
  border-radius:6px;
  cursor:pointer;
  font-size:11px;
  transition:all 0.15s ease;
}}
.citem:hover{{background:rgba(255,255,255,0.05)}}
.citem.active{{
  background:rgba(88,166,255,0.12);
  color:var(--accent);
  font-weight:500;
}}
.cflag{{font-size:14px}}
.ccnt{{
  margin-left:auto;
  font-size:9px;
  color:var(--muted);
  background:rgba(255,255,255,0.05);
  border-radius:8px;
  padding:1px 5px;
}}

#map{{
  flex:1;
  z-index:1;
  background:#090d13 !important;
}}

.dpanel{{
  width:310px;
  background:var(--surface);
  backdrop-filter:var(--blur);
  -webkit-backdrop-filter:var(--blur);
  border-left:1px solid var(--border);
  display:flex;
  flex-direction:column;
  overflow:hidden;
  flex-shrink:0;
  transition:width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}}
.dpanel.hide{{width:0}}
.dinner{{min-width:310px;display:flex;flex-direction:column;height:100%}}
.dhead{{
  padding:12px 14px;
  border-bottom:1px solid var(--border);
  display:flex;
  align-items:center;
  gap:8px;
}}
.dhead h3{{font-size:13px;font-weight:600;flex:1}}
.xbtn{{
  background:none;
  border:none;
  color:var(--muted);
  cursor:pointer;
  font-size:15px;
  padding:2px 5px;
  border-radius:4px;
  transition:all 0.15s ease;
}}
.xbtn:hover{{background:rgba(255,255,255,0.08);color:var(--text)}}
.dbody{{padding:14px;overflow-y:auto;flex:1}}
.dbody::-webkit-scrollbar{{width:4px}}
.dbody::-webkit-scrollbar-thumb{{background:var(--border);border-radius:4px}}

.irow{{
  display:flex;
  justify-content:space-between;
  align-items:center;
  padding:6px 0;
  border-bottom:1px solid rgba(255,255,255,0.05);
  font-size:12px;
}}
.ik{{color:var(--muted)}}
.iv{{font-weight:500}}

.rbadge{{
  display:inline-block;
  padding:3px 9px;
  border-radius:20px;
  font-size:10px;
  font-weight:600;
}}
.rb-low{{background:rgba(46,160,67,0.15);color:var(--low);border:1px solid rgba(46,160,67,0.25)}}
.rb-mod{{background:rgba(210,153,34,0.15);color:var(--mod);border:1px solid rgba(210,153,34,0.25)}}
.rb-high{{background:rgba(218,54,51,0.15);color:var(--high);border:1px solid rgba(218,54,51,0.25)}}
.cw{{margin-top:12px}}
.clbl{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:4px}}

/* Leaflet Popups */
.leaflet-popup-content-wrapper{{
  background:rgba(22,27,34,0.85) !important;
  backdrop-filter:var(--blur) !important;
  -webkit-backdrop-filter:var(--blur) !important;
  border:1px solid var(--border) !important;
  border-radius:var(--r) !important;
  color:var(--text) !important;
  box-shadow:0 8px 32px rgba(0,0,0,0.6) !important;
}}
.leaflet-popup-tip{{background:rgba(22,27,34,0.85) !important;border:1px solid var(--border)}}
.leaflet-popup-content{{margin:9px 12px !important;font-family:'Inter',sans-serif;font-size:12px;min-width:170px}}
.pt{{font-weight:600;font-size:12px;margin-bottom:5px}}
.pg{{display:grid;grid-template-columns:1fr 1fr;gap:4px 14px}}
.pk{{color:var(--muted)}}.pk b{{color:var(--text)}}
</style>
</head>
<body>
<header>
  <h1>&#127757; Africa <span>Drought-Accessibility</span> Bivariate Dashboard</h1>
  <span class="badge">354 Maize-Dominant Districts &middot; 21 Countries</span>
  <div class="spacer"></div>
  <label>Distance:</label>
  <select id="distSel">
    <option value="50km">50 km Catchment (Vehicle)</option>
    <option value="5km">5 km Catchment (Walking)</option>
  </select>
  <label>Basemap:</label>
  <select id="bmSel">
    <option value="dark">CartoDB Dark</option>
    <option value="positron">CartoDB Light</option>
  </select>
</header>

<div class="main">
<aside>
  <div class="ph">Bivariate Toggles (3x3 Matrix)</div>
  <div class="control-group" style="padding-bottom:5px">
    <div style="font-size:10px;color:var(--muted);text-align:center;margin-bottom:4px">DROUGHT RISK (1=Low, 3=High)</div>
    <div class="matrix-container">
      <!-- 3x3 Grid. Rows represent Drought (3 to 1), Cols represent Access (1 to 3) -->
      <div class="matrix-row">
        <div style="font-size:9px;color:var(--muted);width:8px;line-height:36px">3</div>
        <div class="matrix-cell" id="cell-3-1" onclick="toggleMatrixClass(3, 1)"><span class="matrix-cell-text">3-1</span></div>
        <div class="matrix-cell" id="cell-3-2" onclick="toggleMatrixClass(3, 2)"><span class="matrix-cell-text">3-2</span></div>
        <div class="matrix-cell" id="cell-3-3" onclick="toggleMatrixClass(3, 3)"><span class="matrix-cell-text">3-3</span></div>
      </div>
      <div class="matrix-row">
        <div style="font-size:9px;color:var(--muted);width:8px;line-height:36px">2</div>
        <div class="matrix-cell" id="cell-2-1" onclick="toggleMatrixClass(2, 1)"><span class="matrix-cell-text">2-1</span></div>
        <div class="matrix-cell" id="cell-2-2" onclick="toggleMatrixClass(2, 2)"><span class="matrix-cell-text">2-2</span></div>
        <div class="matrix-cell" id="cell-2-3" onclick="toggleMatrixClass(2, 3)"><span class="matrix-cell-text">2-3</span></div>
      </div>
      <div class="matrix-row">
        <div style="font-size:9px;color:var(--muted);width:8px;line-height:36px">1</div>
        <div class="matrix-cell" id="cell-1-1" onclick="toggleMatrixClass(1, 1)"><span class="matrix-cell-text">1-1</span></div>
        <div class="matrix-cell" id="cell-1-2" onclick="toggleMatrixClass(1, 2)"><span class="matrix-cell-text">1-2</span></div>
        <div class="matrix-cell" id="cell-1-3" onclick="toggleMatrixClass(1, 3)"><span class="matrix-cell-text">1-3</span></div>
      </div>
      <div style="font-size:9px;color:var(--muted);margin-top:4px">ACCESSIBILITY &rarr;</div>
    </div>
    <div style="font-size:9.5px;color:var(--muted);text-align:center;line-height:1.3;margin-top:6px">
      Click cells to toggle zone visibility. <br/>
      <b>3-1</b> is the worst zone (High Risk, Low Access).
    </div>
  </div>

  <div class="control-group">
    <div class="ph" style="padding:0;margin-bottom:6px">Cross-Border Access</div>
    <label class="c-border-toggle">
      <input type="checkbox" id="cbHighlight"/>
      <span>Highlight Cross-Border Proximal (172)</span>
    </label>
    <div style="font-size:9.5px;color:var(--muted);line-height:1.3">
      Highlights districts where the nearest food supply point is closer in a neighboring country than in their own.
    </div>
  </div>

  <div class="ph">Countries</div>
  <div class="clist" id="clist"></div>
</aside>

<div id="map"></div>

<div class="dpanel hide" id="dpanel">
  <div class="dinner">
    <div class="dhead"><h3 id="dtitle">Detail</h3>
      <button class="xbtn" onclick="closeD()">&#10005;</button></div>
    <div class="dbody" id="dbody"></div>
  </div>
</div>
</div>

<script>
// ── EMBEDDED DATA ─────────────────────────────────────────────────────────────
const GJ = {GJ_INLINE};

// ── CONFIG & PALETTES ─────────────────────────────────────────────────────────
const YEARS = Array.from({{length:26}},(_,i)=>2000+i);
const FLAGS = {{'Angola':'&#127462;&#127476;','Burundi':'&#127463;&#127470;','Central African Republic':'&#127464;&#127467;','Democratic Republic of the Congo':'&#127464;&#127465;','Egypt':'&#127466;&#127468;','Ethiopia':'&#127466;&#127481;','Ghana':'&#127468;&#127469;','Kenya':'&#127472;&#127466;','Madagascar':'&#127474;&#127468;','Malawi':'&#127474;&#127484;','Mozambique':'&#127474;&#127487;','Namibia':'&#127475;&#127462;','Nigeria':'&#127475;&#127468;','Rwanda':'&#127479;&#127484;','South Africa':'&#127487;&#127462;','South Sudan':'&#127480;&#127480;','Swaziland':'&#127480;&#127487;','Tanzania':'&#127481;&#127487;','Uganda':'&#127482;&#127468;','Zambia':'&#127487;&#127474;','Zimbabwe':'&#127487;&#127484;'}};
const BM = {{
  dark:'https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',
  positron:'https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png',
  sat:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
  ter:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}',
  osm:'https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'
}};

const PALETTES = {{
  pinkBlue: {{
    "1-1": "#e8e8e8", "1-2": "#ace4e4", "1-3": "#5ac8c8",
    "2-1": "#dfb0d6", "2-2": "#a5add3", "2-3": "#5698b9",
    "3-1": "#be64ac", "3-2": "#8c62aa", "3-3": "#3b4994"
  }},
  magma: {{
    "1-1": "#3b0f70", "1-2": "#8c2582", "1-3": "#de4968",
    "2-1": "#8c2582", "2-2": "#de4968", "2-3": "#fe9f6d",
    "3-1": "#de4968", "3-2": "#fe9f6d", "3-3": "#fcfdbf"
  }},
  rdPu: {{
    "1-1": "#f7f7f7", "1-2": "#d4b9da", "1-3": "#c994c7",
    "2-1": "#df65b0", "2-2": "#c51b7d", "2-3": "#de77ae",
    "3-1": "#7a0177", "3-2": "#ae017e", "3-3": "#ce1256"
  }}
}};

let activePalette = "magma";
let activeDistance = "50km"; // '5km' or '50km'
let hiddenClasses = new Set();
let highlightCB = false;
let selCty = "all";
let mapLayer = null, tileLayer = null, chart = null;

const map = L.map('map', {{zoomControl:true}}).setView([0,25],4);
tileLayer = L.tileLayer(BM.dark, {{attribution:'CARTO/OSM',maxZoom:18}}).addTo(map);

// ── Boot ──────────────────────────────────────────────────────────────────────
buildClist();
renderMatrixColors();
render();

// ── Calculate Medians & Bins dynamically in JS ────────────────────────────────
function getAccessMedians() {{
  const key = "access_norm_" + (activeDistance === "5km" ? "5km" : "50km");
  const nonZero = GJ.features
    .map(f => f.properties[key] || 0)
    .filter(v => v > 0);
  nonZero.sort((a,b)=>a-b);
  if (nonZero.length === 0) return 0.5;
  const mid = Math.floor(nonZero.length / 2);
  return nonZero.length % 2 !== 0 ? nonZero[mid] : (nonZero[mid - 1] + nonZero[mid]) / 2.0;
}}

function getBivariateClass(f) {{
  // 1. Drought Bin (derived from spatial_k3 cluster averages)
  // spatial_k3 maps 0=High risk, 1=Moderate risk, 2=Low risk
  const k3 = f.properties.spatial_k3;
  let droughtBin = 1; // Default low
  if (k3 === 0) droughtBin = 3; // 0 is High Vulnerability
  else if (k3 === 1) droughtBin = 2; // 1 is Moderate
  else if (k3 === 2) droughtBin = 1; // 2 is Low
  
  // 2. Access Bin (zero-inflated median split)
  const key = "access_norm_" + (activeDistance === "5km" ? "5km" : "50km");
  const score = f.properties[key] || 0;
  const median = getAccessMedians();
  
  let accessBin = 1;
  if (score <= 0) accessBin = 1;
  else if (score <= median) accessBin = 2;
  else accessBin = 3;
  
  return droughtBin + "-" + accessBin;
}}

// ── Render matrix legends in sidebar ──────────────────────────────────────────
function renderMatrixColors() {{
  const pal = PALETTES[activePalette];
  for (let d = 1; d <= 3; d++) {{
    for (let a = 1; a <= 3; a++) {{
      const key = d + "-" + a;
      const el = document.getElementById("cell-" + key);
      if (el) {{
        el.style.backgroundColor = pal[key];
        if (hiddenClasses.has(key)) {{
          el.classList.add("off");
        }} else {{
          el.classList.remove("off");
        }}
      }}
    }}
  }}
}}

// ── Render map layers ─────────────────────────────────────────────────────────
function render() {{
  if (mapLayer) map.removeLayer(mapLayer);
  const key = "access_norm_" + (activeDistance === "5km" ? "5km" : "50km");
  
  mapLayer = L.geoJSON(GJ, {{
    filter: f => {{
      const p = f.properties;
      if (selCty !== 'all' && p.COUNTRY !== selCty) return false;
      const bClass = getBivariateClass(f);
      if (hiddenClasses.has(bClass)) return false;
      return true;
    }},
    style: f => {{
      const p = f.properties;
      const bClass = getBivariateClass(f);
      const pal = PALETTES[activePalette];
      let fillColor = pal[bClass] || "#cccccc";
      let borderColor = fillColor;
      let weight = 0.7;
      let opacity = 0.65;
      let fillOpacity = 0.75;
      
      // If crossborder highlight is active and district matches
      if (highlightCB && p.crossborder_closer) {{
        fillColor = "#ff0000"; // Bright red fill
        borderColor = "#ffffff"; // White border
        weight = 2.5;
        opacity = 1.0;
        fillOpacity = 0.90;
      }}
      
      return {{fillColor: fillColor, fillOpacity: fillOpacity, color: borderColor, weight: weight, opacity: opacity}};
    }},
    onEachFeature: (f, lyr) => {{
      const p = f.properties;
      const bClass = getBivariateClass(f);
      const score = p[key] || 0;
      
      lyr.on({{
        mouseover: e => {{
          e.target.setStyle({{weight: 2.0, color: '#ffffff', opacity: 0.95, fillOpacity: 0.95}});
          e.target.bringToFront();
          L.popup({{closeButton: false, offset: [0, -4]}}).setLatLng(e.latlng).setContent(
            '<div class="pt">' + p.ADM_NAME + '</div>' +
            '<div style="color:var(--muted);font-size:10px;margin-bottom:5px">' + p.COUNTRY + '</div>' +
            '<div class="pg">' +
            '<div class="pk">Biv Class: <b>' + bClass + '</b></div>' +
            '<div class="pk">Mean Drought: <b>' + p.mean_drought + ' d/yr</b></div>' +
            '<div class="pk">Access Score: <b>' + score.toFixed(4) + '</b></div>' +
            '<div class="pk">Maize %: <b>' + p.maize_pct.toFixed(1) + '%</b></div>' +
            '<div class="pk">Cropland %: <b>' + p.crop_pct.toFixed(1) + '%</b></div>' +
            '<div class="pk">Cross-border: <b>' + (p.crossborder_closer ? 'Yes' : 'No') + '</b></div>' +
            '</div>'
          ).openOn(map);
        }},
        mouseout: e => {{
          mapLayer.resetStyle(e.target);
          map.closePopup();
        }},
        click: () => showD(p)
      }});
    }}
  }}).addTo(map);
}}

function toggleMatrixClass(d, a) {{
  const key = d + "-" + a;
  if (hiddenClasses.has(key)) {{
    hiddenClasses.delete(key);
  }} else {{
    hiddenClasses.add(key);
  }}
  renderMatrixColors();
  render();
}}

// ── Control Listeners ─────────────────────────────────────────────────────────
document.getElementById("distSel").addEventListener("change", e => {{
  activeDistance = e.target.value;
  render();
}});
// Palette selector removed
document.getElementById("bmSel").addEventListener("change", e => {{
  if (tileLayer) map.removeLayer(tileLayer);
  tileLayer = L.tileLayer(BM[e.target.value], {{attribution: 'CARTO/OSM/Esri', maxZoom: 18}}).addTo(map);
  tileLayer.bringToBack();
}});
document.getElementById("cbHighlight").addEventListener("change", e => {{
  highlightCB = e.target.checked;
  render();
}});

// ── Sidebar Country List ──────────────────────────────────────────────────────
function buildClist() {{
  const m = {{}}; GJ.features.forEach(f => {{ const c = f.properties.COUNTRY; m[c] = (m[c] || 0) + 1; }});
  const el = document.getElementById('clist'); el.innerHTML = '';
  const ai = document.createElement('div'); ai.className = 'citem active'; ai.id = 'ci-all';
  ai.innerHTML = '<span class="cflag">&#127757;</span> All Countries<span class="ccnt">' + GJ.features.length + '</span>';
  ai.onclick = () => filCty('all'); el.appendChild(ai);
  Object.entries(m).sort().forEach(([c, n]) => {{
    const d = document.createElement('div'); d.className = 'citem'; d.id = 'ci-' + c.replace(/\s/g, '_');
    d.innerHTML = '<span class="cflag">' + (FLAGS[c] || '&#127988;') + '</span>' + c + '<span class="ccnt">' + n + '</span>';
    d.onclick = () => filCty(c); el.appendChild(d);
  }});
}}
function buildCtySel() {{
  const s = document.getElementById('ctySel');
  [...new Set(GJ.features.map(f => f.properties.COUNTRY))].sort().forEach(c => {{
    const o = document.createElement('option'); o.value = c; o.textContent = c; s.appendChild(o);
  }});
  s.addEventListener('change', e => filCty(e.target.value));
}}
function filCty(c) {{
  selCty = c; document.getElementById('ctySel').value = c;
  document.querySelectorAll('.citem').forEach(e => e.classList.remove('active'));
  const id = c === 'all' ? 'ci-all' : 'ci-' + c.replace(/\s/g, '_');
  const el = document.getElementById(id);
  if (el) {{ el.classList.add('active'); el.scrollIntoView({{block: 'nearest'}}); }}
  render();
  if (c !== 'all') {{
    const feats = GJ.features.filter(f => f.properties.COUNTRY === c);
    map.fitBounds(L.geoJSON({{type: 'FeatureCollection', features: feats}}).getBounds(), {{padding: [30, 30]}});
  }} else map.setView([0, 25], 4);
}}

// ── Detail Panel ──────────────────────────────────────────────────────────────
function showD(p) {{
  document.getElementById('dpanel').classList.remove('hide');
  document.getElementById('dtitle').textContent = p.ADM_NAME;
  
  const cbStatus = p.crossborder_closer ? '<span style="color:#ff4757;font-weight:700">&#9888; Border closer (' + (p.nearest_cb_poi_m / 1000).toFixed(1) + 'km)</span>' : 'No';
  const domesticDist = p.nearest_wc_poi_m ? (p.nearest_wc_poi_m / 1000).toFixed(1) + ' km' : 'None';
  
  document.getElementById('dbody').innerHTML =
    '<div class="irow"><span class="ik">Country</span><span class="iv">' + (FLAGS[p.COUNTRY] || '') + ' ' + p.COUNTRY + '</span></div>' +
    '<div class="irow"><span class="ik">District</span><span class="iv">' + p.ADM_NAME + '</span></div>' +
    '<div class="irow"><span class="ik">Maize % Cropland</span><span class="iv">' + p.maize_pct.toFixed(1) + '%</span></div>' +
    '<div class="irow"><span class="ik">Crop Area %</span><span class="iv">' + p.crop_pct.toFixed(1) + '%</span></div>' +
    '<div class="irow"><span class="ik">Mean Drought Days</span><span class="iv">' + p.mean_drought + ' d/yr</span></div>' +
    '<div class="irow"><span class="ik">Peak Drought Days</span><span class="iv">' + p.max_drought + ' d/yr</span></div>' +
    '<div class="irow"><span class="ik">Domestic Nearest POI</span><span class="iv">' + domesticDist + '</span></div>' +
    '<div class="irow"><span class="ik">Cross-Border Closer?</span><span class="iv">' + cbStatus + '</span></div>' +
    '<div class="cw"><div class="clbl">Drought Days 2000&#8211;2025</div><canvas id="dc" height="110"></canvas></div>';
    
  const td = YEARS.map(y => p['drought_days_' + y] || 0);
  const col = '#58a6ff';
  if (chart) chart.destroy();
  chart = new Chart(document.getElementById('dc').getContext('2d'), {{
    type: 'line',
    data: {{labels: YEARS, datasets: [{{data: td, borderColor: col, backgroundColor: col + '22', fill: true, tension: 0.3, pointRadius: 2, borderWidth: 1.8}}]}},
    options: {{plugins: {{legend: {{display: false}}, tooltip: {{callbacks: {{title: c => 'Year: ' + c[0].label, label: c => c.parsed.y + ' drought days'}}}}}},
      scales: {{x: {{ticks: {{color: '#8b949e', font: {{size: 9}}, maxTicksLimit: 7}}, grid: {{color: '#30363d'}}}},
              y: {{ticks: {{color: '#8b949e', font: {{size: 9}}}}, grid: {{color: '#30363d'}}, title: {{display: true, text: 'Days', color: '#8b949e', font: {{size: 9}}}}}}}},
      animation: {{duration: 300}}}}
  }});
}}
function closeD() {{ document.getElementById('dpanel').classList.add('hide'); if(chart) {{ chart.destroy(); chart = null; }} }}
</script>
</body>
</html>"""

OUT_HTML.write_text(HTML, encoding="utf-8")
size_kb = OUT_HTML.stat().st_size / 1024
print(f"[SAVED] {OUT_HTML}")
print(f"File size: {size_kb:.1f} KB")
print("Open bivariate_dashboard.html in your browser!")
