# XMind Skill

A Claude Code / Claude Desktop skill for creating and reading XMind mind maps. Zero npm dependencies — uses only Node.js built-ins.

## Features

- **Create** XMind files: nested topics, notes (plain + HTML), labels, markers, callouts, boundaries, summaries, relationships, internal links, layout structures, simple tasks (todo/done), planned tasks with Gantt support (dates, duration, progress, priority, dependencies), file attachments, free-positioning flow/logic diagrams
- **Read** XMind files: parse full structure, fuzzy search, task tracking, multi-file analysis, directory scanning, node extraction
- **Format support**: modern (XMind Zen/2020+) and legacy (XMind 8) for both read and write
- **Bilingual**: natural Chinese and English interaction routing

## Install

### Claude Code (CLI)

Symlink or copy the skill into your project or global skills directory:

```bash
# Per project
ln -s /path/to/mcp-xmind/skills/xmind .claude/skills/xmind

# All projects
ln -s /path/to/mcp-xmind/skills/xmind ~/.claude/skills/xmind
```

### Claude Desktop

Build the skill ZIP and upload it:

```bash
npm run build:skill
# → build/xmind-skill.zip
```

Open Claude Desktop > Settings > Capabilities > Skills > Upload `build/xmind-skill.zip`.

## Usage

Once installed, just ask Claude in natural language:

- "帮我做个思维导图" / "create a mind map"
- "打开这个xmind文件" / "read this xmind"
- "做个项目计划" / "make a Gantt chart"
- "画个流程图" / "draw a flowchart"

See [`skills/xmind/SKILL.md`](skills/xmind/SKILL.md) for the full JSON input format and all supported features.

## Quick test

```bash
# Create
echo '{"path":"/tmp/test.xmind","sheets":[{"title":"Test","rootTopic":{"title":"Hello"}}]}' | node skills/xmind/scripts/create_xmind.mjs

# Read
echo '{"action":"read","path":"/tmp/test.xmind"}' | node skills/xmind/scripts/read_xmind.mjs
```

## Project structure

```
skills/xmind/
  SKILL.md                    # Skill definition (routing, format docs, rules)
  scripts/
    create_xmind.mjs          # Create .xmind files (zero deps)
    read_xmind.mjs            # Read/search/analyze .xmind files (zero deps)
scripts/
  build-skill.sh              # Package skill into build/xmind-skill.zip
```

## License

MIT
