const { useState, useRef, useEffect, useCallback, useMemo } = React;

// ─── Constants ─────────────────────────────────────────────
const RTYPE_MAP = { "Second": 32, "Minute": 33, "Hour": 34, "Day": 35 };
const RTYPE_LABELS = { 32: "Second", 33: "Minute", 34: "Hour", 35: "Day" };

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
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
};

// ─── Reusable Components ──────────────────────────────────
function Select({ value, onChange, options, placeholder }) {
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
          {normalizedOptions.map((opt) => (
            <button key={opt.value} onClick={() => { onChange(opt.value); setOpen(false); }}
              style={{ ...st.dropdownItem, background: opt.value === value ? "rgba(99,102,241,0.15)" : "transparent", color: opt.value === value ? "#818cf8" : "#cbd5e1" }}>
              {opt.label}
            </button>
          ))}
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

function SectionHeader({ icon, title, number, subtitle }) {
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

// ─── Popover Component ────────────────────────────────────
function Popover({ popover, splits, onClose }) {
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  if (!popover) return null;

  const split = splits.find((s) => s.split_id === popover.splitId);
  if (!split) return null;

  const top = popover.rect.bottom + 6;
  const left = popover.rect.left;

  let content = null;
  if (popover.type === "symbols") {
    content = (
      <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
        {split.symbols.map((sym) => (
          <span key={sym} style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: "11px",
            padding: "3px 8px", background: "rgba(99,102,241,0.12)",
            border: "1px solid rgba(99,102,241,0.25)", borderRadius: "4px",
            color: "#a5b4fc",
          }}>{sym}</span>
        ))}
      </div>
    );
  } else {
    let startDate, endDate, label;
    if (popover.type === "train") {
      startDate = split.total_start; endDate = split.train_end; label = "Train";
    } else if (popover.type === "dev") {
      startDate = split.train_end; endDate = split.dev_end; label = "Dev";
    } else {
      startDate = split.dev_end; endDate = split.total_end; label = "Test";
    }
    content = (
      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#cbd5e1" }}>
        <div style={{ fontSize: "10px", fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "6px" }}>{label} date range</div>
        <span>{startDate}</span>
        <span style={{ color: "#475569", margin: "0 8px" }}>&rarr;</span>
        <span>{endDate}</span>
      </div>
    );
  }

  return ReactDOM.createPortal(
    <div ref={ref} style={{ ...st.popoverBox, top, left }}>
      {content}
    </div>,
    document.body
  );
}

