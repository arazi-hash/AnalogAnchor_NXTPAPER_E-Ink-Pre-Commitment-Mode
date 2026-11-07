package com.analoganchor.nxtpaperguard

/** Local permission to use one observed binding; never a global model claim. */
data class DeviceQualification(
    val bindingDigest: String,
    val controllerDigest: String,
    val ownerConfirmedNativeInk: Boolean
) {
    fun matches(binding: String, controller: String): Boolean =
        ownerConfirmedNativeInk && validDigest(bindingDigest) && validDigest(controllerDigest) &&
            bindingDigest == binding && controllerDigest == controller

    companion object {
        fun validDigest(value: String): Boolean = value.matches(Regex("[0-9a-f]{64}"))

        fun canComplete(trialPassed: Boolean, normalConfirmed: Boolean, physicalNormal: Boolean,
                        ownerConfirmed: Boolean): Boolean =
            trialPassed && normalConfirmed && physicalNormal && ownerConfirmed
    }
}
