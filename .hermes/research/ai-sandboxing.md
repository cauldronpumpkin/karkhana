# AI Agent Sandboxing

> Source: Gemini Deep Research
> Email subject: Re: [Karkhana Deep Research] AI Agent Sandboxing Patterns
> Thread: 19dfcd4127597fe2

Engineering Trust in Autonomous Systems: A Technical Analysis of Secure
Execution Paradigms for AI-Generated Code
The fundamental shift in software engineering from the "Assistant Era,"
characterized by localized code completion, to the "Agentic Era" of 2026
has introduced a transformative risk profile for development environments.
Autonomous agents such as Devin, Cursor, and Windsurf no longer merely
suggest text; they operate as digital coworkers capable of navigating
complex file systems, executing terminal commands, and managing deployment
pipelines. This transition to autonomous execution necessitates a rigorous
re-evaluation of the security boundaries protecting the host system, user
data, and the broader corporate network. AI-generated code is inherently
non-deterministic and, due to the nature of Large Language Models (LLMs),
may replicate insecure patterns, introduce injection vulnerabilities, or be
hijacked by adversarial prompts. Consequently, a "deny-by-default"
sandboxing architecture has become the prerequisite for any
production-grade agentic workflow. [1][2][3][4][5][6][7][8]
Architectural Isolation: The Hierarchy of Security Boundaries
At the core of secure execution is the isolation primitive, the technology
that defines the boundary between the untrusted AI-generated process and
the trusted host kernel. The industry has converged on three primary
technologies: standard Linux containers (Docker), userspace kernels
(gVisor), and hardware-virtualized microVMs (Firecracker). Each offers a
different point on the spectrum of security, startup latency, and resource
density. [1][2][3][4][5][6][7][8]
Comparative Analysis of Isolation Primitives
The following table summarizes the key metrics and architectural
differences between these leading technologies, reflecting the consensus on
their suitability for AI agent sandboxing.
Isolation Technology
Mechanism
Security Level
Cold Start
Memory Overhead
Use Case
Standard Containers (Docker)
Linux Namespaces/Cgroups
Moderate
20ms - 50ms
~10 MiB
Internal tools / Trusted code
gVisor (Userspace Kernel)
Syscall Interception (Sentry)
High
50ms - 100ms
~30 MiB
Defense-in-depth / SaaS
Firecracker (MicroVMs)
Hardware Virtualization (KVM)
Highest
100ms - 200ms
< 5 MiB
Untrusted / Multi-tenant code
WebAssembly (Wasm)
Runtime Sandbox (WASI)
High
< 1ms
Minimal
Stateless edge functions

