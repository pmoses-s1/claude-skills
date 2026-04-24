# Community Dashboard Examples

These are production-ready SDL dashboard JSON examples. Use them as starting points or copy panels directly. The format is JavaScript-literal (unquoted keys are OK in SDL — it accepts both).

---

## 1. Console Audit & KPI Dashboard

Multi-tab dashboard covering agent lifecycle, threat stats, policy changes, exclusions, network control, device control, Ranger, RemoteOps, Marketplace, and login events. Uses `dataSource.name='ActivityFeed'` for all audit panels.

**Key patterns used:**
- Stacked bar with `timebucket("1 day")` + `transpose` for timelines
- Table panels with `| columns` for clean column naming
- `activity_type in (...)` filtering with quoted string values
- `format(...)` for computed URL deep-links

**Tab: Agents & Scopes** — agent subscriptions by site/group/account/OS, agent updates, decommissions, scope moves.
```javascript
{
  tabs: [{"tabName":"Agents & Scopes",
graphs : [
  {
    graphStyle: "stacked_bar",
    query: "dataSource.name='ActivityFeed' activity_type = \"17\" \n| let scope = format(\"%s / %s\", account_name, site_name)\n| group count = count() by timestamp = timebucket(\"1 day\"), scope\n| transpose scope on timestamp",
    title: "New agents subscribed by site",
    xAxis: "time",
    yScale: "linear",
    layout: { h: 14, w: 20, x: 20, y: 0 }
  },
  {
    query: "dataSource.name='ActivityFeed' activity_type in (\"47\", \"49\", \"50\", \"51\", \"52\", \"54\") \n| columns Time=created_at, Username=data.username, Scope=data.full_scope_details_path, type, Description=primary_description\n| sort -Time",
    title: "Agents decommissioned or uninstalled",
    graphStyle: "",
    showBarsColumn: "false",
    layout: { h: 14, w: 60, x: 0, y: 42 }
  }
]}],
  configType: "TABBED"
}
```

**Tab: Threat Stats** — timeline by confidence/verdict/status, noisiest machines, failed mitigations, custom rule alerts.
```javascript
{
  graphStyle: "stacked_bar",
  query: "index = \"activities\" activity_type in (\"18\",\"19\",\"20\",\"2016\",\"4003\",\"4009\",\"4108\",\"4100\",\"4109\",\"4110\",\"4111\",\"4112\", \"2036\",\"2037\")\n| let confidence = (activity_type in (\"2036\",\"2037\") ? data.new_confidence_level : data.confidence_level)\n| group newest_confidence=newest(confidence) by threat_id, timestamp = timebucket(\"1 day\")\n| group count = count() by timestamp, newest_confidence\n| transpose newest_confidence on timestamp",
  title: "Threat timeline by confidence",
  xAxis: "time",
  yScale: "linear"
}
```

**Tab: Conf & Policy Changes** — sensitive policy mods by user/scope, device control changes, network quarantine, inheritance changes.
```javascript
{
  query: "dataSource.name='ActivityFeed' activity_type in (\"56\", \"57\", \"68\", \"69\", \"73\", \"76\", \"78\", \"79\", \"84\", \"105\", \"87\", \"88\", \"150\") \n| columns Time=created_at, Username=data.username, Scope=data.full_scope_details_path, type, Description=primary_description\n| sort -Time",
  title: "Sensitive policy modifications details",
  graphStyle: "",
  showBarsColumn: "false"
}
```

---

## 2. Purple AI Audit Dashboard

Tracks Purple AI usage by analyst.
```javascript
{
  description: "",
  tabs: [{"tabName":"PurpleAI","graphs":[
    {
      query: "serverHost='scalyr-metalog' action='addPurpleInputOutputMessage'\n| group count = count() by analyst=inputContent.userDetails.emailAddress\n| sort -count",
      title: "Count of PurpleAI questions by analyst",
      graphStyle: "",
      showBarsColumn: "true",
      layout: { h: 12, w: 15, x: 0, y: 0 }
    },
    {
      query: "source = \"scalyr\" action = 'addPurpleInputOutputMessage'\n| let output = (!isempty(outputContent.message) ? outputContent.message : outputContent.powerQuery.query)\n| columns timestamp, conversationId, analyst=inputContent.userDetails.emailAddress, inputContent.userInput, output \n| sort conversationId, +timestamp",
      title: "All questions to PurpleAI by user",
      graphStyle: "",
      showBarsColumn: "false",
      layout: { h: 17, w: 60, x: 0, y: 12 }
    },
    {
      graphStyle: "line",
      lineSmoothing: "straightLines",
      query: "source = \"scalyr\" serverHost='scalyr-metalog' action='addPurpleInputOutputMessage'\n| group count = count() by timestamp = timebucket(\"1 hour\"), status\n| transpose status on timestamp",
      title: "PurpleAI usage timeline by status",
      yScale: "linear",
      layout: { h: 12, w: 15, x: 45, y: 0 }
    },
    {
      graphStyle: "stacked_bar",
      query: "source = \"scalyr\" action = 'addPurpleInputOutputMessage'\n| let analyst=inputContent.userDetails.emailAddress\n| group count = count() by timestamp = timebucket(\"1 day\"), analyst\n| transpose analyst on timestamp",
      title: "PurpleAI query timeline by user",
      xAxis: "time",
      yScale: "linear",
      layout: { h: 12, w: 30, x: 15, y: 0 }
    }
  ]}],
  configType: "TABBED"
}
```

