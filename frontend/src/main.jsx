import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const expenseTypes = [
  ['ADMINISTRATION', 'Administración'],
  ['MAINTENANCE', 'Mantenimiento'],
  ['EXTRAORDINARY', 'Extraordinario'],
  ['LEGAL', 'Legal'],
  ['POOL', 'Piscina'],
  ['GYM', 'Gimnasio'],
  ['SQUASH_COURT', 'Cancha de squash'],
]
const subcategories = {
  ADMINISTRATION: [['EQUIPMENT', 'Equipo'], ['SUPPLIES', 'Insumos'], ['SERVICES_PROVIDER', 'Servicios / Proveedor']],
  MAINTENANCE: [['EQUIPMENT', 'Equipo'], ['SUPPLIES', 'Insumos'], ['SERVICES_PROVIDER', 'Servicios / Proveedor']],
  EXTRAORDINARY: [['GENERAL', 'General']],
  LEGAL: [['CONSULTING', 'Consultorías'], ['PROCEDURES', 'Trámites'], ['LITIGATION', 'Demandas']],
  POOL: [['EQUIPMENT', 'Equipo'], ['SUPPLIES', 'Insumos'], ['SERVICES_PROVIDER', 'Servicios / Proveedor']],
  GYM: [['EQUIPMENT', 'Equipo'], ['SUPPLIES', 'Insumos'], ['SERVICES_PROVIDER', 'Servicios / Proveedor']],
  SQUASH_COURT: [['EQUIPMENT', 'Equipo'], ['SUPPLIES', 'Insumos'], ['SERVICES_PROVIDER', 'Servicios / Proveedor']],
}
const subcategoryName = (value) => Object.values(subcategories).flat().find(([key]) => key === value)?.[1] || value
const roles = [['REQUESTER', 'Puede solicitar'], ['APPROVER', 'Puede aprobar'], ['VIEWER', 'Puede consultar'], ['ADMIN', 'Administrador']]
const roleName = (role) => roles.find(([value]) => value === role)?.[1] || role

function latestExpenseVersions(items) {
  const byReference = new Map()
  for(const item of items){byReference.set(item.request_id,item);byReference.set(item.display_id,item)}
  const rootOf = item => {
    let current=item, guard=0
    while(current.revised_from_request_id&&byReference.has(current.revised_from_request_id)&&guard++<100) current=byReference.get(current.revised_from_request_id)
    return current.request_id
  }
  const latest = new Map()
  for(const item of items){const root=rootOf(item),saved=latest.get(root);if(!saved||Number(item.id)>Number(saved.id))latest.set(root,item)}
  return [...latest.values()]
}

async function api(path, options = {}) {
  const token = localStorage.getItem('access_token')
  const isFormData = options.body instanceof FormData
  const response = await fetch(path, {
    ...options,
    headers: { ...(!isFormData ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options.headers || {}) },
  })
  if (!response.ok) {
    let detail = 'Ocurrió un error'
    try { detail = (await response.json()).detail || detail } catch (_) {}
    const error = new Error(detail); error.status = response.status; throw error
  }
  return response.json()
}

async function downloadAttachment(attachment) {
  const response = await fetch(`/api/expenses/attachments/${attachment.id}`, { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } })
  if (!response.ok) throw new Error('No se pudo descargar el archivo')
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a'); link.href = url; link.download = attachment.original_name; link.click(); URL.revokeObjectURL(url)
}

function Login({ onLogin }) {
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const submit = async (event) => {
    event.preventDefault(); setError('')
    try {
      const result = await api('/api/auth/login', { method: 'POST', body: JSON.stringify(form) })
      localStorage.setItem('access_token', result.access_token); onLogin(result.user)
    } catch (e) { setError(e.message) }
  }
  return <main className="single"><section className="card login-card">
    <div className="brand-mark dark">PH</div><p className="eyebrow">GESTIÓN DE GASTOS</p><h1>Iniciar sesión</h1>
    <p className="muted">Accede con el usuario registrado por el administrador.</p>
    <form onSubmit={submit} className="login-form"><label>Correo<input type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} required /></label><label>Contraseña<input type="password" value={form.password} onChange={e => setForm({...form, password: e.target.value})} required minLength="8" /></label>{error && <div className="notice error">{error}</div>}<button className="primary">Entrar</button></form>
  </section></main>
}

