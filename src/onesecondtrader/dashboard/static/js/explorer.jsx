const { useState, useRef, useEffect, useCallback, useMemo } = React;

// ─── Constants ─────────────────────────────────────────────
const BAR_FIELDS = ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"];
const OPERATORS = ["<=", ">=", "<", ">", "==", "!="];
const STYLES = ["line", "histogram", "dots", "dash1", "dash2", "dash3", "background1", "background2"];
const COLORS = ["black", "red", "blue", "green", "orange", "purple", "cyan", "magenta", "yellow", "teal"];
const WIDTHS = ["thin", "normal", "thick", "extra_thick"];

function formatParamName(name) {
  let result = name.replace(/_/g, ' ');
  result = result.replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2');
  result = result.replace(/([a-z])([A-Z])/g, '$1 $2');
  result = result.replace(/([a-zA-Z])(\d)/g, '$1 $2');
  return result.split(' ').map(word => {
    if (word === word.toUpperCase() && word.length > 1) return word;
    return word.charAt(0).toUpperCase() + word.slice(1);
  }).join(' ');
}

const RTYPE_MAP = { "Second": 32, "Minute": 33, "Hour": 34, "Day": 35 };
const RTYPE_LABELS = { 32: "Second", 33: "Minute", 34: "Hour", 35: "Day" };
const CHART_TYPES = [
  { value: "candlestick", label: "Candlestick" },
  { value: "oc_bars", label: "OC Bars" },
  { value: "c_bars", label: "C Bars" },
  { value: "bars", label: "Bars" },
];
const TIME_PERIODS = ['1min', '5min', '10min', '15min', '20min', 'hour', '4hour', 'day', 'week', 'month', 'quarter', 'year'];
const TIME_PERIOD_LABELS = {
  '1min': '1 Min', '5min': '5 Min', '10min': '10 Min', '15min': '15 Min',
  '20min': '20 Min', 'hour': 'Hour', '4hour': '4 Hour', 'day': 'Day',
  'week': 'Week', 'month': 'Month', 'quarter': 'Quarter', 'year': 'Year'
};
const TIME_PERIODS_BY_RTYPE = {
  35: ['year', 'quarter'],
  34: ['quarter', 'month', 'week'],
  33: ['day', 'hour'],
  32: ['hour', '20min', '10min', '5min'],
};

// ─── Helpers ───────────────────────────────────────────────
function formatTimestamp(ns) {
  const ms = Number(BigInt(ns) / BigInt(1000000));
  const date = new Date(ms);
  return date.toISOString().slice(0, 16).replace('T', ' ');
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// ─── Icons ────────────────────────────────────────────────
const Icons = {
  ChevronDown: () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
  ),
  Plus: () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
  ),
  X: () => (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
  ),
  Save: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
  ),
  Trash: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
  ),
  Database: () => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
  ),
  Activity: () => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
  ),
  Table: () => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
  ),
  Eye: () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
  ),
  EyeOff: () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
  ),
  Play: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"/></svg>
  ),
  Search: () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
  ),
  ChevronRight: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
  ),
  Check: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
  ),
  Stop: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" stroke="none">
      <rect x="4" y="4" width="16" height="16" rx="2" />
    </svg>
  ),
  BarChart: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
  ),
  Flask: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M9 3h6"/><path d="M10 3v7.4a2 2 0 0 1-.5 1.3L4 18.6a1 1 0 0 0 .8 1.4h14.4a1 1 0 0 0 .8-1.4l-5.5-6.9a2 2 0 0 1-.5-1.3V3"/><path d="M8.5 14h7"/></svg>
  ),
  Layers: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
  ),
  Briefcase: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
  ),
  Zap: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
  ),
};

