# LLM Integration Guide — UE5 Docs

This guide explains how to use the 3,444-page Unreal Engine 5.7 documentation corpus with LLMs, AI code assistants, and RAG pipelines.

---

## Option 1 — MCP Server (Claude Code — Best Option)

The bundled MCP server gives Claude direct search access to the entire documentation corpus without flooding the context window.

### Setup

```bash
git clone https://github.com/chcardenasto/DocUnrealEngine.git
cd DocUnrealEngine
pip install -e ".[mcp]"
claude mcp add --transport stdio ue5-docs -- python -m mcp_server.server --docs-dir ./docs-md-py
```

### What Claude can do after setup

```
# Claude will automatically call search_docs and get_doc as needed:
"How does the Gameplay Ability System handle attribute changes?"
"Show me the C++ API for UCharacterMovementComponent"
"What are the replication modes for Actor Network Dormancy?"
```

Claude searches the index, finds the relevant pages, reads them, and answers — without you manually copying documentation.

---

## Option 2 — Unreal MCP + Docs MCP (Dual Server Setup)

> **Available from Unreal Engine 5.8**

Epic Games added a built-in MCP server to the Unreal Editor (plugin: **Unreal MCP**). When combined with this project's documentation server, Claude can:

1. **Look up documentation** (our server) — *"What parameters does SpawnActor take?"*
2. **Execute actions in the editor** (Unreal's server) — *"Spawn a PointLight at position (100, 200, 0)"*

### Setup

**Step 1 — Enable the Unreal MCP plugin in your project**

In the Unreal Editor: *Edit → Plugins → search "MCP" → Enable "Unreal MCP" → Restart*

**Step 2 — Generate the client config**

In the Output Log or console:
```
ModelContextProtocol.GenerateClientConfig ClaudeCode
```

This creates an `.mcp.json` in your project root.

**Step 3 — Add our docs server to `.mcp.json`**

```json
{
  "mcpServers": {
    "unreal-editor": {
      "url": "http://127.0.0.1:8000/mcp"
    },
    "ue5-docs": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mcp_server.server", "--docs-dir", "/path/to/DocUnrealEngine/docs-md-py"]
    }
  }
}
```

**Step 4 — Open Claude Code in your Unreal project directory**

Claude now has both:
- Documentation lookup (our server, 3,444 pages)
- Editor control (Unreal's server — spawn actors, set materials, run tests, etc.)

### Example dual-server workflow

```
You: "Add a Niagara particle system to the scene with fire-like settings"

Claude:
  1. Calls search_docs("Niagara particle system setup") → finds the relevant docs
  2. Reads get_doc("niagara-overview") → understands the API
  3. Calls Unreal editor MCP → spawns and configures the Niagara component
```

### Unreal MCP server tools (built-in UE5.8+)

| Tool | Description |
|------|-------------|
| `list_toolsets` | List available tool categories |
| `describe_toolset` | Get parameter schemas for a toolset |
| `call_tool` | Execute any editor tool |
| Custom via Python | `@toolset_registry.tool_call` decorator |
| Custom via C++ | `meta = (AICallable)` UFUNCTION metadata |

**Connection:** `http://127.0.0.1:8000/mcp` (loopback only, no auth)

---

## Option 3 — AI Code Assistants (Cursor, GitHub Copilot, Cline)

Index the `docs-md-py` folder as a workspace source:

1. Open your Unreal project in **Cursor**
2. Add `DocUnrealEngine/docs-md-py` as a secondary workspace folder
3. Use `@Codebase` or `@Folders` when asking questions
4. The AI indexes all `.md` files and uses them as precise context

Works with any editor that supports workspace-level AI indexing.

---

## Option 4 — Custom GPTs / Claude Projects / NotebookLM

For a no-code "Unreal Engine Expert":

1. Zip the `docs-md-py` folder: `zip -r ue5-docs.zip docs-md-py/`
2. Upload to your platform:
   - **Claude Projects** — upload the ZIP, create a project
   - **Custom GPTs (OpenAI)** — upload under Knowledge
   - **Google NotebookLM** — upload as a source
3. The platform extracts Markdown files and builds an automatic RAG index

**Token budget note:**
- `GUIDE_BOOK.md` ≈ 7–8 million tokens (too large for most models directly)
- Individual files average ~2,000 tokens (perfect for chunking)
- `GUIDE_INDEX.md` is lightweight — feed it first, then request specific pages

---

## Option 5 — Custom RAG Pipeline (LangChain / LlamaIndex)

```python
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# Load all 3,444 Markdown files
loader = DirectoryLoader("./docs-md-py", glob="**/*.md", show_progress=True)
docs = loader.load()

# Split by Markdown headers (preserves semantic boundaries)
splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "H1"), ("##", "H2"), ("###", "H3")]
)
chunks = [chunk for doc in docs for chunk in splitter.split_text(doc.page_content)]

# Embed and store
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
    persist_directory="./ue5-vectordb",
)

# Query
results = vectorstore.similarity_search("How does UGameplayAbility handle cooldowns?", k=5)
```

---

## Tips for Prompting

- **Use the index first**: Feed `GUIDE_INDEX.md` to a large-context model and ask it to identify which files are relevant before you load them
- **Cite sources**: Each file starts with `> Source: https://dev.epicgames.com/...` — ask the LLM to cite this URL in its answers
- **Class names beat descriptions**: Search `"UAbilitySystemComponent"` rather than `"ability component class"`
- **Version pinning**: All files include `> Application Version: 5.7` — useful when asking models to differentiate between UE versions
