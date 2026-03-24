#!/usr/bin/env python3
"""Test various real-world XMind file edge cases that could cause silent [] return"""
import subprocess, json, struct, zlib, os

_HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.join(_HERE, "..", "skills", "xmind", "scripts")

def make_zip_entry(name, data):
    crc = zlib.crc32(data) & 0xffffffff
    compressed = zlib.compress(data, 6)[2:-4]
    name_b = name.encode('utf-8')
    local = struct.pack('<IHHHHHIIIHH',
        0x04034b50, 20, 0, 8, 0, 0, crc, len(compressed), len(data), len(name_b), 0)
    return local + name_b + compressed, crc, len(compressed), len(data)

def build_zip(entries):
    parts, cd_entries, offset = [], [], 0
    for name, data in entries:
        local_data, crc, comp_size, uncomp_size = make_zip_entry(name, data)
        parts.append(local_data)
        name_b = name.encode('utf-8')
        cd = struct.pack('<IHHHHHHIIIHHHHHII',
            0x02014b50, 20, 20, 0, 8, 0, 0, crc, comp_size, uncomp_size,
            len(name_b), 0, 0, 0, 0, 0, offset)
        cd_entries.append(cd + name_b)
        offset += len(local_data)
    cd_data = b''.join(cd_entries)
    eocd = struct.pack('<IHHHHIIH',
        0x06054b50, 0, 0, len(entries), len(entries), len(cd_data), offset, 0)
    return b''.join(parts) + cd_data + eocd

def run_read(path):
    r = subprocess.run(
        ['node', os.path.join(SCRIPT_DIR, 'read_xmind.mjs')],
        input=json.dumps({"action": "read", "path": path}),
        capture_output=True, text=True,
        cwd=os.path.join(_HERE, "..")
    )
    return r.stdout.strip(), r.stderr.strip()

passed = 0
failed = 0
def check(name, stdout, stderr, expect_topics):
    global passed, failed
    try:
        data = json.loads(stdout) if stdout else []
    except:
        data = []
    # Count all topics recursively
    def count(node):
        n = 1
        for c in node.get('children', []): n += count(c)
        for c in node.get('detachedTopics', []): n += count(c)
        return n
    total = sum(count(s) for s in data)
    ok = total >= expect_topics
    status = "PASS" if ok else "FAIL"
    if not ok:
        failed += 1
        print(f"  {status}: {name} — got {total} topics (expected >={expect_topics}), stderr={stderr[:200]}")
    else:
        passed += 1
        print(f"  {status}: {name} — {total} topics")
    return ok

print("=" * 70)
print("Edge case tests for XMind parsing")
print("=" * 70)

# 1. content.json wrapped in object: {"sheets": [...]}
print("\n--- Test 1: content.json as {sheets: [...]} object wrapper ---")
content = {"sheets": [{"id":"s1","title":"Sheet","rootTopic":{"id":"t1","title":"Root","children":{"attached":[{"id":"t2","title":"Child"}]}}}]}
path = '/tmp/edge1.xmind'
with open(path, 'wb') as f:
    f.write(build_zip([('content.json', json.dumps(content).encode())]))
out, err = run_read(path)
check("Object wrapper {sheets:[...]}", out, err, 1)

# 2. content.json with BOM (byte order mark)
print("\n--- Test 2: content.json with UTF-8 BOM ---")
content_arr = [{"id":"s1","title":"Sheet","rootTopic":{"id":"t1","title":"Root","children":{"attached":[{"id":"t2","title":"Child"}]}}}]
path = '/tmp/edge2.xmind'
bom_json = b'\xef\xbb\xbf' + json.dumps(content_arr).encode('utf-8')
with open(path, 'wb') as f:
    f.write(build_zip([('content.json', bom_json)]))
out, err = run_read(path)
check("UTF-8 BOM in content.json", out, err, 2)

# 3. content.xml with namespace prefix on everything
print("\n--- Test 3: XML with namespace prefixes on all elements ---")
xml = '''<?xml version="1.0" encoding="UTF-8"?>
<ns:xmap-content xmlns:ns="urn:xmind:xmap:xmlns:content:2.0">
  <ns:sheet id="s1">
    <ns:title>Prefixed Sheet</ns:title>
    <ns:topic id="t1">
      <ns:title>Root</ns:title>
      <ns:children>
        <ns:topics type="attached">
          <ns:topic id="t2"><ns:title>Child A</ns:title></ns:topic>
        </ns:topics>
      </ns:children>
    </ns:topic>
  </ns:sheet>
</ns:xmap-content>'''
path = '/tmp/edge3.xmind'
with open(path, 'wb') as f:
    f.write(build_zip([('content.xml', xml.encode())]))
out, err = run_read(path)
check("Namespace-prefixed XML elements", out, err, 2)

