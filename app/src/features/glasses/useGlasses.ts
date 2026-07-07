import { useCallback, useEffect, useState } from "react";

import { getGlassesProvider } from "./index";
import { GlassesConnectionState } from "./types";

// 안경 연결 상태를 다루는 훅.
// 화면은 이 훅만 쓰면 되고, mock/meta 제공자 차이는 신경 쓰지 않는다.
export function useGlasses() {
  const provider = getGlassesProvider();
  const [state, setState] = useState<GlassesConnectionState>("unregistered");
  const [busy, setBusy] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const refresh = useCallback(async () => {
    try {
      setState(await provider.getState());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setState("error");
    }
  }, [provider]);

  // 앱 시작 시 1회 초기화 + 상태 조회.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        await provider.initialize();
        if (alive) await refresh();
      } catch (e) {
        if (alive) {
          setError(e instanceof Error ? e.message : String(e));
          setState("error");
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, [provider, refresh]);

  // 폰↔안경 등록(페어링) 진입.
  const connect = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      await provider.startRegistration();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setState("error");
    } finally {
      setBusy(false);
    }
  }, [provider, refresh]);

  const connected = state === "registered" || state === "sessionActive";

  return {
    providerName: provider.name,
    state,
    connected,
    busy,
    error,
    connect,
    refresh,
  };
}
