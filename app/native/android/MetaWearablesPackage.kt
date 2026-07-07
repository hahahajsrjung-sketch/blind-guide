package com.blindguide.app.metawearables

// RN 이 이 네이티브 모듈을 인식하도록 등록하는 ReactPackage.
//
// dev build 에서 android 프로젝트에 이 두 .kt 파일을 넣고, MainApplication 의
// getPackages() 에 add(MetaWearablesPackage()) 를 추가한다.
// (config plugin 으로 자동 등록하려면 withMainApplication mod 로 문자열 주입.
//  템플릿 버전차가 있어 이번엔 수동 등록을 기본으로 안내한다 — SETUP.md 3단계.)

import com.facebook.react.ReactPackage
import com.facebook.react.bridge.NativeModule
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.uimanager.ViewManager

class MetaWearablesPackage : ReactPackage {
    override fun createNativeModules(
        reactContext: ReactApplicationContext
    ): List<NativeModule> = listOf(MetaWearablesModule(reactContext))

    override fun createViewManagers(
        reactContext: ReactApplicationContext
    ): List<ViewManager<*, *>> = emptyList()
}