---

## 3. Alert Investigation Dashboard

Multi-tab investigation dashboard with filters for `endpoint.name` and `src.process.storyline.id`. Covers event overview, process tree, file activity, network, indicators, and lateral movement.

**Tab: Overview** — event category breakdown, indicator categories, file timeline, outbound IPs, DNS by process.
```javascript
{
  tabs: [{"tabName":"Overview","graphs":[
    {
      graphStyle: "stacked_bar",
      query: "event.category contains \"\" dataSource.category = 'security'\n| group count = count() by event.category\n| sort -count",
      title: "Count by event category",
      xAxis: "grouped_data",
      yScale: "linear"
    },
    {
      query: "event.category = \"ip\" event.network.direction = \"OUTGOING\" dataSource.category = 'security'\n| group count = count() by dst.ip.address, src.process.name\n| sort -count\n| columns src.process.name, dst.ip.address, count",
      title: "TOP outgoing IP connections by process",
      graphStyle: "",
      showBarsColumn: "true"
    },
    {
      query: "event.category = \"dns\" dataSource.category = 'security'\n| group count = count() by src.process.name, event.dns.request\n| sort -count",
      title: "TOP DNS petitions by process"
    }
  ],
  filters: [
    { facet: "endpoint.name", name: "Endpoint name" },
    { facet: "src.process.storyline.id", name: "Src storyline ID" }
  ],
  options: {layout: {locked: 1}}
  }],
  configType: "TABBED"
}
```

**Tab: File** — file event timeline, distinct file interactions by process, possible ransom notes detection.
```javascript
{
  query: "event.category = \"file\" dataSource.category = 'security' \n| let windows_path_array = array_split(tgt.file.path, \"\\\\\\\\\")\n| let windows_directory_path_array = array_slice(windows_path_array, 0, len(windows_path_array)-1)\n| let windows_directory_path_string = array_to_string(windows_directory_path_array, \"\\\\\")\n| let windows_filename_string = windows_path_array.get(len(windows_path_array)-1)\n| let unix_path_array = array_split(tgt.file.path, \"/\")\n| let unix_directory_path_array = array_slice(unix_path_array, 0, len(unix_path_array)-1)\n| let unix_directory_path_string = array_to_string(unix_directory_path_array, \"/\")\n| let unix_filename_string = unix_path_array.get(len(unix_path_array)-1)\n| let directory_path_string = (endpoint.os = \"windows\") ? windows_directory_path_string : unix_directory_path_string\n| let filename_string = (endpoint.os = \"windows\") ? windows_filename_string : unix_filename_string\n| group distinct_path_count = estimate_distinct(directory_path_string) by endpoint.name, src.process.name, src.process.image.sha1, event.type, tgt.file.extension, filename_string\n| sort -distinct_path_count\n| columns src.process.name, event.type, distinct_path_count, filename_string\n| limit 10",
  title: "Possible ransom notes"
}
```

**Tab: Network** — IP timeline by direction/status, outbound/inbound scan detection, top destinations/sources.
```javascript
{
  query: "event.category = \"ip\" and event.network.direction = \"OUTGOING\" dataSource.category = 'security'\n| group distinct_dstip=estimate_distinct(dst.ip.address) by endpoint.name, src.ip.address, src.process.name, src.process.storyline.id\n| sort -distinct_dstip\n| columns endpoint.name, src.process.storyline.id, src.process.name, src.ip.address, distinct_dstip\n| limit 10",
  title: "Possible outbound network scan"
}
```

**Tab: Indicators** — indicator category breakdown, HIFI (high-fidelity) indicators, full indicator list.
```javascript
{
  query: "event.category = 'indicators' indicator.name contains (\"appLockerBypass\",\"blockedMimikatz\",\"bloodHound\",\"maliciousPowershellScript\",\"MetasploitNamedPipeImpersonation\",\"ransomware\",\"brute\") dataSource.category = 'security'\n| group count=count() by indicator.category, indicator.name\n| sort -count",
  title: "HIFI Indicators"
}
```

---

## 4. O365 / Azure AD Dashboard

Multi-tab dashboard for Microsoft data sources. Tabs: O365 Alerts, Azure Login Activity, Azure AD lifecycle, SharePoint, OneDrive.

**Tab: O365 Alerts**
```javascript
{
  query: "dataSource.vendor = 'Microsoft' activity_name='newAlert'\n| columns metadata.original_time, severity=unmapped.severity, finding.types, finding.title, details=unmapped.userStates, url=finding.src_url\n| sort -metadata.original_time",
  title: "Microsoft Alerts",
  graphStyle: "",
  showBarsColumn: "false"
}
```

