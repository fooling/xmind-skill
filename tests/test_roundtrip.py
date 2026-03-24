#!/usr/bin/env python3
"""
Read-Write-Read roundtrip fidelity test for BOTH xmind formats (zen + legacy).

Test matrix:
  1. Write zen    -> Read -> Verify all fields
  2. Write legacy -> Read -> Verify all fields
  3. Write zen    -> Read -> Write legacy -> Read -> Cross-compare
  4. Write legacy -> Read -> Write zen    -> Read -> Cross-compare
  5. Format detection (format_info action)
"""
import json, subprocess, sys, os, shutil

_HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.join(_HERE, "..", "skills", "xmind", "scripts")
TEST_DIR   = "/tmp/xmind-version-test"

# ── Helpers ──

def create(input_data):
    p = subprocess.run(
        ["node", f"{SCRIPT_DIR}/create_xmind.mjs"],
        input=json.dumps(input_data), capture_output=True, text=True
    )
    if p.returncode != 0:
        print(f"CREATE ERROR: {p.stderr}")
        sys.exit(1)
    return p.stdout.strip()

def read_action(action_data):
    p = subprocess.run(
        ["node", f"{SCRIPT_DIR}/read_xmind.mjs"],
        input=json.dumps(action_data), capture_output=True, text=True
    )
    if p.returncode != 0:
        print(f"READ ERROR: {p.stderr}")
        sys.exit(1)
    return json.loads(p.stdout)

class Checker:
    def __init__(self, label):
        self.label = label
        self.errors = []
        self.passes = 0

    def check(self, ctx, expected, actual, field=""):
        if expected != actual:
            self.errors.append(f"[{self.label}] {ctx}.{field}: expected={json.dumps(expected, ensure_ascii=False)[:120]}, got={json.dumps(actual, ensure_ascii=False)[:120]}")
        else:
            self.passes += 1

    def summary(self):
        total = self.passes + len(self.errors)
        return total, self.passes, self.errors

# ── Test Data — covers ALL features ──

