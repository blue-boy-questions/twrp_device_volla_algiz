#!/usr/bin/env python3
"""Remove deprecated FDE codepaths from TWRP android-14.1 recovery sources.

partition.cpp and partitionmanager.cpp call legacy Full Disk Encryption (FDE)
functions that android-14.1 system/vold no longer declares in cryptfs.h:
  set_partition_data, cryptfs_check_footer, cryptfs_get_password_type,
  cryptfs_check_passwd, delete_crypto_blk_dev
FDE was removed industry-wide as of Android 10 in favour of FBE (AOSP
system/vold commit 0803ba0, "Remove most of FDE support"). Building with
TW_INCLUDE_CRYPTO on this FBE-only device fails with:
  error: use of undeclared identifier 'cryptfs_check_footer'  (and 4 more)

This applies TWRP upstream Gerrit change 8744 verbatim (removes the dead FDE
branches; FBE paths are unaffected because they are guarded by TW_IS_FBE which
is always true on this device). Blocks are stored base64-encoded so the exact
whitespace matches current upstream byte-for-byte. Idempotent and loud: aborts
on upstream drift (occurrence-count mismatch) instead of silently no-op'ing.
"""
import sys, os, base64

WS = sys.argv[1] if len(sys.argv) > 1 else "."
RE = os.path.join(WS, "bootable/recovery")

