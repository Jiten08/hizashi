// Start-up gate: no saved street -> Connect; house not set up -> Onboarding; else the app.
import { Redirect } from "expo-router";
import { ActivityIndicator, Text, View } from "react-native";
import { Button } from "../components/ui";
import { disconnect, useHub } from "../lib/store";
import { C, T } from "../lib/theme";

export default function Index() {
  const hub = useHub();
  if (!hub.ready) return null;
  if (!hub.conn) return <Redirect href="/connect" />;
  const info = hub.houses[hub.conn.house];
  if (!hub.loaded || !info) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", padding: 32, gap: 12, backgroundColor: C.bg }}>
        {hub.failures < 3 ? <ActivityIndicator /> : null}
        <Text style={[T.title3, { textAlign: "center" }]}>{hub.failures < 3 ? "Reaching your street…" : "Can't reach your street"}</Text>
        <Text style={[T.subhead, { textAlign: "center" }]}>{hub.conn.hub}</Text>
        {hub.failures >= 3 ? (
          <Text style={[T.footnote, { textAlign: "center" }]}>
            {hub.conn.hub.startsWith("https://")
              ? "Check that ngrok is still running on the laptop (ngrok http 8000) and the hub is started."
              : "This address only works on the laptop's Wi-Fi. On another network, use ngrok and scan the new code."}
            {hub.lastError ? ` (${hub.lastError})` : ""} Still trying every couple of seconds.
          </Text>
        ) : null}
        <Button title="Scan a different code" kind="tinted" style={{ marginTop: 8, alignSelf: "stretch" }} onPress={disconnect} />
      </View>
    );
  }
  if (!info.onboarded) return <Redirect href="/onboarding" />;
  return <Redirect href="/today" />;
}