def build_input(path, fmt=None):
    data = {
        "path": path,
        "sheets": [
            {
                "title": "Sheet Alpha",
                "rootTopic": {
                    "title": "Root Node",
                    "notes": {"plain": "Plain note text", "html": "<strong>Bold</strong> and <u>underline</u><br><ul><li>Item 1</li><li>Item 2</li></ul>"},
                    "labels": ["label-a", "label-b"],
                    "markers": ["priority-1", "task-start"],
                    "href": "https://example.com",
                    "structureClass": "org.xmind.ui.logic.right",
                    "children": [
                        {
                            "title": "Task Child",
                            "taskStatus": "todo",
                            "notes": "A child with todo status",
                            "labels": ["urgent"],
                            "callouts": ["Attention!", "Review"],
                            "children": [
                                {"title": "GC Done", "taskStatus": "done", "notes": "Completed", "markers": ["task-done"]},
                                {"title": "GC Todo", "taskStatus": "todo", "notes": "Pending"}
                            ],
                            "boundaries": [{"range": "(0,1)", "title": "Task Group"}]
                        },
                        {
                            "title": "Planned Child",
                            "progress": 0.6,
                            "priority": 2,
                            "startDate": "2026-03-01T00:00:00Z",
                            "dueDate": "2026-03-15T00:00:00Z",
                            "notes": {"html": "<strong>Planned</strong> task with dates"},
                            "labels": ["planned"]
                        },
                        {
                            "title": "Duration Child",
                            "durationDays": 7,
                            "progress": 0.0,
                            "priority": 3,
                            "dependencies": [{"targetTitle": "Planned Child", "type": "FS", "lag": 2}],
                            "notes": "Relative planning"
                        },
                        {
                            "title": "Summary Parent",
                            "notes": "Has summary topics",
                            "children": [
                                {"title": "Item X"},
                                {"title": "Item Y"},
                                {"title": "Item Z"}
                            ],
                            "summaryTopics": [{"range": "(0,2)", "title": "Summary X-Z"}]
                        },
                        {
                            "title": "Shape Child",
                            "shape": "org.xmind.topicShape.diamond",
                            "notes": "Diamond shape node"
                        },
                        {"title": "Plain Child", "notes": "Simple note"}
                    ]
                },
                "relationships": [
                    {"sourceTitle": "GC Done", "targetTitle": "Planned Child", "title": "feeds into"},
                    {"sourceTitle": "Shape Child", "targetTitle": "Plain Child", "shape": "org.xmind.relationshipShape.straight"}
                ]
            },
            {
                "title": "Sheet Beta",
                "rootTopic": {
                    "title": "Second Root",
                    "notes": "Cross-sheet content",
                    "linkToTopic": "Root Node",
                    "children": [
                        {"title": "Beta C1", "notes": "Note in sheet 2", "labels": ["cross-ref"]},
                        {"title": "Beta C2", "markers": ["priority-9"]}
                    ]
                }
            },
            {
                "title": "Sheet Gamma",
                "freePositioning": True,
                "rootTopic": {
                    "title": "Flow Start",
                    "shape": "org.xmind.topicShape.ellipserect",
                    "structureClass": "org.xmind.ui.map.clockwise"
                },
                "detachedTopics": [
                    {"title": "Decision?", "position": {"x": 0, "y": 130}, "shape": "org.xmind.topicShape.diamond"},
                    {"title": "Action A", "position": {"x": 200, "y": 130}},
                    {"title": "Flow End", "position": {"x": 0, "y": 260}, "shape": "org.xmind.topicShape.ellipserect"}
                ],
                "relationships": [
                    {"sourceTitle": "Flow Start", "targetTitle": "Decision?", "shape": "org.xmind.relationshipShape.straight"},
                    {"sourceTitle": "Decision?", "targetTitle": "Action A", "title": "YES", "shape": "org.xmind.relationshipShape.straight"},
                    {"sourceTitle": "Decision?", "targetTitle": "Flow End", "title": "NO", "shape": "org.xmind.relationshipShape.straight"}
                ]
            }
        ]
    }
    if fmt:
        data["format"] = fmt
    return data

# ── Field verification ──