# (filename, base64(old), base64(new))
EDITS = [
    ('partition.cpp', 'CQkJCXNldF9wYXJ0aXRpb25fZGF0YShVc2VfT3JpZ2luYWxfUGF0aCA/IE9yaWdpbmFsX1BhdGguY19zdHIoKSA6IEFjdHVhbF9CbG9ja19EZXZpY2UuY19zdHIoKSwgQ3J5cHRvX0tleV9Mb2NhdGlvbi5jX3N0cigpKTsKCQkJCWlmIChjcnlwdGZzX2NoZWNrX2Zvb3RlcigpID09IDApIHsKCQkJCQlJc19FbmNyeXB0ZWQgPSB0cnVlOwoJCQkJCUlzX0RlY3J5cHRlZCA9IGZhbHNlOwoJCQkJCUNhbl9CZV9Nb3VudGVkID0gZmFsc2U7CgkJCQkJQ3VycmVudF9GaWxlX1N5c3RlbSA9ICJlbW1jIjsKCQkJCQlTZXR1cF9JbWFnZSgpOwoJCQkJCURhdGFNYW5hZ2VyOjpTZXRWYWx1ZShUV19DUllQVE9fUFdUWVBFLCBjcnlwdGZzX2dldF9wYXNzd29yZF90eXBlKCkpOwoJCQkJCURhdGFNYW5hZ2VyOjpTZXRWYWx1ZSgidHdfY3J5cHRvX3B3dHlwZV8wIiwgY3J5cHRmc19nZXRfcGFzc3dvcmRfdHlwZSgpKTsKCQkJCQlEYXRhTWFuYWdlcjo6U2V0VmFsdWUoVFdfQ1JZUFRPX1BBU1NXT1JELCAiIik7CgkJCQkJRGF0YU1hbmFnZXI6OlNldFZhbHVlKCJ0d19jcnlwdG9fZGlzcGxheSIsICIiKTsKCQkJCQlpZiAoZGF0YW1lZGlhKQoJCQkJCQlTZXR1cF9EYXRhX01lZGlhKCk7CgkJCQl9IGVsc2UgewoJCQkJCWd1aV9lcnIoIm1vdW50X2RhdGFfZm9vdGVyPUNvdWxkIG5vdCBtb3VudCAvZGF0YSBhbmQgdW5hYmxlIHRvIGZpbmQgY3J5cHRvIGZvb3Rlci4iKTsKCQkJCX0K', 'CQkJCS8vIExlZ2FjeSBGREUgKEZ1bGwgRGlzayBFbmNyeXB0aW9uKSBmb290ZXItYmFzZWQgZGV0ZWN0aW9uIHJlbW92ZWQuCgkJCQkvLyBGREUgd2FzIGRlcHJlY2F0ZWQgaW5kdXN0cnktd2lkZSBhcyBvZiBBbmRyb2lkIDEwIGluIGZhdm9yIG9mIEZCRQoJCQkJLy8gKHNlZSBBT1NQIHN5c3RlbS92b2xkIGNvbW1pdCAwODAzYmEwLCAiUmVtb3ZlIG1vc3Qgb2YgRkRFIHN1cHBvcnQiKS4KCQkJCS8vIFRoaXMgZGV2aWNlIGlzIEZCRS1vbmx5OyBmb290ZXItYmFzZWQgY3J5cHRvIGRldGVjdGlvbiBpcyBub3QgYXBwbGljYWJsZS4KCQkJCWd1aV9lcnIoIm1vdW50X2RhdGFfZm9vdGVyPUNvdWxkIG5vdCBtb3VudCAvZGF0YSBhbmQgdW5hYmxlIHRvIGZpbmQgY3J5cHRvIGZvb3Rlci4iKTsK'),
    ('partition.cpp', 'CWlmIChJc19EZWNyeXB0ZWQgJiYgIURlY3J5cHRlZF9CbG9ja19EZXZpY2UuZW1wdHkoKSkgewoJCWlmIChkZWxldGVfY3J5cHRvX2Jsa19kZXYoKGNoYXIqKSgidXNlcmRhdGEiKSkgIT0gMCkgewoJCQlMT0dFUlIoIkVycm9yIGRlbGV0aW5nIGNyeXB0byBibG9jayBkZXZpY2UsIGNvbnRpbnVpbmcgYW55d2F5LlxuIik7CgkJfQoJfQo=', 'CS8vIExlZ2FjeSBGREUgY3J5cHRvIGJsb2NrIGRldmljZSBkZWxldGlvbiByZW1vdmVkOyBub3QgYXBwbGljYWJsZSBvbiBGQkUtb25seSBkZXZpY2VzLgo='),
    ('partitionmanager.cpp', 'CQkJTE9HSU5GTygiRkJFIHNldHVwIGZhaWxlZC4gVHJ5aW5nIEZERS4uLlxuIik7CgkJCVNldF9DcnlwdG9fU3RhdGUoKTsKCQkJU2V0X0NyeXB0b19UeXBlKCJibG9jayIpOwoJCQlpbnQgcGFzc3dvcmRfdHlwZSA9IGNyeXB0ZnNfZ2V0X3Bhc3N3b3JkX3R5cGUoKTsKCQkJaWYgKHBhc3N3b3JkX3R5cGUgPT0gQ1JZUFRfVFlQRV9ERUZBVUxUKSB7CgkJCQlMT0dJTkZPKCJEZXZpY2UgaXMgZW5jcnlwdGVkIHdpdGggdGhlIGRlZmF1bHQgcGFzc3dvcmQsIGF0dGVtcHRpbmcgdG8gZGVjcnlwdC5cbiIpOwoJCQkJaWYgKERlY3J5cHRfRGV2aWNlKCJkZWZhdWx0X3Bhc3N3b3JkIikgPT0gMCkgewoJCQkJCWd1aV9tc2coImRlY3J5cHRfc3VjY2Vzcz1TdWNjZXNzZnVsbHkgZGVjcnlwdGVkIHdpdGggZGVmYXVsdCBwYXNzd29yZC4iKTsKCQkJCQlEYXRhTWFuYWdlcjo6U2V0VmFsdWUoVFdfSVNfRU5DUllQVEVELCAwKTsKCQkJCX0gZWxzZSB7CgkJCQkJZ3VpX2VycigidW5hYmxlX3RvX2RlY3J5cHQ9VW5hYmxlIHRvIGRlY3J5cHQgd2l0aCBkZWZhdWx0IHBhc3N3b3JkLiIpOwoJCQkJfQoJCQl9IGVsc2UgewoJCQkJRGF0YU1hbmFnZXI6OlNldFZhbHVlKCJUV19DUllQVE9fVFlQRSIsIHBhc3N3b3JkX3R5cGUpOwoJCQkJRGF0YU1hbmFnZXI6OlNldFZhbHVlKCJ0d19jcnlwdG9fcHd0eXBlXzAiLCBwYXNzd29yZF90eXBlKTsKCQkJfQo=', 'CQkJLy8gTGVnYWN5IEZERSBmYWxsYmFjayByZW1vdmVkOyBGREUgd2FzIGRlcHJlY2F0ZWQgYXMgb2YgQW5kcm9pZCAxMAoJCQkvLyAoc2VlIEFPU1Agc3lzdGVtL3ZvbGQgY29tbWl0IDA4MDNiYTApLiBUaGlzIGRldmljZSBpcyBGQkUtb25seSwKCQkJLy8gc28gYSBmYWlsZWQgRkJFIHNldHVwIGhhcyBubyBsZWdhY3kgZmFsbGJhY2sgcGF0aC4KCQkJTE9HRVJSKCJGQkUgc2V0dXAgZmFpbGVkIGFuZCBubyBsZWdhY3kgRkRFIHN1cHBvcnQgaXMgYXZhaWxhYmxlIG9uIHRoaXMgZGV2aWNlLlxuIik7CgkJCWd1aV9lcnIoInVuYWJsZV90b19kZWNyeXB0PVVuYWJsZSB0byBkZWNyeXB0IHdpdGggZGVmYXVsdCBwYXNzd29yZC4iKTsK'),
    ('partitionmanager.cpp', 'CWNoYXIgaXNkZWNyeXB0ZWRkYXRhW1BST1BFUlRZX1ZBTFVFX01BWF07Cglwcm9wZXJ0eV9nZXQoInR3cnAuZGVjcnlwdC5kb25lIiwgaXNkZWNyeXB0ZWRkYXRhLCAiIik7CglpZiAoc3RyY21wKGlzZGVjcnlwdGVkZGF0YSwgInRydWUiKSA9PSAwKSB7CgkJTE9HSU5GTygiRGF0YSBoYXMgbm8gZGVjcnlwdGlvbiByZXF1aXJlZFxuIik7CgkJcmV0dXJuIDA7Cgl9CgoJaW50IHB3cmV0ID0gLTE7CglwaWRfdCBwaWQgPSBmb3JrKCk7CglpZiAocGlkIDwgMCkgewoJCUxPR0VSUigiZm9yayBmYWlsZWRcbiIpOwoJCXJldHVybiAtMTsKCX0gZWxzZSBpZiAocGlkID09IDApIHsKCQkvLyBDaGlsZCBwcm9jZXNzCgkJY2hhciBjUGFzc3dvcmRbMjU1XTsKCQlzdHJjcHkoY1Bhc3N3b3JkLCBQYXNzd29yZC5jX3N0cigpKTsKCQlpbnQgcmV0ID0gY3J5cHRmc19jaGVja19wYXNzd2QoY1Bhc3N3b3JkKTsKCQlleGl0KHJldCk7Cgl9IGVsc2UgewoJCS8vIFBhcmVudAoJCWludCBzdGF0dXM7CgkJaWYgKFRXRnVuYzo6V2FpdF9Gb3JfQ2hpbGRfVGltZW91dChwaWQsICZzdGF0dXMsICJEZWNyeXB0IiwgMzApKQoJCQlwd3JldCA9IC0xOwoJCWVsc2UKCQkJcHdyZXQgPSBXRVhJVFNUQVRVUyhzdGF0dXMpID8gLTEgOiAwOwoJfQo=', 'CS8vIExlZ2FjeSBGREUgcGFzc3dvcmQgdmVyaWZpY2F0aW9uIHJlbW92ZWQ7IEZERSB3YXMgZGVwcmVjYXRlZCBhcyBvZgoJLy8gQW5kcm9pZCAxMCAoc2VlIEFPU1Agc3lzdGVtL3ZvbGQgY29tbWl0IDA4MDNiYTApLiBUaGlzIGRldmljZSBpcwoJLy8gRkJFLW9ubHksIHNvIHRoaXMgY29kZXBhdGggaXMgdW5yZWFjaGFibGUgKFRXX0lTX0ZCRSByZXR1cm5zIGFib3ZlKSwKCS8vIGJ1dCBpcyBrZXB0IGNvbXBpbGluZyBhcyBhIHNhZmUgZmFsbGJhY2suCglMT0dFUlIoIk5vIGxlZ2FjeSBGREUgZGVjcnlwdGlvbiBwYXRoIGlzIGF2YWlsYWJsZSBvbiB0aGlzIGRldmljZS5cbiIpOwo='),
    ('partitionmanager.cpp', 'CWlmIChwd3JldCAhPSAwKSB7CgkJZ3VpX2VycigiZmFpbF9kZWNyeXB0PUZhaWxlZCB0byBkZWNyeXB0IGRhdGEuIik7CgkJcmV0dXJuIC0xOwoJfQoKCXByb3BlcnR5X2dldCgicm8uY3J5cHRvLmZzX2NyeXB0b19ibGtkZXYiLCBjcnlwdG9fYmxrZGV2LCAiZXJyb3IiKTsKCWlmIChzdHJjbXAoY3J5cHRvX2Jsa2RldiwgImVycm9yIikgPT0gMCkgewoJCUxPR0VSUigiRXJyb3IgcmV0cmlldmluZyBkZWNyeXB0ZWQgZGF0YSBibG9jayBkZXZpY2UuXG4iKTsKCX0gZWxzZSB7CgkJUG9zdF9EZWNyeXB0KGNyeXB0b19ibGtkZXYpOwoJfQoJcmV0dXJuIDA7Cg==', 'CWd1aV9lcnIoImZhaWxfZGVjcnlwdD1GYWlsZWQgdG8gZGVjcnlwdCBkYXRhLiIpOwoJcmV0dXJuIC0xOwo='),
]

