import { StatusBar } from "expo-status-bar";
import { SafeAreaView, StyleSheet } from "react-native";

import MainScreen from "./src/screens/MainScreen";

// 앱 루트. 이번 단계에서는 화면 하나(MainScreen)만 띄운다.
export default function App() {
  return (
    <SafeAreaView style={styles.root}>
      <StatusBar style="light" />
      <MainScreen />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#000000",
  },
});
