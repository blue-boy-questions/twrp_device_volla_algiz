#!/usr/bin/env python3
"""Fix TWRP android-14.1 libtar FBE crypto + link against android-14.1 system/vold.

Two coupled problems, both because android-14.1 vold diverged from what TWRP's
libtar module was written against:

(A) COMPILE: TWRP's libtar targets the OLD vold crypto API: a
    `union fscrypt_policy` typedef plus helpers get_policy(),
    fscrypt_policy_size(), get_policy_size(), get_policy_descriptor(),
    get_policy_content(). android-14.1 vold DROPPED all of that and now exposes
    only v1/v2-overloaded fscrypt_policy_get_struct(), fscrypt_policy_set_struct(),
    lookup_ref_key(), and a lookup_ref_tar() whose signature CHANGED to take the
    descriptor bytes (const uint8_t*) instead of the policy struct. bionic also
    `#define fscrypt_policy fscrypt_policy_v1`, so the bare name can't be a type.
    Used across 5 files: libtar.h, block.c, append.c, extract.c, output.c.

    Fix: device is FBE v2 (TW_USE_FSCRYPT_POLICY := 2 -> USE_FSCRYPT_POLICY_V2).
    Drop libtar/fscrypt_compat.h: static-inline v2 implementations of the five
    removed helpers (ported from android-12.1 vold v2 branches). Retype
    th_buf.fep to `struct fscrypt_policy_v2 *`, include the shim from libtar.h,
    retype the two malloc casts, and fix extract.c's lookup_ref_tar() call.

(B) LINK: libtar.so (a Make module) links the Soong static lib libvold.a. Make
    modules do NOT inherit a Soong static lib's transitive shared_libs, so the
    objects libtar drags out of libvold.a (Decrypt.o -> VolumeManager.o,
    Checkpoint.o) have undefined externals at libtar.so link time:
      android::hal::BootControlClient::WaitForService()  -> libboot_control_client
      NetlinkEvent::dump() / NetlinkEvent::findParam()    -> libsysutils
      async_safe_format_log                               -> libasync_safe (static)
    All three have recovery variants (libboot_control_client + libasync_safe are
    recovery_available:true; libsysutils is force-built for recovery via TWRP's
    TWRP_REQUIRED_MODULES). Fix: add them to libtar/Android.mk's FBE block.

Idempotent and loud: every edit asserts its expected occurrence count and aborts
on upstream drift so CI surfaces it instead of silently building broken.
"""
import sys, os

WS = sys.argv[1] if len(sys.argv) > 1 else "."
LT = os.path.join(WS, "bootable/recovery/libtar")
HDR = os.path.join(LT, "libtar.h")
BLK = os.path.join(LT, "block.c")
APP = os.path.join(LT, "append.c")
EXT = os.path.join(LT, "extract.c")
MK  = os.path.join(LT, "Android.mk")
SHIM = os.path.join(LT, "fscrypt_compat.h")

SHIM_CONTENT = r'''/*
 * fscrypt_compat.h - v2-only shim for TWRP libtar against android-14.1 vold.
 *
 * android-14.1 system/vold removed the old `union fscrypt_policy` helpers
 * (get_policy, fscrypt_policy_size, get_policy_size, get_policy_descriptor,
 * get_policy_content) that libtar still calls. This device is FBE v2
 * (USE_FSCRYPT_POLICY_V2), so provide those helpers as static-inline functions
 * operating directly on `struct fscrypt_policy_v2`. Logic ported verbatim from
 * android-12.1 vold's V2 branches. Included by libtar.h after fscrypt_policy.h.
 */
#ifndef TWRP_LIBTAR_FSCRYPT_COMPAT_H
#define TWRP_LIBTAR_FSCRYPT_COMPAT_H

#ifdef USE_FSCRYPT
#include <stdio.h>
#include <stdint.h>
#include <linux/fs.h>   /* struct fscrypt_policy_v2, FSCRYPT_KEY_IDENTIFIER_SIZE */

#ifndef FSCRYPT_KEY_IDENTIFIER_HEX_SIZE
#define FSCRYPT_KEY_IDENTIFIER_HEX_SIZE ((2 * FSCRYPT_KEY_IDENTIFIER_SIZE) + 1)
#endif

#ifdef __cplusplus
extern "C" {
#endif

static inline uint8_t *get_policy_descriptor(struct fscrypt_policy_v2 *fep) {
	return fep ? fep->master_key_identifier : (uint8_t *)0;
}

static inline uint8_t get_policy_size(struct fscrypt_policy_v2 *fep, bool hex) {
	(void)fep;
	return hex ? (uint8_t)FSCRYPT_KEY_IDENTIFIER_HEX_SIZE
	           : (uint8_t)FSCRYPT_KEY_IDENTIFIER_SIZE;
}

static inline void *get_policy(const struct fscrypt_policy_v2 *fep) {
	return (void *)fep;
}

static inline int fscrypt_policy_size(const struct fscrypt_policy_v2 *fep) {
	(void)fep;
	return (int)sizeof(struct fscrypt_policy_v2);
}

static inline void get_policy_content(struct fscrypt_policy_v2 *fep, char *content) {
	if (!fep || !content) return;
	sprintf(content, "%i %i %i %i %s", (int)fep->version,
		(int)fep->contents_encryption_mode,
		(int)fep->filenames_encryption_mode,
		(int)fep->flags,
		fep->master_key_identifier);
}

#ifdef __cplusplus
}
#endif

#endif /* USE_FSCRYPT */
#endif /* TWRP_LIBTAR_FSCRYPT_COMPAT_H */
'''

