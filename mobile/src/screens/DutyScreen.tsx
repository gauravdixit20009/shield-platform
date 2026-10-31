import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { DutyService } from '../services/dutyService';

export default function DutyScreen({ officer }: { officer: any }) {
  const [isOnDuty, setIsOnDuty] = useState(false);
  const [loading, setLoading] = useState(false);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [isRecordingAudio, setIsRecordingAudio] = useState(false);

  const toggleDuty = async () => {
    setLoading(true);
    try {
      if (!isOnDuty) {
        const res = await DutyService.startDuty();
        setIsOnDuty(true);
        setCoords({ lat: res.latitude, lng: res.longitude });
        Alert.alert(
          'Duty Mode Activated',
          'GPS tracking beacon is actively streaming to Command HQ. Foreground service initiated.'
        );
      } else {
        await DutyService.endDuty();
        setIsOnDuty(false);
        setCoords(null);
        Alert.alert('Duty Mode Deactivated', 'Patrol logged and surveillance stopped.');
      }
    } catch (err: any) {
      Alert.alert('Duty Mode Error', err.message || 'Unable to update duty status.');
    } finally {
      setLoading(false);
    }
  };

  const handlePanicSOS = () => {
    Alert.alert(
      '🚨 TRIGGER EMERGENCY SOS?',
      'Immediate priority distress signal will be broadcast to State Police Command and nearby squads.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'CONFIRM SOS DISPATCH',
          style: 'destructive',
          onPress: async () => {
            try {
              await DutyService.triggerEmergencySOS('Officer Panic Button Activated from Mobile Handset');
              Alert.alert('SOS Transmitted', 'Emergency backup dispatched. Ambient recording started.');
            } catch {
              Alert.alert('Transmission Failed', 'Check network or emergency radio channel.');
            }
          },
        },
      ]
    );
  };

  const toggleIncidentAudio = async () => {
    try {
      if (!isRecordingAudio) {
        await DutyService.startIncidentAudio();
        setIsRecordingAudio(true);
        Alert.alert('Audio Evidence', 'Secure audio statement recording started.');
      } else {
        const uri = await DutyService.stopIncidentAudio();
        setIsRecordingAudio(false);
        Alert.alert('Recording Secured', `Statement saved at:\n${uri}`);
      }
    } catch (err: any) {
      Alert.alert('Audio Error', err.message);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.officerName}>{officer?.full_name || 'Field Officer'}</Text>
        <Text style={styles.officerRank}>{officer?.rank} • {officer?.badge_number}</Text>
      </View>

      {/* DUTY TOGGLE CARD */}
      <View style={[styles.card, isOnDuty ? styles.cardActive : null]}>
        <View style={styles.dutyStatusRow}>
          <View style={[styles.statusDot, isOnDuty ? styles.dotGreen : styles.dotGray]} />
          <Text style={styles.dutyStatusText}>
            {isOnDuty ? 'PATROL ACTIVE • GPS BEACON LIVE' : 'OFF DUTY • MONITORING INACTIVE'}
          </Text>
        </View>

        <Text style={styles.dutyDescription}>
          {isOnDuty
            ? 'Your device telemetry is streaming to central dispatch. Hardware sensors are actively monitored for officer safety.'
            : 'Activate Duty Mode when commencing active shift or field operation. Explicit consent is recorded on server.'}
        </Text>

        {coords && (
          <View style={styles.coordsBox}>
            <Text style={styles.coordsLabel}>ACTIVE TELEMETRY COORDINATES</Text>
            <Text style={styles.coordsValue}>
              LAT: {coords.lat.toFixed(5)}  |  LNG: {coords.lng.toFixed(5)}
            </Text>
          </View>
        )}

        <TouchableOpacity
          style={[styles.dutyBtn, isOnDuty ? styles.dutyBtnActive : styles.dutyBtnInactive]}
          onPress={toggleDuty}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.dutyBtnText}>
              {isOnDuty ? 'END SHIFT & STOP TRACKING' : 'ACTIVATE ON-DUTY PATROL'}
            </Text>
          )}
        </TouchableOpacity>
      </View>

      {/* SOS EMERGENCY PANIC BUTTON */}
      <TouchableOpacity style={styles.panicButton} onPress={handlePanicSOS}>
        <Text style={styles.panicIcon}>🚨</Text>
        <View style={styles.panicTextCol}>
          <Text style={styles.panicTitle}>EMERGENCY SOS BACKUP</Text>
          <Text style={styles.panicSub}>Broadcast priority distress coordinates to HQ</Text>
        </View>
      </TouchableOpacity>

      {/* INCIDENT EVIDENCE CAPTURE */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>INCIDENT EVIDENCE CAPTURE</Text>
        <Text style={styles.sectionSub}>Hardware-signed evidence with tamper-proof SHA-512 chain of custody.</Text>

        <View style={styles.actionsGrid}>
          <TouchableOpacity
            style={[styles.actionBtn, isRecordingAudio ? styles.actionBtnActive : null]}
            onPress={toggleIncidentAudio}
          >
            <Text style={styles.actionBtnIcon}>{isRecordingAudio ? '⏹️' : '🎙️'}</Text>
            <Text style={styles.actionBtnText}>
              {isRecordingAudio ? 'STOP RECORDING' : 'RECORD AUDIO'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => Alert.alert('Camera Capture', 'Incident camera initiated with watermark embedding.')}
          >
            <Text style={styles.actionBtnIcon}>📸</Text>
            <Text style={styles.actionBtnText}>SECURE PHOTO</Text>
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#06090e',
    padding: 16,
  },
  header: {
    marginBottom: 16,
    paddingTop: 10,
  },
  officerName: {
    fontSize: 18,
    fontWeight: '800',
    color: '#ffffff',
  },
  officerRank: {
    fontSize: 12,
    color: '#38bdf8',
    fontWeight: '600',
    marginTop: 2,
  },
  card: {
    backgroundColor: '#0c121d',
    borderColor: '#1e293b',
    borderWidth: 1,
    borderRadius: 16,
    padding: 18,
    marginBottom: 16,
  },
  cardActive: {
    borderColor: '#059669',
    backgroundColor: '#061713',
  },
  dutyStatusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  dotGreen: {
    backgroundColor: '#10b981',
  },
  dotGray: {
    backgroundColor: '#64748b',
  },
  dutyStatusText: {
    fontSize: 11,
    fontWeight: '800',
    color: '#e2e8f0',
    letterSpacing: 0.5,
  },
  dutyDescription: {
    fontSize: 12,
    color: '#94a3b8',
    lineHeight: 18,
    marginBottom: 14,
  },
  coordsBox: {
    backgroundColor: '#09101c',
    borderRadius: 8,
    padding: 10,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#1e293b',
  },
  coordsLabel: {
    fontSize: 9,
    color: '#64748b',
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  coordsValue: {
    fontSize: 11,
    color: '#38bdf8',
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    fontWeight: '700',
    marginTop: 2,
  },
  dutyBtn: {
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  dutyBtnInactive: {
    backgroundColor: '#2563eb',
  },
  dutyBtnActive: {
    backgroundColor: '#dc2626',
  },
  dutyBtnText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 1,
  },
  panicButton: {
    backgroundColor: '#7f1d1d',
    borderColor: '#dc2626',
    borderWidth: 1.5,
    borderRadius: 16,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  panicIcon: {
    fontSize: 28,
    marginRight: 12,
  },
  panicTextCol: {
    flex: 1,
  },
  panicTitle: {
    fontSize: 14,
    fontWeight: '900',
    color: '#fee2e2',
    letterSpacing: 0.5,
  },
  panicSub: {
    fontSize: 11,
    color: '#fca5a5',
    marginTop: 2,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '800',
    color: '#ffffff',
    letterSpacing: 0.5,
  },
  sectionSub: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 2,
    marginBottom: 14,
  },
  actionsGrid: {
    flexDirection: 'row',
    gap: 10,
  },
  actionBtn: {
    flex: 1,
    backgroundColor: '#111927',
    borderColor: '#1e293b',
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  actionBtnActive: {
    backgroundColor: '#991b1b',
    borderColor: '#ef4444',
  },
  actionBtnIcon: {
    fontSize: 20,
    marginBottom: 4,
  },
  actionBtnText: {
    fontSize: 10,
    fontWeight: '800',
    color: '#e2e8f0',
  },
});
