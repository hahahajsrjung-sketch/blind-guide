import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { requestDescription } from "../api/describeClient";
import { captureImage } from "../features/camera/cameraStub";
import {
  errorFeedback,
  successFeedback,
  tapFeedback,
} from "../features/feedback/haptics";
import { GlassesConnectionState } from "../features/glasses/types";
import { useGlasses } from "../features/glasses/useGlasses";
import { speak, stopSpeaking } from "../features/voice/voiceStub";
import { DEMO_ARTWORK_ID, DEMO_USERS } from "../profile/currentProfile";
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

// 시각장애인 우선 화면.
// 원칙: ① 초대형 버튼(화면 하단 엄지 존) ② 모든 상태 변화를 음성+진동으로
//       ③ 초고대비(순검정/순백 + 인디고 포인트) ④ 큰 글자.
export default function MainScreen() {
  const [userIndex, setUserIndex] = useState<number>(0);
  const [status, setStatus] = useState<Status>("idle");
  const [description, setDescription] = useState<string>("");
  const [error, setError] = useState<string>("");

  const glasses = useGlasses();
  const selected = DEMO_USERS[userIndex];

  // 로딩 중 버튼이 숨 쉬듯 커졌다 작아지는 펄스.
  const pulse = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    if (status !== "loading") {
      pulse.setValue(1);
      return;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1.05,
          duration: 600,
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 1,
          duration: 600,
          useNativeDriver: true,
        }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [status, pulse]);

  async function onPressDescribe() {
    stopSpeaking();
    tapFeedback(); // 눌림을 진동으로 확인
    setStatus("loading");
    setError("");
    setDescription("");
    speak("설명을 가져오는 중입니다"); // 화면을 못 봐도 진행 상황을 알게

    try {
      const image = await captureImage();
      const body: DescribeRequest = {
        user_id: selected.profile.user_id,
        image,
        artwork_id: DEMO_ARTWORK_ID,
      };

      const res = await requestDescription(body);
      setDescription(res.description);
      setStatus("done");
      successFeedback();
      speak(res.description);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setStatus("error");
      errorFeedback();
      speak(`오류가 났습니다. ${msg}`);
    }
  }

  function onSelectUser(i: number) {
    stopSpeaking();
    tapFeedback();
    setUserIndex(i);
    speak(`${DEMO_USERS[i].label} 사용자로 바꿨습니다`);
  }

  const isLoading = status === "loading";

  return (
    <View style={styles.container}>
      {/* ── 상단: 타이틀 + 안경 상태 ── */}
      <View style={styles.topBar}>
        <Text style={styles.title}>눈앞 설명</Text>
        <View
          style={[
            styles.glassesChip,
            glasses.connected && styles.glassesChipOn,
          ]}
          accessibilityLabel={`안경 상태: ${GLASSES_STATE_LABEL[glasses.state]}`}
        >
          <Text style={styles.glassesChipText}>
            👓 {GLASSES_STATE_LABEL[glasses.state]}
            {glasses.providerName === "mock" ? "·모의" : ""}
          </Text>
        </View>
      </View>

      {!glasses.connected && (
        <Pressable
          onPress={glasses.connect}
          disabled={glasses.busy}
          style={styles.connectBtn}
          accessibilityRole="button"
          accessibilityLabel="안경 연결"
        >
          <Text style={styles.connectBtnText}>
            {glasses.busy ? "연결 중…" : "안경 연결하기"}
          </Text>
        </Pressable>
      )}

      {/* ── 중단: 결과 영역 (큰 글자) ── */}
      <ScrollView
        style={styles.resultBox}
        contentContainerStyle={styles.resultContent}
      >
        {status === "idle" && (
          <Text style={styles.hint}>
            아래 큰 버튼을 누르면{"\n"}눈앞을 설명해 드립니다
          </Text>
        )}
        {isLoading && (
          <View style={styles.loadingWrap}>
            <ActivityIndicator size="large" color="#a29bfe" />
            <Text style={styles.loadingText}>설명 가져오는 중…</Text>
          </View>
        )}
        {status === "done" && (
          <Text style={styles.resultText}>{description}</Text>
        )}
        {status === "error" && <Text style={styles.errorText}>{error}</Text>}
      </ScrollView>

      {/* ── 음성 컨트롤 (설명 있을 때) ── */}
      {status === "done" && (
        <View style={styles.voiceRow}>
          <Pressable
            onPress={() => {
              tapFeedback();
              speak(description);
            }}
            style={styles.voiceBtn}
            accessibilityRole="button"
            accessibilityLabel="다시 듣기"
          >
            <Text style={styles.voiceBtnText}>🔊 다시 듣기</Text>
          </Pressable>
          <Pressable
            onPress={() => {
              tapFeedback();
              stopSpeaking();
            }}
            style={styles.voiceBtn}
            accessibilityRole="button"
            accessibilityLabel="멈춤"
          >
            <Text style={styles.voiceBtnText}>■ 멈춤</Text>
          </Pressable>
        </View>
      )}

      {/* ── 하단: 사용자 토글 + 초대형 캡처 버튼 (엄지 존) ── */}
      <View style={styles.bottomZone}>
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
                accessibilityLabel={`${u.label} 사용자${active ? ", 선택됨" : ""}`}
              >
                <Text
                  style={[styles.chipText, active && styles.chipTextActive]}
                >
                  {u.label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Animated.View style={{ transform: [{ scale: pulse }] }}>
          <Pressable
            onPress={onPressDescribe}
            disabled={isLoading}
            style={({ pressed }) => [
              styles.bigButton,
              isLoading && styles.bigButtonLoading,
              pressed && styles.bigButtonPressed,
            ]}
            accessibilityRole="button"
            accessibilityLabel="눈앞을 설명해줘"
            accessibilityHint="누르면 안경 카메라로 눈앞을 촬영해 설명을 들려줍니다"
          >
            <Text style={styles.bigButtonText}>
              {isLoading ? "듣는 중…" : "눈앞을\n설명해줘"}
            </Text>
          </Pressable>
        </Animated.View>
      </View>
    </View>
  );
}

