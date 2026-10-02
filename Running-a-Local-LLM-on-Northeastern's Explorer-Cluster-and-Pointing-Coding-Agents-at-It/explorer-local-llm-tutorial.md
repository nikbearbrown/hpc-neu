# Running a Local LLM on Northeastern's Explorer Cluster and Pointing Coding Agents at It

*Ollama in Apptainer on a Slurm GPU node, with Claude Code, Aider, and Continue as the harness. Last checked against Ollama, Claude Code, and Research Computing documentation in October 2026.*

This tutorial shows how to run an open-weight model on an Explorer GPU and drive it from a coding agent, with no per-token billing. It covers two patterns that work for a single person today, and it lays out what a shared "endpoint" for a group of students or fellows would require, because that is a policy question for Research Computing (RC), not a configuration question.

You need an Explorer account with a Slurm association, an SSH client, and basic comfort with a Linux shell. Everything below runs as an ordinary user with no root access.

---

## Part 0 — Corrections to the earlier guidance

Several commands in the guidance that circulated alongside the ServiceNow ticket will fail or create a security problem. Fix these before anything else.

| Earlier guidance | What goes wrong | What to do instead |
|---|---|---|
| `export OLLAMA_HOST=0.0.0.0:11434` | Ollama has no authentication. Binding to `0.0.0.0` on a shared cluster exposes the full API, including model pull and delete, to anyone who can reach the node. The official image already defaults to `0.0.0.0`, and inside Apptainer the image's environment overrides a plain `export` from your shell. | Pass `--env OLLAMA_HOST=127.0.0.1:<port>` to Apptainer. If you need remote access, put a token-checking proxy in front (Part 6). |
| `ssh -L 11434:localhost:11434 user@discovery.neu.edu` | Discovery has been superseded by Explorer, and the login host is `login.explorer.northeastern.edu`. `localhost` on the right side forwards to the login node, not to the compute node where Ollama runs. RC does not support direct SSH into GPU nodes. | `ssh -N -L 11435:<node>:<port> <user>@login.explorer.northeastern.edu` (Part 6). |
| `ANTHROPIC_BASE_URL="http://localhost:11434/v1"` | Claude Code appends `/v1/messages` itself, so this produces `/v1/v1/messages` and a 404. | Use the bare host and port: `http://127.0.0.1:<port>`. Ollama 0.14 and later speak the Anthropic Messages API natively; no LiteLLM translation layer is needed. |
| Setting only `ANTHROPIC_MODEL` | Claude Code routes background tasks and subagents to its `haiku`/`sonnet`/`opus` aliases. Unmapped, those requests ask Ollama for Claude model names it doesn't have. | Map every alias and the subagent model to your local model (Part 4, step 6). |
| `deepseek-r1:1.5b` as the coding model | A 1.5B reasoning distill cannot reliably drive an agent loop with dozens of tool schemas. It will load, then fail at tool calling. | Use a tool-capable coding model in the 20B–120B range (Part 3). |
| No mention of context length | Ollama sizes its default context by available VRAM: 4k under 24 GiB, 32k from 24 to 48 GiB. Claude Code's system prompt and tool definitions alone overflow small windows, and overflow is truncated without an error. | Set `OLLAMA_CONTEXT_LENGTH=65536` (or higher) on the server. |
| `aider --model ollama/...` | Works, but Aider recommends the `ollama_chat/` prefix. | `aider --model ollama_chat/<model>` |
| Continue `config.json` | Continue moved to `config.yaml`. | See Part 7. |
| "Google Antigravity can be configured as the harness" | I could not confirm local-model support in Antigravity. | Treat as unverified. Don't build a course workflow on it. |
| "Zero marginal cost," "bypasses API credit limits entirely" | GPU hours count against fair-share, you wait in the queue, and the GPU IdleBot cancels allocations that sit under-used for an hour. | The accurate claim is "no per-token billing." The costs move to queue time, fair-share, and capability. |

---

## Part 1 — How the pieces fit

There are three layers. The **model host** is Ollama, running inside an Apptainer container on a GPU node that Slurm allocated to you. The **harness** is the coding agent (Claude Code, Aider, Continue) that sends requests and executes tool calls against your files. The **transport** is whatever connects the two, which is either nothing (same machine) or an SSH tunnel.

