import { useState } from 'react'
import { api } from '../../api/client'
import { useDialog } from '../../components/Dialog'
import { useFlash } from '../../components/Flash'
import { EmptyState, ErrorState, Loading, PageHeader, SearchBox } from '../../components/ui'
import { EQUIPMENT_STATUSES, statusLabel } from '../../lib/format'
import { matches } from '../../lib/search'
import { useResources } from '../../lib/useResources'

const EMPTY = { equipment_code: '', equipment_name: '', equipment_type: '', description: '' }

export default function StaffEquipment() {
  const flash = useFlash()
  const ask = useDialog()
  const { equipments, error, loading, reload } = useResources()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [query, setQuery] = useState('')

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const act = async (fn, message) => {
    try {
      await fn()
      flash(message, 'success')
      reload()
      return true
    } catch (err) {
      flash(err.message, 'danger')
      return false
    }
  }

  const onCreate = async (e) => {
    e.preventDefault()
    const ok = await act(
      () => api('/inventory/equipments', { method: 'POST', json: { ...form, description: form.description || null } }),
      `Equipment '${form.equipment_name}' added successfully`,
    )
    if (ok) {
      setForm(EMPTY)
      setShowForm(false)
    }
  }

  const update = (item, patch, message) =>
    act(() => api(`/inventory/equipments/${item.id}`, { method: 'PATCH', json: patch }), message)

  const shown = equipments.filter((e) => matches(query, e.equipment_code, e.equipment_name, e.equipment_type, e.description))

  return (
    <>
      <PageHeader icon="fa-boxes-stacked" title="Equipment Management" subtitle="Manage projectors, laptops, cameras and other bookable gear.">
        <button type="button" className="button" onClick={() => setShowForm(!showForm)}>
          <i className="fa-solid fa-plus-circle" /> Add Equipment
        </button>
      </PageHeader>

      <div className={`expandable-panel ${showForm ? 'show' : ''}`}>
        <h2 className="section-title" style={{ marginBottom: '1.25rem' }}>
          <i className="fa-solid fa-plus" style={{ color: 'var(--primary)' }} /> Register New Equipment
        </h2>
        <form onSubmit={onCreate}>
          <div className="grid grid-3">
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="equipment_code">Asset Code</label>
              <input id="equipment_code" required maxLength={50} placeholder="e.g. PROJ003" value={form.equipment_code} onChange={set('equipment_code')} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="equipment_name">Name</label>
              <input id="equipment_name" required maxLength={255} placeholder="e.g. Epson Projector" value={form.equipment_name} onChange={set('equipment_name')} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="equipment_type">Category</label>
              <input id="equipment_type" required maxLength={100} placeholder="e.g. projector" value={form.equipment_type} onChange={set('equipment_type')} />
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea id="description" rows={2} value={form.description} onChange={set('description')} />
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" className="button secondary-button button-sm" onClick={() => setShowForm(false)}>
              Cancel
            </button>
            <button type="submit" className="button button-sm">
              <i className="fa-solid fa-check" /> Save Equipment
            </button>
          </div>
        </form>
      </div>

      <div className="toolbar-container" style={{ marginTop: 0 }}>
        <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
          อุปกรณ์ทั้งหมด <strong>{equipments.length} ชิ้น</strong> (1 แถวต่ออุปกรณ์ 1 ชิ้น)
        </p>
        <SearchBox value={query} onChange={setQuery} placeholder="Search equipment..." />
      </div>

      {error && <ErrorState error={error} onRetry={reload} />}
      {loading ? (
        <Loading />
      ) : (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Equipment</th>
                <th>Category</th>
                <th>Status</th>
                <th>Bookable</th>
                <th style={{ width: 100 }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.equipment_code}</strong>
                  </td>
                  <td style={{ fontWeight: 600 }}>
                    <i className="fa-solid fa-cube" style={{ color: 'var(--primary)', marginRight: 6 }} />
                    {item.equipment_name}
                    {item.description && (
                      <div className="muted" style={{ fontWeight: 'normal', fontSize: '0.8rem' }}>
                        {item.description}
                      </div>
                    )}
                  </td>
                  <td>{item.equipment_type}</td>
                  <td>
                    <select
                      aria-label={`Status of ${item.equipment_code}`}
                      value={item.status}
                      style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}
                      onChange={(e) => update(item, { status: e.target.value }, `${item.equipment_code} is now ${statusLabel(e.target.value)}`)}
                    >
                      {EQUIPMENT_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {statusLabel(s)}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`${item.equipment_code} bookable`}
                      checked={item.is_bookable}
                      onChange={(e) => update(item, { is_bookable: e.target.checked }, `${item.equipment_code} updated`)}
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="button button-sm danger-button"
                      onClick={async () =>
                        (await ask({ title: `Delete ${item.equipment_name}?`, message: 'This cannot be undone. Equipment with any bookings cannot be deleted; set its status to retired instead.', confirmLabel: 'Delete', danger: true })) &&
                        act(() => api(`/inventory/equipments/${item.id}`, { method: 'DELETE' }), `Equipment '${item.equipment_name}' deleted`)
                      }
                    >
                      <i className="fa-solid fa-trash-can" /> Delete
                    </button>
                  </td>
                </tr>
              ))}
              {shown.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <EmptyState icon="fa-solid fa-box-open" title="No Equipment" text='Click "Add Equipment" above to register items.' />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
