import { Ionicons } from "@expo/vector-icons";
import { Redirect, Tabs } from "expo-router";
import { useHub } from "../../lib/store";
import { C } from "../../lib/theme";

export default function TabLayout() {
  const hub = useHub();
  if (hub.ready && !hub.conn) return <Redirect href="/connect" />;
  const house = hub.conn?.house;
  const pending = hub.approvals.filter((a) => a.house === house && a.status === "pending").length;
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarActiveTintColor: C.orange,
      tabBarInactiveTintColor: "#8E8E93",
      tabBarStyle: { backgroundColor: "rgba(249,249,249,0.97)", borderTopColor: C.sep },
      tabBarLabelStyle: { fontSize: 10, fontWeight: "500" },
    }}>
      <Tabs.Screen name="today" options={{ title: "Today", tabBarIcon: ({ color, focused }) => <Ionicons name={focused ? "sunny" : "sunny-outline"} size={25} color={color as string} /> }} />
      <Tabs.Screen name="approvals" options={{
        title: "Approvals", tabBarBadge: pending || undefined, tabBarBadgeStyle: { backgroundColor: C.red, fontSize: 11 },
        tabBarIcon: ({ color, focused }) => <Ionicons name={focused ? "checkmark-circle" : "checkmark-circle-outline"} size={25} color={color as string} />,
      }} />
      <Tabs.Screen name="rules" options={{ title: "Rules", tabBarIcon: ({ color, focused }) => <Ionicons name={focused ? "options" : "options-outline"} size={25} color={color as string} /> }} />
      <Tabs.Screen name="history" options={{ title: "History", tabBarIcon: ({ color, focused }) => <Ionicons name={focused ? "time" : "time-outline"} size={25} color={color as string} /> }} />
    </Tabs>
  );
}
