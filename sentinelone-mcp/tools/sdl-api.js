/**
 * SDL API tools — sentinelone-sdl-api, sentinelone-sdl-dashboard, sentinelone-sdl-log-parser skills
 *
 * Tools:
 *   sdl_list_files     List all config files on the SDL tenant
 *   sdl_get_file       Get file content and version (parsers, dashboards, alerts, lookups)
 *   sdl_put_file       Deploy or update a config file (with optimistic locking)
 *   sdl_delete_file    Delete a config file
 *   sdl_upload_logs    Upload raw log events to SDL (requires Log Write key)
 */

import { listFiles, getFile, putFile, deleteFile, uploadLogs } from '../lib/sdl.js';

export const tools = [
  // ─── sdl_list_files ───────────────────────────────────────────────────────
  {
    name: 'sdl_list_files',
    description: `List all configuration files stored in the SDL tenant. Returns all paths organized by type: /logParsers/, /dashboards/, /alerts/, /lookups/, /datatables/. Use this to discover what parsers and dashboards are already deployed, or to find a file path before calling sdl_get_file or sdl_put_file.`,
    inputSchema: {
      type: 'object',
      properties: {},
      required: [],
    },
    async handler() {
      const result = await listFiles();
      return JSON.stringify(result, null, 2);
    },
  },

  // ─── sdl_get_file ─────────────────────────────────────────────────────────
  {
    name: 'sdl_get_file',
    description: `Get the content and current version number of a SDL configuration file. Use before sdl_put_file to read the current version for optimistic locking (pass the returned version as expectedVersion). Supports any file type: parsers (/logParsers/<name>), dashboards (/dashboards/<name>), alerts (/alerts/<name>), lookups (/lookups/<name>), datatables (/datatables/<name>). Always read before overwriting — this prevents concurrent-edit conflicts.`,
    inputSchema: {
      type: 'object',
      properties: {
        path: {
          type: 'string',
          description: 'Full SDL config path, e.g. "/logParsers/FortiGate" or "/dashboards/SOC-Overview". Get the path from sdl_list_files.',
        },
      },
      required: ['path'],
    },
    async handler({ path }) {
      const result = await getFile(path);
      return JSON.stringify(result, null, 2);
    },
  },

  // ─── sdl_put_file ─────────────────────────────────────────────────────────
  {
    name: 'sdl_put_file',
    description: `Deploy or update a SDL configuration file. Always call sdl_get_file first to obtain the current expectedVersion — this prevents overwriting concurrent edits. If creating a new file, omit expectedVersion. File type conventions: parsers go to /logParsers/<name>, dashboards to /dashboards/<name>, alerts to /alerts/<name>, lookups to /lookups/<name>. Requires Configuration Write key (SDL_CONFIG_WRITE_KEY) or a console JWT that has config write permissions.`,
    inputSchema: {
      type: 'object',
      properties: {
        path: {
          type: 'string',
          description: 'Full SDL config path, e.g. "/logParsers/MyParser" or "/dashboards/SOC-Ops".',
        },
        content: {
          type: 'string',
          description: 'File content as a string. For dashboards: valid dashboard JSON. For parsers: augmented-JSON parser definition. For lookups: CSV or JSON.',
        },
        expectedVersion: {
          type: 'number',
          description: 'Current file version from sdl_get_file. Required for updates to enable optimistic locking. Omit only when creating a new file.',
        },
      },
      required: ['path', 'content'],
    },
    async handler({ path, content, expectedVersion }) {
      const result = await putFile(path, content, expectedVersion);
      return JSON.stringify(result, null, 2);
    },
  },

  // ─── sdl_delete_file ──────────────────────────────────────────────────────
  {
    name: 'sdl_delete_file',
    description: `Delete a SDL configuration file (parser, dashboard, alert, lookup, datatable). Use with caution — deletion is permanent. Always read the file with sdl_get_file first to confirm you have the right path and version.`,
    inputSchema: {
      type: 'object',
      properties: {
        path: {
          type: 'string',
          description: 'Full SDL config path to delete.',
        },
        expectedVersion: {
          type: 'number',
          description: 'Current file version for optimistic locking (from sdl_get_file). Strongly recommended.',
        },
      },
      required: ['path'],
    },
    async handler({ path, expectedVersion }) {
      const result = await deleteFile(path, expectedVersion);
      return JSON.stringify(result, null, 2);
    },
  },

  // ─── sdl_upload_logs ──────────────────────────────────────────────────────
  {
    name: 'sdl_upload_logs',
    description: `Upload raw log events to SDL via the uploadLogs endpoint (plain text, newline-separated). Used for ingesting custom telemetry, testing parsers, and one-off log imports. Requires an SDL Log Write Access key (SDL_LOG_WRITE_KEY) — the console JWT is NOT accepted for this endpoint. Max 6 MB per request, 10 GB per day. Pair with a parser at logfile= to apply field extraction.`,
    inputSchema: {
      type: 'object',
      properties: {
        logContent: {
          type: 'string',
          description: 'Raw log text, newline-separated. Each line becomes a separate SDL event.',
        },
        parser: {
          type: 'string',
          description: 'Parser name to apply to the uploaded events (matches the "parser" header). Omit to use the default parser.',
        },
        logfile: {
          type: 'string',
          description: 'Logical logfile identifier sent as the "logfile" header, e.g. "myapp/access.log". Used by parsers to route events.',
        },
        serverHost: {
          type: 'string',
          description: 'Source host name, sent as the "server-host" header.',
        },
      },
      required: ['logContent'],
    },
    async handler({ logContent, parser, logfile, serverHost }) {
      const result = await uploadLogs(logContent, { parser, logfile, serverHost });
      return JSON.stringify(result, null, 2);
    },
  },
];
