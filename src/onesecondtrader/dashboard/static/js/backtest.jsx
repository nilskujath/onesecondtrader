const { useState, useRef, useEffect, useCallback, useMemo } = React;

// ─── Constants ─────────────────────────────────────────────
const RTYPE_MAP = { "Second": 32, "Minute": 33, "Hour": 34, "Day": 35 };
const RTYPE_LABELS = { 32: "Second", 33: "Minute", 34: "Hour", 35: "Day" };
const VALID_STYLES = ["line", "histogram", "dots", "dash1", "dash2", "dash3", "background1", "background2"];
const VALID_COLORS = ["black", "red", "blue", "green", "orange", "purple", "cyan", "magenta", "yellow", "teal"];
const VALID_WIDTHS = ["thin", "normal", "thick", "extra_thick"];
const CHART_TYPE_OPTIONS = [
  { value: "candlestick", label: "Candlestick" },
  { value: "oc_bars", label: "OC Bars" },
  { value: "c_bars", label: "C Bars" },
  { value: "bars", label: "Bars" },
];

// ─── Helpers ───────────────────────────────────────────────
function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatParamName(name) {
  let result = name.replace(/_/g, " ");
  result = result.replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2");
  result = result.replace(/([a-z])([A-Z])/g, "$1 $2");
  result = result.replace(/([a-zA-Z])(\d)/g, "$1 $2");
  return result.split(" ").map(word => {
    if (word === word.toUpperCase() && word.length > 1) return word;
    return word.charAt(0).toUpperCase() + word.slice(1);
  }).join(" ");
}

function formatTimestamp(ns) {
  const ms = Number(BigInt(ns) / BigInt(1000000));
  const date = new Date(ms);
  return date.toISOString().slice(0, 16).replace("T", " ");
}

function getDefaultPanel(name, assignedPanels) {
  const upper = name.toUpperCase();
  if (/^SMA_/.test(upper) || /^BB_UPPER_/.test(upper) || /^BB_LOWER_/.test(upper) ||
      /^PSAR_/.test(upper) || /PERIOD HIGH/.test(upper) || /PERIOD LOW/.test(upper)) {
    return 0;
  }
  const adxGroup = ["ADX_", "PLUS_DI_", "MINUS_DI_"];
  if (adxGroup.some(prefix => upper.startsWith(prefix))) {
    for (const [existingName, panel] of Object.entries(assignedPanels)) {
      if (adxGroup.some(prefix => existingName.toUpperCase().startsWith(prefix))) {
        return panel;
      }
    }
  }
  const maxPanel = Math.max(0, ...Object.values(assignedPanels));
  return maxPanel + 1;
}

// ─── Icons ────────────────────────────────────────────────
const Icons = {
  ChevronDown: () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
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
  Layers: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
  ),
  BarChart: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
  ),
  Flask: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M9 3h6"/><path d="M10 3v7.4a2 2 0 0 1-.5 1.3L4 18.6a1 1 0 0 0 .8 1.4h14.4a1 1 0 0 0 .8-1.4l-5.5-6.9a2 2 0 0 1-.5-1.3V3"/><path d="M8.5 14h7"/></svg>
  ),
  Table: () => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
  ),
  Play: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"/></svg>
  ),
  Search: () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
  ),
  Check: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
  ),
  Plus: () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
  ),
  Activity: () => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
  ),
};