// ─── Reusable Components ──────────────────────────────────
function Select({ value, onChange, options, placeholder, small, grouped }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // options can be strings or {value, label} objects
  const normalizedOptions = options.map((opt) =>
    typeof opt === "object" && opt !== null ? opt : { value: opt, label: opt }
  );

  const selectedLabel = (() => {
    if (grouped) {
      for (const opt of normalizedOptions) {
        if (opt.options) {
          const found = opt.options.find((o) => o.value === value);
          if (found) return found.label;
        }
      }
    }
    const found = normalizedOptions.find((o) => o.value === value);
    return found ? found.label : value;
  })();

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button onClick={() => setOpen(!open)}
        style={{ ...st.select, ...(small ? { padding: "4px 8px", fontSize: "11px", width: "100%" } : {}), color: value ? "#e2e8f0" : "#64748b" }}>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1, textAlign: "left" }}>
          {selectedLabel || placeholder || "Select..."}
        </span>
        <Icons.ChevronDown />
      </button>
      {open && (
        <div style={st.dropdown}>
          {grouped ? (
            normalizedOptions.map((group) => (
              <div key={group.label}>
                <div style={{ padding: "4px 10px 3px", fontSize: "9px", fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.5px" }}>{group.label}</div>
                {(group.options || []).map((opt) => (
                  <button key={opt.value} onClick={() => { onChange(opt.value); setOpen(false); }}
                    style={{ ...st.dropdownItem, background: opt.value === value ? "rgba(99,102,241,0.15)" : "transparent", color: opt.value === value ? "#818cf8" : "#cbd5e1" }}>
                    {opt.label}
                  </button>
                ))}
              </div>
            ))
          ) : (
            normalizedOptions.map((opt) => (
              <button key={opt.value} onClick={() => { onChange(opt.value); setOpen(false); }}
                style={{ ...st.dropdownItem, background: opt.value === value ? "rgba(99,102,241,0.15)" : "transparent", color: opt.value === value ? "#818cf8" : "#cbd5e1" }}>
                {opt.label}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function Chip({ label, onRemove }) {
  return (
    <span style={st.chip}>
      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "10.5px" }}>{label}</span>
      {onRemove && <button onClick={onRemove} style={st.chipX}><Icons.X /></button>}
    </span>
  );
}

function SectionHeader({ icon, title, number, subtitle, right }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "9px", marginBottom: "14px" }}>
      <div style={st.sectionIcon}>{icon}</div>
      <div style={{ minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "7px" }}>
          <span style={st.sectionNumber}>{number}</span>
          <h2 style={st.sectionTitle}>{title}</h2>
        </div>
        {subtitle && <p style={st.sectionSubtitle}>{subtitle}</p>}
      </div>
      <div style={{ flex: 1 }} />
      {right}
    </div>
  );
}

function PresetBar({ presets, selected, onSelect, presetName, onNameChange, onSave, onDelete }) {
  const [hovered, setHovered] = useState(false);
  const [editing, setEditing] = useState(false);

  const presetOptions = presets.map((p) => typeof p === "object" ? { value: p.name, label: p.name } : { value: p, label: p });

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}>
      {editing ? (
        <input type="text" value={presetName} onChange={(e) => onNameChange(e.target.value)}
          onBlur={() => { if (!presetName) setEditing(false); }}
          onKeyDown={(e) => { if (e.key === "Enter") { onSave(); setEditing(false); } if (e.key === "Escape") setEditing(false); }}
          autoFocus
          placeholder="Preset name..."
          style={st.presetInlineInput} />
      ) : null}
      <div style={{ display: "flex", gap: "1px", opacity: hovered ? 1 : 0, transition: "opacity 0.15s" }}>
        <button onClick={() => setEditing(!editing)} style={st.iconBtn} title="Save as..."><Icons.Save /></button>
        <button onClick={onDelete} style={{ ...st.iconBtn, color: selected ? "#f87171" : "#334155" }} title="Delete"><Icons.Trash /></button>
      </div>
      <div style={st.presetChip}>
        <Select value={selected} onChange={onSelect} options={presetOptions} placeholder="No preset" small />
      </div>
    </div>
  );
}

function colorToHex(name) {
  const map = { blue: "#6366f1", red: "#ef4444", green: "#22c55e", orange: "#f97316", purple: "#a855f7", cyan: "#06b6d4", white: "#f1f5f9", black: "#334155", magenta: "#d946ef", yellow: "#eab308", teal: "#14b8a6" };
  return map[name] || name;
}

const PANEL_OPTIONS = [
  { value: -3, label: "Panel 3", dir: "above" },
  { value: -2, label: "Panel 2", dir: "above" },
  { value: -1, label: "Panel 1", dir: "above" },
  { value: 0, label: "On Chart", dir: "chart" },
  { value: 1, label: "Panel 1", dir: "below" },
  { value: 2, label: "Panel 2", dir: "below" },
  { value: 3, label: "Panel 3", dir: "below" },
];

const ArrowUp = () => (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
);
const ArrowDown = () => (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>
);

function panelLabel(value) {
  const opt = PANEL_OPTIONS.find((o) => o.value === value);
  return opt ? opt.label : `Panel ${Math.abs(value)}`;
}

function panelDir(value) {
  const opt = PANEL_OPTIONS.find((o) => o.value === value);
  return opt ? opt.dir : (value < 0 ? "above" : "below");
}

function PanelChip({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const dir = panelDir(value);
  return (
    <div ref={ref} style={{ position: "relative", zIndex: open ? 100 : 1, flexShrink: 0 }}>
      <button onClick={() => setOpen(!open)} style={{
        display: "inline-flex", alignItems: "center", gap: "4px",
        padding: "3px 8px", borderRadius: "4px", border: "none", cursor: "pointer",
        fontSize: "10px", fontWeight: 600, fontFamily: "'DM Sans', sans-serif",
        letterSpacing: "0.3px", transition: "all 0.15s",
        width: "95px", justifyContent: "space-between",
        background: dir === "above" ? "rgba(251,191,36,0.12)" : dir === "below" ? "rgba(99,102,241,0.12)" : "rgba(148,163,184,0.12)",
        color: dir === "above" ? "#fbbf24" : dir === "below" ? "#a5b4fc" : "#94a3b8",
      }}>
        {panelLabel(value)}
        <Icons.ChevronDown />
      </button>
      {open && (
        <div style={{
          position: "absolute", top: "100%", left: 0, marginTop: "4px",
          background: "#1e293b", border: "1px solid rgba(51,65,85,0.8)", borderRadius: "7px",
          padding: "3px", zIndex: 200, minWidth: "140px",
          boxShadow: "0 10px 35px rgba(0,0,0,0.5)",
        }}>
          <div style={{ padding: "4px 10px 3px", fontSize: "9px", fontWeight: 600, color: "#fbbf24", textTransform: "uppercase", letterSpacing: "0.5px", opacity: 0.7, display: "flex", alignItems: "center", gap: "4px" }}><ArrowUp /> Above Chart</div>
          {PANEL_OPTIONS.filter((o) => o.dir === "above").map((opt) => (
            <button key={opt.value} onClick={() => { onChange(opt.value); setOpen(false); }}
              style={{
                width: "100%", padding: "5px 10px", background: opt.value === value ? "rgba(251,191,36,0.12)" : "transparent",
                border: "none", color: opt.value === value ? "#fbbf24" : "#cbd5e1",
                fontSize: "11.5px", fontFamily: "'DM Sans', sans-serif", cursor: "pointer",
                borderRadius: "4px", textAlign: "left",
              }}>
              {opt.label}
            </button>
          ))}
          <div style={{ height: "1px", background: "rgba(51,65,85,0.5)", margin: "3px 6px" }} />
          {PANEL_OPTIONS.filter((o) => o.dir === "chart").map((opt) => (
            <button key={opt.value} onClick={() => { onChange(opt.value); setOpen(false); }}
              style={{
                width: "100%", padding: "5px 10px", background: opt.value === value ? "rgba(148,163,184,0.12)" : "transparent",
                border: "none", color: opt.value === value ? "#94a3b8" : "#cbd5e1",
                fontSize: "11.5px", fontFamily: "'DM Sans', sans-serif", cursor: "pointer",
                borderRadius: "4px", textAlign: "left",
              }}>
              {opt.label}
            </button>
          ))}
          <div style={{ height: "1px", background: "rgba(51,65,85,0.5)", margin: "3px 6px" }} />
          {PANEL_OPTIONS.filter((o) => o.dir === "below").map((opt) => (
            <button key={opt.value} onClick={() => { onChange(opt.value); setOpen(false); }}
              style={{
                width: "100%", padding: "5px 10px", background: opt.value === value ? "rgba(99,102,241,0.12)" : "transparent",
                border: "none", color: opt.value === value ? "#818cf8" : "#cbd5e1",
                fontSize: "11.5px", fontFamily: "'DM Sans', sans-serif", cursor: "pointer",
                borderRadius: "4px", textAlign: "left",
              }}>
              {opt.label}
            </button>
          ))}
          <div style={{ padding: "3px 10px 4px", fontSize: "9px", fontWeight: 600, color: "#818cf8", textTransform: "uppercase", letterSpacing: "0.5px", opacity: 0.7, display: "flex", alignItems: "center", gap: "4px" }}><ArrowDown /> Below Chart</div>
        </div>
      )}
    </div>
  );
}

function displayName(indicator) {
  return indicator.replace(/([a-z])([A-Z])/g, "$1 $2");
}

function AddIndicatorButton({ options, onAdd }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef(null);
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Group by package
  const groups = {};
  options.forEach((i) => {
    const pkg = i.package || "Other";
    if (!groups[pkg]) groups[pkg] = [];
    groups[pkg].push(i);
  });

  const filteredGroups = {};
  const searchLower = search.toLowerCase();
  Object.keys(groups).sort().forEach((pkg) => {
    const filtered = groups[pkg].filter((i) => i.class_name.toLowerCase().includes(searchLower));
    if (filtered.length > 0) filteredGroups[pkg] = filtered;
  });

  return (
    <div ref={ref} style={{ position: "relative", flex: 1 }}>
      <button onClick={() => setOpen(!open)} style={{ ...st.fillBetweenBtn, width: "100%" }}>
        <Icons.Plus />
        <span>Add Indicator</span>
      </button>
      {open && (
        <div style={{
          position: "absolute", bottom: "100%", left: 0, right: 0, marginBottom: "4px",
          background: "#1e293b", border: "1px solid rgba(51,65,85,0.8)", borderRadius: "7px",
          padding: "3px", zIndex: 200, maxHeight: "300px", overflowY: "auto",
          boxShadow: "0 -10px 35px rgba(0,0,0,0.5)",
        }}>
          <div style={{ padding: "4px" }}>
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search indicators..."
              style={{ ...st.tagSearchInput, width: "100%", padding: "6px 8px", background: "rgba(30,41,59,0.6)", border: "1px solid rgba(51,65,85,0.5)", borderRadius: "4px" }} />
          </div>
          {Object.keys(filteredGroups).length > 0 ? (
            Object.keys(filteredGroups).sort().map((pkg) => (
              <div key={pkg}>
                <div style={{ padding: "4px 10px 3px", fontSize: "9px", fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.5px" }}>{pkg}</div>
                {filteredGroups[pkg].map((ind) => (
                  <button key={ind.class_name} onClick={() => { onAdd(ind.class_name); setOpen(false); setSearch(""); }}
                    style={{ ...st.dropdownItem, display: "flex", alignItems: "center", gap: "6px" }}>
                    {displayName(ind.class_name)}
                  </button>
                ))}
              </div>
            ))
          ) : (
            <div style={{ padding: "8px 10px", color: "#475569", fontSize: "12px", textAlign: "center" }}>No indicators available</div>
          )}
        </div>
      )}
    </div>
  );
}

function paramsChanged(ind) {
  if (!ind.savedParams) return ind.needsCalculation;
  if (ind.params.some((p, i) => p !== ind.savedParams[i]) || ind.params.length !== ind.savedParams.length) return true;
  if (ind.savedParamsDict) {
    for (const k of Object.keys(ind.paramsDict)) {
      const cur = ind.paramsDict[k];
      if (typeof cur === 'object' && cur !== null) {
        if (JSON.stringify(cur) !== JSON.stringify(ind.savedParamsDict[k])) return true;
      }
    }
  }
  return false;
}

// ─── Navigation Pages ────────────────────────────────────
const NAV_ITEMS = [
  { key: "splits", icon: <Icons.Layers />, label: "Splits" },
  { key: "explorer", icon: <Icons.BarChart />, label: "Explore" },
  { key: "backtest", icon: <Icons.Flask />, label: "Backtest" },
];

function Sidebar({ activePage, onNavigate }) {
  return (
    <div style={st.sidebar}>
      <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1, paddingTop: "16px" }}>
        {NAV_ITEMS.map((item) => {
          const isActive = activePage === item.key;
          return (
            <button key={item.key} onClick={() => onNavigate(item.key)}
              style={{
                ...st.navBtn,
                background: isActive ? "rgba(99,102,241,0.12)" : "transparent",
                color: isActive ? "#a5b4fc" : "#475569",
              }}>
              {isActive && <div style={st.navActiveBar} />}
              {item.icon}
              <span style={{ fontSize: "9px", fontWeight: isActive ? 600 : 500, letterSpacing: "0.2px", marginTop: "3px" }}>{item.label}</span>
            </button>
          );
        })}
      </div>

    </div>
  );
}

function PlaceholderPage({ title, subtitle }) {
  return (
    <div style={{ padding: "24px 28px" }}>
      <div style={st.header}>
        <div>
          <h1 style={st.pageTitle}>{title}</h1>
          <p style={st.pageSubtitle}>{subtitle}</p>
        </div>
      </div>
      <div style={{ ...st.card, marginTop: "16px", display: "flex", alignItems: "center", justifyContent: "center", minHeight: "300px" }}>
        <div style={{ textAlign: "center", color: "#475569" }}>
          <p style={{ fontSize: "14px", fontWeight: 500 }}>Coming soon</p>
          <p style={{ fontSize: "12px", marginTop: "4px" }}>This page is under development</p>
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────
function ExplorerRedesign() {
  // Navigation
  const [activePage, setActivePage] = useState("explorer");

  // API-loaded data
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [indicatorRuns, setIndicatorRuns] = useState({});
  const activeRunIds = Object.values(indicatorRuns)
    .filter(r => r && r.status === 'completed' && r.run_id)
    .map(r => r.run_id);
  const [availableIndicatorsData, setAvailableIndicatorsData] = useState([]);
  const [rtypes, setRtypes] = useState([]);
  const [publishers, setPublishers] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [coverageSymbols, setCoverageSymbols] = useState([]);
  const [allCoverageData, setAllCoverageData] = useState([]);
  const [symbolCoverage, setSymbolCoverage] = useState({});
  const [segments, setSegments] = useState([]);
  const [calculatingSet, setCalculatingSet] = useState(new Set());
  const pendingRunIds = useRef({});
  const pollGeneration = useRef({});
  const calcQueue = useRef([]);
  const processingQueue = useRef(false);
  const abortedWhileQueued = useRef(new Set());
  const segmentLoadResolver = useRef(null);
  const segmentAbortRef = useRef(null);
  const [activeCalcIndex, setActiveCalcIndex] = useState(null);
  const currentSessionIdRef = useRef(currentSessionId);
  currentSessionIdRef.current = currentSessionId;
  const [indicatorCompletionCount, setIndicatorCompletionCount] = useState(0);
  const initialSegmentsLoadedRef = useRef(false);
  const [expandedRows, setExpandedRows] = useState({});
  const [chartCache, setChartCache] = useState({});
  const [timePeriod, setTimePeriod] = useState("day");
  const [dsPresets, setDsPresets] = useState([]);
  const [indPresets, setIndPresets] = useState([]);
  const [condPresets, setCondPresets] = useState([]);
  const [selectedPublisherId, setSelectedPublisherId] = useState(null);
  const [hasContinuousSymbols, setHasContinuousSymbols] = useState(false);
  const [contractType, setContractType] = useState("outrights");
  const [settingsVersion, setSettingsVersion] = useState(0);

  // Data Source
  const [dsPreset, setDsPreset] = useState("");
  const [dsPresetName, setDsPresetName] = useState("");
  const [barPeriod, setBarPeriod] = useState("");
  const [provider, setProvider] = useState("");
  const [exchange, setExchange] = useState("");
  const [symbolSearch, setSymbolSearch] = useState("");
  const [selectedSymbols, setSelectedSymbols] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [showSymbolDropdown, setShowSymbolDropdown] = useState(false);
  const skipSymbolClearRef = useRef(false);

  // Split sources
  const [splitSources, setSplitSources] = useState([]);
  const [selectedSplitSource, setSelectedSplitSource] = useState("");

  const splitSourceOptions = useMemo(() => {
    const groups = {};
    splitSources.forEach(s => {
      if (!groups[s.split_name]) groups[s.split_name] = [];
      groups[s.split_name].push(s);
    });
    return Object.keys(groups).map(name => ({
      label: name,
      options: groups[name].map(s => ({
        value: s.source_name,
        label: `${s.region.charAt(0).toUpperCase() + s.region.slice(1)}: ${s.start_date} → ${s.end_date}`,
      })),
    }));
  }, [splitSources]);

  // Indicators & Chart (merged)
  const [indPreset, setIndPreset] = useState("");
  const [indPresetName, setIndPresetName] = useState("");
  const [chartType, setChartType] = useState("c_bars");
  const [indicators, setIndicators] = useState([]);
  const indicatorsRef = useRef(indicators);
  indicatorsRef.current = indicators;

  const [expandedCards, setExpandedCards] = useState({});
  const [calcProgress, setCalcProgress] = useState({});  // { [index]: 0.0–1.0 }

  // Fill Between
  const [fillBetweens, setFillBetweens] = useState([]);
  const ALPHAS = ["0.05", "0.10", "0.15", "0.20", "0.25", "0.30", "0.40", "0.50"];

  const addFillBetween = () => {
    setFillBetweens([...fillBetweens, {
      upper: fillBetweenOptions[0] || "",
      lower: fillBetweenOptions[1] || fillBetweenOptions[0] || "",
      color: "blue",
      alpha: "0.15",
    }]);
  };
  const updateFillBetween = (index, field, value) => {
    const next = [...fillBetweens];
    next[index] = { ...next[index], [field]: value };
    setFillBetweens(next);
  };
  const removeFillBetween = (index) => {
    setFillBetweens(fillBetweens.filter((_, i) => i !== index));
  };

  const toggleExpand = (index) => {
    setExpandedCards((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  // Sort: above panels (most negative first), then on-chart (0), then below panels (ascending)
  const sortedIndicators = indicators
    .map((ind, i) => ({ ...ind, origIndex: i }))
    .sort((a, b) => a.panel - b.panel);

  const calculatedNames = indicators
    .map((ind, idx) => indicatorRuns[idx]?.status === 'completed' ? (ind.computedName || ind.indicator) : null)
    .filter(Boolean);
  const fillBetweenOptions = ["OPEN", "HIGH", "LOW", "CLOSE", ...calculatedNames];

  // Chart Display
  const [displayTab, setDisplayTab] = useState("bars");
  const [barsPerChart, setBarsPerChart] = useState(500);
  const displayTabRef = useRef(displayTab);
  displayTabRef.current = displayTab;
  const barsPerChartRef = useRef(barsPerChart);
  barsPerChartRef.current = barsPerChart;
  const timePeriodRef = useRef(timePeriod);
  timePeriodRef.current = timePeriod;

  // Signal filter state
  const [conditions, setConditions] = useState([]);
  const [condPreset, setCondPreset] = useState("");
  const [condPresetName, setCondPresetName] = useState("");
  const [sigLeft, setSigLeft] = useState("OPEN");
  const [sigOp, setSigOp] = useState("<=");
  const [sigRight, setSigRight] = useState("(Value)");
  const [sigValue, setSigValue] = useState(0);
  const [contextBars, setContextBars] = useState(50);
  const [gapTolerance, setGapTolerance] = useState(0);
  const [isFiltering, setIsFiltering] = useState(false);
  const [filterProgress, setFilterProgress] = useState(0);
  const filterIdRef = useRef(null);
  const filterPollRef = useRef(null);

  const rightOptions = ["(Value)", ...BAR_FIELDS, ...indicators.map((ind) => ind.computedName || ind.indicator)];
  const leftOptions = [...BAR_FIELDS, ...indicators.map((ind) => ind.computedName || ind.indicator)];

  const addCondition = () => {
    setConditions([...conditions, { left: sigLeft, op: sigOp, right: sigRight, value: sigRight === "(Value)" ? sigValue : null }]);
  };
  const removeCondition = (index) => {
    setConditions(conditions.filter((_, i) => i !== index));
  };

  // ─── Coverage filtering helper ───
  const filterAndSetCoverage = useCallback((allData, ctype, hasCont) => {
    let filtered = allData;
    if (hasCont) {
      if (ctype === 'continuous') filtered = allData.filter(r => r.symbol_type === 'continuous');
      else if (ctype === 'spreads') filtered = allData.filter(r => r.symbol_type === 'raw_symbol' && r.symbol.includes('-'));
      else filtered = allData.filter(r => r.symbol_type === 'raw_symbol' && !r.symbol.includes('-'));
    }
    const syms = filtered.map(r => r.symbol);
    setCoverageSymbols(syms);
    const covMap = {};
    filtered.forEach(r => { covMap[r.symbol] = { min_ts: r.min_ts, max_ts: r.max_ts }; });
    setSymbolCoverage(covMap);
    return syms;
  }, []);

  // ─── On mount: load rtypes, indicators, presets ───
  useEffect(() => {
    fetch('/api/secmaster/symbols_coverage').then(r => r.json()).then(data => {
      const syms = data.symbols || [];
      const rtypeSet = new Set(syms.map(s => s.rtype));
      const sorted = [...rtypeSet].sort((a, b) => a - b);
      setRtypes(sorted);
      if (sorted.length === 1) setBarPeriod(RTYPE_LABELS[sorted[0]] || 'rtype ' + sorted[0]);
    });
    fetch('/api/indicators').then(r => r.json()).then(data => {
      setAvailableIndicatorsData(data.indicators || []);
    });
    fetch('/api/presets').then(r => r.json()).then(d => setDsPresets(d.presets || []));
    fetch('/api/explore/presets').then(r => r.json()).then(d => setIndPresets(d.presets || []));
    fetch('/api/explore/condition-presets').then(r => r.json()).then(d => setCondPresets(d.presets || []));
    fetch('/api/splits/sources').then(r => r.json()).then(d => setSplitSources(d || []));
  }, []);

  // ─── Cancel pending runs on page unload ───
  useEffect(() => {
    const cancelAll = () => {
      Object.values(pendingRunIds.current).forEach(runId => {
        if (runId) navigator.sendBeacon(`/api/explorer/cancel/${runId}`, '');
      });
      if (filterIdRef.current) {
        navigator.sendBeacon(`/api/cancel-filter/${filterIdRef.current}`, '');
      }
      if (filterPollRef.current) clearTimeout(filterPollRef.current);
    };
    window.addEventListener('beforeunload', cancelAll);
    return () => {
      window.removeEventListener('beforeunload', cancelAll);
      cancelAll();
    };
  }, []);

  // ─── On barPeriod change: load publishers ───
  useEffect(() => {
    if (skipSymbolClearRef.current) return;
    let cancelled = false;
    if (!barPeriod) { setPublishers([]); return; }
    const rtype = RTYPE_MAP[barPeriod];
    if (!rtype) return;
    fetch(`/api/secmaster/publishers?rtype=${rtype}`).then(r => r.json()).then(data => {
      if (!cancelled) {
        const pubs = data.publishers || [];
        setPublishers(pubs);
        if (pubs.length === 1 && !skipSymbolClearRef.current) setProvider(pubs[0]);
      }
    });
    if (!skipSymbolClearRef.current) {
      setProvider(""); setExchange(""); setDatasets([]);
      setSelectedPublisherId(null); setCoverageSymbols([]);
      setSelectedSymbols([]); setCurrentSessionId(null);
    }
    return () => { cancelled = true; };
  }, [barPeriod]);

  // ─── On provider change: load datasets ───
  useEffect(() => {
    if (skipSymbolClearRef.current) return;
    let cancelled = false;
    if (!provider || !barPeriod) { setDatasets([]); return; }
    const rtype = RTYPE_MAP[barPeriod];
    fetch(`/api/secmaster/publishers/${encodeURIComponent(provider)}/datasets?rtype=${rtype}`)
      .then(r => r.json()).then(data => {
        if (!cancelled) {
          const ds = data.datasets || [];
          setDatasets(ds);
          if (ds.length === 1 && !skipSymbolClearRef.current) {
            setExchange(ds[0].dataset);
            setSelectedPublisherId(ds[0].publisher_id);
          }
        }
      });
    if (!skipSymbolClearRef.current) {
      setExchange(""); setSelectedPublisherId(null);
      setCoverageSymbols([]); setSelectedSymbols([]); setCurrentSessionId(null);
    }
    return () => { cancelled = true; };
  }, [provider, barPeriod]);

  // ─── On dataset (exchange/publisher_id) change: load symbol coverage ───
  useEffect(() => {
    if (skipSymbolClearRef.current) return;
    let cancelled = false;
    if (!selectedPublisherId || !barPeriod) { setCoverageSymbols([]); return; }
    const rtype = RTYPE_MAP[barPeriod];
    fetch(`/api/secmaster/symbols_coverage?publisher_id=${selectedPublisherId}&rtype=${rtype}`)
      .then(r => r.json()).then(data => {
        if (cancelled) return;
        const all = data.symbols || [];
        setAllCoverageData(all);
        const hasCont = all.some(r => r.symbol_type === 'continuous');
        setHasContinuousSymbols(hasCont);
        const syms = filterAndSetCoverage(all, hasCont ? contractType : 'outrights', hasCont);
        if (!skipSymbolClearRef.current) {
          setSelectedSymbols(syms.length === 1 ? [syms[0]] : []);
          setCurrentSessionId(null);
        }
      });
    return () => { cancelled = true; };
  }, [selectedPublisherId, barPeriod, filterAndSetCoverage]);

  // ─── On contract type change: re-filter coverage ───
  useEffect(() => {
    if (skipSymbolClearRef.current) return;
    if (allCoverageData.length > 0) {
      const syms = filterAndSetCoverage(allCoverageData, contractType, hasContinuousSymbols);
      if (!skipSymbolClearRef.current) {
        setSelectedSymbols(syms.length === 1 ? [syms[0]] : []);
      }
    }
  }, [contractType, allCoverageData, hasContinuousSymbols, filterAndSetCoverage]);

  // ─── Date range auto-fill from coverage ───
  useEffect(() => {
    if (skipSymbolClearRef.current) return;
    if (selectedSymbols.length === 0) {
      setStartDate("");
      setEndDate("");
      return;
    }
    let minTs = null, maxTs = null;
    selectedSymbols.forEach(s => {
      const cov = symbolCoverage[s];
      if (cov) {
        if (minTs === null || cov.min_ts < minTs) minTs = cov.min_ts;
        if (maxTs === null || cov.max_ts > maxTs) maxTs = cov.max_ts;
      }
    });
    if (minTs !== null) {
      const minDate = new Date(Math.floor(minTs / 1000000)).toISOString().split('T')[0];
      const maxDate = new Date(Math.floor(maxTs / 1000000)).toISOString().split('T')[0];
      setStartDate(minDate);
      setEndDate(maxDate);
    }
  }, [selectedSymbols, symbolCoverage]);

  // ─── Deterministic skip-ref reset (declared AFTER hooks 3-7) ───
  useEffect(() => {
    skipSymbolClearRef.current = false;
  });

  // ─── Reset session when data source changes ───
  useEffect(() => {
    setCurrentSessionId(null);
    setSegments([]);
    setExpandedRows({});
    setChartCache({});
    setIndicators([]);
    setIndicatorRuns({});
    setExpandedCards({});
    setFillBetweens([]);
    setIndicatorCompletionCount(0);
    initialSegmentsLoadedRef.current = false;
  }, [barPeriod, provider, exchange, selectedPublisherId, selectedSymbols, contractType]);

  // ─── Light reset when date range changes ───
  useEffect(() => {
    setCurrentSessionId(null);
    setSegments([]);
    setExpandedRows({});
    setChartCache({});
    setIndicatorRuns({});
    setIndicatorCompletionCount(0);
    initialSegmentsLoadedRef.current = false;
  }, [startDate, endDate]);

  // ─── Early session creation on data source selection ───
  useEffect(() => {
    if (!selectedPublisherId || selectedSymbols.length === 0 || !barPeriod) return;
    const rtype = RTYPE_MAP[barPeriod];
    if (!rtype) return;

    let cancelled = false;
    const symbolType = (hasContinuousSymbols && contractType === 'continuous') ? 'continuous' : 'raw_symbol';

    const createSession = async () => {
      try {
        const res = await fetch('/api/explorer/session', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            publisher_id: selectedPublisherId, rtype,
            symbols: [...selectedSymbols].sort(),
            start_date: startDate || null, end_date: endDate || null,
            symbol_type: symbolType,
          }),
        });
        if (!res.ok || cancelled) return;
        const data = await res.json();
        if (cancelled) return;

        // Set session state directly (OHLC pre-calc no longer exists)
        setCurrentSessionId(data.session_id);
      } catch (e) {
        if (!cancelled) console.error('Failed to create session', e);
      }
    };

    createSession();
    return () => { cancelled = true; };
  }, [selectedPublisherId, selectedSymbols, barPeriod, startDate, endDate, hasContinuousSymbols, contractType]);

  // ─── Symbol search ───
  const filteredSymbols = coverageSymbols.filter(
    (sym) => sym.toLowerCase().includes(symbolSearch.toLowerCase()) && !selectedSymbols.includes(sym)
  );

  // ─── Available indicators ───
  const availableIndicators = availableIndicatorsData;

  const symbolRef = useRef(null);
  useEffect(() => {
    const handler = (e) => { if (symbolRef.current && !symbolRef.current.contains(e.target)) setShowSymbolDropdown(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // ─── Get default panel for indicator ───
  const getDefaultPanel = useCallback((className) => {
    const upper = className.toUpperCase();
    if (/SMA|BOLLINGER|PARABOLICSAR|PERIODHIGHLOW|PERIODEXTREME/.test(upper)) return 0;
    const max = Math.max(0, ...indicators.map(ind => Math.abs(ind.panel)));
    return max + 1;
  }, [indicators]);

  // ─── Add indicator ───
  const addIndicator = useCallback((className) => {
    const meta = availableIndicatorsData.find(i => i.class_name === className);
    if (!meta) return;
    const paramValues = [];
    const paramsDict = {};
    const paramsMeta = meta.params || [];
    paramsMeta.forEach(p => {
      paramsDict[p.name] = p.default;
      paramValues.push(String(p.default ?? ''));
    });
    paramsMeta.forEach(p => {
      if (p.type === 'indicator_class' && p.kwargs_name && p.source_params) {
        const selectedSource = p.default || '';
        const subParams = p.source_params[selectedSource] || [];
        const kwargsDict = {};
        subParams.forEach(sp => { kwargsDict[sp.name] = sp.default; });
        paramsDict[p.kwargs_name] = kwargsDict;
      }
    });
    setIndicators(prev => [...prev, {
      indicator: className,
      class_name: className,
      params: paramValues,
      paramsMeta: paramsMeta,
      paramsDict: paramsDict,
      savedParams: [...paramValues],
      savedParamsDict: JSON.parse(JSON.stringify(paramsDict)),
      panel: getDefaultPanel(className),
      style: 'line', color: 'blue', width: 'normal',
      visible: true, needsCalculation: true,
    }]);
  }, [availableIndicatorsData, getDefaultPanel]);

  const removeIndicator = (index) => {
    const nextIndicators = indicators.filter((_, i) => i !== index);
    setIndicators(nextIndicators);
    const nextRuns = {};
    Object.keys(indicatorRuns).forEach(k => {
      const ki = parseInt(k);
      if (ki < index) nextRuns[ki] = indicatorRuns[ki];
      else if (ki > index) nextRuns[ki - 1] = indicatorRuns[ki];
    });
    setIndicatorRuns(nextRuns);
    if (currentSessionId) {
      saveChartSettings(nextIndicators, nextRuns);
    }
  };

  const updateIndicator = (index, field, value) => {
    const next = [...indicators];
    next[index] = { ...next[index], [field]: value };
    setIndicators(next);
    // Save chart settings when display settings change
    if (['panel', 'style', 'color', 'width', 'visible'].includes(field) && currentSessionId) {
      saveChartSettings(next);
    }
  };

  const updateParam = (index, paramIndex, value, paramMeta) => {
    const next = [...indicators];
    const newParams = [...next[index].params];
    newParams[paramIndex] = value;
    const newDict = { ...next[index].paramsDict };
    if (paramMeta) {
      if (paramMeta.type === 'indicator_class') {
        newDict[paramMeta.name] = value;
        if (paramMeta.kwargs_name && paramMeta.source_params) {
          const subParams = paramMeta.source_params[value] || [];
          const kwargsDict = {};
          subParams.forEach(sp => { kwargsDict[sp.name] = sp.default; });
          newDict[paramMeta.kwargs_name] = kwargsDict;
        }
      } else if (paramMeta.type === 'int') newDict[paramMeta.name] = parseInt(value) || 0;
      else if (paramMeta.type === 'float') newDict[paramMeta.name] = parseFloat(value) || 0;
      else newDict[paramMeta.name] = value;
    }
    next[index] = { ...next[index], params: newParams, paramsDict: newDict, needsCalculation: true };
    setIndicators(next);
  };

  const updateSourceSubParam = (index, kwargsName, subParamName, value, subParamMeta) => {
    const next = [...indicators];
    const newDict = { ...next[index].paramsDict };
    const kwargsDict = { ...(newDict[kwargsName] || {}) };
    if (subParamMeta.type === 'int') kwargsDict[subParamName] = parseInt(value) || 0;
    else if (subParamMeta.type === 'float') kwargsDict[subParamName] = parseFloat(value) || 0;
    else kwargsDict[subParamName] = value;
    newDict[kwargsName] = kwargsDict;
    next[index] = { ...next[index], paramsDict: newDict, needsCalculation: true };
    setIndicators(next);
  };

  // ─── Save chart settings to session ───
  const saveChartSettings = useCallback(async (indicatorsList, runsList) => {
    if (!currentSessionId) return;
    const inds = indicatorsList || indicators;
    const runs = runsList || indicatorRuns;
    const chartSettings = {
      indicators: {},
      fill_between: fillBetweens.map(fb => ({
        upper: fb.upper, lower: fb.lower, color: fb.color, alpha: parseFloat(fb.alpha) || 0.15,
      })),
      chart_type: chartType,
    };
    inds.forEach((ind, idx) => {
      const runInfo = runs[idx];
      if (runInfo && runInfo.run_id) {
        const name = ind.computedName || ind.indicator;
        chartSettings.indicators[name] = {
          panel: ind.panel,
          below_price: ind.panel !== 0,
          style: ind.style,
          color: ind.color,
          width: ind.width,
          visible: ind.visible,
        };
      }
    });
    try {
      await fetch(`/api/sessions/${currentSessionId}/chart-settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chartSettings),
      });
      setSettingsVersion(v => v + 1);
      setChartCache({});
    } catch (e) {
      console.error('Failed to save chart settings', e);
    }
  }, [currentSessionId, indicators, fillBetweens, chartType, indicatorRuns]);

  // ─── Per-indicator calculation (sequential queue) ───
  const enqueueCalculation = (index) => {
    // If already queued or calculating, don't double-queue
    if (calculatingSet.has(index)) return;

    // Cancel any existing completed run being re-calculated
    const existingRunId = pendingRunIds.current[index];
    if (existingRunId) {
      fetch(`/api/explorer/cancel/${existingRunId}`, { method: 'POST' }).catch(() => {});
      delete pendingRunIds.current[index];
    }

    // Bump generation to kill any stale poll
    pollGeneration.current[index] = (pollGeneration.current[index] || 0) + 1;

    setCalculatingSet(prev => new Set(prev).add(index));
    calcQueue.current.push(index);
    processQueue();
  };

  const processQueue = async () => {
    if (processingQueue.current) return;
    processingQueue.current = true;

    while (calcQueue.current.length > 0) {
      const index = calcQueue.current[0];
      if (abortedWhileQueued.current.has(index)) {
        abortedWhileQueued.current.delete(index);
        calcQueue.current.shift();
        continue;
      }
      await runSingleCalculation(index);
      calcQueue.current.shift();
    }

    setActiveCalcIndex(null);
    processingQueue.current = false;
  };

  const runSingleCalculation = async (index) => {
    const ind = indicatorsRef.current[index];
    const gen = (pollGeneration.current[index] || 0) + 1;
    pollGeneration.current[index] = gen;

    setActiveCalcIndex(index);
    setCalcProgress(prev => ({ ...prev, [index]: 0.02 }));

    try {
      let sessionId = currentSessionIdRef.current;
      if (!sessionId) {
        const rtype = RTYPE_MAP[barPeriod];
        const symbolType = (hasContinuousSymbols && contractType === 'continuous') ? 'continuous' : 'raw_symbol';
        const res = await fetch('/api/explorer/session', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            publisher_id: selectedPublisherId, rtype,
            symbols: [...selectedSymbols].sort(),
            start_date: startDate || null, end_date: endDate || null,
            symbol_type: symbolType,
          })
        });
        if (!res.ok) throw new Error(`Session request failed (${res.status})`);
        const data = await res.json();
        sessionId = data.session_id;
        setCurrentSessionId(sessionId);
      }
      setCalcProgress(prev => ({ ...prev, [index]: 0.05 }));
      if (pollGeneration.current[index] !== gen) return;

      const symbolType = (hasContinuousSymbols && contractType === 'continuous') ? 'continuous' : 'raw_symbol';
      const res = await fetch('/api/explorer/run-single', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          symbols: selectedSymbols, rtype: RTYPE_MAP[barPeriod],
          publisher_id: selectedPublisherId,
          start_date: startDate || null, end_date: endDate || null,
          indicator: { class_name: ind.class_name, params: ind.paramsDict },
          symbol_type: symbolType,
        })
      });
      if (!res.ok) throw new Error(`Run request failed (${res.status})`);
      const data = await res.json();
      pendingRunIds.current[index] = data.run_id;
      if (data.indicator_name) {
        setIndicators(prev => {
          const next = [...prev];
          next[index] = { ...next[index], computedName: data.indicator_name };
          return next;
        });
      }
      setCalcProgress(prev => ({ ...prev, [index]: 0.08 }));
      if (pollGeneration.current[index] !== gen) return;

      let outcome;
      if (data.cached) {
        setCalcProgress(prev => ({ ...prev, [index]: 0.85 }));
        outcome = 'completed';
      } else {
        outcome = await pollIndicatorStatusAsync(index, data.run_id, gen);
      }
      if (outcome !== 'completed') return;

      await markIndicatorComplete(index, data.run_id);
      setCalcProgress(prev => ({ ...prev, [index]: 0.92 }));

      // Await segment load — markIndicatorComplete queued state updates
      // (setIndicatorRuns, setIndicatorCompletionCount) that will trigger the
      // loadSegments useEffect after React flushes. The useEffect resolves
      // this promise when loadSegments completes.
      await new Promise(resolve => { segmentLoadResolver.current = resolve; });
      if (pollGeneration.current[index] !== gen) return;

      setCalcProgress(prev => ({ ...prev, [index]: 1.0 }));
      await new Promise(r => setTimeout(r, 200));
      setCalcProgress(prev => { const next = {...prev}; delete next[index]; return next; });
    } catch (e) {
      setCalcProgress(prev => { const next = {...prev}; delete next[index]; return next; });
      setCalculatingSet(prev => { const next = new Set(prev); next.delete(index); return next; });
      if (e.message !== 'cancelled') {
        alert('Calculation failed: ' + e.message);
      }
    }
  };

  const handleAbort = async (index) => {
    const isActive = calcQueue.current.length > 0 && calcQueue.current[0] === index;

    if (isActive) {
      const runId = pendingRunIds.current[index];
      if (runId) {
        pollGeneration.current[index] = (pollGeneration.current[index] || 0) + 1;
        try {
          await fetch(`/api/explorer/cancel/${runId}`, { method: 'POST' });
        } catch (e) {
          console.error('Failed to cancel run:', e);
        }
        delete pendingRunIds.current[index];
      }
      if (segmentLoadResolver.current) {
        const resolver = segmentLoadResolver.current;
        segmentLoadResolver.current = null;
        resolver();
      }
    } else {
      abortedWhileQueued.current.add(index);
    }

    setCalcProgress(prev => { const next = {...prev}; delete next[index]; return next; });
    setCalculatingSet(prev => { const next = new Set(prev); next.delete(index); return next; });
  };

  const pollIndicatorStatusAsync = (index, runId, gen) => {
    return new Promise((resolve, reject) => {
      let unknownCount = 0;
      const poll = () => {
        if (pollGeneration.current[index] !== gen) { resolve('generation_mismatch'); return; }
        fetch(`/api/explorer/status/${runId}`).then(r => r.json()).then(d => {
          if (pollGeneration.current[index] !== gen) { resolve('generation_mismatch'); return; }
          if (d.status === 'completed') {
            setCalcProgress(prev => ({ ...prev, [index]: 0.85 }));
            resolve('completed');
          } else if (d.status === 'cancelled') {
            setCalcProgress(prev => { const next = {...prev}; delete next[index]; return next; });
            setCalculatingSet(prev => { const next = new Set(prev); next.delete(index); return next; });
            delete pendingRunIds.current[index];
            resolve('cancelled');
          } else if (d.status && d.status.startsWith('error')) {
            setCalcProgress(prev => { const next = {...prev}; delete next[index]; return next; });
            setCalculatingSet(prev => { const next = new Set(prev); next.delete(index); return next; });
            reject(new Error(d.status));
          } else {
            if (d.status === 'unknown') {
              unknownCount++;
              if (unknownCount > 120) { reject(new Error('Run not found on server')); return; }
            }
            setCalcProgress(prev => ({ ...prev, [index]: 0.08 + (d.progress || 0) * 0.77 }));
            setTimeout(poll, 500);
          }
        }).catch(reject);
      };
      poll();
    });
  };

  const markIndicatorComplete = async (index, runId) => {
    let computedName = null;
    try {
      const res = await fetch(`/api/runs/${runId}/indicators`);
      const data = await res.json();
      const ohlcv = new Set(["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]);
      const names = (data.indicators || []).filter(n => !ohlcv.has(n));
      if (names.length > 0) computedName = names[0];
    } catch (e) {
      console.error("Failed to fetch indicator names", e);
    }

    setIndicators(prev => {
      const next = [...prev];
      next[index] = {
        ...next[index],
        savedParams: [...next[index].params],
        savedParamsDict: JSON.parse(JSON.stringify(next[index].paramsDict)),
        needsCalculation: false,
        computedName: computedName,
      };
      return next;
    });
    setIndicatorRuns(prev => ({ ...prev, [index]: { run_id: runId, status: 'completed' } }));
    setCalculatingSet(prev => { const next = new Set(prev); next.delete(index); return next; });
    delete pendingRunIds.current[index];
    setIndicatorCompletionCount(c => c + 1);
  };

  // ─── Chart segments loading ───
  const loadSegments = useCallback(async () => {
    if (!currentSessionId) return;
    if (segmentAbortRef.current) segmentAbortRef.current.abort();
    const controller = new AbortController();
    segmentAbortRef.current = controller;
    try {
      let url, res, data;
      const runIdsParam = activeRunIds.length > 0 ? `&run_ids=${activeRunIds.join(',')}` : '';
      if (displayTab === 'bars') {
        url = `/api/sessions/${currentSessionId}/chart-segments?mode=bars&bars_per_chart=${barsPerChart}${runIdsParam}`;
        res = await fetch(url, { signal: controller.signal });
        data = await res.json();
      } else if (displayTab === 'time') {
        url = `/api/sessions/${currentSessionId}/chart-segments?mode=time&time_period=${timePeriod}${runIdsParam}`;
        res = await fetch(url, { signal: controller.signal });
        data = await res.json();
      } else if (displayTab === 'condition') {
        return; // Condition filtering is manual via the Filter button
      }
      if (!controller.signal.aborted) {
        setSegments(data.segments || []);
        setExpandedRows({});
        setChartCache({});
      }
    } catch (e) {
      if (e.name === 'AbortError') return;
      console.error('Failed to load segments', e);
    }
  }, [currentSessionId, displayTab, barsPerChart, timePeriod, activeRunIds.join(',')]);

  // ─── Load segments when session/tab/settings change ───
  useEffect(() => {
    if (currentSessionId) {
      if (initialSegmentsLoadedRef.current) {
        initialSegmentsLoadedRef.current = false;
        if (segmentLoadResolver.current) {
          const resolver = segmentLoadResolver.current;
          segmentLoadResolver.current = null;
          resolver();
        }
        return;
      }
      loadSegments().finally(() => {
        if (segmentLoadResolver.current) {
          const resolver = segmentLoadResolver.current;
          segmentLoadResolver.current = null;
          resolver();
        }
      });
    }
    return () => {
      if (segmentAbortRef.current) segmentAbortRef.current.abort();
    };
  }, [currentSessionId, displayTab, barsPerChart, timePeriod, loadSegments, indicatorCompletionCount]);

  // ─── Save chart settings after indicator calculation completes ───
  useEffect(() => {
    if (currentSessionId && indicatorCompletionCount > 0) {
      saveChartSettings();
    }
  }, [indicatorCompletionCount, saveChartSettings, currentSessionId]);

  // ─── Background filter (condition tab) ───
  const startFilter = async () => {
    if (isFiltering || conditions.length === 0 || !currentSessionId) return;
    setIsFiltering(true);
    setFilterProgress(0.02);
    setSegments([]);
    setExpandedRows({});
    setChartCache({});
    try {
      const condSpecs = conditions.map(c => ({
        left_field: c.left, operator: c.op,
        ...(c.right === '(Value)' ? { right_value: c.value } : { right_field: c.right }),
      }));
      const res = await fetch(`/api/sessions/${currentSessionId}/start-filter`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conditions: condSpecs, context_bars: contextBars, gap_tolerance: gapTolerance, ...(activeRunIds.length > 0 ? { run_ids: activeRunIds } : {}) }),
      });
      const { filter_id } = await res.json();
      filterIdRef.current = filter_id;
      // Poll for status
      const poll = () => {
        fetch(`/api/filter-status/${filter_id}`).then(r => r.json()).then(d => {
          if (filterIdRef.current !== filter_id) return; // stale
          if (d.status === 'completed') {
            setSegments(d.segments || []);
            setExpandedRows({});
            setChartCache({});
            setFilterProgress(1.0);
            setTimeout(() => {
              setIsFiltering(false);
              setFilterProgress(0);
              filterIdRef.current = null;
            }, 200);
          } else if (d.status === 'cancelled' || d.status === 'error') {
            setIsFiltering(false);
            setFilterProgress(0);
            filterIdRef.current = null;
            if (d.status === 'error' && d.error) console.error('Filter error:', d.error);
          } else {
            setFilterProgress(d.progress || 0.02);
            filterPollRef.current = setTimeout(poll, 500);
          }
        }).catch(() => {
          setIsFiltering(false);
          setFilterProgress(0);
          filterIdRef.current = null;
        });
      };
      filterPollRef.current = setTimeout(poll, 500);
    } catch (e) {
      console.error('Failed to start filter', e);
      setIsFiltering(false);
      setFilterProgress(0);
    }
  };

  const abortFilter = async () => {
    const fid = filterIdRef.current;
    if (fid) {
      try { await fetch(`/api/cancel-filter/${fid}`, { method: 'POST' }); } catch (e) {}
    }
    if (filterPollRef.current) clearTimeout(filterPollRef.current);
    filterIdRef.current = null;
    setIsFiltering(false);
    setFilterProgress(0);
  };

  // ─── Toggle segment row expansion ───
  const toggleRowExpand = (index) => {
    setExpandedRows(prev => ({ ...prev, [index]: !prev[index] }));
  };

  // ─── Data Source Presets ───
  const saveDsPreset = async () => {
    const name = dsPresetName.trim();
    if (!name) { alert('Enter a preset name'); return; }
    const rtype = RTYPE_MAP[barPeriod];
    if (!rtype) { alert('Select a bar period first'); return; }
    if (!selectedPublisherId) { alert('Select a publisher and dataset first'); return; }
    const symbolType = (hasContinuousSymbols && contractType === 'continuous') ? 'continuous' : 'raw_symbol';
    const exists = dsPresets.some(p => p.name === name);
    const method = exists ? 'PUT' : 'POST';
    const apiUrl = exists ? `/api/presets/${encodeURIComponent(name)}` : '/api/presets';
    await fetch(apiUrl, {
      method, headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name, rtype, publisher_name: provider, publisher_id: selectedPublisherId,
        symbols: selectedSymbols, symbol_type: symbolType,
      })
    });
    setDsPresetName("");
    const res = await fetch('/api/presets');
    const d = await res.json();
    setDsPresets(d.presets || []);
    setDsPreset(name);
  };

  const deleteDsPreset = async () => {
    if (!dsPreset) { alert('Select a preset to delete'); return; }
    if (!confirm('Delete preset "' + dsPreset + '"?')) return;
    await fetch(`/api/presets/${encodeURIComponent(dsPreset)}`, { method: 'DELETE' });
    const res = await fetch('/api/presets');
    const d = await res.json();
    setDsPresets(d.presets || []);
    setDsPreset("");
  };

  const loadDsPreset = async (name) => {
    const preset = dsPresets.find(p => p.name === name);
    if (!preset) { setDsPreset(name); return; }
    setDsPreset(name);

    try {
      const rtype = preset.rtype;
      const rtypeLabel = RTYPE_LABELS[rtype] || '';

      const [pubData, dsData, covData] = await Promise.all([
        fetch(`/api/secmaster/publishers?rtype=${rtype}`).then(r => r.json()),
        fetch(`/api/secmaster/publishers/${encodeURIComponent(preset.publisher_name)}/datasets?rtype=${rtype}`).then(r => r.json()),
        fetch(`/api/secmaster/symbols_coverage?publisher_id=${preset.publisher_id}&rtype=${rtype}`).then(r => r.json()),
      ]);

      const pubs = pubData.publishers || [];
      const dsList = dsData.datasets || [];
      const all = covData.symbols || [];
      const matchingDs = dsList.find(d => d.publisher_id === preset.publisher_id);
      const hasCont = all.some(r => r.symbol_type === 'continuous');
      const ctype = (preset.symbol_type === 'continuous' && hasCont) ? 'continuous' : 'outrights';

      // Ref set AFTER await, BEFORE state — no render can intervene
      skipSymbolClearRef.current = true;

      setBarPeriod(rtypeLabel);
      setPublishers(pubs);
      setProvider(preset.publisher_name);
      setDatasets(dsList);
      if (matchingDs) {
        setExchange(matchingDs.dataset);
        setSelectedPublisherId(matchingDs.publisher_id);
      }
      setAllCoverageData(all);
      setHasContinuousSymbols(hasCont);
      setContractType(ctype);
      filterAndSetCoverage(all, ctype, hasCont);

      let filtered = all;
      if (hasCont) {
        if (ctype === 'continuous') filtered = all.filter(r => r.symbol_type === 'continuous');
        else filtered = all.filter(r => r.symbol_type === 'raw_symbol' && !r.symbol.includes('-'));
      }
      const availableSyms = filtered.map(r => r.symbol);
      const validSymbols = (preset.symbols || []).filter(s => availableSyms.includes(s));
      setSelectedSymbols(validSymbols);

      // Explicit date computation (hook 5 is suppressed during loading)
      let minTs = null, maxTs = null;
      validSymbols.forEach(s => {
        const covEntry = all.find(r => r.symbol === s);
        if (covEntry) {
          if (minTs === null || covEntry.min_ts < minTs) minTs = covEntry.min_ts;
          if (maxTs === null || covEntry.max_ts > maxTs) maxTs = covEntry.max_ts;
        }
      });
      if (minTs !== null) {
        setStartDate(new Date(Math.floor(minTs / 1000000)).toISOString().split('T')[0]);
        setEndDate(new Date(Math.floor(maxTs / 1000000)).toISOString().split('T')[0]);
      } else {
        setStartDate("");
        setEndDate("");
      }
    } catch (e) {
      skipSymbolClearRef.current = false;
      console.error('Failed to apply data source preset', e);
    }
  };

  // ─── Load from Split ───
  const loadSplitSource = async (sourceName) => {
    if (!sourceName) return;
    setSelectedSplitSource(sourceName);
    const source = splitSources.find(s => s.source_name === sourceName);
    if (!source) return;

    try {
      const rtype = source.rtype;
      const rtypeLabel = RTYPE_LABELS[rtype] || '';

      const [pubData, dsData, covData] = await Promise.all([
        fetch(`/api/secmaster/publishers?rtype=${rtype}`).then(r => r.json()),
        fetch(`/api/secmaster/publishers/${encodeURIComponent(source.publisher_name)}/datasets?rtype=${rtype}`).then(r => r.json()),
        fetch(`/api/secmaster/symbols_coverage?publisher_id=${source.publisher_id}&rtype=${rtype}`).then(r => r.json()),
      ]);

      const pubs = pubData.publishers || [];
      const dsList = dsData.datasets || [];
      const all = covData.symbols || [];
      const matchingDs = dsList.find(d => d.publisher_id === source.publisher_id);
      const hasCont = all.some(r => r.symbol_type === 'continuous');
      const ctype = (source.symbol_type === 'continuous' && hasCont) ? 'continuous' : 'outrights';

      // Ref set AFTER await, BEFORE state — no render can intervene
      skipSymbolClearRef.current = true;

      setBarPeriod(rtypeLabel);
      setPublishers(pubs);
      setProvider(source.publisher_name);
      setDatasets(dsList);
      if (matchingDs) {
        setExchange(matchingDs.dataset);
        setSelectedPublisherId(matchingDs.publisher_id);
      }
      setAllCoverageData(all);
      setHasContinuousSymbols(hasCont);
      setContractType(ctype);
      filterAndSetCoverage(all, ctype, hasCont);

      let filtered = all;
      if (hasCont) {
        if (ctype === 'continuous') filtered = all.filter(r => r.symbol_type === 'continuous');
        else filtered = all.filter(r => r.symbol_type === 'raw_symbol' && !r.symbol.includes('-'));
      }
      const availableSyms = filtered.map(r => r.symbol);
      const validSymbols = (source.symbols || []).filter(s => availableSyms.includes(s));
      setSelectedSymbols(validSymbols);
      setStartDate(source.start_date);
      setEndDate(source.end_date);
    } catch (e) {
      skipSymbolClearRef.current = false;
      console.error('Failed to apply split source', e);
    }
  };

  // ─── Indicator Presets ───
  const saveIndPreset = async () => {
    const name = indPresetName.trim();
    if (!name) { alert('Enter a preset name'); return; }
    const config = {
      indicators: indicators.map(ind => ({
        class_name: ind.class_name,
        params: ind.paramsDict,
        chart: { panel: ind.panel, below_price: ind.panel !== 0, style: ind.style, color: ind.color, width: ind.width, visible: ind.visible },
      })),
      fill_between: fillBetweens,
      chart_type: chartType,
    };
    const exists = indPresets.some(p => p.name === name);
    const method = exists ? 'PUT' : 'POST';
    const apiUrl = exists ? `/api/explore/presets/${encodeURIComponent(name)}` : '/api/explore/presets';
    await fetch(apiUrl, {
      method, headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, config }),
    });
    setIndPresetName("");
    const res = await fetch('/api/explore/presets');
    const d = await res.json();
    setIndPresets(d.presets || []);
    setIndPreset(name);
  };

  const deleteIndPreset = async () => {
    if (!indPreset) { alert('Select a preset to delete'); return; }
    if (!confirm('Delete preset "' + indPreset + '"?')) return;
    await fetch(`/api/explore/presets/${encodeURIComponent(indPreset)}`, { method: 'DELETE' });
    const res = await fetch('/api/explore/presets');
    const d = await res.json();
    setIndPresets(d.presets || []);
    setIndPreset("");
  };

  const loadIndPreset = (name) => {
    const preset = indPresets.find(p => p.name === name);
    setIndPreset(name);
    if (!preset || !preset.config) return;
    const config = preset.config;
    const newIndicators = (config.indicators || []).map(ind => {
      const meta = availableIndicatorsData.find(a => a.class_name === ind.class_name);
      const paramsMeta = meta ? (meta.params || []) : [];
      const paramsDict = ind.params || {};
      const paramValues = paramsMeta.map(p => String(paramsDict[p.name] ?? p.default ?? ''));
      paramsMeta.forEach(p => {
        if (p.type === 'indicator_class' && p.kwargs_name && !(p.kwargs_name in paramsDict)) {
          const selectedSource = paramsDict[p.name] || p.default || '';
          const subParams = (p.source_params || {})[selectedSource] || [];
          const kwargsDict = {};
          subParams.forEach(sp => { kwargsDict[sp.name] = sp.default; });
          paramsDict[p.kwargs_name] = kwargsDict;
        }
      });
      const chart = ind.chart || {};
      return {
        indicator: ind.class_name,
        class_name: ind.class_name,
        params: paramValues,
        paramsMeta,
        paramsDict,
        savedParams: [...paramValues],
        savedParamsDict: JSON.parse(JSON.stringify(paramsDict)),
        panel: chart.panel !== undefined ? chart.panel : 0,
        style: chart.style || 'line',
        color: chart.color || 'blue',
        width: chart.width || 'normal',
        visible: chart.visible !== undefined ? chart.visible : true,
        needsCalculation: true,
      };
    });
    setIndicators(newIndicators);
    setFillBetweens(config.fill_between || []);
    if (config.chart_type) setChartType(config.chart_type);
    setCurrentSessionId(null);
    setIndicatorRuns({});
  };

  // ─── Condition Presets ───
  const saveCondPreset = async () => {
    const name = condPresetName.trim();
    if (!name) { alert('Enter a preset name'); return; }
    const config = {
      conditions: conditions.map(c => ({ leftField: c.left, operator: c.op, rightField: c.right !== '(Value)' ? c.right : null, rightValue: c.right === '(Value)' ? c.value : null })),
      contextBars, gapTolerance,
    };
    const exists = condPresets.some(p => p.name === name);
    const method = exists ? 'PUT' : 'POST';
    const apiUrl = exists ? `/api/explore/condition-presets/${encodeURIComponent(name)}` : '/api/explore/condition-presets';
    await fetch(apiUrl, {
      method, headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, config }),
    });
    setCondPresetName("");
    const res = await fetch('/api/explore/condition-presets');
    const d = await res.json();
    setCondPresets(d.presets || []);
    setCondPreset(name);
  };

  const deleteCondPreset = async () => {
    if (!condPreset) { alert('Select a preset to delete'); return; }
    if (!confirm('Delete preset "' + condPreset + '"?')) return;
    await fetch(`/api/explore/condition-presets/${encodeURIComponent(condPreset)}`, { method: 'DELETE' });
    const res = await fetch('/api/explore/condition-presets');
    const d = await res.json();
    setCondPresets(d.presets || []);
    setCondPreset("");
  };

  const loadCondPreset = (name) => {
    const preset = condPresets.find(p => p.name === name);
    setCondPreset(name);
    if (!preset || !preset.config) return;
    const config = preset.config;
    const newConditions = (config.conditions || []).map(c => ({
      left: c.leftField, op: c.operator,
      right: c.rightField || '(Value)',
      value: c.rightValue != null ? c.rightValue : null,
    }));
    setConditions(newConditions);
    if (config.contextBars != null) setContextBars(config.contextBars);
    if (config.gapTolerance != null) setGapTolerance(config.gapTolerance);
  };

  // ─── Bar period options from rtypes ───
  const barPeriodOptions = rtypes.map(r => ({
    value: RTYPE_LABELS[r] || 'rtype ' + r,
    label: RTYPE_LABELS[r] || 'rtype ' + r,
  }));

  // ─── Publisher (provider) options ───
  const providerOptions = publishers.map(p => ({
    value: p,
    label: capitalize(p),
  }));

  // ─── Dataset (venue/exchange) options ───
  const venueOptions = datasets.map(d => ({
    value: d.dataset,
    label: d.dataset,
    publisher_id: d.publisher_id,
  }));

  const handleVenueChange = (datasetLabel) => {
    setExchange(datasetLabel);
    const ds = datasets.find(d => d.dataset === datasetLabel);
    if (ds) {
      setSelectedPublisherId(ds.publisher_id);
    }
  };

  // ─── Time period options for current rtype ───
  const currentRtype = barPeriod ? RTYPE_MAP[barPeriod] : null;
  const availableTimePeriods = (currentRtype && TIME_PERIODS_BY_RTYPE[currentRtype]) ? TIME_PERIODS_BY_RTYPE[currentRtype] : TIME_PERIODS;
  const timePeriodOptions = availableTimePeriods.map(p => ({
    value: p,
    label: TIME_PERIOD_LABELS[p] || p,
  }));

  // Ensure current timePeriod is valid for the rtype
  useEffect(() => {
    if (availableTimePeriods.indexOf(timePeriod) === -1 && availableTimePeriods.length > 0) {
      setTimePeriod(availableTimePeriods[0]);
    }
  }, [availableTimePeriods, timePeriod]);

  return (
    <div style={st.appShell}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=JetBrains+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        input[type="date"]::-webkit-calendar-picker-indicator { filter: invert(0.5); cursor: pointer; }
        input[type="number"]::-webkit-inner-spin-button { opacity: 0.3; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #475569; }
        button:hover { filter: brightness(1.15); }
      `}</style>

      <Sidebar activePage={activePage} onNavigate={(page) => {
        if (page === "splits") { window.location.href = "/splits"; return; }
        if (page === "backtest") { window.location.href = "/backtest"; return; }
        setActivePage(page);
      }} />

      <div style={st.mainContent}>
        {activePage === "explorer" && (
          <div style={st.page}>

      {/* ─── Page Header ─── */}
      <div style={st.header}>
        <div>
          <h1 style={st.pageTitle}>Explore Charts</h1>
          <p style={st.pageSubtitle}>Explore market data and filter for signals</p>
        </div>
      </div>

      {/* ─── TOP ROW: 2 columns ─── */}
      <div style={st.topGrid}>

        {/* ── Box 1: Data Source ── */}
        <div style={{ ...st.card, position: "relative", zIndex: 1 }}>
          <SectionHeader icon={<Icons.Database />} number="01" title="Data Source" subtitle="Select market data to explore"
            right={<PresetBar presets={dsPresets} selected={dsPreset} onSelect={loadDsPreset} presetName={dsPresetName} onNameChange={setDsPresetName} onSave={saveDsPreset} onDelete={deleteDsPreset} />}
          />

          {splitSources.length > 0 && (
            <div style={{ marginBottom: "10px" }}>
              <Select value={selectedSplitSource} onChange={(val) => { setSelectedSplitSource(val); loadSplitSource(val); }}
                options={splitSourceOptions} placeholder="Load from Split..." grouped />
              <label style={st.labelBelow}>Split Selection</label>
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
            <div>
              <Select value={barPeriod} onChange={setBarPeriod} options={barPeriodOptions} placeholder="Select..." />
              <label style={st.labelBelow}>Bar Period</label>
            </div>
            <div>
              <Select value={provider} onChange={setProvider} options={providerOptions} placeholder="Select..." />
              <label style={st.labelBelow}>Dataset</label>
            </div>
            <div>
              <Select value={exchange} onChange={handleVenueChange} options={venueOptions.map(v => ({ value: v.value, label: v.label }))} placeholder="Select..." />
              <label style={st.labelBelow}>Venue</label>
            </div>
          </div>

          {/* Contract type selector (only shown when continuous symbols exist) */}
          {hasContinuousSymbols && (
            <div style={{ marginTop: "10px" }}>
              <div style={st.tabs}>
                {['outrights', 'continuous', 'spreads'].map(ct => (
                  <button key={ct} onClick={() => setContractType(ct)}
                    style={{ ...st.tab, ...(contractType === ct ? st.tabActive : {}) }}>
                    {capitalize(ct)}
                  </button>
                ))}
              </div>
              <label style={st.labelBelow}>Contract Type</label>
            </div>
          )}

          {/* Symbols — tag input style */}
          <div style={{ marginTop: "31.5px", position: "relative" }} ref={symbolRef}>
            <div style={st.tagInputWrap} onClick={() => document.getElementById('sym-search')?.focus()}>
              {selectedSymbols.map((sym) => (
                <Chip key={sym} label={sym} onRemove={() => setSelectedSymbols(selectedSymbols.filter((s) => s !== sym))} />
              ))}
              <input id="sym-search" type="text" value={symbolSearch}
                onChange={(e) => { setSymbolSearch(e.target.value); setShowSymbolDropdown(true); }}
                onFocus={() => setShowSymbolDropdown(true)}
                placeholder={selectedSymbols.length === 0 ? "Search symbols..." : ""}
                style={st.tagSearchInput} />
            </div>
            <label style={st.labelBelow}>Symbols</label>
            {showSymbolDropdown && coverageSymbols.length > 0 && (symbolSearch === "" || filteredSymbols.length > 0) && (
              <div style={{ ...st.dropdown, position: "absolute", left: 0, right: 0, marginTop: "4px", zIndex: 200 }}>
                {symbolSearch === "" && (
                  <>
                    <div style={{ padding: "4px 10px 3px", fontSize: "9px", fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.5px" }}>Add all symbols</div>
                    <button onClick={() => {
                      const allSyms = coverageSymbols.filter(s => !selectedSymbols.includes(s));
                      setSelectedSymbols([...selectedSymbols, ...allSyms]);
                      setShowSymbolDropdown(false);
                    }} style={{ ...st.dropdownItem, display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "11px" }}>{exchange || "All"}</span>
                      <span style={{ fontSize: "10px", color: "#475569" }}>-- all symbols</span>
                    </button>
                    <div style={{ height: "1px", background: "rgba(51,65,85,0.4)", margin: "3px 6px" }} />
                    <div style={{ padding: "4px 10px 3px", fontSize: "9px", fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.5px" }}>Individual symbols</div>
                  </>
                )}
                {filteredSymbols.slice(0, 100).map((sym) => (
                  <button key={sym} onClick={() => { setSelectedSymbols([...selectedSymbols, sym]); setSymbolSearch(""); setShowSymbolDropdown(false); }} style={st.dropdownItem}>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "11px" }}>{sym}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Date Range — pinned to bottom */}
          <div style={{ marginTop: "auto", paddingTop: "10px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={{ ...st.dateInput, flex: 1 }} />
              <span style={{ color: "#475569", fontSize: "12px", flexShrink: 0 }}>--</span>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={{ ...st.dateInput, flex: 1 }} />
            </div>
          </div>
        </div>

        {/* ── Box 2: Indicators & Chart Settings (merged) ── */}
        <div style={{ ...st.card, position: "relative", zIndex: 1 }}>
          <SectionHeader icon={<Icons.Activity />} number="02" title="Indicators" subtitle="Add indicators and configure visualization"
            right={<PresetBar presets={indPresets} selected={indPreset} onSelect={loadIndPreset} presetName={indPresetName} onNameChange={setIndPresetName} onSave={saveIndPreset} onDelete={deleteIndPreset} />}
          />

          {/* Indicator list — sorted by panel position, collapsible */}
          {indicators.length > 0 ? (
            <div style={st.indicatorList}>
              {sortedIndicators.map((ind) => {
                const i = ind.origIndex;
                const isExpanded = expandedCards[i];
                const isDirty = paramsChanged(ind) || ind.needsCalculation;
                const isCalculating = calculatingSet.has(i);
                const isActive = activeCalcIndex === i;
                const isQueued = isCalculating && !isActive;
                return (
                  <div key={i} style={{
                    ...st.indCard,
                    opacity: ind.visible ? 1 : 0.4,
                  }}>
                    {/* Collapsed row */}
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}
                      onClick={(e) => {
                        if (e.target.closest('button')) return;
                        toggleExpand(i);
                      }}>
                      <div style={{ ...st.iconBtn, color: "#64748b", transition: "transform 0.15s", transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)" }}>
                        <Icons.ChevronRight />
                      </div>
                      <span style={st.indName}>{ind.computedName || displayName(ind.indicator)}</span>
                      {isDirty && <span style={st.newBadge}>modified</span>}
                      {isActive && (calcProgress[i] || 0) > 0 && <span style={{ ...st.newBadge, color: "#fbbf24", background: "rgba(251,191,36,0.12)", borderColor: "rgba(251,191,36,0.25)" }}>calculating...</span>}
                      {isQueued && <span style={{ ...st.newBadge, color: "#94a3b8", background: "rgba(148,163,184,0.12)", borderColor: "rgba(148,163,184,0.25)" }}>queued...</span>}
                      <div style={{ flex: 1 }} />
                      <button onClick={() => updateIndicator(i, "visible", !ind.visible)}
                        style={{ ...st.iconBtn, color: ind.visible ? "#818cf8" : "#475569" }}>
                        {ind.visible ? <Icons.Eye /> : <Icons.EyeOff />}
                      </button>
                      <button onClick={() => removeIndicator(i)} style={{ ...st.iconBtn, color: "#475569" }}>
                        <Icons.X />
                      </button>
                    </div>
                    {isActive && (calcProgress[i] || 0) > 0 && (
                      <div style={{ height: "2px", background: "rgba(51,65,85,0.3)", borderRadius: "1px", marginTop: "4px", overflow: "hidden" }}>
                        <div style={{
                          height: "100%",
                          width: `${(calcProgress[i] || 0) * 100}%`,
                          background: "linear-gradient(90deg, #fbbf24, #f59e0b)",
                          borderRadius: "1px",
                          transition: "width 0.3s ease",
                        }} />
                      </div>
                    )}
                    {/* Expanded section */}
                    {isExpanded && (
                      <div style={{ paddingLeft: "28px", paddingTop: "10px", marginTop: "8px", borderTop: "1px solid rgba(51,65,85,0.3)" }}>
                        {/* Indicator Parameters */}
                        <div style={{ marginBottom: "10px" }}>
                          <span style={st.expandSectionLabel}>Indicator Parameters</span>
                          <div style={{ display: "flex", alignItems: "flex-end", marginTop: "6px" }}>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "flex-end", flex: 1 }}>
                              {ind.paramsMeta && ind.paramsMeta.map((pm, pi) => {
                                if (pm.type === 'indicator_class') {
                                  const sourceValue = ind.params[pi];
                                  const subParams = (pm.source_params && pm.source_params[sourceValue]) || [];
                                  const kwargsDict = (pm.kwargs_name && ind.paramsDict[pm.kwargs_name]) || {};
                                  return (
                                    <React.Fragment key={pi}>
                                      <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                                        <span style={{ fontSize: "9px", color: "#64748b", textTransform: "uppercase" }}>{pm.name.replace(/_/g, ' ')}</span>
                                        <Select value={sourceValue} onChange={(v) => updateParam(i, pi, v, pm)}
                                          options={pm.choices || []} small />
                                      </div>
                                      {subParams.map(sp => (
                                        <div key={sp.name} style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                                          <span style={{ fontSize: "9px", color: "#8b7dcf", textTransform: "uppercase" }}>{sp.name.replace(/_/g, ' ')}</span>
                                          {sp.type === 'enum' ? (
                                            <Select value={kwargsDict[sp.name] ?? sp.default ?? ''} onChange={(v) => updateSourceSubParam(i, pm.kwargs_name, sp.name, v, sp)}
                                              options={sp.choices || []} small />
                                          ) : (
                                            <input type="text" value={kwargsDict[sp.name] ?? sp.default ?? ''}
                                              onChange={(e) => updateSourceSubParam(i, pm.kwargs_name, sp.name, e.target.value, sp)}
                                              style={{ ...st.paramInput, borderColor: "rgba(51,65,85,0.4)" }} />
                                          )}
                                        </div>
                                      ))}
                                    </React.Fragment>
                                  );
                                }
                                return (
                                  <div key={pi} style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                                    <span style={{ fontSize: "9px", color: "#64748b", textTransform: "uppercase" }}>{pm.name.replace(/_/g, ' ')}</span>
                                    {pm.type === 'enum' ? (
                                      <Select value={ind.params[pi]} onChange={(v) => updateParam(i, pi, v, pm)}
                                        options={pm.choices || []} small />
                                    ) : (
                                      <input type="text" value={ind.params[pi]}
                                        onChange={(e) => updateParam(i, pi, e.target.value, pm)}
                                        style={{ ...st.paramInput, borderColor: ind.params[pi] !== (ind.savedParams[pi] || "") ? "rgba(251,191,36,0.5)" : "rgba(51,65,85,0.4)" }} />
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                            {isDirty && (
                              isCalculating ? (
                                <button onClick={() => handleAbort(i)}
                                  style={{ ...st.doneBtn, background: "linear-gradient(135deg, #dc2626 0%, #ef4444 100%)",
                                           boxShadow: "0 2px 10px rgba(239,68,68,0.25)" }}>
                                  <Icons.Stop />
                                  <span>Abort</span>
                                </button>
                              ) : (
                                <button onClick={() => enqueueCalculation(i)} style={st.doneBtn}>
                                  <Icons.Play />
                                  <span>Calculate</span>
                                </button>
                              )
                            )}
                          </div>
                        </div>
                        {/* Separator */}
                        <div style={{ height: "1px", background: "rgba(51,65,85,0.3)", margin: "10px 0" }} />
                        {/* Chart Display Settings */}
                        <div>
                          <span style={st.expandSectionLabel}>Chart Display</span>
                          <div style={{ display: "flex", gap: "10px", alignItems: "center", marginTop: "6px" }}>
                            <div style={st.propGroup}>
                              <span style={st.propLabel}>Panel</span>
                              <PanelChip value={ind.panel} onChange={(v) => updateIndicator(i, "panel", v)} />
                            </div>
                            <div style={st.propGroup}>
                              <span style={st.propLabel}>Style</span>
                              <Select value={ind.style} onChange={(v) => updateIndicator(i, "style", v)} options={STYLES.map(s => ({ value: s, label: formatParamName(s) }))} small />
                            </div>
                            <div style={st.propGroup}>
                              <span style={st.propLabel}>Color</span>
                              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                                <div style={{ width: "8px", height: "8px", borderRadius: "2px", background: colorToHex(ind.color), flexShrink: 0 }} />
                                <Select value={ind.color} onChange={(v) => updateIndicator(i, "color", v)} options={COLORS.map(s => ({ value: s, label: formatParamName(s) }))} small />
                              </div>
                            </div>
                            <div style={st.propGroup}>
                              <span style={st.propLabel}>Width</span>
                              <Select value={ind.width} onChange={(v) => updateIndicator(i, "width", v)} options={WIDTHS.map(s => ({ value: s, label: formatParamName(s) }))} small />
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={st.emptyState}>No indicators added -- select one below to get started</div>
          )}

          {/* Fill Between entries */}
          {fillBetweens.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "5px", marginTop: "10px" }}>
              <span style={{ fontSize: "9.5px", fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.5px" }}>Fill Between</span>
              {fillBetweens.map((fb, i) => (
                  <div key={i} style={{ ...st.fillBetweenRow, alignItems: "start" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 16px", flex: 1 }}>
                      <div style={st.propGroup}>
                        <span style={st.propLabel}>Upper</span>
                        <Select value={fb.upper} onChange={(v) => updateFillBetween(i, "upper", v)} options={fillBetweenOptions} small />
                      </div>
                      <div style={st.propGroup}>
                        <span style={st.propLabel}>Lower</span>
                        <Select value={fb.lower} onChange={(v) => updateFillBetween(i, "lower", v)} options={fillBetweenOptions} small />
                      </div>
                      <div style={st.propGroup}>
                        <span style={st.propLabel}>Color</span>
                        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                          <div style={{ width: "8px", height: "8px", borderRadius: "2px", background: colorToHex(fb.color), flexShrink: 0 }} />
                          <Select value={fb.color} onChange={(v) => updateFillBetween(i, "color", v)} options={COLORS.map(s => ({ value: s, label: formatParamName(s) }))} small />
                        </div>
                      </div>
                      <div style={st.propGroup}>
                        <span style={st.propLabel}>Alpha</span>
                        <Select value={fb.alpha} onChange={(v) => updateFillBetween(i, "alpha", v)} options={ALPHAS} small />
                      </div>
                    </div>
                    <button onClick={() => removeFillBetween(i)} style={{ ...st.iconBtn, color: "#f87171", paddingTop: "4px" }}>
                      <Icons.X />
                    </button>
                  </div>
              ))}
            </div>
          )}

          {/* Bottom actions */}
          <div style={{ marginTop: "auto", paddingTop: "12px", display: "flex", gap: "8px" }}>
            <AddIndicatorButton options={availableIndicators} onAdd={addIndicator} />
            <button onClick={addFillBetween} style={st.fillBetweenBtn}>
              <Icons.Plus />
              <span>Add Fill Between</span>
            </button>
          </div>
        </div>
      </div>

      {/* ─── BOTTOM ROW: Full-width Chart Display ─── */}
      <div style={{ ...st.card, marginTop: "16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <SectionHeader icon={<Icons.Table />} number="03" title="Chart Display" subtitle="Chart visualization and signal filtering"
            right={displayTab === "condition" ? (
              <PresetBar presets={condPresets} selected={condPreset} onSelect={loadCondPreset} presetName={condPresetName} onNameChange={setCondPresetName} onSave={saveCondPreset} onDelete={deleteCondPreset} />
            ) : null}
          />
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
          <div style={st.tabs}>
            {[
              { key: "bars", label: "By Bars" },
              { key: "time", label: "By Time" },
              { key: "condition", label: "By Signal" },
            ].map((tab) => (
              <button key={tab.key} onClick={() => {
                  setDisplayTab(tab.key);
                  if (tab.key === 'condition') {
                    setSegments([]); setExpandedRows({}); setChartCache({});
                  }
                }}
                style={{ ...st.tab, ...(displayTab === tab.key ? st.tabActive : {}) }}>
                {tab.label}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            {displayTab === "bars" && (
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <label style={{ ...st.label, marginBottom: 0, whiteSpace: "nowrap" }}>Bars per chart</label>
                <input type="number" value={barsPerChart} onChange={(e) => setBarsPerChart(Number(e.target.value))} style={{ ...st.numberInput, width: "80px" }} />
              </div>
            )}
            {displayTab === "time" && (
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <label style={{ ...st.label, marginBottom: 0, whiteSpace: "nowrap" }}>Time Period</label>
                <div style={{ width: "110px" }}>
                  <Select value={timePeriod} onChange={setTimePeriod} options={timePeriodOptions} small />
                </div>
              </div>
            )}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <label style={{ ...st.label, marginBottom: 0, whiteSpace: "nowrap" }}>Chart Type</label>
              <div style={{ width: "130px" }}>
                <Select value={chartType} onChange={setChartType} options={CHART_TYPES} />
              </div>
            </div>
          </div>
        </div>

        {/* Signal filter panel — visible when By Signal tab active */}
        {displayTab === "condition" && (
          <div style={st.signalPanel}>
            {/* Condition builder row */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={st.signalLabel}>Left</span>
                <div style={{ width: "140px" }}><Select value={sigLeft} onChange={setSigLeft} options={leftOptions} small /></div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={st.signalLabel}>Operator</span>
                <div style={{ width: "110px" }}><Select value={sigOp} onChange={setSigOp} options={OPERATORS} small /></div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={st.signalLabel}>Right</span>
                <div style={{ width: "140px" }}><Select value={sigRight} onChange={setSigRight} options={rightOptions} small /></div>
              </div>
              {sigRight === "(Value)" && (
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <span style={st.signalLabel}>Value</span>
                  <input type="number" value={sigValue} onChange={(e) => setSigValue(Number(e.target.value))}
                    style={{ ...st.numberInput, width: "70px" }} />
                </div>
              )}
              <button onClick={addCondition} style={st.addCondBtn}>
                <Icons.Plus />
                <span>Add</span>
              </button>
            </div>

            {/* Conditions list */}
            {conditions.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginTop: "10px" }}>
                {conditions.map((c, i) => (
                  <div key={i} style={st.conditionRow}>
                    <span style={st.conditionText}>
                      {c.left} <span style={st.conditionOp}>{c.op}</span> {c.right === "(Value)" ? c.value : c.right}
                    </span>
                    <button onClick={() => removeCondition(i)} style={{ ...st.iconBtn, color: "#475569" }}><Icons.X /></button>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: "#475569", fontSize: "11.5px", marginTop: "10px", fontStyle: "italic" }}>
                Add a condition above, then click Filter to view chart segments
              </p>
            )}

            {/* Filter / Abort button + progress */}
            {conditions.length > 0 && (
              <div style={{ marginTop: "10px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  {isFiltering ? (
                    <button onClick={abortFilter} style={{ ...st.doneBtn, background: "linear-gradient(135deg, #dc2626 0%, #ef4444 100%)", boxShadow: "0 2px 10px rgba(239,68,68,0.25)" }}>
                      <Icons.Stop />
                      <span>Abort</span>
                    </button>
                  ) : (
                    <button onClick={startFilter} style={st.doneBtn}>
                      <Icons.Play />
                      <span>Filter</span>
                    </button>
                  )}
                  {isFiltering && <span style={{ ...st.newBadge, color: "#fbbf24", background: "rgba(251,191,36,0.12)", borderColor: "rgba(251,191,36,0.25)" }}>filtering...</span>}
                </div>
                {isFiltering && filterProgress > 0 && (
                  <div style={{ height: "2px", background: "rgba(51,65,85,0.3)", borderRadius: "1px", marginTop: "6px", overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${filterProgress * 100}%`, background: "linear-gradient(90deg, #fbbf24, #f59e0b)", borderRadius: "1px", transition: "width 0.3s ease" }} />
                  </div>
                )}
              </div>
            )}

            {/* Context bars & Gap tolerance */}
            <div style={{ display: "flex", gap: "16px", marginTop: "12px", paddingTop: "10px", borderTop: "1px solid rgba(51,65,85,0.3)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={st.signalLabel}>Context bars</span>
                <input type="number" value={contextBars} onChange={(e) => setContextBars(Number(e.target.value))}
                  style={{ ...st.numberInput, width: "65px" }} />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={st.signalLabel}>Gap tolerance</span>
                <input type="number" value={gapTolerance} onChange={(e) => setGapTolerance(Number(e.target.value))}
                  style={{ ...st.numberInput, width: "65px" }} />
              </div>
            </div>
          </div>
        )}

        <div style={st.tableWrap}>
          <table style={st.table}>
            <thead>
              <tr>
                <th style={st.th}>Symbol</th>
                <th style={{ ...st.th, width: "70px", textAlign: "center", whiteSpace: "nowrap" }}>
                  {displayTab === "condition" ? "Region #" : "Segment #"}
                </th>
                <th style={st.th}>{displayTab === "condition" ? "Condition Start" : "Start"}</th>
                <th style={st.th}>{displayTab === "condition" ? "Condition End" : "End"}</th>
                {displayTab === "condition" && (
                  <th style={{ ...st.th, width: "100px", textAlign: "right" }}>Cond Bars</th>
                )}
                <th style={{ ...st.th, width: "80px", textAlign: "right" }}>Bars</th>
              </tr>
            </thead>
            <tbody>
              {segments.length > 0 ? segments.map((seg, i) => {
                const isExpanded = expandedRows[i];
                const startTs = displayTab === "condition" ? seg.condition_start_ts : (displayTab === "time" ? seg.period_start_ns : seg.start_ts);
                const endTs = displayTab === "condition" ? seg.condition_end_ts : (displayTab === "time" ? seg.period_end_ns : seg.end_ts);
                return (
                  <React.Fragment key={i}>
                    <tr onClick={() => toggleRowExpand(i)}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.35)", cursor: "pointer", background: isExpanded ? "rgba(99,102,241,0.05)" : "transparent" }}>
                      <td style={st.td}><span style={st.segSymbol}>{seg.symbol}</span></td>
                      <td style={{ ...st.td, textAlign: "center" }}><span style={st.segNum}>{seg.segment_num}</span></td>
                      <td style={st.td}><span style={st.segTime}>{startTs ? formatTimestamp(startTs) : '-'}</span></td>
                      <td style={st.td}><span style={st.segTime}>{endTs ? formatTimestamp(endTs) : '-'}</span></td>
                      {displayTab === "condition" && (
                        <td style={{ ...st.td, textAlign: "right" }}><span style={st.segBars}>{seg.condition_bar_count || 0}</span></td>
                      )}
                      <td style={{ ...st.td, textAlign: "right" }}><span style={st.segBars}>{seg.bar_count}</span></td>
                    </tr>
                    {isExpanded && (
                      <tr>
                        <td colSpan={displayTab === "condition" ? 6 : 5} style={{ padding: "8px 14px", background: "rgba(15,23,42,0.5)" }}>
                          {seg.bar_count > 5000 ? (
                            <div style={{ textAlign: "center", color: "#94a3b8", padding: "24px 16px", fontSize: "12px", fontStyle: "italic" }}>
                              Segment has {seg.bar_count.toLocaleString()} bars — refine your condition to produce smaller regions
                            </div>
                          ) : (
                            <img
                              src={`/api/sessions/${currentSessionId}/segment-chart.png?symbol=${encodeURIComponent(seg.symbol)}&start_ns=${seg.start_ts}&end_ns=${seg.end_ts}&chart_type=${chartType}${seg.condition_start_ts ? '&highlight_start_ns=' + seg.condition_start_ts + '&highlight_end_ns=' + seg.condition_end_ts : ''}&run_ids=${activeRunIds.join(',')}&_v=${settingsVersion}`}
                              alt={`Chart for ${seg.symbol} segment ${seg.segment_num}`}
                              style={{ width: "100%", borderRadius: "6px", border: "1px solid rgba(51,65,85,0.3)" }}
                              onError={(e) => { e.target.style.display = 'none'; }}
                            />
                          )}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              }) : (
                <tr>
                  <td colSpan={displayTab === "condition" ? 6 : 5} style={{ ...st.td, textAlign: "center", color: "#475569", padding: "24px", fontStyle: "italic" }}>
                    {currentSessionId ? (displayTab === "condition" ? "Add a condition above and click Filter" : "No segments found") : "Select a data source to view charts"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
        )}

        {activePage === "backtest" && (
          <PlaceholderPage title="Run Backtests" subtitle="Test strategies against historical data" />
        )}
      </div>
    </div>
  );
}

// ─── Styles ───────────────────────────────────────────────
const st = {
  appShell: {
    display: "flex", minHeight: "100vh", background: "#0c0f1a",
    fontFamily: "'DM Sans', sans-serif",
  },
  sidebar: {
    width: "62px", minHeight: "100vh", background: "rgba(10,13,25,0.95)",
    borderRight: "1px solid rgba(51,65,85,0.3)",
    display: "flex", flexDirection: "column", alignItems: "center",
    padding: "12px 0", position: "sticky", top: 0,
    backdropFilter: "blur(10px)", zIndex: 300, flexShrink: 0,
  },
  navBtn: {
    width: "54px", padding: "8px 0 6px", display: "flex", flexDirection: "column",
    alignItems: "center", justifyContent: "center", gap: "0px",
    border: "none", borderRadius: "8px", cursor: "pointer", position: "relative",
    transition: "all 0.15s", fontFamily: "'DM Sans', sans-serif",
  },
  navActiveBar: {
    position: "absolute", left: "-4px", top: "50%", transform: "translateY(-50%)",
    width: "3px", height: "24px", borderRadius: "0 2px 2px 0",
    background: "linear-gradient(180deg, #6366f1, #818cf8)",
  },
  mainContent: {
    flex: 1, minWidth: 0, overflowY: "auto",
    backgroundImage: "radial-gradient(ellipse at 20% 0%, rgba(99,102,241,0.05) 0%, transparent 60%), radial-gradient(ellipse at 80% 100%, rgba(59,130,246,0.03) 0%, transparent 60%)",
  },
  page: {
    fontFamily: "'DM Sans', sans-serif",
    color: "#e2e8f0",
    padding: "24px 28px",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "22px",
    paddingBottom: "16px",
    borderBottom: "1px solid rgba(51,65,85,0.35)",
  },
  pageTitle: { fontSize: "20px", fontWeight: 600, color: "#f1f5f9", letterSpacing: "-0.3px" },
  pageSubtitle: { fontSize: "12.5px", color: "#64748b", marginTop: "2px" },
  topGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1.6fr",
    gap: "16px",
    alignItems: "stretch",
  },
  card: {
    background: "rgba(15,23,42,0.7)",
    border: "1px solid rgba(51,65,85,0.45)",
    borderRadius: "10px",
    padding: "18px",
    backdropFilter: "blur(10px)",
    display: "flex",
    flexDirection: "column",
  },
  sectionIcon: {
    width: "30px", height: "30px", borderRadius: "7px",
    background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)",
    display: "flex", alignItems: "center", justifyContent: "center", color: "#818cf8", flexShrink: 0,
  },
  sectionNumber: { fontSize: "10px", fontWeight: 600, color: "#818cf8", fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.5px" },
  sectionTitle: { fontSize: "14px", fontWeight: 600, color: "#f1f5f9", letterSpacing: "-0.2px" },
  sectionSubtitle: { fontSize: "11px", color: "#64748b", marginTop: "1px" },
  presetChip: {
    background: "rgba(30,41,59,0.5)",
    border: "1px solid rgba(51,65,85,0.4)",
    borderRadius: "6px",
    padding: "2px",
  },
  presetInlineInput: {
    background: "rgba(30,41,59,0.6)", border: "1px solid rgba(51,65,85,0.5)",
    borderRadius: "5px", color: "#e2e8f0", fontSize: "11px",
    fontFamily: "'DM Sans', sans-serif", padding: "4px 8px", outline: "none",
    width: "140px",
  },
  label: {
    display: "block", fontSize: "10px", fontWeight: 500, color: "#64748b",
    textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "5px",
  },
  labelBelow: {
    display: "block", fontSize: "9.5px", fontWeight: 500, color: "#475569",
    textTransform: "uppercase", letterSpacing: "0.4px", marginTop: "4px",
  },
  select: {
    width: "100%", padding: "9px 10px", background: "rgba(30,41,59,0.6)",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "6px", color: "#e2e8f0",
    fontSize: "12px", fontFamily: "'DM Sans', sans-serif", cursor: "pointer",
    display: "flex", alignItems: "center", justifyContent: "space-between", gap: "6px", outline: "none",
  },
  dropdown: {
    position: "absolute", top: "100%", left: 0, right: 0, marginTop: "3px",
    background: "#1e293b", border: "1px solid rgba(51,65,85,0.8)", borderRadius: "7px",
    padding: "3px", zIndex: 1000, maxHeight: "180px", overflowY: "auto",
    boxShadow: "0 10px 35px rgba(0,0,0,0.5)",
  },
  dropdownItem: {
    width: "100%", padding: "6px 9px", background: "transparent", border: "none",
    color: "#cbd5e1", fontSize: "12px", fontFamily: "'DM Sans', sans-serif",
    cursor: "pointer", borderRadius: "4px", textAlign: "left",
  },
  tagInputWrap: {
    display: "flex", flexWrap: "wrap", alignItems: "center", gap: "5px",
    padding: "6px 10px", background: "rgba(30,41,59,0.6)",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "6px",
    cursor: "text", minHeight: "38px",
  },
  tagSearchInput: {
    flex: 1, minWidth: "80px", background: "transparent", border: "none", outline: "none",
    color: "#e2e8f0", fontSize: "12px", fontFamily: "'DM Sans', sans-serif",
    padding: "2px 0",
  },
  chip: {
    display: "inline-flex", alignItems: "center", gap: "5px", padding: "3px 8px",
    background: "rgba(99,102,241,0.12)", border: "1px solid rgba(99,102,241,0.25)",
    borderRadius: "4px", color: "#a5b4fc",
  },
  chipX: { background: "none", border: "none", color: "#818cf8", cursor: "pointer", padding: 0, display: "flex", alignItems: "center", opacity: 0.7 },
  dateInput: {
    width: "100%", padding: "9px 10px", background: "transparent",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "6px", color: "#64748b",
    fontSize: "12px", fontFamily: "'DM Sans', sans-serif", outline: "none",
  },
  iconBtn: { background: "none", border: "none", color: "#64748b", cursor: "pointer", padding: "3px", display: "flex", alignItems: "center", borderRadius: "3px" },

  // Merged indicator list
  indicatorList: {
    display: "flex", flexDirection: "column", gap: "5px", flex: 1,
    overflow: "visible",
  },
  indCard: {
    padding: "6px 10px", background: "rgba(30,41,59,0.3)", borderRadius: "6px",
    border: "1px solid rgba(51,65,85,0.3)", transition: "opacity 0.15s",
    position: "relative", overflow: "visible",
  },
  indName: {
    fontSize: "12px", fontWeight: 500, color: "#e2e8f0",
    letterSpacing: "-0.1px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
  },
  newBadge: {
    fontSize: "9px", fontWeight: 600, color: "#34d399", background: "rgba(52,211,153,0.12)",
    border: "1px solid rgba(52,211,153,0.25)", borderRadius: "3px", padding: "1px 5px",
    textTransform: "uppercase", letterSpacing: "0.5px", flexShrink: 0,
  },
  propGroup: { display: "flex", alignItems: "center", gap: "4px" },
  propLabel: { fontSize: "9.5px", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.3px", fontWeight: 500 },
  expandSectionLabel: {
    fontSize: "9.5px", fontWeight: 600, color: "#64748b", textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  paramInput: {
    padding: "4px 8px", background: "rgba(30,41,59,0.6)", border: "1px solid rgba(51,65,85,0.4)",
    borderRadius: "4px", color: "#e2e8f0", fontSize: "11px",
    fontFamily: "'JetBrains Mono', monospace", outline: "none", width: "70px",
    textAlign: "center", transition: "border-color 0.15s",
  },
  doneBtn: {
    display: "inline-flex", alignItems: "center", gap: "5px", padding: "5px 14px",
    background: "linear-gradient(135deg, #059669 0%, #34d399 100%)", border: "none",
    borderRadius: "5px", color: "#fff", fontSize: "11px", fontWeight: 600,
    fontFamily: "'DM Sans', sans-serif", cursor: "pointer",
    boxShadow: "0 2px 10px rgba(52,211,153,0.25)",
  },
  emptyState: { textAlign: "center", color: "#475569", fontSize: "12px", padding: "24px 16px", fontStyle: "italic", flex: 1, display: "flex", alignItems: "center", justifyContent: "center" },
  fillBetweenRow: {
    display: "flex", alignItems: "center", gap: "8px",
    padding: "8px 10px", background: "rgba(30,41,59,0.3)", borderRadius: "6px",
    border: "1px solid rgba(51,65,85,0.3)",
  },

  // Bottom actions
  fillBetweenBtn: {
    display: "flex", alignItems: "center", gap: "5px", padding: "9px 10px",
    background: "transparent", border: "1px solid rgba(51,65,85,0.5)", borderRadius: "6px",
    color: "#64748b", fontSize: "11.5px", fontFamily: "'DM Sans', sans-serif", cursor: "pointer",
    whiteSpace: "nowrap", flex: 1, justifyContent: "center",
  },
  numberInput: {
    width: "100%", padding: "7px 10px", background: "rgba(30,41,59,0.6)",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "5px", color: "#e2e8f0",
    fontSize: "12px", fontFamily: "'JetBrains Mono', monospace", outline: "none", textAlign: "center",
  },
  signalPanel: {
    padding: "14px", background: "rgba(30,41,59,0.3)", borderRadius: "8px",
    border: "1px solid rgba(51,65,85,0.3)", marginBottom: "12px",
  },
  signalLabel: {
    fontSize: "10px", fontWeight: 500, color: "#64748b", textTransform: "uppercase",
    letterSpacing: "0.3px", whiteSpace: "nowrap",
  },
  addCondBtn: {
    display: "inline-flex", alignItems: "center", gap: "4px", padding: "5px 12px",
    background: "rgba(99,102,241,0.12)", border: "1px solid rgba(99,102,241,0.3)",
    borderRadius: "5px", color: "#818cf8", fontSize: "11px", fontWeight: 600,
    fontFamily: "'DM Sans', sans-serif", cursor: "pointer", whiteSpace: "nowrap",
  },
  conditionRow: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "5px 10px", background: "rgba(30,41,59,0.4)", borderRadius: "5px",
    border: "1px solid rgba(51,65,85,0.25)",
  },
  conditionText: {
    fontSize: "12px", fontFamily: "'JetBrains Mono', monospace", color: "#cbd5e1",
  },
  conditionOp: {
    color: "#818cf8", fontWeight: 600,
  },

  // Chart Display
  tabs: {
    display: "inline-flex", gap: "2px", background: "rgba(30,41,59,0.35)",
    borderRadius: "7px", padding: "3px",
  },
  tab: {
    padding: "6px 14px", background: "transparent", border: "none", borderRadius: "5px",
    color: "#64748b", fontSize: "12px", fontWeight: 500,
    fontFamily: "'DM Sans', sans-serif", cursor: "pointer", transition: "all 0.15s",
  },
  tabActive: { background: "rgba(99,102,241,0.15)", color: "#a5b4fc" },
  tableWrap: { border: "1px solid rgba(51,65,85,0.35)", borderRadius: "8px", overflow: "hidden" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: "12px" },
  th: {
    padding: "8px 14px", textAlign: "left", fontSize: "10px", fontWeight: 600, color: "#64748b",
    textTransform: "uppercase", letterSpacing: "0.5px", background: "rgba(30,41,59,0.4)",
    borderBottom: "1px solid rgba(51,65,85,0.4)",
  },
  td: { padding: "7px 14px", verticalAlign: "middle" },
  segSymbol: {
    fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", color: "#a5b4fc",
    background: "rgba(99,102,241,0.08)", padding: "2px 6px", borderRadius: "3px",
  },
  segNum: { fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", color: "#94a3b8" },
  segTime: { fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", color: "#94a3b8" },
  segBars: { fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", color: "#6366f1", fontWeight: 500 },
};

// ─── Mount ────────────────────────────────────────────────
ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(ExplorerRedesign));
