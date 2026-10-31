import * as Linking from "expo-linking";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { parseConnect } from "../lib/api";
import { connect, getHub, loadConnection } from "../lib/store";
import { C } from "../lib/theme";

export default function RootLayout() {
  // hizashi://connect?hub=…&house=… (or the same query on a web preview) connects straight away.
  const url = Linking.useLinkingURL();
  useEffect(() => {
    loadConnection().then(() => {
      const c = url ? parseConnect(url) : null;
      const cur = getHub().conn;
      if (c && (c.hub !== cur?.hub || c.house !== cur?.house)) connect(c);
    });
  }, [url]);
  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: C.bg } }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="connect" />
        <Stack.Screen name="onboarding" options={{ gestureEnabled: false }} />
        <Stack.Screen name="(tabs)" />
      </Stack>
    </SafeAreaProvider>
  );
}
