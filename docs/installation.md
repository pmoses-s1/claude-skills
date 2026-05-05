# Installation and Upgrade Guide

This page covers everything needed to go from zero to a working PrincipalSOCAnalyst session: prerequisites, MCP server setup, plugin install, credential configuration, and project creation. Upgrade instructions are at the bottom.

- [Prerequisites](#prerequisites)
- [Step 1: Install sentinelone-mcp](#step-1-install-sentinelone-mcp)
- [Step 2: Configure MCP servers](#step-2-configure-mcp-servers)
- [Step 3: Install the plugin](#step-3-install-the-plugin)
- [Step 4: Create the Cowork project](#step-4-create-the-cowork-project)
- [Step 5: Verify the install](#step-5-verify-the-install)
- [Upgrading](#upgrading)
- [Building from source](#building-from-source)
- [Configuration](#configuration)

---

## Prerequisites

| Requirement | Check | Install |
|---|---|---|
| Node.js 18+ | `node --version` | [nodejs.org](https://nodejs.org) |
| `uv` (for purple-mcp) | `uvx --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh`, then open a new terminal to confirm `uvx --version` works |
| SentinelOne API token | Settings → Users → Service Users | [Community guide](https://community.sentinelone.com/s/article/000005291) |
| SDL API keys | Singularity Data Lake → API Keys | [Community guide](https://community.sentinelone.com/s/article/000006763) |
| Regional endpoint URLs (`S1_CONSOLE_URL`, `SDL_XDR_URL`, `S1_HEC_INGEST_URL`) | — | [SentinelOne Endpoint URLs by Region](https://community.sentinelone.com/s/article/000004961) |
| VirusTotal API key (or equivalent threat intel MCP) | [virustotal.com/gui/my-apikey](https://www.virustotal.com/gui/my-apikey) | Free tier is sufficient |

---

## Step 1: Install sentinelone-mcp

`sentinelone-mcp` is a Node.js MCP server. It gives Claude direct access to PowerQuery, the SDL API, the Management Console REST API, UAM, and Hyperautomation, bypassing the Cowork sandbox proxy.

**Clone or download the repo** (if you haven't already):

```bash
git clone https://github.com/pmoses-s1/claude-skills.git
cd claude-skills
```

Install the MCP server dependencies:

```bash
cd sentinelone-mcp
npm install
cd ..
```

Note the absolute path to `sentinelone-mcp/index.js` — you will need it in the next step.

---

## Step 2: Configure MCP servers

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, or `%APPDATA%\Claude\claude_desktop_config.json` on Windows. Add the three MCP servers shown below.

Replace every placeholder (`yourname`, `usea1-yourorg`, `eyJ...`, key values) with your real values.

```json
{
  "mcpServers": {
    "sentinelone-mcp": {
      "command": "node",
      "args": [
        "/path/to/claude-skills/sentinelone-mcp/index.js"
      ],
      "env": {
        "S1_CONSOLE_URL": "https://usea1-yourorg.sentinelone.net",
        "S1_CONSOLE_API_TOKEN": "eyJ...your-api-token...",
        "S1_HEC_INGEST_URL": "https://ingest.us1.sentinelone.net",
        "SDL_XDR_URL": "https://xdr.us1.sentinelone.net",
        "SDL_LOG_WRITE_KEY": "your-log-write-key",
        "SDL_LOG_READ_KEY": "your-log-read-key",
        "SDL_CONFIG_WRITE_KEY": "your-config-write-key",
        "SDL_CONFIG_READ_KEY": "your-config-read-key"
      }
    },
    "purple-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Sentinel-One/purple-mcp.git",
        "purple-mcp",
        "--mode",
        "stdio"
      ],
      "env": {
        "PURPLEMCP_CONSOLE_TOKEN": "eyJ...your-api-token...",
        "PURPLEMCP_CONSOLE_BASE_URL": "https://usea1-yourorg.sentinelone.net"
      }
    },
    "virustotal": {
      "command": "mcp-virustotal",
      "env": {
        "VIRUSTOTAL_API_KEY": "your-virustotal-api-key"
      }
    }
  },
  "preferences": {
    "localAgentModeTrustedFolders": [
      "/path/to/claude-skills"
    ],
    "coworkScheduledTasksEnabled": true,
    "coworkWebSearchEnabled": true
  }
}
```

**Key config notes:**

- `sentinelone-mcp`: set `command` to `node` and the first `args` entry to the absolute path of `sentinelone-mcp/index.js` in this repo.
- `purple-mcp`: uses `uvx` directly — confirm it is in your PATH with `uvx --version` before restarting Claude Desktop.
- `virustotal`: the VirusTotal MCP is shown as a concrete example. Replace it with your organisation's approved threat intel MCP if different. Install the npm package with `npm install -g mcp-virustotal` if using VirusTotal.
- Both `S1_CONSOLE_API_TOKEN` and `PURPLEMCP_CONSOLE_TOKEN` are the same Management Console API token; you can generate one under Settings → Users → Service Users.
- Region URLs vary. Look up your region's `S1_HEC_INGEST_URL` and `SDL_XDR_URL` in the [SentinelOne Endpoint URLs by Region](https://community.sentinelone.com/s/article/000004961) article.

**Restart Claude Desktop** after saving the config file.

Full credential reference: [credentials.md](./credentials.md)

---

## Step 3: Install the plugin

The plugin bundles all six skills in a single file. Download `sentinelone-skills-vX.Y.Z.plugin` from [`sentinelone-skills-plugin/dist/`](../sentinelone-skills-plugin/dist/).

In the Claude desktop app:

1. Open the **Cowork** tab
2. Click **Customize** in the left sidebar
3. Click **Browse plugins**
4. Upload the `.plugin` file

All six skills install in one step. No individual skill configuration is needed after this.

**If plugin upload fails**, install individual `.skill` files from the same `dist/` folder. Double-click any `.skill` file in Finder (macOS) or Explorer (Windows) to trigger the install prompt, or upload each one via Browse plugins.

The six skill files are: `sentinelone-mgmt-console-api.skill`, `sentinelone-powerquery.skill`, `sentinelone-sdl-api.skill`, `sentinelone-sdl-dashboard.skill`, `sentinelone-sdl-log-parser.skill`, `sentinelone-hyperautomation.skill`.

---

## Step 4: Create the Cowork project

> Create this project in Cowork, not Claude.ai chat. Open the Claude desktop app and navigate to Cowork from the sidebar.

1. In the Claude desktop app, open **Cowork** and click **New Project**
2. Name it `PrincipalSOCAnalyst`
3. Click **Select Folder** and choose this `claude-skills` folder (the one containing `CLAUDE.md`)
4. Under **Add files**, add `CLAUDE.md` so Claude reads the SOC Analyst persona on every session start

> **credentials.json:** If you are using `sentinelone-mcp` (recommended), all credentials are in `claude_desktop_config.json` and you do not need to add `credentials.json` to the project. If you are running skills directly without `sentinelone-mcp`, add `credentials.json` here as well. See [credentials.md](./credentials.md) for setup.

5. Confirm that `sentinelone-skills` appears under Personal plugins, and that `sentinelone-mcp`, `purple-mcp`, and your threat intel MCP appear under MCP Servers

---

## Step 5: Verify the install

Open the **PrincipalSOCAnalyst** project and start a new session. Claude will automatically:

- Enumerate all live `dataSource.name` values in your SDL
- Pull open alerts in parallel

If either of these steps fails, check:

- `sentinelone-mcp` is listed and green under MCP Servers in the Cowork session panel
- The API token has the correct scope (Viewer or higher for read operations; IR Team or higher for response actions)
- The `SDL_XDR_URL` and API keys match your region

To confirm which plugin version is active, ask Claude: `which version of sentinelone-skills is installed?`

---

## Upgrading

When a newer `sentinelone-skills-vX.Y.Z.plugin` is published in [`sentinelone-skills-plugin/dist/`](../sentinelone-skills-plugin/dist/):

1. Download the new `.plugin` file
2. In the Claude desktop app, open the **Cowork** tab
3. Click **Customize** → **Browse plugins**
4. Upload the new `.plugin` file
5. When prompted that `sentinelone-skills` is already installed, click **Replace**

All six skills upgrade in one step. Credentials and project-folder configuration are untouched.

**Upgrading sentinelone-mcp:**

```bash
cd claude-skills
git pull
cd sentinelone-mcp && npm install
```

Restart Claude Desktop after pulling changes.

**Upgrading purple-mcp:**

`uvx` fetches the latest version from GitHub on each startup, so no manual update step is needed. To force a refresh: `uvx cache clean purple-mcp`.

---

## Building from source

After making local changes to skill files, rebuild the plugin:

```bash
# Incremental build
cd sentinelone-skills-plugin && bash scripts/build.sh

# Clean build (removes old dist files first)
cd sentinelone-skills-plugin && bash scripts/build.sh --clean
```

Then reinstall the resulting `.plugin` file from `sentinelone-skills-plugin/dist/` via Browse plugins → Replace.

---

## Configuration

**If you are using `sentinelone-mcp` (recommended):** credentials are passed as environment variables in `claude_desktop_config.json` as shown in [Step 2](#step-2-configure-mcp-servers) above. You do not need a `credentials.json` file in your project folder.

**If you are using the skills directly without `sentinelone-mcp`** (or for backwards compatibility): the skills also read credentials from a `credentials.json` file placed in your Cowork project folder. The plugin's SessionStart hook auto-discovers it and makes it available to every skill in the session.

**Setup is two commands.** Copy [`credentials.example.json`](../sentinelone-skills-plugin/credentials.example.json) from this repo into your Cowork project folder, renaming it to `credentials.json`, then edit it.

**macOS / Linux:**

```bash
# 1. Pick your Cowork project folder.
PROJECT_DIR=~/Documents/Claude/Projects/MyProject

# 2. Copy the example, renaming to credentials.json.
cp sentinelone-skills-plugin/credentials.example.json "$PROJECT_DIR/credentials.json"

# 3. Edit it: replace the placeholder values with your real ones.
${EDITOR:-nano} "$PROJECT_DIR/credentials.json"
```

**Windows (PowerShell):**

```powershell
# 1. Pick your Cowork project folder.
$projectDir = "$env:USERPROFILE\Documents\Claude\Projects\MyProject"

# 2. Copy the example, renaming to credentials.json.
Copy-Item .\sentinelone-skills-plugin\credentials.example.json "$projectDir\credentials.json"

# 3. Edit it: replace the placeholder values with your real ones.
notepad "$projectDir\credentials.json"
```

If you only downloaded the `.plugin` file (not the full repo), extract `credentials.example.json` from the plugin zip with any unzip tool, or grab it directly from the repo at [`sentinelone-skills-plugin/credentials.example.json`](../sentinelone-skills-plugin/credentials.example.json).

| Credential key | Required for | How to get it |
|---|---|---|
| `S1_CONSOLE_URL` | All management console skills | Your console URL, e.g. `https://usea1-acme.sentinelone.net` |
| `S1_CONSOLE_API_TOKEN` | `sentinelone-mgmt-console-api`, `sentinelone-powerquery`, plus SDL query and config methods (not `uploadLogs`) | Settings → Users → Service Users → Create New Service User → copy the API token. The same JWT works for the SDL API from Management version Z SP5+. See [Creating service users](https://community.sentinelone.com/s/article/000005291) and [SDL API Keys](https://community.sentinelone.com/s/article/000006763) |
| `S1_HEC_INGEST_URL` | UAM alert/indicator ingest and log ingest via HEC | The SentinelOne HEC ingest host for your region, e.g. `https://ingest.us1.sentinelone.net`. See [SentinelOne Endpoint URLs by Region](https://community.sentinelone.com/s/article/000004961) |
| `SDL_XDR_URL` | `sentinelone-sdl-api`, `sentinelone-sdl-dashboard`, `sentinelone-sdl-log-parser` | Your SDL tenant URL, e.g. `https://xdr.us1.sentinelone.net`. See [SentinelOne Endpoint URLs by Region](https://community.sentinelone.com/s/article/000004961) |
| `SDL_LOG_WRITE_KEY` | `uploadLogs` only | Singularity Data Lake → menu next to username → API Keys → Log Access Keys → New Key (Log Write Access). See [SDL API Keys](https://community.sentinelone.com/s/article/000006763) |
| `SDL_CONFIG_WRITE_KEY` | Deploying parsers/dashboards via `putFile` | Singularity Data Lake → menu next to username → API Keys → Configuration Access Keys → New Key (Configuration Write Access). See [SDL API Keys](https://community.sentinelone.com/s/article/000006763) |

Resolution order (highest priority wins):
1. Environment variables in `claude_desktop_config.json` via `sentinelone-mcp` (recommended)
2. `<project folder>/credentials.json` (backwards-compatible fallback for direct skill usage)
3. `~/.config/sentinelone/credentials.json` (terminal fallback)

Full credential reference including all SDL keys: [credentials.md](./credentials.md)