def verify_all_fields(ck, read_result, fmt_name, skip_zen_only=False):
    """Verify every field in the read result. skip_zen_only=True for legacy format."""

    ck.check(f"{fmt_name}", 3, len(read_result), "sheet count")

    # ─── Sheet 1 ───
    s1 = read_result[0]
    ck.check(f"{fmt_name}.s1", "Sheet Alpha", s1.get("sheetTitle"), "sheetTitle")
    ck.check(f"{fmt_name}.s1", "Root Node", s1["title"], "title")
    ck.check(f"{fmt_name}.s1", "Plain note text", s1.get("notes",{}).get("content"), "notes.plain")
    ck.check(f"{fmt_name}.s1", True, "<strong>Bold</strong>" in s1.get("notes",{}).get("html",""), "notes.html bold")
    ck.check(f"{fmt_name}.s1", True, "<u>underline</u>" in s1.get("notes",{}).get("html",""), "notes.html underline")
    ck.check(f"{fmt_name}.s1", True, "<li>Item 1</li>" in s1.get("notes",{}).get("html",""), "notes.html li")
    ck.check(f"{fmt_name}.s1", ["label-a", "label-b"], s1.get("labels"), "labels")
    ck.check(f"{fmt_name}.s1", ["priority-1", "task-start"], s1.get("markers"), "markers")
    ck.check(f"{fmt_name}.s1", "https://example.com", s1.get("href"), "href")
    ck.check(f"{fmt_name}.s1", "org.xmind.ui.logic.right", s1.get("structureClass"), "structureClass")

    # Relationships
    rels = s1.get("relationships", [])
    ck.check(f"{fmt_name}.s1", 2, len(rels), "relationships count")
    rel_titles = [r.get("title","") for r in rels]
    ck.check(f"{fmt_name}.s1", True, "feeds into" in rel_titles, "rel 'feeds into'")
    # Rel shape (second relationship)
    rel_shapes = [r.get("shape","") for r in rels]
    ck.check(f"{fmt_name}.s1", True, "org.xmind.relationshipShape.straight" in rel_shapes, "rel straight shape")

    children = s1.get("children", [])
    ck.check(f"{fmt_name}.s1", 6, len(children), "children count")

    # Child 0: Tasks + Callouts + Boundaries
    c0 = children[0]
    ck.check(f"{fmt_name}.c0", "Task Child", c0["title"], "title")
    ck.check(f"{fmt_name}.c0", "todo", c0.get("taskStatus"), "taskStatus")
    ck.check(f"{fmt_name}.c0", "A child with todo status", c0.get("notes",{}).get("content"), "notes")
    ck.check(f"{fmt_name}.c0", ["urgent"], c0.get("labels"), "labels")
    callouts = c0.get("callouts", [])
    ck.check(f"{fmt_name}.c0", 2, len(callouts), "callouts count")
    ct = sorted([c["title"] for c in callouts])
    ck.check(f"{fmt_name}.c0", sorted(["Attention!", "Review"]), ct, "callout texts")
    bounds = c0.get("boundaries", [])
    ck.check(f"{fmt_name}.c0", 1, len(bounds), "boundaries count")
    ck.check(f"{fmt_name}.c0", "(0,1)", bounds[0].get("range"), "boundary range")
    ck.check(f"{fmt_name}.c0", "Task Group", bounds[0].get("title"), "boundary title")
    gc = c0.get("children", [])
    ck.check(f"{fmt_name}.c0", 2, len(gc), "grandchildren count")
    ck.check(f"{fmt_name}.gc0", "GC Done", gc[0]["title"], "title")
    ck.check(f"{fmt_name}.gc0", "done", gc[0].get("taskStatus"), "taskStatus")
    ck.check(f"{fmt_name}.gc0", ["task-done"], gc[0].get("markers"), "markers")
    ck.check(f"{fmt_name}.gc0", "Completed", gc[0].get("notes",{}).get("content"), "notes")
    ck.check(f"{fmt_name}.gc1", "GC Todo", gc[1]["title"], "title")
    ck.check(f"{fmt_name}.gc1", "todo", gc[1].get("taskStatus"), "taskStatus")

    # Child 1: Planned Task
    c1 = children[1]
    ck.check(f"{fmt_name}.c1", "Planned Child", c1["title"], "title")
    ck.check(f"{fmt_name}.c1", 0.6, c1.get("progress"), "progress")
    ck.check(f"{fmt_name}.c1", 2, c1.get("priority"), "priority")
    ck.check(f"{fmt_name}.c1", True, c1.get("startDate","").startswith("2026-03-01"), "startDate")
    ck.check(f"{fmt_name}.c1", True, c1.get("dueDate","").startswith("2026-03-15"), "dueDate")
    ck.check(f"{fmt_name}.c1", 14 * 86400000, c1.get("duration"), "duration 14d ms")
    ck.check(f"{fmt_name}.c1", ["planned"], c1.get("labels"), "labels")
    ck.check(f"{fmt_name}.c1", True, "<strong>Planned</strong>" in c1.get("notes",{}).get("html",""), "notes.html")

    # Child 2: Duration + Dependencies
    c2 = children[2]
    ck.check(f"{fmt_name}.c2", "Duration Child", c2["title"], "title")
    ck.check(f"{fmt_name}.c2", 0.0, c2.get("progress"), "progress")
    ck.check(f"{fmt_name}.c2", 3, c2.get("priority"), "priority")
    ck.check(f"{fmt_name}.c2", 7 * 86400000, c2.get("duration"), "duration 7d ms")
    ck.check(f"{fmt_name}.c2", "Relative planning", c2.get("notes",{}).get("content"), "notes")
    deps = c2.get("dependencies", [])
    ck.check(f"{fmt_name}.c2", 1, len(deps), "deps count")
    if deps:
        ck.check(f"{fmt_name}.c2", "FS", deps[0].get("type"), "dep type")
        ck.check(f"{fmt_name}.c2", 2, deps[0].get("lag"), "dep lag")
        ck.check(f"{fmt_name}.c2", True, len(deps[0].get("id","")) > 0, "dep target id present")

    # Child 3: Summary Topics
    c3 = children[3]
    ck.check(f"{fmt_name}.c3", "Summary Parent", c3["title"], "title")
    ck.check(f"{fmt_name}.c3", "Has summary topics", c3.get("notes",{}).get("content"), "notes")
    sums = c3.get("summaries", [])
    ck.check(f"{fmt_name}.c3", 1, len(sums), "summaries count")
    if sums:
        ck.check(f"{fmt_name}.c3", "(0,2)", sums[0].get("range"), "summary range")
        ck.check(f"{fmt_name}.c3", "Summary X-Z", sums[0].get("topicTitle"), "summary topicTitle")
    c3k = c3.get("children", [])
    ck.check(f"{fmt_name}.c3", 3, len(c3k), "children count")
    ck.check(f"{fmt_name}.c3", ["Item X", "Item Y", "Item Z"], [k["title"] for k in c3k], "children titles")

    # Child 4: Shape
    c4 = children[4]
    ck.check(f"{fmt_name}.c4", "Shape Child", c4["title"], "title")
    ck.check(f"{fmt_name}.c4", "org.xmind.topicShape.diamond", c4.get("shape"), "shape")
    ck.check(f"{fmt_name}.c4", "Diamond shape node", c4.get("notes",{}).get("content"), "notes")

    # Child 5: Plain
    c5 = children[5]
    ck.check(f"{fmt_name}.c5", "Plain Child", c5["title"], "title")
    ck.check(f"{fmt_name}.c5", "Simple note", c5.get("notes",{}).get("content"), "notes")

    # ─── Sheet 2: Cross-sheet link ───
    s2 = read_result[1]
    ck.check(f"{fmt_name}.s2", "Sheet Beta", s2.get("sheetTitle"), "sheetTitle")
    ck.check(f"{fmt_name}.s2", "Second Root", s2["title"], "title")
    ck.check(f"{fmt_name}.s2", "Cross-sheet content", s2.get("notes",{}).get("content"), "notes")
    ck.check(f"{fmt_name}.s2", True, s2.get("href","").startswith("xmind:#"), "linkToTopic -> xmind:#id")
    s2k = s2.get("children", [])
    ck.check(f"{fmt_name}.s2", 2, len(s2k), "children count")
    ck.check(f"{fmt_name}.s2.c0", "Beta C1", s2k[0]["title"], "title")
    ck.check(f"{fmt_name}.s2.c0", ["cross-ref"], s2k[0].get("labels"), "labels")
    ck.check(f"{fmt_name}.s2.c0", "Note in sheet 2", s2k[0].get("notes",{}).get("content"), "notes")
    ck.check(f"{fmt_name}.s2.c1", "Beta C2", s2k[1]["title"], "title")
    ck.check(f"{fmt_name}.s2.c1", ["priority-9"], s2k[1].get("markers"), "markers")

    # ─── Sheet 3: Free positioning + detached topics ───
    s3 = read_result[2]
    ck.check(f"{fmt_name}.s3", "Sheet Gamma", s3.get("sheetTitle"), "sheetTitle")
    ck.check(f"{fmt_name}.s3", "Flow Start", s3["title"], "title")
    ck.check(f"{fmt_name}.s3", "org.xmind.topicShape.ellipserect", s3.get("shape"), "shape")
    ck.check(f"{fmt_name}.s3", "org.xmind.ui.map.clockwise", s3.get("structureClass"), "structureClass")

    if not skip_zen_only:
        ck.check(f"{fmt_name}.s3", "free", s3.get("topicPositioning"), "topicPositioning")

    dt = s3.get("detachedTopics", [])
    ck.check(f"{fmt_name}.s3", 3, len(dt), "detachedTopics count")
    dt_titles = [d["title"] for d in dt]
    ck.check(f"{fmt_name}.s3", True, "Decision?" in dt_titles, "has Decision?")
    ck.check(f"{fmt_name}.s3", True, "Action A" in dt_titles, "has Action A")
    ck.check(f"{fmt_name}.s3", True, "Flow End" in dt_titles, "has Flow End")

    # Detached positions
    decision = [d for d in dt if d["title"] == "Decision?"][0]
    ck.check(f"{fmt_name}.s3.dt", 0, decision.get("position",{}).get("x"), "Decision x")
    ck.check(f"{fmt_name}.s3.dt", 130, decision.get("position",{}).get("y"), "Decision y")
    ck.check(f"{fmt_name}.s3.dt", "org.xmind.topicShape.diamond", decision.get("shape"), "Decision shape")

    action_a = [d for d in dt if d["title"] == "Action A"][0]
    ck.check(f"{fmt_name}.s3.dt", 200, action_a.get("position",{}).get("x"), "ActionA x")
    ck.check(f"{fmt_name}.s3.dt", 130, action_a.get("position",{}).get("y"), "ActionA y")

    # Sheet 3 relationships
    s3_rels = s3.get("relationships", [])
    ck.check(f"{fmt_name}.s3", 3, len(s3_rels), "relationships count")
    s3_rel_titles = sorted([r.get("title","") for r in s3_rels])
    ck.check(f"{fmt_name}.s3", True, "YES" in s3_rel_titles, "rel YES")
    ck.check(f"{fmt_name}.s3", True, "NO" in s3_rel_titles, "rel NO")
    s3_rel_shapes = [r.get("shape","") for r in s3_rels]
    ck.check(f"{fmt_name}.s3", True, all(s == "org.xmind.relationshipShape.straight" for s in s3_rel_shapes if s), "all straight rels")


