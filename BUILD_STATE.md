# BUILD_STATE — TWRP algiz (vendor_boot) CI build

**Status:** IN_PROGRESS
**Goal:** `.github/workflows/build-twrp.yml` green on GitHub Actions AND
`out/target/product/algiz/vendor_boot.img` produced + validated (section 4 of the brief).
**Driver:** Hermes Agent (no local clone; build only on the GitHub runner).

---

## Current attempt
- **Attempt:** 1 (first Hermes-driven real fix)
- **Latest run id:** _pending — triggering after this commit_
- **Branch:** main

## Latest commit / change summary
- Fix the libtar FBE-crypto compile error (the real failure) + make the
  workflow report the build's TRUE status.
- New committed patch script `patches/fix_libtar_fscrypt_v2.py` (run by the
  workflow against the synced tree).
- Workflow `Build` step: read `PIPESTATUS[0]` immediately (previously
  clobbered → false green), fail on non-zero `mka`, and assert
  `vendor_boot.img` actually exists.

## Latest REAL build error (run 37521292124, the last "green" one)
It was a **false green**: `mka vendorbootimage` actually FAILED at 78% but the
job reported success because `PIPESTATUS` was read after other commands. The
only artifact was `build-tail.log` (no image). Real error:

```
bootable/recovery/libtar/libtar.h:74:2: error: must use 'struct' tag to refer to type 'fscrypt_policy_v1'
block.c / append.c: calls to undeclared get_policy / fscrypt_policy_size /
  get_policy_size / get_policy_descriptor; incompatible fscrypt_policy_v1 vs _v2 pointers
11 errors → ninja: build stopped → "failed to build some targets"
```

## Root cause (confirmed, not guessed)
TWRP's `bootable/recovery/libtar` targets the OLD vold crypto API
(`union fscrypt_policy` typedef + `get_policy*()` helpers). The TeamWin
`android-14.1` `system/vold` DROPPED all of that and exposes only the
v1/v2-overloaded `fscrypt_policy_get_struct()` / `lookup_ref_key()`
(selected by `-DUSE_FSCRYPT_POLICY_V1/_V2`). So libtar no longer compiles.

## Fix applied
This device is FBE **v2** (`BoardConfig: TW_USE_FSCRYPT_POLICY := 2`). Made
libtar **v2-only** so it matches vold's v2 overloads exactly:
- `th_buf.fep` → `struct fscrypt_policy_v2 *`
- `get_policy(fep)` → `(void*)fep`
- `fscrypt_policy_size(fep)` → `sizeof(struct fscrypt_policy_v2)`
- `get_policy_size(fep,false|true)` → `FSCRYPT_KEY_IDENTIFIER_SIZE` (16) /
  `FSCRYPT_KEY_IDENTIFIER_HEX_SIZE` (33)
- `get_policy_descriptor(fep)` → `fep->master_key_identifier`
- `get_policy_content(fep,buf)` → `snprintf` of `fep->version`
Patch validated locally against the real `android-14.1` libtar sources:
applies cleanly, idempotent, aborts loudly on upstream drift.
Note: v2-only means FBE-v1 backup restore isn't cross-compatible — irrelevant
for this v2 device.

## Hypotheses already tried that did NOT work (never repeat)
- H1 (commit d3ffa3ad / earlier): patch `libtar.h` with sed to retype `fep`
  as `fscrypt_policy_v2 *` and rename `get_policy_size`/`get_policy_descriptor`
  → `get_policy_v2_*`. FAILED: those `*_v2_*` helpers do NOT exist in
  android-14.1 vold either, and `block.c` (`get_policy`, `fscrypt_policy_size`,
  `get_policy_content`) was never touched → still 11 errors. The sed was also
  silently matching nothing. Superseded by the committed Python patch that
  edits libtar.h **and** block.c **and** append.c with occurrence counts.

## Exact next step
1. (done this commit) land fix + state.
2. Trigger `gh workflow run build-twrp.yml` (defaults:
   manifest_branch=twrp-14.1, build_target=vendorbootimage,
   lunch_combo=twrp_algiz-ap2a-eng). Record run id here.
3. Poll ~every 90s. On failure: `gh run view <id> --log-failed`, find root
   cause, smallest fix, commit, re-trigger. On success: run section-4
   validation, then mark DONE.

## Validation checklist (section 4) — run after a green build
1. `vendor_boot.img` exists, size plausible (stock was ~ tens of MB).
2. header v4; two fragments: `platform` (stock) + `recovery` (TWRP).
3. stock kernel + dtb intact.
4. recovery fragment: TWRP binary, fstab matching `stock_recovery.fstab.ref`, init rc.
5. AVB signed algorithm NONE.
6. report `sha256sum`.
