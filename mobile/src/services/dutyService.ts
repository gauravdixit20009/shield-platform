import * as Location from 'expo-location';
import * as TaskManager from 'expo-task-manager';
import * as Notifications from 'expo-notifications';
import { Accelerometer } from 'expo-sensors';
import { Audio } from 'expo-av';
import { mobileApi, getDeviceFingerprint } from './api';

const DUTY_LOCATION_TASK = 'SHIELD_BACKGROUND_LOCATION_TASK';

// Configure foreground persistent notification
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

let accelerometerSubscription: any = null;
let lastMovementTimestamp = Date.now();
let activeRecording: Audio.Recording | null = null;

// Background task definition
TaskManager.defineTask(DUTY_LOCATION_TASK, async ({ data, error }: any) => {
  if (error) {
    console.error('Location task error:', error);
    return;
  }
  if (data) {
    const { locations } = data;
    const loc = locations[0];
    if (loc) {
      try {
        await mobileApi.post('/duty/location', {
          latitude: loc.coords.latitude,
          longitude: loc.coords.longitude,
          altitude: loc.coords.altitude,
          accuracy: loc.coords.accuracy,
          speed: loc.coords.speed,
          heading: loc.coords.heading,
        });
      } catch (err) {
        console.error('Failed to sync location to HQ:', err);
      }
    }
  }
});

export const DutyService = {
  async startDuty(): Promise<{ status: string; latitude: number; longitude: number }> {
    const { status: fgStatus } = await Location.requestForegroundPermissionsAsync();
    if (fgStatus !== 'granted') {
      throw new Error('Location permission is required for Duty Mode');
    }

    const { status: bgStatus } = await Location.requestBackgroundPermissionsAsync();
    if (bgStatus !== 'granted') {
      throw new Error('Background location permission is required for active patrol');
    }

    const currentLoc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
    const fingerprint = await getDeviceFingerprint();

    // Register with server
    const res = await mobileApi.post('/duty/start', {
      device_fingerprint: fingerprint,
      initial_latitude: currentLoc.coords.latitude,
      initial_longitude: currentLoc.coords.longitude,
    });

    // Start background location updates (every 30s)
    await Location.startLocationUpdatesAsync(DUTY_LOCATION_TASK, {
      accuracy: Location.Accuracy.Balanced,
      timeInterval: 30000,
      distanceInterval: 15,
      foregroundService: {
        notificationTitle: 'SHIELD Active Patrol',
        notificationBody: 'On-Duty Monitoring & Emergency Dispatch Beacon Active',
        notificationColor: '#2563eb',
      },
    });

    // Start Accelerometer to detect dead-officer (no motion for extended period)
    lastMovementTimestamp = Date.now();
    accelerometerSubscription = Accelerometer.addListener(({ x, y, z }) => {
      const acceleration = Math.sqrt(x * x + y * y + z * z);
      if (Math.abs(acceleration - 1) > 0.15) {
        lastMovementTimestamp = Date.now();
      }
    });
    Accelerometer.setUpdateInterval(5000);

    return {
      status: res.data.status,
      latitude: currentLoc.coords.latitude,
      longitude: currentLoc.coords.longitude,
    };
  },

  async endDuty(): Promise<void> {
    const hasStarted = await Location.hasStartedLocationUpdatesAsync(DUTY_LOCATION_TASK);
    if (hasStarted) {
      await Location.stopLocationUpdatesAsync(DUTY_LOCATION_TASK);
    }
    if (accelerometerSubscription) {
      accelerometerSubscription.remove();
      accelerometerSubscription = null;
    }
    if (activeRecording) {
      await this.stopIncidentAudio();
    }
    await mobileApi.post('/duty/end');
  },

  async triggerEmergencySOS(message?: string): Promise<any> {
    const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Highest });
    const res = await mobileApi.post('/duty/panic', {
      latitude: loc.coords.latitude,
      longitude: loc.coords.longitude,
      message: message || 'EMERGENCY: Officer Panic Button Triggered from mobile client',
    });

    // Automatically trigger ambient recording for situational evidence
    try {
      await this.startIncidentAudio();
    } catch (e) {
      console.warn('Auto recording fallback failed', e);
    }

    return res.data;
  },

  async startIncidentAudio(): Promise<void> {
    const { granted } = await Audio.requestPermissionsAsync();
    if (!granted) return;

    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
    });

    const recording = new Audio.Recording();
    await recording.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
    await recording.startAsync();
    activeRecording = recording;
  },

  async stopIncidentAudio(): Promise<string | null> {
    if (!activeRecording) return null;
    await activeRecording.stopAndUnloadAsync();
    const uri = activeRecording.getURI();
    activeRecording = null;
    return uri;
  },
};
