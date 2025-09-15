import { StatusBar } from "expo-status-bar";
import React, { useState } from "react";
import { Button, SafeAreaView, StyleSheet, Text, TextInput, View } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

function LoginScreen({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  return (
    <SafeAreaView style={styles.centered}>
      <Text style={styles.title}>Action-Reaction</Text>
      <View style={styles.formGroup}>
        <Text>Email</Text>
        <TextInput style={styles.input} value={email} onChangeText={setEmail} autoCapitalize="none" />
      </View>
      <View style={styles.formGroup}>
        <Text>Password</Text>
        <TextInput style={styles.input} value={password} onChangeText={setPassword} secureTextEntry />
      </View>
      <Button title="Continue" onPress={onLogin} />
      <Text style={styles.muted}>Mock login. Any credentials work.</Text>
    </SafeAreaView>
  );
}

function DashboardScreen() {
  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>Dashboard</Text>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Save Gmail invoices to Drive</Text>
        <Text style={styles.muted}>When: Gmail - New Email w/ 'Invoice'</Text>
        <Text style={styles.muted}>Then: Drive - Upload Attachment</Text>
        <View style={{ height: 8 }} />
        <Button title="Create AREA" onPress={() => {}} />
      </View>
    </SafeAreaView>
  );
}

function ConnectionsScreen() {
  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>Service Connection Hub</Text>
      {["Google Drive", "Gmail", "Slack", "GitHub"].map((s) => (
        <View key={s} style={styles.rowBetween}>
          <Text>{s}</Text>
          <Button title="Connect" onPress={() => {}} />
        </View>
      ))}
    </SafeAreaView>
  );
}

function WizardScreen() {
  const [step, setStep] = useState(1);
  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>AREA Creation Wizard</Text>
      <Text style={styles.muted}>Step {step} of 5</Text>
      <View style={{ height: 12 }} />
      <Button title="Next" onPress={() => setStep(Math.min(step + 1, 5))} />
    </SafeAreaView>
  );
}

function AccountScreen() {
  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>Account</Text>
      <View style={styles.formGroup}>
        <Text>Name</Text>
        <TextInput style={styles.input} defaultValue="Jane Doe" />
      </View>
      <View style={styles.formGroup}>
        <Text>Email</Text>
        <TextInput style={styles.input} defaultValue="jane@example.com" />
      </View>
      <Button title="Save" onPress={() => {}} />
    </SafeAreaView>
  );
}

const Stack = createNativeStackNavigator();
const Tabs = createBottomTabNavigator();

function TabsNavigator() {
  return (
    <Tabs.Navigator>
      <Tabs.Screen name="Dashboard" component={DashboardScreen} />
      <Tabs.Screen name="Connections" component={ConnectionsScreen} />
      <Tabs.Screen name="Wizard" component={WizardScreen} />
      <Tabs.Screen name="Account" component={AccountScreen} />
    </Tabs.Navigator>
  );
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {loggedIn ? (
          <Stack.Screen name="Main" component={TabsNavigator} />
        ) : (
          <Stack.Screen name="Login">
            {() => <LoginScreen onLogin={() => setLoggedIn(true)} />}
          </Stack.Screen>
        )}
      </Stack.Navigator>
      <StatusBar style="auto" />
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#fff", padding: 16 },
  centered: { flex: 1, backgroundColor: "#fff", padding: 16, justifyContent: "center" },
  title: { fontSize: 24, fontWeight: "600", marginBottom: 24, textAlign: "center" },
  h1: { fontSize: 22, fontWeight: "600", marginBottom: 12 },
  formGroup: { marginBottom: 12 },
  input: { borderWidth: 1, borderColor: "#ddd", padding: 10, borderRadius: 6 },
  muted: { color: "#666", marginTop: 8 },
  rowBetween: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 12, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: "#eee" },
  card: { borderWidth: 1, borderColor: "#eee", borderRadius: 8, padding: 12, marginBottom: 12 },
  cardTitle: { fontWeight: "600", marginBottom: 4 },
});
