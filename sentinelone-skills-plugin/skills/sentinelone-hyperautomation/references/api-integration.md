# API Integration Reference

## Environment Variables

Two environment variables drive all API interactions with the console:

| Variable | Contains |
|----------|----------|
| `S1_CONSOLE_URL` | Full console base URL, e.g. `https://usea1-acme.sentinelone.net` |
| `S1_CONSOLE_API_TOKEN` | Console User (personal) API token (generated in Settings → Users → API Token) |

**Always validate these before use.** Run the two-step check below — if either step fails,
stop and tell the user what went wrong before proceeding with any workflow operation.

### Step 1 — Validate `S1_CONSOLE_URL` (no auth required)

```
GET {S1_CONSOLE_URL}/web/api/v2.1/system
```

This endpoint requires no authentication and always returns `200` with `{"data": {"health": "ok"}}`
when the console is reachable. A non-200 response or a network error means `S1_CONSOLE_URL` is wrong
or the console is unreachable.

### Step 2 — Validate `S1_CONSOLE_API_TOKEN` (auth + permission check)

```
GET {S1_CONSOLE_URL}/web/api/v2.1/hyper-automate/api/public/workflows?limit=1
Authorization: ApiToken {S1_CONSOLE_API_TOKEN}
```

A `200` response confirms the token is valid and has `Hyper Automate.view` permission.
Failure responses:
- `401` — token is missing or expired
- `403` — token lacks `Hyper Automate.view` permission

```javascript
// Validation helper
async function validateCredentials(apiUrl, apiToken) {
  // Step 1: URL check
  const sysRes = await fetch(`${apiUrl}/web/api/v2.1/system`);
  if (!sysRes.ok) throw new Error(`Console unreachable (${sysRes.status}). Check S1_CONSOLE_URL.`);
  const { data: { health } } = await sysRes.json();
  if (health !== 'ok') throw new Error(`Console health: ${health}`);

  // Step 2: Token check
  const authRes = await fetch(
    `${apiUrl}/web/api/v2.1/hyper-automate/api/public/workflows?limit=1`,
    { headers: { "Authorization": `ApiToken ${apiToken}` } }
  );
  if (authRes.status === 401) throw new Error('S1_CONSOLE_API_TOKEN is invalid or expired.');
  if (authRes.status === 403) throw new Error('S1_CONSOLE_API_TOKEN lacks Hyper Automate.view permission.');
  if (!authRes.ok) throw new Error(`Token check failed (${authRes.status})`);
}
```

---

## Overview

The Hyperautomation API allows programmatic management of workflows: import, export, activate,
deactivate, trigger, list, and monitor executions.

**Base URL**: `https://<your-console-url>/web/api/v2.1/`
**Authentication**: `Authorization: ApiToken <token>` header (Console User personal API token)
**Content-Type**: `application/json` for POST requests

All POST request bodies follow the S1 envelope pattern:
```json
{ "data": { /* payload */ } }
```

All scope-filtering query params are **plural**: `accountIds`, `siteIds`, `groupIds`.

---

## Endpoint Reference

### 1. Import Workflow
`POST /hyper-automate/api/public/workflow-import-export/import`

**Permission**: `Hyper Automate.workflowsCreateEdit`

**Query params** (at least one required to set scope):
| Param | Type | Description |
|-------|------|-------------|
| `accountIds` | string | Comma-separated account IDs |
| `siteIds` | string | Comma-separated site IDs |
| `groupIds` | string | Comma-separated group IDs |

**Body**:
```json
{
  "data": {
    "name": "Workflow Name",           // required, max 255 chars
    "description": "optional text",    // optional, max 2048 chars
    "actions": [ /* action objects */ ]
  }
}
```

**Responses**:
- `200` — Successful
- `422` — Validation error (malformed JSON, wrong field types, etc.)

