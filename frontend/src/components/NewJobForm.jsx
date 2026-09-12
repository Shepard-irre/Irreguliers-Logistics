import { useEffect, useMemo, useState } from 'react'
import {
  getRaffineriesReferenceData,
  estimateRaffineriesJob,
  createRaffineriesJob,
  analyzeScreenshot,
} from '../lib/api'

function methodCode(methodName) {
  return methodName.toLowerCase().replace(/ /g, '_')
}

const NAME_SUFFIXES = [' (Raw)', '(Raw)', ' (Ore)', '(Ore)', ' (Brut)', '(Brut)', ' (Mined)', '(Mined)']

function stripSuffix(name) {
  let cleaned = name || ''
  for (const suffix of NAME_SUFFIXES) {
    cleaned = cleaned.replace(suffix, '')
  }
  return cleaned.trim()
}

function matchCommodity(commodities, rawName) {
  const cleaned = stripSuffix(rawName).toLowerCase()
  if (!cleaned) return null
  return (
    commodities.find(
      (c) => cleaned.includes(c.name.toLowerCase()) || c.name.toLowerCase().includes(cleaned),
    ) || null
  )
}

function clampQuality(value) {
  const n = value ? parseInt(value, 10) : 500
  return Math.max(1, Math.min(1000, n || 500))
}

let nextLineId = 1

