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
        <ActivityIndicator />
        <Text style={T.headline}>Reaching your street…</Text>
        <Text style={[T.subhead, { textAlign: "center" }]}>{hub.conn.hub}</Text>
        <Button title="Use a different code" kind="plain" onPress={disconnect} />
      </View>
    );
  }
  if (!info.onboarded) return <Redirect href="/onboarding" />;
  return <Redirect href="/today" />;
}