function StatusBadge({ status }) { return <span className={`badge badge-${String(status).toLowerCase()}`}>{String(status).replaceAll('_', ' ')}</span> }

function ExpenseForm({ onCreated, draft, onCancelEdit }) {
  const empty = { title: '', description: '', expense_type: 'MAINTENANCE', expense_subcategory: 'EQUIPMENT', amount: '', supplier: '', item_url: '' }
  const [form, setForm] = useState(empty); const [quotation, setQuotation] = useState(null); const [message, setMessage] = useState(null); const [saving, setSaving] = useState(false)
  useEffect(()=>{if(draft){setForm({title:draft.title,description:draft.description,expense_type:draft.expense_type,expense_subcategory:draft.expense_subcategory,amount:String(draft.amount),supplier:draft.supplier,item_url:draft.item_url||'',revised_from_request_id:draft.request_id});setQuotation(null);setMessage(null)}},[draft?.request_id])
  const submit = async e => { e.preventDefault(); setSaving(true); setMessage(null); if(!form.item_url&&!quotation){setMessage({type:'error',text:'Debes proporcionar una URL o adjuntar una cotización.'});setSaving(false);return} let item=null; try { const payload={...form,amount:Number(form.amount),item_url:form.item_url||null,quotation_pending:Boolean(quotation)}; const editing=Boolean(draft); delete payload.revised_from_request_id; item = await api(editing?`/api/expenses/${draft.request_id}/resubmit`:'/api/expenses', { method: editing?'PUT':'POST', body: JSON.stringify(payload) }); if(quotation){const data=new FormData();data.append('file',quotation);await api(`/api/expenses/${item.request_id}/attachments`,{method:'POST',body:data})} setForm(empty);setQuotation(null);e.target.reset();setMessage({type:'success', text:`Solicitud ${item.display_id} enviada a aprobación con sus soportes.`});onCreated() } catch (err) { setMessage({type:'error', text:item?`La solicitud ${item.display_id} se guardó, pero el archivo no pudo cargarse: ${err.message}`:err.message});onCreated() } finally { setSaving(false) } }
  return <section className="card" id="expense-form"><div className="card-heading"><div><p className="eyebrow">{draft?'CORRECCIÓN Y REENVÍO':'NUEVA SOLICITUD'}</p><h2>{draft?'Corregir solicitud existente':'Registrar gasto'}</h2></div>{draft&&<button className="secondary" type="button" onClick={()=>{setForm(empty);onCancelEdit?.()}}>Cancelar edición</button>}</div>{draft&&<div className="revision-notice">Se actualizará la solicitud <strong>{draft.display_id}</strong> sin crear otra fila. El flujo anterior expirará y se generarán enlaces de aprobación nuevos.</div>}<form onSubmit={submit} className="form-grid">
    <label className="full">Título<input value={form.title} onChange={e=>setForm({...form,title:e.target.value})} required minLength="3" /></label>
    <label>Categoría<select value={form.expense_type} onChange={e=>{const type=e.target.value;setForm({...form,expense_type:type,expense_subcategory:subcategories[type][0][0]})}}>{expenseTypes.map(x=><option key={x[0]} value={x[0]}>{x[1]}</option>)}</select></label>
    <label>Subcategoría<select value={form.expense_subcategory} onChange={e=>setForm({...form,expense_subcategory:e.target.value})}>{subcategories[form.expense_type].map(x=><option key={x[0]} value={x[0]}>{x[1]}</option>)}</select></label>
    <label>Monto (USD)<input type="number" min="0.01" step="0.01" value={form.amount} onChange={e=>setForm({...form,amount:e.target.value})} required /></label>
    <label className="full">Proveedor<input value={form.supplier} onChange={e=>setForm({...form,supplier:e.target.value})} required minLength="2" /></label>
    <div className="full support-requirement">Adjunta al menos un soporte para iniciar el flujo: URL, cotización o ambos.</div>
    <label>URL del producto o servicio<input type="url" value={form.item_url} onChange={e=>setForm({...form,item_url:e.target.value})} placeholder="https://..." /></label>
    <label>Cotización (PDF o imagen, máx. 10 MB)<input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" onChange={e=>setQuotation(e.target.files[0]||null)} /></label>
    <label className="full">Descripción / justificación<textarea rows="4" value={form.description} onChange={e=>setForm({...form,description:e.target.value})} required minLength="3" /></label>
    <div className="full form-actions">{message && <div className={`notice ${message.type}`}>{message.text}</div>}<button className="primary" disabled={saving}>{saving?'Guardando...':draft?'Guardar y reenviar':'Crear solicitud'}</button></div>
  </form></section>
}

