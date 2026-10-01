# twrp_device_volla_algiz

TWRP / TeamWin Recovery **device tree** for the **Volla Phone Quintus**
(codename `algiz`).

| | |
|---|---|
| SoC | MediaTek **Dimensity 7050** (MT6877TT), `ro.board.platform=mt6877` |
| Android | **16** (Volla OS 16 / DariaOS 6, LineageOS-based) |
| Partitioning | **A/B + Virtual A/B**, dynamic partitions (`super`) |
| Boot layout | GKI 2.0: `boot`=kernel-only, `init_boot`=generic ramdisk, `vendor_boot`=platform **+ recovery** ramdisk fragments |
| Screen | 1080×2400 AMOLED, density 477, 120 Hz |
| `/data` | f2fs, FBE v2 (`aes-256-xts`) + metadata encryption |

## The important architectural fact

This device has **no standalone `recovery` partition**. Recovery ships as a
**ramdisk fragment of type `recovery` inside `vendor_boot`** (verified: the
stock `vendor_boot.img` carries two fragments, `platform` 8.8 MB and
`recovery` 17.9 MB). The GKI `boot.img` is kernel-only.

Consequences for building and flashing:

- The build target is **`mka vendorbootimage`**, not `recoveryimage`.
- We **reuse the stock GKI kernel** (`prebuilt/kernel.gz`) — no kernel source
  build is required for recovery.
- `init_boot` (where KernelSU/Magisk LKM root lives) is **never touched** by
  this tree.

## Building

Uses the TWRP minimal manifest, branch **`twrp-14.1`** (closest match to the
device's Android 16 recovery semantics). See
[`.github/workflows/build-twrp.yml`](.github/workflows/build-twrp.yml) — it runs
entirely on a GitHub Actions runner (the maintainer's build host has a tight
disk quota).

```bash
repo init --depth=1 -u https://github.com/minimal-manifest-twrp/platform_manifest_twrp_aosp.git -b twrp-14.1
# clone this tree to device/volla/algiz, then:
export ALLOW_MISSING_DEPENDENCIES=true
source build/envsetup.sh
lunch twrp_algiz-eng
mka vendorbootimage
```

Output: `out/target/product/algiz/vendor_boot.img` (TWRP as the recovery
fragment, stock platform fragment + stock kernel preserved).

## Flashing (non-destructive test first)

> Flashing a custom recovery requires an **unlocked bootloader**. All commands
> run on your **Windows** PC (PowerShell — use `;` not `&&`).

**1. Non-destructive boot test (nothing is written):**

```powershell
fastboot boot twrp-vendor_boot.img
```

If the device does not support `fastboot boot` of a vendor_boot image, flash to
the inactive slot and test there before committing.

**2. Permanent install:**

```powershell
fastboot flash vendor_boot twrp-vendor_boot.img
fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img
fastboot reboot recovery
```

The repacked image is signed with AVB algorithm **NONE** (re-signing needs
Volla's private key, which is not public), so `vbmeta` must be flashed with
verity/verification disabled.

**Recovery path:** keep the stock `vendor_boot.img`
(md5 `32adf911d8c2e206dc389019b1007573`) — `fastboot flash vendor_boot
stock-vendor_boot.img` restores stock recovery.

## Provenance

Stock images extracted from
[zahedan-vollaos-rom-porter `stable-20260828`](https://github.com/sajjad85gh/zahedan-vollaos-rom-porter/releases/tag/stable-20260828)
(DariaOS 6). All verified facts are recorded in
[`device-facts.json`](device-facts.json).
