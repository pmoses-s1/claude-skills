# Building Blocks Reference

Complete data payloads for every action type in SentinelOne Hyperautomation.

---

## TRIGGERS

### Manual Trigger (static — no user input)
```json
{
  "type": "manual_trigger",
  "tag": "core_action",
  "connection_id": null,
  "connection_name": null,
  "use_connection_name": false,
  "integration_id": null,
  "data": {
    "name": "Manual Trigger",
    "action_type": "manual_trigger",
    "trigger_type": "static",
    "dynamic_properties": {},
    "static_payload": "{}"
  },
  "state": "active",
  "description": null,
  "client_data": { "position": {"x": 0, "y": 0}, "dimensions": {"width": 256, "height": 100}, "collapsed": false },
  "snippet_workflow_id": null,
  "snippet_version_id": null
}
```

### Manual Trigger (dynamic — prompts user for input)
```json
{
  "type": "manual_trigger",
  "tag": "core_action",
  "connection_id": null,
  "connection_name": null,
  "use_connection_name": false,
  "integration_id": null,
  "data": {
    "name": "Manual Trigger",
    "action_type": "manual_trigger",
    "trigger_type": "dynamic",
    "dynamic_properties": {
      "AssetName": {
        "title": "",
        "description": "Enter the asset name to investigate",
        "index": 0,
        "type": "text",
        "validation": { "required": true, "min_length": null, "max_length": null }
      }
    },
    "static_payload": "{}"
  }
}
```
Input types: `"text"`, `"number"`, `"json"`, `"email"`, `"date"`, `"time"`, `"checkbox"`
Reference: `{{manual-trigger.data.AssetName}}`

### Scheduled Trigger
```json
{
  "type": "scheduled_trigger",
  "tag": "core_action",
  "data": {
    "name": "Scheduled Trigger",
    "action_type": "scheduled_trigger",
    "schedule_method": "weekly",
    "until": null,
    "max_runs": 1,
    "schedule_value": [
      {
        "schedule_method": "weekly",
        "minute": 0,
        "hour": 18,
        "tz": "Europe/Rome",
        "week_day": 2
      }
    ],
    "start_at": null,
    "start_at_method": "immediately",
    "ends_on": "never"
  }
}
```
`week_day`: 0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday
`schedule_method` options: `"daily"`, `"weekly"`, `"monthly"`, `"interval"`

### HTTP Trigger (Webhook)
```json
{
  "type": "http_trigger",
  "tag": "core_action",
  "data": {
    "name": "HTTP Trigger",
    "action_type": "http_trigger",
    "url_identifier": "97ab0444-6f32-493b-b761-30970291414d",
    "supported_methods": { "get": true, "post": true },
    "response_status_code": 200,
    "response_body": "{\"Status\": \"OK\"}",
    "response_content_type": "application/json",
    "response_headers": {},
    "include_headers": true,
    "allow_empty_request_body": true
  }
}
```
Reference incoming data: `{{http-trigger.body.someField}}`

### Singularity Response Trigger
```json
{
  "type": "singularity_response_trigger",
  "tag": "core_action",
  "data": {
    "name": "Singularity Response Trigger",
    "action_type": "singularity_response_trigger",
    "filter_groups": [
      {
        "condition": {
          "operator": "and",
          "conditions": [
            {
              "input_value": "detectionSource.product",
              "compared_value": "EDR",
              "comparison_operator": "equals"
            }
          ]
        },
        "is_disabled": false,
        "run_automatically": false,
        "event_type": "alert",
        "event_subtypes": ["CREATE"]
      }
    ]
  }
}
```
Common trigger data references:
- `{{singularity-response-trigger.data.id}}` — alert ID
- `{{singularity-response-trigger.data.name}}` — alert name
- `{{singularity-response-trigger.data.severity}}` — severity
- `{{singularity-response-trigger.data.asset.name}}` — asset/hostname
- `{{singularity-response-trigger.data.asset.agentUuid}}` — agent UUID
- `{{singularity-response-trigger.data.process.file.sha1}}` — file SHA1
- `{{singularity-response-trigger.data.process.file.sha256}}` — file SHA256
- `{{singularity-response-trigger.data.detectionSource.product}}` — product (EDR, STAR, CWS...)
- `{{singularity-response-trigger.data.externalId}}` — threat external ID
- `{{singularity-response-trigger.data.indicators[0].id}}` — first indicator ID
- `{{singularity-response-trigger.data.indicators[0].eventTime}}` — first indicator event time