// ─── Main Component ───────────────────────────────────────
function SplitsApp() {
  // Data source state
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

  // Split-specific state
  const [trainPct, setTrainPct] = useState(60);
  const [devPct, setDevPct] = useState(20);
  const [splits, setSplits] = useState([]);
  const [saving, setSaving] = useState(false);
  const [popover, setPopover] = useState(null);

  // Derived values
  const testPct = 100 - trainPct - devPct;

  const pctError = useMemo(() => {
    if (trainPct < 1 || devPct < 1 || testPct < 1) return "Each region must be at least 1%";
    if (trainPct + devPct > 99) return "Train + Dev must be <= 99%";
    return "";
  }, [trainPct, devPct, testPct]);

  const { trainEnd, devEnd } = useMemo(() => {
    if (!startDate || !endDate || pctError) return { trainEnd: "", devEnd: "" };
    const start = new Date(startDate + "T00:00:00Z");
    const end = new Date(endDate + "T00:00:00Z");
    const totalDays = Math.round((end - start) / (1000 * 60 * 60 * 24));
    if (totalDays <= 0) return { trainEnd: "", devEnd: "" };
    const trainDays = Math.round(totalDays * trainPct / 100);
    const devDays = Math.round(totalDays * devPct / 100);
    const tEnd = new Date(start);
    tEnd.setUTCDate(tEnd.getUTCDate() + trainDays);
    const dEnd = new Date(tEnd);
    dEnd.setUTCDate(dEnd.getUTCDate() + devDays);
    return {
      trainEnd: tEnd.toISOString().split("T")[0],
      devEnd: dEnd.toISOString().split("T")[0],
    };
  }, [startDate, endDate, trainPct, devPct, pctError]);

  const canSave = useMemo(() => {
    const rtype = barPeriod ? RTYPE_MAP[barPeriod] : null;
    return !!(
      rtype && selectedPublisherId && selectedSymbols.length > 0 &&
      startDate && endDate && !pctError && trainEnd && devEnd && !saving
    );
  }, [barPeriod, selectedPublisherId, selectedSymbols, startDate, endDate, pctError, trainEnd, devEnd, saving]);

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

  // ─── On mount: load rtypes + saved splits ───
  useEffect(() => {
    fetch("/api/secmaster/symbols_coverage").then(r => r.json()).then(data => {
      const syms = data.symbols || [];
      const rtypeSet = new Set(syms.map(s => s.rtype));
      const sorted = [...rtypeSet].sort((a, b) => a - b);
      setRtypes(sorted);
      if (sorted.length === 1) setBarPeriod(RTYPE_LABELS[sorted[0]] || "rtype " + sorted[0]);
    });
    loadSplits();
  }, []);

  // ─── On barPeriod change: load publishers, clear downstream ───
  useEffect(() => {
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
    setSelectedPublisherId(null); setCoverageSymbols([]);
    setSelectedSymbols([]);
    return () => { cancelled = true; };
  }, [barPeriod]);

  // ─── On provider + barPeriod change: load datasets, clear downstream ───
  useEffect(() => {
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

  // ─── On selectedPublisherId + barPeriod change: load symbol coverage ───
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
        setSelectedSymbols(syms.length === 1 ? [syms[0]] : []);
      });
    return () => { cancelled = true; };
  }, [selectedPublisherId, barPeriod, filterAndSetCoverage]);

  // ─── On contract type change: re-filter coverage ───
  useEffect(() => {
    if (allCoverageData.length > 0) {
      const syms = filterAndSetCoverage(allCoverageData, contractType, hasContinuousSymbols);
      setSelectedSymbols(syms.length === 1 ? [syms[0]] : []);
    }
  }, [contractType, allCoverageData, hasContinuousSymbols, filterAndSetCoverage]);

  // ─── Date range auto-fill from coverage ───
  useEffect(() => {
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
      setStartDate(new Date(Math.floor(minTs / 1000000)).toISOString().split("T")[0]);
      setEndDate(new Date(Math.floor(maxTs / 1000000)).toISOString().split("T")[0]);
    }
  }, [selectedSymbols, symbolCoverage]);

  // ─── Outside-click handler for symbol dropdown ───
  const symbolRef = useRef(null);
  useEffect(() => {
    const handler = (e) => { if (symbolRef.current && !symbolRef.current.contains(e.target)) setShowSymbolDropdown(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // ─── Venue change handler ───
  const handleVenueChange = (datasetLabel) => {
    setExchange(datasetLabel);
    const ds = datasets.find(d => d.dataset === datasetLabel);
    if (ds) setSelectedPublisherId(ds.publisher_id);
  };

  // ─── Symbol search ───
  const filteredSymbols = coverageSymbols.filter(
    (sym) => sym.toLowerCase().includes(symbolSearch.toLowerCase()) && !selectedSymbols.includes(sym)
  );

  // ─── API functions ───
  const loadSplits = async () => {
    const res = await fetch("/api/splits");
    const data = await res.json();
    setSplits(data.splits || []);
  };

  const saveSplit = async () => {
    const rtype = RTYPE_MAP[barPeriod];
    if (!rtype || !selectedPublisherId || selectedSymbols.length === 0) return;
    setSaving(true);
    try {
      const symbolType = (hasContinuousSymbols && contractType === "continuous") ? "continuous" : "raw_symbol";
      const res = await fetch("/api/splits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          publisher_id: selectedPublisherId,
          publisher_name: provider,
          rtype,
          symbols: selectedSymbols,
          symbol_type: symbolType,
          total_start: startDate,
          total_end: endDate,
          train_pct: trainPct,
          dev_pct: devPct,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        alert(data.detail || "Failed to save split");
        return;
      }
      await loadSplits();
    } catch (e) {
      alert("Error saving split: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const deleteSplit = async (splitId) => {
    if (!confirm("Delete this split?")) return;
    await fetch(`/api/splits/${splitId}`, { method: "DELETE" });
    await loadSplits();
  };

  // ─── Computed options ───
  const barPeriodOptions = rtypes.map(r => ({
    value: RTYPE_LABELS[r] || "rtype " + r,
    label: RTYPE_LABELS[r] || "rtype " + r,
  }));

  const providerOptions = publishers.map(p => ({
    value: p,
    label: capitalize(p),
  }));

  const venueOptions = datasets.map(d => ({
    value: d.dataset,
    label: d.dataset,
  }));

  // ─── Render ───
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

      <Sidebar activePage="splits" onNavigate={(page) => {
        if (page === "explorer") { window.location.href = "/explorer"; return; }
        if (page === "backtest") { window.location.href = "/backtest"; return; }
      }} />

      <div style={st.mainContent}>
        <div style={st.page}>

          {/* ─── Page Header ─── */}
          <div style={st.header}>
            <div>
              <h1 style={st.pageTitle}>Data Splits</h1>
              <p style={st.pageSubtitle}>Define and manage data splits</p>
            </div>
          </div>

          {/* ─── TOP ROW: 2 columns ─── */}
          <div style={st.topGrid}>

            {/* ── Card 1: Split Configuration ── */}
            <div style={{ ...st.card, position: "relative", zIndex: 2 }}>
              <SectionHeader icon={<Icons.Layers />} number="01" title="Split Configuration" subtitle="Select data source and set train/dev/test percentages" />

              {/* Data source controls */}
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

              {/* Symbols — tag input */}
              {coverageSymbols.length > 0 && (
                <div style={{ marginTop: "12px", position: "relative" }} ref={symbolRef}>
                  <div style={st.tagInputWrap} onClick={() => document.getElementById("sym-search")?.focus()}>
                    {selectedSymbols.map((sym) => (
                      <Chip key={sym} label={sym} onRemove={() => setSelectedSymbols(selectedSymbols.filter(s => s !== sym))} />
                    ))}
                    <input id="sym-search" type="text" value={symbolSearch}
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

              {/* Divider */}
              <div style={{ height: "1px", background: "rgba(51,65,85,0.35)", margin: "14px 0" }} />

              {/* Split percentages */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px", marginBottom: "14px" }}>
                <div>
                  <input type="number" value={trainPct} min={1} max={98}
                    onChange={(e) => setTrainPct(parseInt(e.target.value) || 0)}
                    style={st.splitPctInput} />
                  <label style={st.labelBelow}>Train %</label>
                </div>
                <div>
                  <input type="number" value={devPct} min={1} max={98}
                    onChange={(e) => setDevPct(parseInt(e.target.value) || 0)}
                    style={st.splitPctInput} />
                  <label style={st.labelBelow}>Dev %</label>
                </div>
                <div>
                  <input type="number" value={testPct} readOnly style={{ ...st.splitPctInput, color: "#8b949e", cursor: "default", background: "rgba(30,41,59,0.3)" }} />
                  <label style={st.labelBelow}>Test %</label>
                </div>
              </div>

              {/* Date boundary preview */}
              {trainEnd && devEnd && (
                <div style={st.splitDatePreview}>
                  <div><span style={{ ...st.regionLabel, color: "#94a3b8" }}>Train</span> {startDate} &rarr; {trainEnd}</div>
                  <div><span style={{ ...st.regionLabel, color: "#94a3b8" }}>Dev</span> {trainEnd} &rarr; {devEnd}</div>
                  <div><span style={{ ...st.regionLabel, color: "#94a3b8" }}>Test</span> {devEnd} &rarr; {endDate}</div>
                </div>
              )}

              {/* Validation error */}
              {pctError && <div style={st.splitError}>{pctError}</div>}

              {/* Save button */}
              <button onClick={saveSplit} disabled={!canSave}
                style={{
                  ...st.saveBtn,
                  opacity: canSave ? 1 : 0.4,
                  cursor: canSave ? "pointer" : "default",
                }}>
                <Icons.Save />
                <span>{saving ? "Saving..." : "Save Split"}</span>
              </button>
            </div>

            {/* ── Card 2: Saved Splits ── */}
            <div style={{ ...st.card }}>
              <SectionHeader icon={<Icons.Table />} number="02" title="Saved Splits" subtitle="Manage existing data splits" />

              {splits.length === 0 ? (
                <div style={st.emptyState}>No splits saved yet</div>
              ) : (
                <div style={st.tableWrap}>
                  <table style={st.table}>
                    <thead>
                      <tr>
                        <th style={st.th}>Split Name</th>
                        <th style={st.th}># Symbols</th>
                        <th style={st.th}>Bar Period</th>
                        <th style={st.th}># Bars Train</th>
                        <th style={st.th}># Bars Dev</th>
                        <th style={st.th}># Bars Test</th>
                        <th style={{ ...st.th, width: "60px" }}></th>
                      </tr>
                    </thead>
                    <tbody>
                      {splits.map((s) => (
                        <tr key={s.split_id} style={{ borderBottom: "1px solid rgba(33,38,45,0.5)" }}
                          onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(99,102,241,0.04)"; }}
                          onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}>
                          <td style={st.td}>{s.name}</td>
                          <td style={st.td}>
                            <span style={st.clickableCell} onClick={(e) => setPopover({ type: "symbols", splitId: s.split_id, rect: e.currentTarget.getBoundingClientRect() })}>
                              {s.symbols.length}
                            </span>
                          </td>
                          <td style={{ ...st.td, fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", color: "#8b949e" }}>
                            {RTYPE_LABELS[s.rtype] || "rtype " + s.rtype}
                          </td>
                          <td style={st.td}>
                            <span style={st.clickableCell} onClick={(e) => setPopover({ type: "train", splitId: s.split_id, rect: e.currentTarget.getBoundingClientRect() })}>
                              {(s.train_bars || 0).toLocaleString()}
                            </span>
                          </td>
                          <td style={st.td}>
                            <span style={st.clickableCell} onClick={(e) => setPopover({ type: "dev", splitId: s.split_id, rect: e.currentTarget.getBoundingClientRect() })}>
                              {(s.dev_bars || 0).toLocaleString()}
                            </span>
                          </td>
                          <td style={st.td}>
                            <span style={st.clickableCell} onClick={(e) => setPopover({ type: "test", splitId: s.split_id, rect: e.currentTarget.getBoundingClientRect() })}>
                              {(s.test_bars || 0).toLocaleString()}
                            </span>
                          </td>
                          <td style={st.td}>
                            <button onClick={() => deleteSplit(s.split_id)} style={st.deleteBtn}>
                              <Icons.Trash />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <Popover popover={popover} splits={splits} onClose={() => setPopover(null)} />
            </div>

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
  topGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1.6fr",
    gap: "16px",
    alignItems: "stretch",
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
  emptyState: { textAlign: "center", color: "#475569", fontSize: "12px", padding: "24px 16px", fontStyle: "italic", flex: 1, display: "flex", alignItems: "center", justifyContent: "center" },
  tableWrap: { border: "1px solid rgba(51,65,85,0.35)", borderRadius: "8px", overflow: "hidden" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: "12px" },
  th: {
    padding: "8px 14px", textAlign: "left", fontSize: "10px", fontWeight: 600, color: "#64748b",
    textTransform: "uppercase", letterSpacing: "0.5px", background: "rgba(30,41,59,0.4)",
    borderBottom: "1px solid rgba(51,65,85,0.4)",
  },
  td: { padding: "7px 14px", verticalAlign: "top" },

  // Split-specific styles
  splitPctInput: {
    width: "100%", padding: "9px 10px", background: "rgba(30,41,59,0.6)",
    border: "1px solid rgba(51,65,85,0.5)", borderRadius: "6px", color: "#e2e8f0",
    fontSize: "12px", fontFamily: "'JetBrains Mono', monospace",
    textAlign: "center", outline: "none",
  },
  splitDatePreview: {
    fontSize: "12px", color: "#8b949e", marginBottom: "14px",
    lineHeight: "1.7", fontFamily: "'JetBrains Mono', monospace",
  },
  regionLabel: {
    display: "inline-block", minWidth: "42px", fontWeight: 600,
  },
  splitError: {
    color: "#f85149", fontSize: "12px", marginBottom: "8px",
  },
  saveBtn: {
    display: "inline-flex", alignItems: "center", gap: "6px", padding: "8px 18px",
    background: "linear-gradient(135deg, #6366f1 0%, #818cf8 100%)", border: "none",
    borderRadius: "6px", color: "#fff", fontSize: "12px", fontWeight: 600,
    fontFamily: "'DM Sans', sans-serif",
    boxShadow: "0 2px 10px rgba(99,102,241,0.25)",
    transition: "all 0.15s",
  },
  deleteBtn: {
    background: "transparent", border: "none",
    color: "#f85149", padding: "0", borderRadius: "0",
    cursor: "pointer", display: "flex", alignItems: "center",
    transition: "all 0.15s",
  },
  clickableCell: {
    color: "#58a6ff",
    cursor: "pointer",
    textDecoration: "none",
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: "11px",
  },
  popoverBox: {
    position: "fixed",
    background: "#1e293b",
    border: "1px solid rgba(51,65,85,0.8)",
    borderRadius: "7px",
    padding: "10px 14px",
    zIndex: 500,
    boxShadow: "0 10px 35px rgba(0,0,0,0.5)",
    maxHeight: "200px",
    overflowY: "auto",
  },
};

// ─── Mount ────────────────────────────────────────────────
ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(SplitsApp));
