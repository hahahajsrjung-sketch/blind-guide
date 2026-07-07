import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { requestDescription } from "../api/describeClient";
import { captureImage } from "../features/camera/cameraStub";
import { useGlasses } from "../features/glasses/useGlasses";
import { GlassesConnectionState } from "../features/glasses/types";
import { speak, stopSpeaking } from "../features/voice/voiceStub";
import {
  DEMO_ARTWORK_ID,
  DEMO_USERS,
} from "../profile/currentProfile";
import { DescribeRequest } from "../types";

type Status = "idle" | "loading" | "done" | "error";

// 안경 상태를 한국어로.
const GLASSES_STATE_LABEL: Record<GlassesConnectionState, string> = {
  unregistered: "연결 안 됨",
  registering: "연결 중…",
  registered: "연결됨",
  sessionActive: "카메라 준비됨",
  error: "오류",
};

// 이번 뼈대의 화면 하나: 프로필 토글 + 버튼 + 결과 표시 영역.
// [사용자 선택] → [버튼 탭] → 가짜 image → POST /describe → 설명을 글자로 표시.
// 사용자를 바꿔 누르면 시각 상태(onset)에 따라 설명이 다르게 오는 걸 확인한다.
export default function MainScreen() {
  const [userIndex, setUserIndex] = useState<number>(0);
  const [status, setStatus] = useState<Status>("idle");
  const [description, setDescription] = useState<string>("");
  const [error, setError] = useState<string>("");

  const glasses = useGlasses();
  const selected = DEMO_USERS[userIndex];

  async function onPressDescribe() {
    stopSpeaking(); // 이전 낭독 중지
    setStatus("loading");
    setError("");
    setDescription("");

    try {
      const image = await captureImage(); // 지금은 가짜 placeholder
      const body: DescribeRequest = {
        user_id: selected.profile.user_id,
        image,
        artwork_id: DEMO_ARTWORK_ID,
      };

      const res = await requestDescription(body);
      setDescription(res.description);
      setStatus("done");
      speak(res.description); // 받은 설명을 소리로 읽어준다
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setStatus("error");
      speak(msg); // 오류도 소리로 안내 (화면을 못 보는 사용자 배려)
    }
  }

  function onSelectUser(i: number) {
    stopSpeaking();
    setUserIndex(i);
  }

  const isLoading = status === "loading";

  return (
    <View style={styles.container}>
      <Text style={styles.title}>눈앞 설명 듣기</Text>

      {/* 안경 연결 상태. mock 모드에서는 자동 연결, meta 모드면 실제 페어링 */}
      <View style={styles.glassesRow}>
        <Text style={styles.glassesStatus} accessibilityLabel={`안경 상태: ${GLASSES_STATE_LABEL[glasses.state]}`}>
          안경: {GLASSES_STATE_LABEL[glasses.state]}
          {glasses.providerName === "mock" ? " (모의)" : ""}
        </Text>
        {!glasses.connected && (
          <Pressable
            onPress={glasses.connect}
            disabled={glasses.busy}
            style={styles.glassesBtn}
            accessibilityRole="button"
            accessibilityLabel="안경 연결"
          >
            <Text style={styles.glassesBtnText}>
              {glasses.busy ? "연결 중…" : "안경 연결"}
            </Text>
          </Pressable>
        )}
      </View>

      {/* 데모 사용자(시각 상태) 선택 — 바꿔 누르면 설명이 달라지는지 확인 */}
      <Text style={styles.sectionLabel}>사용자(시각 상태)</Text>
      <View style={styles.userRow}>
        {DEMO_USERS.map((u, i) => {
          const active = i === userIndex;
          return (
            <Pressable
              key={u.profile.user_id}
              onPress={() => onSelectUser(i)}
              disabled={isLoading}
              style={[styles.chip, active && styles.chipActive]}
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
              accessibilityLabel={`${u.label} 사용자`}
            >
              <Text style={[styles.chipText, active && styles.chipTextActive]}>
                {u.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Pressable
        onPress={onPressDescribe}
        disabled={isLoading}
        style={({ pressed }) => [
          styles.button,
          isLoading && styles.buttonDisabled,
          pressed && styles.buttonPressed,
        ]}
        accessibilityRole="button"
        accessibilityLabel="눈앞을 설명해줘"
      >
        <Text style={styles.buttonText}>
          {isLoading ? "설명 받는 중…" : "눈앞을 설명해줘"}
        </Text>
      </Pressable>

      <ScrollView
        style={styles.resultBox}
        contentContainerStyle={styles.resultContent}
      >
        {status === "idle" && (
          <Text style={styles.hint}>버튼을 누르면 설명이 여기 표시됩니다.</Text>
        )}
        {isLoading && <ActivityIndicator size="large" color="#ffffff" />}
        {status === "done" && (
          <Text style={styles.resultText}>{description}</Text>
        )}
        {status === "error" && <Text style={styles.errorText}>{error}</Text>}
      </ScrollView>

      {status === "done" && (
        <View style={styles.voiceRow}>
          <Pressable
            onPress={() => speak(description)}
            style={styles.voiceBtn}
            accessibilityRole="button"
            accessibilityLabel="다시 듣기"
          >
            <Text style={styles.voiceBtnText}>🔊 다시 듣기</Text>
          </Pressable>
          <Pressable
            onPress={stopSpeaking}
            style={styles.voiceBtn}
            accessibilityRole="button"
            accessibilityLabel="멈춤"
          >
            <Text style={styles.voiceBtnText}>■ 멈춤</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000000",
    paddingHorizontal: 20,
    paddingTop: 24,
  },
  title: {
    color: "#ffffff",
    fontSize: 26,
    fontWeight: "700",
  },
  glassesRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 12,
    paddingVertical: 10,
    paddingHorizontal: 14,
    backgroundColor: "#141414",
    borderRadius: 12,
  },
  glassesStatus: {
    color: "#cccccc",
    fontSize: 15,
    fontWeight: "600",
    flexShrink: 1,
  },
  glassesBtn: {
    backgroundColor: "#2a2a2a",
    borderRadius: 999,
    paddingVertical: 8,
    paddingHorizontal: 16,
    marginLeft: 10,
  },
  glassesBtnText: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "700",
  },
  sectionLabel: {
    color: "#9a9a9a",
    fontSize: 14,
    marginTop: 20,
    marginBottom: 8,
  },
  userRow: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 20,
  },
  chip: {
    paddingVertical: 12,
    paddingHorizontal: 18,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#3a3a3a",
    backgroundColor: "#151515",
  },
  chipActive: {
    backgroundColor: "#1e6fff",
    borderColor: "#1e6fff",
  },
  chipText: {
    color: "#bbbbbb",
    fontSize: 16,
    fontWeight: "600",
  },
  chipTextActive: {
    color: "#ffffff",
  },
  button: {
    backgroundColor: "#1e6fff",
    borderRadius: 16,
    paddingVertical: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  buttonDisabled: {
    backgroundColor: "#324a7a",
  },
  buttonPressed: {
    opacity: 0.85,
  },
  buttonText: {
    color: "#ffffff",
    fontSize: 20,
    fontWeight: "700",
  },
  resultBox: {
    flex: 1,
    marginTop: 20,
    marginBottom: 24,
    backgroundColor: "#111111",
    borderRadius: 16,
    padding: 18,
  },
  resultContent: {
    flexGrow: 1,
    justifyContent: "center",
  },
  hint: {
    color: "#6a6a6a",
    fontSize: 16,
    textAlign: "center",
  },
  resultText: {
    color: "#ffffff",
    fontSize: 20,
    lineHeight: 30,
  },
  errorText: {
    color: "#ff6b6b",
    fontSize: 16,
    lineHeight: 24,
  },
  voiceRow: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 24,
  },
  voiceBtn: {
    flex: 1,
    backgroundColor: "#1b1b1b",
    borderWidth: 1,
    borderColor: "#3a3a3a",
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  voiceBtnText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "600",
  },
});
