import * as LocalAuthentication from 'expo-local-authentication';

export async function checkBiometricsAvailable(): Promise<boolean> {
  const hasHardware = await LocalAuthentication.hasHardwareAsync();
  const isEnrolled = await LocalAuthentication.isEnrolledAsync();
  return hasHardware && isEnrolled;
}

export async function authenticateWithBiometrics(promptMessage: string = 'Verify Officer Identity'): Promise<boolean> {
  try {
    const available = await checkBiometricsAvailable();
    if (!available) return false;

    const result = await LocalAuthentication.authenticateAsync({
      promptMessage,
      fallbackLabel: 'Enter Service PIN',
      cancelLabel: 'Cancel',
      disableDeviceFallback: false,
    });

    return result.success;
  } catch (err) {
    console.error('Biometric error:', err);
    return false;
  }
}
