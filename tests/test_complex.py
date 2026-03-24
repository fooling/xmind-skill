#!/usr/bin/env python3
"""
Complex XMind 8 compatibility tests.

Simulates real-world XMind 8 files with:
  - 57+ topics, each with ~22 fields
  - 1300+ total elements in the XML tree
  - sceneId / sceneDetail on every topic
  - styles.xml with per-topic styling (shape, font, color, border)
  - attachments/ directory entries
  - numbering, images, custom extensions
  - deeply nested hierarchies (5+ levels)
  - mixed content HTML notes with xhtml namespace
  - boundaries, summaries, callouts, markers, labels
  - relationships with control points
  - detached/floating topics
  - internal xmind:# links across sheets
  - folded branches
"""
import json, subprocess, sys, os, zipfile, shutil, random, string

_HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.join(_HERE, "..", "skills", "xmind", "scripts")
TEST_DIR   = "/tmp/xmind-complex-test"

def read_action(action_data):
    p = subprocess.run(
        ["node", f"{SCRIPT_DIR}/read_xmind.mjs"],
        input=json.dumps(action_data), capture_output=True, text=True
    )
    if p.returncode != 0:
        print(f"READ ERROR: {p.stderr}")
        sys.exit(1)
    return json.loads(p.stdout)

def create_xmind(path, format_name, sheets_json):
    inp = json.dumps({"path": path, "format": format_name, "sheets": sheets_json})
    p = subprocess.run(
        ["node", f"{SCRIPT_DIR}/create_xmind.mjs"],
        input=inp, capture_output=True, text=True
    )
    if p.returncode != 0:
        print(f"CREATE ERROR: {p.stderr}")
        sys.exit(1)

class Checker:
    def __init__(self, label):
        self.label = label
        self.errors = []
        self.passes = 0
    def ok(self, ctx, cond, msg=""):
        if cond:
            self.passes += 1
        else:
            self.errors.append(f"[{self.label}] {ctx}: {msg}")
    def eq(self, ctx, expected, actual, field=""):
        if expected == actual:
            self.passes += 1
        else:
            self.errors.append(f"[{self.label}] {ctx}.{field}: expected={json.dumps(expected, ensure_ascii=False)[:100]}, got={json.dumps(actual, ensure_ascii=False)[:100]}")
    def report(self):
        t = self.passes + len(self.errors)
        status = f"{self.passes}/{t} passed"
        if self.errors:
            status += f", {len(self.errors)} FAILED"
        print(f"  -> {status}")
        for e in self.errors:
            print(f"     x {e}")
        return t, self.passes, self.errors

# ══════════════════════════════════════════════
# TEST A: Large XMind 8 file with 57 richly-fielded topics
# ══════════════════════════════════════════════