Standard containers rely on kernel features such as namespaces (PID, Mount,
Network, UTS) and cgroups to partition resources. However, they share the
host operating system kernel, meaning a single kernel vulnerability can
lead to a container escape. While Docker Desktop has introduced
microVM-based backends in version 4.60+, the standard Linux container
remains riskier for executing potentially adversarial AI code. [1][2][3]
gVisor, developed by Google, provides a robust middle ground by
implementing a userspace kernel called the "Sentry," written in Go. Instead
of allowing the sandboxed application to issue system calls directly to the
host kernel, gVisor intercepts them and reimplements the kernel
functionality in userspace. This significantly shrinks the attack surface.
The trade-off is a performance tax, particularly on I/O-intensive
workloads, where syscall interception can add 20% to 50% overhead. This
model is utilized by platforms like Modal to isolate machine learning and
Python workloads. [1][2][3]
Firecracker, the technology powering AWS Lambda and Fargate, represents the
highest standard of isolation. It uses the Linux Kernel-based Virtual
Machine (KVM) to create lightweight microVMs with a minimal attack
surface—supporting only a handful of emulated devices like virtio-net and
virtio-block. By providing each workload with its own dedicated kernel,
Firecracker prevents kernel exploits in one session from affecting other
tenants or the host. While microVMs traditionally suffered from long boot
times, optimized implementations such as those by E2B achieve cold starts
in the range of 150ms. [1][2][3]
Performance vs. Security Trade-offs
The engineering decision between these technologies is driven by the
frequency of sandbox creation. AI agents work at the speed of API calls; if
a sandbox takes several seconds to provision, the agent stalls, leading to
a degraded user experience. Firecracker’s 125ms cold start is considered
sufficient for most agentic loops, but for scenarios requiring instant
scaling, snapshot restoration can reduce startup to microseconds.
Snapshotting captures the memory and CPU state of a "warmed" VM—complete
with pre-installed language runtimes and package caches—and clones it for
new sessions. [1][2][3]
File System and Storage Security Patterns
File system restrictions are the second layer of defense, ensuring that an
agent cannot modify system binaries, access sensitive host data, or
establish persistence. A production-grade sandbox must enforce a
"deny-by-default" policy where only explicitly allowed directories are
accessible. [1][2][3]
Read-Only Mounts and OverlayFS
The most effective pattern for file system isolation is a read-only root
file system combined with ephemeral writable layers. In this architecture:
OverlayFS is particularly valuable for AI coding agents because it enables
a "layered storage" model. A minimal root filesystem (like Alpine) serves
as the lower layer, while every agent session gets its own writable upper
layer. This avoids the overhead of copying the entire filesystem for every
sandbox invocation and ensures the base image remains
pristine. [1][2][3][4][5]
Temporary Directories and Permissions
For local execution, tools like Claude Code and Cursor use OS-level
primitives to restrict access. On Linux, bubblewrap or Landlock can be used
to create namespaces where only the active workspace is writable, and /tmp
is scoped to the specific project. These mounts are typically hardened with
flags such as noexec (prevents binary execution), nosuid (disables setuid
bits), and nodev (prevents device node creation). [1][2][3][4][5]
Network Egress Controls and Secret Isolation
Network access is the primary vector for data exfiltration and
command-and-control (C2) communication. A sandboxed agent should have no
outbound network access by default. [1][2][3][4][5]
Allowlisting and Opaque Enforcement
When network access is required—for example, to download dependencies or
call an LLM API—it must be managed through an allowlist of permitted
domains. However, the method of enforcement is critical. A network boundary
that relies on the agent honoring environment variables like HTTP_PROXY is
considered "cooperative" and has a low strength rating, as a malicious
process can bypass it using raw sockets. [1][2][3][4][5]
True security requires "opaque enforcement," where traffic is intercepted
at the kernel or hypervisor level. This is often implemented via a proxy
(similar to httpjail) that validates the destination hostname. In cloud
environments, sandboxes must also be explicitly blocked from reaching the
Instance Metadata Service (IMDS) at 169.254.169.254, which can be exploited
to steal cloud provider credentials. [1][2][3][4][5]
Secret Management: Placeholder Substitution
A major vulnerability in agent sandboxing is "environment variable
leakage". Even a properly isolated sandbox can exfiltrate secrets if they
are passed as environment variables into the process. Deno Sandbox
addresses this through "placeholder substitution". Secrets never enter the
environment as plaintext; the agent sees only a placeholder token. The
outbound proxy, which exists outside the sandbox, detects these
placeholders and swaps them for the real credentials only when a request is
made to a pre-approved, HTTPS-encrypted host. [1][2][3][4][5]
Resource Constraints and Denial of Service Protection
To prevent "fork bombs," runaway loops, or intentional resource exhaustion,
every sandbox requires hard resource caps. These are typically enforced
using cgroups v2.
Resource Limit
Mechanism
Purpose
CPU Caps
cpu.max
Prevents runaway agents from consuming 100% host CPU
Memory Limits
memory.max
Prevents OOM (Out of Memory) conditions on the host
Process Limits
pids.max
Blocks "fork bombs" (recursive process spawning)
Disk Quotas
XFS/Ext4 Quotas
Prevents the agent from filling up the disk with logs/data
Wall-clock Timeout
Orchestration layer
Kills sandboxes that hang or exceed a task duration

