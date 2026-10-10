# BUILD_STATE — TWRP algiz (vendor_boot) CI build

**Status:** IN_PROGRESS
**Goal:** `.github/workflows/build-twrp.yml` green on GitHub Actions AND
`out/target/product/algiz/vendor_boot.img` produced + validated (section 4 of the brief).
**Driver:** Hermes Agent (no local clone; build only on the GitHub runner).

---

## Current attempt
- **Attempt:** 6
- **Latest run id:** _pending — triggering after this commit_ (prev: 38051300116 FAILED at 85% = NEW real build error: deprecated FDE identifiers in partition.cpp/partitionmanager.cpp)
- **Branch:** main

## Latest REAL failure (run 38051300116 — attempt 5): deprecated FDE identifiers (real build, FIXED attempt 6)
Attempt-5 disk/dpkg fixes WORKED: deps installed, repo synced, libtar fscrypt
v2 patch applied, and the build ran ~60 min to 85% — past the whole libtar
compile+link saga and well past the attempt-3 ENOSPC point. New, deeper error
in `recovery` itself at ninja 85%:
```
FAILED: .../recovery_intermediates/partition.o
bootable/recovery/partition.cpp:711:5: error: use of undeclared identifier 'set_partition_data'
partition.cpp:712:9: error: use of undeclared identifier 'cryptfs_check_footer'
partition.cpp:718/719: error: use of undeclared identifier 'cryptfs_get_password_type'
partition.cpp:2163: error: use of undeclared identifier 'delete_crypto_blk_dev'
FAILED: .../recovery_intermediates/partitionmanager.o
partitionmanager.cpp:635:24: error: use of undeclared identifier 'cryptfs_get_password_type'
partitionmanager.cpp:2187:13: error: use of undeclared identifier 'cryptfs_check_passwd'
ninja: build stopped: subcommand failed.
```
Root cause (confirmed, not guessed): TWRP `android-14.1` partition.cpp +
partitionmanager.cpp still call the old **FDE** (Full Disk Encryption) API —
set_partition_data, cryptfs_check_footer, cryptfs_get_password_type,
cryptfs_check_passwd, delete_crypto_blk_dev. android-14.1 `system/vold`
cryptfs.h declares NONE of them (verified: it declares only
cryptfs_setup_ext_volume + cryptfs_get_keygen). FDE was dropped industry-wide
at Android 10 (AOSP vold commit 0803ba0 "Remove most of FDE support"). Any
FBE-only device building with TW_INCLUDE_CRYPTO hits this. These branches are
already runtime-dead on FBE devices (guarded by TW_IS_FBE, always true here).

## Fix applied (attempt 6)
Apply TWRP upstream Gerrit change 8744 verbatim via a new committed, idempotent
patch script `patches/fix_fde_removal.py` (run from the workflow right after the
libtar patch). It removes the 5 dead FDE blocks across 2 files:
- partition.cpp: footer-based FDE detection in the Key_Directory-empty branch
  (now falls through to the existing "could not find crypto footer" gui_err);
  the delete_crypto_blk_dev cleanup in the wipe path.
- partitionmanager.cpp: the "FBE setup failed, trying FDE" fallback branch; the
  fork()/cryptfs_check_passwd() password path in Decrypt_Device() + its
  now-unreachable success tail.
Script stores old/new blocks base64 (byte-exact vs current upstream), applies
each exactly once, is idempotent (skips if already applied), aborts loudly on
upstream drift (occurrence-count != 1), and asserts no FDE symbol remains.
Verified locally against the real android-14.1 blobs: python-apply == `git apply`
of the Gerrit patch; a full-tree grep of the android-14.1 recovery source
confirms these 5 symbols appear in ONLY these 2 files (no other call sites).

## Earlier REAL failure (run 38043204749 — attempt 3): runner ENOSPC (infra, not code)
The libtar LINK fix compiled AND linked; the build ran 34 min into image
assembly, then the GitHub runner itself crashed:
```
Unhandled exception. System.IO.IOException: No space left on device :
  '/home/runner/actions-runner/.../Worker_...log'
```
Disk timeline (from attempt 2's logs; one /dev/root fs for everything):
after cleanup 115G free → after repo sync + 24G swapfile only 9.7G free (94%)
→ out/ ate the rest. Fix = attempt-4 disk budget (see above). This is the
"runner out of disk" infrastructure class, but it was recurring deterministically
so it needed a config change, not a blind rerun.

## Earlier REAL build error (run 38035738536 — attempt 2)
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
- **H4** (attempt 3, run 38043204749, commit e9ee0b36): the libtar fix was
  CORRECT (compiled + linked); the build died from runner ENOSPC during image
  assembly, not code. Don't "fix" code for this — it's a disk-budget problem.
  Addressed in attempt 4 by freeing more runner disk and shrinking swap 24G→16G.
- **H5** (attempt 4, run 38048277769, commit bf3a436e): freed disk by `rm -rf`
  of toolchain dirs AND `apt-get purge` of the same toolchains' packages. The
  purge's dpkg maintainer scripts failed on the already-deleted files, leaving
  dpkg half-broken, so the next step's `apt-get install` of build deps died
  with exit 100 (google-cloud-cli). Lesson: free space with `rm -rf` of the
  self-contained toolchain DIRECTORIES only; never apt-purge a package whose
  files you already rm'd. Fixed in attempt 5 (rm only, no purge/autoremove).
- **H6** (attempt 5, run 38051300116, commit TBD): disk/dpkg fixes worked and
  the build reached 85%, but `recovery` failed to compile — partition.cpp /
  partitionmanager.cpp call the removed FDE API. NOT a libtar problem (that was
  already fixed); a separate upstream/vold divergence. Fixed in attempt 6 by
  removing the dead FDE codepaths (Gerrit 8744) via fix_fde_removal.py.

## Exact next step
1. (done this commit) land fix_fde_removal.py + wire it into the workflow after
   the libtar patch step + update this state.
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
