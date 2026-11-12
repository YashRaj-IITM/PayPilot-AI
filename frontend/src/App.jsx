import { useCallback, useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Activity, ArrowUpRight, BarChart3, Bell,
  CheckCircle2, ChevronDown, CircleDollarSign, Clock3,
  CreditCard, FileText, LayoutDashboard, Loader2,
  Package, Plus, RefreshCw, Search, ShieldCheck, Sparkles,
  Truck, Wallet, X, Zap
} from 'lucide-react'
import './App.css'

const API = 'http://127.0.0.1:5000/api'

const money = (value, currency = 'USD') =>
  new Intl.NumberFormat('en-US', {
    style: 'currency', currency, maximumFractionDigits: 2
  }).format(Number(value || 0))

function App() {
  const [procurements, setProcurements] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [payments, setPayments] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [search, setSearch] = useState('')
  const [activeNav, setActiveNav] = useState('Overview')
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    title: '', description: '', budget_amount: '', currency: 'USD'
  })

  const selected = procurements.find(p => p.id === selectedId) || procurements[0] || null
  const quotes = selected?.quotes || []

  const totalSpend = useMemo(() =>
    payments.filter(p => p.status === 'COMPLETED')
      .reduce((sum, p) => sum + Number(p.amount || 0), 0),
  [payments])

  const completedCount = payments.filter(p => p.status === 'COMPLETED').length
  const filtered = procurements.filter(p =>
    `${p.title} ${p.description}`.toLowerCase().includes(search.toLowerCase())
  )

  const request = useCallback(async (path, options = {}) => {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok || data.success === false) {
      throw new Error(data.error || `Request failed (${response.status})`)
    }

    return data
  }, [])

  const loadData = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true)

    try {
      const data = await request('/procurements')
      const list = data.procurements || []

      setProcurements(list)

      if (list.length && !list.some(p => p.id === selectedId)) {
        setSelectedId(list[0].id)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [request, selectedId])

  const loadPayments = useCallback(async (id) => {
    if (!id) return

    try {
      const data = await request(`/procurements/${id}/payments`)
      setPayments(data.payments || data.transactions || [])
    } catch {
      setPayments([])
    }
  }, [request])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    if (selectedId) loadPayments(selectedId)
  }, [selectedId, loadPayments])

  async function runAnalysis() {
    if (!selected) return
    setBusy('analysis')
    setError('')
    setNotice('')
    try {
      const data = await request(`/procurements/${selected.id}/analyze`, {
        method: 'POST', body: JSON.stringify({})
      })
      setAnalysis(data)
      setNotice('AI procurement analysis completed.')
      await loadData()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  async function approveQuote(quote) {
    if (!selected) return
    if (!window.confirm(`Approve ${quote.supplier_name} for ${money(quote.total_price, selected.currency)}?`)) return
    setBusy('approval')
    setError('')
    setNotice('')
    try {
      const data = await request(`/procurements/${selected.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ quote_id: quote.id })
      })
      setNotice(`Approval recorded. Transaction #${data.transaction_id} created.`)
      await loadData()
      await loadPayments(selected.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  async function createPayment(transaction) {
    setBusy('payment')
    setError('')
    try {
      const data = await request(`/procurements/${selected.id}/payment/create`, {
        method: 'POST',
        body: JSON.stringify({ transaction_id: transaction.id })
      })
      if (!data.approval_url) throw new Error('PayPal approval URL was not returned.')
      window.location.href = data.approval_url
    } catch (err) {
      setError(err.message)
      setBusy('')
    }
  }

  async function createProcurement(event) {
    event.preventDefault()
    setBusy('create')
    setError('')
    try {
      const data = await request('/procurements', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          budget_amount: Number(form.budget_amount)
        })
      })
      setNotice('Procurement request created successfully.')
      setShowCreate(false)
      setForm({ title: '', description: '', budget_amount: '', currency: 'USD' })
      await loadData()
      if (data.procurement?.id) setSelectedId(data.procurement.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')
    const transactionId = params.get('transaction_id')
    if (!token || !transactionId) return

    let cancelled = false

    async function capture() {
      setBusy('capture')

      try {
        const data = await request(`/payments/${transactionId}/capture`, {
          method: 'POST',
          body: JSON.stringify({ order_id: token })
        })

        if (!cancelled) {
          setNotice(data.message || 'PayPal payment captured successfully.')
          window.history.replaceState({}, '', window.location.pathname)
          await loadData()
          if (selectedId) await loadPayments(selectedId)
        }
      } catch (err) {
        if (!cancelled) {
          setError(`Payment return received, but capture needs attention: ${err.message}`)
        }
      } finally {
        if (!cancelled) setBusy('')
      }
    }

    capture()
    return () => { cancelled = true }
  }, [request, loadData, loadPayments, selectedId])

  const statusClass = status => (status || 'DRAFT').toLowerCase().replaceAll('_', '-')

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={() => setActiveNav('Overview')}>
          <span className="brand-mark"><Zap size={22} fill="currentColor" /></span>
          <span>paypilot<span className="brand-ai"> AI</span><small>PROCUREMENT INTELLIGENCE</small></span>
        </a>

        <div className="workspace-label">WORKSPACE</div>
        <nav className="nav-list">
          {[
            ['Overview', LayoutDashboard],
            ['Procurements', Package],
            ['Supplier Analysis', BarChart3],
            ['Approvals', ShieldCheck],
            ['Payments', Wallet]
          ].map(([label, Icon]) => (
            <button key={label}
              className={`nav-link ${activeNav === label ? 'active' : ''}`}
              onClick={() => setActiveNav(label)}>
              <Icon size={18} /><span>{label}</span>
              {label === 'Approvals' && selected?.status === 'ANALYZED' &&
                <span className="nav-dot" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sandbox-card">
            <span className="sandbox-indicator" />
            <div><strong>Sandbox environment</strong><small>PayPal test mode active</small></div>
          </div>
          <div className="profile">
            <div className="avatar">PP</div>
            <div><strong>Procurement Admin</strong><small>Workspace owner</small></div>
            <ChevronDown size={16} />
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><span>/</span><strong>{activeNav}</strong></div>
          <div className="top-actions">
            <span className="environment-pill"><span /> SANDBOX</span>
            <button className="icon-button" aria-label="Notifications"><Bell size={19} /></button>
            <div className="top-avatar">PP</div>
          </div>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow"><Sparkles size={14} /> INTELLIGENT PROCUREMENT PLATFORM</div>
              <h1>{activeNav === 'Overview' ? 'Procurement overview' : activeNav}</h1>
              <p>Make smarter purchasing decisions. Let AI handle the analysis.</p>
            </div>
            <div className="heading-actions">
              <button className="button button-secondary" onClick={loadData}>
                <RefreshCw size={16} /> Refresh
              </button>
              <button className="button button-primary" onClick={() => setShowCreate(true)}>
                <Plus size={17} /> New request
              </button>
            </div>
          </div>

          {error && <div className="alert alert-error"><X size={17} />{error}<button onClick={() => setError('')}><X size={15}/></button></div>}
          {notice && <div className="alert alert-success"><CheckCircle2 size={17} />{notice}<button onClick={() => setNotice('')}><X size={15}/></button></div>}

          <section className="stats-grid">
            <div className="stat-card">
              <div className="stat-top"><span>Total requests</span><span className="stat-icon purple"><FileText size={19}/></span></div>
              <strong>{procurements.length}</strong>
              <small><span className="muted">Across your workspace</span></small>
            </div>
            <div className="stat-card">
              <div className="stat-top"><span>Completed payments</span><span className="stat-icon green"><CircleDollarSign size={19}/></span></div>
              <strong>{completedCount}</strong>
              <small><span className="positive"><ArrowUpRight size={13}/> Verified captures</span></small>
            </div>
            <div className="stat-card">
              <div className="stat-top"><span>Total paid</span><span className="stat-icon blue"><Wallet size={19}/></span></div>
              <strong>{money(totalSpend)}</strong>
              <small><span className="muted">Sandbox transactions</span></small>
            </div>
            <div className="stat-card">
              <div className="stat-top"><span>Active suppliers</span><span className="stat-icon orange"><Truck size={19}/></span></div>
              <strong>{quotes.length}</strong>
              <small><span className="muted">For selected request</span></small>
            </div>
          </section>

          <section className="content-grid">
            <div className="panel procurement-panel">
              <div className="panel-heading">
                <div><h2>Procurement requests</h2><p>Track and manage purchasing activity</p></div>
                <button className="text-button" onClick={() => setActiveNav('Procurements')}>View all <ArrowUpRight size={14}/></button>
              </div>
              <div className="search-box"><Search size={16}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search requests..." /></div>

              {loading ? <div className="empty-state"><Loader2 className="spin" />Loading procurements...</div> :
                filtered.length === 0 ? <div className="empty-state">No procurement requests found.</div> :
                <div className="request-list">
                  {filtered.map(p => (
                    <button key={p.id} className={`request-row ${selected?.id === p.id ? 'selected' : ''}`}
                      onClick={() => { setSelectedId(p.id); setAnalysis(null) }}>
                      <span className="request-icon"><Package size={19}/></span>
                      <span className="request-info"><strong>{p.title}</strong><small>REQ-{String(p.id).padStart(4, '0')} · {p.quotes?.length || 0} supplier quotes</small></span>
                      <span className={`status-badge ${statusClass(p.status)}`}>{p.status}</span>
                      <span className="request-amount">{money(p.budget_amount, p.currency)}</span>
                    </button>
                  ))}
                </div>
              }
            </div>

            <div className="panel selected-panel">
              <div className="panel-heading">
                <div><h2>Request details</h2><p>Selected procurement</p></div>
                {selected && <span className={`status-badge ${statusClass(selected.status)}`}>{selected.status}</span>}
              </div>
              {selected ? <>
                <div className="selected-title">{selected.title}</div>
                <p className="description">{selected.description}</p>
                <div className="detail-metrics">
                  <div><small>Approved budget</small><strong>{money(selected.budget_amount, selected.currency)}</strong></div>
                  <div><small>Supplier quotes</small><strong>{quotes.length}</strong></div>
                </div>
                <div className="budget-track"><span style={{width: `${Math.min(100, quotes.length ? Math.max(...quotes.map(q => Number(q.total_price))) / Number(selected.budget_amount) * 100 : 0)}%`}} /></div>
                <div className="budget-caption"><span>Highest quote vs budget</span><strong>{money(Math.max(0, ...quotes.map(q => Number(q.total_price))), selected.currency)}</strong></div>
                <button className="button button-ai" onClick={runAnalysis} disabled={!!busy}>
                  {busy === 'analysis' ? <Loader2 className="spin" size={16}/> : <Sparkles size={16}/>}
                  {busy === 'analysis' ? 'Analyzing...' : 'Run AI analysis'}
                </button>
              </> : <div className="empty-state">Select a procurement request.</div>}
            </div>
          </section>

          <section className="panel quotes-panel">
            <div className="panel-heading">
              <div><h2>Supplier comparison</h2><p>Compare pricing, delivery and supplier value</p></div>
              <span className="table-label"><Activity size={14}/> LIVE DATA</span>
            </div>
            {quotes.length ? <div className="table-wrap"><table>
              <thead><tr><th>SUPPLIER</th><th>OFFER</th><th>UNIT PRICE</th><th>QUANTITY</th><th>TOTAL</th><th>DELIVERY</th><th>STATUS</th><th>ACTION</th></tr></thead>
              <tbody>{quotes.map(q => (
                <tr key={q.id}>
                  <td><div className="supplier-cell"><span className="supplier-avatar">{q.supplier_name?.slice(0,1)}</span><strong>{q.supplier_name}</strong></div></td>
                  <td className="offer-cell">{q.item_description}</td>
                  <td>{money(q.unit_price, selected.currency)}</td>
                  <td>{q.quantity}</td>
                  <td className="price-cell">{money(q.total_price, selected.currency)}</td>
                  <td><span className="delivery"><Clock3 size={14}/>{q.delivery_days} days</span></td>
                  <td><span className="quote-status">{payments.some(p => Number(p.quote_id) === Number(q.id) && p.status === 'COMPLETED') ? 'Paid' : selected.status === 'PAID' ? 'Not selected' : selected.status === 'APPROVED' ? 'Awaiting payment' : 'Quoted'}</span></td>
                  <td>{selected.status !== 'PAID' && selected.status !== 'APPROVED' ?
                    <button className="small-action" disabled={!!busy || selected.status !== 'ANALYZED'} onClick={() => approveQuote(q)}>Approve</button> :
                    <span className="muted">—</span>}</td>
                </tr>
              ))}</tbody>
            </table></div> : <div className="empty-state">No supplier quotes yet.</div>}
          </section>

          <section className="bottom-grid">
            <div className="panel ai-panel">
              <div className="panel-heading">
                <div><h2><Sparkles size={18}/> AI procurement intelligence</h2><p>Gemini-powered decision support</p></div>
                <span className="ai-tag">GEMINI AI</span>
              </div>
              {analysis?.ai_insights ? <div className="ai-result">
                <div className="ai-result-heading"><CheckCircle2 size={17}/> Analysis completed</div>
                <div className="ai-meta">
                  <span>{analysis.ai_insights?.provider || 'AI provider'}</span>
                  <span>{analysis.ai_insights?.model || 'AI model'}</span>
                </div>
                <div className="ai-report">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {typeof analysis.ai_insights === 'string'
                      ? analysis.ai_insights
                      : analysis.ai_insights?.report || JSON.stringify(analysis.ai_insights, null, 2)}
                  </ReactMarkdown>
                </div>
              </div> : <div className="ai-placeholder">
                <div className="ai-orb"><Sparkles size={23}/></div>
                <strong>Turn supplier data into decisions</strong>
                <p>Run an AI analysis to receive supplier recommendations, risk observations and an explainable procurement assessment.</p>
                <button className="text-button" onClick={runAnalysis} disabled={!selected || !!busy}>Analyze selected request <ArrowUpRight size={14}/></button>
              </div>}
            </div>

            <div className="panel payment-panel">
              <div className="panel-heading"><div><h2>Payment activity</h2><p>PayPal transaction records</p></div><CreditCard size={19} className="heading-icon"/></div>
              {payments.length ? <div className="payment-list">{payments.map(p => (
                <div className="payment-row" key={p.id}>
                  <span className="payment-icon"><CreditCard size={17}/></span>
                  <span className="payment-info"><strong>Transaction #{p.id}</strong><small>{p.paypal_capture_id ? `Capture ${p.paypal_capture_id}` : p.paypal_order_id || 'Awaiting checkout'}</small></span>
                  <span className="payment-right"><strong>{money(p.amount, p.currency)}</strong><small className={`payment-status ${statusClass(p.status)}`}>{p.status}</small></span>
                  {p.status === 'APPROVED' && <button className="small-action" disabled={!!busy} onClick={() => createPayment(p)}>Pay with PayPal</button>}
                </div>
              ))}</div> : <div className="empty-state">No payment transactions for this request.</div>}
              <div className="payment-footer"><ShieldCheck size={15}/> Human approval required · PayPal Sandbox</div>
            </div>
          </section>

          <footer className="footer"><span>© 2026 PayPilot AI</span><span><span className="footer-dot"/> All systems operational</span><span>Built for the PayPal AI Hackathon</span></footer>
        </div>
      </main>

      {showCreate && <div className="modal-backdrop" onClick={() => setShowCreate(false)}>
        <form className="modal" onSubmit={createProcurement} onClick={e => e.stopPropagation()}>
          <div className="modal-heading"><div><h2>New procurement request</h2><p>Describe what your business needs to purchase.</p></div><button type="button" className="icon-button" onClick={() => setShowCreate(false)}><X size={19}/></button></div>
          <label>Request title<input required value={form.title} onChange={e => setForm({...form, title: e.target.value})} placeholder="e.g. Office laptop procurement"/></label>
          <label>Description<textarea required rows="3" value={form.description} onChange={e => setForm({...form, description: e.target.value})} placeholder="Describe specifications and requirements..."/></label>
          <div className="form-row"><label>Budget<input required type="number" min="0.01" step="0.01" value={form.budget_amount} onChange={e => setForm({...form, budget_amount: e.target.value})} placeholder="3000"/></label><label>Currency<select value={form.currency} onChange={e => setForm({...form, currency: e.target.value})}><option>USD</option><option>EUR</option><option>GBP</option><option>INR</option></select></label></div>
          <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setShowCreate(false)}>Cancel</button><button className="button button-primary" disabled={!!busy}>{busy === 'create' ? 'Creating...' : 'Create request'}</button></div>
        </form>
      </div>}
    </div>
  )
}

export default App