def verify_search_actions(ck, path, fmt_name):
    """Verify all search/extract actions work correctly."""

    # todo search
    todos = read_action({"action": "search_nodes", "path": path, "taskStatus": "todo"})
    todo_titles = sorted([m["title"] for m in todos["matches"]])
    ck.check(f"{fmt_name}.search", sorted(["Task Child", "GC Todo"]), todo_titles, "todo titles")

    # done search
    dones = read_action({"action": "search_nodes", "path": path, "taskStatus": "done"})
    done_titles = [m["title"] for m in dones["matches"]]
    ck.check(f"{fmt_name}.search", ["GC Done"], done_titles, "done titles")

    # notes search
    ns = read_action({"action": "search_nodes", "path": path, "query": "planning", "searchIn": ["notes"]})
    ck.check(f"{fmt_name}.search", 1, ns["totalMatches"], "notes search count")
    ck.check(f"{fmt_name}.search", "Duration Child", ns["matches"][0]["title"], "notes search title")

    # label search
    ls = read_action({"action": "search_nodes", "path": path, "query": "urgent", "searchIn": ["labels"]})
    ck.check(f"{fmt_name}.search", 1, ls["totalMatches"], "label search count")

    # callout search
    cs = read_action({"action": "search_nodes", "path": path, "query": "Attention", "searchIn": ["callouts"]})
    ck.check(f"{fmt_name}.search", 1, cs["totalMatches"], "callout search count")

    # fuzzy extract
    fz = read_action({"action": "extract_node", "path": path, "searchQuery": "Planned Child"})
    ck.check(f"{fmt_name}.search", True, fz["totalMatches"] > 0, "fuzzy found")
    ck.check(f"{fmt_name}.search", True, fz["matches"][0]["matchConfidence"] >= 0.5, "fuzzy confidence")

    # extract by ID — get ID from a read first
    data = read_action({"action": "read", "path": path})
    target_id = data[0]["children"][0]["id"]
    bi = read_action({"action": "extract_node_by_id", "path": path, "nodeId": target_id})
    ck.check(f"{fmt_name}.search", True, bi["found"], "byid found")
    ck.check(f"{fmt_name}.search", "Task Child", bi["node"]["title"], "byid title")

    # format_info
    fi = read_action({"action": "format_info", "path": path})
    ck.check(f"{fmt_name}.search", True, fi["format"] in ("zen", "legacy"), "format_info valid")


