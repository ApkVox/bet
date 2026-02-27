import React, { useState, useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { View, useColorScheme, StyleSheet } from 'react-native';
import Header from './src/components/Header';
import PredictionsScreen from './src/screens/PredictionsScreen';
import HistoryScreen from './src/screens/HistoryScreen';
import { LightTheme, DarkTheme } from './src/theme/theme';

export default function App() {
  const systemScheme = useColorScheme();
  const [isDark, setIsDark] = useState(systemScheme === 'dark');
  const [sport, setSport] = useState('nba');
  const [section, setSection] = useState('predictions');

  const colors = isDark ? DarkTheme : LightTheme;

  const toggleTheme = () => setIsDark(prev => !prev);

  return (
    <View style={[styles.root, { backgroundColor: colors.bg }]}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Header
        sport={sport}
        setSport={setSport}
        section={section}
        setSection={setSection}
        isDark={isDark}
        toggleTheme={toggleTheme}
        colors={colors}
      />
      <View style={styles.content}>
        {section === 'predictions' ? (
          <PredictionsScreen sport={sport} colors={colors} />
        ) : (
          <HistoryScreen sport={sport} colors={colors} />
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  content: { flex: 1 },
});