**Tab: Azure Login Activity** — logon status timeline, top 15 failing users, logins by country, failed logins by country, every login attempt detailed (with geo enrichment, OS, browser extraction from JSON arrays).
```javascript
{
  query: "dataSource.vendor='Microsoft' metadata.product.name='AzureActiveDirectory' event.type in ('Logon', 'UserLoginFailed') !isempty(actor.user.email_addr)\n| let ip_address = event.type='Logon' ? device.ip : unmapped.ActorIpAddress\n| let data_array = array_from_json(unmapped.DeviceProperties)\n| let os = json_object_value(data_array.get(0), \"Name\")=\"OS\" ? json_object_value(data_array.get(0), \"Value\") : \"not found\"\n| let browser = json_object_value(data_array.get(0), \"Name\")=\"BrowserType\" ? json_object_value(data_array.get(0), \"Value\") : \"not found\"\n| group count = count() by actor.user.email_addr, event.type, os, browser, ip_address, country=geo_ip_country(ip_address), unmapped.LogonError\n| sort -count",
  title: "Every login attempt detailed"
}
```

**Tab: OneDrive** — download timeline, top users downloading by GB and distinct file count.
```javascript
{
  query: "dataSource.vendor='Microsoft' metadata.product.name='OneDrive' event.type in ('FileDownloaded')\n| group downloaded_bytes = sum(unmapped.FileSizeBytes), distinct_files=estimate_distinct(unmapped.SourceFileName) by user=unmapped.UserId\n| let downloaded_gbytes = downloaded_bytes/1024/1024/1024\n| columns user, downloaded_gbytes, distinct_files\n| sort -distinct_files\n| limit 10",
  title: "Top users downloading by distinct file count"
}
```

---

## 5. Fortinet Dashboard

Single-tab dashboard with parameters for dynamic filtering. Covers source/destination IPs, bytes sent/received, URL categories, protocol breakdown.

Uses a hidden parameter pattern:
```javascript
{
  parameters: [
    {
      name: "base_search",
      options: { display: "hidden" },
      defaultValue: "dataSource.name='Fortigate'"
    }
  ],
  graphs: [
    {
      query: "dataSource.vendor='Fortinet' | group count = count() by dst_endpoint.location.country | sort -count | limit 20",
      title: "Top Destination Countries",
      graphStyle: "donut",
      maxPieSlices: 20,
      dataLabelType: "PERCENTAGE"
    },
    {
      query: "| parse \"$bytes_out{regex=\\\\d+}$\" from traffic.bytes_out\n| filter( dataSource.name == \"FortiGate\" AND event.type == \"traffic\" )\n| group TotalBytesSent = sum( bytes_out )\n| limit 1000",
      title: "Total Bytes Sent in Timeframe",
      graphStyle: "number",
      trendConfig: {
        enabled: true,
        indicators: {
          arrow: { enabled: true },
          number: { calculationType: "PERCENTAGE", enabled: true },
          upwardsMeaning: "POSITIVE"
        }
      }
    },
    {
      query: "dataSource.category = 'security' | filter( dataSource.name == \"FortiGate\" AND metadata.log_name == \"webfilter\" )\n| group URLCount = count() by http_request.url.categories | sort -URLCount | limit 1000",
      title: "URL Categories",
      graphStyle: "pie",
      maxPieSlices: 10
    }
  ],
  description: "Fortinet FortiGate traffic and security events"
}
```

---

## Panel Snippets Library

### Activity type quick reference (ActivityFeed)
Common activity types for audit dashboards:
- `"17"` — Agent subscribed (new enrollment)
- `"43"` — Agent updated
- `"47","49","50","51","52","54"` — Agent decommissioned/uninstalled
- `"18","19","20"` — Threat created/confirmed/mitigated
- `"2028"` — Threat resolved (use `data.new_incident_status_title`)
- `"2030"` — Analyst verdict set
- `"2036","2037"` — Threat confidence updated
- `"3608"` — Custom STAR rule alert
- `"27"` — User logged in
- `"133","134"` — Login failure (existing/unknown user)
- `"56","57","68","69","73","76","78","79","84","87","88","105","150"` — Sensitive policy modifications
- `"5125","5126"` — USB device blocked/allowed
- `"5232"` — Firewall connection blocked
- `"3001","3008"-"3011"` — Exclusions added
- `"3618"` — RemoteOps script executed

### Geo enrichment
```
| let country = geo_ip_country(src.ip.address)
| let state   = geo_ip_state(src.ip.address)
```

### RFC1918 filter (exclude private IPs)
```
| let rfc1918 = not (dst.ip.address matches '((127\\..*)|(192\\.168\\..*)|(10\\..*)|(172\\.1[6-9]\\..*)|(172\\.2[0-9]\\..*)|(172\\.3[0-1]\\..*)).*')
| filter rfc1918 = true
```

### Format deep-link URL
```
| let Threat_URL = format("https://your-console.sentinelone.net/incidents/threats/%s/overview", threat_id)
```

### Normalize values to 0–100 for honeycomb
```
| let max=overall_max(value), min=overall_min(value)
| let normalized = ((value - min)/(max - min))*100
```