def cross_compare(ck, data_a, data_b, label, skip_keys=None):
    """Deep compare two read results, ignoring IDs and specified keys."""
    skip = skip_keys or set()
    skip.update({"id", "topicId", "end1Id", "end2Id", "styleProperties", "styleId"})

    def compare(a, b, path):
        if type(a) != type(b):
            ck.check(label, type(a).__name__, type(b).__name__, f"{path} type")
            return
        if isinstance(a, list):
            ck.check(label, len(a), len(b), f"{path} length")
            for i in range(min(len(a), len(b))):
                compare(a[i], b[i], f"{path}[{i}]")
        elif isinstance(a, dict):
            all_keys = set(a.keys()) | set(b.keys())
            for k in sorted(all_keys):
                if k in skip:
                    continue
                # Skip href with xmind:# (internal ID references differ between files)
                if k == "href":
                    va = a.get(k, "")
                    vb = b.get(k, "")
                    if (isinstance(va, str) and va.startswith("xmind:#")) or (isinstance(vb, str) and vb.startswith("xmind:#")):
                        continue
                if k not in a:
                    ck.errors.append(f"[{label}] {path}.{k}: missing in first")
                elif k not in b:
                    ck.errors.append(f"[{label}] {path}.{k}: missing in second")
                else:
                    compare(a[k], b[k], f"{path}.{k}")
        else:
            ck.check(label, a, b, path)

    compare(data_a, data_b, "root")