FDE_SYMS = ["set_partition_data", "cryptfs_check_footer",
            "cryptfs_get_password_type", "cryptfs_check_passwd",
            "delete_crypto_blk_dev"]

def read(p):
    with open(p, "r", encoding="utf-8", errors="surrogateescape") as fh:
        return fh.read()

def write(p, t):
    with open(p, "w", encoding="utf-8", errors="surrogateescape") as fh:
        fh.write(t)

# group edits per file
bufs = {}
for fn, b_old, b_new in EDITS:
    path = os.path.join(RE, fn)
    if not os.path.isfile(path):
        sys.exit(f"::error::missing source file: {path}")
    bufs.setdefault(path, read(path))

for fn, b_old, b_new in EDITS:
    path = os.path.join(RE, fn)
    old = base64.b64decode(b_old).decode()
    new = base64.b64decode(b_new).decode()
    txt = bufs[path]
    if new in txt and old not in txt:
        continue  # already applied
    n = txt.count(old)
    if n != 1:
        sys.exit(f"::error::{fn}: expected exactly 1 occurrence of an FDE block "
                 f"but found {n} (upstream drift vs Gerrit 8744 base)")
    bufs[path] = txt.replace(old, new, 1)

for path, txt in bufs.items():
    write(path, txt)

# structural verification: no removed FDE symbol may remain
errs = []
for path in bufs:
    t = read(path)
    for sym in FDE_SYMS:
        if sym in t:
            errs.append(f"{os.path.basename(path)}: {sym} still present after patch")
if errs:
    print("::error::FDE removal patch incomplete:")
    for e in errs:
        print("  " + e)
    sys.exit(1)

print("FDE-removal patch applied cleanly (partition.cpp, partitionmanager.cpp)")
