import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { mobileApi } from '../services/api';

export default function AriaChatScreen() {
  const [messages, setMessages] = useState<any[]>([
    {
      id: '1',
      sender: 'aria',
      text: 'Officer, ARIA intelligence assistant is ready. Ask me to synthesize case files, review suspect connections, or suggest next investigative steps.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMsg = { id: Date.now().toString(), sender: 'user', text: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    const textToSend = input.trim();
    setInput('');
    setLoading(true);

    try {
      const res = await mobileApi.post('/ai/chat', { message: textToSend });
      const ariaMsg = {
        id: (Date.now() + 1).toString(),
        sender: 'aria',
        text: res.data.response || 'No response returned from model.',
      };
      setMessages((prev) => [...prev, ariaMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), sender: 'aria', text: 'Unable to reach local ARIA server node.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <View style={styles.header}>
        <Text style={styles.headerTitle}>ARIA INTELLIGENCE ASSISTANT</Text>
        <Text style={styles.headerSub}>Sovereign On-Premises LLM • Zero Cloud Leakage</Text>
      </View>

      <FlatList
        data={messages}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: 16 }}
        renderItem={({ item }) => (
          <View
            style={[
              styles.bubble,
              item.sender === 'user' ? styles.userBubble : styles.ariaBubble,
            ]}
          >
            <Text style={styles.bubbleSender}>
              {item.sender === 'user' ? 'YOU' : 'ARIA ANALYST'}
            </Text>
            <Text style={styles.bubbleText}>{item.text}</Text>
          </View>
        )}
      />

      {loading && (
        <View style={styles.loadingRow}>
          <ActivityIndicator color="#818cf8" size="small" />
          <Text style={styles.loadingText}>ARIA is synthesizing case telemetry...</Text>
        </View>
      )}

      <View style={styles.inputBar}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="Ask ARIA about suspects, FIR points, or evidence..."
          placeholderTextColor="#64748b"
        />
        <TouchableOpacity style={styles.sendBtn} onPress={sendMessage}>
          <Text style={styles.sendBtnText}>➤</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#06090e',
  },
  header: {
    padding: 16,
    paddingTop: 10,
    borderBottomWidth: 1,
    borderColor: '#1e293b',
  },
  headerTitle: {
    fontSize: 13,
    fontWeight: '800',
    color: '#818cf8',
    letterSpacing: 0.5,
  },
  headerSub: {
    fontSize: 10,
    color: '#64748b',
    marginTop: 2,
  },
  bubble: {
    borderRadius: 12,
    padding: 12,
    marginBottom: 10,
    maxWidth: '85%',
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: '#1e293b',
  },
  ariaBubble: {
    alignSelf: 'flex-start',
    backgroundColor: '#111827',
    borderWidth: 1,
    borderColor: '#312e81',
  },
  bubbleSender: {
    fontSize: 9,
    fontWeight: '800',
    color: '#818cf8',
    marginBottom: 4,
  },
  bubbleText: {
    fontSize: 12,
    color: '#f8fafc',
    lineHeight: 18,
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 16,
    marginBottom: 8,
  },
  loadingText: {
    fontSize: 11,
    color: '#818cf8',
    fontStyle: 'italic',
  },
  inputBar: {
    flexDirection: 'row',
    padding: 12,
    borderTopWidth: 1,
    borderColor: '#1e293b',
    backgroundColor: '#0c121d',
    alignItems: 'center',
    gap: 8,
  },
  input: {
    flex: 1,
    backgroundColor: '#111927',
    borderWidth: 1,
    borderColor: '#334155',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    color: '#fff',
    fontSize: 12,
  },
  sendBtn: {
    backgroundColor: '#4f46e5',
    width: 36,
    height: 36,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtnText: {
    color: '#fff',
    fontSize: 14,
  },
});