```text
Pattern A — everything on the GPU node (recommended)

  GPU node (your Slurm job)
  ┌──────────────────────────────────────────┐
  │  claude ──► Ollama @ 127.0.0.1:<random>  │
  │  your repo in /home, /projects, /scratch │
  └──────────────────────────────────────────┘

Pattern B — harness on your laptop

  Laptop                     Login node                 GPU node (your Slurm job)
  claude ──► 127.0.0.1:11435 ══ ssh tunnel ══► <node>:<proxy> ──► Caddy (token check)
                                                                     │
                                                                     ▼
                                                     Ollama @ 127.0.0.1:<random>
```

**Pattern A** keeps the model and the harness inside the same job. There is no network exposure beyond the node itself, nothing to tunnel, and your code stays on Northeastern storage. Use it unless you have a specific reason not to.

**Pattern B** keeps your editor and files on your laptop and sends only inference traffic to the cluster. It requires Ollama to be reachable from the login node, which means it must listen on the node's network interface, which means it needs an authentication layer in front. Whether RC permits this forwarding is one of the questions in Part 10.

**Pattern C**, a standing endpoint shared by a cohort, is not something a Slurm job is designed to be. Part 10 explains why and gives you the questions to put to RC.

---

## Part 2 — One-time setup

Run these once. They create a private working directory, pull the container images to cluster storage instead of your home quota, and install Claude Code on the cluster.

**Step 1.** Connect to Explorer.

```bash
ssh <your-nu-username>@login.explorer.northeastern.edu
```

**Step 2.** Get a CPU node for setup work. Container pulls and unpacking shouldn't run on the login node.

```bash
srun --partition=short --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=8G --time=01:00:00 --pty /bin/bash
```

**Step 3.** Create the environment file. This defaults to `/scratch/$USER/llm`, which needs no editing but is subject to scratch purge policy. If your PI has `/projects` space, change `LLM_ROOT` to a directory there so model weights persist.

```bash
mkdir -p ~/.ollama-hpc && chmod 700 ~/.ollama-hpc
cat > ~/.ollama-hpc/env.sh << 'EOF'
# Storage. Change to /projects/<group>/$USER/llm if your PI has project space.
export LLM_ROOT="/scratch/$USER/llm"

export OLLAMA_SIF="$LLM_ROOT/images/ollama.sif"
export CADDY_SIF="$LLM_ROOT/images/caddy.sif"
export OLLAMA_MODELS="$LLM_ROOT/models"
export APPTAINER_CACHEDIR="$LLM_ROOT/apptainer-cache"
export APPTAINER_TMPDIR="$LLM_ROOT/apptainer-tmp"

# Model and context window. See Part 3.
export LLM_MODEL="qwen3-coder:30b"
export LLM_CONTEXT=65536
EOF
```

**Step 4.** Create the directories and pull the images. Apptainer otherwise caches into a hidden directory in `/home`, which fills your quota.

```bash
source ~/.ollama-hpc/env.sh
mkdir -p "$LLM_ROOT/images" "$LLM_ROOT/run" "$OLLAMA_MODELS" "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"
apptainer pull "$OLLAMA_SIF" docker://ollama/ollama:latest
apptainer pull "$CADDY_SIF" docker://caddy:2
apptainer exec "$OLLAMA_SIF" ollama --version
```

Write down the version printed by the last command. You need 0.14 or later for the Anthropic-compatible API. Once you have a version that works, pin it (for example `docker://ollama/ollama:<version>`) so a course cohort doesn't drift onto different builds.

**Step 5.** Create the start script. You'll `source` it inside every GPU job. It picks a random free port so you don't collide with other users on a shared node, binds Ollama to localhost only, and defines an `ollama` shell function that talks to your server rather than the image's default port.

