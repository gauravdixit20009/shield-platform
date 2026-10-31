import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { mobileApi } from '../services/api';

export default function CasesScreen() {
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadCases = async () => {
    setLoading(true);
    try {
      const res = await mobileApi.get('/cases/');
      setCases(res.data.cases || []);
    } catch {
      Alert.alert('Error', 'Unable to fetch assigned cases.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  const renderItem = ({ item }: { item: any }) => (
    <TouchableOpacity
      style={styles.card}
      onPress={() => Alert.alert(item.case_number, `${item.title}\n\nCategory: ${item.category}\nPriority: ${item.priority}\nStatus: ${item.status}`)}
    >
      <View style={styles.headerRow}>
        <Text style={styles.caseNumber}>{item.case_number}</Text>
        <View style={[styles.priorityBadge, item.priority === 'CRITICAL' ? styles.badgeCrit : styles.badgeHigh]}>
          <Text style={styles.priorityText}>{item.priority}</Text>
        </View>
      </View>
      <Text style={styles.title}>{item.title}</Text>
      <Text style={styles.location}>📍 {item.incident_location || 'Jurisdiction HQ'}</Text>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <View style={styles.titleRow}>
        <Text style={styles.headerTitle}>ASSIGNED CASE REPOSITORY</Text>
        <TouchableOpacity onPress={loadCases}>
          <Text style={styles.refreshText}>Sync</Text>
        </TouchableOpacity>
      </View>
      {loading ? (
        <ActivityIndicator color="#38bdf8" style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={cases}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          contentContainerStyle={{ paddingBottom: 20 }}
          ListEmptyComponent={<Text style={styles.emptyText}>No assigned cases found.</Text>}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#06090e',
    padding: 16,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    paddingTop: 10,
  },
  headerTitle: {
    fontSize: 13,
    fontWeight: '800',
    color: '#94a3b8',
    letterSpacing: 0.5,
  },
  refreshText: {
    fontSize: 12,
    color: '#38bdf8',
    fontWeight: '700',
  },
  card: {
    backgroundColor: '#0c121d',
    borderColor: '#1e293b',
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  caseNumber: {
    fontSize: 11,
    fontWeight: '700',
    color: '#38bdf8',
  },
  priorityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  badgeCrit: {
    backgroundColor: '#991b1b',
  },
  badgeHigh: {
    backgroundColor: '#854d0e',
  },
  priorityText: {
    fontSize: 9,
    fontWeight: '800',
    color: '#ffffff',
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    color: '#f8fafc',
    marginBottom: 6,
  },
  location: {
    fontSize: 11,
    color: '#64748b',
  },
  emptyText: {
    color: '#64748b',
    textAlign: 'center',
    marginTop: 40,
    fontSize: 12,
  },
});