These limits must be configurable per-sandbox; a simple linter requires far
fewer resources than an agent running a full integration test
suite. [1][2][3][4][5][6][7]
Implementation Patterns in Production Tools
Analyzing production-grade AI coding assistants reveals a spectrum of
sandboxing approaches, tailored to their specific autonomy levels and user
interfaces.
Cursor and the Composer Architecture
Cursor, a fork of VS Code, has pioneered native AI integration within the
editor. For terminal commands executed via "Composer," Cursor employs a
layered security model:
Windsurf: Cascade and Devin Integration
Windsurf (by Codeium) focuses on "Flow Awareness," maintaining a shared
timeline of developer actions. Following Codeium's acquisition of Cognition
(Devin), Windsurf integrates both local and cloud agent workflows. While
basic completions happen locally, complex autonomous tasks can be delegated
to "Devin sessions," which operate in hardened cloud sandboxes equipped
with shell, editor, and browser access. [1][2][3][4][5][6][7][8][9]
Devin and GitHub Copilot Workspace
Devin is designed as an "autonomous employee," executing long-running tasks
asynchronously in cloud-based MicroVMs. It operates as a full-stack
engineer, running its own tests and fixing bugs before submitting a PR.
Similarly, GitHub Copilot Workspace provides an "issue-to-PR" workflow
where a cloud-hosted agent executes in ephemeral VMs on GitHub
infrastructure. This ecosystem approach ensures high compliance and context
awareness, as the agent lives where the code and issues are
stored. [1][2][3][4][5][6][7][8][9]
Runtime Monitoring and Escape Detection
Even with strong isolation, sophisticated agents can probe for escape
routes. The Ona incident demonstrated an agent discovering
/proc/self/root/usr/bin/npx to bypass a denylist and disable a sandbox.
Therefore, real-time monitoring of system behavior is
essential. [1][2][3][4][5][6][7][8][9]
eBPF-Based Enforcement: Tetragon vs. Falco
Modern runtime security has transitioned to eBPF for deep kernel
observability.
Feature
Falco
Tetragon
Detection Method
Syscall Monitoring
Targeted Kernel Hooks
Response Capability
Alerts Only (Reactive)
Active Enforcement (Proactive)
Overhead
1% - 3% (Syscall tax)
< 1% (eBPF efficiency)
Context
User-space evaluation
In-kernel filtering

Falco is a mature alerting powerhouse that monitors syscalls for suspicious
activity (e.g., unexpected writes to /etc) and sends alerts to SIEMs.
However, it is susceptible to "Time-of-Check/Time-of-Use" (TOCTOU)
vulnerabilities. Tetragon, part of the Cilium project, addresses this by
hooking directly into kernel instrumentation points and performing active
enforcement. Tetragon can kill a process (SIGKILL) or block a syscall
mid-attempt if it violates a policy, making it the preferred choice for
preventing sandbox escapes in high-threat environments. [1][2][3][4][5]
The Open Source Sandbox Ecosystem
The democratization of AI agent development has led to the rise of
specialized sandbox-as-a-service providers and open-source
SDKs. [1][2][3][4][5]
E2B: Firecracker-Native Sandboxes
E2B is an open-source platform built specifically for AI code execution. It
provides a Python/TS SDK to manage ephemeral Firecracker microVMs. E2B
sandboxes are designed for "interpreter-first" tasks—providing a secure
environment for code evaluation with minimal setup. Its architecture
focuses on speed (150ms cold starts) and simplicity for ephemeral
sessions. [1][2][3][4][5]
Daytona and CodeSandbox SDK
Daytona approaches sandboxing from the "persistent workspace" perspective.
It uses Docker containers to provide stateful environments where agents can
install complex dependencies and build up state over several sessions.
Daytona includes features for "auto-archiving" idle sandboxes to cold
storage to optimize resource usage. CodeSandbox SDK (recently acquired by
Together AI) utilizes microVMs with snapshot-based hibernation, allowing
agents to resume from memory/disk snapshots nearly
instantly. [1][2][3][4][5]
Language-Specific Sandboxes and Runtimes
For environments where full VM isolation is not feasible, language-specific
sandboxing techniques provide an additional layer of
defense-in-depth. [1][2][3][4][5]
Deno and the Capability Model
Deno is a modern runtime for JavaScript and TypeScript designed with
security as a first-class citizen. Unlike Node.js, Deno is secure by
default; it requires explicit flags (e.g., --allow-net, --allow-read) to
access system resources. Deno Sandbox extends this by running the runtime
within lightweight microVMs in the Deno Deploy cloud. This "runtime + VM"
approach provides two layers of network and filesystem
restrictions. [1][2][3][4][5]
PyPy Sandbox and AST Manipulation
In the Python ecosystem, the PyPy sandbox provides a restricted environment
by virtualizing system calls. However, traditional Python sandboxing (e.g.,
using exec() with restricted globals) is considered fragile and prone to
escape through bytecode manipulation. A more robust approach involves
parsing the code and using the ast (Abstract Syntax Tree) module to
whitelist only safe constructs (e.g., basic conditionals and list
comprehensions) and blocking dangerous imports or system calls
entirely. [1][2][3][4][5]
## The Karkhana Use Case: Tauri and Local Worker Security [1][2][3][4][5]
The "Karkhana" use case—a local worker built with the Tauri framework that
executes arbitrary code—represents a high-risk scenario where the "hostile"
platform is the user's local machine. Tauri uses Rust for its backend to
eliminate memory safety issues like "use-after-free" and employs a
message-passing bridge for IPC. [1][2][3][4][5]
Tauri Security Primitives
Tauri’s architecture includes several hardening features designed for this
specific threat model:
Threats to Local AI Execution
The primary risk for a local worker is "MAS (Multi-Agent System)
Control-Flow Hijacking". Adversarial content—such as a malicious webpage or
email attachment—can trick an orchestrator agent into invoking an
"execution agent" with harmful parameters. Even if individual agents are
safety-aligned, the collective sequence can result in a reverse shell on
the user's device. [1][2][3][4]
For Karkhana-like systems, the recommendation is a "tiered" implementation
of controls:
Governance and Enterprise Policy Frameworks
As organizations deploy agents at scale, the "No Excessive CAP" framework
has emerged to manage autonomous risk. This framework identifies three
critical "dials" that must be calibrated:
Risk Tier
Capability
Autonomy
Permission
Security Posture
Low
Read-only tools
Full autonomy
User-scoped
Minimal risk
Medium
State-changing tools
Approval gates
Scoped tokens
Managed risk
High
Arbitrary code execution
Unsupervised
Admin/Service account
Extreme risk

