import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as SecureStore from 'expo-secure-store';

import LoginScreen from './src/screens/LoginScreen';
import DutyScreen from './src/screens/DutyScreen';
import CasesScreen from './src/screens/CasesScreen';
import AriaChatScreen from './src/screens/AriaChatScreen';

export default function App() {
  const [officer, setOfficer] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'duty' | 'cases' | 'aria'>('duty');

  useEffect(() => {
    checkExistingSession();
  }, []);

  const checkExistingSession = async () => {
    try {
      const stored = await SecureStore.getItemAsync('shield_officer');
      if (stored) {
        setOfficer(JSON.parse(stored));
      }
    } catch (e) {
      console.warn('Session check error', e);
    }
  };

  const handleLogout = async () => {
    await SecureStore.deleteItemAsync('shield_token');
    await SecureStore.deleteItemAsync('shield_officer');
    setOfficer(null);
  };

  if (!officer) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar style="light" />
        <LoginScreen onLoginSuccess={(off) => setOfficer(off)} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />

      {/* TOP STATUS BAR */}
      <View style={styles.topBar}>
        <View style={styles.brandRow}>
          <Text style={styles.brandShield}>SHIELD</Text>
          <View style={styles.enclaveBadge}>
            <Text style={styles.enclaveText}>OFFICER ENCLAVE</Text>
          </View>
        </View>
        <TouchableOpacity onPress={handleLogout} style={styles.logoutBtn}>
          <Text style={styles.logoutText}>Sign Out</Text>
        </TouchableOpacity>
      </View>

      {/* SCREEN BODY */}
      <View style={styles.screenContainer}>
        {activeTab === 'duty' && <DutyScreen officer={officer} />}
        {activeTab === 'cases' && <CasesScreen />}
        {activeTab === 'aria' && <AriaChatScreen />}
      </View>

      {/* BOTTOM NAVIGATION TABS */}
      <View style={styles.tabBar}>
        <TouchableOpacity
          style={[styles.tabItem, activeTab === 'duty' && styles.tabItemActive]}
          onPress={() => setActiveTab('duty')}
        >
          <Text style={styles.tabIcon}>📍</Text>
          <Text style={[styles.tabLabel, activeTab === 'duty' && styles.tabLabelActive]}>DUTY</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tabItem, activeTab === 'cases' && styles.tabItemActive]}
          onPress={() => setActiveTab('cases')}
        >
          <Text style={styles.tabIcon}>🗂️</Text>
          <Text style={[styles.tabLabel, activeTab === 'cases' && styles.tabLabelActive]}>CASES</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tabItem, activeTab === 'aria' && styles.tabItemActive]}
          onPress={() => setActiveTab('aria')}
        >
          <Text style={styles.tabIcon}>🤖</Text>
          <Text style={[styles.tabLabel, activeTab === 'aria' && styles.tabLabelActive]}>ARIA AI</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#06090e',
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderColor: '#1e293b',
    backgroundColor: '#0a0f18',
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  brandShield: {
    fontSize: 14,
    fontWeight: '900',
    color: '#ffffff',
    letterSpacing: 1,
  },
  enclaveBadge: {
    backgroundColor: '#064e3b',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  enclaveText: {
    fontSize: 9,
    fontWeight: '800',
    color: '#34d399',
  },
  logoutBtn: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    backgroundColor: '#1f1315',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#7f1d1d',
  },
  logoutText: {
    fontSize: 10,
    color: '#f87171',
    fontWeight: '700',
  },
  screenContainer: {
    flex: 1,
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#0a0f18',
    borderTopWidth: 1,
    borderColor: '#1e293b',
    paddingVertical: 8,
  },
  tabItem: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 4,
  },
  tabItemActive: {
    borderTopWidth: 2,
    borderColor: '#38bdf8',
  },
  tabIcon: {
    fontSize: 18,
    marginBottom: 2,
  },
  tabLabel: {
    fontSize: 9,
    fontWeight: '700',
    color: '#64748b',
    letterSpacing: 0.5,
  },
  tabLabelActive: {
    color: '#38bdf8',
  },
});
