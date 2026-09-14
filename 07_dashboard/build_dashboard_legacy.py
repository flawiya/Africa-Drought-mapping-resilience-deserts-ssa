"""
Last Updated: 2026-06-30
build_dashboard.py
Builds the Africa Drought Dashboard HTML.
- Embeds district GeoJSON + POI GeoJSON directly (no server needed)
- Works when opened via file:// in any browser
- Premium Dark Glassmorphism aesthetic
- Marker clustering with custom neon icons for POIs
"""
from pathlib import Path
import json
import geopandas as gpd
import pandas as pd

BASE    = Path(__file__).parent
GPKG_PATH = BASE / "outputs" / "districts_2sfca_accessibility.gpkg"
POI_PATH = BASE / "outputs" / "pois_for_dashboard.geojson"
OUT     = BASE / "outputs" / "dashboard.html"

# ── Load and process district GPKG ────────────────────────────────────────────
if not GPKG_PATH.exists():
    print(f"Error: {GPKG_PATH} does not exist. Run script_03 first.")
    exit(1)

print("Loading districts geopackage...")
gdf = gpd.read_file(GPKG_PATH).to_crs(4326)

# Ensure spatial_k3 exists
if "spatial_k3" not in gdf.columns:
    print("[ERROR] 'spatial_k3' not found in accessibility GeoPackage.")
    sys.exit(1)

# Map spatial_k3 to risk_label
risk_map = {0: "High Vulnerability", 1: "Moderate Vulnerability", 2: "Low Vulnerability"}
gdf["risk_label"] = gdf["spatial_k3"].map(risk_map).fillna("Unknown")

# Rename dr_XXXX to drought_days_XXXX
rename_dict = {}
year_cols = []
for c in gdf.columns:
    if c.startswith("dr_") and c[3:].isdigit():
        year_name = f"drought_days_{c[3:]}"
        rename_dict[c] = year_name
        year_cols.append(year_name)

gdf_renamed = gdf.rename(columns=rename_dict)

# Calculate mean, max, and trend drought metrics
gdf_renamed["mean_drought"] = gdf_renamed[year_cols].mean(axis=1).round(1)
gdf_renamed["max_drought"] = gdf_renamed[year_cols].max(axis=1).round(1)
gdf_renamed["trend_2010_2025"] = gdf_renamed["drought_days_2025"] - gdf_renamed["drought_days_2010"]

export_cols = [
    "geometry", "COUNTRY", "ADM_NAME", "risk_label", "crop_pct", "maize_pct",
    "mean_drought", "max_drought", "trend_2010_2025",
    "access_norm_5km", "access_norm_50km", "crossborder_closer", "nearest_wc_poi_m", "nearest_cb_poi_m"
] + year_cols

gdf_export = gdf_renamed[export_cols].copy()

# Simplify geometries to keep the GeoJSON extremely lightweight
print("Simplifying geometries...")
gdf_export["geometry"] = gdf_export["geometry"].simplify(tolerance=0.005, preserve_topology=True)

# Convert to JSON
gj = json.loads(gdf_export.to_json())
GJ_INLINE = json.dumps(gj, separators=(",", ":"))

# ── Load POI GeoJSON if available ─────────────────────────────────────────────
if POI_PATH.exists():
    poi_gj = json.loads(POI_PATH.read_text(encoding="utf-8"))
    POI_INLINE = json.dumps(poi_gj, separators=(",", ":"))
    POI_COUNT  = len(poi_gj.get("features", []))
    print(f"POIs loaded: {POI_COUNT:,}")
else:
    POI_INLINE = '{"type":"FeatureCollection","features":[]}'
    POI_COUNT  = 0
    print("POIs not yet downloaded — dashboard will load with empty POI layer.")

# ── HTML ──────────────────────────────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Africa Maize-District Drought &amp; Food-System Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

<!-- Leaflet Marker Cluster Library -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.1.0/MarkerCluster.css"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.1.0/MarkerCluster.Default.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.1.0/leaflet.markercluster.js"></script>