// ─── Reusable Components ──────────────────────────────────
function Select({ value, onChange, options, placeholder, grouped }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

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
    <div ref={ref} style={{ position: "relative", zIndex: open ? 100 : "auto" }}>
      <button onClick={() => setOpen(!open)}
        style={{ ...st.select, color: value ? "#e2e8f0" : "#64748b" }}>
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

// ─── Navigation ───────────────────────────────────────────
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

// ─── Main Component ───────────────────────────────────────
function BacktestApp() {
  // ─── Data Source State ───
  const [rtypes, setRtypes] = useState([]);
  const [publishers, setPublishers] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [coverageSymbols, setCoverageSymbols] = useState([]);
  const [allCoverageData, setAllCoverageData] = useState([]);
  const [symbolCoverage, setSymbolCoverage] = useState({});
  const [selectedPublisherId, setSelectedPublisherId] = useState(null);
  const [hasContinuousSymbols, setHasContinuousSymbols] = useState(false);
  const [contractType, setContractType] = useState("outrights");
  const [barPeriod, setBarPeriod] = useState("");
  const [provider, setProvider] = useState("");
  const [exchange, setExchange] = useState("");
  const [symbolSearch, setSymbolSearch] = useState("");
  const [selectedSymbols, setSelectedSymbols] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [showSymbolDropdown, setShowSymbolDropdown] = useState(false);
  const [splitSources, setSplitSources] = useState([]);
  const [selectedSplitSource, setSelectedSplitSource] = useState("");
  const isLoadingPresetRef = useRef(false);

  // ─── Strategy & Presets State ───
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState("");
  const [strategyParams, setStrategyParams] = useState([]);
  const [paramValues, setParamValues] = useState({});
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState("");
  const [presetName, setPresetName] = useState("");

  // ─── Runs State ───
  const [dbRuns, setDbRuns] = useState([]);
  const [activeRuns, setActiveRuns] = useState({});
  const activeRunsRef = useRef({});
  const [selectedRunIds, setSelectedRunIds] = useState(new Set());
  const pollTimeouts = useRef({});

  // ─── Analysis State ───
  const [analysisRunId, setAnalysisRunId] = useState(null);
  const [perfSymbols, setPerfSymbols] = useState([]);
  const [perfSelectedSymbol, setPerfSelectedSymbol] = useState(null);
  const [perfSymbolSearch, setPerfSymbolSearch] = useState("");
  const [showPerfSuggestions, setShowPerfSuggestions] = useState(false);
  const [perfSuggestionIndex, setPerfSuggestionIndex] = useState(-1);

  // ─── Trades State ───
  const [roundtrips, setRoundtrips] = useState([]);
  const [filteredRoundtrips, setFilteredRoundtrips] = useState([]);
  const [tradesSymbolFilter, setTradesSymbolFilter] = useState("");
  const [sortColumn, setSortColumn] = useState("symbol");
  const [sortAsc, setSortAsc] = useState(true);
  const [expandedTradeIdx, setExpandedTradeIdx] = useState(new Set());

  // ─── Chart Settings State ───
  const [chartType, setChartType] = useState("c_bars");
  const [chartContext, setChartContext] = useState(100);
  const [indicatorNames, setIndicatorNames] = useState([]);
  const [chartSettingsData, setChartSettingsData] = useState({ indicators: {}, fill_between: [] });
  const [indicatorDefaultsData, setIndicatorDefaultsData] = useState({});
  const [settingsVersion, setSettingsVersion] = useState(0);
  const [chartCache, setChartCache] = useState({});

  // ─── Derived ───
  const completedRuns = useMemo(() => dbRuns.filter(r => r.status === "completed"), [dbRuns]);

  const barPeriodOptions = rtypes.map(r => ({
    value: RTYPE_LABELS[r] || "rtype " + r,
    label: RTYPE_LABELS[r] || "rtype " + r,
  }));
  const providerOptions = publishers.map(p => ({ value: p, label: capitalize(p) }));
  const venueOptions = datasets.map(d => ({ value: d.dataset, label: d.dataset }));

  const filteredSymbols = coverageSymbols.filter(
    (sym) => sym.toLowerCase().includes(symbolSearch.toLowerCase()) && !selectedSymbols.includes(sym)
  );

  const perfFilteredSymbols = useMemo(() => {
    if (!perfSymbolSearch) return perfSymbols;
    const q = perfSymbolSearch.toUpperCase();
    return perfSymbols.filter(s => s.toUpperCase().includes(q));
  }, [perfSymbols, perfSymbolSearch]);

  // Split source grouped options
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
        label: `${capitalize(s.region)}: ${s.start_date} → ${s.end_date}`,
      })),
    }));
  }, [splitSources]);

  // Sorted trades
  const sortedTrades = useMemo(() => {
    const data = [...filteredRoundtrips];
    data.sort((a, b) => {
      let valA = a[sortColumn];
      let valB = b[sortColumn];
      if (typeof valA === "string") { valA = valA.toLowerCase(); valB = (valB || "").toLowerCase(); }
      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });
    return data;
  }, [filteredRoundtrips, sortColumn, sortAsc]);

  const canRun = useMemo(() => {
    const rtype = barPeriod ? RTYPE_MAP[barPeriod] : null;
    return !!(selectedStrategy && rtype && selectedPublisherId && selectedSymbols.length > 0);
  }, [selectedStrategy, barPeriod, selectedPublisherId, selectedSymbols]);

  const canSavePreset = useMemo(() => {
    const rtype = barPeriod ? RTYPE_MAP[barPeriod] : null;
    return !!(presetName.trim() && rtype && selectedPublisherId && selectedSymbols.length > 0);
  }, [presetName, barPeriod, selectedPublisherId, selectedSymbols]);

  // ─── Coverage filtering helper ───
  const filterAndSetCoverage = useCallback((allData, ctype, hasCont) => {
    let filtered = allData;
    if (hasCont) {
      if (ctype === "continuous") filtered = allData.filter(r => r.symbol_type === "continuous");
      else if (ctype === "spreads") filtered = allData.filter(r => r.symbol_type === "raw_symbol" && r.symbol.includes("-"));
      else filtered = allData.filter(r => r.symbol_type === "raw_symbol" && !r.symbol.includes("-"));
    }
    const syms = filtered.map(r => r.symbol);
    setCoverageSymbols(syms);
    const covMap = {};
    filtered.forEach(r => { covMap[r.symbol] = { min_ts: r.min_ts, max_ts: r.max_ts }; });
    setSymbolCoverage(covMap);
    return syms;
  }, []);

  // ─── Mount effects ───
  useEffect(() => {
    // Load rtypes
    fetch("/api/secmaster/symbols_coverage").then(r => r.json()).then(data => {
      const syms = data.symbols || [];
      const rtypeSet = new Set(syms.map(s => s.rtype));
      const sorted = [...rtypeSet].sort((a, b) => a - b);
      setRtypes(sorted);
      if (sorted.length === 1) setBarPeriod(RTYPE_LABELS[sorted[0]] || "rtype " + sorted[0]);
    });
    // Load strategies
    fetch("/api/strategies").then(r => r.json()).then(data => {
      const strats = data.strategies || [];
      setStrategies(strats);
      if (strats.length > 0) {
        setSelectedStrategy(strats[0].id);
      }
    });
    // Load presets
    fetch("/api/presets").then(r => r.json()).then(d => setPresets(d.presets || []));
    // Load db runs
    loadDbRuns();
    // Restore active runs
    fetch("/api/backtest/running").then(r => r.json()).then(data => {
      const running = data.running || [];
      const newActive = {};
      running.forEach(r => {
        newActive[r.run_id] = {
          strategy: r.strategy || "Unknown",
          symbols: r.symbols || [],
          startDate: r.start_date || null,
          endDate: r.end_date || null,
          status: r.status || "running",
          progress: r.progress || 0,
        };
      });
      activeRunsRef.current = newActive;
      setActiveRuns({ ...newActive });
      running.forEach(r => startPolling(r.run_id));
    });
    // Load indicator defaults
    fetch("/api/indicator-defaults").then(r => r.json()).then(d => setIndicatorDefaultsData(d || {})).catch(() => {});
    // Load split sources
    fetch("/api/splits/sources").then(r => r.json()).then(d => setSplitSources(d || [])).catch(() => {});
    // Cleanup polling on unmount
    return () => {
      Object.values(pollTimeouts.current).forEach(t => clearTimeout(t));
    };
  }, []);

  // ─── Data source cascade ───
  // barPeriod → load publishers
  useEffect(() => {
    if (isLoadingPresetRef.current) return;
    let cancelled = false;
    if (!barPeriod) { setPublishers([]); return; }
    const rtype = RTYPE_MAP[barPeriod];
    if (!rtype) return;
    fetch(`/api/secmaster/publishers?rtype=${rtype}`).then(r => r.json()).then(data => {
      if (!cancelled) {
        const pubs = data.publishers || [];
        setPublishers(pubs);
        if (pubs.length === 1) setProvider(pubs[0]);
      }
    });
    setProvider(""); setExchange(""); setDatasets([]);
    setSelectedPublisherId(null); setCoverageSymbols([]); setSelectedSymbols([]);
    return () => { cancelled = true; };
  }, [barPeriod]);

  // provider + barPeriod → load datasets
  useEffect(() => {
    if (isLoadingPresetRef.current) return;
    let cancelled = false;
    if (!provider || !barPeriod) { setDatasets([]); return; }
    const rtype = RTYPE_MAP[barPeriod];
    fetch(`/api/secmaster/publishers/${encodeURIComponent(provider)}/datasets?rtype=${rtype}`)
      .then(r => r.json()).then(data => {
        if (!cancelled) {
          const ds = data.datasets || [];
          setDatasets(ds);
          if (ds.length === 1) {
            setExchange(ds[0].dataset);
            setSelectedPublisherId(ds[0].publisher_id);
          }
        }
      });
    setExchange(""); setSelectedPublisherId(null);
    setCoverageSymbols([]); setSelectedSymbols([]);
    return () => { cancelled = true; };
  }, [provider, barPeriod]);

  // selectedPublisherId + barPeriod → load symbol coverage
  useEffect(() => {
    let cancelled = false;
    if (!selectedPublisherId || !barPeriod) { setCoverageSymbols([]); return; }
    const rtype = RTYPE_MAP[barPeriod];
    fetch(`/api/secmaster/symbols_coverage?publisher_id=${selectedPublisherId}&rtype=${rtype}`)
      .then(r => r.json()).then(data => {
        if (cancelled) return;
        const all = data.symbols || [];
        setAllCoverageData(all);
        const hasCont = all.some(r => r.symbol_type === "continuous");
        setHasContinuousSymbols(hasCont);
        const syms = filterAndSetCoverage(all, hasCont ? contractType : "outrights", hasCont);
        if (!isLoadingPresetRef.current) {
          setSelectedSymbols(syms.length === 1 ? [syms[0]] : []);
        }
      });
    return () => { cancelled = true; };
  }, [selectedPublisherId, barPeriod, filterAndSetCoverage]);

  // contractType → re-filter coverage
  useEffect(() => {
    if (allCoverageData.length > 0) {
      const syms = filterAndSetCoverage(allCoverageData, contractType, hasContinuousSymbols);
      if (!isLoadingPresetRef.current) {
        setSelectedSymbols(syms.length === 1 ? [syms[0]] : []);
      }
    }
  }, [contractType, allCoverageData, hasContinuousSymbols, filterAndSetCoverage]);

  // selectedSymbols + symbolCoverage → auto-fill date range
  useEffect(() => {
    if (isLoadingPresetRef.current) return;
    if (selectedSymbols.length === 0) { setStartDate(""); setEndDate(""); return; }
    let minTs = null, maxTs = null;
    selectedSymbols.forEach(s => {
      const cov = symbolCoverage[s];
      if (cov) {
        if (minTs === null || cov.min_ts < minTs) minTs = cov.min_ts;
        if (maxTs === null || cov.max_ts > maxTs) maxTs = cov.max_ts;
      }
    });
    if (minTs !== null) {
      setStartDate(new Date(Math.floor(minTs / 1000000)).toISOString().split("T")[0]);
      setEndDate(new Date(Math.floor(maxTs / 1000000)).toISOString().split("T")[0]);
    }
  }, [selectedSymbols, symbolCoverage]);

  // ─── Strategy params loading ───
  useEffect(() => {
    if (!selectedStrategy) return;
    fetch(`/api/strategies/${selectedStrategy}`).then(r => r.json()).then(data => {
      const params = (data.parameters || []).filter(p => p.name !== "bar_period");
      setStrategyParams(params);
      const defaults = {};
      params.forEach(p => { defaults[p.name] = p.default; });
      setParamValues(defaults);
    });
  }, [selectedStrategy]);

  // ─── Analysis effect: load data when analysisRunId changes ───
  useEffect(() => {
    if (!analysisRunId) {
      setPerfSymbols([]); setPerfSelectedSymbol(null); setPerfSymbolSearch("");
      setRoundtrips([]); setFilteredRoundtrips([]); setTradesSymbolFilter("");
      setIndicatorNames([]); setChartSettingsData({ indicators: {}, fill_between: [] });
      setExpandedTradeIdx(new Set()); setChartCache({});
      return;
    }
    // Load perf symbols, trades, indicator settings in parallel
    Promise.all([
      fetch(`/api/runs/${analysisRunId}/roundtrips`).then(r => r.json()),
      fetch(`/api/runs/${analysisRunId}/indicators`).then(r => r.json()),
      fetch(`/api/runs/${analysisRunId}/chart-settings`).then(r => r.json()),
    ]).then(([rtsData, indData, settingsJson]) => {
      // Perf symbols
      const rts = rtsData.roundtrips || [];
      const syms = [...new Set(rts.map(rt => rt.symbol))].sort();
      setPerfSymbols(syms);
      setPerfSelectedSymbol(null);
      setPerfSymbolSearch("");

      // Trades
      const tradeNums = {};
      rts.forEach(rt => {
        tradeNums[rt.symbol] = (tradeNums[rt.symbol] || 0) + 1;
        rt.trade_num = tradeNums[rt.symbol];
      });
      setRoundtrips(rts);
      setFilteredRoundtrips(rts);
      setTradesSymbolFilter("");
      setSortColumn("symbol");
      setSortAsc(true);
      setExpandedTradeIdx(new Set());
      setChartCache({});

      // Indicator settings
      const indNames = indData.indicators || [];
      setIndicatorNames(indNames);
      const settings = settingsJson || {};
      if (!settings.indicators) settings.indicators = {};
      if (!settings.fill_between) settings.fill_between = [];
      const ct = settings.chart_type || (indicatorDefaultsData.chart_type || "c_bars");
      setChartType(ct);
      const assignedPanels = {};
      indNames.forEach(name => {
        if (!settings.indicators[name]) {
          if (indicatorDefaultsData.indicators && indicatorDefaultsData.indicators[name]) {
            const saved = indicatorDefaultsData.indicators[name];
            const panel = saved.panel !== undefined ? saved.panel : getDefaultPanel(name, assignedPanels);
            settings.indicators[name] = {
              panel, below_price: saved.below_price !== undefined ? saved.below_price : true,
              style: saved.style || "line", color: saved.color || "black",
              width: saved.width || "normal", visible: saved.visible !== undefined ? saved.visible : true,
            };
          } else {
            const panel = getDefaultPanel(name, assignedPanels);
            settings.indicators[name] = { panel, below_price: true, style: "line", color: "black", width: "normal", visible: true };
          }
          assignedPanels[name] = settings.indicators[name].panel;
        } else {
          const cfg = settings.indicators[name];
          if (cfg.panel < 0 && cfg.below_price === undefined) {
            cfg.panel = Math.abs(cfg.panel);
            cfg.below_price = false;
          }
          if (cfg.below_price === undefined) cfg.below_price = true;
          assignedPanels[name] = cfg.panel;
        }
      });
      setChartSettingsData({ ...settings });
    }).catch(e => console.error("Failed to load analysis data", e));
  }, [analysisRunId, indicatorDefaultsData]);

  // ─── Outside-click handlers ───
  const symbolRef = useRef(null);
  const perfRef = useRef(null);
  useEffect(() => {
    const handler = (e) => {
      if (symbolRef.current && !symbolRef.current.contains(e.target)) setShowSymbolDropdown(false);
      if (perfRef.current && !perfRef.current.contains(e.target)) setShowPerfSuggestions(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // ─── Key functions ───
  const loadDbRuns = async () => {
    const res = await fetch("/api/runs");
    const data = await res.json();
    setDbRuns(data.runs || []);
  };

  const handleVenueChange = (datasetLabel) => {
    setExchange(datasetLabel);
    const ds = datasets.find(d => d.dataset === datasetLabel);
    if (ds) setSelectedPublisherId(ds.publisher_id);
  };

  const startPolling = (runId) => {
    const poll = async (refreshCount) => {
      try {
        const r = await fetch(`/api/backtest/status/${runId}`);
        const d = await r.json();
        if (d.status === "completed" || d.status.startsWith("error")) {
          delete activeRunsRef.current[runId];
          setActiveRuns({ ...activeRunsRef.current });
          await loadDbRuns();
          if ((refreshCount || 0) < 5) {
            pollTimeouts.current[runId] = setTimeout(() => poll((refreshCount || 0) + 1), 500);
          }
          return;
        }
        if (activeRunsRef.current[runId]) {
          activeRunsRef.current[runId].status = d.status === "queued" ? "queued" : "running";
          activeRunsRef.current[runId].progress = d.progress || 0;
          setActiveRuns({ ...activeRunsRef.current });
        }
      } catch (e) { /* retry */ }
      pollTimeouts.current[runId] = setTimeout(() => poll(), 1000);
    };
    poll();
  };

  const runBacktest = async () => {
    const rtype = RTYPE_MAP[barPeriod];
    if (!rtype || !selectedPublisherId || selectedSymbols.length === 0 || !selectedStrategy) return;
    const symbolType = (hasContinuousSymbols && contractType === "continuous") ? "continuous" : "raw_symbol";
    const params = {};
    strategyParams.forEach(p => {
      const val = paramValues[p.name];
      if (p.type === "bool") params[p.name] = !!val;
      else if (p.type === "int") params[p.name] = parseInt(val);
      else if (p.type === "float") params[p.name] = parseFloat(val);
      else params[p.name] = val;
    });
    try {
      const res = await fetch("/api/backtest/run", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy: selectedStrategy, strategy_params: params,
          symbols: selectedSymbols, rtype, publisher_id: selectedPublisherId,
          start_date: startDate || null, end_date: endDate || null,
          symbol_type: symbolType,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to start backtest");
      const runId = data.run_id;
      activeRunsRef.current[runId] = {
        strategy: selectedStrategy, symbols: [...selectedSymbols],
        barPeriod: RTYPE_LABELS[rtype] || "Unknown",
        startDate: startDate || null, endDate: endDate || null,
        status: "queued", progress: 0,
      };
      setActiveRuns({ ...activeRunsRef.current });
      startPolling(runId);
    } catch (e) {
      alert(`Error: ${e.message}`);
    }
  };

  const toggleRunSelection = (runId) => {
    setSelectedRunIds(prev => {
      const next = new Set(prev);
      if (next.has(runId)) next.delete(runId); else next.add(runId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    const allIds = dbRuns.map(r => r.run_id);
    setSelectedRunIds(prev => {
      if (prev.size === allIds.length && allIds.length > 0) return new Set();
      return new Set(allIds);
    });
  };

  const deleteSelectedRuns = async () => {
    if (selectedRunIds.size === 0) return;
    if (!confirm(`Delete ${selectedRunIds.size} run(s)? This cannot be undone.`)) return;
    const res = await fetch("/api/runs", {
      method: "DELETE", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_ids: Array.from(selectedRunIds) }),
    });
    if (res.ok) {
      if (selectedRunIds.has(analysisRunId)) setAnalysisRunId(null);
      setSelectedRunIds(new Set());
      await loadDbRuns();
    } else {
      try { const d = await res.json(); alert(d.detail || "Failed to delete runs"); } catch { alert("Failed to delete runs"); }
    }
  };

  const selectAnalysisRun = (runId) => {
    setAnalysisRunId(runId || null);
  };

  // ─── Preset functions ───
  const applyPreset = async (preset) => {
    isLoadingPresetRef.current = true;
    try {
      const bp = RTYPE_LABELS[preset.rtype];
      setBarPeriod(bp || "");
      // Load publishers
      const pubRes = await fetch(`/api/secmaster/publishers?rtype=${preset.rtype}`);
      const pubData = await pubRes.json();
      setPublishers(pubData.publishers || []);
      setProvider(preset.publisher_name);
      // Load datasets
      const dsRes = await fetch(`/api/secmaster/publishers/${encodeURIComponent(preset.publisher_name)}/datasets?rtype=${preset.rtype}`);
      const dsData = await dsRes.json();
      const dsList = dsData.datasets || [];
      setDatasets(dsList);
      const ds = dsList.find(d => d.publisher_id === preset.publisher_id);
      setExchange(ds ? ds.dataset : "");
      setSelectedPublisherId(preset.publisher_id);
      // Load coverage
      const covRes = await fetch(`/api/secmaster/symbols_coverage?publisher_id=${preset.publisher_id}&rtype=${preset.rtype}`);
      const covData = await covRes.json();
      const all = covData.symbols || [];
      setAllCoverageData(all);
      const hasCont = all.some(r => r.symbol_type === "continuous");
      setHasContinuousSymbols(hasCont);
      const ct = (preset.symbol_type === "continuous" && hasCont) ? "continuous" : "outrights";
      setContractType(ct);
      const syms = filterAndSetCoverage(all, ct, hasCont);
      setSelectedSymbols(preset.symbols.filter(s => syms.includes(s)));
    } finally {
      isLoadingPresetRef.current = false;
    }
  };

  const loadSplitSource = async (sourceName) => {
    const source = splitSources.find(s => s.source_name === sourceName);
    if (!source) return;
    isLoadingPresetRef.current = true;
    try {
      const bp = RTYPE_LABELS[source.rtype];
      setBarPeriod(bp || "");
      const pubRes = await fetch(`/api/secmaster/publishers?rtype=${source.rtype}`);
      const pubData = await pubRes.json();
      setPublishers(pubData.publishers || []);
      setProvider(source.publisher_name);
      const dsRes = await fetch(`/api/secmaster/publishers/${encodeURIComponent(source.publisher_name)}/datasets?rtype=${source.rtype}`);
      const dsData = await dsRes.json();
      const dsList = dsData.datasets || [];
      setDatasets(dsList);
      const ds = dsList.find(d => d.publisher_id === source.publisher_id);
      setExchange(ds ? ds.dataset : "");
      setSelectedPublisherId(source.publisher_id);
      const covRes = await fetch(`/api/secmaster/symbols_coverage?publisher_id=${source.publisher_id}&rtype=${source.rtype}`);
      const covData = await covRes.json();
      const all = covData.symbols || [];
      setAllCoverageData(all);
      const hasCont = all.some(r => r.symbol_type === "continuous");
      setHasContinuousSymbols(hasCont);
      const ct = (source.symbol_type === "continuous" && hasCont) ? "continuous" : "outrights";
      setContractType(ct);
      const syms = filterAndSetCoverage(all, ct, hasCont);
      setSelectedSymbols(source.symbols.filter(s => syms.includes(s)));
      setStartDate(source.start_date);
      setEndDate(source.end_date);
    } finally {
      isLoadingPresetRef.current = false;
    }
  };

  const savePreset = async () => {
    const name = presetName.trim();
    if (!name) { alert("Enter a preset name"); return; }
    const rtype = RTYPE_MAP[barPeriod];
    if (!rtype) { alert("Select a bar period first"); return; }
    if (!selectedPublisherId) { alert("Select a publisher and dataset first"); return; }
    if (selectedSymbols.length === 0) { alert("Select at least one symbol"); return; }
    const exists = presets.some(p => p.name === name);
    const method = exists ? "PUT" : "POST";
    const url = exists ? `/api/presets/${encodeURIComponent(name)}` : "/api/presets";
    const symbolType = (hasContinuousSymbols && contractType === "continuous") ? "continuous" : "raw_symbol";
    await fetch(url, {
      method, headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, rtype, publisher_name: provider, publisher_id: selectedPublisherId, symbols: selectedSymbols, symbol_type: symbolType }),
    });
    setPresetName("");
    const res = await fetch("/api/presets"); const d = await res.json(); setPresets(d.presets || []);
    setSelectedPreset(name);
  };

  const deletePreset = async () => {
    if (!selectedPreset) { alert("Select a preset to delete"); return; }
    if (!confirm(`Delete preset "${selectedPreset}"?`)) return;
    await fetch(`/api/presets/${encodeURIComponent(selectedPreset)}`, { method: "DELETE" });
    setSelectedPreset("");
    const res = await fetch("/api/presets"); const d = await res.json(); setPresets(d.presets || []);
  };

  // ─── Trades filter ───
  useEffect(() => {
    if (!tradesSymbolFilter.trim()) { setFilteredRoundtrips(roundtrips); return; }
    const terms = tradesSymbolFilter.toLowerCase().split(/[,\s]+/).filter(t => t.length > 0);
    setFilteredRoundtrips(roundtrips.filter(rt => terms.some(term => rt.symbol.toLowerCase().includes(term))));
  }, [tradesSymbolFilter, roundtrips]);

  // ─── Chart settings functions ───
  const saveIndicatorSettings = async (newSettings, newChartType) => {
    if (!analysisRunId) return;
    const sData = newSettings || chartSettingsData;
    const cType = newChartType || chartType;
    try {
      await fetch(`/api/runs/${analysisRunId}/chart-settings`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...sData, chart_type: cType }),
      });
      setSettingsVersion(v => v + 1);
      setChartCache({});
    } catch (e) { console.error("Failed to save indicator settings", e); }
  };

  const saveIndicatorDefault = (name, settings) => {
    fetch("/api/indicator-defaults/" + encodeURIComponent(name), {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    }).catch(e => console.error("Failed to save indicator default", e));
  };

  const saveGlobalDefaults = (data) => {
    fetch("/api/indicator-defaults", {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).catch(e => console.error("Failed to save global defaults", e));
  };

  const onIndSettingChange = (name, field, value) => {
    setChartSettingsData(prev => {
      const next = { ...prev, indicators: { ...prev.indicators } };
      if (!next.indicators[name]) next.indicators[name] = {};
      next.indicators[name] = { ...next.indicators[name] };
      if (field === "panel") {
        value = Math.max(0, parseInt(value) || 0);
        if (value === 0) next.indicators[name].below_price = true;
      }
      if (field === "below_price") value = value === true || value === "true";
      if (field === "visible") value = value === true || value === "true";
      next.indicators[name][field] = value;
      saveIndicatorDefault(name, next.indicators[name]);
      saveIndicatorSettings(next);
      return next;
    });
  };

  const onChartTypeChange = (value) => {
    setChartType(value);
    saveIndicatorSettings(null, value);
    saveGlobalDefaults({ chart_type: value });
  };

  const onContextChange = (value) => {
    const v = parseInt(value) || 100;
    setChartContext(v);
    setChartCache({});
    setSettingsVersion(sv => sv + 1);
    setExpandedTradeIdx(new Set());
  };

  const addFillBetween = () => {
    setChartSettingsData(prev => {
      const names = indicatorNames.length >= 2 ? indicatorNames : ["", ""];
      const fb = [...(prev.fill_between || []), { upper: names[0] || "", lower: names[1] || "", color: "blue", alpha: 0.15 }];
      const next = { ...prev, fill_between: fb };
      return next;
    });
  };

  const removeFillBetween = (idx) => {
    setChartSettingsData(prev => {
      const fb = (prev.fill_between || []).filter((_, i) => i !== idx);
      const next = { ...prev, fill_between: fb };
      saveIndicatorSettings(next);
      return next;
    });
  };

  const onFillBetweenChange = (idx, field, value) => {
    setChartSettingsData(prev => {
      const fb = [...(prev.fill_between || [])];
      if (field === "alpha") value = parseFloat(value) || 0.15;
      fb[idx] = { ...fb[idx], [field]: value };
      const next = { ...prev, fill_between: fb };
      saveIndicatorSettings(next);
      return next;
    });
  };

  // ─── Chart URL builder ───
  const getChartUrl = (trade) => {
    return `/api/runs/${analysisRunId}/chart.png?symbol=${encodeURIComponent(trade.symbol)}&start_ns=${trade.entry_ts}&end_ns=${trade.exit_ts}&direction=${trade.direction}&pnl=${trade.pnl_after_commission}&chart_type=${chartType}&context=${chartContext}&_v=${settingsVersion}`;
  };

  const toggleChart = (idx) => {
    setExpandedTradeIdx(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx); else next.add(idx);
      return next;
    });
  };

  const handleSort = (column) => {
    if (sortColumn === column) setSortAsc(!sortAsc);
    else { setSortColumn(column); setSortAsc(true); }
  };

  // ─── Perf symbol keyboard handler ───
  const onPerfSymbolKeydown = (e) => {
    if (!showPerfSuggestions || perfFilteredSymbols.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setPerfSuggestionIndex(i => Math.min(i + 1, perfFilteredSymbols.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setPerfSuggestionIndex(i => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (perfSuggestionIndex >= 0 && perfSuggestionIndex < perfFilteredSymbols.length) {
        setPerfSelectedSymbol(perfFilteredSymbols[perfSuggestionIndex]);
        setPerfSymbolSearch(perfFilteredSymbols[perfSuggestionIndex]);
        setShowPerfSuggestions(false);
      }
    } else if (e.key === "Escape") {
      setShowPerfSuggestions(false);
    }
  };

  // ─── Render ───
  const activeRunIds = Object.keys(activeRuns).filter(id => activeRuns[id].status === "running" || activeRuns[id].status === "queued").reverse();
  const allDbRunIds = dbRuns.map(r => r.run_id);
  const allSelected = allDbRunIds.length > 0 && selectedRunIds.size === allDbRunIds.length;
  const COLUMNS = [
    { key: "symbol", label: "Symbol" }, { key: "trade_num", label: "#" },
    { key: "direction", label: "Direction" }, { key: "duration_bars", label: "Bars" },
    { key: "max_position", label: "Max Position" }, { key: "high_watermark", label: "High Watermark" },
    { key: "low_watermark", label: "Low Watermark" }, { key: "max_drawdown", label: "Max Drawdown" },
    { key: "pnl_before_commission", label: "PnL (Gross)" }, { key: "pnl_after_commission", label: "PnL (Net)" },
  ];

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

      <Sidebar activePage="backtest" onNavigate={(page) => {
        if (page === "explorer") { window.location.href = "/explorer"; return; }
        if (page === "splits") { window.location.href = "/splits"; return; }
      }} />

      <div style={st.mainContent}>
        <div style={st.page}>

          {/* ─── Page Header ─── */}
          <div style={st.header}>
            <div>
              <h1 style={st.pageTitle}>Backtest</h1>
              <p style={st.pageSubtitle}>Run and analyze strategy backtests</p>
            </div>
          </div>

          {/* ════════════════════════════════════════════════════════
              Box 0: Data Source
              ════════════════════════════════════════════════════════ */}
          <div style={{ ...st.card, marginBottom: "16px", position: "relative", zIndex: 10 }}>
            <SectionHeader icon={<Icons.Database />} number="01" title="Data Source" subtitle="Select market data for backtesting" />

            {/* Split source selector */}
            {splitSources.length > 0 && (
              <div style={{ marginBottom: "10px" }}>
                <Select value={selectedSplitSource} onChange={(val) => { setSelectedSplitSource(val); loadSplitSource(val); }}
                  options={splitSourceOptions} placeholder="Load from Split..." grouped />
                <label style={st.labelBelow}>Split Source</label>
              </div>
            )}

            {/* 3-col: Bar Period, Dataset, Venue */}
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
                <Select value={exchange} onChange={handleVenueChange} options={venueOptions} placeholder="Select..." />
                <label style={st.labelBelow}>Venue</label>
              </div>
            </div>

            {/* Contract type tabs */}
            {hasContinuousSymbols && (
              <div style={{ marginTop: "10px" }}>
                <div style={st.tabs}>
                  {["outrights", "continuous", "spreads"].map(ct => (
                    <button key={ct} onClick={() => setContractType(ct)}
                      style={{ ...st.tab, ...(contractType === ct ? st.tabActive : {}) }}>
                      {capitalize(ct)}
                    </button>
                  ))}
                </div>
                <label style={st.labelBelow}>Contract Type</label>
              </div>
            )}

            {/* Symbol tag input */}
            {coverageSymbols.length > 0 && (
              <div style={{ marginTop: "12px", position: "relative" }} ref={symbolRef}>
                <div style={st.tagInputWrap} onClick={() => document.getElementById("bt-sym-search")?.focus()}>
                  {selectedSymbols.map((sym) => (
                    <Chip key={sym} label={sym} onRemove={() => setSelectedSymbols(selectedSymbols.filter(s => s !== sym))} />
                  ))}
                  <input id="bt-sym-search" type="text" value={symbolSearch}
                    onChange={(e) => { setSymbolSearch(e.target.value); setShowSymbolDropdown(true); }}
                    onFocus={() => setShowSymbolDropdown(true)}
                    placeholder={selectedSymbols.length === 0 ? "Search symbols..." : ""}
                    style={st.tagSearchInput} />
                </div>
                <label style={st.labelBelow}>Symbols ({selectedSymbols.length} selected)</label>
                {showSymbolDropdown && (symbolSearch === "" || filteredSymbols.length > 0) && (
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
            )}

            {/* Date range */}
            <div style={{ marginTop: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={{ ...st.dateInput, flex: 1 }} />
                <span style={{ color: "#475569", fontSize: "12px", flexShrink: 0 }}>--</span>
                <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={{ ...st.dateInput, flex: 1 }} />
              </div>
            </div>
          </div>

          {/* ════════════════════════════════════════════════════════
              Box 1: Settings + Runs (2-column)
              ════════════════════════════════════════════════════════ */}
          <div style={{ display: "flex", gap: "16px", marginBottom: "16px" }}>

            {/* Left: Settings */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ ...st.card, height: "100%", position: "relative", zIndex: 5 }}>
                <SectionHeader icon={<Icons.Flask />} number="02" title="Settings" subtitle="Strategy and parameters" />

                {/* Strategy select */}
                <div style={{ marginBottom: "12px" }}>
                  <label style={st.label}>Strategy</label>
                  <Select value={selectedStrategy} onChange={setSelectedStrategy}
                    options={strategies.map(s => ({ value: s.id, label: s.name }))} placeholder="Select strategy..." />
                </div>

                {/* Strategy params */}
                <div style={{ marginBottom: "12px" }}>
                  <label style={st.label}>Parameters</label>
                  <div style={st.paramsContainer}>
                    {strategyParams.length === 0 ? (
                      <div style={{ color: "#64748b", fontSize: "12px" }}>No parameters</div>
                    ) : (
                      strategyParams.map(p => (
                        <div key={p.name} style={st.paramRow}>
                          <label style={{ minWidth: "120px", fontSize: "12px", color: "#94a3b8" }}>{formatParamName(p.name)}</label>
                          {p.choices && p.choices.length > 0 ? (
                            <select value={paramValues[p.name] ?? p.default} onChange={(e) => setParamValues({ ...paramValues, [p.name]: e.target.value })}
                              style={st.formSelect}>
                              {p.choices.map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                          ) : p.type === "bool" ? (
                            <input type="checkbox" checked={!!paramValues[p.name]}
                              onChange={(e) => setParamValues({ ...paramValues, [p.name]: e.target.checked })}
                              style={{ cursor: "pointer", accentColor: "#6366f1" }} />
                          ) : (
                            <input type={p.type === "float" || p.type === "int" ? "number" : "text"}
                              value={paramValues[p.name] ?? p.default}
                              step={p.step || (p.type === "float" ? "0.01" : "1")}
                              min={p.min} max={p.max}
                              onChange={(e) => setParamValues({ ...paramValues, [p.name]: e.target.value })}
                              style={st.formInput} />
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Preset bar */}
                <div style={{ marginBottom: "12px" }}>
                  <label style={st.label}>Preset</label>
                  <div style={st.presetRow}>
                    <select value={selectedPreset} onChange={(e) => {
                      const name = e.target.value;
                      setSelectedPreset(name);
                      if (name) {
                        const preset = presets.find(p => p.name === name);
                        if (preset) applyPreset(preset);
                      }
                    }} style={{ ...st.formSelect, flex: 1 }}>
                      <option value="">-- Select Preset --</option>
                      {presets.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
                    </select>
                    <input type="text" value={presetName} onChange={(e) => setPresetName(e.target.value)}
                      placeholder="New preset name..." style={{ ...st.formInput, flex: 1 }} />
                    <button onClick={savePreset} style={{ ...st.btn, ...st.btnSm, ...(canSavePreset ? st.btnSecondaryActive : st.btnSecondary) }}>Save</button>
                    <button onClick={deletePreset} style={{ ...st.btn, ...st.btnSm, ...(selectedPreset ? st.btnDangerActive : st.btnDanger) }}>Delete</button>
                  </div>
                </div>

                {/* Run button */}
                <button onClick={runBacktest} disabled={!canRun}
                  style={{ ...st.runBtn, opacity: canRun ? 1 : 0.4, cursor: canRun ? "pointer" : "not-allowed" }}>
                  <Icons.Play />
                  <span>Run Backtest</span>
                </button>
              </div>
            </div>

            {/* Right: Runs */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ ...st.card, height: "100%", overflow: "hidden", display: "flex", flexDirection: "column" }}>
                <SectionHeader icon={<Icons.Activity />} number="" title="Runs" subtitle="Active and completed runs" />

                {(dbRuns.length > 0 || activeRunIds.length > 0) && (
                  <div style={st.runsToolbar}>
                    <label style={st.selectAllLabel}>
                      <input type="checkbox" checked={allSelected} onChange={toggleSelectAll}
                        style={{ width: "16px", height: "16px", accentColor: "#6366f1", cursor: "pointer" }} />
                      Select all
                    </label>
                    <button onClick={deleteSelectedRuns} disabled={selectedRunIds.size === 0}
                      style={{ ...st.btnDelete, opacity: selectedRunIds.size === 0 ? 0.4 : 1, cursor: selectedRunIds.size === 0 ? "not-allowed" : "pointer" }}>
                      Delete ({selectedRunIds.size})
                    </button>
                  </div>
                )}

                <div style={{ flex: 1, overflowY: "auto", maxHeight: "500px", display: "flex", flexDirection: "column", gap: "8px" }}>
                  {/* Active runs */}
                  {activeRunIds.map(id => {
                    const run = activeRuns[id];
                    const isQueued = run.status === "queued";
                    return (
                      <div key={id} style={st.runItem}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                            <span style={st.runName}>{run.strategy}</span>
                            <span style={{ ...st.runStatus, ...(isQueued ? st.runStatusQueued : st.runStatusRunning) }}>
                              {isQueued ? "queued" : "running"}
                            </span>
                          </div>
                          <div style={{ fontSize: "12px", color: "#64748b", marginBottom: isQueued ? 0 : "6px" }}>
                            {run.symbols.length} symbol{run.symbols.length !== 1 ? "s" : ""} · {run.startDate || "all"} to {run.endDate || "all"}
                          </div>
                          {!isQueued && (
                            <div style={st.progressBar}>
                              <div style={{ ...st.progressFill, width: `${run.progress}%` }} />
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}

                  {/* DB runs */}
                  {dbRuns.filter(r => r.status !== "running").map(r => {
                    const config = r.config || {};
                    const stratNames = config.strategies ? config.strategies.join(", ") : r.name;
                    const symbolCount = (config.symbols || []).length;
                    const sd = config.start_date || "-";
                    const ed = config.end_date || "-";
                    const timePart = r.run_id.slice(11, 19).replace(/-/g, ":");
                    const isSelected = selectedRunIds.has(r.run_id);
                    const isCompleted = r.status === "completed";
                    return (
                      <div key={r.run_id} style={{ ...st.runItem, borderColor: isSelected ? "#6366f1" : "rgba(51,65,85,0.4)" }}>
                        <input type="checkbox" checked={isSelected} onChange={() => toggleRunSelection(r.run_id)}
                          style={{ flexShrink: 0, marginTop: "2px", width: "16px", height: "16px", accentColor: "#6366f1", cursor: "pointer" }} />
                        <div style={{ flex: 1, minWidth: 0, cursor: isCompleted ? "pointer" : "default", opacity: isCompleted ? 1 : 0.7 }}
                          onClick={() => isCompleted && selectAnalysisRun(r.run_id)}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                            <span style={st.runName}>
                              {stratNames} <span style={{ color: "#64748b", fontSize: "11px", marginLeft: "4px" }}>{timePart}</span>
                            </span>
                            <span style={{
                              ...st.runStatus,
                              ...(r.status === "completed" ? st.runStatusCompleted :
                                  r.status === "failed" ? st.runStatusFailed :
                                  r.status === "cancelled" ? st.runStatusCancelled :
                                  r.status.startsWith("error") ? st.runStatusFailed : {})
                            }}>
                              {r.status}
                            </span>
                          </div>
                          <div style={{ fontSize: "12px", color: "#64748b" }}>
                            {symbolCount} symbol{symbolCount !== 1 ? "s" : ""} · {sd} to {ed}
                          </div>
                        </div>
                      </div>
                    );
                  })}

                  {dbRuns.length === 0 && activeRunIds.length === 0 && (
                    <div style={st.emptyState}>
                      <p>No runs yet</p>
                      <p style={{ marginTop: "4px", fontSize: "11px" }}>Configure settings and click Run Backtest</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* ════════════════════════════════════════════════════════
              Box 2: Analysis
              ════════════════════════════════════════════════════════ */}
          <div style={{ ...st.card, marginBottom: "16px", position: "relative", zIndex: 3 }}>
            <SectionHeader icon={<Icons.Table />} number="03" title="Analysis" subtitle="Select a completed run to analyze" />

            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <label style={{ fontSize: "12px", color: "#64748b", fontWeight: 500, whiteSpace: "nowrap" }}>Run:</label>
              <div style={{ flex: 1, maxWidth: "400px" }}>
                <Select value={analysisRunId || ""} onChange={(val) => selectAnalysisRun(val)}
                  options={[
                    { value: "", label: "Select a completed run..." },
                    ...completedRuns.map(r => {
                      const config = r.config || {};
                      const stratNames = config.strategies ? config.strategies.join(", ") : r.name;
                      const timePart = r.run_id.slice(11, 19).replace(/-/g, ":");
                      return { value: r.run_id, label: `${stratNames} (${timePart})` };
                    }),
                  ]}
                  placeholder="Select a completed run..." />
              </div>
            </div>
          </div>

          {/* ════════════════════════════════════════════════════════
              Box 3: Symbol Performance
              ════════════════════════════════════════════════════════ */}
          <div style={{ ...st.card, marginBottom: "16px", position: "relative", zIndex: 2 }}>
            <SectionHeader icon={<Icons.Activity />} number="04" title="Symbol Performance" subtitle="Per-symbol PnL and trade journey" />

            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
              <label style={{ fontSize: "12px", color: "#64748b", fontWeight: 500, whiteSpace: "nowrap" }}>Symbol:</label>
              <div style={{ position: "relative", flex: 1, maxWidth: "300px" }} ref={perfRef}>
                <input type="text" value={perfSymbolSearch}
                  disabled={perfSymbols.length === 0}
                  placeholder={perfSymbols.length === 0 ? "Select a run first..." : "Search symbol..."}
                  onChange={(e) => { setPerfSymbolSearch(e.target.value); setShowPerfSuggestions(true); setPerfSuggestionIndex(-1); setPerfSelectedSymbol(null); }}
                  onFocus={() => { if (perfSymbolSearch || perfSymbols.length > 0) setShowPerfSuggestions(true); }}
                  onKeyDown={onPerfSymbolKeydown}
                  autoComplete="off"
                  style={st.perfInput} />
                {showPerfSuggestions && perfFilteredSymbols.length > 0 && (
                  <div style={st.perfSuggestions}>
                    {perfFilteredSymbols.map((s, i) => (
                      <div key={s} onClick={() => { setPerfSelectedSymbol(s); setPerfSymbolSearch(s); setShowPerfSuggestions(false); }}
                        style={{ ...st.perfSuggestion, background: i === perfSuggestionIndex ? "rgba(99,102,241,0.15)" : "transparent", color: i === perfSuggestionIndex ? "#818cf8" : "#e2e8f0" }}>
                        {s}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: "flex", gap: "16px" }}>
              <div style={st.chartCard}>
                <h3 style={st.chartCardTitle}>PnL Summary</h3>
                <div style={st.chartContent}>
                  {analysisRunId && perfSelectedSymbol ? (
                    <img src={`/api/runs/${analysisRunId}/pnl-summary.png?symbol=${encodeURIComponent(perfSelectedSymbol)}`}
                      alt="PnL Summary" style={st.chartImg}
                      onError={(e) => { e.target.style.display = "none"; e.target.parentNode.innerHTML = '<div style="color: #475569; font-size: 13px;">Failed to load chart</div>'; }} />
                  ) : (
                    <div style={{ color: "#475569", fontSize: "13px" }}>Select a run and symbol</div>
                  )}
                </div>
              </div>
              <div style={st.chartCard}>
                <h3 style={st.chartCardTitle}>Trade Journey</h3>
                <div style={st.chartContent}>
                  {analysisRunId && perfSelectedSymbol ? (
                    <img src={`/api/runs/${analysisRunId}/trade-journey.png?symbol=${encodeURIComponent(perfSelectedSymbol)}`}
                      alt="Trade Journey" style={st.chartImg}
                      onError={(e) => { e.target.style.display = "none"; e.target.parentNode.innerHTML = '<div style="color: #475569; font-size: 13px;">Failed to load chart</div>'; }} />
                  ) : (
                    <div style={{ color: "#475569", fontSize: "13px" }}>Select a run and symbol</div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* ════════════════════════════════════════════════════════
              Box 4: Trades
              ════════════════════════════════════════════════════════ */}
          <div style={{ ...st.card, position: "relative", zIndex: 1 }}>
            <SectionHeader icon={<Icons.Table />} number="05" title="Trades" subtitle="Round-trip trade details and charts" />

            {analysisRunId ? (
              <>
                {/* Settings row */}
                <div style={st.settingsBox}>
                  <div style={{ display: "flex", alignItems: "center", gap: "24px", flexWrap: "wrap" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <label style={{ fontSize: "12px", color: "#64748b", fontWeight: 500 }}>Symbol:</label>
                      <input type="text" value={tradesSymbolFilter} onChange={(e) => setTradesSymbolFilter(e.target.value)}
                        placeholder="Filter symbols..." style={st.settingsInput} />
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <label style={{ fontSize: "12px", color: "#64748b", fontWeight: 500 }}>Context:</label>
                      <input type="number" value={chartContext} min={10} max={500}
                        onChange={(e) => onContextChange(e.target.value)}
                        style={{ ...st.settingsInput, width: "80px" }} />
                    </div>
                  </div>
                </div>

                {/* Indicator settings panel */}
                {analysisRunId && (
                  <div style={st.indSettingsPanel}>
                    <div style={st.indSettingsHeader}>Chart Settings</div>
                    <div style={{ padding: "0 16px 16px" }}>
                      {/* Chart type */}
                      <div style={{ display: "flex", alignItems: "center", gap: "24px", marginBottom: "12px", paddingBottom: "12px", borderBottom: "1px solid rgba(33,38,45,0.5)" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <label style={{ fontSize: "12px", color: "#64748b", fontWeight: 500 }}>Chart Type:</label>
                          <select value={chartType} onChange={(e) => onChartTypeChange(e.target.value)} style={st.indSelect}>
                            {CHART_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                          </select>
                        </div>
                      </div>

                      {/* Indicator settings table */}
                      {indicatorNames.length > 0 && (
                        <>
                          <table style={st.indTable}>
                            <thead>
                              <tr>
                                <th style={st.indTh}>Indicator</th>
                                <th style={st.indTh}>Panel</th>
                                <th style={st.indTh}>Below</th>
                                <th style={st.indTh}>Style</th>
                                <th style={st.indTh}>Color</th>
                                <th style={st.indTh}>Width</th>
                                <th style={st.indTh}>Visible</th>
                              </tr>
                            </thead>
                            <tbody>
                              {indicatorNames.map(name => {
                                const cfg = (chartSettingsData.indicators || {})[name] || { panel: 0, below_price: true, style: "line", color: "black", width: "normal", visible: true };
                                return (
                                  <tr key={name} style={{ borderBottom: "1px solid rgba(33,38,45,0.5)" }}>
                                    <td style={{ ...st.indTd, fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", maxWidth: "250px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={name}>{name}</td>
                                    <td style={st.indTd}>
                                      <input type="number" min={0} value={cfg.panel || 0}
                                        onChange={(e) => onIndSettingChange(name, "panel", e.target.value)}
                                        style={{ ...st.indNumInput, width: "50px" }} />
                                    </td>
                                    <td style={st.indTd}>
                                      <input type="checkbox" checked={cfg.below_price !== false}
                                        disabled={(cfg.panel || 0) === 0}
                                        onChange={(e) => onIndSettingChange(name, "below_price", e.target.checked)}
                                        style={{ cursor: "pointer" }} />
                                    </td>
                                    <td style={st.indTd}>
                                      <select value={cfg.style || "line"} onChange={(e) => onIndSettingChange(name, "style", e.target.value)} style={st.indSelect}>
                                        {VALID_STYLES.map(s => <option key={s} value={s}>{formatParamName(s)}</option>)}
                                      </select>
                                    </td>
                                    <td style={st.indTd}>
                                      <select value={cfg.color || "black"} onChange={(e) => onIndSettingChange(name, "color", e.target.value)} style={st.indSelect}>
                                        {VALID_COLORS.map(c => <option key={c} value={c}>{formatParamName(c)}</option>)}
                                      </select>
                                    </td>
                                    <td style={st.indTd}>
                                      <select value={cfg.width || "normal"} onChange={(e) => onIndSettingChange(name, "width", e.target.value)} style={st.indSelect}>
                                        {VALID_WIDTHS.map(w => <option key={w} value={w}>{formatParamName(w)}</option>)}
                                      </select>
                                    </td>
                                    <td style={st.indTd}>
                                      <input type="checkbox" checked={cfg.visible !== false}
                                        onChange={(e) => onIndSettingChange(name, "visible", e.target.checked)}
                                        style={{ cursor: "pointer" }} />
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>

                          {/* Fill between */}
                          <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: "1px solid rgba(33,38,45,0.5)" }}>
                            <label style={{ fontSize: "12px", color: "#64748b", fontWeight: 500 }}>Fill Between</label>
                            {(chartSettingsData.fill_between || []).map((fb, idx) => (
                              <div key={idx} style={st.fillBetweenRow}>
                                <label style={{ fontSize: "11px", color: "#64748b" }}>Upper:</label>
                                <select value={fb.upper} onChange={(e) => onFillBetweenChange(idx, "upper", e.target.value)} style={st.fbSelect}>
                                  {indicatorNames.map(n => <option key={n} value={n}>{n}</option>)}
                                </select>
                                <label style={{ fontSize: "11px", color: "#64748b" }}>Lower:</label>
                                <select value={fb.lower} onChange={(e) => onFillBetweenChange(idx, "lower", e.target.value)} style={st.fbSelect}>
                                  {indicatorNames.map(n => <option key={n} value={n}>{n}</option>)}
                                </select>
                                <label style={{ fontSize: "11px", color: "#64748b" }}>Color:</label>
                                <select value={fb.color} onChange={(e) => onFillBetweenChange(idx, "color", e.target.value)} style={st.fbSelect}>
                                  {VALID_COLORS.map(c => <option key={c} value={c}>{formatParamName(c)}</option>)}
                                </select>
                                <label style={{ fontSize: "11px", color: "#64748b" }}>Alpha:</label>
                                <input type="number" step="0.05" min={0} max={1} value={fb.alpha}
                                  onChange={(e) => onFillBetweenChange(idx, "alpha", e.target.value)}
                                  style={st.fbInput} />
                                <button onClick={() => removeFillBetween(idx)} style={st.fbRemoveBtn}>Remove</button>
                              </div>
                            ))}
                            <div style={{ marginTop: "8px" }}>
                              <button onClick={addFillBetween} style={st.fbAddBtn}>+ Add Fill Between</button>
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* Trades table */}
                {roundtrips.length === 0 ? (
                  <div style={st.emptyState}>No round-trip trades found</div>
                ) : (
                  <div style={{ border: "1px solid rgba(51,65,85,0.35)", borderRadius: "8px", overflow: "hidden" }}>
                    <table style={st.tradesTable}>
                      <thead>
                        <tr>
                          {COLUMNS.map(c => (
                            <th key={c.key} onClick={() => handleSort(c.key)}
                              style={{ ...st.tradesTh, color: sortColumn === c.key ? "#e2e8f0" : "#64748b" }}>
                              {c.label}
                              <span style={{ marginLeft: "4px", opacity: sortColumn === c.key ? 1 : 0.3 }}>
                                {sortColumn === c.key ? (sortAsc ? "▲" : "▼") : "▲"}
                              </span>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {sortedTrades.map((rt, idx) => {
                          const pnlGrossClass = rt.pnl_before_commission >= 0 ? "#3fb950" : "#f85149";
                          const pnlNetClass = rt.pnl_after_commission >= 0 ? "#3fb950" : "#f85149";
                          const hwmColor = rt.high_watermark >= 0 ? "#3fb950" : "#f85149";
                          const lwmColor = rt.low_watermark >= 0 ? "#3fb950" : "#f85149";
                          const mddColor = rt.max_drawdown > 0 ? "#f85149" : "#e2e8f0";
                          const dirColor = rt.direction.toLowerCase() === "long" ? "#3fb950" : "#f85149";
                          const isExpanded = expandedTradeIdx.has(idx);
                          return (
                            <React.Fragment key={`${rt.symbol}_${rt.entry_ts}_${idx}`}>
                              <tr onClick={() => toggleChart(idx)} style={{ cursor: "pointer", borderBottom: "1px solid rgba(33,38,45,0.5)" }}
                                onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(99,102,241,0.04)"; }}
                                onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}>
                                <td style={{ ...st.tradesTd, fontFamily: "'JetBrains Mono', monospace" }}>{rt.symbol}</td>
                                <td style={st.tradesTd}>{rt.trade_num}</td>
                                <td style={{ ...st.tradesTd, fontWeight: 500, color: dirColor }}>{rt.direction}</td>
                                <td style={st.tradesTd}>{rt.duration_bars}</td>
                                <td style={st.tradesTd}>{rt.max_position}</td>
                                <td style={{ ...st.tradesTd, fontWeight: 500, fontFamily: "'JetBrains Mono', monospace", color: hwmColor }}>{rt.high_watermark >= 0 ? "+" : ""}{rt.high_watermark.toFixed(2)}</td>
                                <td style={{ ...st.tradesTd, fontWeight: 500, fontFamily: "'JetBrains Mono', monospace", color: lwmColor }}>{rt.low_watermark >= 0 ? "+" : ""}{rt.low_watermark.toFixed(2)}</td>
                                <td style={{ ...st.tradesTd, fontWeight: 500, fontFamily: "'JetBrains Mono', monospace", color: mddColor }}>{rt.max_drawdown > 0 ? "-" : ""}{rt.max_drawdown.toFixed(2)}</td>
                                <td style={{ ...st.tradesTd, fontWeight: 500, fontFamily: "'JetBrains Mono', monospace", color: pnlGrossClass }}>{rt.pnl_before_commission >= 0 ? "+" : ""}{rt.pnl_before_commission.toFixed(2)}</td>
                                <td style={{ ...st.tradesTd, fontWeight: 500, fontFamily: "'JetBrains Mono', monospace", color: pnlNetClass }}>{rt.pnl_after_commission >= 0 ? "+" : ""}{rt.pnl_after_commission.toFixed(2)}</td>
                              </tr>
                              {isExpanded && (
                                <tr>
                                  <td colSpan={10} style={{ padding: "16px", background: "rgba(15,23,42,0.5)" }}>
                                    <div style={{ textAlign: "center" }}>
                                      <img src={getChartUrl(rt)} alt="Trade Chart" style={{ maxWidth: "100%", height: "auto", borderRadius: "4px" }}
                                        onError={(e) => { e.target.style.display = "none"; e.target.parentNode.innerHTML = '<div style="color: #475569; font-size: 13px; padding: 24px;">Failed to load chart</div>'; }} />
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </React.Fragment>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            ) : (
              <div style={st.emptyState}>Select a run to view trades</div>
            )}
          </div>

        </div>
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
    display: "flex", justifyContent: "space-between", alignItems: "center",
    marginBottom: "22px", paddingBottom: "16px",
    borderBottom: "1px solid rgba(51,65,85,0.35)",
  },
  pageTitle: { fontSize: "20px", fontWeight: 600, color: "#f1f5f9", letterSpacing: "-0.3px" },
  pageSubtitle: { fontSize: "12.5px", color: "#64748b", marginTop: "2px" },
  card: {
    background: "rgba(15,23,42,0.7)", border: "1px solid rgba(51,65,85,0.45)",
    borderRadius: "10px", padding: "18px", backdropFilter: "blur(10px)",
    display: "flex", flexDirection: "column",
  },
  sectionIcon: {
    width: "30px", height: "30px", borderRadius: "7px",
    background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)",
    display: "flex", alignItems: "center", justifyContent: "center", color: "#818cf8", flexShrink: 0,
  },
  sectionNumber: { fontSize: "10px", fontWeight: 600, color: "#818cf8", fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.5px" },
  sectionTitle: { fontSize: "14px", fontWeight: 600, color: "#f1f5f9", letterSpacing: "-0.2px" },
  sectionSubtitle: { fontSize: "11px", color: "#64748b", marginTop: "1px" },
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
    padding: "3px", zIndex: 50, maxHeight: "180px", overflowY: "auto",
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
    color: "#e2e8f0", fontSize: "12px", fontFamily: "'DM Sans', sans-serif", padding: "2px 0",
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
  emptyState: {
    textAlign: "center", color: "#475569", fontSize: "12px", padding: "24px 16px",
    fontStyle: "italic", flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
  },

  // ─── Backtest-specific styles ───
  paramsContainer: {
    padding: "12px", background: "rgba(30,41,59,0.4)", borderRadius: "6px",
    border: "1px solid rgba(51,65,85,0.3)",
  },
  paramRow: {
    display: "flex", gap: "12px", marginBottom: "8px", alignItems: "center",
  },
  formInput: {
    flex: 1, padding: "7px 10px", background: "rgba(30,41,59,0.6)",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "5px",
    color: "#e2e8f0", fontSize: "12px", fontFamily: "'DM Sans', sans-serif", outline: "none",
  },
  formSelect: {
    flex: 1, padding: "7px 10px", background: "rgba(30,41,59,0.6)",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "5px",
    color: "#e2e8f0", fontSize: "12px", fontFamily: "'DM Sans', sans-serif",
    cursor: "pointer", outline: "none",
  },
  presetRow: {
    display: "flex", gap: "6px", alignItems: "center",
    background: "rgba(30,41,59,0.4)", borderRadius: "6px", padding: "8px 10px",
    border: "1px solid rgba(51,65,85,0.3)",
  },
  btn: {
    border: "none", borderRadius: "5px", fontSize: "11px", fontWeight: 600,
    fontFamily: "'DM Sans', sans-serif", transition: "all 0.15s",
  },
  btnSm: { padding: "6px 12px", whiteSpace: "nowrap" },
  btnSecondary: { background: "#1e293b", color: "#64748b", cursor: "not-allowed" },
  btnSecondaryActive: { background: "linear-gradient(135deg, #6366f1, #818cf8)", color: "#fff", cursor: "pointer" },
  btnDanger: { background: "#1e293b", color: "#64748b", cursor: "not-allowed" },
  btnDangerActive: { background: "rgba(248,81,73,0.12)", color: "#f85149", cursor: "pointer", border: "1px solid rgba(248,81,73,0.3)" },
  runBtn: {
    display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "8px",
    width: "100%", padding: "10px 20px",
    background: "linear-gradient(135deg, #6366f1 0%, #818cf8 100%)", border: "none",
    borderRadius: "6px", color: "#fff", fontSize: "13px", fontWeight: 600,
    fontFamily: "'DM Sans', sans-serif",
    boxShadow: "0 2px 10px rgba(99,102,241,0.25)", transition: "all 0.15s",
  },

  // Runs
  runsToolbar: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    marginBottom: "12px", paddingBottom: "12px",
    borderBottom: "1px solid rgba(51,65,85,0.3)",
  },
  selectAllLabel: {
    display: "flex", alignItems: "center", gap: "8px",
    fontSize: "12px", color: "#64748b", cursor: "pointer",
  },
  btnDelete: {
    padding: "5px 12px", background: "rgba(248,81,73,0.12)",
    border: "1px solid rgba(248,81,73,0.3)", borderRadius: "5px",
    color: "#f85149", fontSize: "11px", fontWeight: 600,
    fontFamily: "'DM Sans', sans-serif", cursor: "pointer",
  },
  runItem: {
    background: "rgba(30,41,59,0.3)", border: "1px solid rgba(51,65,85,0.4)",
    borderRadius: "6px", padding: "10px 12px",
    display: "flex", gap: "10px", alignItems: "flex-start",
  },
  runName: {
    fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#e2e8f0",
  },
  runStatus: {
    fontSize: "10px", fontWeight: 600, padding: "2px 8px", borderRadius: "10px",
    textTransform: "uppercase", letterSpacing: "0.3px",
  },
  runStatusRunning: { background: "rgba(251,191,36,0.15)", color: "#fbbf24" },
  runStatusQueued: { background: "rgba(100,116,139,0.15)", color: "#94a3b8" },
  runStatusCompleted: { background: "rgba(52,211,153,0.12)", color: "#34d399" },
  runStatusFailed: { background: "rgba(248,81,73,0.12)", color: "#f85149" },
  runStatusCancelled: { background: "rgba(51,65,85,0.3)", color: "#64748b" },
  progressBar: {
    height: "4px", background: "rgba(51,65,85,0.4)", borderRadius: "2px", overflow: "hidden",
  },
  progressFill: {
    height: "100%", background: "linear-gradient(90deg, #6366f1, #818cf8)",
    borderRadius: "2px", transition: "width 0.3s ease",
  },

  // Symbol performance
  perfInput: {
    width: "100%", padding: "8px 12px", background: "rgba(30,41,59,0.6)",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "6px",
    color: "#e2e8f0", fontSize: "12px", fontFamily: "'DM Sans', sans-serif",
    outline: "none",
  },
  perfSuggestions: {
    position: "absolute", top: "100%", left: 0, right: 0,
    background: "#1e293b", border: "1px solid rgba(51,65,85,0.8)",
    borderRadius: "6px", maxHeight: "200px", overflowY: "auto",
    zIndex: 100, marginTop: "4px",
    boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
  },
  perfSuggestion: {
    padding: "8px 12px", cursor: "pointer", fontSize: "12px",
    fontFamily: "'JetBrains Mono', monospace",
  },

  // Charts
  chartCard: {
    flex: 1, background: "rgba(30,41,59,0.3)", border: "1px solid rgba(51,65,85,0.4)",
    borderRadius: "8px", padding: "16px", display: "flex", flexDirection: "column", minWidth: 0,
  },
  chartCardTitle: { margin: "0 0 12px 0", fontSize: "13px", fontWeight: 500, color: "#64748b" },
  chartContent: { flex: 1, display: "flex", alignItems: "center", justifyContent: "center", minHeight: "300px" },
  chartImg: { maxWidth: "100%", maxHeight: "100%", height: "auto", borderRadius: "4px", background: "#fff" },

  // Trades settings
  settingsBox: {
    background: "rgba(30,41,59,0.3)", border: "1px solid rgba(51,65,85,0.3)",
    borderRadius: "6px", padding: "12px 16px", marginBottom: "12px",
  },
  settingsInput: {
    padding: "6px 10px", background: "rgba(30,41,59,0.6)",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "4px",
    color: "#e2e8f0", fontSize: "12px", fontFamily: "'DM Sans', sans-serif", outline: "none",
  },

  // Indicator settings
  indSettingsPanel: {
    background: "rgba(30,41,59,0.3)", border: "1px solid rgba(51,65,85,0.3)",
    borderRadius: "6px", marginBottom: "12px", overflow: "hidden",
  },
  indSettingsHeader: {
    display: "flex", alignItems: "center", gap: "8px",
    padding: "12px 16px", color: "#64748b", fontSize: "12px", fontWeight: 600,
    textTransform: "uppercase", letterSpacing: "0.3px",
  },
  indTable: { width: "100%", borderCollapse: "collapse", fontSize: "12px" },
  indTh: {
    padding: "8px 10px", textAlign: "left", color: "#64748b", fontWeight: 500,
    borderBottom: "1px solid rgba(51,65,85,0.4)", fontSize: "11px",
  },
  indTd: { padding: "6px 10px", color: "#e2e8f0" },
  indSelect: {
    padding: "4px 8px", background: "rgba(30,41,59,0.6)",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "4px",
    color: "#e2e8f0", fontSize: "11px", cursor: "pointer", outline: "none",
  },
  indNumInput: {
    padding: "4px 6px", background: "rgba(30,41,59,0.6)",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "4px",
    color: "#e2e8f0", fontSize: "11px", outline: "none",
  },

  // Fill between
  fillBetweenRow: {
    display: "flex", alignItems: "center", gap: "8px", marginTop: "8px", flexWrap: "wrap",
  },
  fbSelect: {
    padding: "4px 8px", background: "rgba(30,41,59,0.6)",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "4px",
    color: "#e2e8f0", fontSize: "11px", cursor: "pointer", outline: "none",
  },
  fbInput: {
    padding: "4px 8px", background: "rgba(30,41,59,0.6)",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "4px",
    color: "#e2e8f0", fontSize: "11px", outline: "none", width: "60px",
  },
  fbRemoveBtn: {
    padding: "4px 10px", background: "rgba(248,81,73,0.08)",
    border: "1px solid rgba(248,81,73,0.25)", borderRadius: "4px",
    color: "#f85149", fontSize: "11px", cursor: "pointer",
    fontFamily: "'DM Sans', sans-serif",
  },
  fbAddBtn: {
    padding: "5px 12px", background: "transparent",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "4px",
    color: "#64748b", fontSize: "11px", cursor: "pointer",
    fontFamily: "'DM Sans', sans-serif",
  },

  // Trades table
  tradesTable: { width: "100%", borderCollapse: "collapse", fontSize: "12px" },
  tradesTh: {
    position: "sticky", top: 0, background: "rgba(30,41,59,0.6)",
    padding: "8px 12px", textAlign: "left", fontWeight: 500,
    borderBottom: "1px solid rgba(51,65,85,0.4)", cursor: "pointer",
    userSelect: "none", whiteSpace: "nowrap", fontSize: "11px",
    textTransform: "uppercase", letterSpacing: "0.3px",
  },
  tradesTd: {
    padding: "8px 12px", color: "#e2e8f0", whiteSpace: "nowrap", fontSize: "12px",
  },
};

// ─── Mount ────────────────────────────────────────────────
ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(BacktestApp));