# (file, old, new, expected_count)
EDITS = [
    # --- (A) compile shim ---
    (HDR,
     "#ifdef USE_FSCRYPT\n#include \"fscrypt_policy.h\"\n#endif",
     "#ifdef USE_FSCRYPT\n#include \"fscrypt_policy.h\"\n#include \"fscrypt_compat.h\"\n#endif", 1),
    (HDR,
     "\tfscrypt_policy  *fep;",
     "\tstruct fscrypt_policy_v2  *fep;", 1),
    (BLK,
     "t->th_buf.fep = (fscrypt_policy*)malloc(sizeof(fscrypt_policy));",
     "t->th_buf.fep = (struct fscrypt_policy_v2*)malloc(sizeof(struct fscrypt_policy_v2));", 1),
    (APP,
     "t->th_buf.fep = (fscrypt_policy *)malloc(sizeof(fscrypt_policy));",
     "t->th_buf.fep = (struct fscrypt_policy_v2 *)malloc(sizeof(struct fscrypt_policy_v2));", 1),
    (EXT,
     "if (!lookup_ref_tar(t->th_buf.fep, &binary_policy[0])) {",
     "if (!lookup_ref_tar(descriptor, &binary_policy[0])) {", 1),

    # --- (B) link deps: add the libs that provide libvold.a's dragged externals ---
    (MK,
     "    LOCAL_STATIC_LIBRARIES += libvold libscrypt_static\n",
     "    LOCAL_STATIC_LIBRARIES += libvold libscrypt_static libasync_safe\n", 1),
    (MK,
     "        libchrome \\\n        libbootloader_message \\\n        libgatekeeper_aidl\n",
     "        libchrome \\\n        libbootloader_message \\\n        libgatekeeper_aidl \\\n        libsysutils \\\n        libboot_control_client\n", 1),
]

for f in (HDR, BLK, APP, EXT, MK):
    if not os.path.isfile(f):
        sys.exit(f"::error::missing source file: {f}")

def read(f):
    with open(f, "r", encoding="utf-8", errors="surrogateescape") as fh:
        return fh.read()

def write(f, txt):
    with open(f, "w", encoding="utf-8", errors="surrogateescape") as fh:
        fh.write(txt)

# --- shim ---
if os.path.isfile(SHIM) and read(SHIM) == SHIM_CONTENT:
    print("fscrypt_compat.h already present")
else:
    write(SHIM, SHIM_CONTENT)
    print("wrote libtar/fscrypt_compat.h")

# --- edits ---
bufs = {}
for f in (HDR, BLK, APP, EXT, MK):
    bufs.setdefault(f, read(f))

for f, old, new, want in EDITS:
    txt = bufs[f]
    if new in txt and old not in txt:
        continue  # already applied
    n = txt.count(old)
    if n != want:
        sys.exit(f"::error::{os.path.basename(f)}: expected {want} occurrence(s) of "
                 f"<<{old}>> but found {n} (upstream drift)")
    bufs[f] = txt.replace(old, new)

for f, txt in bufs.items():
    write(f, txt)

# --- structural verification (cannot link here; runner does the real build) ---
errs = []
h = read(HDR)
if "struct fscrypt_policy_v2  *fep;" not in h:
    errs.append("libtar.h: fep not retyped to fscrypt_policy_v2")
if '#include "fscrypt_compat.h"' not in h:
    errs.append("libtar.h: fscrypt_compat.h not included")
for f in (BLK, APP):
    t = read(f)
    if "(fscrypt_policy*)" in t or "(fscrypt_policy *)" in t:
        errs.append(f"{os.path.basename(f)}: bare fscrypt_policy malloc cast remains")
if "lookup_ref_tar(t->th_buf.fep" in read(EXT):
    errs.append("extract.c: lookup_ref_tar still passed fep instead of descriptor")
mk = read(MK)
for lib in ("libasync_safe", "libsysutils", "libboot_control_client"):
    if lib not in mk:
        errs.append(f"Android.mk: missing link dep {lib}")
for sym in ("get_policy_descriptor", "get_policy_size", "get_policy", "fscrypt_policy_size"):
    if sym not in read(SHIM):
        errs.append(f"fscrypt_compat.h: missing {sym}")

if errs:
    print("::error::libtar fscrypt v2 patch incomplete:")
    for e in errs:
        print("  " + e)
    sys.exit(1)

print("libtar fscrypt v2 + link-deps patch applied cleanly")