```bash
cat > ~/.ollama-hpc/start-ollama.sh << 'EOF'
# Source this inside a GPU job:  source ~/.ollama-hpc/start-ollama.sh
source ~/.ollama-hpc/env.sh

if [ -z "$SLURM_JOB_ID" ]; then
  echo "Not inside a Slurm job. Start a GPU job first." >&2
  return 1 2>/dev/null || exit 1
fi

export OLLAMA_PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')
export RUN_DIR="$LLM_ROOT/run/$SLURM_JOB_ID"
mkdir -p "$RUN_DIR" && chmod 700 "$RUN_DIR"

# --env is required: the image sets OLLAMA_HOST=0.0.0.0:11434, which would override a plain export.
apptainer exec --nv -B "$LLM_ROOT" \
  --env OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT" \
  --env OLLAMA_MODELS="$OLLAMA_MODELS" \
  --env OLLAMA_CONTEXT_LENGTH="$LLM_CONTEXT" \
  --env OLLAMA_NUM_PARALLEL=1 \
  --env OLLAMA_KEEP_ALIVE=-1 \
  --env OLLAMA_FLASH_ATTENTION=1 \
  "$OLLAMA_SIF" ollama serve > "$RUN_DIR/ollama.log" 2>&1 &
export OLLAMA_PID=$!

for i in $(seq 1 90); do
  curl -sf "http://127.0.0.1:$OLLAMA_PORT/api/version" > /dev/null && break
  sleep 1
done
if ! curl -sf "http://127.0.0.1:$OLLAMA_PORT/api/version" > /dev/null; then
  echo "Ollama did not start. See $RUN_DIR/ollama.log" >&2
  return 1 2>/dev/null || exit 1
fi

ollama() {
  apptainer exec -B "$LLM_ROOT" --env OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT" "$OLLAMA_SIF" ollama "$@"
}
export -f ollama

echo "Ollama is up on 127.0.0.1:$OLLAMA_PORT (pid $OLLAMA_PID). Log: $RUN_DIR/ollama.log"
EOF
```

**Step 6.** Create the Claude Code configuration script for Pattern A.

```bash
cat > ~/.ollama-hpc/claude-local.sh << 'EOF'
# Source this after start-ollama.sh:  source ~/.ollama-hpc/claude-local.sh
if [ -z "$OLLAMA_PORT" ]; then
  echo "Run: source ~/.ollama-hpc/start-ollama.sh first." >&2
  return 1 2>/dev/null || exit 1
fi
export PATH="$HOME/.local/bin:$PATH"
unset ANTHROPIC_API_KEY
export ANTHROPIC_BASE_URL="http://127.0.0.1:$OLLAMA_PORT"
export ANTHROPIC_AUTH_TOKEN="ollama"
export ANTHROPIC_MODEL="$LLM_MODEL"
export ANTHROPIC_DEFAULT_OPUS_MODEL="$LLM_MODEL"
export ANTHROPIC_DEFAULT_SONNET_MODEL="$LLM_MODEL"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="$LLM_MODEL"
export CLAUDE_CODE_SUBAGENT_MODEL="$LLM_MODEL"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
echo "Claude Code -> $ANTHROPIC_BASE_URL using $LLM_MODEL"
EOF
```

`unset ANTHROPIC_API_KEY` matters. If a real key is in your environment, Claude Code will send it to whatever is listening at the base URL.

**Step 7.** Create a persistent token for Pattern B. It stays the same across jobs so IDE configurations keep working. Regenerate it any time to revoke access.

```bash
openssl rand -hex 32 > ~/.ollama-hpc/token && chmod 600 ~/.ollama-hpc/token
```

