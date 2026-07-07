import * as Haptics from "expo-haptics";

// 촉각 피드백. 화면을 못 보는 사용자에게 상태 변화를 진동으로도 알린다.
// (expo-haptics 는 Expo Go 에서 그대로 동작. 웹에서는 no-op)

// 버튼 눌림 — 짧은 탁.
export function tapFeedback(): void {
  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
}

// 성공 — 설명 도착.
export function successFeedback(): void {
  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(
    () => {}
  );
}

// 실패 — 오류.
export function errorFeedback(): void {
  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(
    () => {}
  );
}
