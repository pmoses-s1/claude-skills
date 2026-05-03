#!/usr/bin/env node
/**
 * SentinelOne MCP Server
 *
 * Implements the Model Context Protocol (MCP) over stdio using raw JSON-RPC 2.0.
 * No external dependencies — pure Node.js 18+.
 *
 * Exposes:
 *   Resources  : sentinelone://soc-context  (CLAUDE.md SOC analyst operating instructions)
 *   Prompts    : soc_analyst                (system prompt embedding CLAUDE.md)
 *   Tools (21) : PowerQuery, Mgmt Console, SDL API, Hyperautomation, UAM Ingest
 *
 * Run as: node index.js
 * Configure in claude_desktop_config.json or .mcp.json — see README.md.
 */

import { createInterface } from 'readline';
import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

import { tools as pqTools }        from './tools/powerquery.js';
import { tools as mgmtTools }       from './tools/mgmt-console.js';
import { tools as sdlTools }        from './tools/sdl-api.js';
import { tools as haTools }         from './tools/hyperautomation.js';
import { tools as uamIngestTools }  from './tools/uam-ingest.js';
import { getCreds, hasS1Creds, hasSdlCreds } from './lib/credentials.js';
import { hasHecCreds } from './lib/uam-ingest.js';

const __dir = dirname(fileURLToPath(import.meta.url));

// ─── SOC context (CLAUDE.md) ──────────────────────────────────────────────────

function loadSocContext() {
  // Search for CLAUDE.md relative to this server (and up the tree)
  const candidates = [
    join(__dir, '..', 'CLAUDE.md'),            // claude-skills/CLAUDE.md
    join(__dir, '..', '..', 'CLAUDE.md'),       // project root
    join(__dir, 'CLAUDE.md'),                   // same dir
  ];
  for (const p of candidates) {
    if (existsSync(p)) {
      try { return readFileSync(p, 'utf-8'); } catch { /* skip */ }
    }
  }
  return '# SentinelOne SOC Analyst Context\n\n_CLAUDE.md not found. Place it in the claude-skills/ folder._';
}

const SOC_CONTEXT = loadSocContext();

// ─── Tool registry ────────────────────────────────────────────────────────────

const ALL_TOOLS = [...pqTools, ...mgmtTools, ...sdlTools, ...haTools, ...uamIngestTools];

// MCP tool schema (inputSchema is JSON Schema)
const TOOL_DEFS = ALL_TOOLS.map(t => ({
  name: t.name,
  description: t.description,
  inputSchema: t.inputSchema,
}));

// Handler map
const HANDLERS = Object.fromEntries(ALL_TOOLS.map(t => [t.name, t.handler]));

// ─── Resources ────────────────────────────────────────────────────────────────

const RESOURCES = [
  {
    uri: 'sentinelone://soc-context',
    name: 'SOC Analyst Operating Instructions',
    description: 'CLAUDE.md — Principal SOC Analyst operating instructions including investigation workflow, evidence discipline, anomaly detection playbook, MITRE ATT&CK mapping, and tool usage priorities.',
    mimeType: 'text/markdown',
  },
  {
    uri: 'sentinelone://credentials-status',
    name: 'Credential Configuration Status',
    description: 'Reports which credentials are configured and which API surfaces are available.',
    mimeType: 'application/json',
  },
];

// ─── Prompts ──────────────────────────────────────────────────────────────────

const PROMPTS = [
  {
    name: 'soc_analyst',
    description: 'Load the Principal SOC Analyst system context from CLAUDE.md. Call at the start of every security investigation session to prime the operating instructions, evidence discipline rules, investigation workflow, and tool usage priorities.',
    arguments: [],
  },
  {
    name: 'session_init',
    description: 'Structured session initialization prompt. Triggers mandatory data-source enumeration, alert triage, and schema discovery in parallel — mirroring the standard engagement workflow from the SOC playbook.',
    arguments: [],
  },
];

// ─── MCP protocol ─────────────────────────────────────────────────────────────

const SERVER_INFO = {
  name: 'sentinelone-mcp-server',
  version: '1.0.0',
};

const PROTOCOL_VERSION = '2024-11-05';

function ok(id, result) {
  return { jsonrpc: '2.0', id, result };
}

function err(id, code, message, data) {
  return { jsonrpc: '2.0', id, error: { code, message, ...(data ? { data } : {}) } };
}

