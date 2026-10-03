# Codex setup

Codex CLI was already present during bootstrap: `codex-cli 0.159.3`, verified with
`codex --version`. No replacement or authentication was performed.

If absent on another machine, install the stable CLI:

```sh
npm install -g @openai/codex@latest
codex --version
```

From the repository root, the owner should authenticate interactively with `codex login` and
complete the supported browser login flow. Start work with `codex`. On a headless machine,
the supported `codex login --device-auth` flow may be available depending on account/workspace
settings. See [official authentication documentation](https://learn.chatgpt.com/docs/auth).

Project-specific instructions live in root `AGENTS.md`. Codex stores login state outside this
repository in its supported user credential storage. Never copy credentials, auth caches,
ChatGPT/OpenAI tokens, or API keys into repository files. Bootstrap does not need an API key.

The existing CLI is currently provided by an npm cache shim. If that cache is removed, the owner
can use the global installation command above to obtain a durable executable. Do not request
credentials in chat or automatically authenticate.
