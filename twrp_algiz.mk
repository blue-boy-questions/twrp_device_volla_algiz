#
# twrp_algiz.mk — TWRP product makefile for Volla Phone Quintus (algiz)
#

# Inherit from the common TWRP config.
$(call inherit-product, $(SRC_TARGET_DIR)/product/base.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)

# Inherit the device-specific definitions.
$(call inherit-product, device/volla/algiz/device.mk)

# Inherit TWRP common.
$(call inherit-product-if-exists, vendor/twrp/config/common.mk)

PRODUCT_DEVICE := algiz
PRODUCT_NAME := twrp_algiz
PRODUCT_BRAND := volla
PRODUCT_MODEL := Volla Phone Quintus
PRODUCT_MANUFACTURER := volla

PRODUCT_GMS_CLIENTID_BASE := android-volla

# Fingerprint matches stock so OTA/AVB expectations line up during testing.
PRODUCT_BUILD_PROP_OVERRIDES += \
    BuildFingerprint=volla/algiz/algiz:16/BP4A.251205.006/30-volla-16.0:user/release-keys \
    DeviceName=algiz \
    DeviceProduct=algiz
