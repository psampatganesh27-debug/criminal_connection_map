import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

const GROUP_CONFIG = {
  Person: { color: '#ef4444', label: 'Suspects' },
  Phone: { color: '#3b82f6', label: 'Phones' },
  Account: { color: '#10b981', label: 'Accounts' },
  FIR: { color: '#f59e0b', label: 'FIRs' },
  Vehicle: { color: '#a855f7', label: 'Vehicles' }
}

export default function App() {
  const [rawGraphData, setRawGraphData] = useState({ nodes: [], links: [] })
  const [influencers, setInfluencers] = useState([])
  const [selectedNode, setSelectedNode] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  
  const [appMode, setAppMode] = useState('NORMAL')
  const [propagatedNodeIds, setPropagatedNodeIds] = useState(new Set())
  const [watcherTargetId, setWatcherTargetId] = useState(null)

  const [pathMode, setPathMode] = useState(false)
  const [pathEndpoints, setPathEndpoints] = useState([])
  const [highlightedPath, setHighlightedPath] = useState([])

  // Set timeline bounds using absolute timestamps
  const MIN_TIMESTAMP = new Date('2026-07-01').getTime()
  const MAX_TIMESTAMP = new Date().getTime() // Automatically pulls today's exact date

  const [currentTimestamp, setCurrentTimestamp] = useState(MAX_TIMESTAMP) 
  
  const [activeFilters, setActiveFilters] = useState({
    Person: true, Phone: true, Account: true, FIR: true, Vehicle: true
  })

  const [ingestMode, setIngestMode] = useState(false)
  const [newFIR, setNewFIR] = useState({ 
    fir_number: '', 
    filing_date: '2026-08-31', 
    narrative: '', 
    analyst_id: 'Agent_742' 
  })

  const [dimensions, setDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight
  })

  const graphRef = useRef()
  const lastClickRef = useRef({ time: 0, nodeId: null })

  useEffect(() => {
    const handleResize = () => setDimensions({ width: window.innerWidth, height: window.innerHeight })
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const fetchNetworkData = () => {
    fetch('http://localhost:8000/api/network')
      .then((res) => res.json())
      .then((data) => setRawGraphData(data))
      .catch((err) => console.error('Error loading graph:', err))

    fetch('http://localhost:8000/api/analytics/influencers')
      .then((res) => res.json())
      .then((data) => setInfluencers(data))
      .catch((err) => console.error('Error loading influencers:', err))
  }

  useEffect(() => {
    fetchNetworkData()
  }, [])

  // --- OPTIMIZED PHYSICS ENGINE ---
  useEffect(() => {
    if (graphRef.current) {
      // Reduced repulsion to keep the map tighter and easier to navigate
      graphRef.current.d3Force('charge').strength(-250)
      graphRef.current.d3Force('link').distance(90)
    }
  }, [rawGraphData])

  const handleIngestSubmit = (e) => {
    e.preventDefault()
    if (!newFIR.fir_number || !newFIR.narrative) return

    fetch('http://localhost:8000/api/ingest/fir', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newFIR)
    })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        alert(`Ingested successfully! Extracted ${data.extracted.phones.length} phones and ${data.extracted.suspects.length} suspects.`)
        setNewFIR({ fir_number: '', filing_date: '2026-08-31', narrative: '' })
        setIngestMode(false)
        fetchNetworkData() 
      } else {
        alert("Ingestion failed: " + data.detail)
      }
    })
    .catch(err => console.error("Ingest error:", err))
  }

  const filteredData = useMemo(() => {
    if (!rawGraphData.nodes.length) return { nodes: [], links: [] }

    const visibleNodes = rawGraphData.nodes.filter((n) => activeFilters[n.group] !== false)
    const visibleNodeIds = new Set(visibleNodes.map((n) => n.id))

    let visibleLinks = rawGraphData.links.filter((l) => {
      const sourceId = typeof l.source === 'object' ? l.source.id : l.source
      const targetId = typeof l.target === 'object' ? l.target.id : l.target
      return visibleNodeIds.has(sourceId) && visibleNodeIds.has(targetId)
    })

    if (appMode === 'PROPAGATION') {
      visibleLinks = visibleLinks.filter((l) => {
        const sId = typeof l.source === 'object' ? l.source.id : l.source
        const tId = typeof l.target === 'object' ? l.target.id : l.target
        return propagatedNodeIds.has(sId) || propagatedNodeIds.has(tId)
      })
    }

    return { nodes: visibleNodes, links: visibleLinks }
  }, [rawGraphData, activeFilters, appMode, propagatedNodeIds])
  const getNodeTitle = (node) => {
    if (!node || !node.properties) return node.id || ''
    return (
      node.properties.name || node.properties.number || node.properties.account_number ||
      node.properties.plate_number || node.properties.fir_number || node.id
    )
  }

  // --- CAMERA CONTROLS ---
  const handleRecenter = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(800, 60) // Smoothly snaps back to see the whole map
    }
  }

  const handleNodeClick = useCallback((node) => {
    if (!node || !isFinite(node.x) || !isFinite(node.y)) return

    const now = Date.now()
    const last = lastClickRef.current
    const isDoubleClick = (last.nodeId === node.id && now - last.time < 350)
    lastClickRef.current = { time: now, nodeId: node.id }

    if (appMode === 'PROPAGATION') {
      setSelectedNode(node)
      if (isDoubleClick) {
        setPropagatedNodeIds(prev => {
          const next = new Set(prev)
          next.add(node.id)
          return next
        })
      }
      if (graphRef.current) {
        graphRef.current.centerAt(node.x, node.y, 800)
        graphRef.current.zoom(1.8, 800) // Lowered zoom severity
      }
      return
    }

    if (appMode === 'WATCHER') {
      setWatcherTargetId(node.id)
      setSelectedNode(node)
      if (graphRef.current) {
        graphRef.current.centerAt(node.x, node.y, 800)
        graphRef.current.zoom(1.8, 800) // Lowered zoom severity
      }
      return
    }

    if (pathMode) {
      if (pathEndpoints.length === 0 || pathEndpoints.length === 2) {
        setPathEndpoints([node])
        setHighlightedPath([])
      } else if (pathEndpoints.length === 1) {
        const source = pathEndpoints[0]
        const target = node
        setPathEndpoints([source, target])
        
        fetch(`http://localhost:8000/api/network/path?source_id=${encodeURIComponent(source.id)}&target_id=${encodeURIComponent(target.id)}`)
          .then(res => res.json())
          .then(data => {
            if (data.path && data.path.length > 0) {
              setHighlightedPath(data.path)
              handleRecenter() // Auto-recenter to view the whole path
            } else {
              alert("No connecting path found between these entities.")
              setPathEndpoints([])
            }
          })
      }
      return
    }

    setSelectedNode(node)
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 800)
      graphRef.current.zoom(1.8, 800) // Lowered zoom severity
    }
  }, [appMode, pathMode, pathEndpoints])

  const handleSearchChange = (term) => {
    setSearchTerm(term)
    if (!term.trim()) return

    const target = filteredData.nodes.find((n) =>
      getNodeTitle(n).toLowerCase().includes(term.toLowerCase())
    )

    if (target && isFinite(target.x) && isFinite(target.y)) {
      if (!pathMode) setSelectedNode(target)
      if (graphRef.current) {
        graphRef.current.centerAt(target.x, target.y, 800)
        graphRef.current.zoom(1.8, 800) // Lowered zoom severity
      }
    }
  }

  const handleLeaderboardClick = (nodeId) => {
    const target = filteredData.nodes.find((n) => n.id === nodeId)
    if (target && isFinite(target.x) && isFinite(target.y)) {
      setSelectedNode(target)
      if (graphRef.current) {
        graphRef.current.centerAt(target.x, target.y, 800)
        graphRef.current.zoom(1.8, 800) // Lowered zoom severity
      }
    }
  }

  const drawNode = useCallback((node, ctx, globalScale) => {
    if (!isFinite(node.x) || !isFinite(node.y)) return

    const cfg = GROUP_CONFIG[node.group] || { color: '#9ca3af' }
    const isSelected = selectedNode && selectedNode.id === node.id
    const isMatch = searchTerm && getNodeTitle(node).toLowerCase().includes(searchTerm.toLowerCase())
    
    let opacity = 1
    
    // TEMPORAL GHOSTING: Dim nodes created after the timeline slider date
    // Legacy nodes missing audit data default to August 1, 2026
    const rawDate = node.properties?.ingested_at || node.properties?.filing_date || '2026-08-01'
    
    if (rawDate) {
      const nodeTime = new Date(rawDate).getTime()
      if (!isNaN(nodeTime) && nodeTime > currentTimestamp) {
        opacity = 0.05
      }
    }

    if (appMode === 'WATCHER' && watcherTargetId) {
      const isTarget = node.id === watcherTargetId
      const isConnected = rawGraphData.links.some(l => {
        const sId = typeof l.source === 'object' ? l.source.id : l.source
        const tId = typeof l.target === 'object' ? l.target.id : l.target
        return (sId === watcherTargetId && tId === node.id) || (tId === watcherTargetId && sId === node.id)
      })
      opacity = Math.min(opacity, (isTarget || isConnected) ? 1 : 0.1)
    }

    const isPathActive = highlightedPath.length > 0
    const isInPath = highlightedPath.includes(node.id)
    if (isPathActive && !isInPath) opacity = Math.min(opacity, 0.15)

    const radius = node.group === 'Person' ? 8 : 5
    ctx.globalAlpha = opacity

    // ... (Keep the rest of your existing drawing logic for circles and text below this)

    if (isSelected || isMatch || (pathEndpoints.find(n => n.id === node.id))) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI, false)
      ctx.fillStyle = isInPath ? '#34d399' : (isSelected ? '#ffffff' : '#fbbf24')
      ctx.fill()
    }

    ctx.beginPath()
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false)
    ctx.fillStyle = cfg.color
    ctx.fill()
    ctx.lineWidth = 1
    ctx.strokeStyle = '#000000'
    ctx.stroke()

    const isGhosted = opacity <= 0.05
    const shouldDrawLabel = !isGhosted && (
      globalScale > 1.2 || 
      node.group === 'Person' || 
      isSelected || 
      isMatch || 
      isInPath || 
      (appMode === 'WATCHER' && opacity === 1)
    )

    if (shouldDrawLabel) {
      const label = getNodeTitle(node)
      const fontSize = Math.max(11 / globalScale, 3)
      ctx.font = `${fontSize}px sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'

      const textWidth = ctx.measureText(label).width
      ctx.fillStyle = `rgba(0, 0, 0, ${0.75 * opacity})`
      ctx.fillRect(node.x - textWidth / 2 - 2, node.y + radius + 2, textWidth + 4, fontSize + 2)

      ctx.fillStyle = (isSelected || isInPath) ? '#ffffff' : '#e5e7eb'
      ctx.fillText(label, node.x, node.y + radius + 3)
    }
    
    ctx.globalAlpha = 1
  }, [selectedNode, searchTerm, highlightedPath, pathEndpoints, appMode, watcherTargetId, rawGraphData.links, currentTimestamp])

  const toggleFilter = (type) => setActiveFilters((prev) => ({ ...prev, [type]: !prev[type] }))

  const switchMode = (mode) => {
    setAppMode(mode)
    setSelectedNode(null)
    setPathMode(false)
    if (mode === 'PROPAGATION') setPropagatedNodeIds(new Set())
    if (mode !== 'WATCHER') setWatcherTargetId(null)
    handleRecenter()
  }

  const togglePathMode = () => {
    setPathMode(!pathMode)
    setIngestMode(false)
    setPathEndpoints([])
    setHighlightedPath([])
    setSelectedNode(null)
  }

  const toggleIngestMode = () => {
    setIngestMode(!ingestMode)
    setPathMode(false)
  }

  return (
    <div style={{ position: 'relative', width: '100vw', height: '100vh', overflow: 'hidden' }}>
      
      <ForceGraph2D
        ref={graphRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={filteredData}
        nodeCanvasObject={drawNode}
        // These two props add massive friction to stop the graph from floating away
        d3AlphaDecay={0.05}
        d3VelocityDecay={0.4}
        nodePointerAreaPaint={(node, color, ctx) => {
          ctx.fillStyle = color
          ctx.beginPath()
          ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI, false)
          ctx.fill()
        }}
        
        linkColor={(link) => {
          const sId = typeof link.source === 'object' ? link.source.id : link.source
          const tId = typeof link.target === 'object' ? link.target.id : link.target

          // TEMPORAL GHOSTING: Apply the fallback date to legacy links
          const linkRawDate = link.properties?.timestamp || link.properties?.ingested_at || '2026-08-01'
          const linkTime = new Date(linkRawDate.split(' ')[0]).getTime()
          
          if (!isNaN(linkTime) && linkTime > currentTimestamp) {
            return 'rgba(255, 255, 255, 0.01)' // Drops opacity to make them practically invisible
          }

          if (appMode === 'WATCHER' && watcherTargetId) {
            const isConnectedToWatcher = sId === watcherTargetId || tId === watcherTargetId
            return isConnectedToWatcher ? '#34d399' : 'rgba(255, 255, 255, 0.02)'
          }

          if (highlightedPath.length === 0) return 'rgba(255, 255, 255, 0.15)'
          return (highlightedPath.includes(sId) && highlightedPath.includes(tId)) ? '#34d399' : 'rgba(255, 255, 255, 0.05)'
        }}


        linkWidth={(link) => {
          const sId = typeof link.source === 'object' ? link.source.id : link.source
          const tId = typeof link.target === 'object' ? link.target.id : link.target

          if (appMode === 'WATCHER' && watcherTargetId) {
            return (sId === watcherTargetId || tId === watcherTargetId) ? 3 : 1
          }

          if (highlightedPath.length === 0) return 1
          return (highlightedPath.includes(sId) && highlightedPath.includes(tId)) ? 3 : 1
        }}
        onNodeClick={handleNodeClick}
        minZoom={0.2}
        maxZoom={8}
      />

      {/* MODE SELECTOR TOP BAR */}
      <div style={{ position: 'absolute', top: 16, left: '50%', transform: 'translateX(-50%)', backgroundColor: 'rgba(17, 24, 39, 0.95)', border: '1px solid #374151', borderRadius: '8px', padding: '6px', display: 'flex', gap: '6px', zIndex: 10, backdropFilter: 'blur(4px)' }}>
        <button onClick={() => switchMode('NORMAL')} style={{ padding: '6px 12px', backgroundColor: appMode === 'NORMAL' ? '#2563eb' : '#1f2937', border: 'none', borderRadius: '4px', color: '#fff', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer' }}>
          🌐 Normal View
        </button>
        <button onClick={() => switchMode('PROPAGATION')} style={{ padding: '6px 12px', backgroundColor: appMode === 'PROPAGATION' ? '#059669' : '#1f2937', border: 'none', borderRadius: '4px', color: '#fff', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer' }}>
          ⚡ Map Propagation
        </button>
        <button onClick={() => switchMode('WATCHER')} style={{ padding: '6px 12px', backgroundColor: appMode === 'WATCHER' ? '#d97706' : '#1f2937', border: 'none', borderRadius: '4px', color: '#fff', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer' }}>
          👁️ Path Watcher
        </button>
        
        {/* NEW: RECENTER MAP BUTTON */}
        <div style={{ width: '1px', backgroundColor: '#4b5563', margin: '0 4px' }} />
        <button onClick={handleRecenter} style={{ padding: '6px 12px', backgroundColor: '#374151', border: '1px solid #4b5563', borderRadius: '4px', color: '#fff', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer', transition: 'background 0.2s' }}>
          🎯 Recenter Map
        </button>
      </div>

      {/* PROPAGATION RESET BUTTON (Appears only in Propagation Mode) */}
      {appMode === 'PROPAGATION' && (
        <div style={{ position: 'absolute', top: 70, left: '50%', transform: 'translateX(-50%)', zIndex: 10 }}>
          <button onClick={() => setPropagatedNodeIds(new Set())} style={{ padding: '6px 12px', backgroundColor: '#dc2626', border: 'none', borderRadius: '4px', color: '#fff', fontSize: '0.7rem', fontWeight: 'bold', cursor: 'pointer', boxShadow: '0 2px 10px rgba(0,0,0,0.4)' }}>
            🔄 Revert All Connections
          </button>
        </div>
      )}

      {/* TIMELINE SLIDER (BOTTOM CENTER) */}
      <div style={{ position: 'absolute', bottom: 24, left: '50%', transform: 'translateX(-50%)', width: '500px', backgroundColor: 'rgba(17, 24, 39, 0.95)', border: '1px solid #374151', borderRadius: '8px', padding: '16px', zIndex: 10, backdropFilter: 'blur(4px)', boxShadow: '0 4px 20px rgba(0,0,0,0.5)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#9ca3af', textTransform: 'uppercase' }}>Timeline Scrubbing</span>
          <span style={{ fontSize: '0.85rem', fontWeight: 'bold', color: '#34d399' }}>
            {new Date(currentTimestamp).toLocaleDateString('default', { month: 'long', day: 'numeric', year: 'numeric' })}
          </span>
        </div>
        <input 
          type="range" 
          min={MIN_TIMESTAMP} 
          max={MAX_TIMESTAMP} 
          step={86400000} 
          value={currentTimestamp} 
          onChange={(e) => setCurrentTimestamp(parseInt(e.target.value))}
          style={{ width: '100%', cursor: 'pointer', accentColor: '#34d399' }}
        />
      </div>

      {/* LEFT SIDEBAR (Controls & Analytics) */}
      <div style={{ position: 'absolute', top: 16, left: 16, width: '320px', maxHeight: 'calc(100vh - 120px)', backgroundColor: 'rgba(17, 24, 39, 0.95)', border: '1px solid #374151', borderRadius: '8px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px', zIndex: 10, backdropFilter: 'blur(4px)', boxShadow: '0 4px 20px rgba(0,0,0,0.5)', overflowY: 'auto'}}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 'bold', margin: '0 0 2px 0', color: '#fff' }}>NET-WEAVER OSINT</h2>
          <p style={{ fontSize: '0.72rem', color: '#9ca3af', margin: 0 }}>Criminal Syndicate Relationship Mapping</p>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={togglePathMode} style={{ flex: 1, padding: '10px', backgroundColor: pathMode ? '#065f46' : '#1f2937', border: `1px solid ${pathMode ? '#10b981' : '#4b5563'}`, borderRadius: '4px', color: '#fff', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer' }}>
            {pathMode ? '🛑 Cancel' : '📍 Pathfinding'}
          </button>
          <button onClick={toggleIngestMode} style={{ flex: 1, padding: '10px', backgroundColor: ingestMode ? '#7f1d1d' : '#1f2937', border: `1px solid ${ingestMode ? '#ef4444' : '#4b5563'}`, borderRadius: '4px', color: '#fff', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer' }}>
            {ingestMode ? '🛑 Cancel' : '➕ Add Intel'}
          </button>
        </div>

        {/* Ingest Form */}
        {ingestMode && (
          <form onSubmit={handleIngestSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '8px', backgroundColor: '#111827', padding: '10px', borderRadius: '4px', border: '1px solid #374151' }}>
              {/* NEW ANALYST ID FIELD */}
              <input type="text" placeholder="Analyst ID (e.g. Agent_742)" value={newFIR.analyst_id} onChange={e => setNewFIR({...newFIR, analyst_id: e.target.value})} style={{ padding: '6px', backgroundColor: '#1f2937', border: '1px solid #4b5563', color: '#fff', fontSize: '0.75rem' }} required />
              
              <input type="text" placeholder="FIR Number (e.g. FIR-2026-001)" value={newFIR.fir_number} onChange={e => setNewFIR({...newFIR, fir_number: e.target.value})} style={{ padding: '6px', backgroundColor: '#1f2937', border: '1px solid #4b5563', color: '#fff', fontSize: '0.75rem' }} required />

              <input type="date" value={newFIR.filing_date} onChange={e => setNewFIR({...newFIR, filing_date: e.target.value})} style={{ padding: '6px', backgroundColor: '#1f2937', border: '1px solid #4b5563', color: '#fff', fontSize: '0.75rem' }} required />

              <textarea placeholder="Paste police report narrative here..." value={newFIR.narrative} onChange={e => setNewFIR({...newFIR, narrative: e.target.value})} style={{ padding: '6px', backgroundColor: '#1f2937', border: '1px solid #4b5563', color: '#fff', fontSize: '0.75rem', height: '80px', resize: 'none' }} required />

              <button type="submit" style={{ padding: '8px', backgroundColor: '#dc2626', color: '#fff', border: 'none', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer' }}>Process & Ingest</button>
          </form>
        )}

        {/* Pathfinding Instructions */}
        {pathMode && (
          <div style={{ backgroundColor: '#111827', padding: '10px', borderRadius: '4px', border: '1px dashed #34d399', fontSize: '0.75rem', color: '#a7f3d0' }}>
            {pathEndpoints.length === 0 && "1. Click the Source entity on the graph."}
            {pathEndpoints.length === 1 && "2. Click the Target entity to compute path."}
            {pathEndpoints.length === 2 && "Path found. Click any node to reset."}
          </div>
        )}

        {/* Search */}
        {!pathMode && !ingestMode && (
          <input type="text" placeholder="Search name, phone, account..." value={searchTerm} onChange={(e) => handleSearchChange(e.target.value)} style={{ width: '100%', padding: '8px 10px', backgroundColor: '#1f2937', border: '1px solid #4b5563', borderRadius: '4px', color: '#fff', fontSize: '0.78rem', outline: 'none' }} />
        )}

        {/* Filters */}
        <div>
          <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', color: '#9ca3af', fontWeight: 'bold', margin: '8px 0 6px' }}>Entity Filters</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {Object.entries(GROUP_CONFIG).map(([type, cfg]) => {
              const active = activeFilters[type] !== false
              return (
                <button key={type} onClick={() => toggleFilter(type)} style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '0.72rem', border: '1px solid', borderColor: active ? cfg.color : '#374151', backgroundColor: active ? 'rgba(55, 65, 81, 0.8)' : '#111827', color: active ? '#fff' : '#6b7280', cursor: 'pointer' }}>
                  ● {cfg.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Leaderboard */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px'}}>
          <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', color: '#9ca3af', fontWeight: 'bold' }}>Key Influencers</div>
          {influencers.map((inf, idx) => (
            <div 
              key={idx} 
              onClick={() => handleLeaderboardClick(inf.id)}
              style={{ 
                backgroundColor: '#1f2937', padding: '8px 10px', borderRadius: '4px', 
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
                border: idx === 0 ? '1px solid #ef4444' : '1px solid transparent',
                cursor: 'pointer'
              }}
            >
              <div>
                <div style={{ fontSize: '0.78rem', fontWeight: 'bold', color: idx === 0 ? '#f87171' : '#f3f4f6' }}>{inf.name} {idx === 0 && '👑'}</div>
                <div style={{ fontSize: '0.65rem', color: '#9ca3af' }}>Rank #{idx + 1}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.78rem', fontWeight: 'bold', color: '#34d399' }}>{inf.centrality_score}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* RIGHT INSPECTOR DRAWER (Entity Details) */}
      {!pathMode && selectedNode && (
        <div style={{ position: 'absolute', top: 16, right: 16, width: '320px', maxHeight: 'calc(100vh - 120px)', backgroundColor: 'rgba(17, 24, 39, 0.95)', border: '1px solid #374151', borderRadius: '8px', padding: '16px', zIndex: 10, display: 'flex', flexDirection: 'column', gap: '10px', backdropFilter: 'blur(4px)', boxShadow: '0 4px 20px rgba(0,0,0,0.5)', overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.68rem', fontWeight: 'bold', color: GROUP_CONFIG[selectedNode.group]?.color || '#fff' }}>{selectedNode.group?.toUpperCase()} ENTITY</span>
            <button onClick={() => setSelectedNode(null)} style={{ background: 'none', border: 'none', color: '#9ca3af', fontSize: '1rem', cursor: 'pointer' }}>✕</button>
          </div>
          <h3 style={{ fontSize: '1rem', fontWeight: 'bold', margin: 0, color: '#fff' }}>{getNodeTitle(selectedNode)}</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.75rem' }}>
            {Object.entries(selectedNode.properties || {}).map(([key, value]) => {
              
              // Intercept the UTC timestamp and format it to local time
              let displayValue = String(value)
              if (key === 'ingested_at') {
                displayValue = new Date(value).toLocaleString()
              }

              return (
                <div key={key} style={{ backgroundColor: '#1f2937', padding: '6px 8px', borderRadius: '4px' }}>
                  <span style={{ color: '#9ca3af', textTransform: 'capitalize' }}>{key.replace('_', ' ')}: </span>
                  <span style={{ color: '#fff', fontWeight: '500', wordBreak: 'break-word' }}>{displayValue}</span>
                </div>
              )
            })}
          </div>

          {selectedNode.group === 'FIR' && (
            <div style={{ marginTop: '8px', fontSize: '0.72rem' }}>
              <div style={{ color: '#f59e0b', fontWeight: 'bold', marginBottom: '4px' }}>Case Narrative:</div>
              <div style={{ backgroundColor: '#1f2937', padding: '8px', borderRadius: '4px', lineHeight: '1.4', color: '#d1d5db' }}>{selectedNode.properties.narrative}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}