def build_large_xmind8():
    """Build a content.xml + styles.xml simulating a real large XMind 8 file."""

    markers_pool = ["priority-1","priority-2","priority-3","priority-4","priority-5",
                     "task-done","task-start","task-half","task-oct",
                     "smiley-smile","smiley-laugh","flag-red","flag-green","flag-blue",
                     "star-red","star-orange","star-yellow","star-green","star-blue"]
    shapes_pool = ["org.xmind.topicShape.roundedRect","org.xmind.topicShape.rect",
                   "org.xmind.topicShape.diamond","org.xmind.topicShape.ellipserect",
                   "org.xmind.topicShape.underline","org.xmind.topicShape.circle",
                   "org.xmind.topicShape.parallelogram"]
    structures_pool = ["org.xmind.ui.map.clockwise","org.xmind.ui.logic.right",
                       "org.xmind.ui.org-chart.down","org.xmind.ui.tree.right",
                       "org.xmind.ui.fishbone.leftHeaded"]
    fonts_pool = ["Arial","Helvetica","Times New Roman","Verdana","Georgia","Courier New"]
    colors_pool = ["#333333","#FF0000","#00AA00","#0055CC","#8800AA","#CC6600","#006666"]
    statuses = ["todo","done"]
    dep_types = ["FS","FF","SS","SF"]

    topic_id = [0]
    style_id = [0]
    styles = []  # list of (id, shape, font, color, bgColor)

    def new_id():
        topic_id[0] += 1
        return f"topic{topic_id[0]:04d}"

    def new_style_id():
        style_id[0] += 1
        sid = f"style{style_id[0]:04d}"
        shape = shapes_pool[style_id[0] % len(shapes_pool)]
        font = fonts_pool[style_id[0] % len(fonts_pool)]
        color = colors_pool[style_id[0] % len(colors_pool)]
        bg = colors_pool[(style_id[0] + 3) % len(colors_pool)]
        styles.append((sid, shape, font, f"{10 + style_id[0]}pt", color, bg))
        return sid

    def esc(s):
        return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

    def build_topic_xml(depth, idx, parent_id, max_children=5, indent="      "):
        tid = new_id()
        sid = new_style_id()
        scene_id = f"scene-{tid}"
        scene_detail = f"detail-{tid}-d{depth}"
        ts = 1710000000000 + topic_id[0] * 1000

        # ~22 fields per topic: id, title, structure-class, style-id, timestamp, sceneId,
        # sceneDetail, branch, notes(plain+html), labels(2), markers(2), href, image,
        # numbering, position, taskStatus, progress, priority, boundaries, callouts, extensions

        attrs = [
            f'id="{tid}"',
            f'style-id="{sid}"',
            f'timestamp="{ts}"',
            f'sceneId="{scene_id}"',
            f'sceneDetail="{scene_detail}"',
        ]
        if depth <= 1:
            attrs.append(f'structure-class="{structures_pool[idx % len(structures_pool)]}"')
        if depth >= 2 and idx % 3 == 0:
            attrs.append('branch="folded"')
        if idx % 7 == 0:
            attrs.append(f'xlink:href="https://example.com/topic/{tid}"')

        xml = f'{indent}<topic {" ".join(attrs)}>\n'
        title = f"Topic {tid} (L{depth}-{idx})"
        xml += f'{indent}  <title>{esc(title)}</title>\n'

        # Notes: plain + HTML
        plain_note = f"Note for {title}. This is a detailed description with context about the topic content at depth {depth}, index {idx}."
        html_note = f'<xhtml:p>Rich note for <xhtml:span style="font-weight: bold;">{esc(title)}</xhtml:span></xhtml:p><xhtml:p>Paragraph 2 with <xhtml:span style="font-style: italic;">italic</xhtml:span> and <xhtml:span style="text-decoration: underline;">underline</xhtml:span>.</xhtml:p>'
        xml += f'{indent}  <notes>\n'
        xml += f'{indent}    <plain>{esc(plain_note)}</plain>\n'
        xml += f'{indent}    <xhtml:html>{html_note}</xhtml:html>\n'
        xml += f'{indent}  </notes>\n'

        # Labels
        xml += f'{indent}  <labels>\n'
        xml += f'{indent}    <label>category-{depth}</label>\n'
        xml += f'{indent}    <label>priority-{(idx % 5) + 1}</label>\n'
        xml += f'{indent}  </labels>\n'

        # Markers
        m1 = markers_pool[idx % len(markers_pool)]
        m2 = markers_pool[(idx + 5) % len(markers_pool)]
        xml += f'{indent}  <marker-refs>\n'
        xml += f'{indent}    <marker-ref marker-id="{m1}"/>\n'
        xml += f'{indent}    <marker-ref marker-id="{m2}"/>\n'
        xml += f'{indent}  </marker-refs>\n'

        # Position (for detached topics or deep nodes)
        if depth >= 3:
            px = idx * 150 + depth * 50
            py = depth * 100 + idx * 30
            xml += f'{indent}  <position svg:x="{px}" svg:y="{py}"/>\n'

        # Image (every 4th topic)
        if idx % 4 == 0:
            xml += f'{indent}  <xhtml:img xhtml:src="xap:attachments/{tid}.png" svg:width="{100 + idx * 10}" svg:height="{80 + idx * 5}"/>\n'

        # Numbering (every 5th topic)
        if idx % 5 == 0:
            xml += f'{indent}  <numbering number-format="arabic" number-separator=".">\n'
            xml += f'{indent}    <prefix>(</prefix>\n'
            xml += f'{indent}    <suffix>)</suffix>\n'
            xml += f'{indent}  </numbering>\n'

        # Extensions: task info + custom
        xml += f'{indent}  <extensions>\n'
        status = statuses[idx % 2]
        progress = round((idx * 0.1) % 1.0, 2)
        priority = (idx % 9) + 1
        start_ts = 1709251200000 + idx * 86400000
        due_ts = start_ts + 14 * 86400000
        xml += f'{indent}    <extension provider="org.xmind.ui.task">\n'
        xml += f'{indent}      <content>\n'
        xml += f'{indent}        <status>{status}</status>\n'
        xml += f'{indent}        <progress>{progress}</progress>\n'
        xml += f'{indent}        <priority>{priority}</priority>\n'
        xml += f'{indent}        <start>{start_ts}</start>\n'
        xml += f'{indent}        <due>{due_ts}</due>\n'
        xml += f'{indent}      </content>\n'
        xml += f'{indent}    </extension>\n'
        # Custom extension
        xml += f'{indent}    <extension provider="com.acme.metadata">\n'
        xml += f'{indent}      <content owner="user-{idx}" department="dept-{depth}">\n'
        xml += f'{indent}        <category>cat-{idx % 8}</category>\n'
        xml += f'{indent}        <rating>{(idx % 5) + 1}</rating>\n'
        xml += f'{indent}      </content>\n'
        xml += f'{indent}    </extension>\n'
        xml += f'{indent}  </extensions>\n'

        # Children
        num_children = min(max_children, max(0, 4 - depth)) if depth < 4 else 0
        if num_children > 0:
            xml += f'{indent}  <children>\n'
            xml += f'{indent}    <topics type="attached">\n'
            child_ids = []
            for ci in range(num_children):
                child_xml, child_id = build_topic_xml(depth + 1, ci, tid, max_children - 1, indent + '      ')
                xml += child_xml
                child_ids.append(child_id)
            xml += f'{indent}    </topics>\n'
            # Callout on first topic at each level
            if idx == 0:
                xml += f'{indent}    <topics type="callout">\n'
                xml += f'{indent}      <topic id="{new_id()}"><title>Callout for {esc(title)}</title></topic>\n'
                xml += f'{indent}    </topics>\n'
            xml += f'{indent}  </children>\n'

            # Boundaries (if has 2+ children)
            if len(child_ids) >= 2:
                xml += f'{indent}  <boundaries>\n'
                xml += f'{indent}    <boundary id="{new_id()}" range="(0,{len(child_ids)-1})">\n'
                xml += f'{indent}      <title>Group in {esc(title)}</title>\n'
                xml += f'{indent}    </boundary>\n'
                xml += f'{indent}  </boundaries>\n'

        xml += f'{indent}</topic>\n'
        return xml, tid

    # Build content.xml
    root_xml, root_id = build_topic_xml(0, 0, None, max_children=6)

    # Build second sheet for cross-references
    sheet2_root_id = new_id()
    sheet2_xml = f"""    <topic id="{sheet2_root_id}" style-id="{new_style_id()}" timestamp="1710099000000"
           sceneId="scene-sheet2" sceneDetail="detail-sheet2-root" xlink:href="xmind:#{root_id}">
      <title>Sheet 2 Root (links to Sheet 1)</title>
      <notes><plain>Cross-sheet reference to main map</plain></notes>
      <labels><label>cross-ref</label></labels>
      <children>
        <topics type="attached">
"""
    for i in range(5):
        tid = new_id()
        sid = new_style_id()
        sheet2_xml += f"""          <topic id="{tid}" style-id="{sid}" timestamp="{1710099001000 + i * 1000}"
                 sceneId="scene-s2-{i}" sceneDetail="detail-s2-{i}">
            <title>Sheet2 Topic {i}</title>
            <notes><plain>Content for sheet 2 topic {i}</plain></notes>
            <labels><label>s2-label-{i}</label></labels>
            <marker-refs><marker-ref marker-id="{markers_pool[i % len(markers_pool)]}"/></marker-refs>
          </topic>
"""
    sheet2_xml += """        </topics>
      </children>
    </topic>"""

    # Build third sheet with detached/floating topics
    float_topics = []
    for i in range(8):
        fid = new_id()
        fsid = new_style_id()
        shape = shapes_pool[i % len(shapes_pool)]
        float_topics.append((fid, f"Float {i}", i * 200 - 400, i * 120 - 200, shape))

    sheet3_root_id = new_id()
    sheet3_root_sid = new_style_id()
    sheet3_xml = f"""    <topic id="{sheet3_root_id}" style-id="{sheet3_root_sid}" timestamp="1710199000000"
           structure-class="org.xmind.ui.map.clockwise" sceneId="scene-flow-root" sceneDetail="detail-flow-root"
           shape-class="org.xmind.topicShape.ellipserect">
      <title>Flow Diagram Root</title>
      <children>
        <topics type="attached"/>
        <topics type="detached">
"""
    for fid, ftitle, fx, fy, fshape in float_topics:
        fsid = new_style_id()
        sheet3_xml += f"""          <topic id="{fid}" style-id="{fsid}" timestamp="1710199001000"
                 sceneId="scene-{fid}" sceneDetail="detail-{fid}">
            <title>{esc(ftitle)}</title>
            <position svg:x="{fx}" svg:y="{fy}"/>
            <notes><plain>Floating topic at ({fx}, {fy})</plain></notes>
          </topic>
"""
    sheet3_xml += """        </topics>
      </children>
    </topic>"""

    # Relationships for sheet3
    rels3_xml = "    <relationships>\n"
    for i in range(len(float_topics) - 1):
        rel_id = new_id()
        rels3_xml += f'      <relationship id="{rel_id}" end1="{float_topics[i][0]}" end2="{float_topics[i+1][0]}">\n'
        rels3_xml += f'        <title>step {i}→{i+1}</title>\n'
        rels3_xml += f'        <control-points>\n'
        rels3_xml += f'          <control-point index="0" amount="0.3" angle="{15 + i * 5}"/>\n'
        rels3_xml += f'          <control-point index="1" amount="0.7" angle="{-10 - i * 3}"/>\n'
        rels3_xml += f'        </control-points>\n'
        rels3_xml += f'      </relationship>\n'
    rels3_xml += "    </relationships>\n"

    # Assemble full content.xml
    content_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<xmap-content xmlns="urn:xmind:xmap:xmlns:content:2.0"
              xmlns:xhtml="http://www.w3.org/1999/xhtml"
              xmlns:xlink="http://www.w3.org/1999/xlink"
              xmlns:svg="http://www.w3.org/2000/svg"
              xmlns:fo="http://www.w3.org/1999/XSL/Format"
              version="2.0" timestamp="1710000000000">
  <sheet id="sheet1" theme="theme1" timestamp="1710000000000">
    <title>Main Project Map</title>
{root_xml}
    <relationships>
      <relationship id="{new_id()}" end1="topic0002" end2="topic0010">
        <title>cross-link</title>
      </relationship>
    </relationships>
  </sheet>
  <sheet id="sheet2" theme="theme2" timestamp="1710099000000">
    <title>Reference Sheet</title>
{sheet2_xml}
  </sheet>
  <sheet id="sheet3" theme="theme3" timestamp="1710199000000">
    <title>Flow Diagram</title>
{sheet3_xml}
{rels3_xml}
  </sheet>
