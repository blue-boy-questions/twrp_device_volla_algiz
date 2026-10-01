#
# device.mk — Volla Phone Quintus (algiz) TWRP
#

LOCAL_PATH := device/volla/algiz

# A/B OTA (recovery is part of boot/vendor_boot, not standalone)
AB_OTA_UPDATER := true
AB_OTA_PARTITIONS += boot init_boot vendor_boot dtbo vbmeta vbmeta_system vbmeta_vendor

# Dynamic / Virtual A/B
PRODUCT_USE_DYNAMIC_PARTITIONS := true
PRODUCT_VIRTUAL_AB_OTA := true
PRODUCT_VIRTUAL_AB_COMPRESSION := true

# Recovery resources that must live in the vendor_boot recovery fragment.
PRODUCT_PACKAGES += \
    android.hardware.health@2.1-impl-cuttlefish \
    update_engine_sideload

# Soong namespaces (kept empty here; the TWRP tree supplies them)
PRODUCT_SOONG_NAMESPACES += $(LOCAL_PATH)

# Device identity
PRODUCT_DEVICE := algiz
PRODUCT_NAME := twrp_algiz
PRODUCT_BRAND := volla
PRODUCT_MODEL := Volla Phone Quintus
PRODUCT_MANUFACTURER := volla

# fastboot / recovery USB identity (from stock recovery props)
PRODUCT_PROPERTY_OVERRIDES += \
    ro.product.first_api_level=31 \
    ro.recovery.usb.vid=18D1 \
    ro.recovery.usb.adb.pid=D001 \
    ro.recovery.usb.fastboot.pid=4EE0
