#
# BoardConfig.mk — Volla Phone Quintus (algiz)
# MediaTek MT6877 (Dimensity 7050) · Android 16 · GKI 2.0 · A/B + Virtual A/B
#
# Key architectural facts (verified from stock images):
#   - boot.img        : header v4, kernel only (gzip, 14,554,925 B), ramdisk_size=0
#   - init_boot.img   : header v4, ramdisk only (gzip)
#   - vendor_boot.img : header v4, page 4096, carries TWO ramdisk fragments —
#                         type=platform  (8.8 MB)  and  type=recovery (17.9 MB).
#     => recovery is NOT a standalone partition; it is the recovery fragment
#        inside vendor_boot. We rebuild that fragment as TWRP.
#   - Load addresses (from vendor_boot header):
#        kernel  0x40080000   ramdisk 0x51100000   tags/dtb 0x47c80000
#   - super (dynamic) : system/system_ext/vendor/product/*_dlkm, erofs+ext4
#   - /data           : f2fs, FBE v2 (aes-256-xts) + metadata encryption
#

DEVICE_PATH := device/volla/algiz

# ------------------------------------------------------------------ Platform
TARGET_BOARD_PLATFORM := mt6877
TARGET_BOARD_PLATFORM_GPU := mali-g68

# ---------------------------------------------------------------- Architecture
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-2a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_VARIANT := cortex-a78
TARGET_CPU_VARIANT_RUNTIME := cortex-a78

TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv8-2a
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := cortex-a55
TARGET_2ND_CPU_VARIANT_RUNTIME := cortex-a55

TARGET_USES_64_BIT_BINDER := true

# -------------------------------------------------------------------- Bootloader
TARGET_NO_BOOTLOADER := true
TARGET_USES_UEFI := true

# ------------------------------------------------------------------------ Kernel
# We reuse the STOCK GKI kernel — no kernel source build for recovery.
BOARD_PREBUILT_DTBOIMAGE := $(DEVICE_PATH)/prebuilt/dtbo.img
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/kernel.gz
BOARD_INCLUDE_DTB_IN_BOOTIMG := false

BOARD_KERNEL_CMDLINE := bootopt=64S3,32N2,64N2 androidboot.serialconsole=0
BOARD_KERNEL_BASE := 0x40000000
BOARD_KERNEL_PAGESIZE := 4096
BOARD_KERNEL_OFFSET := 0x00080000
BOARD_RAMDISK_OFFSET := 0x11100000
BOARD_KERNEL_TAGS_OFFSET := 0x07c80000
BOARD_DTB_OFFSET := 0x07c80000

BOARD_MKBOOTIMG_ARGS += --header_version 4
BOARD_MKBOOTIMG_ARGS += --kernel_offset $(BOARD_KERNEL_OFFSET)
BOARD_MKBOOTIMG_ARGS += --ramdisk_offset $(BOARD_RAMDISK_OFFSET)
BOARD_MKBOOTIMG_ARGS += --tags_offset $(BOARD_KERNEL_TAGS_OFFSET)
BOARD_MKBOOTIMG_ARGS += --dtb_offset $(BOARD_DTB_OFFSET)
BOARD_MKBOOTIMG_ARGS += --pagesize $(BOARD_KERNEL_PAGESIZE)

# -------------------------------------------------------- Boot image geometry
# boot partition = 40 MiB (0x2800000). Kernel-only, ramdisk_size must stay 0.
BOARD_BOOTIMAGE_PARTITION_SIZE := 41943040
# init_boot = 8 MiB. We DO NOT touch it (ramdisk only; root lives here).
BOARD_INIT_BOOT_IMAGE_PARTITION_SIZE := 8388608
# vendor_boot = 64 MiB. THIS is where our recovery fragment ships.
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := 67108864

# ------------------------------------------------------ GKI / ramdisk topology
BOARD_USES_RECOVERY_AS_BOOT := false
BOARD_MOVE_RECOVERY_RESOURCES_TO_VENDOR_BOOT := true
BOARD_USES_GENERIC_KERNEL_IMAGE := true

# Two ramdisk fragments: the stock platform one, plus our recovery one.
BOARD_BOOT_HEADER_VERSION := 4
BOARD_VENDOR_RAMDISK_FRAGMENTS := recovery
BOARD_VENDOR_BOOT_HEADER_VERSION := 4
# Put TWRP's ramdisk into the "recovery" vendor ramdisk fragment.
BOARD_INCLUDE_RECOVERY_RAMDISK_IN_VENDOR_BOOT := true
BOARD_VENDOR_RAMDISK_FRAGMENT.recovery.KERNEL_MODULE_DIRS :=