**Step 8.** Leave the setup node, then install Claude Code on the login node (it's a small download).

```bash
exit
```

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc && claude --version
```

---

## Part 3 — Choose a GPU and a model

Two numbers decide whether a setup works: the model's weights must fit in VRAM, and there must be room left for the context window's KV cache. If either spills, Ollama offloads layers to CPU and generation slows to a crawl.

| Model (Ollama tag) | Approximate size | Reasonable GPU | Notes |
|---|---|---|---|
| `gpt-oss:20b` | ~14 GB | A100, H200 | Listed by Ollama as a recommended local model for Claude Code. Fast. |
| `qwen3-coder:30b` | ~19 GB | A100, H200 | Coding-tuned mixture-of-experts, also on Ollama's recommended list. The default in `env.sh`. |
| `glm-4.7-flash` | ~23 GB VRAM at 64k context (Ollama's figure) | A100, H200 | Recommended by Ollama for coding tools. |
| `gpt-oss:120b` | ~65 GB | A100 80 GB, H200 | The strongest of these that fits on a single GPU. Request more host memory (`--mem=64G`). |
| `deepseek-r1:1.5b` | ~1 GB | Anything | Not suitable for agentic coding. Fine for testing that the server starts. |

Sizes are approximate. Check the model's page on ollama.com for the exact download size and confirm it has the **tools** label before you pull it. A model without tool support will print tool calls as plain text instead of executing them.

The `gpu` partition allows one GPU per job, so stay within a single card. On an H200 every model in the table fits with a large context. On older cards such as V100 or T4, current Ollama builds may not support the GPU or may fall back to CPU; check the log as shown in Part 4, step 5, and request a newer type if that happens.

On context: Ollama's documentation says agents and coding tools need at least 64,000 tokens. `env.sh` sets 65,536. On an H200 you can raise `LLM_CONTEXT` to 131072 for long sessions. If you are short on VRAM, adding `--env OLLAMA_KV_CACHE_TYPE=q8_0` to the `apptainer exec` line in `start-ollama.sh` roughly halves KV-cache memory at a small quality cost.

---

## Part 4 — Pattern A: model and harness on the same GPU node

**Step 1.** From the login node, consider starting `tmux` first so a dropped connection doesn't kill your session. Note which login node you're on; you'll need to reconnect to the same one to reattach.

```bash
tmux new -s llm
```

**Step 2.** Request an interactive GPU session. At the time of writing, `gpu-interactive` defaults to 1 hour with a 2-hour maximum and allows one GPU. Requesting a specific GPU type can lengthen the wait.

```bash
srun --partition=gpu-interactive --nodes=1 --ntasks=1 --gres=gpu:h200:1 --cpus-per-task=4 --mem=32G --time=02:00:00 --pty /bin/bash
```

You can also launch a JupyterLab or desktop session on `gpu-interactive` through Open OnDemand and run the remaining steps in its terminal.

**Step 3.** Start Ollama.

```bash
source ~/.ollama-hpc/start-ollama.sh
```

**Step 4.** Pull the model. The first pull takes a few minutes; later jobs reuse the copy in `$OLLAMA_MODELS`.

```bash
ollama pull "$LLM_MODEL"
```

**Step 5.** Run a smoke test against the Anthropic-compatible endpoint, then confirm the model is fully on the GPU with the context you asked for.

```bash
curl -s "http://127.0.0.1:$OLLAMA_PORT/v1/messages" \
  -H "content-type: application/json" \
  -H "x-api-key: ollama" \
  -H "anthropic-version: 2023-06-01" \
  -d "{\"model\": \"$LLM_MODEL\", \"max_tokens\": 64, \"messages\": [{\"role\": \"user\", \"content\": \"Reply with the single word: ready\"}]}"
```

```bash
ollama ps
```

In the `ollama ps` output, `PROCESSOR` should read `100% GPU` and `CONTEXT` should match `LLM_CONTEXT`. If you see a CPU/GPU split, the model or context is too large for the card. To confirm Ollama found the GPU at all:

```bash
grep -i "inference compute" "$RUN_DIR/ollama.log"
```

**Step 6.** Configure Claude Code for this session.

```bash
source ~/.ollama-hpc/claude-local.sh
```

**Step 7.** Move to your project and start Claude Code. Replace the path with your repository.

```bash
cd ~/path/to/your/repo
```

```bash
claude
```

Inside Claude Code, run `/status` to confirm it is using your local base URL rather than Anthropic's API. If you also use Claude Code with a subscription on this account, the environment credential takes precedence while these variables are set; `/status` is how you check.

**Step 8.** When you're done, exit Claude Code and then exit the `srun` shell. Exiting ends the job and returns the GPU to the queue.

```bash
exit
```

Some Claude Code features don't carry over to a local backend. Server-side tools such as web search run on Anthropic's infrastructure and won't work, and Anthropic-style prompt caching is not supported by Ollama's compatibility layer. Keep MCP servers to a minimum; every tool schema consumes context the model needs for your code.

---

## Part 5 — Pattern A in batch: headless runs

The scheduler is built for batch work, and so is this setup. A headless Claude Code run inside `sbatch` keeps the GPU busy for the life of the job, doesn't trip the IdleBot, and doesn't require you to sit at a terminal.

**Step 1.** Create the batch script.

```bash
cat > ~/.ollama-hpc/headless.sbatch << 'SBATCH_EOF'
#!/bin/bash
#SBATCH --job-name=claude-headless
#SBATCH --partition=gpu
#SBATCH --gres=gpu:h200:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=%x-%j.out
# Usage: sbatch ~/.ollama-hpc/headless.sbatch /path/to/repo /path/to/task.md

REPO="$1"
TASK="$2"
source ~/.ollama-hpc/start-ollama.sh || exit 1
ollama pull "$LLM_MODEL" || exit 1
source ~/.ollama-hpc/claude-local.sh || exit 1
cd "$REPO" || exit 1
claude -p "$(cat "$TASK")" --permission-mode acceptEdits
SBATCH_EOF
```

**Step 2.** Write the task as a markdown file, put the repository on a fresh git branch, and submit. Replace the paths with yours.

```bash
sbatch ~/.ollama-hpc/headless.sbatch ~/path/to/your/repo ~/path/to/task.md
```

`acceptEdits` lets the agent change files without prompting; shell commands still require permission and will be refused in a non-interactive run unless you allow them in the project's `.claude/settings.json`. Review the branch's diff before merging anything. Check `claude --help` on your installed version for current flag names.

---

## Part 6 — Pattern B: harness on your laptop

This pattern depends on RC allowing SSH forwarding from a login node to a port on your compute node. Confirm that before teaching it (Part 10).

Because the laptop reaches the node through the login node, the proxy has to listen on the node's cluster-network interface. Ollama itself stays on localhost; Caddy sits in front and rejects any request that doesn't carry your bearer token. Claude Code sends `ANTHROPIC_AUTH_TOKEN` as `Authorization: Bearer <token>`, so the proxy is transparent to it.

**Step 1.** On the login node, create the server job.

```bash
cat > ~/.ollama-hpc/serve.sbatch << 'SBATCH_EOF'
#!/bin/bash
#SBATCH --job-name=ollama-serve
#SBATCH --partition=gpu
#SBATCH --gres=gpu:h200:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=%x-%j.out

source ~/.ollama-hpc/start-ollama.sh || exit 1
ollama pull "$LLM_MODEL" || exit 1

PROXY_PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("0.0.0.0", 0)); print(s.getsockname()[1]); s.close()')
TOKEN=$(cat ~/.ollama-hpc/token)
umask 077

