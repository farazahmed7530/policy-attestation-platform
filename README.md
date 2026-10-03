# Policy Management & Attestation Platform

Publish internal policies, have people attest to them, and prove afterwards **exactly which
words each person agreed to, and when**.

**FastAPI + Next.js.** Runs with no setup — SQLite by default, Postgres by environment variable.

---

## The problem

Every regulated company has to show that staff have read its policies. SOC 2, ISO 27001 and
HIPAA all ask for it. Most organisations answer with a spreadsheet and a shared document, and
that answer falls apart under one question:

> *"This policy was edited in March. Your employee signed in January. What did they actually
> agree to?"*

If the policy document is a living file, nobody can answer. The signature records that
somebody clicked a button next to a document whose contents have since changed. As evidence,
it is worthless.

## The design decision everything else follows from

**A policy version is immutable.**

A *policy* is a name. A *version* is the actual text — frozen, with a SHA-256 content hash.
Editing never mutates a version; it publishes the next one. Attestations reference a version,
not a policy, and they copy the content hash as it stood at signing.

```
Policy "Acceptable Use"
├── v1  hash 4a12f1d9…   ← Amara, Ben and Clara signed this
└── v2  hash 92c3e81f…   ← published afterwards; changes nothing about their signatures
```

So the January signature keeps meaning what it meant in January. The March edit is a new
version and, if you want people to re-affirm, a new campaign.

### Belt and braces

The attestation stores the content hash **as well as** the foreign key. The key says which
version; the hash says what that version said at the moment of signing. If the version row
were ever altered directly in the database, the two would stop agreeing, and the completion
report flags it per person rather than failing silently.

### Whitespace is not a change

Hashing normalises whitespace before digesting. Reflowing a paragraph is not a change of
meaning, and forcing a company to re-collect two hundred signatures because someone fixed
a line break is how a compliance tool gets abandoned.

## What it does

**For the employee** — a list of what they still have to sign, with overdue flagged. They
open the policy, read it, tick the confirmation, attest. Time spent reading is recorded,
because "signed three seconds after opening" is worth knowing.

**For the administrator** — publish new versions with a summary of changes, launch an
attestation campaign against a specific version, and see completion: who signed, when, how
long they read for, whether their hash still matches, and who needs chasing.

## Running it

**Backend** (Python 3.9+)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Seeds five employees, two policies and one live campaign on first run.
Interactive API docs at `http://localhost:8000/docs`.

**Frontend** (Node 18+)

```bash
cd frontend
npm install
npm run dev
```

`http://localhost:3000` — employee view at `/`, administration at `/admin`.
Requests to `/api/*` are proxied to the backend.

**Tests**

```bash
cd backend && .venv/bin/python -m pytest tests -q
```

**Postgres**

```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/policies
```

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/policies` | Policies with their full version history |
| `POST` | `/api/policies` | Create a policy and its first version |
| `POST` | `/api/policies/{id}/versions` | Publish the next version (never edits an old one) |
| `GET` | `/api/campaigns` | Campaigns with the version each targets |
| `POST` | `/api/campaigns` | Launch a campaign against a specific version |
| `POST` | `/api/campaigns/{id}/attest` | Record an attestation |
| `GET` | `/api/campaigns/{id}/completion` | Who signed, integrity check, chase list |
| `GET` | `/api/employees/{id}/outstanding` | What this person still has to sign |

## Tests

Seven tests, aimed at the invariant rather than the CRUD:

```
publishing a new version does not alter the old one
an attestation survives the policy being rewritten   ← the one that matters
republishing identical text is rejected
reformatting is not treated as a change
nobody can attest twice
the outstanding list shrinks when someone signs
completion reports who still needs chasing
```

## A design note on authentication

There is none. The employee selector stands in for an identity provider, and every endpoint
trusts the `employee_id` it is given.

That is a deliberate scope decision, not an oversight — the interesting problem here is
version binding, and bolting on a half-built auth system would add surface without adding
insight. In production this sits behind SSO and the employee comes from the session, never
the request body.

## What I would add next

- **SSO and real sessions**, replacing the selector.
- **Reminder scheduling** — the chase list exists; sending the chase emails does not.
- **Re-attestation campaigns** triggered automatically when a new version publishes.
- **Policy exceptions** — someone granted a documented exemption, with an expiry.
- **PDF export of a completion report**, which is what actually gets handed to an auditor.

## Licence

MIT