**Response body** (key fields on success):
```json
{
  "data": {
    "id": "<workflow_id>",
    "version_id": "<version_id>",
    "name": "Workflow Name",
    "state": "...",
    "lifecycle_state": "...",
    "scope_id": "...",
    "scope_level": "...",
    "created_at": "...",
    "created_by_user": { "id": "...", "email": "...", "name": "..." },
    "version_count": 1
  }
}
```

**Notes**:
- Imported workflows are created as **Private Draft**, visible only to the owner of the token
  used for import.
- **Use a Console User (personal) token, not a Service User token.** The Hyperautomation API
  has no endpoint to change workflow ownership or share a workflow programmatically. A workflow
  imported with a Service User token would be owned by that service account and invisible to
  human users in the console UI.
- After import, the workflow must be activated before it runs.

---

### 2. Batch Import Workflows
`POST /hyper-automate/api/public/workflow-import-export/import/batch`

**Permission**: `Hyper Automate.workflowsCreateEdit`

**Query params**: same as single import (`accountIds`, `siteIds`, `groupIds`)

Accepts multiple workflow objects. Use for bulk deployments.

**Body params** (multipart/form-data):
- `file` (required) — the batch import file
- `filter` (required) — scope filter string
- `body` (optional) — `{ "data": {...}, "filter": {"type": "JsonPath"|"JsonSchema", "value": "..."} }`

**Responses**: `201` success, `422` validation error.

---

### 3. Export Workflow (single)
`GET /hyper-automate/api/public/workflow-import-export/export/{workflow_id}/{version_id}`

**Permission**: `Hyper Automate.workflowsExport`

Returns the full workflow JSON for re-import or inspection.

**Finding IDs**: From the console URL when viewing a workflow:
`https://<console>/hyperautomation/workflow/<workflow_id>/<version_id>`

---

### 4. Batch Export Workflows
`GET /hyper-automate/api/public/workflow-import-export/export`

**Permission**: `Hyper Automate.workflowsExport`

**Query params** (all optional — combine to filter):
| Param | Type | Description |
|-------|------|-------------|
| `workflow_ids` | string | Comma-separated workflow IDs |
| `integrations` | string | Filter by integration name |
| `trigger_types` | string | Filter by trigger type |
| `core_actions` | string | Filter by core action type |
| `states` | string | Filter by workflow state |
| `name__contains` | string | Name substring match |
| `name__eq` | string | Exact name match |
| `tags` | string | Filter by tags |
| `accountIds` | string | Scope to account(s) |
| `siteIds` | string | Scope to site(s) |
| `groupIds` | string | Scope to group(s) |

---

### 5. List Workflows
`GET /hyper-automate/api/public/workflows`

**Permission**: `Hyper Automate.view`

**Query params**:
| Param | Type | Description |
|-------|------|-------------|
| `integrations` | string | Filter by integration |
| `trigger_types` | string | Filter by trigger type |
| `core_actions` | string | Filter by action type |
| `states` | string | Filter by state (e.g. `active`, `inactive`) |
| `name__contains` | string | Name substring |
| `name__eq` | string | Exact name match |
| `description__contains` | string | Description substring |
| `is_snippet` | boolean | Filter snippets only |
| `workflow_ids` | string | Comma-separated IDs |
| `tags` | string | Filter by tag |
| `oversight` | boolean | Filter oversight workflows |
| `limit` | integer | Page size |
| `skip` | integer | Offset for pagination |
| `sortBy` | string | Field to sort by |
| `sortOrder` | string | `asc` or `desc` |
| `accountIds` | string | Scope to account(s) |
| `siteIds` | string | Scope to site(s) |
| `groupIds` | string | Scope to group(s) |

---

### 6. List Workflow Versions
`GET /hyper-automate/api/public/workflows/versions/list/{workflow_id}`

**Permission**: `Hyper Automate.view`

Returns all versions (draft, active, inactive) for a given workflow.