// SightSpace 톤: 순검정 배경 + 인디고(#6c5ce7) 포인트 + 순백 텍스트 (초고대비)
const INDIGO = "#6c5ce7";
const INDIGO_DIM = "#4a3fb5";

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000000",
    paddingHorizontal: 20,
    paddingTop: 16,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  title: {
    color: "#ffffff",
    fontSize: 26,
    fontWeight: "800",
    letterSpacing: -0.5,
  },
  glassesChip: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 999,
    backgroundColor: "#161616",
    borderWidth: 1,
    borderColor: "#333333",
  },
  glassesChipOn: {
    borderColor: INDIGO,
  },
  glassesChipText: {
    color: "#dddddd",
    fontSize: 14,
    fontWeight: "600",
  },
  connectBtn: {
    marginTop: 12,
    backgroundColor: "#161616",
    borderWidth: 1,
    borderColor: INDIGO,
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: "center",
  },
  connectBtnText: {
    color: "#ffffff",
    fontSize: 18,
    fontWeight: "700",
  },
  resultBox: {
    flex: 1,
    marginTop: 16,
    backgroundColor: "#0d0d0d",
    borderRadius: 20,
    padding: 20,
  },
  resultContent: {
    flexGrow: 1,
    justifyContent: "center",
  },
  hint: {
    color: "#8a8a8a",
    fontSize: 20,
    lineHeight: 30,
    textAlign: "center",
  },
  loadingWrap: {
    alignItems: "center",
    gap: 14,
  },
  loadingText: {
    color: "#a29bfe",
    fontSize: 18,
    fontWeight: "600",
  },
  resultText: {
    color: "#ffffff",
    fontSize: 22,
    lineHeight: 34,
    fontWeight: "500",
  },
  errorText: {
    color: "#ff7675",
    fontSize: 18,
    lineHeight: 27,
  },
  voiceRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 12,
  },
  voiceBtn: {
    flex: 1,
    backgroundColor: "#161616",
    borderWidth: 1,
    borderColor: "#3a3a3a",
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: "center",
  },
  voiceBtnText: {
    color: "#ffffff",
    fontSize: 17,
    fontWeight: "700",
  },
  bottomZone: {
    paddingTop: 14,
    paddingBottom: 10,
  },
  userRow: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 14,
  },
  chip: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#3a3a3a",
    backgroundColor: "#111111",
    alignItems: "center",
  },
  chipActive: {
    backgroundColor: INDIGO,
    borderColor: INDIGO,
  },
  chipText: {
    color: "#bbbbbb",
    fontSize: 17,
    fontWeight: "700",
  },
  chipTextActive: {
    color: "#ffffff",
  },
  bigButton: {
    backgroundColor: INDIGO,
    borderRadius: 28,
    minHeight: 150, // 화면 하단을 크게 차지하는 엄지 존 버튼
    alignItems: "center",
    justifyContent: "center",
  },
  bigButtonLoading: {
    backgroundColor: INDIGO_DIM,
  },
  bigButtonPressed: {
    opacity: 0.85,
  },
  bigButtonText: {
    color: "#ffffff",
    fontSize: 30,
    lineHeight: 40,
    fontWeight: "800",
    textAlign: "center",
    letterSpacing: -0.5,
  },
});