function ClosurePanel({ expense, onDone, onCancel }) {
  const [order,setOrder]=useState(null),[invoice,setInvoice]=useState(null),[notes,setNotes]=useState(''),[saving,setSaving]=useState(false),[error,setError]=useState('')
  const submit=async e=>{e.preventDefault();setSaving(true);setError('');try{const data=new FormData();data.append('purchase_order',order);data.append('invoice',invoice);if(notes)data.append('notes',notes);await api(`/api/expenses/${expense.request_id}/close`,{method:'POST',body:data});onDone()}catch(err){setError(err.message)}finally{setSaving(false)}}
  return <form className="closure-panel" onSubmit={submit}><div><p className="eyebrow">CIERRE DE APROBACIÓN</p><h3>{expense.title}</h3><span className="muted">Adjunta los documentos finales para cerrar esta solicitud aprobada.</span></div><label>Orden de compra<input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" onChange={e=>setOrder(e.target.files[0]||null)} required /></label><label>Factura<input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" onChange={e=>setInvoice(e.target.files[0]||null)} required /></label><label>Notas de cierre<textarea rows="2" value={notes} onChange={e=>setNotes(e.target.value)} /></label>{error&&<div className="notice error">{error}</div>}<div className="closure-actions"><button type="button" className="secondary" onClick={onCancel}>Cancelar</button><button className="primary" disabled={saving}>{saving?'Cerrando...':'Cerrar aprobación'}</button></div></form>
}