**Query params**: `accountIds`, `siteIds`, `groupIds` for scope.

---

### 7. Activate a Workflow Version
`POST /hyper-automate/api/public/workflows/{workflow_id}/{version_id}/activation`

**Permission**: `Hyper Automate.workflowsActivateDeactivate`

**Query params**: `accountIds`, `siteIds`, `groupIds` for scope.

**Body** (all fields optional):
```json
{
  "data": {
    "version_description": "optional version note",
    "timeout": 86400,              // seconds, default 86400 (24h)
    "daily_max_executions": 0,     // 0 = unlimited
    "max_concurrency": 0,          // 0 = unlimited
    "notify_to": ["user@example.com"],
    "time_saved": null,            // integer (minutes saved per run)
    "time_saved_unit": null,       // unit string
    "is_snippet": false,
    "dimensions": { "height": 0, "width": 0 }  // canvas dimensions (optional)
  }
}
```

**Responses**: `204` success (no body), `422` validation error.

---

### 8. Deactivate a Workflow
`POST /hyper-automate/api/public/workflows/{workflow_id}/deactivate`

**Permission**: `Hyper Automate.workflowsActivateDeactivate`

**Query params**: `version_id` (optional), `accountIds`, `siteIds`, `groupIds`.

**Body**: `{ "data": null }` or empty `{}`

**Responses**: `204` success (no body), `422` validation error.

---

### 9. Trigger a Manual Workflow
`POST /hyper-automate/api/public/workflow-execution/manual/{workflow_id}/{version_id}`

**Permission**: `Hyper Automate.workflowsRun`

**Query params**: `accountIds`, `siteIds`, `groupIds` for scope.

**Body** (all fields optional):
```json
{
  "data": {
    "payload": "optional string payload passed to the workflow",
    "singularity_response_event_id": null,
    "singularity_response_event_type": null,
    "is_downstream_execution": false,
    "parent_execution_id": null
  }
}
```

**Responses**: `201` success, `422` validation error.

---

### 10. List Workflow Executions
`GET /hyper-automate/api/public/workflow-execution`

**Permission**: `Hyper Automate.view`

**Query params**:
| Param | Type | Description |
|-------|------|-------------|
| `workflow_id` | string | Filter by specific workflow |
| `trigger_types` | string | Filter by trigger type |
| `states` | string | Filter by execution state |
| `workflow_name__contains` | string | Workflow name substring |
| `is_snippet` | boolean | Snippets only |
| `tags` | string | Filter by tag |
| `integrations` | string | Filter by integration |
| `created_at__gte` | datetime | From timestamp |
| `created_at__lt` | datetime | To timestamp |
| `limit` | integer | Page size |
| `skip` | integer | Offset for pagination |
| `sortBy` | string | Sort field |
| `sortOrder` | string | `asc` or `desc` |
| `accountIds` | string | Scope to account(s) |
| `siteIds` | string | Scope to site(s) |
| `groupIds` | string | Scope to group(s) |

---

**Response** includes `data` (array) and `pagination: { nextCursor, totalItems }`.

---

### 11. Get Execution Detail
`GET /hyper-automate/api/public/workflow-execution/{workflow_execution_id}`

**Permission**: `Hyper Automate.view`

**Response fields**:
- Required: `id`, `mgmt_id`, `scope_id`, `singularity_response_event_id`, `version_id`, `workflow_id`
- Optional: `created_at`, `duration`, `error_actions` (array), `executed_actions` (integer),
  `scope_level` (enum), `singularity_response_event_type` (enum), `state` (enum),
  `time_saved` (number), `updated_at`, `workflow_state` (enum)

---

### 12. Enable Agent PNA for Hyperautomation
`POST /agents/enable-hyper-automation-pna`

**Permission**: `Endpoints.edit` + `Hyper Automate.connectionsEdit`

Enables the Private Network Access agent integration for use in Hyperautomation connections.

