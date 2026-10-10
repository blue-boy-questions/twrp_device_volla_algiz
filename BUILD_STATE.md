# BUILD_STATE — TWRP algiz (vendor_boot) CI build

**Status:** IN_PROGRESS
**Goal:** `.github/workflows/build-twrp.yml` green on GitHub Actions AND
`out/target/product/algiz/vendor_boot.img` produced + validated (section 4 of the brief).
**Driver:** Hermes Agent (no local clone; build only on the GitHub runner).

---

## Current attempt
- **Attempt:** 3
- **Latest run id:** _pending — triggering after this commit_ (prev: 38035738536 FAILED at libtar.so LINK)
- **Branch:** main

## Latest commit / change summary
- Attempt 3: the compile shim worked; now fix the libtar.so **LINK** stage.
  libtar.so (a Make module) links the Soong static lib libvold.a but Make
  modules don't inherit a Soong static lib's transitive shared_libs, so three
  externals dragged out of libvold.a were undefined at link:
  BootControlClient::WaitForService (libboot_control_client), NetlinkEvent::
  dump/findParam (libsysutils), async_safe_format_log (libasync_safe).
- `patches/fix_libtar_fscrypt_v2.py` now also edits `libtar/Android.mk`:
  adds `libasync_safe` (static) and `libsysutils` + `libboot_control_client`
  (shared) to the TW_INCLUDE_CRYPTO_FBE block. All three have recovery variants.

## Latest REAL build error (run 38035738536 — attempt 2)
Attempt-2 shim fixed the COMPILE; libtar.so then failed to LINK:
```
ld.lld: error: undefined symbol: android::hal::BootControlClient::WaitForService()
ld.lld: error: undefined symbol: NetlinkEvent::dump()
ld.lld: error: undefined symbol: NetlinkEvent::findParam(char const*)
ld.lld: error: undefined symbol: async_safe_format_log
clang++: error: linker command failed → ninja: build stopped
```
These are externals of objects libtar drags out of libvold.a (Decrypt.o →
VolumeManager.o, Checkpoint.o). See attempt-3 fix above.

## Earlier REAL build error (run 38025818062 — attempt 1)
Attempt-1 patch (edit block.c + append.c inline) was INCOMPLETE: it missed
`extract.c` and `output.c`, which call the same removed helpers. Build failed
again at libtar/extract.c:

```
extract.c:561 error: call to undeclared function 'get_policy_size'
extract.c:563 error: call to undeclared function 'get_policy_descriptor'
extract.c:573 error: incompatible pointer types passing
  'struct fscrypt_policy_v2 *' to 'const uint8_t *' (lookup_ref_tar signature changed)
4 errors → ninja: build stopped
```
Note: the workflow correctly reported this as FAILURE now (no more false green).

## Root cause (confirmed, not guessed)
TWRP's `bootable/recovery/libtar` targets the OLD vold crypto API
(`union fscrypt_policy` typedef + `get_policy*()` helpers) across FIVE files:
libtar.h, block.c, append.c, extract.c, output.c. TeamWin `android-14.1`
`system/vold` DROPPED all of that; it exposes only v1/v2-overloaded
`fscrypt_policy_get_struct()`, `fscrypt_policy_set_struct()`, `lookup_ref_key()`,
and a `lookup_ref_tar()` whose signature CHANGED to take descriptor bytes
(`const uint8_t*`) instead of the policy struct. bionic also `#define
fscrypt_policy fscrypt_policy_v1`, so the bare name can't be a type.

## Fix applied (attempt 2 — the shim)
Device is FBE **v2** (`BoardConfig: TW_USE_FSCRYPT_POLICY := 2`).
- New `libtar/fscrypt_compat.h`: static-inline v2 implementations of
  `get_policy`, `fscrypt_policy_size`, `get_policy_size`,
  `get_policy_descriptor`, `get_policy_content` taking
  `struct fscrypt_policy_v2 *` (ported from android-12.1 vold v2 branches).
- `libtar.h`: `th_buf.fep` → `struct fscrypt_policy_v2 *`; include the shim.
- `block.c` / `append.c`: retype the two bare-`fscrypt_policy` mallocs to v2.
- `extract.c`: `lookup_ref_tar(t->th_buf.fep,…)` → `lookup_ref_tar(descriptor,…)`.
- Everything else (output.c LOG, lookup_ref_key, get/set_struct) resolves once
  fep is v2 + shim in scope — no edits needed.
Patch is idempotent, aborts loudly on upstream drift, and structurally
self-verifies after applying.

## Hypotheses already tried that did NOT work (never repeat)
- **H1** (pre-Hermes, commit d3ffa3ad): sed `libtar.h` to retype fep and rename
  helpers → `get_policy_v2_*`. FAILED: those `*_v2_*` helpers don't exist in
  android-14.1 vold; block.c untouched; sed matched nothing. 11 errors.
- **H2** (attempt 1, run 38025818062, commit 23460c6b): inline-edit only
  block.c + append.c to v2 constants. FAILED: `extract.c` and `output.c` use
  the SAME removed helpers and were untouched → extract.c 4 errors. Lesson:
  the fscrypt call sites span 5 files, not 2 — a shim header beats per-line edits.
- **H3** (attempt 2, run 38035738536, commit 8d67467f): shim header fixed the
  COMPILE but libtar.so failed to LINK — undefined BootControlClient::
  WaitForService / NetlinkEvent::dump+findParam / async_safe_format_log.
  Lesson: libtar is a Make module linking the Soong libvold.a; it does NOT
  inherit libvold's transitive shared_libs, so every external that the pulled
  libvold objects reference must be listed explicitly in libtar/Android.mk.
  Fixed in attempt 3 by adding libasync_safe/libsysutils/libboot_control_client.

## Exact next step
1. (done this commit) land the shim fix + state.
2. Trigger `gh workflow run build-twrp.yml -R <R> --ref main` (defaults).
   Record run id here.
3. Poll ~every 90s. On failure: `gh run view <id> --log-failed`, inspect
   build-tail.log, find root cause, smallest fix, commit, re-trigger. On
   success: `gh run download`, run `validate_vendor_boot.py`, then mark DONE.

## Validation checklist (section 4) — run after a green build
1. `vendor_boot.img` exists, size plausible.
2. header v4; two fragments: `platform` (stock) + `recovery` (TWRP).
3. stock kernel + dtb intact.
4. recovery fragment: TWRP binary, fstab matching `stock_recovery.fstab.ref`, init rc.
5. AVB signed algorithm NONE.
6. report `sha256sum`.