function ExpenseTable({ refreshKey, canEdit, isAdmin, onEdit, onChanged }) {
  const [items,setItems]=useState([]); const [error,setError]=useState(''); const [search,setSearch]=useState(''); const [status,setStatus]=useState(''); const [category,setCategory]=useState(''); const [closing,setClosing]=useState(null)
  useEffect(()=>{ api('/api/expenses').then(data=>setItems(latestExpenseVersions(data).map(item=>({...item,approvals:item.approvals.filter(a=>a.flow_id===item.flow_id),internal_request_id:item.request_id,request_id:item.display_id})))).catch(e=>setError(e.message)) },[refreshKey])
  const cancel=async expense=>{const reason=window.prompt(`Indica el motivo para cancelar "${expense.title}":`);if(!reason)return;try{await api(`/api/expenses/${expense.request_id}/cancel`,{method:'POST',body:JSON.stringify({reason})});onChanged()}catch(err){setError(err.message)}}
  const normalized=search.trim().toLowerCase(); const filtered=items.filter(x=>(!status||x.status===status)&&(!category||x.expense_type===category)&&(!normalized||[x.display_id,x.request_id,x.title,x.supplier,x.requested_by,x.flow_id].some(value=>String(value||'').toLowerCase().includes(normalized))))
  return <section className="card"><div className="card-heading"><div><p className="eyebrow">SEGUIMIENTO</p><h2>Solicitudes</h2></div></div>{closing&&<ClosurePanel expense={closing} onCancel={()=>setClosing(null)} onDone={()=>{setClosing(null);onChanged()}}/>}<div className="table-filters"><label>Buscar<input value={search} onChange={e=>setSearch(e.target.value)} placeholder="ID, solicitud, proveedor..." /></label><label>Estado<select value={status} onChange={e=>setStatus(e.target.value)}><option value="">Todos</option><option value="SUBMITTED">Enviada</option><option value="PENDING_APPROVAL">Pendiente</option><option value="APPROVED">Aprobada</option><option value="REJECTED">Rechazada</option><option value="NEEDS_REVISION">Requiere revisión</option><option value="CANCELLED">Cancelada</option><option value="CLOSED">Cerrada</option></select></label><label>Categoría<select value={category} onChange={e=>setCategory(e.target.value)}><option value="">Todas</option>{expenseTypes.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>{(search||status||category)&&<button className="secondary" onClick={()=>{setSearch('');setStatus('');setCategory('')}}>Limpiar</button>}<span className="filter-count">{filtered.length} de {items.length}</span></div>{error?<div className="notice error">{error}</div>:items.length===0?<p className="muted">Aún no hay solicitudes.</p>:filtered.length===0?<p className="muted">No hay solicitudes que coincidan con los filtros.</p>:<div className="table-wrap"><table><thead><tr><th>ID único</th><th>Solicitud</th><th>Categoría</th><th>Soportes</th><th>Solicitante</th><th>Monto</th><th>Estado</th><th>Flujo</th>{canEdit&&<th>Acción</th>}</tr></thead><tbody>{filtered.map(x=><tr key={x.request_id}><td><span className="id-code" title={x.request_id}>{x.request_id}</span>{x.revised_from_request_id&&<span className="subtext">Corrección de {x.revised_from_request_id.slice(0,8)}…</span>}</td><td><strong>{x.title}</strong><span className="subtext">{x.supplier}</span></td><td>{x.expense_type}<span className="subtext">{subcategoryName(x.expense_subcategory)}</span></td><td className="support-cell">{x.item_url&&<a href={x.item_url} target="_blank" rel="noreferrer">Ver producto/servicio</a>}{x.attachments.map(a=><button className="link-button" key={a.id} onClick={()=>downloadAttachment(a).catch(e=>setError(e.message))}>{a.document_type==='PURCHASE_ORDER'?'Orden: ':a.document_type==='INVOICE'?'Factura: ':''}{a.original_name}</button>)}{!x.item_url&&!x.attachments.length&&<span className="muted">—</span>}</td><td>{x.requested_by}</td><td>${Number(x.amount).toLocaleString(undefined,{minimumFractionDigits:2})}</td><td><StatusBadge status={x.status}/>{x.cancellation_reason&&<span className="subtext" title={x.cancellation_reason}>Motivo: {x.cancellation_reason}</span>}{x.closed_by&&<span className="subtext">Cerrada por {x.closed_by}</span>}</td><td className="flow-cell"><span title={x.flow_id}>Flujo: {x.flow_id}</span>{x.approvals.map(a=><span key={a.id}>{a.step}. {a.approver_role} · {a.status}</span>)}</td>{canEdit&&<td><div className="row-actions"><button className="secondary nowrap" onClick={()=>onEdit(x)}>Corregir / reenviar</button>{['SUBMITTED','PENDING_APPROVAL','APPROVED'].includes(x.status)&&<button className="danger nowrap" onClick={()=>cancel(x)}>Cancelar solicitud</button>}{isAdmin&&x.status==='APPROVED'&&<button className="primary nowrap" onClick={()=>setClosing(x)}>Cerrar aprobación</button>}</div></td>}</tr>)}</tbody></table></div>}</section>
}

function CorrectionPicker({ refreshKey, onEdit }) {
  const [items,setItems]=useState([])
  useEffect(()=>{api('/api/expenses').then(data=>setItems(latestExpenseVersions(data)))},[refreshKey])
  if(!items.length)return null
  return <section className="correction-bar"><span>¿Necesitas corregir una solicitud enviada?</span><div><select id="correction-request" defaultValue=""><option value="" disabled>Selecciona una solicitud</option>{items.map(x=><option key={x.request_id} value={x.request_id}>{x.title} · {x.status} · {x.request_id.slice(0,8)}</option>)}</select><button className="secondary nowrap" onClick={()=>{const id=document.getElementById('correction-request').value;const item=items.find(x=>x.request_id===id);if(item)onEdit(item)}}>Corregir / reenviar</button></div></section>
}

function Users() {
  const blank={name:'',email:'',password:'',role:'REQUESTER'}; const [form,setForm]=useState(blank); const [users,setUsers]=useState([]); const [message,setMessage]=useState(null)
  const load=()=>api('/api/users').then(setUsers).catch(e=>setMessage({type:'error',text:e.message})); useEffect(load,[])
  const create=async e=>{e.preventDefault();try{await api('/api/users',{method:'POST',body:JSON.stringify(form)});setForm(blank);setMessage({type:'success',text:'Usuario registrado.'});load()}catch(err){setMessage({type:'error',text:err.message})}}
  const update=async (id,changes)=>{try{await api(`/api/users/${id}`,{method:'PATCH',body:JSON.stringify(changes)});load()}catch(err){setMessage({type:'error',text:err.message})}}
  return <><section className="card"><div className="card-heading"><div><p className="eyebrow">ADMINISTRACIÓN</p><h2>Registrar usuario</h2></div></div><form className="form-grid" onSubmit={create}><label>Nombre<input value={form.name} onChange={e=>setForm({...form,name:e.target.value})} required /></label><label>Correo<input type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})} required /></label><label>Contraseña inicial<input type="password" minLength="8" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} required /></label><label>Rol<select value={form.role} onChange={e=>setForm({...form,role:e.target.value})}>{roles.map(x=><option key={x[0]} value={x[0]}>{x[1]}</option>)}</select></label><div className="full form-actions">{message&&<div className={`notice ${message.type}`}>{message.text}</div>}<button className="primary">Registrar</button></div></form></section>
  <section className="card"><h2>Usuarios</h2><div className="table-wrap"><table><thead><tr><th>Usuario</th><th>Rol</th><th>Estado</th><th>Acción</th></tr></thead><tbody>{users.map(u=><tr key={u.id}><td><strong>{u.name}</strong><span className="subtext">{u.email}</span></td><td><select value={u.role} onChange={e=>update(u.id,{role:e.target.value})}>{roles.map(x=><option key={x[0]} value={x[0]}>{x[1]}</option>)}</select></td><td>{u.active?'Activo':'Inactivo'}</td><td><button className="secondary" onClick={()=>update(u.id,{active:!u.active})}>{u.active?'Desactivar':'Activar'}</button></td></tr>)}</tbody></table></div></section></>
}

