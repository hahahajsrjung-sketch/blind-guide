import { getGlassesProvider } from "../glasses";

// 백엔드로 보낼 이미지를 한 장 얻는다.
//
// 이미지 소스는 안경(웨어러블) 카메라다. 실제 소스는 features/glasses 의
// 제공자(mock 또는 Meta 안경)가 담당하고, 여기서는 그걸 불러 이미지 문자열만
// 꺼낸다. 설정(EXPO_PUBLIC_GLASSES_PROVIDER)에 따라 소스가 바뀌어도 화면 코드는
// 안 바뀐다.
//
// (나중에 폰 자체 카메라(expo-camera)를 대체 소스로 붙일 수도 있다. 그때도
//  같은 captureImage() 뒤로 숨긴다.)
export async function captureImage(): Promise<string> {
  const captured = await getGlassesProvider().captureImage();
  return captured.image;
}