# init_boot carries the generic ramdisk on A16; keep it out of our build scope.
BOARD_USES_GENERIC_KERNEL_IMAGE := true
BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := true

# --------------------------------------------------------------- Partitions / AVB
BOARD_SUPER_PARTITION_GROUPS := mt6877_dynamic_partitions
# Dynamic partition members (verified from fstab).
BOARD_MT6877_DYNAMIC_PARTITIONS_PARTITION_LIST := \
    system system_ext vendor product vendor_dlkm odm_dlkm system_dlkm

# Super partition geometry. The build system requires the group *_SIZE to be
# non-empty even for TWRP (which does not populate the logical partitions).
# Values are sized from the stock super.img (raw 5,683,488,968 B). Virtual A/B
# uses snapshots rather than a doubled super, so the group max is the super size
# minus the standard 4 MiB metadata/alignment overhead. Refined from the real
# on-device super block size if it differs.
BOARD_SUPER_PARTITION_SIZE := 9663676416
BOARD_MT6877_DYNAMIC_PARTITIONS_SIZE := 9659482112
BOARD_SUPER_PARTITION_METADATA_DEVICE := super

TARGET_USES_MKE2FS := true
BOARD_USES_METADATA_PARTITION := true

# Treble (stock prop ro.treble.enabled=true; silences the config.mk warning).
PRODUCT_FULL_TREBLE_OVERRIDE := true
BOARD_VNDK_VERSION := current

# A/B
AB_OTA_UPDATER := true
ENABLE_VIRTUAL_AB := true

# AVB — recovery/vendor_boot repack is signed with algorithm NONE (no OEM key).
# Flashing TWRP implies an unlocked bootloader; vbmeta must be flashed with
# --disable-verity --disable-verification (documented in flash notes).
BOARD_AVB_ENABLE := true
BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS += --flags 3
BOARD_AVB_VBMETA_SYSTEM := system system_ext product
BOARD_AVB_VBMETA_SYSTEM_KEY_PATH := external/avb/test/data/testkey_rsa2048.pem
BOARD_AVB_VBMETA_SYSTEM_ALGORITHM := SHA256_RSA2048
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX := $(PLATFORM_SECURITY_PATCH_TIMESTAMP)
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX_LOCATION := 2

# ----------------------------------------------------------------- Filesystems
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true
BOARD_HAS_LARGE_FILESYSTEM := true

# ------------------------------------------------------------- Recovery / TWRP
TARGET_RECOVERY_PIXEL_FORMAT := "RGBX_8888"
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery/root/system/etc/recovery.fstab
TARGET_USES_MKE2FS := true

# Screen: 1080x2400 AMOLED, density 477 (from ro.sf.lcd_density).
TW_THEME := portrait_hdpi
TW_SCREEN_BLANK_ON_BOOT := true
TW_INPUT_BLACKLIST := "hbtp_vm"
TW_EXTRA_LANGUAGES := true
TW_DEFAULT_LANGUAGE := en

# Encryption — FBE v2 + metadata (keydirectory=/metadata/vold/metadata_encryption)
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_INCLUDE_FBE_METADATA_DECRYPT := true
BOARD_USES_METADATA_PARTITION := true
PLATFORM_SECURITY_PATCH := 2026-08-01
PLATFORM_VERSION := 16
TW_DEFAULT_LANGUAGE := en
TARGET_RECOVERY_DENSITY := xxhdpi

# A/B + system-as-root helpers
TW_INCLUDE_REPACKTOOLS := true
TW_INCLUDE_RESETPROP := true
TW_USE_TOOLBOX := true
TW_EXCLUDE_APEX := false

# No separate /recovery or /boot ramdisk UI; brightness path for the AMOLED panel
TW_MAX_BRIGHTNESS := 2047
TW_DEFAULT_BRIGHTNESS := 1024
TW_BRIGHTNESS_PATH := "/sys/class/leds/lcd-backlight/brightness"

# USB gadget identity (from stock recovery props)
TW_OZIP_DECRYPT_SIZE := 16

# ----------------------------------------------------------------- Misc
BOARD_SUPPRESS_SECURE_ERASE := true
TARGET_USES_LOGD := true
TW_EXCLUDE_DEFAULT_USB_INIT := true
TW_HAS_DOWNLOAD_MODE := false
