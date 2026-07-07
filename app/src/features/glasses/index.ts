import { GLASSES_PROVIDER } from "../../config";
import { MetaWearablesProvider } from "./metaWearablesProvider";
import { MockGlassesProvider } from "./mockGlassesProvider";
import { GlassesProvider } from "./types";

export * from "./types";

// 설정(EXPO_PUBLIC_GLASSES_PROVIDER)에 따라 안경 제공자를 하나 고른다.
// 기본은 mock (하드웨어 없이 동작). "meta" 로 두면 실제 안경(dev build 필요).
let provider: GlassesProvider | null = null;

export function getGlassesProvider(): GlassesProvider {
  if (provider) return provider;
  provider =
    GLASSES_PROVIDER === "meta"
      ? new MetaWearablesProvider()
      : new MockGlassesProvider();
  return provider;
}
