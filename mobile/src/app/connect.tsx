// Connect this phone to a house: scan the code on the street dashboard, or type the hub address.
import { CameraView, useCameraPermissions } from "expo-camera";
import { Redirect, router } from "expo-router";
import { useRef, useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { Button, Section, Segmented } from "../components/ui";
import { parseConnect } from "../lib/api";
import { connect, useHub } from "../lib/store";
import { C, T } from "../lib/theme";
import type { House } from "../lib/types";

export default function Connect() {
  const insets = useSafeAreaInsets();
  const [permission, requestPermission] = useCameraPermissions();
  const [scanning, setScanning] = useState(false);
  const [hub, setHub] = useState("");
  const [house, setHouse] = useState<House>("h12");
  const [error, setError] = useState<string | null>(null);
  const done = useRef(false);
  const linked = useHub().conn;
  if (linked && !scanning) return <Redirect href="/" />;

  const go = async (c: { hub: string; house: House }) => {
    if (done.current) return;
    done.current = true;
    await connect(c);
    router.replace("/");
  };

  if (scanning) {
    return (
      <View style={{ flex: 1, backgroundColor: "#000" }}>
        <CameraView style={StyleSheet.absoluteFill} barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
          onBarcodeScanned={({ data }) => {
            const c = parseConnect(data);
            if (c) go(c); else setError("That code isn't a Hizashi street code.");
          }} />
        <View style={[styles.scanFrame]} pointerEvents="none" />
        <View style={{ position: "absolute", top: insets.top + 12, left: 16, right: 16, flexDirection: "row", justifyContent: "space-between" }}>
          <Pressable onPress={() => setScanning(false)} style={styles.close}><Ionicons name="close" size={22} color="#fff" /></Pressable>
        </View>
        <Text style={[T.headline, styles.scanHint, { bottom: insets.bottom + 48 }]}>
          {error ?? "Point at the house code on the street dashboard"}
        </Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={{ flex: 1, backgroundColor: C.bg, paddingTop: insets.top + 40, paddingHorizontal: 16 }}>
      <View style={{ alignItems: "center" }}>
        <View style={styles.logo}><Ionicons name="sunny" size={44} color="#fff" /></View>
        <Text style={[T.largeTitle, { marginTop: 18, textAlign: "center" }]}>Hizashi</Text>
        <Text style={[T.subhead, { textAlign: "center", marginTop: 6, paddingHorizontal: 12 }]}>
          Your home's energy agent. Sells spare rooftop power to neighbours, inside limits you set.
        </Text>
      </View>

      <Button title="Scan house code" icon="qr-code-outline" style={{ marginTop: 36 }}
        onPress={async () => {
          setError(null);
          if (!permission?.granted) {
            const p = await requestPermission();
            if (!p.granted) { setError("Camera access is off. Type the address below instead."); return; }
          }
          setScanning(true);
        }} />
      {error ? <Text style={[T.footnote, { color: C.red, textAlign: "center", marginTop: 8 }]}>{error}</Text> : null}

      <Section header="Or enter it" footer="The address is on the street dashboard, e.g. https://abcd.ngrok-free.app">
        <TextInput value={hub} onChangeText={setHub} placeholder="https://…" autoCapitalize="none" autoCorrect={false}
          keyboardType="url" placeholderTextColor={C.label3}
          style={[T.body, { paddingHorizontal: 16, height: 46 }]} />
        <View style={{ padding: 12, paddingTop: 0 }}>
          <Segmented value={house} onChange={setHouse}
            options={(["h12", "h14", "h16", "h18"] as House[]).map((h) => ({ value: h, label: `House ${h.slice(1)}` }))} />
        </View>
      </Section>
      <Button title="Connect" kind="tinted" style={{ marginTop: 16 }} disabled={!/^https?:\/\/.+/.test(hub.trim())}
        onPress={() => go({ hub: hub.trim().replace(/\/+$/, ""), house })} />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  logo: { width: 84, height: 84, borderRadius: 20, backgroundColor: C.orange, alignItems: "center", justifyContent: "center",
    shadowColor: C.orange, shadowOpacity: 0.35, shadowRadius: 14, shadowOffset: { width: 0, height: 6 } },
  scanFrame: { position: "absolute", alignSelf: "center", top: "28%", width: 250, height: 250, borderRadius: 28, borderWidth: 3, borderColor: "rgba(255,255,255,0.9)" },
  scanHint: { position: "absolute", left: 24, right: 24, color: "#fff", textAlign: "center" },
  close: { width: 36, height: 36, borderRadius: 18, backgroundColor: "rgba(0,0,0,0.5)", alignItems: "center", justifyContent: "center" },
});