---

### 13. Disable Agent PNA for Hyperautomation
`POST /agents/disable-hyper-automation-pna`

**Permission**: `Endpoints.edit` + `Hyper Automate.connectionsEdit`

---

### 14. Evaluate Expression
`POST /hyper-automate/api/public/workflow-action-expressions/{base_action_id}/evaluate-expression`

Evaluates a Hyperautomation expression string against a given context.

**Body**:
```json
{
  "data": {
    "expression": "{{action.some_field | upper}}",   // required
    "loop_context": {}                                // optional
  }
}
```

**Responses**: `200` success, `422` validation error.

---

### 15. Expression Breakdown
`POST /hyper-automate/api/public/workflow-action-expressions/{base_action_id}/expression-breakdown`

Same body as Evaluate Expression. Returns a parsed breakdown of expression components.

---

## Common Integration Flow

### Deploy a new workflow end-to-end

Uses the `S1_CONSOLE_URL` and `S1_CONSOLE_API_TOKEN` environment variables. Always call `validateCredentials()`
(defined above) before any workflow operation.

```javascript
const apiUrl   = process.env.S1_CONSOLE_URL;    // e.g. https://usea1-acme.sentinelone.net
const apiToken = process.env.S1_CONSOLE_API_TOKEN;  // Service User API token
const siteId   = process.env.SITE_ID;    // optional — scope to a specific site

const base = `${apiUrl}/web/api/v2.1/hyper-automate/api/public`;
const headers = {
  "Authorization": `ApiToken ${apiToken}`,
  "Content-Type": "application/json"
};

// 0. Validate credentials first
await validateCredentials(apiUrl, apiToken);

// 1. Import
const importRes = await fetch(`${base}/workflow-import-export/import?siteIds=${siteId}`, {
  method: "POST",
  headers,
  body: JSON.stringify({ data: workflowJson })
});
const importData = await importRes.json();
const { id: workflowId, version_id: versionId } = importData.data;

// 2. Activate
await fetch(`${base}/workflows/${workflowId}/${versionId}/activation?siteIds=${siteId}`, {
  method: "POST",
  headers,
  body: JSON.stringify({ data: {} })
});
// Note: activation returns 204 (no body)

// 3. Trigger (if manual workflow)
const triggerRes = await fetch(
  `${base}/workflow-execution/manual/${workflowId}/${versionId}?siteIds=${siteId}`,
  {
    method: "POST",
    headers,
    body: JSON.stringify({ data: { payload: "optional" } })
  }
);
// triggerRes.status === 201 on success
```

---

## Error Reference

| HTTP | Meaning | Common causes |
|------|---------|---------------|
| `200` / `201` / `204` | Success | — |
| `400` | Bad request | Malformed body, invalid field value |
| `401` | Unauthorized | Missing or expired API token |
| `403` | Forbidden | Token lacks required permission |
| `404` | Not found | Wrong workflow/version ID |
| `422` | Validation error | Schema mismatch, duplicate `export_id`, invalid `type` value, missing required field |

Common import `422` messages:
- `"Invalid action type"` — typo in `type` field
- `"export_id conflict"` — duplicate `export_id` values in actions array
- `"Invalid target"` — `connected_to.target` references non-existent `export_id`
- `"Missing required field"` — required field absent from data object

---

## Console URL Formats

| Region | Pattern |
|--------|---------|
| US East 1 | `https://usea1-<tenant>.sentinelone.net` |
| EU West 1 | `https://euw1-<tenant>.sentinelone.net` |
| US East 2 | `https://usea2-<tenant>.sentinelone.net` |

**Token location**: Settings → Users → [your user] → API Token → Generate.
Use a **Console User (personal) token**. Do not use a Service User token — the Hyperautomation
API provides no endpoint to share or transfer workflow ownership, so a workflow imported with
a Service User token would be owned by that service account and invisible to human users.