function send(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function log(...args) {
  process.stderr.write('[sentinelone-mcp] ' + args.join(' ') + '\n');
}

// ─── Method handlers ──────────────────────────────────────────────────────────

async function dispatch(method, params, id) {
  switch (method) {

    case 'initialize': {
      return ok(id, {
        protocolVersion: PROTOCOL_VERSION,
        capabilities: {
          resources: { subscribe: false, listChanged: false },
          tools: { listChanged: false },
          prompts: { listChanged: false },
        },
        serverInfo: SERVER_INFO,
        instructions: 'SentinelOne MCP server providing PowerQuery, Mgmt Console API, SDL API, and Hyperautomation tools. Load the "soc_analyst" prompt at session start for full operating context.',
      });
    }

    case 'ping': {
      return ok(id, {});
    }

    case 'resources/list': {
      return ok(id, { resources: RESOURCES });
    }

    case 'resources/read': {
      const uri = params?.uri;
      if (uri === 'sentinelone://soc-context') {
        return ok(id, {
          contents: [{ uri, mimeType: 'text/markdown', text: SOC_CONTEXT }],
        });
      }
      if (uri === 'sentinelone://credentials-status') {
        const c = getCreds();
        const status = {
          s1MgmtApi: {
            configured: hasS1Creds(),
            consoleUrl: c.S1_CONSOLE_URL ? c.S1_CONSOLE_URL.replace(/https?:\/\//, '').split('.')[0] + '...' : 'NOT SET',
            tokenPresent: !!c.S1_CONSOLE_API_TOKEN,
          },
          sdlApi: {
            configured: hasSdlCreds(),
            xdrUrl: c.SDL_XDR_URL || 'NOT SET',
            configWriteKey: !!c.SDL_CONFIG_WRITE_KEY,
            logWriteKey: !!c.SDL_LOG_WRITE_KEY,
          },
          uamIngestApi: {
            configured: hasHecCreds(),
            hecUrl: c.S1_HEC_INGEST_URL || 'NOT SET (add S1_HEC_INGEST_URL to credentials.json)',
            tokenPresent: !!c.S1_CONSOLE_API_TOKEN,
          },
        };
        return ok(id, {
          contents: [{ uri, mimeType: 'application/json', text: JSON.stringify(status, null, 2) }],
        });
      }
      return err(id, -32002, `Resource not found: ${uri}`);
    }

    case 'prompts/list': {
      return ok(id, { prompts: PROMPTS });
    }

    case 'prompts/get': {
      const name = params?.name;

      if (name === 'soc_analyst') {
        return ok(id, {
          description: 'Principal SOC Analyst operating instructions from CLAUDE.md',
          messages: [
            {
              role: 'user',
              content: {
                type: 'text',
                text: `You are operating as a Principal SOC Analyst. Load and follow the instructions below precisely.\n\n${SOC_CONTEXT}`,
              },
            },
          ],
        });
      }

      if (name === 'session_init') {
        return ok(id, {
          description: 'Structured session initialization',
          messages: [
            {
              role: 'user',
              content: {
                type: 'text',
                text: `Begin a new SOC analyst session. Follow this initialization sequence:

1. Call \`powerquery_enumerate_sources\` to discover active SDL data sources (MANDATORY — never assume sources from prior sessions).
2. In parallel, call \`uam_list_alerts\` with filter="status=OPEN" to pull active alerts.
3. For each discovered data source not already in the schema registry, plan schema discovery via \`powerquery_schema_discover\`.
4. Report: (a) active data sources list, (b) open alert count and top 5 by severity, (c) which sources need schema discovery.

Apply the SOC analyst context from the soc_analyst prompt throughout.`,
              },
            },
          ],
        });
      }

      return err(id, -32002, `Prompt not found: ${name}`);
    }

    case 'tools/list': {
      return ok(id, { tools: TOOL_DEFS });
    }

    case 'tools/call': {
      const toolName = params?.name;
      const args = params?.arguments || {};

      if (!toolName) {
        return err(id, -32602, 'Missing tool name');
      }

      const handler = HANDLERS[toolName];
      if (!handler) {
        return err(id, -32602, `Tool not found: ${toolName}`);
      }

      try {
        const output = await handler(args);
        const text = typeof output === 'string' ? output : JSON.stringify(output, null, 2);
        return ok(id, {
          content: [{ type: 'text', text }],
          isError: false,
        });
      } catch (e) {
        log(`Tool error [${toolName}]:`, e.message);
        return ok(id, {
          content: [{ type: 'text', text: `Error: ${e.message}` }],
          isError: true,
        });
      }
    }

    // Notifications have no id — just ignore
    case 'notifications/initialized':
    case 'initialized':
      return null;

    default: {
      if (id !== undefined) {
        return err(id, -32601, `Method not found: ${method}`);
      }
      return null;
    }
  }
}

// ─── Main loop ────────────────────────────────────────────────────────────────

async function main() {
  log(`Starting (node ${process.version})`);

  const creds = getCreds();
  log(`S1 Mgmt API:  ${hasS1Creds() ? 'configured (' + creds.S1_CONSOLE_URL + ')' : 'NOT configured'}`);
  log(`SDL API:      ${hasSdlCreds() ? 'configured (' + creds.SDL_XDR_URL + ')' : 'NOT configured'}`);
  log(`UAM Ingest:   ${hasHecCreds() ? 'configured (' + creds.S1_HEC_INGEST_URL + ')' : 'NOT configured (add S1_HEC_INGEST_URL to credentials.json)'}`);
  log(`Tools:        ${ALL_TOOLS.length} registered`);

  const rl = createInterface({ input: process.stdin, terminal: false });

  // Track in-flight async requests so we don't exit while one is still running
  let inFlight = 0;
  let stdinClosed = false;

  function maybeExit() {
    if (stdinClosed && inFlight === 0) {
      log('All requests complete, exiting.');
      process.exit(0);
    }
  }

  rl.on('line', async (line) => {
    const trimmed = line.trim();
    if (!trimmed) return;

    let msg;
    try {
      msg = JSON.parse(trimmed);
    } catch (e) {
      send(err(null, -32700, `Parse error: ${e.message}`));
      return;
    }

    // Notification (no id) — handle but don't respond
    const isNotification = msg.id === undefined;

    inFlight++;
    try {
      const response = await dispatch(msg.method, msg.params, msg.id);
      if (response !== null && !isNotification) {
        send(response);
      }
    } catch (e) {
      log('Unhandled dispatch error:', e.message, e.stack);
      if (!isNotification) {
        send(err(msg.id ?? null, -32603, `Internal error: ${e.message}`));
      }
    } finally {
      inFlight--;
      maybeExit();
    }
  });

  rl.on('close', () => {
    log('stdin closed, waiting for in-flight requests...');
    stdinClosed = true;
    maybeExit();
  });

  process.on('SIGINT', () => {
    log('SIGINT received, exiting.');
    process.exit(0);
  });
}

main().catch(e => {
  process.stderr.write(`Fatal: ${e.message}\n${e.stack}\n`);
  process.exit(1);
});