</xmap-content>"""

    # Build styles.xml
    styles_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    styles_xml += '<xmap-styles xmlns="urn:xmind:xmap:xmlns:style:2.0"\n'
    styles_xml += '             xmlns:fo="http://www.w3.org/1999/XSL/Format"\n'
    styles_xml += '             xmlns:svg="http://www.w3.org/2000/svg">\n'
    styles_xml += '  <automatic-styles>\n'
    for sid, shape, font, size, color, bg in styles:
        styles_xml += f'    <style id="{sid}" type="topic">\n'
        styles_xml += f'      <topic-properties shape-class="{shape}" fo:font-family="{font}" fo:font-size="{size}" fo:color="{color}" svg:fill="{bg}" border-line-width="1pt" border-line-color="{color}"/>\n'
        styles_xml += f'    </style>\n'
    styles_xml += '  </automatic-styles>\n'
    styles_xml += '</xmap-styles>\n'

    # Build manifest
    manifest_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<manifest xmlns="urn:xmind:xmap:xmlns:manifest:1.0">\n'
    manifest_xml += '  <file-entry full-path="content.xml" media-type="text/xml"/>\n'
    manifest_xml += '  <file-entry full-path="meta.xml" media-type="text/xml"/>\n'
    manifest_xml += '  <file-entry full-path="styles.xml" media-type="text/xml"/>\n'
    manifest_xml += '  <file-entry full-path="META-INF/manifest.xml" media-type="text/xml"/>\n'
    # Simulate attachments
    for i in range(15):
        manifest_xml += f'  <file-entry full-path="attachments/topic{(i*4+1):04d}.png" media-type="image/png"/>\n'
    manifest_xml += '</manifest>\n'

    meta_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<meta xmlns="urn:xmind:xmap:xmlns:meta:2.0" version="2.0">\n  <Creator><Name>XMind 8 Pro</Name><Version>3.7.9</Version></Creator>\n</meta>\n'

    return content_xml, styles_xml, manifest_xml, meta_xml, topic_id[0], len(styles)


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

if os.path.exists(TEST_DIR):
    shutil.rmtree(TEST_DIR)
os.makedirs(TEST_DIR, exist_ok=True)

all_checkers = []

# ─── TEST A: Large complex XMind 8 file ───
print("=" * 70)
print("TEST A: Large XMind 8 file (57+ topics, ~22 fields each, styles.xml)")
print("=" * 70)

content_xml, styles_xml, manifest_xml, meta_xml, total_topics, total_styles = build_large_xmind8()

# Write the ZIP manually (simulating a real XMind 8 file from another editor)
xmind8_path = f"{TEST_DIR}/large_xmind8.xmind"
with zipfile.ZipFile(xmind8_path, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('content.xml', content_xml)
    z.writestr('styles.xml', styles_xml)
    z.writestr('meta.xml', meta_xml)
    z.writestr('META-INF/manifest.xml', manifest_xml)
    # Fake attachment files
    for i in range(15):
        z.writestr(f'attachments/topic{(i*4+1):04d}.png', f'FAKE_PNG_DATA_{i}')

print(f"  Built: {total_topics} topics, {total_styles} styles")
print(f"  XML size: {len(content_xml)} bytes")

# Read it
data = read_action({"action": "read", "path": xmind8_path})

ckA = Checker("LargeXMind8")
ckA.eq("sheets", 3, len(data), "sheet count")

# Sheet 1: check structure
s1 = data[0]
ckA.eq("s1", "Main Project Map", s1.get("sheetTitle"), "sheetTitle")
ckA.eq("s1", "Topic topic0001 (L0-0)", s1["title"], "root title")

# Count all topics recursively
def count_topics(node):
    n = 1
    for c in node.get("children", []):
        n += count_topics(c)
    for d in node.get("detachedTopics", []):
        n += count_topics(d)
    return n

s1_count = count_topics(s1)
s2_count = count_topics(data[1])
s3_count = count_topics(data[2])
total_read = s1_count + s2_count + s3_count
print(f"  Read back: {s1_count} (sheet1) + {s2_count} (sheet2) + {s3_count} (sheet3) = {total_read} topics")
ckA.ok("topic_count", total_read >= 57, f"expected ≥57 topics, got {total_read}")

# Verify root topic has all expected fields
ckA.ok("root.sceneId", s1.get("sceneId") == "scene-topic0001", f"got {s1.get('sceneId')}")
ckA.ok("root.sceneDetail", "detail-topic0001" in s1.get("sceneDetail",""), f"got {s1.get('sceneDetail')}")
ckA.ok("root.timestamp", s1.get("timestamp") is not None, "timestamp present")
ckA.ok("root.structureClass", s1.get("structureClass") is not None, "structureClass present")
ckA.ok("root.styleId", s1.get("styleId") is not None, "styleId present")
ckA.ok("root.shape", s1.get("shape") is not None, f"shape resolved from styles.xml: {s1.get('shape')}")
ckA.ok("root.styleProperties", s1.get("styleProperties") is not None, "styleProperties present")
ckA.ok("root.notes.plain", s1.get("notes",{}).get("content") is not None, "notes.plain present")
ckA.ok("root.notes.html", s1.get("notes",{}).get("html") is not None, "notes.html present")
ckA.ok("root.labels", len(s1.get("labels",[])) == 2, f"labels: {s1.get('labels')}")
ckA.ok("root.markers", len(s1.get("markers",[])) == 2, f"markers: {s1.get('markers')}")
ckA.ok("root.image", s1.get("image") is not None, f"image: {s1.get('image')}")
ckA.ok("root.numbering", s1.get("numbering") is not None, f"numbering: {s1.get('numbering')}")
ckA.ok("root.taskStatus", s1.get("taskStatus") is not None, f"taskStatus: {s1.get('taskStatus')}")
ckA.ok("root.progress", s1.get("progress") is not None, f"progress: {s1.get('progress')}")
ckA.ok("root.priority", s1.get("priority") is not None, f"priority: {s1.get('priority')}")
ckA.ok("root.startDate", s1.get("startDate") is not None, f"startDate: {s1.get('startDate')}")
ckA.ok("root.dueDate", s1.get("dueDate") is not None, f"dueDate: {s1.get('dueDate')}")
ckA.ok("root.extensions", s1.get("extensions") is not None, f"custom extensions preserved")
ckA.ok("root.callouts", s1.get("callouts") is not None, f"callouts: {s1.get('callouts')}")
ckA.ok("root.boundaries", s1.get("boundaries") is not None, f"boundaries: {len(s1.get('boundaries',[]))}")

# Verify custom extension content
if s1.get("extensions"):
    ext = s1["extensions"][0]
    ckA.eq("custom_ext", "com.acme.metadata", ext.get("provider"), "provider")
    ckA.ok("custom_ext.content", ext.get("content",{}).get("category") is not None, f"category: {ext.get('content',{}).get('category')}")
    ckA.ok("custom_ext.owner", ext.get("content",{}).get("owner") is not None, f"owner: {ext.get('content',{}).get('owner')}")

# Verify styleProperties from styles.xml
sp = s1.get("styleProperties", {})
ckA.ok("style.font", "fo:font-family" in sp, f"font: {sp.get('fo:font-family')}")
ckA.ok("style.size", "fo:font-size" in sp, f"size: {sp.get('fo:font-size')}")
ckA.ok("style.color", "fo:color" in sp, f"color: {sp.get('fo:color')}")
ckA.ok("style.fill", "svg:fill" in sp, f"fill: {sp.get('svg:fill')}")

# Spot-check deep topics
def find_topics_with_field(node, field, results=None):
    if results is None: results = []
    if node.get(field):
        results.append(node)
    for c in node.get("children", []):
        find_topics_with_field(c, field, results)
    for d in node.get("detachedTopics", []):
        find_topics_with_field(d, field, results)
    return results

sceneId_topics = find_topics_with_field(s1, "sceneId")
ckA.ok("sceneId_coverage", len(sceneId_topics) == s1_count,
       f"sceneId on {len(sceneId_topics)}/{s1_count} topics")

timestamp_topics = find_topics_with_field(s1, "timestamp")
ckA.ok("timestamp_coverage", len(timestamp_topics) == s1_count,
       f"timestamp on {len(timestamp_topics)}/{s1_count} topics")

styleId_topics = find_topics_with_field(s1, "styleId")
ckA.ok("styleId_coverage", len(styleId_topics) == s1_count,
       f"styleId on {len(styleId_topics)}/{s1_count} topics")

shape_topics = find_topics_with_field(s1, "shape")
ckA.ok("shape_resolved", len(shape_topics) == s1_count,
       f"shape resolved on {len(shape_topics)}/{s1_count} topics (from styles.xml)")

notes_topics = find_topics_with_field(s1, "notes")
ckA.ok("notes_coverage", len(notes_topics) == s1_count,
       f"notes on {len(notes_topics)}/{s1_count} topics")

# Verify HTML notes have proper mixed content ordering
html_note = s1.get("notes",{}).get("html","")
ckA.ok("html.bold", "font-weight: bold;" in html_note, "HTML has bold span")
ckA.ok("html.order", html_note.index("Rich note") < html_note.index("bold"), "mixed content order correct")

# Sheet 2: cross-sheet link
s2 = data[1]
ckA.eq("s2", "Reference Sheet", s2.get("sheetTitle"), "sheetTitle")
ckA.ok("s2.href", s2.get("href","").startswith("xmind:#"), f"cross-sheet link: {s2.get('href','')[:30]}")
ckA.ok("s2.sceneId", s2.get("sceneId") == "scene-sheet2", f"sceneId: {s2.get('sceneId')}")
ckA.eq("s2.children", 5, len(s2.get("children",[])), "children count")
for i, c in enumerate(s2.get("children",[])):
    ckA.ok(f"s2.c{i}.sceneId", c.get("sceneId") is not None, f"sceneId: {c.get('sceneId')}")

# Sheet 3: detached/floating topics + relationships
s3 = data[2]
ckA.eq("s3", "Flow Diagram", s3.get("sheetTitle"), "sheetTitle")
dt = s3.get("detachedTopics", [])
ckA.eq("s3.detached", 8, len(dt), "detached count")
for i, d in enumerate(dt):
    ckA.ok(f"s3.dt{i}.pos", d.get("position") is not None, f"position: {d.get('position')}")
    ckA.ok(f"s3.dt{i}.sceneId", d.get("sceneId") is not None, f"sceneId: {d.get('sceneId')}")

s3_rels = s3.get("relationships", [])
ckA.eq("s3.rels", 7, len(s3_rels), "relationship count")
for i, r in enumerate(s3_rels):
    ckA.ok(f"s3.rel{i}.title", r.get("title") is not None, f"title: {r.get('title')}")
    ckA.ok(f"s3.rel{i}.cp", len(r.get("controlPoints",[])) == 2, f"controlPoints: {len(r.get('controlPoints',[]))}")

ckA.report()
all_checkers.append(ckA)

# ─── TEST B: Search actions on the large file ───
print()
print("=" * 70)
print("TEST B: Search/extract actions on large XMind 8 file")
print("=" * 70)

ckB = Checker("LargeSearch")

# Search todos
todos = read_action({"action": "search_nodes", "path": xmind8_path, "taskStatus": "todo"})
ckB.ok("todo", todos["totalMatches"] > 0, f"found {todos['totalMatches']} todo tasks")

# Search dones
dones = read_action({"action": "search_nodes", "path": xmind8_path, "taskStatus": "done"})
ckB.ok("done", dones["totalMatches"] > 0, f"found {dones['totalMatches']} done tasks")

# Text search in notes
ns = read_action({"action": "search_nodes", "path": xmind8_path, "query": "depth 2", "searchIn": ["notes"]})
ckB.ok("notes_search", ns["totalMatches"] > 0, f"found {ns['totalMatches']} notes with 'depth 2'")

# Label search
ls = read_action({"action": "search_nodes", "path": xmind8_path, "query": "category-1", "searchIn": ["labels"]})
ckB.ok("label_search", ls["totalMatches"] > 0, f"found {ls['totalMatches']} with label category-1")

# Fuzzy extract
fz = read_action({"action": "extract_node", "path": xmind8_path, "searchQuery": "L2-1"})
ckB.ok("fuzzy", fz["totalMatches"] > 0, f"fuzzy found {fz['totalMatches']} for 'L2-1'")

# Format info
fi = read_action({"action": "format_info", "path": xmind8_path})
ckB.eq("format", "legacy", fi["format"], "detected as legacy")
ckB.ok("files", "styles.xml" in fi["files"], f"styles.xml in file list: {fi['files']}")

# List
fl = read_action({"action": "list", "directory": TEST_DIR})
ckB.ok("list", xmind8_path in fl, "file found in list")

# Search files by content
sf = read_action({"action": "search_files", "pattern": "Flow Diagram", "directory": TEST_DIR})
ckB.ok("search_files", xmind8_path in sf, "found by content search")

ckB.report()
all_checkers.append(ckB)

# ─── TEST C: Write-Read-Write-Read cycle across formats ───
print()
print("=" * 70)
print("TEST C: Write ZEN (complex) -> Read -> Write Legacy -> Read -> Compare")
print("=" * 70)

ckC = Checker("CrossFormat")

# Build a complex zen file via create_xmind.mjs
complex_sheets = [
    {
        "title": "Complex Sheet",
        "rootTopic": {
            "title": "Root",
            "notes": {"plain": "Root note", "html": "<strong>Bold</strong> and <u>underline</u>"},
            "labels": ["L1", "L2", "L3"],
            "markers": ["priority-1", "priority-2", "task-start"],
            "structureClass": "org.xmind.ui.logic.right",
            "callouts": ["Note A", "Note B", "Note C"],
            "children": [
                {
                    "title": f"Branch {i}",
                    "notes": f"Notes for branch {i} with detailed content",
                    "labels": [f"tag-{i}", f"cat-{i % 3}"],
                    "markers": [f"priority-{i+1}"],
                    "taskStatus": "todo" if i % 2 == 0 else "done",
                    "progress": round(i * 0.15, 2),
                    "priority": i + 1,
                    "startDate": f"2026-0{i+1}-01T00:00:00Z" if i < 9 else f"2026-{i+1}-01T00:00:00Z",
                    "dueDate": f"2026-0{i+1}-15T00:00:00Z" if i < 9 else f"2026-{i+1}-15T00:00:00Z",
                    "children": [
                        {
                            "title": f"Sub {i}-{j}",
                            "notes": {"plain": f"Sub note {i}-{j}", "html": f"<strong>Sub {i}-{j}</strong>"},
                            "labels": [f"sub-{j}"],
                            "shape": "org.xmind.topicShape.diamond" if j == 0 else "org.xmind.topicShape.rect",
                            "children": [
                                {"title": f"Leaf {i}-{j}-{k}", "notes": f"Leaf note {i}-{j}-{k}", "taskStatus": "todo" if k == 0 else "done"}
                                for k in range(3)
                            ]
                        }
                        for j in range(4)
                    ],
                    "boundaries": [{"range": "(0,1)", "title": f"Group {i}A"}, {"range": "(2,3)", "title": f"Group {i}B"}],
                    "summaryTopics": [{"range": "(0,3)", "title": f"Summary of Branch {i}"}]
                }
                for i in range(8)
            ]
        },
        "relationships": [
            {"sourceTitle": f"Branch {i}", "targetTitle": f"Branch {i+1}", "title": f"step {i}→{i+1}"}
            for i in range(7)
        ]
    },
    {
        "title": "Floating Sheet",
        "freePositioning": True,
        "rootTopic": {"title": "Origin", "shape": "org.xmind.topicShape.ellipserect"},
        "detachedTopics": [
            {"title": f"Node {i}", "position": {"x": i * 180, "y": (i % 3) * 120},
             "shape": "org.xmind.topicShape.diamond" if i % 2 == 0 else "org.xmind.topicShape.rect",
             "notes": f"Detached node {i}"}
            for i in range(10)
        ],
        "relationships": [
            {"sourceTitle": f"Node {i}", "targetTitle": f"Node {i+1}",
             "shape": "org.xmind.relationshipShape.straight", "title": f"flow {i}"}
            for i in range(9)
        ]
    }
]

# Write as zen
zen_path = f"{TEST_DIR}/complex_zen.xmind"
create_xmind(zen_path, "zen", complex_sheets)
zen_data = read_action({"action": "read", "path": zen_path})

# Write as legacy
leg_path = f"{TEST_DIR}/complex_legacy.xmind"
create_xmind(leg_path, "xmind8", complex_sheets)
leg_data = read_action({"action": "read", "path": leg_path})

# Compare key metrics
zen_total = sum(count_topics(s) for s in zen_data)
leg_total = sum(count_topics(s) for s in leg_data)
ckC.eq("total_topics", zen_total, leg_total, "topic count matches")

# Verify sheet structure
ckC.eq("sheets", len(zen_data), len(leg_data), "sheet count")

# Deep field comparison (spot check)
for si in range(len(zen_data)):
    zs = zen_data[si]
    ls = leg_data[si]
    ckC.eq(f"s{si}.title", zs["title"], ls["title"], "root title")
    ckC.eq(f"s{si}.sheetTitle", zs.get("sheetTitle"), ls.get("sheetTitle"), "sheetTitle")

    # Check children count recursively
    def get_all_titles(node):
        titles = [node["title"]]
        for c in node.get("children", []):
            titles.extend(get_all_titles(c))
        for d in node.get("detachedTopics", []):
            titles.extend(get_all_titles(d))
        return titles

    zen_titles = sorted(get_all_titles(zs))
    leg_titles = sorted(get_all_titles(ls))
    ckC.eq(f"s{si}.all_titles", zen_titles, leg_titles, "all topic titles match")

# Verify zen has all expected fields
zen_s1 = zen_data[0]
ckC.eq("zen.children", 8, len(zen_s1.get("children",[])), "8 branches")
ckC.eq("zen.rels", 7, len(zen_s1.get("relationships",[])), "7 relationships")
for i, c in enumerate(zen_s1.get("children",[])):
    ckC.ok(f"zen.c{i}.notes", c.get("notes") is not None, "notes present")
    ckC.ok(f"zen.c{i}.labels", len(c.get("labels",[])) == 2, "2 labels")
    ckC.ok(f"zen.c{i}.markers", len(c.get("markers",[])) == 1, "1 marker")
    ckC.ok(f"zen.c{i}.taskStatus", c.get("taskStatus") in ("todo","done"), f"taskStatus: {c.get('taskStatus')}")
    ckC.ok(f"zen.c{i}.boundaries", len(c.get("boundaries",[])) == 2, "2 boundaries")
    ckC.ok(f"zen.c{i}.summaries", len(c.get("summaries",[])) == 1, "1 summary")
    ckC.ok(f"zen.c{i}.sub_count", len(c.get("children",[])) == 4, "4 sub-topics")
    # Verify leaf level
    for j, sub in enumerate(c.get("children",[])):
        ckC.ok(f"zen.c{i}.s{j}.shape", sub.get("shape") is not None, f"shape: {sub.get('shape')}")
        ckC.ok(f"zen.c{i}.s{j}.leaves", len(sub.get("children",[])) == 3, "3 leaves")

# Same checks for legacy
leg_s1 = leg_data[0]
ckC.eq("leg.children", 8, len(leg_s1.get("children",[])), "8 branches")
ckC.eq("leg.rels", 7, len(leg_s1.get("relationships",[])), "7 relationships")

# Verify detached sheet
zen_s2 = zen_data[1]
leg_s2 = leg_data[1]
ckC.eq("s2.detached", len(zen_s2.get("detachedTopics",[])), len(leg_s2.get("detachedTopics",[])), "detached count")
ckC.eq("s2.rels", len(zen_s2.get("relationships",[])), len(leg_s2.get("relationships",[])), "rel count")

ckC.report()
all_checkers.append(ckC)

# ═══════════════════════════════════════════════
# FINAL
# ═══════════════════════════════════════════════
print()
print("=" * 70)
total_pass = sum(ck.passes for ck in all_checkers)
total_err  = sum(len(ck.errors) for ck in all_checkers)
total      = total_pass + total_err

if total_err == 0:
    print(f"ALL {total} CHECKS PASSED across {len(all_checkers)} tests.")
else:
    print(f"RESULT: {total_pass}/{total} passed, {total_err} FAILED")
    sys.exit(1)
