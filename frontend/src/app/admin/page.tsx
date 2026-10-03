'use client'

import { useEffect, useState } from 'react'

import {
  getCampaigns, getCompletion, getPolicies, launchCampaign, publishVersion,
  type Completion, type Policy, type Version,
} from '@/lib/api'

interface CampaignRow { id: number; name: string; due_at: string; policy_version: Version }

export default function Admin() {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [campaigns, setCampaigns] = useState<CampaignRow[]>([])
  const [completion, setCompletion] = useState<Completion | null>(null)
  const [editing, setEditing] = useState<Policy | null>(null)
  const [draft, setDraft] = useState('')
  const [summary, setSummary] = useState('')
  const [error, setError] = useState<string | null>(null)

  const refresh = async () => {
    setPolicies(await getPolicies())
    setCampaigns(await getCampaigns())
  }
  useEffect(() => { refresh() }, [])

  const startEdit = (policy: Policy) => {
    setEditing(policy)
    setDraft(policy.versions.at(-1)?.body ?? '')
    setSummary('')
    setError(null)
  }

  const publish = async () => {
    if (!editing) return
    try {
      await publishVersion(editing.id, draft, summary)
      setEditing(null)
      await refresh()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const launch = async (version: Version, policyName: string) => {
    await launchCampaign(version.id, `${policyName} v${version.number} attestation`, 14)
    await refresh()
  }

  return (
    <>
      <header>
        <h1>Administration</h1>
        <p className="muted">
          Publishing a new version never alters an older one. Attestations stay bound to the
          exact text that was signed.
        </p>
      </header>

      <h2>Policies</h2>
      {policies.map((policy) => (
        <article key={policy.id} className="card">
          <div className="card-head">
            <div>
              <h3>{policy.name}</h3>
              <p className="muted">{policy.category} · {policy.versions.length} version(s)</p>
            </div>
            <button className="ghost" onClick={() => startEdit(policy)}>Publish new version</button>
          </div>

          <table>
            <thead>
              <tr><th>Version</th><th>Published</th><th>Changes</th><th>Hash</th><th></th></tr>
            </thead>
            <tbody>
              {policy.versions.map((version) => (
                <tr key={version.id}>
                  <td>v{version.number}</td>
                  <td>{new Date(version.published_at).toLocaleDateString()}</td>
                  <td>{version.summary_of_changes || '—'}</td>
                  <td><code>{version.content_hash.slice(0, 10)}…</code></td>
                  <td>
                    <button className="small" onClick={() => launch(version, policy.name)}>
                      Launch campaign
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      ))}

      {editing && (
        <div className="reader">
          <h2>New version of {editing.name}</h2>
          <textarea value={draft} onChange={(event) => setDraft(event.target.value)} rows={14} />
          <input
            type="text"
            placeholder="What changed, in one line"
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
          />
          {error && <p className="banner bad">{error}</p>}
          <div className="actions">
            <button onClick={publish}>Publish</button>
            <button className="ghost" onClick={() => setEditing(null)}>Cancel</button>
          </div>
        </div>
      )}

      <h2>Campaigns</h2>
      {campaigns.map((campaign) => (
        <article key={campaign.id} className="card">
          <div className="card-head">
            <div>
              <h3>{campaign.name}</h3>
              <p className="muted">Due {new Date(campaign.due_at).toLocaleDateString()}</p>
            </div>
            <button
              className="ghost"
              onClick={async () => setCompletion(await getCompletion(campaign.id))}
            >
              View completion
            </button>
          </div>
        </article>
      ))}

      {completion && (
        <div className="reader">
          <h2>{completion.campaign}</h2>
          <p className="muted">
            {completion.policy} v{completion.version} · hash{' '}
            <code>{completion.content_hash.slice(0, 16)}…</code>
          </p>

          <div className="stats">
            <div className="stat">
              <span>{completion.summary.completion_percent}%</span><label>Complete</label>
            </div>
            <div className="stat"><span>{completion.summary.signed}</span><label>Signed</label></div>
            <div className="stat">
              <span>{completion.summary.outstanding}</span><label>Outstanding</label>
            </div>
          </div>

          <h3>Signed</h3>
          {completion.signed.length === 0 ? <p className="muted">Nobody yet.</p> : (
            <table>
              <thead>
                <tr><th>Name</th><th>When</th><th>Time reading</th><th>Integrity</th></tr>
              </thead>
              <tbody>
                {completion.signed.map((row) => (
                  <tr key={row.email}>
                    <td>{row.name}</td>
                    <td>{new Date(row.attested_at).toLocaleString()}</td>
                    <td>{row.seconds_reading}s</td>
                    <td>
                      <span className={`pill ${row.hash_matches_version ? 'ok' : 'bad'}`}>
                        {row.hash_matches_version ? 'hash matches' : 'VERSION ALTERED'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h3>Still to chase</h3>
          {completion.chase_list.length === 0 ? <p className="muted">Nobody — everyone signed.</p> : (
            <ul>
              {completion.chase_list.map((person) => (
                <li key={person.email}>{person.name} <span className="muted">· {person.email}</span></li>
              ))}
            </ul>
          )}

          <div className="actions">
            <button className="ghost" onClick={() => setCompletion(null)}>Close</button>
          </div>
        </div>
      )}
    </>
  )
}