### Email Trigger
```json
{
  "type": "email_trigger",
  "tag": "core_action",
  "data": {
    "name": "Email Trigger",
    "action_type": "email_trigger"
    /* connection details configured in console */
  }
}
```
Reference: `{{email-trigger.body}}`, `{{email-trigger.subject}}`

---

## CORE ACTIONS

### Variable
```json
{
  "type": "variable",
  "tag": "core_action",
  "data": {
    "name": "My Variables",
    "action_type": "variable",
    "variables": [
      {
        "name": "myVar",
        "value": "someValue or {{expression}}",
        "is_secret": false
      },
      {
        "name": "emptyArray",
        "value": "[]",
        "is_secret": false
      }
    ],
    "variables_scope": "local"
  }
}
```
`variables_scope`: `"local"` (default) or `"global"`
Reference: `{{local_var.myVar}}` or `{{global_var.myVar}}`

> **HARD RULE — one variable per action when referencing other local variables**
>
> All entries in a single Variable action's `variables` array are evaluated simultaneously, not
> sequentially. If variable B's value references `{{local_var.A}}` and A is defined in the same
> action, A will be unresolved at evaluation time and B will silently receive an empty/null value.
>
> **Rule**: if any variable's value references a local variable defined elsewhere in the same
> workflow, give each such variable its own dedicated Variable action.
>
> ❌ **Wrong** — `fullPath` silently resolves to empty because `baseUrl` is not yet available:
> ```json
> {
>   "name": "Set Vars",
>   "action_type": "variable",
>   "variables": [
>     { "name": "baseUrl", "value": "https://api.example.com", "is_secret": false },
>     { "name": "fullPath", "value": "{{local_var.baseUrl}}/v1/alerts", "is_secret": false }
>   ],
>   "variables_scope": "local"
> }
> ```
>
> ✅ **Right** — two separate actions, each with one variable:
> ```json
> {
>   "name": "Set Base URL",
>   "action_type": "variable",
>   "variables": [
>     { "name": "baseUrl", "value": "https://api.example.com", "is_secret": false }
>   ],
>   "variables_scope": "local"
> }
> ```
> *(connected_to → next action)*
> ```json
> {
>   "name": "Set Full Path",
>   "action_type": "variable",
>   "variables": [
>     { "name": "fullPath", "value": "{{local_var.baseUrl}}/v1/alerts", "is_secret": false }
>   ],
>   "variables_scope": "local"
> }
> ```
>
> **Exception**: grouping multiple variables in a single action is fine when none of their values
> reference each other or any other `local_var` defined in this workflow (e.g., all values are
> literals, trigger fields, or external action outputs).

### Loop (dynamic — iterates over an array)
```json
{
  "type": "loop",
  "tag": "core_action",
  "data": {
    "name": "Loop Items",
    "action_type": "loop",
    "loop_type": "dynamic",
    "number_of_iterations": 5,
    "object_to_iterate": "{{local_var.myArray}}",
    "is_parallel": false
  }
}
```
Current item reference: `{{loop-items.item}}` or `{{loop-items.item.fieldName}}`
Current index: `{{loop-items.index}}`
Connect loop to first inner action using `custom_handle: "inner"`.
Actions inside the loop have `"parent_action": <loop_export_id>`.

### Loop (while — indefinite, until Break)
```json
{
  "type": "loop",
  "tag": "core_action",
  "data": {
    "name": "While Loop",
    "action_type": "loop",
    "loop_type": "while",
    "number_of_iterations": 1,
    "object_to_iterate": null,
    "is_parallel": false
  }
}
```

### Loop (fixed — runs N times)
```json
{
  "type": "loop",
  "tag": "core_action",
  "data": {
    "name": "Fixed Loop",
    "action_type": "loop",
    "loop_type": "fixed",
    "number_of_iterations": 10,
    "object_to_iterate": null,
    "is_parallel": false
  }
}
```

