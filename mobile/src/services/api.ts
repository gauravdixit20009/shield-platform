import axios, { AxiosInstance } from 'axios';
import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';
import { Platform } from 'react-native';

const API_BASE_URL = 'http://127.0.0.1:8000'; // Replace with production MeghRaj URL e.g., https://api.shield.gov.in

let cachedFingerprint: string | null = null;

export async function getDeviceFingerprint(): Promise<string> {
  if (cachedFingerprint) return cachedFingerprint;
  
  let stored = await SecureStore.getItemAsync('shield_device_uuid');
  if (!stored) {
    stored = Crypto.randomUUID();
    await SecureStore.setItemAsync('shield_device_uuid', stored);
  }
  
  const raw = `${stored}|${Platform.OS}|${Platform.Version}`;
  cachedFingerprint = await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, raw);
  return cachedFingerprint;
}

export const mobileApi: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

mobileApi.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('shield_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const fingerprint = await getDeviceFingerprint();
  config.headers['X-Device-Fingerprint'] = fingerprint;
  return config;
});

mobileApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = await SecureStore.getItemAsync('shield_refresh_token');
        if (!refreshToken) throw new Error('No refresh token');
        
        const fingerprint = await getDeviceFingerprint();
        const { data } = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
          device_fingerprint: fingerprint,
        });

        await SecureStore.setItemAsync('shield_token', data.access_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return mobileApi(originalRequest);
      } catch {
        await SecureStore.deleteItemAsync('shield_token');
        await SecureStore.deleteItemAsync('shield_officer');
      }
    }
    return Promise.reject(error);
  }
);