cat > "$RUN_DIR/Caddyfile" << CADDY_EOF
{
    admin off
    auto_https off
}
:${PROXY_PORT} {
    @authorized header Authorization "Bearer ${TOKEN}"
    handle @authorized {
        reverse_proxy 127.0.0.1:${OLLAMA_PORT}
    }
    handle {
        respond "unauthorized" 401
    }
}
CADDY_EOF

cat > ~/.ollama-hpc/current << CONN_EOF
NODE=$(hostname)
PROXY_PORT=${PROXY_PORT}
MODEL=${LLM_MODEL}
JOB=${SLURM_JOB_ID}
CONN_EOF
trap 'rm -f ~/.ollama-hpc/current' EXIT TERM INT

echo "Serving $LLM_MODEL on $(hostname):$PROXY_PORT behind token auth"
apptainer exec -B "$LLM_ROOT" \
  --env XDG_CONFIG_HOME="$RUN_DIR/caddy-config" \
  --env XDG_DATA_HOME="$RUN_DIR/caddy-data" \
  "$CADDY_SIF" caddy run --config "$RUN_DIR/Caddyfile" --adapter caddyfile
SBATCH_EOF
```

`admin off` disables Caddy's admin API, which would otherwise open another unauthenticated port on the node. The `XDG_*` overrides point Caddy at writable directories, because the container image's defaults are read-only under Apptainer.

**Step 2.** Submit the job and wait for it to reach the `R` (running) state.

```bash
sbatch ~/.ollama-hpc/serve.sbatch
```

```bash
squeue -u $USER
```

**Step 3.** On your **laptop**, add an SSH host entry. Replace `YOUR_NU_USERNAME`. Connection sharing means you authenticate once instead of on every command.

```bash
cat >> ~/.ssh/config << 'SSH_EOF'

Host explorer
    HostName login.explorer.northeastern.edu
    User YOUR_NU_USERNAME
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 4h
SSH_EOF
```

**Step 4.** On your laptop, create the tunnel script. It reads the running job's node and port, checks the job is alive, writes a private environment file, and opens the tunnel.

```bash
mkdir -p ~/bin
cat > ~/bin/explorer-llm << 'LAPTOP_EOF'
#!/bin/bash
set -euo pipefail
HOST="explorer"
LOCAL_PORT="${LOCAL_PORT:-11435}"

CONN="$(ssh "$HOST" 'cat ~/.ollama-hpc/current 2>/dev/null' || true)"
if [ -z "$CONN" ]; then
  echo "No running server. Submit one: ssh $HOST 'sbatch ~/.ollama-hpc/serve.sbatch'" >&2
  exit 1
fi
NODE="$(printf '%s\n' "$CONN" | sed -n 's/^NODE=//p')"
PROXY_PORT="$(printf '%s\n' "$CONN" | sed -n 's/^PROXY_PORT=//p')"
MODEL="$(printf '%s\n' "$CONN" | sed -n 's/^MODEL=//p')"
JOB="$(printf '%s\n' "$CONN" | sed -n 's/^JOB=//p')"
STATE="$(ssh "$HOST" "squeue -h -j $JOB -o %T" 2>/dev/null || true)"
if [ "$STATE" != "RUNNING" ]; then
  echo "Job $JOB is not running (state: ${STATE:-gone}). Resubmit serve.sbatch." >&2
  exit 1
