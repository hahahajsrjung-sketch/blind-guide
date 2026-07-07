package com.blindguide.app.metawearables

// ─────────────────────────────────────────────────────────────────────────────
// Meta Wearables 네이티브 모듈 — 레퍼런스 구현.
//
// JS(src/features/glasses/metaWearablesProvider.ts)가 기대하는 NativeModule 이름:
//   "MetaWearables"
// 메서드: initialize / startRegistration / getState / capturePhoto / stop
//
// 이 파일은 문서(v0.8.0)의 세션·스트림 API 기반 "레퍼런스"다. 실제 SDK 타입/시그니처
// 는 도입 시점 버전에 맞춰 조정한다. 특히 아래 [TODO] 표시 부분은 Activity 수명주기와
// 얽혀 있어(권한 요청 런처 등) 첫 dev build 때 실물로 검증해야 한다.
//
// 출처: https://wearables.developer.meta.com/docs/build-integration-android/
// ─────────────────────────────────────────────────────────────────────────────

import android.util.Base64
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

// 아래 import 는 실제 SDK 패키지에 맞춰 조정한다 (v0.8.0 기준 예시).
// import com.meta.wearable.mwdat.core.Wearables
// import com.meta.wearable.mwdat.core.AutoDeviceSelector
// import com.meta.wearable.mwdat.camera.StreamConfiguration
// import com.meta.wearable.mwdat.camera.VideoQuality

class MetaWearablesModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    private val scope = CoroutineScope(Dispatchers.Main)

    // JS 에서 NativeModules.MetaWearables 로 잡히는 이름.
    override fun getName(): String = "MetaWearables"

    @ReactMethod
    fun initialize(promise: Promise) {
        try {
            // Wearables.initialize(reactApplicationContext)
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("INIT_FAILED", e.message, e)
        }
    }

    @ReactMethod
    fun startRegistration(promise: Promise) {
        try {
            val activity = currentActivity
                ?: return promise.reject("NO_ACTIVITY", "현재 Activity 가 없습니다.")
            // Wearables.startRegistration(activity)
            // [TODO] registrationState 를 관찰해 완료 시점을 알 수 있으면 그때 resolve.
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("REGISTER_FAILED", e.message, e)
        }
    }

    @ReactMethod
    fun getState(promise: Promise) {
        try {
            // [TODO] Wearables.registrationState / 세션 상태를 아래 문자열 중 하나로 매핑:
            //   "unregistered" | "registering" | "registered" | "sessionActive" | "error"
            promise.resolve("unregistered")
        } catch (e: Exception) {
            promise.reject("STATE_FAILED", e.message, e)
        }
    }

    @ReactMethod
    fun capturePhoto(promise: Promise) {
        scope.launch {
            try {
                // 문서 흐름:
                //   val session = Wearables.createSession(AutoDeviceSelector()).getOrElse { ... }
                //   session.start()
                //   val config = StreamConfiguration(VideoQuality.MEDIUM, frameRate = 24)
                //   val stream = session.addStream(config).getOrThrow()
                //   stream.start()
                //   val photo = stream.capturePhoto().getOrThrow()   // PhotoData
                //
                // PhotoData 의 바이트를 base64 data URI 로 변환해 JS 로 넘긴다.
                // (backend recognition 은 data URI / http URL 을 실제 인식)
                //
                // [TODO] 카메라 권한(Wearables.checkPermissionStatus/RequestPermissionContract)은
                //        Activity/Fragment 의 ActivityResult 런처가 필요하다. 권한 화면은
                //        네이티브 Activity 에서 처리하고, 여기서는 권한이 있다고 가정한다.
                val bytes: ByteArray = ByteArray(0) // = photo.bytes  (실제 값으로 교체)
                val b64 = Base64.encodeToString(bytes, Base64.NO_WRAP)
                val dataUri = "data:image/jpeg;base64,$b64"
                promise.resolve(dataUri)
            } catch (e: Exception) {
                promise.reject("CAPTURE_FAILED", e.message, e)
            }
        }
    }

    @ReactMethod
    fun stop(promise: Promise) {
        try {
            // stream.stop()/close(); 세션 종료
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("STOP_FAILED", e.message, e)
        }
    }
}