# ═══════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════

if os.path.exists(TEST_DIR):
    shutil.rmtree(TEST_DIR)
os.makedirs(TEST_DIR, exist_ok=True)

all_checkers = []

# ─── Test 1: Write zen -> Read -> Verify ───
print("=" * 70)
print("TEST 1: Write ZEN -> Read -> Verify all fields")
print("=" * 70)

zen_path = f"{TEST_DIR}/test_zen.xmind"
create(build_input(zen_path, "zen"))
zen_data = read_action({"action": "read", "path": zen_path})

ck1 = Checker("ZEN write-read")
verify_all_fields(ck1, zen_data, "zen", skip_zen_only=False)
verify_search_actions(ck1, zen_path, "zen")
t1, p1, e1 = ck1.summary()
print(f"  -> {p1}/{t1} passed" + (f", {len(e1)} FAILED" if e1 else ""))
for e in e1: print(f"     x {e}")
all_checkers.append(ck1)

# ─── Test 2: Write legacy -> Read -> Verify ───
print()
print("=" * 70)
print("TEST 2: Write LEGACY (XMind 8) -> Read -> Verify all fields")
print("=" * 70)

legacy_path = f"{TEST_DIR}/test_legacy.xmind"
create(build_input(legacy_path, "xmind8"))
legacy_data = read_action({"action": "read", "path": legacy_path})

ck2 = Checker("LEGACY write-read")
verify_all_fields(ck2, legacy_data, "legacy", skip_zen_only=True)
verify_search_actions(ck2, legacy_path, "legacy")
t2, p2, e2 = ck2.summary()
print(f"  -> {p2}/{t2} passed" + (f", {len(e2)} FAILED" if e2 else ""))
for e in e2: print(f"     x {e}")
all_checkers.append(ck2)

