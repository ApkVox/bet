import React, { useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View, useColorScheme } from 'react-native';
import Header from './src/components/Header';
import PredictionsScreen from './src/screens/PredictionsScreen';
import HistoryScreen from './src/screens/HistoryScreen';
import { theme } from './src/theme/theme';

export default function App() {
  const systemColorScheme = useColorScheme();
  const [isDark, setIsDark] = useState(systemColorScheme === 'dark');
  const [sport, setSport] = useState('nba');
  const [section, setSection] = useState('predictions');

  const colors = isDark ? theme.dark : theme.light;

  return (
    <View style={[styles.container, { backgroundColor: colors.bgPrimary }]}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Header
        sport={sport}
        setSport={setSport}
        section={section}
        setSection={setSection}
        isDark={isDark}
        setIsDark={setIsDark}
      />

      <View style={styles.content}>
        {section === 'predictions' ? (
          <PredictionsScreen sport={sport} isDark={isDark} />
        ) : (
          <HistoryScreen sport={sport} isDark={isDark} />
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
  },
});
