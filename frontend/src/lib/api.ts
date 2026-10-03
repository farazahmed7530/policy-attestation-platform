export interface Employee { id: number; name: string; email: string; department: string }

export interface Version {
  id: number; number: number; body: string; content_hash: string
  summary_of_changes: string; published_at: string
}

export interface Policy { id: number; name: string; category: string; versions: Version[] }

export interface Outstanding {
  campaign_id: number; campaign_name: string; policy_name: string
  version_number: number; due_at: string; overdue: boolean; body: string
}

export interface Completion {
  campaign: string; policy: string; version: number; content_hash: string
  due_at: string; overdue: boolean
  summary: { total: number; signed: number; outstanding: number; completion_percent: number }
  signed: Array<{
    name: string; email: string; department: string; attested_at: string
    seconds_reading: number; hash_matches_version: boolean
  }>
  chase_list: Array<{ name: string; email: string; department: string }>
}

async function call<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    ...options,
  })
  if (!response.ok) throw new Error((await response.json()).detail ?? response.statusText)
  return response.json() as Promise<T>
}

export const getEmployees = () => call<Employee[]>('/employees')
export const getPolicies = () => call<Policy[]>('/policies')
export const getOutstanding = (employeeId: number) =>
  call<Outstanding[]>(`/employees/${employeeId}/outstanding`)
export const getCompletion = (campaignId: number) =>
  call<Completion>(`/campaigns/${campaignId}/completion`)
export const getCampaigns = () =>
  call<Array<{ id: number; name: string; due_at: string; policy_version: Version }>>('/campaigns')

export const attest = (campaignId: number, employeeId: number, secondsReading: number) =>
  call(`/campaigns/${campaignId}/attest`, {
    method: 'POST',
    body: JSON.stringify({ employee_id: employeeId, seconds_reading: secondsReading }),
  })

export const publishVersion = (policyId: number, body: string, summary: string) =>
  call<Version>(`/policies/${policyId}/versions`, {
    method: 'POST',
    body: JSON.stringify({ body, summary_of_changes: summary }),
  })

export const launchCampaign = (versionId: number, name: string, dueInDays: number) =>
  call(`/campaigns`, {
    method: 'POST',
    body: JSON.stringify({ policy_version_id: versionId, name, due_in_days: dueInDays }),
  })