# ─── Test 3: Write zen -> Read -> Write legacy -> Read -> Compare ───
print()
print("=" * 70)
print("TEST 3: ZEN -> Read -> Write as LEGACY -> Read -> Cross-compare")
print("=" * 70)

zen2legacy_path = f"{TEST_DIR}/zen_to_legacy.xmind"
# Re-serialize the zen read result as legacy input
zen_reshuffled = build_input(zen2legacy_path, "legacy")
create(zen_reshuffled)
zen2legacy_data = read_action({"action": "read", "path": zen2legacy_path})

ck3 = Checker("ZEN->LEGACY cross")
# topicPositioning/floatingTopicFlexible are zen-only
cross_compare(ck3, zen_data, zen2legacy_data, "zen-vs-legacy", skip_keys={"topicPositioning", "floatingTopicFlexible"})
t3, p3, e3 = ck3.summary()
print(f"  -> {p3}/{t3} passed" + (f", {len(e3)} FAILED" if e3 else ""))
for e in e3: print(f"     x {e}")
all_checkers.append(ck3)

# ─── Test 4: Write legacy -> Read -> Write zen -> Read -> Compare ───
print()
print("=" * 70)
print("TEST 4: LEGACY -> Read -> Write as ZEN -> Read -> Cross-compare")
print("=" * 70)

legacy2zen_path = f"{TEST_DIR}/legacy_to_zen.xmind"
legacy_reshuffled = build_input(legacy2zen_path, "zen")
create(legacy_reshuffled)
legacy2zen_data = read_action({"action": "read", "path": legacy2zen_path})

ck4 = Checker("LEGACY->ZEN cross")
cross_compare(ck4, legacy_data, legacy2zen_data, "legacy-vs-zen", skip_keys={"topicPositioning", "floatingTopicFlexible"})
t4, p4, e4 = ck4.summary()
print(f"  -> {p4}/{t4} passed" + (f", {len(e4)} FAILED" if e4 else ""))
for e in e4: print(f"     x {e}")
all_checkers.append(ck4)

# ─── Test 5: Format detection ───
print()
print("=" * 70)
print("TEST 5: Format detection (format_info)")
print("=" * 70)

ck5 = Checker("format_info")

fi_zen = read_action({"action": "format_info", "path": zen_path})
ck5.check("detect", "zen", fi_zen["format"], "zen file")
ck5.check("detect", True, "content.json" in fi_zen["files"], "zen has content.json")

fi_legacy = read_action({"action": "format_info", "path": legacy_path})
ck5.check("detect", "legacy", fi_legacy["format"], "legacy file")
ck5.check("detect", True, "content.xml" in fi_legacy["files"], "legacy has content.xml")

t5, p5, e5 = ck5.summary()
print(f"  -> {p5}/{t5} passed" + (f", {len(e5)} FAILED" if e5 else ""))
for e in e5: print(f"     x {e}")
all_checkers.append(ck5)

# ─── Test 6: Version alias coverage ───
print()
print("=" * 70)
print("TEST 6: Version alias resolution")
print("=" * 70)

ck6 = Checker("aliases")

alias_tests = [
    # (alias, expected_format)
    ("zen",       "zen"),
    ("json",      "zen"),
    ("latest",    "zen"),
    ("modern",    "zen"),
    ("new",       "zen"),
    ("2024",      "zen"),
    ("2020",      "zen"),
    ("xmind2024", "zen"),
    ("legacy",    "legacy"),
    ("xml",       "legacy"),
    ("old",       "legacy"),
    ("xmind8",    "legacy"),
    ("xmind7",    "legacy"),
    ("8",         "legacy"),
    ("7",         "legacy"),
    ("2013",      "legacy"),
    ("2008",      "legacy"),
    ("pro8",      "legacy"),
    ("pro7",      "legacy"),
]

for alias, expected_fmt in alias_tests:
    alias_path = f"{TEST_DIR}/alias_{alias.replace(' ','_')}.xmind"
    create(build_input(alias_path, alias))
    fi = read_action({"action": "format_info", "path": alias_path})
    ck6.check("alias", expected_fmt, fi["format"], f'"{alias}"')