export default function NewJobForm({ onCreated, onClose }) {
  const [refData, setRefData] = useState(null)
  const [loadError, setLoadError] = useState(null)

  const [sessionId, setSessionId] = useState('')
  const [terminalId, setTerminalId] = useState('')
  const [methodName, setMethodName] = useState('')

  const [lineCommodityId, setLineCommodityId] = useState('')
  const [lineQtyCscu, setLineQtyCscu] = useState(10000)
  const [lineQuality, setLineQuality] = useState(500)
  const [lines, setLines] = useState([])

  const [estimates, setEstimates] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const [screenshotFile, setScreenshotFile] = useState(null)
  const [screenshotInputKey, setScreenshotInputKey] = useState(0)
  const [visionBusy, setVisionBusy] = useState(false)
  const [visionOrders, setVisionOrders] = useState(null)
  const [screenshotWarning, setScreenshotWarning] = useState(null)
  const [selectedOrderIdx, setSelectedOrderIdx] = useState(0)

  useEffect(() => {
    getRaffineriesReferenceData()
      .then(setRefData)
      .catch((e) => setLoadError(e.message))
  }, [])

  const selectedSession = useMemo(
    () => refData?.sessions.find((s) => String(s.id) === sessionId),
    [refData, sessionId],
  )

  const terminals = useMemo(() => {
    if (!refData) return []
    if (!selectedSession) return refData.terminals
    const filtered = refData.terminals.filter((t) => t.star_system_name === selectedSession.star_system)
    return filtered.length ? filtered : refData.terminals
  }, [refData, selectedSession])

  useEffect(() => {
    if (!refData) return
    const stillValid = terminalId && terminals.some((t) => String(t.id) === terminalId)
    if (!stillValid && terminals.length) setTerminalId(String(terminals[0].id))
    if (!methodName && refData.methods.length) setMethodName(refData.methods[0].name)
    if (!lineCommodityId && refData.commodities.length) setLineCommodityId(String(refData.commodities[0].id))
  }, [refData, terminals, terminalId, methodName, lineCommodityId])

  function handleAddLine() {
    if (!sessionId) {
      setError('Sélectionne une session de minage avant d\'ajouter un lot.')
      return
    }
    const commodity = refData.commodities.find((c) => String(c.id) === lineCommodityId)
    if (!commodity) return
    if (Number(lineQtyCscu) < 100) {
      setError("Quantité minimum : 100 cSCU (1 SCU) — l'unité de raffinage la plus petite.")
      return
    }
    setError(null)
    setLines((prev) => [
      ...prev,
      {
        lineId: nextLineId++,
        commodityId: lineCommodityId,
        commodityName: commodity.name,
        quantityCscu: Number(lineQtyCscu),
        quality: Number(lineQuality),
      },
    ])
    setEstimates(null)
  }

  function updateLine(lineId, patch) {
    setLines((prev) => prev.map((l) => (l.lineId === lineId ? { ...l, ...patch } : l)))
    setEstimates(null)
  }

  function removeLine(lineId) {
    setLines((prev) => prev.filter((l) => l.lineId !== lineId))
    setEstimates(null)
  }

  function autoSelectTerminal(guess) {
    if (!guess) return
    const words = guess.toLowerCase().split(/\s+/).filter((w) => w.length >= 3)
    if (!words.length) return
    let best = null
    let bestScore = 0
    for (const t of terminals) {
      const label = `${t.name} ${t.star_system_name || ''}`.toLowerCase()
      const score = words.filter((w) => label.includes(w)).length
      if (score > bestScore) {
        best = t
        bestScore = score
      }
    }
    if (best && bestScore >= Math.max(1, Math.floor(words.length / 2))) {
      setTerminalId(String(best.id))
    }
  }

  function autoSelectMethod(guess) {
    if (!guess || !refData) return
    const g = guess.toLowerCase()
    const match = refData.methods.find((m) => g.includes(m.name.toLowerCase()) || m.name.toLowerCase().includes(g))
    if (match) setMethodName(match.name)
  }

  function buildImportedLine(commodity, quantityCscu, quality, knownOutputScu) {
    return {
      lineId: nextLineId++,
      commodityId: String(commodity.id),
      commodityName: commodity.name,
      quantityCscu,
      quality: clampQuality(quality),
      knownOutputScu,
    }
  }

  // TYPE A never exposes the true raw ore quantity — only RENDEM (the total
  // refined output, already known). quantityCscu is a placeholder derived
  // from that known output so the line has *some* input value to display.
  function importTypeALines(linesData) {
    const imported = []
    const unmatched = []
    for (const line of linesData) {
      const commodity = matchCommodity(refData.commodities, line.commodity_name)
      if (!commodity) {
        unmatched.push(line.commodity_name)
        continue
      }
      const outputScu = line.quantity_refined ? Number(line.quantity_refined) / 100 : null
      const quantityCscu = outputScu ? Math.round(outputScu * 100) : 1
      imported.push(buildImportedLine(commodity, quantityCscu, line.quality, outputScu))
    }
    return { imported, unmatched }
  }

  // TYPE B exposes the real raw quantity (QTE) directly, plus RENDEM only
  // when the "AFFINER" indicator is lit (quantity_refined truthy).
  function importTypeBLines(linesData) {
    const imported = []
    const unmatched = []
    for (const line of linesData) {
      if (line.active === false) continue
      const name = line.name || line.commodity_name
      const commodity = matchCommodity(refData.commodities, name)
      const qtyRaw = line.quantity_raw
      if (!commodity || !qtyRaw) {
        unmatched.push(name)
        continue
      }
      const outputScu = line.quantity_refined ? Number(line.quantity_refined) / 100 : null
      imported.push(buildImportedLine(commodity, Number(qtyRaw), line.quality, outputScu))
    }
    return { imported, unmatched }
  }

  function handleImportOrder(order) {
    const { imported, unmatched } = importTypeALines(order.lines || [])
    setLines((prev) => [...prev, ...imported])
    setEstimates(null)
    if (unmatched.length) {
      setError(`Minerai non reconnu : ${unmatched.join(', ')} — ajoute-le manuellement.`)
    } else {
      setError(null)
    }
    const remaining = visionOrders.filter((o) => o.orderNum !== order.orderNum)
    setVisionOrders(remaining.length ? remaining : null)
    setSelectedOrderIdx(0)
  }

  function handleImportAllOrders() {
    let allImported = []
    let allUnmatched = []
    for (const order of visionOrders) {
      const { imported, unmatched } = importTypeALines(order.lines || [])
      allImported = allImported.concat(imported)
      allUnmatched = allUnmatched.concat(unmatched)
    }
    setLines((prev) => [...prev, ...allImported])
    setEstimates(null)
    setError(allUnmatched.length ? `Minerai non reconnu : ${allUnmatched.join(', ')} — ajoute-le manuellement.` : null)
    setVisionOrders(null)
  }

  async function handleAnalyzeScreenshot() {
    if (!screenshotFile) return
    if (!sessionId) {
      setError('Sélectionne une session de minage avant d\'analyser un screenshot.')
      return
    }
    setVisionBusy(true)
    setError(null)
    setScreenshotWarning(null)
    try {
      const result = await analyzeScreenshot(screenshotFile, sessionId)
      if (result.error) {
        setError(result.error)
        return
      }

      if (result.duplicate_screenshot) {
        setScreenshotWarning(
          `Tu as déjà utilisé "${screenshotFile.name}" durant cette session — les lots seront quand même importés, vérifie qu'il ne s'agit pas d'un doublon.`
        )
      }

      // Clear the file input so re-selecting the exact same file (common when testing
      // or re-importing on purpose) fires a fresh change event next time.
      setScreenshotFile(null)
      setScreenshotInputKey((k) => k + 1)

      if (result.terminal_name) autoSelectTerminal(result.terminal_name)
      if (result.method) autoSelectMethod(result.method)

      if (result.orders) {
        const orderEntries = result.orders
          .filter((o) => o.screen_type === 'A')
          .map((o, i) => ({
            orderNum: i + 1,
            processingTimeMinutes: o.processing_time_minutes,
            lines: o.lines || [],
          }))
        setVisionOrders(orderEntries.length ? orderEntries : null)
      } else if (result.screen_type === 'A' && result.lines) {
        setVisionOrders([{ orderNum: 1, processingTimeMinutes: result.processing_time_minutes, lines: result.lines }])
      } else if (result.screen_type === 'B' && result.lines) {
        const { imported, unmatched } = importTypeBLines(result.lines)
        setLines((prev) => [...prev, ...imported])
        setEstimates(null)
        if (unmatched.length) {
          setError(`Minerai non reconnu : ${unmatched.join(', ')} — ajoute-le manuellement.`)
        }
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setVisionBusy(false)
    }
  }

  async function handleEstimateAll() {
    setBusy(true)
    setError(null)
    try {
      const results = []
      for (const line of lines) {
        const quantity = Math.max(1, Math.floor(line.quantityCscu / 100))
        if (line.knownOutputScu != null) {
          // Already known from a Vision import (RENDEM) — no need to estimate.
          results.push({
            ...line,
            quantity,
            estimated_output: line.knownOutputScu,
            yield_pct: quantity ? Math.round((line.knownOutputScu / quantity) * 1000) / 10 : null,
            confidence: '🎮 Valeur du jeu',
            audit_count: 0,
            correctedCscu: Math.round(line.knownOutputScu * 100),
            saved: false,
          })
          continue
        }
        const result = await estimateRaffineriesJob({
          commodity_id: Number(line.commodityId),
          terminal_id: Number(terminalId),
          method_code: methodCode(methodName),
          quantity,
        })
        results.push({
          ...line,
          quantity,
          ...result,
          correctedCscu: result.estimated_output * 100,
          saved: false,
        })
      }
      setEstimates(results)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function saveEstimate(est) {
    const terminal = terminals.find((t) => String(t.id) === terminalId)
    await createRaffineriesJob({
      commodity_id: Number(est.commodityId),
      commodity_name: est.commodityName,
      terminal_id: Number(terminalId),
      terminal_name: `${terminal.name} (${terminal.star_system_name || '?'})`,
      method: methodCode(methodName),
      quantity_raw: est.quantity,
      quantity_estimated: est.correctedCscu / 100,
      yield_rate: est.yield_pct,
      confidence: est.confidence,
      audit_count: est.audit_count,
      quality: Number(est.quality),
      session_id: selectedSession ? selectedSession.id : null,
    })
  }

  async function handleSaveOne(lineId) {
    setBusy(true)
    setError(null)
    try {
      const est = estimates.find((e) => e.lineId === lineId)
      await saveEstimate(est)
      setEstimates((prev) => prev.map((e) => (e.lineId === lineId ? { ...e, saved: true } : e)))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleSaveAllRemaining() {
    setBusy(true)
    setError(null)
    try {
      for (const est of estimates) {
        if (!est.saved) await saveEstimate(est)
      }
      onCreated()
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  function updateEstimateField(lineId, patch) {
    setEstimates((prev) => prev.map((e) => (e.lineId === lineId ? { ...e, ...patch } : e)))
  }

  if (loadError) {
    return (
      <div className="cut bg-irr-panel border border-irr-border p-6 text-red-400 text-sm">
        {loadError}
      </div>
    )
  }

  if (!refData) {
    return (
      <div className="cut bg-irr-panel border border-irr-border p-6 text-irr-dim text-sm">
        Chargement des données UEX…
      </div>
    )
  }

  const allSaved = estimates && estimates.every((e) => e.saved)

  return (
    <div className="cut bg-irr-panel border border-irr-border p-6 flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <span className="font-display font-bold text-lg tracking-wide">Nouveau job de raffinage</span>
        <button onClick={onClose} className="text-irr-dim hover:text-irr-text text-xs font-display font-semibold">
          Fermer
        </button>
      </div>

      <label className="flex flex-col gap-1">
        <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
          Session de minage
        </span>
        <select
          value={sessionId}
          onChange={(e) => setSessionId(e.target.value)}
          className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
        >
          <option value="">-- Sélectionner une session --</option>
          {refData.sessions.map((s) => (
            <option key={s.id} value={s.id}>
              {s.numero} — {s.star_system}
            </option>
          ))}
        </select>
      </label>

      {!sessionId && (
        <div className="text-amber-400 text-xs">
          Sélectionne une session de minage avant de pouvoir ajouter des lots ou analyser un screenshot.
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
            Station de raffinage
          </span>
          <select
            value={terminalId}
            onChange={(e) => { setTerminalId(e.target.value); setEstimates(null) }}
            className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
          >
            {terminals.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.star_system_name || '?'})
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
            Méthode
          </span>
          <select
            value={methodName}
            onChange={(e) => { setMethodName(e.target.value); setEstimates(null) }}
            className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
          >
            {refData.methods.map((m) => (
              <option key={m.name} value={m.name}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex flex-col gap-2 border-t border-irr-border pt-4">
        <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
          Importer depuis un screenshot in-game
        </span>
        <div className="flex gap-3 items-center">
          <label className="flex-1">
            <span className="sr-only">Screenshot raffinerie</span>
            <input
              key={screenshotInputKey}
              type="file"
              accept="image/png,image/jpeg,image/jpg"
              aria-label="Screenshot raffinerie"
              onChange={(e) => setScreenshotFile(e.target.files?.[0] || null)}
              className="text-xs text-irr-muted file:cut-sm file:mr-3 file:border file:border-irr-border-strong file:bg-irr-panel-alt file:text-irr-text file:text-xs file:font-display file:font-semibold file:px-3 file:py-1.5"
            />
          </label>
          <button
            type="button"
            disabled={!screenshotFile || visionBusy || !sessionId}
            onClick={handleAnalyzeScreenshot}
            className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent font-display font-semibold text-xs tracking-wide px-4 py-2 disabled:opacity-50 shrink-0"
          >
            {visionBusy ? 'Analyse…' : 'Analyser le screenshot'}
          </button>
        </div>

        {visionOrders && (
          <div className="flex flex-col gap-2 mt-1">
            <span className="text-xs text-irr-muted">
              {visionOrders.length} ordre(s) détecté(s) — lequel importer ?
            </span>
            <div className="flex flex-col gap-1.5">
              {visionOrders.map((order, i) => {
                const minerals = [...new Set((order.lines || []).map((l) => l.commodity_name))].join(', ')
                return (
                  <label key={order.orderNum} className="flex items-center gap-2 text-xs">
                    <input
                      type="radio"
                      name="vision-order"
                      checked={selectedOrderIdx === i}
                      onChange={() => setSelectedOrderIdx(i)}
                    />
                    Ordre {order.orderNum} ({minerals})
                  </label>
                )
              })}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => handleImportOrder(visionOrders[selectedOrderIdx])}
                className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent font-display font-semibold text-xs tracking-wide px-4 py-1.5"
              >
                Importer cet ordre
              </button>
              <button
                type="button"
                onClick={handleImportAllOrders}
                className="cut-sm border border-irr-border-strong text-irr-muted font-display font-semibold text-xs tracking-wide px-4 py-1.5"
              >
                Tout importer
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-2 border-t border-irr-border pt-4">
        <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
          Ajouter un lot à raffiner
        </span>
        <div className="grid grid-cols-4 gap-3 items-end">
          <label className="flex flex-col gap-1 col-span-2">
            <span className="text-[9.5px] text-irr-dim">Minerai brut</span>
            <select
              value={lineCommodityId}
              onChange={(e) => setLineCommodityId(e.target.value)}
              className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
            >
              {refData.commodities.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[9.5px] text-irr-dim">Quantité (cSCU)</span>
            <input
              type="number"
              min="100"
              step="100"
              value={lineQtyCscu}
              onChange={(e) => setLineQtyCscu(e.target.value)}
              className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 font-mono text-sm text-irr-text focus:outline-none focus:border-irr-accent"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[9.5px] text-irr-dim">Qualité</span>
            <input
              type="number"
              min="1"
              max="1000"
              value={lineQuality}
              onChange={(e) => setLineQuality(e.target.value)}
              className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 font-mono text-sm text-irr-text focus:outline-none focus:border-irr-accent"
            />
          </label>
        </div>
        <button
          type="button"
          disabled={!sessionId}
          onClick={handleAddLine}
          className="cut-sm self-start bg-irr-accent-dim border border-irr-accent text-irr-accent font-display font-semibold text-xs tracking-wide px-4 py-1.5 disabled:opacity-50"
        >
          + Ajouter
        </button>
      </div>

      {lines.length > 0 && !estimates && (
        <div className="flex flex-col gap-2 border-t border-irr-border pt-4">
          <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
            Lots à raffiner
          </span>
          {lines.map((line) => (
            <div key={line.lineId} className="flex items-center gap-3 bg-irr-panel-alt border border-irr-border px-3 py-2 text-sm">
              <span className="flex-1 font-display font-semibold">{line.commodityName}</span>
              <input
                type="number"
                min="100"
                step="100"
                value={line.quantityCscu}
                onChange={(e) => updateLine(line.lineId, { quantityCscu: Number(e.target.value) })}
                className="bg-irr-panel border border-irr-border-strong px-2 py-1 font-mono text-xs text-irr-text w-24 focus:outline-none focus:border-irr-accent"
              />
              <input
                type="number"
                min="1"
                max="1000"
                value={line.quality}
                onChange={(e) => updateLine(line.lineId, { quality: Number(e.target.value) })}
                className="bg-irr-panel border border-irr-border-strong px-2 py-1 font-mono text-xs text-irr-text w-20 focus:outline-none focus:border-irr-accent"
              />
              <button
                onClick={() => removeLine(line.lineId)}
                className="text-irr-dim hover:text-red-400 text-xs"
              >
                Retirer
              </button>
            </div>
          ))}

          <button
            type="button"
            disabled={busy}
            onClick={handleEstimateAll}
            className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent font-display font-semibold text-sm tracking-wide py-2.5 disabled:opacity-50 mt-2"
          >
            Calculer l'estimation pour tous les lots
          </button>
        </div>
      )}

      {estimates && (
        <div className="flex flex-col gap-3 border-t border-irr-border pt-4">
          <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
            Résultats de l'estimation
          </span>
          {estimates.map((est) => (
            <div key={est.lineId} className="bg-irr-panel-alt border border-irr-border p-3 flex flex-col gap-2">
              <div className="flex justify-between items-center">
                <span className="font-display font-semibold text-sm">{est.commodityName}</span>
                <span className="text-xs text-irr-muted">
                  {est.confidence} ({est.audit_count} audits) — rendement {est.yield_pct}%
                </span>
              </div>
              <div className="flex items-center gap-3">
                <label className="flex flex-col gap-1 flex-1">
                  <span className="text-[9.5px] text-irr-dim">Corriger cSCU raffiné</span>
                  <input
                    type="number"
                    min="0"
                    step="50"
                    disabled={est.saved}
                    value={est.correctedCscu}
                    onChange={(e) => updateEstimateField(est.lineId, { correctedCscu: Number(e.target.value) })}
                    className="bg-irr-panel border border-irr-border-strong px-2 py-1.5 font-mono text-sm text-irr-text focus:outline-none focus:border-irr-accent disabled:opacity-50"
                  />
                </label>
                {est.saved ? (
                  <span className="text-irr-green text-xs font-display font-semibold">✓ Enregistré</span>
                ) : (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => handleSaveOne(est.lineId)}
                    className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent font-display font-semibold text-xs tracking-wide px-4 py-2 disabled:opacity-50"
                  >
                    Enregistrer ce lot
                  </button>
                )}
              </div>
            </div>
          ))}

          {!allSaved && (
            <button
              type="button"
              disabled={busy}
              onClick={handleSaveAllRemaining}
              className="cut-sm border border-irr-accent text-irr-accent font-display font-semibold text-sm tracking-wide py-2.5 disabled:opacity-50"
            >
              Enregistrer tous les lots restants
            </button>
          )}
        </div>
      )}

      {screenshotWarning && <div className="text-amber-400 text-xs">{screenshotWarning}</div>}
      {error && <div className="text-red-400 text-xs">{error}</div>}
    </div>
  )
}
