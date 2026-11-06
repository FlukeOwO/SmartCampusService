import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { useFlash } from '../../components/Flash'
import { PageHeader } from '../../components/ui'
import { ALLOWED_UPLOADS, MAX_FILES, MAX_FILE_MB, PRIORITIES, REQUEST_TYPES, statusLabel } from '../../lib/format'

export default function CreateRequest() {
  const flash = useFlash()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    title: '',
    description: '',
    location: '',
    request_type: 'maintenance',
    priority: 'medium',
    contact_phone: '',
  })
  const [files, setFiles] = useState([])
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const onFiles = (e) => {
    const picked = Array.from(e.target.files)
    const tooBig = picked.find((f) => f.size > MAX_FILE_MB * 1024 * 1024)
    if (picked.length > MAX_FILES) setError(`You can attach at most ${MAX_FILES} files.`)
    else if (tooBig) setError(`${tooBig.name} is larger than ${MAX_FILE_MB} MB.`)
    else setError(null)
    setFiles(picked)
  }

  const onSubmit = async (e) => {
    e.preventDefault()
    if (files.length > MAX_FILES) return
    setSubmitting(true)
    setError(null)
    // multipart/form-data: ฟิลด์ข้อความ + ไฟล์หลายไฟล์ในชื่อ "files"
    const body = new FormData()
    Object.entries(form).forEach(([key, value]) => value && body.append(key, value))
    files.forEach((file) => body.append('files', file))
    try {
      const created = await api('/requests', { method: 'POST', form: body })
      flash(`Request ${created.request_number} submitted successfully`, 'success')
      navigate('/student/requests')
    } catch (err) {
      setError(
        err.status === 422
          ? 'Please check the form: title needs at least 5 characters and description at least 10.'
          : err.message,
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <PageHeader title="Report Campus Issue" subtitle="Submit a maintenance ticket or facility issue for staff assistance.">
        <Link to="/student/requests" className="button secondary-button">
          Back to Requests
        </Link>
      </PageHeader>

      <div className="form-card" style={{ maxWidth: 560 }}>
        {error && (
          <div className="alert danger" role="alert">
            <i className="fa-solid fa-circle-exclamation" />
            <span>{error}</span>
          </div>
        )}
        <form onSubmit={onSubmit}>
          <div className="form-group">
            <label htmlFor="title">Issue Title</label>
            <input
              id="title"
              type="text"
              placeholder="e.g. Broken Air Conditioner in Room A101"
              required
              minLength={5}
              maxLength={255}
              value={form.title}
              onChange={set('title')}
            />
          </div>

          <div className="grid grid-2" style={{ gap: '1rem', margin: 0 }}>
            <div className="form-group">
              <label htmlFor="type">Type</label>
              <select id="type" value={form.request_type} onChange={set('request_type')}>
                {REQUEST_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {statusLabel(t)}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="priority">Priority</label>
              <select id="priority" value={form.priority} onChange={set('priority')}>
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="location">Location / Room</label>
            <input
              id="location"
              type="text"
              placeholder="e.g. Building A, 2nd Floor, Room A204"
              value={form.location}
              onChange={set('location')}
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              placeholder="Please describe the problem in detail to help staff resolve it quickly..."
              required
              minLength={10}
              value={form.description}
              onChange={set('description')}
            />
          </div>

          <div className="form-group">
            <label htmlFor="phone">Contact Phone (optional)</label>
            <input id="phone" type="tel" maxLength={20} value={form.contact_phone} onChange={set('contact_phone')} />
          </div>

          <div className="form-group">
            <label htmlFor="files">
              <i className="fa-solid fa-paperclip" /> Attachments (optional)
            </label>
            <input id="files" type="file" multiple accept={ALLOWED_UPLOADS} onChange={onFiles} />
            <small className="muted">
              Up to {MAX_FILES} files, {MAX_FILE_MB} MB each: images, PDF, Word or Excel.
            </small>
            {files.length > 0 && (
              <ul className="file-list" aria-label="Selected files">
                {files.map((f) => (
                  <li key={f.name}>
                    <i className="fa-regular fa-file" /> {f.name}{' '}
                    <span className="muted">({f.size > 1024 * 1024 ? `${(f.size / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(f.size / 1024)} KB`})</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
            <button type="submit" className="button" style={{ flex: 1 }} disabled={submitting}>
              {submitting ? 'Submitting...' : 'Submit Request'}
            </button>
            <Link to="/student/requests" className="button secondary-button">
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </>
  )
}
