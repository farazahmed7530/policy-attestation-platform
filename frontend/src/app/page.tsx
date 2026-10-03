'use client'

import { useEffect, useState } from 'react'

import { attest, getEmployees, getOutstanding, type Employee, type Outstanding } from '@/lib/api'

export default function EmployeeView() {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [employeeId, setEmployeeId] = useState<number | null>(null)
  const [items, setItems] = useState<Outstanding[]>([])
  const [open, setOpen] = useState<Outstanding | null>(null)
  const [openedAt, setOpenedAt] = useState<number>(0)
  const [confirmed, setConfirmed] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    getEmployees().then((people) => {
      setEmployees(people)
      setEmployeeId(people[0]?.id ?? null)
    })
  }, [])

  const refresh = (id: number) => getOutstanding(id).then(setItems)
  useEffect(() => {
    if (employeeId) refresh(employeeId)
  }, [employeeId])

  const openPolicy = (item: Outstanding) => {
    setOpen(item)
    setOpenedAt(Date.now())
    setConfirmed(false)
    setMessage(null)
  }

  const submit = async () => {
    if (!open || !employeeId) return
    const seconds = Math.round((Date.now() - openedAt) / 1000)
    await attest(open.campaign_id, employeeId, seconds)
    setMessage(`Attested to ${open.policy_name} v${open.version_number}.`)
    setOpen(null)
    refresh(employeeId)
  }

  return (
    <>
      <header>
        <h1>Policies awaiting your attestation</h1>
        <label className="who">
          Signed in as
          <select
            value={employeeId ?? ''}
            onChange={(event) => setEmployeeId(Number(event.target.value))}
          >
            {employees.map((employee) => (
              <option key={employee.id} value={employee.id}>
                {employee.name} · {employee.department}
              </option>
            ))}
          </select>
        </label>
        <p className="muted">
          No authentication in this project — the selector stands in for an identity provider.
        </p>
      </header>

      {message && <p className="banner ok">{message}</p>}

      {items.length === 0 ? (
        <p className="muted">Nothing outstanding. Everything assigned to you is signed.</p>
      ) : (
        items.map((item) => (
          <article key={item.campaign_id} className="card">
            <div className="card-head">
              <div>
                <h3>{item.policy_name}</h3>
                <p className="muted">
                  {item.campaign_name} · version {item.version_number}
                </p>
              </div>
              <span className={`pill ${item.overdue ? 'bad' : 'warn'}`}>
                {item.overdue ? 'Overdue' : `Due ${new Date(item.due_at).toLocaleDateString()}`}
              </span>
            </div>
            <button onClick={() => openPolicy(item)}>Read and attest</button>
          </article>
        ))
      )}

      {open && (
        <div className="reader">
          <h2>
            {open.policy_name} <span className="muted">version {open.version_number}</span>
          </h2>
          <div className="body">
            {open.body.split('\n\n').map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
          </div>

          <label className="confirm">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
            I have read this policy and agree to follow it.
          </label>

          <div className="actions">
            <button disabled={!confirmed} onClick={submit}>Attest</button>
            <button className="ghost" onClick={() => setOpen(null)}>Cancel</button>
          </div>
        </div>
      )}
    </>
  )
}