function ApprovalPage({token,user}) { const [data,setData]=useState(null),[comment,setComment]=useState(''),[message,setMessage]=useState(null); const load=()=>api(`/api/approvals/${token}`).then(setData).catch(e=>setMessage({type:'error',text:e.message})); useEffect(load,[token]); const decide=async decision=>{if(decision==='REVISION_REQUESTED'&&comment.trim().length<3){setMessage({type:'error',text:'Indica en el comentario qué debe corregir el solicitante.'});return}try{await api(`/api/approvals/${token}`,{method:'POST',body:JSON.stringify({decision,comment:comment||null})});setMessage({type:'success',text:decision==='REVISION_REQUESTED'?'Solicitud devuelta al solicitante para revisión.':'Decisión registrada.'});load()}catch(e){setMessage({type:'error',text:e.message})}}; if(!data)return <main className="single"><section className="card">{message?<div className="notice error">{message.text}</div>:'Cargando...'}</section></main>; const x=data.expense,pending=data.approval_status==='PENDING',preferredAction=new URLSearchParams(window.location.search).get('action'),resultClass=data.approval_status==='REVISION_REQUESTED'?'revision':data.approval_status.toLowerCase(),resultIcon=data.approval_status==='APPROVED'?'✓':data.approval_status==='REJECTED'?'×':'!',resultLabel=data.approval_status==='APPROVED'?'APROBADA':data.approval_status==='REJECTED'?'RECHAZADA':'EN REVISIÓN',promptLabel=preferredAction==='approve'?'APROBAR':preferredAction==='reject'?'RECHAZAR':'ENVIAR A REVISIÓN'; return <main className="single"><section className="card approval-card"><p className="eyebrow">APROBACIÓN DE GASTO</p><h1>Solicitud {x.display_id}</h1><p className="muted">Flujo: {x.flow_id}</p>{!pending&&['APPROVED','REJECTED','REVISION_REQUESTED'].includes(data.approval_status)&&<div className={`decision-result ${resultClass}`}><div className="decision-icon">{resultIcon}</div><strong>{resultLabel}</strong><span>{data.approval_status==='REVISION_REQUESTED'?'La solicitud volvió al solicitante para que realice las correcciones indicadas.':'La decisión fue registrada correctamente.'}</span></div>}{pending&&preferredAction&&<div className={`action-prompt ${preferredAction}`}>El correo solicitó <strong>{promptLabel}</strong>. Revisa todo el detalle y confirma tu decisión abajo.</div>}<div className="amount">${Number(x.amount).toLocaleString(undefined,{minimumFractionDigits:2})}</div><h2>{x.title}</h2><h3 className="detail-title">Detalle de la solicitud</h3><dl className="details"><div><dt>Categoría</dt><dd>{x.expense_type}</dd></div><div><dt>Subcategoría</dt><dd>{subcategoryName(x.expense_subcategory)||'—'}</dd></div><div><dt>Proveedor</dt><dd>{x.supplier}</dd></div><div><dt>Solicitante</dt><dd>{x.requested_by}</dd></div><div><dt>Responsable de esta acción</dt><dd>{user.email}</dd></div><div><dt>Estado del paso</dt><dd>{data.approval_status}</dd></div></dl><div className="description-box"><strong>Descripción / justificación</strong><p>{x.description}</p></div>{(x.item_url||x.attachments.length>0)&&<div className="support-box"><strong>Soportes de la solicitud</strong>{x.item_url&&<a href={x.item_url} target="_blank" rel="noreferrer">Abrir producto o servicio</a>}{x.attachments.map(a=><button className="link-button" key={a.id} onClick={()=>downloadAttachment(a).catch(e=>setMessage({type:'error',text:e.message}))}>Descargar {a.original_name}</button>)}</div>}<label>Comentario de la decisión<textarea rows="4" value={comment} onChange={e=>setComment(e.target.value)} disabled={!pending} placeholder="Para revisión, indica qué debe corregir el solicitante."/></label>{message&&<div className={`notice ${message.type}`}>{message.text}</div>}<div className="decision-actions"><button className="danger" disabled={!pending} onClick={()=>decide('REJECTED')}>{preferredAction==='reject'?'Confirmar rechazo':'Rechazar'}</button><button className="review" disabled={!pending} onClick={()=>decide('REVISION_REQUESTED')}>{preferredAction==='revision'?'Confirmar envío a revisión':'Enviar a revisión'}</button><button className="primary" disabled={!pending} onClick={()=>decide('APPROVED')}>{preferredAction==='approve'?'Confirmar aprobación':'Aprobar'}</button></div></section></main> }