### Condition
See workflow-schema.md for simple vs. multi style details.
```json
{
  "type": "condition",
  "tag": "core_action",
  "data": {
    "name": "Is Success",
    "action_type": "condition",
    "condition_type": "multi",
    "condition": null,
    "conditions": [
      {
        "input_value": "{{my-action.status_code}}",
        "compared_value": "200",
        "comparison_operator": "equals"
      }
    ],
    "conditions_relationship": "and"
  }
}
```
Operators: `"equals"`, `"not_equals"`, `"contains"`, `"not_contains"`, `"greater_than"`,
`"greater_than_or_equals"`, `"less_than"`, `"less_than_or_equals"`, `"in"`, `"is_empty"`, `"is_not_empty"`

### Delay
```json
{
  "type": "delay",
  "tag": "core_action",
  "data": {
    "name": "Delay",
    "action_type": "delay",
    "time_unit": "seconds",
    "value": 20
  }
}
```
`time_unit` options: `"seconds"`, `"minutes"`, `"hours"`

### Break Loop
```json
{
  "type": "break_loop",
  "tag": "core_action",
  "data": {
    "name": "Break Loop",
    "action_type": "break_loop"
  }
}
```
Must have `"parent_action": <loop_export_id>`. `"connected_to": []`.

### Send Email
```json
{
  "type": "send_email",
  "tag": "core_action",
  "data": {
    "name": "Send Email",
    "action_type": "send_email",
    "subject": "Alert: {{singularity-response-trigger.data.name}}",
    "to": ["recipient@example.com"],
    "cc": [],
    "bcc": [],
    "reply_to": [],
    "mime_type": "text/plain",
    "body": "Alert details: {{singularity-response-trigger.data.description}}",
    "attachments": [],
    "continue_on_fail": false
  }
}
```
`mime_type`: `"text/plain"` or `"text/html"`
For attachments: `"attachments": [{"name": "file.zip", "content": "{{Function.COMPRESS(...)}}"}]`

### HTTP Request (core — no integration)
```json
{
  "type": "http_request",
  "tag": "core_action",
  "connection_id": null,
  "connection_name": null,
  "use_connection_name": false,
  "integration_id": null,
  "data": {
    "name": "Retrieve TOR Exit Nodes",
    "action_type": "http_request",
    "public_action_id": null,
    "method": "get",
    "url": "https://raw.githubusercontent.com/example/file.txt",
    "url_path": null,
    "url_prefix": null,
    "payload": null,
    "parameters": [],
    "retry_on_status_code": null,
    "retry_on_status_codes": [],
    "ssl_verification": true,
    "timeout": 30,
    "headers": { "Content-Type": "application/json" },
    "use_authentication_data": true,
    "use_proxy": false,
    "proxy_user": null,
    "proxy_password": null,
    "proxy_host": null,
    "proxy_port": null,
    "redirect_follow": true,
    "continue_on_fail": false
  }
}
```
`method`: `"get"`, `"post"`, `"put"`, `"patch"`, `"delete"`
Reference response: `{{action-slug.body}}`, `{{action-slug.status_code}}`