<style>
:root{{
  --bg:#080b10;
  --surface:rgba(22,27,34,0.7);
  --surface2:rgba(33,38,45,0.7);
  --border:rgba(48,54,61,0.5);
  --text:#e6edf3;
  --muted:#8b949e;
  --low:#1b8a43;
  --mod:#c07a00;
  --high:#b81d18;
  --accent:#58a6ff;
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

/* ── GLASS CONTAINER ── */
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

select{{
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
select:hover,select:focus{{
  border-color:var(--accent);
  box-shadow:0 0 6px rgba(88,166,255,0.4);
  outline:none;
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
.stats{{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:10px}}
.sc{{
  background:var(--surface2);
  border-radius:var(--r);
  border:1px solid var(--border);
  padding:8px 10px;
  transition:all 0.2s ease;
}}
.sc:hover{{
  border-color:var(--accent);
  transform:translateY(-1px);
}}
.sv{{font-size:17px;font-weight:700;letter-spacing:-0.4px}}
.sl{{font-size:9px;color:var(--muted);margin-top:1px}}

.c-acc{{color:var(--accent)}}.c-pur{{color:#bc8cff}}.c-low{{color:var(--low)}}.c-mod{{color:var(--mod)}}.c-high{{color:var(--high)}}

.slider-wrap{{
  padding:10px 14px;
  border-bottom:1px solid var(--border);
}}
.slider-row{{display:flex;align-items:center;gap:6px}}
.yr-lbl{{font-size:12px;font-weight:700;color:var(--accent);min-width:34px}}
input[type=range]{{flex:1;accent-color:var(--accent);cursor:pointer;height:4px}}

.play-btn{{
  background:var(--surface2);
  border:1px solid var(--border);
  color:var(--text);
  border-radius:6px;
  padding:4px 10px;
  font-size:11px;
  cursor:pointer;
  transition:all 0.2s ease;
  font-weight:500;
}}
.play-btn:hover{{
  background:var(--accent);
  border-color:var(--accent);
  color:#000;
}}

.leg-block{{
  padding:10px 14px;
  border-bottom:1px solid var(--border);
}}
.leg-item{{
  display:flex;
  align-items:center;
  gap:7px;
  padding:5px 6px;
  border-radius:6px;
  cursor:pointer;
  transition:all 0.15s ease;
  font-size:11px;
}}
.leg-item:hover{{background:rgba(255,255,255,0.05)}}
.leg-item.off{{opacity:.25}}
.leg-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.leg-cnt{{
  margin-left:auto;
  font-size:10px;
  color:var(--muted);
  background:rgba(255,255,255,0.08);
  border-radius:10px;
  padding:1px 6px;
}}

/* POI legend */
.poi-section{{
  padding:10px 14px;
  border-bottom:1px solid var(--border);
}}
.poi-header{{
  display:flex;
  align-items:center;
  gap:6px;
  margin-bottom:6px;
}}
.poi-toggle{{
  display:flex;
  align-items:center;
  gap:6px;
  cursor:pointer;
  font-size:11px;
  color:var(--text);
}}
.poi-toggle input{{accent-color:var(--accent);cursor:pointer}}
.poi-cats{{
  padding-left:4px;
  max-height:160px;
  overflow-y:auto;
}}
.poi-cats::-webkit-scrollbar{{width:3px}}
.poi-cats::-webkit-scrollbar-thumb{{background:var(--border);border-radius:2px}}
.poi-cat{{
  display:flex;
  align-items:center;
  gap:6px;
  padding:4px 6px;
  border-radius:4px;
  font-size:11px;
  cursor:pointer;
  transition:all 0.15s ease;
}}
.poi-cat:hover{{background:rgba(255,255,255,0.05)}}
.poi-cat.off{{opacity:.25}}
.poi-dot{{
  width:10px;
  height:10px;
  border-radius:50%;
  flex-shrink:0;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:7px;
  color:white;
}}
.poi-cnt{{margin-left:auto;font-size:10px;color:var(--muted)}}

/* country list */
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

/* Custom marker cluster & popups */
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
.leaflet-popup-content{{margin:9px 12px !important;font-family:'Inter',sans-serif;font-size:12px;min-width:160px}}
.pt{{font-weight:600;font-size:12px;margin-bottom:5px}}
.pg{{display:grid;grid-template-columns:1fr 1fr;gap:4px 14px}}
.pk{{color:var(--muted)}}.pk b{{color:var(--text)}}
</style>
</head>
<body>
<header>
  <h1>&#127757; Africa <span>Maize-District</span> Drought &amp; Food-System Dashboard</h1>
  <span class="badge">354 Districts &middot; 21 Countries</span>
  <span class="badge" id="poiBadge">{POI_COUNT:,} POIs</span>
  <div class="spacer"></div>
  <label>Cluster:</label>
  <select id="clsSel">
    <option value="all">All Clusters</option>
    <option value="Low Vulnerability">Low Vulnerability</option>
    <option value="Moderate Vulnerability">Moderate Vulnerability</option>
    <option value="High Vulnerability">High Vulnerability</option>
  </select>
  <label>Country:</label>
  <select id="ctySel"><option value="all">All Countries</option></select>
  <label>Basemap:</label>
  <select id="bmSel">
    <option value="dark">CartoDB Dark</option>
    <option value="positron">CartoDB Light</option>
  </select>
</header>

<div class="main">
<aside>
  <div class="ph">Overview</div>
  <div class="stats">
    <div class="sc"><div class="sv c-acc" id="sDist">354</div><div class="sl">Districts</div></div>
    <div class="sc"><div class="sv c-pur" id="sCty">21</div><div class="sl">Countries</div></div>
    <div class="sc"><div class="sv c-low" id="sLow">151</div><div class="sl">Low Risk</div></div>
    <div class="sc"><div class="sv c-mod" id="sMod">85</div><div class="sl">Moderate</div></div>
    <div class="sc"><div class="sv c-high" id="sHigh">118</div><div class="sl">High Risk</div></div>
    <div class="sc"><div class="sv c-acc" id="sYear">2025</div><div class="sl">Viewing Year</div></div>
  </div>
  <div class="slider-wrap">
    <div style="font-size:10px;color:var(--muted);margin-bottom:3px">DROUGHT YEAR</div>
    <div class="slider-row">
      <span class="yr-lbl" id="yrLbl">2025</span>
      <input type="range" id="yrSlider" min="2000" max="2025" value="2025" step="1"/>
      <button class="play-btn" id="playBtn">&#9654; Play</button>
    </div>
  </div>

  <!-- District cluster legend -->
  <div class="leg-block">
    <div class="ph" style="padding:0 0 6px;border:none">Drought Clusters (k=3)</div>
    <div class="leg-item" id="ll" onclick="togCluster('Low Vulnerability')">
      <div class="leg-dot" style="background:var(--low)"></div>Low Vulnerability
      <span class="leg-cnt" id="cl">151</span></div>
    <div class="leg-item" id="lm" onclick="togCluster('Moderate Vulnerability')">
      <div class="leg-dot" style="background:var(--mod)"></div>Moderate Vulnerability
      <span class="leg-cnt" id="cm">85</span></div>
    <div class="leg-item" id="lh" onclick="togCluster('High Vulnerability')">
      <div class="leg-dot" style="background:var(--high)"></div>High Vulnerability
      <span class="leg-cnt" id="ch">118</span></div>
  </div>

  <!-- POI layer controls -->
  <div class="poi-section">
    <div class="poi-header">
      <label class="poi-toggle">
        <input type="checkbox" id="poiToggle" checked/>
        <span style="font-size:11px;font-weight:600">Food-System POIs</span>
      </label>
      <span id="poiTotal" style="margin-left:auto;font-size:10px;color:var(--muted)">{POI_COUNT:,} pts</span>
    </div>
    <div class="poi-cats" id="poiCats"></div>
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
const GJ  = {GJ_INLINE};
const POI = {POI_INLINE};

// ── CONFIG ────────────────────────────────────────────────────────────────────
const YEARS = Array.from({{length:26}},(_,i)=>2000+i);
const RC = {{'Low Vulnerability':'#1b8a43','Moderate Vulnerability':'#c07a00','High Vulnerability':'#b81d18','Unknown':'#58a6ff'}};
const FLAGS = {{'Angola':'&#127462;&#127476;','Burundi':'&#127463;&#127470;','Central African Republic':'&#127464;&#127467;','Democratic Republic of the Congo':'&#127464;&#127465;','Egypt':'&#127466;&#127468;','Ethiopia':'&#127466;&#127481;','Ghana':'&#127468;&#127469;','Kenya':'&#127472;&#127466;','Madagascar':'&#127474;&#127468;','Malawi':'&#127474;&#127484;','Mozambique':'&#127474;&#127487;','Namibia':'&#127475;&#127462;','Nigeria':'&#127475;&#127468;','Rwanda':'&#127479;&#127484;','South Africa':'&#127487;&#127462;','South Sudan':'&#127480;&#127480;','Swaziland':'&#127480;&#127487;','Tanzania':'&#127481;&#127487;','Uganda':'&#127482;&#127468;','Zambia':'&#127487;&#127474;','Zimbabwe':'&#127487;&#127484;'}};
const BM = {{
  dark:'https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',
  positron:'https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png',
  sat:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
  ter:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}',
  osm:'https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'
}};

// POI category styling - modern relevant symbols & high-contrast dark-mode colors
const POI_STYLE = {{
  market:         {{color:'#ff4757', icon:'🎪', label:'Market / Marketplace'}},
  supermarket:    {{color:'#ffa502', icon:'🛒', label:'Supermarket'}},
  convenience:    {{color:'#eccc68', icon:'🛍️', label:'Convenience / Grocery'}},
  agri_supply:    {{color:'#2ed573', icon:'🚜', label:'Agri Supply / Farm Shop'}},
  wholesale:      {{color:'#1e90ff', icon:'📦', label:'Wholesale'}},
  bank:           {{color:'#9b59b6', icon:'🏦', label:'Bank'}},
  microfinance:   {{color:'#8e44ad', icon:'💳', label:'Microfinance'}},
  bus_station:    {{color:'#1abc9c', icon:'🚏', label:'Bus Station'}},
  fuel_logistics: {{color:'#34495e', icon:'🚚', label:'Fuel / Logistics'}},
  other:          {{color:'#7f8c8d', icon:'📍', label:'Other'}},
}};

let distLayer=null, poiLayer=null, tile=null;
let selCty='all', selCls='all', hidden=new Set(), hiddenPOI=new Set(), yr=2025, timer=null, chart=null;
let showPOI=true;

const map = L.map('map',{{zoomControl:true}}).setView([0,25],4);
tile = L.tileLayer(BM.dark,{{attribution:'CARTO/OSM',maxZoom:18}}).addTo(map);

// ── Boot ──────────────────────────────────────────────────────────────────────
buildClist(); buildCtySel(); render(); buildPOILayer(); buildPOICats();

// ── District layer ────────────────────────────────────────────────────────────
function render(){{
  if(distLayer) map.removeLayer(distLayer);
  const yc='drought_days_'+yr; let lo=0,mo=0,hi=0;
  distLayer = L.geoJSON(GJ,{{
    filter:f=>{{
      const p=f.properties;
      if(selCty!=='all'&&p.COUNTRY!==selCty) return false;
      if(selCls!=='all'&&p.risk_label!==selCls) return false;
      if(hidden.has(p.risk_label)) return false;
      return true;
    }},
    style:f=>{{
      const p=f.properties, c=RC[p.risk_label]||'#58a6ff', dd=p[yc]||0;
      // Decreased transparency (higher opacity) for stronger solid colors
      const op=Math.min(0.35+(dd/180)*0.55,0.90);
      if(p.risk_label==='Low Vulnerability') lo++;
      else if(p.risk_label==='Moderate Vulnerability') mo++;
      else if(p.risk_label==='High Vulnerability') hi++;
      return{{fillColor:c,fillOpacity:op,color:c,weight:0.7,opacity:0.65}};
    }},
    onEachFeature:(f,lyr)=>{{
      const p=f.properties;
      lyr.on({{
        mouseover:e=>{{
          e.target.setStyle({{weight:2.0,color:'#ffffff',opacity:0.95,fillOpacity:Math.min((p['drought_days_'+yr]||0)/180*0.55+0.45,0.98)}});
          e.target.bringToFront();
          if(poiLayer) poiLayer.bringToFront(); // Ensure POIs stay on top
          L.popup({{closeButton:false,offset:[0,-4]}}).setLatLng(e.latlng).setContent(
            '<div class="pt">'+p.ADM_NAME+'</div>'+
            '<div style="color:var(--muted);font-size:10px;margin-bottom:5px">'+p.COUNTRY+'</div>'+
            '<div class="pg">'+
            '<div class="pk">Risk: <b>'+(p.risk_label||'').replace(' Vulnerability','')+'</b></div>'+
            '<div class="pk">Year: <b>'+yr+'</b></div>'+
            '<div class="pk">Drought: <b>'+(p[yc]||0)+' days</b></div>'+
            '<div class="pk">Mean: <b>'+p.mean_drought+' d/yr</b></div>'+
            '<div class="pk">Maize: <b>'+p.maize_pct+'%</b></div>'+
            '<div class="pk">Crop: <b>'+p.crop_pct+'%</b></div>'+
            '<div class="pk">5km Acc: <b>'+(p.access_norm_5km||0).toFixed(4)+'</b></div>'+
            '<div class="pk">50km Acc: <b>'+(p.access_norm_50km||0).toFixed(4)+'</b></div>'+
            '</div>'
          ).openOn(map);
        }},
        mouseout:e=>{{distLayer.resetStyle(e.target);map.closePopup();}},
        click:()=>showD(p)
      }});
    }}
  }}).addTo(map);
  if(poiLayer) poiLayer.bringToFront();
  document.getElementById('sDist').textContent=lo+mo+hi;
  document.getElementById('sLow').textContent=lo; document.getElementById('sHigh').textContent=hi;
  document.getElementById('sMod').textContent=mo;
  document.getElementById('cl').textContent=lo; document.getElementById('cm').textContent=mo; document.getElementById('ch').textContent=hi;
  document.getElementById('sCty').textContent=selCty==='all'?[...new Set(GJ.features.map(f=>f.properties.COUNTRY))].length:1;
}}

// ── POI layer (Clustered & Styled) ────────────────────────────────────────────
function buildPOILayer(){{
  if(poiLayer) map.removeLayer(poiLayer);
  if(!showPOI||!POI.features.length) return;
  
  // Custom dark styled cluster group
  poiLayer = L.markerClusterGroup({{
    maxClusterRadius: 35,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: true,
    disableClusteringAtZoom: 12,
    iconCreateFunction: function(cluster) {{
      const count = cluster.getChildCount();
      return L.divIcon({{
        html: `<div style="
          background: rgba(8,11,16,0.85);
          color: var(--accent);
          border: 1.5px solid var(--accent);
          box-shadow: 0 0 8px var(--accent);
          width: 28px;
          height: 28px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 10px;
          font-weight: 700;
        ">${{count}}</div>`,
        className: 'custom-poi-cluster',
        iconSize: [28, 28]
      }});
    }}
  }});

  L.geoJSON(POI, {{
    filter: f => !hiddenPOI.has(f.properties.category),
    pointToLayer:(f,ll)=>{{
      const cat=f.properties.category;
      const s=POI_STYLE[cat]||POI_STYLE.other;
      
      // Beautiful glowing circular icon containing the emoji symbol
      const icon = L.divIcon({{
        html: `<div style="
          background-color: ${{s.color}};
          width: 20px;
          height: 20px;
          border-radius: 50%;
          border: 1px solid #ffffff;
          box-shadow: 0 0 6px ${{s.color}};
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 11px;
          cursor: pointer;
        ">${{s.icon}}</div>`,
        className: 'custom-poi-marker',
        iconSize: [20, 20],
        iconAnchor: [10, 10]
      }});
      
      return L.marker(ll, {{icon: icon}});
    }},
    onEachFeature:(f,lyr)=>{{
      const p=f.properties, s=POI_STYLE[p.category]||POI_STYLE.other;
      lyr.bindPopup(
        '<div class="pt">'+s.icon+' '+(p.name||'Unnamed')+'</div>'+
        '<div class="pg" style="margin-top:4px">'+
        '<div class="pk">Type: <b>'+s.label+'</b></div>'+
        '<div class="pk">Country: <b>'+p.country+'</b></div>'+
        '</div>',
        {{closeButton:true,maxWidth:220}}
      );
    }}
  }}).addTo(poiLayer);
  
  poiLayer.addTo(map);
}}

// ── POI sidebar controls ──────────────────────────────────────────────────────
function buildPOICats(){{
  const counts={{}};
  POI.features.forEach(f=>{{const c=f.properties.category; counts[c]=(counts[c]||0)+1;}});
  const el=document.getElementById('poiCats'); el.innerHTML='';
  Object.entries(POI_STYLE).forEach(([cat,s])=>{{
    const n=counts[cat]||0; if(n===0) return;
    const d=document.createElement('div'); d.className='poi-cat'; d.id='pc-'+cat;
    d.innerHTML='<div class="poi-dot" style="background:'+s.color+'">'+s.icon+'</div>'+
      s.label+'<span class="poi-cnt">'+n+'</span>';
    d.onclick=()=>togPOICat(cat);
    el.appendChild(d);
  }});
  if(!Object.values(counts).some(v=>v>0)){{
    el.innerHTML='<div style="font-size:11px;color:var(--muted);padding:4px 0">No POIs downloaded yet</div>';
  }}
}}
function togPOICat(cat){{
  if(hiddenPOI.has(cat)) hiddenPOI.delete(cat); else hiddenPOI.add(cat);
  document.getElementById('pc-'+cat)?.classList.toggle('off',hiddenPOI.has(cat));
  buildPOILayer();
}}
document.getElementById('poiToggle').addEventListener('change',e=>{{
  showPOI=e.target.checked; buildPOILayer();
}});

// ── Country list ──────────────────────────────────────────────────────────────
function buildClist(){{
  const m={{}};GJ.features.forEach(f=>{{const c=f.properties.COUNTRY;m[c]=(m[c]||0)+1;}});
  const el=document.getElementById('clist'); el.innerHTML='';
  const ai=document.createElement('div'); ai.className='citem active'; ai.id='ci-all';
  ai.innerHTML='<span class="cflag">&#127757;</span> All Countries<span class="ccnt">'+GJ.features.length+'</span>';
  ai.onclick=()=>filCty('all'); el.appendChild(ai);
  Object.entries(m).sort().forEach(([c,n])=>{{
    const d=document.createElement('div'); d.className='citem'; d.id='ci-'+c.replace(/\s/g,'_');
    d.innerHTML='<span class="cflag">'+(FLAGS[c]||'&#127988;')+'</span>'+c+'<span class="ccnt">'+n+'</span>';
    d.onclick=()=>filCty(c); el.appendChild(d);
  }});
}}
function buildCtySel(){{
  const s=document.getElementById('ctySel');
  [...new Set(GJ.features.map(f=>f.properties.COUNTRY))].sort().forEach(c=>{{
    const o=document.createElement('option'); o.value=c; o.textContent=c; s.appendChild(o);
  }});
  s.addEventListener('change',e=>filCty(e.target.value));
}}
function filCty(c){{
  selCty=c; document.getElementById('ctySel').value=c;
  document.querySelectorAll('.citem').forEach(e=>e.classList.remove('active'));
  const id=c==='all'?'ci-all':'ci-'+c.replace(/\s/g,'_');
  const el=document.getElementById(id);
  if(el){{el.classList.add('active'); el.scrollIntoView({{block:'nearest'}});}}
  render();
  if(c!=='all'){{
    const feats=GJ.features.filter(f=>f.properties.COUNTRY===c);
    map.fitBounds(L.geoJSON({{type:'FeatureCollection',features:feats}}).getBounds(),{{padding:[30,30]}});
  }} else map.setView([0,25],4);
}}

// ── Filters ───────────────────────────────────────────────────────────────────
document.getElementById('clsSel').addEventListener('change',e=>{{selCls=e.target.value;render();}});
function togCluster(n){{
  if(hidden.has(n)) hidden.delete(n); else hidden.add(n);
  const ids={{'Low Vulnerability':'ll','Moderate Vulnerability':'lm','High Vulnerability':'lh'}};
  document.getElementById(ids[n])?.classList.toggle('off',hidden.has(n)); render();
}}
document.getElementById('bmSel').addEventListener('change',e=>{{
  if(tile) map.removeLayer(tile);
  tile=L.tileLayer(BM[e.target.value],{{attribution:'Esri/CARTO/OSM',maxZoom:18}}).addTo(map);
  tile.bringToBack();
}});

// ── Year slider ───────────────────────────────────────────────────────────────
document.getElementById('yrSlider').addEventListener('input',e=>{{
  yr=+e.target.value;
  document.getElementById('yrLbl').textContent=yr;
  document.getElementById('sYear').textContent=yr; render();
}});
document.getElementById('playBtn').addEventListener('click',()=>{{
  if(timer){{clearInterval(timer);timer=null;document.getElementById('playBtn').textContent='&#9654; Play';return;}}
  document.getElementById('playBtn').textContent='&#9646;&#9646; Pause';
  let y=yr>=2025?2000:yr;
  timer=setInterval(()=>{{
    y++; document.getElementById('yrSlider').value=y; yr=y;
    document.getElementById('yrLbl').textContent=y; document.getElementById('sYear').textContent=y; render();
    if(y>=2025){{clearInterval(timer);timer=null;document.getElementById('playBtn').textContent='&#9654; Play';}}
  }},600);
}});

// ── Detail panel ──────────────────────────────────────────────────────────────
function showD(p){{
  document.getElementById('dpanel').classList.remove('hide');
  document.getElementById('dtitle').textContent=p.ADM_NAME;
  const rc={{'Low Vulnerability':'rb-low','Moderate Vulnerability':'rb-mod','High Vulnerability':'rb-high'}};
  const trend=+(p.trend_2010_2025||0);
  const tarr=trend>5?'&#8593; Worsening':trend<-5?'&#8595; Improving':'&#8594; Stable';
  const tc=trend>5?'#da3633':trend<-5?'#2ea043':'#d29922';
  const cbStatus = p.crossborder_closer ? '<span style="color:#ff4757;font-weight:700">&#9888; Border closer (' + (p.nearest_cb_poi_m / 1000).toFixed(1) + 'km)</span>' : 'No';
  const domesticDist = p.nearest_wc_poi_m ? (p.nearest_wc_poi_m / 1000).toFixed(1) + ' km' : 'None';

  document.getElementById('dbody').innerHTML=
    '<div style="margin-bottom:8px"><span class="rbadge '+(rc[p.risk_label]||'rb-low')+'">'+p.risk_label+'</span></div>'+
    '<div class="irow"><span class="ik">Country</span><span class="iv">'+(FLAGS[p.COUNTRY]||'')+' '+p.COUNTRY+'</span></div>'+
    '<div class="irow"><span class="ik">District</span><span class="iv">'+p.ADM_NAME+'</span></div>'+
    '<div class="irow"><span class="ik">Maize % Cropland</span><span class="iv">'+p.maize_pct+'%</span></div>'+
    '<div class="irow"><span class="ik">Crop Area %</span><span class="iv">'+p.crop_pct+'%</span></div>'+
    '<div class="irow"><span class="ik">Mean Drought Days</span><span class="iv">'+p.mean_drought+' d/yr</span></div>'+
    '<div class="irow"><span class="ik">Peak Drought Days</span><span class="iv">'+p.max_drought+' d/yr</span></div>'+
    '<div class="irow"><span class="ik">2SFCA 5km Walk</span><span class="iv">'+(p.access_norm_5km||0).toFixed(4)+'</span></div>'+
    '<div class="irow"><span class="ik">2SFCA 50km Drive</span><span class="iv">'+(p.access_norm_50km||0).toFixed(4)+'</span></div>'+
    '<div class="irow"><span class="ik">Nearest Domestic POI</span><span class="iv">'+domesticDist+'</span></div>'+
    '<div class="irow"><span class="ik">Cross-Border Closer?</span><span class="iv">'+cbStatus+'</span></div>'+
    '<div class="irow"><span class="ik">Drought in '+yr+'</span><span class="iv">'+(p['drought_days_'+yr]||0)+' days</span></div>'+
    '<div class="irow"><span class="ik">Trend 2010&#8594;2025</span><span class="iv" style="color:'+tc+'">'+tarr+' ('+(trend>0?'+':'')+trend+'d)</span></div>'+
    '<div class="cw"><div class="clbl">Drought Days 2000&#8211;2025</div><canvas id="dc" height="110"></canvas></div>';
  const td=YEARS.map(y=>p['drought_days_'+y]||0), col=RC[p.risk_label]||'#58a6ff';
  if(chart) chart.destroy();
  chart=new Chart(document.getElementById('dc').getContext('2d'),{{
    type:'line',
    data:{{labels:YEARS,datasets:[{{data:td,borderColor:col,backgroundColor:col+'22',fill:true,tension:0.3,pointRadius:2,pointHoverRadius:4,borderWidth:1.8}}]}},
    options:{{plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{title:c=>'Year: '+c[0].label,label:c=>c.parsed.y+' drought days'}}}}}},
      scales:{{x:{{ticks:{{color:'#8b949e',font:{{size:9}},maxTicksLimit:7}},grid:{{color:'#30363d'}}}},
              y:{{ticks:{{color:'#8b949e',font:{{size:9}}}},grid:{{color:'#30363d'}},title:{{display:true,text:'Days',color:'#8b949e',font:{{size:9}}}}}}}},
      animation:{{duration:300}}}}
  }});
}}
function closeD(){{document.getElementById('dpanel').classList.add('hide');if(chart){{chart.destroy();chart=null;}}}}
</script>
</body>
</html>"""

OUT.write_text(HTML, encoding="utf-8")
size_kb = OUT.stat().st_size / 1024
print(f"[SAVED] {OUT}")
print(f"File size: {size_kb:.1f} KB  |  POIs embedded: {POI_COUNT:,}")
print("Open dashboard.html in your browser!")