function App(){
  const [user,setUser]=useState(null),[loading,setLoading]=useState(true),[tab,setTab]=useState('expenses'),[refresh,setRefresh]=useState(0),[revision,setRevision]=useState(null)
  useEffect(()=>{if(!localStorage.getItem('access_token')){setLoading(false);return}api('/api/auth/me').then(setUser).catch(()=>localStorage.removeItem('access_token')).finally(()=>setLoading(false))},[])
  if(loading)return <main className="single">Cargando...</main>
  if(!user)return <Login onLogin={setUser}/>
  const match=window.location.pathname.match(/^\/approve\/([^/]+)$/)
  if(match)return <ApprovalPage token={match[1]} user={user}/>
  const logout=()=>{localStorage.removeItem('access_token');setUser(null)}
  const startRevision=item=>{setRevision(item);setTimeout(()=>document.getElementById('expense-form')?.scrollIntoView({behavior:'smooth'}),0)}
  const created=()=>{setRevision(null);setRefresh(x=>x+1)}
  const canCreate=['REQUESTER','ADMIN'].includes(user.role)
  return <><header className="topbar"><div><div className="brand-mark">PH</div><div><strong>Gestión de Gastos</strong><span>{user.name} · {roleName(user.role)}</span></div></div><div className="header-actions">{user.role==='ADMIN'&&<button onClick={()=>setTab(tab==='users'?'expenses':'users')}>{tab==='users'?'Solicitudes':'Usuarios'}</button>}<button onClick={logout}>Salir</button></div></header><main className="layout"><section className="hero"><p className="eyebrow">CONTROL · TRAZABILIDAD · APROBACIÓN</p><h1>{tab==='users'?'Administración de usuarios':'Solicitudes de gasto del PH'}</h1></section>{tab==='users'?<Users/>:<>{canCreate&&<ExpenseForm onCreated={created} draft={revision} onCancelEdit={()=>setRevision(null)}/>}<ExpenseTable refreshKey={refresh} canEdit={canCreate} isAdmin={user.role==='ADMIN'} onEdit={startRevision} onChanged={()=>setRefresh(x=>x+1)}/></>}</main></>
}

createRoot(document.getElementById('root')).render(<React.StrictMode><App/></React.StrictMode>)