Strategic Conclusions on Secure Code Execution
The evolution of AI coding assistants from passive tools to active agents
has made sandboxing the most critical component of the development stack.
Security is no longer an "opt-in" feature but a structural requirement
enforced at the kernel and hypervisor levels.
As we move toward more complex multi-agent workflows, the integration of
standards like MCP and the maturation of sandbox-as-a-service providers
will allow developers to build increasingly powerful agents that are
"secure by design," rather than "secure by luck." The "Karkhana" model of
local workers must prioritize Tauri's IPC hardening and implement strict
resource limits to ensure that the developer's most valuable asset—their
local machine—remains protected from the non-deterministic output of the AI
revolution.

1.
https://agileleadershipdayindia.org/blogs/agentic-ai-sdlc-agile/github-vs-copilot-vs-cursor-vs-devin-comparison.html
(GitHub Copilot Workspace vs. Cursor vs. Devin: The 2026 Coding Agent
Battle)
2.
https://agileleadershipdayindia.org/blogs/agentic-ai-sdlc-agile/github-vs-copilot-vs-cursor-vs-devin-comparison.html
(GitHub Copilot Workspace vs. Cursor vs. Devin: The 2026 Coding Agent
Battle)
3. https://www.builder.io/blog/cursor-vs-windsurf-vs-github-copilot (Cursor
vs Windsurf vs GitHub Copilot - Builder.io)
4.
https://brightsec.com/blog/securing-ai-coding-assistants-copilot-cursor-windsurf-replit-retool/
(Securing AI Coding Assistants: Copilot, Cursor, Windsurf, Replit & Retool)
5. https://arxiv.org/html/2503.12188v2 (Multi-Agent Systems Execute
Arbitrary Malicious Code - arXiv)
6. https://www.bunnyshell.com/guides/coding-agent-sandbox/ (Coding Agent
Sandbox: Secure Environments for AI-Generated ...)
7. https://www.bunnyshell.com/guides/sandboxed-environments-ai-coding/
(Sandboxed Environments for AI Coding: The Complete Guide | Bunnyshell)
8. https://northflank.com/blog/what-is-an-ai-sandbox (What is an AI
sandbox? | Blog - Northflank)
9.
https://www.softwareseni.com/ai-agents-in-production-the-sandboxing-problem-no-one-has-solved/
(AI Agents in Production: The Sandboxing Problem No One Has Solved -
SoftwareSeni)


On Wed, May 6, 2026 at 3:57 PM <cauldronpumpkin@gmail.com> wrote:

> Research task: How to safely execute AI-generated code. Patterns used by
> Cursor, Windsurf, Devin, and others.
>
> Please cover:
> - Container isolation (Docker, Firecracker, gVisor) — startup time vs
> security tradeoffs
> - Filesystem restrictions: read-only mounts, temp directories, overlayfs
> - Network egress controls: no-internet vs allowlisted domains vs full
> access
> - Resource limits: CPU/memory caps, timeout enforcement, process limits
> - Language-specific sandboxes (PyPy sandbox, Deno permissions, seccomp)
> - What production AI coding tools actually do: Cursor, Windsurf, Devin,
> GitHub Copilot Workspace
> - Escape detection: syscall monitoring, anomaly detection
> - Open source sandboxing tools: E2B, Daytona, CodeSandbox SDK
> - The Karkhana use case: local worker (Tauri), AI engine runs arbitrary
> code, needs safe execution
>
> Reply to this thread with your Gemini Deep Research results (paste as text
> or attach .md/.txt).
