# Zendesk + Claude Code

Connects Claude Code to Zendesk through an MCP server (`.mcp.json`).

## Setup

1. Install [uv](https://docs.astral.sh/uv/) and clone a Zendesk MCP server that
   exposes a `zendesk` entry point (e.g. `reminia/zendesk-mcp-server`), then run
   `uv venv && uv pip install -e .` inside it.
2. In Zendesk, enable API token access (Admin Center > Apps and integrations >
   APIs > Zendesk API) and create a token.
3. Export the variables from `.env.example` in your shell (or your Claude Code
   environment's secrets). Never commit real values.
4. Start Claude Code in this repo, approve the `zendesk` project server, and run
   `/mcp` to confirm it is connected.

Review the MCP server's code before giving it your API token.
