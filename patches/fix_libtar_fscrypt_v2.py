#!/usr/bin/env python3
# Fix TWRP android-14.1 libtar FBE crypto against android-14.1 system/vold.
#
# ROOT CAUSE
#   TWRP's bootable/recovery/libtar (libtar.h, block.c, append.c) was written
#   against the OLD vold crypto API that exported a `union fscrypt_policy`
#   typedef plus helpers: get_policy(), fscrypt_policy_size(),
#   get_policy_size(), get_policy_descriptor(), get_policy_content().
#   android-14.1 system/vold DROPPED all of that; it now exposes only the
#   v1/v2-overloaded fscrypt_policy_get_struct() and lookup_ref_key()
#   (selected by -DUSE_FSCRYPT_POLICY_V1 / _V2). libtar therefore fails:
#     libtar.h:74  must use 'struct' tag to refer to type 'fscrypt_policy_v1'
#     block.c/append.c  calls to undeclared get_policy*/fscrypt_policy_size.
#
# FIX
#   algiz is FBE v2 (BoardConfig TW_USE_FSCRYPT_POLICY := 2 -> -DUSE_FSCRYPT_POLICY_V2).
#   Make libtar v2-only so it matches vold's v2 overloads exactly:
#     th_buf.fep                   -> struct fscrypt_policy_v2 *
#     get_policy(fep)              -> (void*)fep
#     fscrypt_policy_size(fep)     -> sizeof(struct fscrypt_policy_v2)
#     get_policy_size(fep,false)   -> FSCRYPT_KEY_IDENTIFIER_SIZE      (16)
#     get_policy_size(fep,true)    -> FSCRYPT_KEY_IDENTIFIER_HEX_SIZE  (33)
#     get_policy_descriptor(fep)   -> fep->master_key_identifier
#     get_policy_content(fep,buf)  -> snprintf version string
#   fscrypt_policy_get_struct()/lookup_ref_key()/fep->version already work once
#   fep is a struct fscrypt_policy_v2 *.
#
# Idempotent and loud: each replacement must apply exactly as many times as
# expected; a count mismatch (upstream drift) aborts with a clear error so CI
# surfaces it instead of silently building a broken recovery.
import sys, os

WS = sys.argv[1] if len(sys.argv) > 1 else "."
LT = os.path.join(WS, "bootable/recovery/libtar")
HDR = os.path.join(LT, "libtar.h")
BLK = os.path.join(LT, "block.c")
APP = os.path.join(LT, "append.c")

BROKEN_MARKERS = [
    "fscrypt_policy  *fep;",
    "get_policy(",
    "fscrypt_policy_size(",
    "get_policy_size(",
    "get_policy_descriptor(",
    "get_policy_content(",
    "(fscrypt_policy*)",
    "(fscrypt_policy *)",
]

# (file, old, new, expected_count)
EDITS = [
    (HDR,
     "\tfscrypt_policy  *fep;",
     "\tstruct fscrypt_policy_v2  *fep;", 1),

    (BLK,
     "t->th_buf.fep = (fscrypt_policy*)malloc(sizeof(fscrypt_policy));",
     "t->th_buf.fep = (struct fscrypt_policy_v2*)malloc(sizeof(struct fscrypt_policy_v2));", 1),
    (BLK,
     "memcpy(get_policy(t->th_buf.fep), start, fscrypt_policy_size(t->th_buf.fep));",
     "memcpy((void*)t->th_buf.fep, start, sizeof(struct fscrypt_policy_v2));", 1),
    (BLK,
     "get_policy_content(t->th_buf.fep, content);",
     "snprintf(content, sizeof(content), \"%u\", (unsigned)t->th_buf.fep->version);", 1),
    (BLK,
     "size = fscrypt_policy_size(t->th_buf.fep);",
     "size = (uint8_t)sizeof(struct fscrypt_policy_v2);", 1),
    (BLK,
     "descriptor = get_policy_descriptor(t->th_buf.fep);",
     "descriptor = t->th_buf.fep->master_key_identifier;", 1),
    (BLK,
     "memcpy(ptr + sz - size - 1, get_policy(t->th_buf.fep), size);",
     "memcpy(ptr + sz - size - 1, (void*)t->th_buf.fep, size);", 1),

    (APP,
     "t->th_buf.fep = (fscrypt_policy *)malloc(sizeof(fscrypt_policy));",
     "t->th_buf.fep = (struct fscrypt_policy_v2 *)malloc(sizeof(struct fscrypt_policy_v2));", 1),
    (APP,
     "size = get_policy_size(t->th_buf.fep, false);",
     "size = (uint8_t)FSCRYPT_KEY_IDENTIFIER_SIZE;", 1),
    (APP,
     "hex_size = get_policy_size(t->th_buf.fep, true);",
     "hex_size = (uint8_t)FSCRYPT_KEY_IDENTIFIER_HEX_SIZE;", 1),
    (APP,
     "descriptor = get_policy_descriptor(t->th_buf.fep);",
     "descriptor = t->th_buf.fep->master_key_identifier;", 1),
]

for f in (HDR, BLK, APP):
    if not os.path.isfile(f):
        sys.exit(f"::error::missing source file: {f}")

def read(f):
    with open(f, "r", encoding="utf-8", errors="surrogateescape") as fh:
        return fh.read()

def any_broken():
    for f in (HDR, BLK, APP):
        txt = read(f)
        for m in BROKEN_MARKERS:
            if m in txt:
                return True
    return False

if not any_broken():
    print("libtar already patched for fscrypt v2; nothing to do")
    sys.exit(0)

bufs = {f: read(f) for f in (HDR, BLK, APP)}

for f, old, new, want in EDITS:
    txt = bufs[f]
    if new in txt and old not in txt:
        # already applied for this edit
        continue
    n = txt.count(old)
    if n != want:
        sys.exit(f"::error::{os.path.basename(f)}: expected {want} occurrence(s) of "
                 f"<<{old}>> but found {n} (upstream drift)")
    bufs[f] = txt.replace(old, new)

for f, txt in bufs.items():
    with open(f, "w", encoding="utf-8", errors="surrogateescape") as fh:
        fh.write(txt)

# verify clean
leftovers = []
for f in (HDR, BLK, APP):
    txt = read(f)
    for m in BROKEN_MARKERS:
        if m in txt:
            leftovers.append(f"{os.path.basename(f)}: {m}")
if leftovers:
    print("::error::libtar fscrypt v2 patch incomplete; still present:")
    for l in leftovers:
        print("  " + l)
    sys.exit(1)

print("libtar fscrypt v2 patch applied cleanly")
