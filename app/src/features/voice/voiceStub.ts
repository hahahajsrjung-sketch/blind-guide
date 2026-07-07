// 음성 출력 모듈.
//
// 시각장애인 앱이라 설명을 소리로 들려주는 게 핵심이다. expo-speech(기기 내장
// TTS)로 한국어 낭독한다. 안경/카메라 없이 폰만으로 동작한다.
//
// 나중 확장 지점: 안경 스피커로 출력, 음성 속도/톤을 프로필에 맞춰 조절.
import * as Speech from "expo-speech";

// 낭독. 진행 중인 낭독이 있으면 멈추고 새로 읽는다.
export function speak(text: string): void {
  if (!text) return;
  Speech.stop();
  Speech.speak(text, { language: "ko-KR" });
}

// 낭독 중지.
export function stopSpeaking(): void {
  Speech.stop();
}

// 현재 낭독 중인지.
export function isSpeaking(): Promise<boolean> {
  return Speech.isSpeakingAsync();
}
