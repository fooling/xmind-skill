# CLAUDE.md

## Build & Test
- `npm run build:skill` — package skill into `build/xmind-skill.zip`
- `npm run test:create` — quick smoke test for create script
- `npm run test:read` — quick smoke test for read script

## Architecture
- Skill definition: `skills/xmind/SKILL.md`
- Create script: `skills/xmind/scripts/create_xmind.mjs` — zero npm deps (ZIP via `zlib.deflateRawSync`)
- Read script: `skills/xmind/scripts/read_xmind.mjs` — zero npm deps (ZIP via `zlib.inflateRawSync`)
- Build script: `scripts/build-skill.sh`

## XMind Format
- Fichier .xmind = ZIP contenant `content.json`, `metadata.json`, `manifest.json`
- Topics requièrent `class: "topic"`, sheets requièrent `class: "sheet"` + `theme: {}`
- Planned tasks nécessitent `extensions` avec `org.xmind.ui.working-day-settings` au niveau sheet
- `topicOverlapping: "overlap"` requis au niveau sheet
- Notes HTML : `realHTML.content` (balises supportées: `<strong>`, `<u>`, `<ul>`, `<ol>`, `<li>`, `<br>`) — `<code>` non supporté par XMind
- Liens internes entre topics/sheets : `href: "xmind:#<topicId>"`
- Legacy format (XMind 8): XML-based (`content.xml`, `meta.xml`, `META-INF/manifest.xml`)

## Patterns
- IDs générés via `crypto.randomUUID()` tronqué à 26 chars sans tirets
- Résolution par titre (relationships, dependencies, linkToTopic) : stocker title→id dans un Map, résoudre après construction
- Tests : `echo JSON | node skills/xmind/scripts/create_xmind.mjs` pour tester la création
- Both scripts read JSON from stdin and are fully standalone (no npm install needed)

## Skill
- `skills/xmind/` : skill standalone pour Claude Desktop et Claude Code
- Scripts : `create_xmind.mjs` (création) + `read_xmind.mjs` (lecture/analyse)
- Build : `npm run build:skill` → `build/xmind-skill.zip`
- Claude Code : `ln -s /path/to/mcp-xmind/skills/xmind ~/.claude/skills/xmind`