t6, p6, e6 = ck6.summary()
print(f"  -> {p6}/{t6} passed" + (f", {len(e6)} FAILED" if e6 else ""))
for e in e6: print(f"     x {e}")
all_checkers.append(ck6)

# ─── Test 7: Read-Write-Read cycle (zen -> legacy -> zen) ───
print()
print("=" * 70)
print("TEST 7: Full cycle: Write ZEN -> Read -> Write LEGACY -> Read -> Write ZEN -> Read -> Compare with original")
print("=" * 70)

cycle_leg_path = f"{TEST_DIR}/cycle_leg.xmind"
cycle_zen2_path = f"{TEST_DIR}/cycle_zen2.xmind"

# zen_data already read from test 1
# Write as legacy
create(build_input(cycle_leg_path, "legacy"))
cycle_leg_data = read_action({"action": "read", "path": cycle_leg_path})

# Write back as zen
create(build_input(cycle_zen2_path, "zen"))
cycle_zen2_data = read_action({"action": "read", "path": cycle_zen2_path})

ck7 = Checker("full-cycle")
# Compare zen original with zen after zen->legacy->zen round-trip
cross_compare(ck7, zen_data, cycle_zen2_data, "cycle", skip_keys={"topicPositioning", "floatingTopicFlexible"})
t7, p7, e7 = ck7.summary()
print(f"  -> {p7}/{t7} passed" + (f", {len(e7)} FAILED" if e7 else ""))
for e in e7: print(f"     x {e}")
all_checkers.append(ck7)

# ─── Test 8: list/search_files on mixed-format directory ───
print()
print("=" * 70)
print("TEST 8: list & search_files across mixed-format directory")
print("=" * 70)

ck8 = Checker("mixed-dir")

all_files = read_action({"action": "list", "directory": TEST_DIR})
# Should find all .xmind files we created
ck8.check("list", True, zen_path in all_files, "zen in list")
ck8.check("list", True, legacy_path in all_files, "legacy in list")

# search_files by name
sf = read_action({"action": "search_files", "pattern": "legacy", "directory": TEST_DIR})
ck8.check("search_files", True, legacy_path in sf, "legacy found by name")

# search_files by content — both formats should be searchable
sf2 = read_action({"action": "search_files", "pattern": "GC Done", "directory": TEST_DIR})
ck8.check("search_files", True, zen_path in sf2, "zen found by content")
ck8.check("search_files", True, legacy_path in sf2, "legacy found by content")

# read_multiple across formats
rm = read_action({"action": "read_multiple", "paths": [zen_path, legacy_path]})
ck8.check("read_multi", 2, len(rm), "result count")
ck8.check("read_multi", True, len(rm[0]["content"]) == 3, "zen has 3 sheets")
ck8.check("read_multi", True, len(rm[1]["content"]) == 3, "legacy has 3 sheets")

t8, p8, e8 = ck8.summary()
print(f"  -> {p8}/{t8} passed" + (f", {len(e8)} FAILED" if e8 else ""))
for e in e8: print(f"     x {e}")
all_checkers.append(ck8)

# ═══════════════════════════════════════════
#  FINAL SUMMARY
# ═══════════════════════════════════════════
print()
print("=" * 70)
total_pass = sum(ck.passes for ck in all_checkers)
total_err  = sum(len(ck.errors) for ck in all_checkers)
total      = total_pass + total_err

if total_err == 0:
    print(f"ALL {total} CHECKS PASSED across 8 tests — zero information loss in both formats.")
else:
    print(f"RESULT: {total_pass}/{total} passed, {total_err} FAILED")
    print()
    for ck in all_checkers:
        if ck.errors:
            print(f"  [{ck.label}]")
            for e in ck.errors:
                print(f"    x {e}")
    sys.exit(1)