fi
TOKEN="$(ssh "$HOST" 'cat ~/.ollama-hpc/token')"

umask 077
cat > ~/.explorer-llm.env << ENV_EOF
unset ANTHROPIC_API_KEY
export ANTHROPIC_BASE_URL="http://127.0.0.1:${LOCAL_PORT}"
export ANTHROPIC_AUTH_TOKEN="${TOKEN}"
export ANTHROPIC_MODEL="${MODEL}"
export ANTHROPIC_DEFAULT_OPUS_MODEL="${MODEL}"
export ANTHROPIC_DEFAULT_SONNET_MODEL="${MODEL}"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="${MODEL}"
export CLAUDE_CODE_SUBAGENT_MODEL="${MODEL}"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export OPENAI_API_BASE="http://127.0.0.1:${LOCAL_PORT}/v1"
export OPENAI_API_KEY="${TOKEN}"
ENV_EOF

echo "Job $JOB on $NODE: localhost:$LOCAL_PORT -> $NODE:$PROXY_PORT"
echo "Leave this window open. In another terminal: source ~/.explorer-llm.env && claude"
exec ssh -N -L "${LOCAL_PORT}:${NODE}:${PROXY_PORT}" "$HOST"
LAPTOP_EOF
chmod +x ~/bin/explorer-llm
```

The local port is 11435 rather than 11434 so it doesn't collide with an Ollama install on your laptop.

**Step 5.** Open the tunnel and leave that terminal running.

```bash
~/bin/explorer-llm
```

**Step 6.** In a second laptop terminal, confirm the proxy rejects unauthenticated requests and accepts yours. The first command should print `401`; the second should return a short message.

```bash
source ~/.explorer-llm.env && curl -s -o /dev/null -w "%{http_code}\n" "$ANTHROPIC_BASE_URL/api/version"
```

```bash
source ~/.explorer-llm.env && curl -s "$ANTHROPIC_BASE_URL/v1/messages" \
  -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
  -H "content-type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d "{\"model\": \"$ANTHROPIC_MODEL\", \"max_tokens\": 64, \"messages\": [{\"role\": \"user\", \"content\": \"Reply with the single word: ready\"}]}"
```

**Step 7.** Start Claude Code from your project directory in that same terminal.

```bash
source ~/.explorer-llm.env && claude
```

**Step 8.** When finished, close Claude Code, press Ctrl-C in the tunnel window, and cancel the server so the GPU goes back to the queue.

```bash
ssh explorer 'scancel --name=ollama-serve'
```

Two residual risks remain, and you should know them rather than discover them. The proxy blocks access from elsewhere on the cluster, but Ollama's own random localhost port is still reachable by other users who have jobs on the same node; a random port is obscurity, not security. And `~/.explorer-llm.env` holds the token in plain text on your laptop, protected only by file permissions.

---

## Part 7 — Other harnesses

**Aider, Pattern A (on the node).** Install Aider per its documentation (for example `python -m pip install --user aider-install && aider-install`), then, inside a job where `start-ollama.sh` has run:

```bash
export OLLAMA_API_BASE="http://127.0.0.1:$OLLAMA_PORT" && aider --model "ollama_chat/$LLM_MODEL"
```

**Aider, Pattern B (laptop, through the proxy).** The proxy requires a bearer token, which Aider's Ollama-native provider doesn't send, so use its OpenAI-compatible mode. The environment file already sets `OPENAI_API_BASE` and `OPENAI_API_KEY`. Run this in a dedicated terminal so those variables don't leak into other tools.

```bash
source ~/.explorer-llm.env && aider --model "openai/$ANTHROPIC_MODEL"
```

Aider may warn that it doesn't know this model's context window. The warning is harmless because the server enforces `OLLAMA_CONTEXT_LENGTH`; an OpenAI-compatible client has no field to request a context size anyway.

**Continue (VS Code / JetBrains), Pattern B.** Add a model to `~/.continue/config.yaml`. Paste the token from `~/.ollama-hpc/token` on the cluster in place of the placeholder.

```yaml
name: Explorer LLM
version: 1.0.0
schema: v1
models:
  - name: Explorer qwen3-coder
    provider: openai
    model: qwen3-coder:30b
    apiBase: http://127.0.0.1:11435/v1
    apiKey: PASTE_TOKEN_HERE
    roles:
      - chat
      - edit
      - apply
```

**Codex, OpenCode, Droid.** Ollama's `ollama launch` command configures these tools automatically when Ollama runs on the same machine at its default port. On Explorer the port is randomized and, in Pattern B, sits behind a token, so configure them as OpenAI-compatible providers using the base URL and key from `~/.explorer-llm.env`. Their configuration formats change often; follow each tool's current documentation rather than a copied snippet.

---

## Part 8 — Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `404` on every request | Base URL includes `/v1` | Use `http://127.0.0.1:<port>` for Claude Code. Only OpenAI-compatible clients take `/v1`. |
| Error mentioning a model like `claude-haiku-…` not found | Alias models not mapped | Source `claude-local.sh` (Pattern A) or `~/.explorer-llm.env` (Pattern B), which set all `ANTHROPIC_DEFAULT_*_MODEL` variables. |
| Claude Code hangs or gives incoherent answers on the first prompt | Context window too small, prompt silently truncated | Check `CONTEXT` in `ollama ps`. Confirm `OLLAMA_CONTEXT_LENGTH` reached the server via `--env`. Update both Ollama and Claude Code if it persists; hangs with local backends have been reported against specific version pairs. |
| Tool calls appear as raw JSON or XML in the chat | Model lacks tool support in Ollama | Choose a model with the **tools** label. |
| `ollama ps` shows a CPU/GPU split | Weights plus KV cache exceed VRAM | Lower `LLM_CONTEXT`, use `OLLAMA_KV_CACHE_TYPE=q8_0`, pick a smaller model, or request a larger GPU. |
| No `inference compute` line naming CUDA in the log | Container didn't see the GPU | Confirm `--nv` is present and you're on a GPU node (`nvidia-smi`). |
| `ollama` commands report "connection refused" | Client hitting the image's default port | Use the `ollama` function from `start-ollama.sh`, not a bare `apptainer exec … ollama`. |
| `401` from the proxy | Token mismatch | Re-run `~/bin/explorer-llm` to rewrite the env file; check you didn't regenerate the token mid-job. |
| Tunnel connects but requests hang | Job ended or node/port changed | Re-run `~/bin/explorer-llm`; it checks the job state first. |
| Email from the IdleBot | GPU under-used for 15 minutes | Finish up or `scancel`. Don't add synthetic load (see Part 9). |
| Home quota full | Image cache or models defaulted to `/home` | Confirm `APPTAINER_CACHEDIR` and `OLLAMA_MODELS` point under `LLM_ROOT`; clear `~/.apptainer` and `~/.ollama/models`. |
| `ollama pull` fails on the compute node | No outbound network from that node, or registry issue | Ask RC whether compute-node egress is available; models can also be imported from GGUF files staged through the transfer node. |

---

## Part 9 — Operating within the cluster's rules

Explorer runs a GPU IdleBot. If an allocated GPU is under-utilized for 15 minutes, it emails you; if the GPU stays under-utilized for an hour, it cancels the job. An inference server waiting for your next prompt is, from the GPU's point of view, idle. Interactive coding is bursty, with long gaps while you read diffs and think, so a Pattern A or B session that you walk away from will be flagged and then cancelled. That is the policy working as intended.

Do not keep a job alive by running filler work on the GPU. That defeats a fairness mechanism other users depend on, and it's the kind of thing that ends with RC restricting access for everyone using this workflow. Start a session when you sit down, cancel it when you stop, and move long unattended work into batch jobs (Part 5), where the GPU is genuinely busy.

Cancel what you're not using. `squeue -u $USER` shows your jobs; `scancel <jobid>` ends one.

---

## Part 10 — The shared endpoint question (what INC23568600 is really asking)

The ticket asks whether it's acceptable to run "a small self-hosted LLM inference endpoint." A personal session in your own allocation (Patterns A and B) and a standing endpoint for a group of people are different things, and the second runs into the cluster's design in several ways.

A Slurm job has a wall-clock limit (8 hours maximum on `gpu` at the time of writing), so an endpoint built on one dies on a schedule and comes back on a different node with a different address. Between users' requests the GPU is idle, which the IdleBot treats as waste. Ollama is optimized for one user; with `OLLAMA_NUM_PARALLEL` above 1 it serves concurrent requests by splitting memory across slots, each slot needing its own context-sized KV cache, so a 64k context for five students costs roughly five times the KV memory. A multi-user deployment would usually use vLLM instead, which batches concurrent requests continuously and supports API keys; recent vLLM releases also expose an Anthropic-compatible `/v1/messages` endpoint, but verify that on the version you deploy. And a shared endpoint means other people's code and prompts pass through a service you run, which raises questions about logging, retention, and who is responsible when it breaks.

On "AICR or Discovery": Discovery has been superseded by Explorer, and all public GPUs now live there. AICR is the newer AI Compute Resource cluster at MGHPCC, with 248 NVIDIA B200 and 152 NVIDIA RTX Pro GPUs and access granted by proposal. Whether AICR's scheduling and idle policies would treat a standing inference service differently from Explorer's is a question only RC can answer.

If RC's reply on the ticket hasn't already settled these points, the following can go back to them as-is:

```text
Thanks for the update on INC23568600. To make sure what we run fits Explorer's policies, could you confirm the following?

1. Running Ollama inside a gpu or gpu-interactive allocation for one user's interactive coding session is acceptable, given that GPU utilization is bursty and the IdleBot may flag gaps between requests.

2. SSH local port forwarding from a login node to a port on the compute node running my job (ssh -L <local>:<node>:<port> login.explorer.northeastern.edu) is permitted.

3. A process in my job may listen on the compute node's cluster-network interface if it sits behind a bearer-token reverse proxy, or services should bind to localhost only.

4. For a shared endpoint serving a small cohort of students and fellows, RC's preferred route: a managed service hosted by RC, a reservation, or an AICR allocation (for example on the RTX Pro nodes). We would want per-user tokens and no prompt logging beyond what RC requires.

5. The preferred storage location and quota for model weights, which run roughly 15 to 70 GB per model.

I'm happy to share the job scripts for review.
```

---

## Part 11 — What to expect

Open-weight models in the 20B–120B range are capable, but they are not frontier models, and Claude Code's agent loop is demanding. It sends a long system prompt, dozens of tool schemas, and growing conversation history on every turn, and it expects the model to call tools precisely, recover from errors, and stay on task across many steps. Expect more malformed tool calls, more loops, and earlier loss of the thread on large multi-file changes than you'd see with Claude. Long sessions also slow down as context grows, because the compatibility layer doesn't support Anthropic's prompt caching.

Where this setup does well: well-scoped tasks with clear acceptance criteria, bulk work over many files in batch jobs, work on code that shouldn't leave Northeastern infrastructure, and teaching situations where students benefit from seeing how a smaller model's behavior differs from a frontier model's on the same task. Where it does poorly: open-ended refactors, debugging that requires sustained reasoning across a large codebase, and anything where a wrong tool call is expensive.

A practical split is to use the local model for drafting, boilerplate, tests, and batch passes, and to reserve frontier-model credits for the hard problems. Measured that way, the savings are real. Measured as "the same thing, for free," they aren't.

---

## Further reading

Ollama, Anthropic compatibility (supported features, `/v1/messages`, environment variables): https://docs.ollama.com/api/anthropic-compatibility

Ollama, context length (VRAM-based defaults, the 64k recommendation for coding tools, `ollama ps`): https://docs.ollama.com/context-length

Ollama blog, Claude Code with Anthropic API compatibility (v0.14): https://ollama.com/blog/claude

Ollama blog, `ollama launch` (Claude Code, OpenCode, Codex, Droid; recommended coding models): https://ollama.com/blog/launch

Claude Code, environment variables (`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, model alias variables): https://code.claude.com/docs/en/env-vars

Northeastern RC, partitions on Explorer: https://rc.northeastern.edu/partitions

Northeastern RC, GPU IdleBot: https://rc-docs.northeastern.edu/en/explorer-main/gpus/idlebot.html

Northeastern RC, H200 quick start (srun and sbatch examples): https://rc-docs.northeastern.edu/en/explorer-main/gpus/quickstart-h200.html

Northeastern RC, Apptainer on Explorer (bind mounts, cache directories): https://rc-docs.northeastern.edu/en/explorer-main/containers/apptainer.html

Northeastern RC, connecting to Explorer: https://rc-docs.northeastern.edu/en/latest/connectingtocluster/linux.html

Northeastern RC, July 2025 operational changes (gpu-interactive queue, IdleBot, no direct SSH to GPU nodes): https://researchcomputing.sites.northeastern.edu/2025/07/29/research-computing-operational-improvements-on-the-explorer-cluster

Aider, Ollama setup: https://aider.chat/docs/llms/ollama.html

Continue, model configuration: https://docs.continue.dev