# 4. content.xml with default namespace (no prefix but xmlns=)
print("\n--- Test 4: XML with default namespace (xmlns=...) ---")
xml = '''<?xml version="1.0" encoding="UTF-8"?>
<xmap-content xmlns="urn:xmind:xmap:xmlns:content:2.0" xmlns:fo="http://www.w3.org/1999/XSL/Format" xmlns:svg="http://www.w3.org/2000/svg">
  <sheet id="s1" timestamp="1703000000000">
    <title>Real Sheet</title>
    <topic id="t1" structure-class="org.xmind.ui.logic.right" timestamp="1703000001000">
      <title>Main Topic</title>
      <children>
        <topics type="attached">
          <topic id="t2"><title>Sub 1</title></topic>
          <topic id="t3"><title>Sub 2</title>
            <children>
              <topics type="attached">
                <topic id="t4"><title>Deep</title></topic>
              </topics>
            </children>
          </topic>
        </topics>
      </children>
    </topic>
  </sheet>
</xmap-content>'''
path = '/tmp/edge4.xmind'
with open(path, 'wb') as f:
    f.write(build_zip([('content.xml', xml.encode())]))
out, err = run_read(path)
check("Default namespace XML", out, err, 4)

# 5. content.xml where root is NOT xmap-content (e.g. just <content> or <workbook>)
print("\n--- Test 5: Non-standard root element ---")
xml = '''<?xml version="1.0" encoding="UTF-8"?>
<workbook>
  <sheet id="s1">
    <title>Alt Root</title>
    <topic id="t1"><title>Root</title></topic>
  </sheet>
</workbook>'''
path = '/tmp/edge5.xmind'
with open(path, 'wb') as f:
    f.write(build_zip([('content.xml', xml.encode())]))
out, err = run_read(path)
print(f"  INFO: Non-standard root — stderr: {err[:200]}")

# 6. Very large content.json with deeply nested topics
print("\n--- Test 6: Deep nesting (20 levels) ---")
def make_deep(depth, i=0):
    topic = {"id": f"t{i}", "title": f"Level {depth}"}
    if depth > 0:
        topic["children"] = {"attached": [make_deep(depth-1, i+1)]}
    return topic
content_arr = [{"id":"s1","title":"Deep","rootTopic": make_deep(20)}]
path = '/tmp/edge6.xmind'
with open(path, 'wb') as f:
    f.write(build_zip([('content.json', json.dumps(content_arr).encode())]))
out, err = run_read(path)
check("20-level deep nesting", out, err, 21)

# 7. content.xml with CRLF line endings
print("\n--- Test 7: CRLF line endings in XML ---")
xml = '<?xml version="1.0" encoding="UTF-8"?>\r\n<xmap-content xmlns="urn:xmind:xmap:xmlns:content:2.0">\r\n  <sheet id="s1">\r\n    <title>CRLF</title>\r\n    <topic id="t1">\r\n      <title>Root</title>\r\n      <children>\r\n        <topics type="attached">\r\n          <topic id="t2"><title>Child</title></topic>\r\n        </topics>\r\n      </children>\r\n    </topic>\r\n  </sheet>\r\n</xmap-content>'
path = '/tmp/edge7.xmind'
with open(path, 'wb') as f:
    f.write(build_zip([('content.xml', xml.encode())]))
out, err = run_read(path)
check("CRLF line endings", out, err, 2)

# 8. content.xml with mixed namespace prefixes (xmind desktop style)
print("\n--- Test 8: Mixed namespace prefixes (real XMind desktop) ---")
xml = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE xmap-content SYSTEM "xmap-content.dtd">
<xmap-content xmlns="urn:xmind:xmap:xmlns:content:2.0"
  xmlns:fo="http://www.w3.org/1999/XSL/Format"
  xmlns:svg="http://www.w3.org/2000/svg"
  xmlns:xhtml="http://www.w3.org/1999/xhtml"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  timestamp="1703123456789" version="2.0">
  <sheet id="1abc" timestamp="1703123456789">
    <title>Sheet 1</title>
    <topic id="2def" timestamp="1703123456789" structure-class="org.xmind.ui.map.clockwise">
      <title>Central Topic</title>
      <notes>
        <plain><content>Some plain note</content></plain>
        <xhtml:html xmlns:xhtml="http://www.w3.org/1999/xhtml">
          <xhtml:p>Some <xhtml:strong>rich</xhtml:strong> note</xhtml:p>
        </xhtml:html>
      </notes>
      <children>
        <topics type="attached">
          <topic id="3ghi" xlink:href="http://example.com" style-id="style1">
            <title>Link Topic</title>
            <marker-refs>
              <marker-ref marker-id="priority-1"/>
            </marker-refs>
            <labels><label>tag1</label></labels>
          </topic>
          <topic id="4jkl" branch="folded">
            <title>Folded Branch</title>
            <children>
              <topics type="attached">
                <topic id="5mno"><title>Hidden Child</title></topic>
              </topics>
            </children>
          </topic>
        </topics>
        <topics type="detached">
          <topic id="6pqr">
            <title>Floating</title>
            <position svg:x="100" svg:y="200"/>
          </topic>
        </topics>
      </children>
      <boundaries>
        <boundary id="b1" range="(0,1)"/>
      </boundaries>
    </topic>
    <relationships>
      <relationship id="r1" end1="3ghi" end2="4jkl">
        <title>connects</title>
      </relationship>
    </relationships>
  </sheet>