### HTTP Request (integration-backed)
Same as above but:
- `"tag": "integration"`
- `"connection_id": null` (set to null for import; user configures)
- `"connection_name": ""`
- `"integration_id": null` (set to null for import)
- `"public_action_id": "<uuid>"` (from the integration's action catalog)
- URL uses `{{Connection.protocol}}{{Connection.url}}/path/to/api`

When generating workflows for import, always set `connection_id`, `connection_name`,
and `integration_id` to null/"" — these are resolved from the user's configured connections.

### URL pattern for integration-backed SentinelOne actions:
```
"url": "{{Connection.protocol}}{{Connection.url}}/web/api/v2.1/<endpoint>"
```

### Snippet
```json
{
  "type": "snippet",
  "tag": "core_action",
  "data": {
    "name": "My Snippet",
    "action_type": "snippet"
  },
  "snippet_workflow_id": null,
  "snippet_version_id": null
}
```
Snippets are reusable groups of actions. Connect using `custom_handle: "inner"`.

### Create Interaction
```json
{
  "type": "create_interaction",
  "tag": "core_action",
  "data": {
    "name": "Create Interaction",
    "action_type": "create_interaction",
    "interactions": [
      { "label": "1 hour", "value": "1 hour" },
      { "label": "4 hours", "value": "4 hours" },
      { "label": "24 hours", "value": "24 hours" }
    ]
  }
}
```
Reference interaction URLs: `{{create-interaction.interaction_url.1 hour}}`
Reference interaction ID: `{{create-interaction.interaction_id}}`

### Wait for Interaction
```json
{
  "type": "wait_for_interaction",
  "tag": "core_action",
  "data": {
    "name": "Wait for Interaction",
    "action_type": "wait_for_interaction",
    "interaction_id": "{{create-interaction.interaction_id}}",
    "time_unit": "hours",
    "value": 24
  }
}
```

### Wait for Slack
```json
{
  "type": "wait_for_slack",
  "tag": "core_action",
  "data": {
    "name": "Wait for Slack",
    "action_type": "wait_for_slack",
    "message_ts": "{{post-alert.body.ts}}",
    "time_unit": "days",
    "value": 5
  }
}
```
Reference response: `{{wait-for-slack.body}}`, `{{wait-for-slack.timeout}}`,
`{{wait-for-slack.body.actions[0].value}}`

---

## COMMON PATTERNS

### Success/Fail branch pattern (used throughout M365 workflows)
```
Action → Condition (Is Success, checks status_code) → 
  TRUE: Variable (success note) → HTTP (add note)
  FALSE: Variable (fail note) → HTTP (add note)
```

### Add Note to Unified Alert (GraphQL mutation — most common pattern)
```json
{
  "name": "Add Note to Alert",
  "action_type": "http_request",
  "method": "post",
  "url": "{{Connection.protocol}}{{Connection.url}}/web/api/v2.1/unifiedalerts/graphql",
  "payload": "{\n  \"query\": \"mutation AddNoteToAlert($note:String!, $id:String!) { alertTriggerActions(actions:[{ id:\\\"S1/alert/addNote\\\", payload:{ note:{ value:$note }}}], filter:{ or:[{ and:[{ fieldId:\\\"id\\\", stringEqual:{ value:$id } }]}]}) { ... on ActionsTriggered { actions { actionId } } } }\",\n  \"variables\": {\n    \"id\": \"{{singularity-response-trigger.data.id}}\",\n    \"note\": \"{{local_var.note_markdown}}\"\n  }\n}"
}
```

### SDL Query (AI SIEM Singularity Data Lake)
```json
{
  "method": "post",
  "url": "{{Connection.protocol}}{{Connection.url}}/sdl/api/query",
  "payload": "{\n  \"filter\": \"dataSource.name = 'indicator' and metadata.uid = '{{singularity-response-trigger.data.indicators[0].id}}'\",\n  \"startTime\": \"{{singularity-response-trigger.data.indicators[0].eventTime}}\",\n  \"endTime\": \"{{Function.DELTA(singularity-response-trigger.data.indicators[0].eventTime,-0.1)}}\"\n}"
}
```

### PowerQuery (SDL Power Query)
```json
{
  "method": "post",
  "url": "{{Connection.protocol}}{{Connection.url}}/sdl/api/powerQuery",
  "payload": "{\n  \"query\": \"endpoint.name = '{{local_var.hostname}}' | group count() by event.type\",\n  \"startTime\": \"24h\"\n}"
}
```

### TI Ingestion (Threat Intelligence IOC)
```json
{
  "method": "post",
  "url": "{{Connection.protocol}}{{Connection.url}}/web/api/v2.1/threat-intelligence/iocs",
  "payload": "{\n  \"filter\": { \"siteIds\": [\"<your-site-id>\"] },\n  \"data\": [{\n    \"type\": \"IPV4\",\n    \"validUntil\": \"{{Function.DELTA_NOW(-72)}}\",\n    \"description\": \"TOR exit node\",\n    \"method\": \"EQUALS\",\n    \"creationTime\": \"{{Function.DATETIME_NOW()}}\",\n    \"externalId\": \"OSINT\",\n    \"value\": \"{{loop.item}}\",\n    \"originalRiskScore\": \"50\",\n    \"severity\": \"5\",\n    \"source\": \"My TI Library\",\n    \"name\": \"TOR Node Indicator\"\n  }]\n}"
}
```
