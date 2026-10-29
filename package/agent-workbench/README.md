# Harness

Double-click **Harness** on the Windows desktop. Pick your project, choose an
agent, describe a task and press **Start task**. Use **Open session** for chat,
permissions and follow-up work. The local model stays off.

- **Codex / Claude:** use your existing signed-in accounts.
- **Models:** browse downloaded local models, search Hugging Face and download
  GGUF files into ~/models. Downloading never starts the GPU.
- **Cloud model:** connect OpenRouter or OpenCode Console in Connections.
- **Local model:** turn it on explicitly, then turn it off when finished.
- **Stop Local Model:** desktop shortcut to free GPU memory immediately.

The local control panel uses Python's standard library and plain HTML/CSS/JS.
No extra application framework, SDK or desktop runtime is installed.

Read docs/START-HERE.md for daily use, STATUS.md for actual verification, and
 docs/ARCHITECTURE.md for the reviewed design and upstream references.

The pinned installer remains scripts/setup.sh. The panel can also be launched
with workbench ui. Opening the panel or running diagnostics never starts GPU inference.