</xmap-content>'''
path = '/tmp/edge8.xmind'
with open(path, 'wb') as f:
    f.write(build_zip([
        ('content.xml', xml.encode()),
        ('META-INF/manifest.xml', b'<manifest/>'),
    ]))
out, err = run_read(path)
ok = check("Real XMind desktop file simulation", out, err, 5)
if ok:
    data = json.loads(out)
    root = data[0]
    # Verify specific fields
    checks = []
    checks.append(("structureClass", root.get('structureClass') == 'org.xmind.ui.map.clockwise'))
    checks.append(("notes.content", 'Some plain note' in str(root.get('notes', {}))))
    checks.append(("notes.html", 'rich' in str(root.get('notes', {}))))
    checks.append(("boundaries", len(root.get('boundaries', [])) == 1))
    checks.append(("relationships", len(root.get('relationships', [])) == 1))
    ch = root.get('children', [])
    checks.append(("child href", ch[0].get('href') == 'http://example.com' if ch else False))
    checks.append(("child markers", ch[0].get('markers') == ['priority-1'] if ch else False))
    checks.append(("child labels", ch[0].get('labels') == ['tag1'] if ch else False))
    checks.append(("child branch", ch[1].get('branch') == 'folded' if len(ch) > 1 else False))
    checks.append(("detachedTopics", len(root.get('detachedTopics', [])) == 1))
    checks.append(("detached position", root.get('detachedTopics', [{}])[0].get('position') == {'x': 100, 'y': 200}))
    for name, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok: failed += 1
        else: passed += 1
        print(f"    {status}: {name}")

# 9. content.json stored (compression=0) instead of deflated
print("\n--- Test 9: Stored (uncompressed) ZIP entries ---")
content_arr = [{"id":"s1","title":"Stored","rootTopic":{"id":"t1","title":"Root"}}]
content_bytes = json.dumps(content_arr).encode()
# Build ZIP with STORED entries
def make_stored_zip(entries):
    parts, cd_entries, offset = [], [], 0
    for name, data in entries:
        crc = zlib.crc32(data) & 0xffffffff
        name_b = name.encode('utf-8')
        local = struct.pack('<IHHHHHIIIHH',
            0x04034b50, 20, 0, 0, 0, 0, crc, len(data), len(data), len(name_b), 0)  # compression=0
        local_data = local + name_b + data
        parts.append(local_data)
        cd = struct.pack('<IHHHHHHIIIHHHHHII',
            0x02014b50, 20, 20, 0, 0, 0, 0, crc, len(data), len(data),
            len(name_b), 0, 0, 0, 0, 0, offset)
        cd_entries.append(cd + name_b)
        offset += len(local_data)
    cd_data = b''.join(cd_entries)
    eocd = struct.pack('<IHHHHIIH',
        0x06054b50, 0, 0, len(entries), len(entries), len(cd_data), offset, 0)
    return b''.join(parts) + cd_data + eocd

path = '/tmp/edge9.xmind'
with open(path, 'wb') as f:
    f.write(make_stored_zip([('content.json', content_bytes)]))
out, err = run_read(path)
check("Stored (uncompressed) ZIP", out, err, 1)

# 10. ZIP with extra data before EOCD (e.g. archive comment)
print("\n--- Test 10: ZIP with archive comment ---")
content_arr = [{"id":"s1","title":"Comment","rootTopic":{"id":"t1","title":"Root"}}]
path = '/tmp/edge10.xmind'
zip_data = build_zip([('content.json', json.dumps(content_arr).encode())])
# Append comment to EOCD
comment = b'XMind created this file'
# Fix EOCD comment length
eocd_pos = zip_data.rfind(b'\x50\x4b\x05\x06')
modified = bytearray(zip_data)
struct.pack_into('<H', modified, eocd_pos + 20, len(comment))
modified.extend(comment)
with open(path, 'wb') as f:
    f.write(bytes(modified))
out, err = run_read(path)
check("ZIP with archive comment", out, err, 1)

print(f"\n{'='*70}")
print(f"Results: {passed} passed, {failed} failed out of {passed+failed}")
print(f"{'='*70}")
