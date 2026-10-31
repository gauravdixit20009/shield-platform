import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { mobileApi, getDeviceFingerprint } from '../services/api';
import { authenticateWithBiometrics } from '../services/biometricService';

export default function LoginScreen({ onLoginSuccess }: { onLoginSuccess: (officer: any) => void }) {
  const [badgeNumber, setBadgeNumber] = useState('IPS-MH-2024-001');
  const [password, setPassword] = useState('Password@123');
  const [totpToken, setTotpToken] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchCurrentOtp = async () => {
    try {
      const res = await mobileApi.get('/auth/demo-totp');
      setTotpToken(res.data.code);
    } catch {
      Alert.alert('Notice', 'Enter 6-digit TOTP from your authenticator app.');
    }
  };

  const handleLogin = async () => {
    if (!badgeNumber || !password || !totpToken) {
      Alert.alert('Required Fields', 'Please enter Badge Number, Password, and 6-digit MFA Code.');
      return;
    }

    setLoading(true);
    try {
      // First verify biometrics on device
      const bioPassed = await authenticateWithBiometrics('Confirm Officer Identity to Unlock Device Enclave');
      if (!bioPassed) {
        Alert.alert('Biometric Verification', 'Biometric check cancelled or failed. Please authenticate.');
        setLoading(false);
        return;
      }

      const fingerprint = await getDeviceFingerprint();
      const res = await mobileApi.post('/auth/login', {
        badge_number: badgeNumber.trim().toUpperCase(),
        password: password,
        totp_token: totpToken.trim(),
        device_fingerprint: fingerprint,
      });

      const { access_token, refresh_token, officer } = res.data;
      await SecureStore.setItemAsync('shield_token', access_token);
      await SecureStore.setItemAsync('shield_refresh_token', refresh_token);
      await SecureStore.setItemAsync('shield_officer', JSON.stringify(officer));

      onLoginSuccess(officer);
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Authentication failed. Please verify credentials.';
      Alert.alert('Security Authorization Failed', detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <View style={styles.card}>
        <View style={styles.logoBadge}>
          <Text style={styles.logoText}>🛡️</Text>
        </View>

        <Text style={styles.title}>SHIELD ENCLAVE</Text>
        <Text style={styles.subtitle}>Sovereign Police & Intelligence Client</Text>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>BADGE NUMBER / SERVICE ID</Text>
          <TextInput
            style={styles.input}
            value={badgeNumber}
            onChangeText={setBadgeNumber}
            placeholder="e.g. IPS-MH-2024-001"
            placeholderTextColor="#64748b"
            autoCapitalize="characters"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>CLEARANCE PASSWORD</Text>
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            placeholder="••••••••••••"
            placeholderTextColor="#64748b"
            secureTextEntry
          />
        </View>

        <View style={styles.inputGroup}>
          <View style={styles.mfaHeaderRow}>
            <Text style={styles.label}>6-DIGIT MFA TOKEN (TOTP)</Text>
            <TouchableOpacity onPress={fetchCurrentOtp}>
              <Text style={styles.mfaFetchText}>Auto-Fill Current OTP</Text>
            </TouchableOpacity>
          </View>
          <TextInput
            style={[styles.input, styles.otpInput]}
            value={totpToken}
            onChangeText={setTotpToken}
            placeholder="000000"
            placeholderTextColor="#64748b"
            keyboardType="number-pad"
            maxLength={6}
          />
        </View>

        <TouchableOpacity
          style={styles.loginBtn}
          onPress={handleLogin}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.loginBtnText}>AUTHENTICATE & LOG IN</Text>
          )}
        </TouchableOpacity>

        <Text style={styles.securityFooter}>
          Hardware-Protected Keystore • End-to-End Cryptographic Audit
        </Text>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#06090e',
    justifyContent: 'center',
    padding: 20,
  },
  card: {
    backgroundColor: '#0c121d',
    borderColor: '#1e293b',
    borderWidth: 1,
    borderRadius: 20,
    padding: 24,
  },
  logoBadge: {
    alignSelf: 'center',
    width: 60,
    height: 60,
    borderRadius: 16,
    backgroundColor: '#1e293b',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  logoText: {
    fontSize: 28,
  },
  title: {
    fontSize: 20,
    fontWeight: '800',
    color: '#ffffff',
    textAlign: 'center',
    letterSpacing: 1.5,
  },
  subtitle: {
    fontSize: 12,
    color: '#94a3b8',
    textAlign: 'center',
    marginBottom: 24,
    marginTop: 4,
  },
  inputGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 10,
    fontWeight: '700',
    color: '#94a3b8',
    marginBottom: 6,
    letterSpacing: 0.5,
  },
  mfaHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'between',
    alignItems: 'center',
  },
  mfaFetchText: {
    fontSize: 11,
    color: '#38bdf8',
    fontWeight: '600',
  },
  input: {
    backgroundColor: '#111927',
    borderColor: '#334155',
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: '#f8fafc',
    fontSize: 14,
  },
  otpInput: {
    letterSpacing: 8,
    textAlign: 'center',
    fontWeight: '700',
    color: '#f59e0b',
  },
  loginBtn: {
    backgroundColor: '#2563eb',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 10,
  },
  loginBtnText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '800',
    letterSpacing: 1,
  },
  securityFooter: {
    fontSize: 10,
    color: '#64748b',
    textAlign: 'center',
    marginTop: 18,
  },
});
