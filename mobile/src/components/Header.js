import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';

export default function Header({ sport, setSport, section, setSection, isDark, toggleTheme, colors }) {
    return (
        <View style={[styles.header, { backgroundColor: colors.bgSecondary, borderBottomColor: colors.border }]}>
            {/* Top: Logo + Theme */}
            <View style={styles.topRow}>
                <View style={styles.logo}>
                    <Text style={styles.logoIcon}>🏀</Text>
                    <Text style={[styles.logoText, { color: colors.text }]}>La Fija</Text>
                </View>
                <TouchableOpacity
                    style={[styles.themeBtn, { backgroundColor: colors.bgMuted }]}
                    onPress={toggleTheme}
                    activeOpacity={0.7}
                >
                    <Text style={{ fontSize: 20 }}>{isDark ? '☀️' : '🌙'}</Text>
                </TouchableOpacity>
            </View>

            {/* Sport Selector */}
            <View style={[styles.selectorRow, { backgroundColor: colors.bgMuted }]}>
                <TouchableOpacity
                    style={[styles.selectorBtn, sport === 'nba' && styles.selectorActive]}
                    onPress={() => setSport('nba')}
                    activeOpacity={0.7}
                >
                    <Text style={[styles.selectorText, sport === 'nba' && styles.selectorTextActive]}>
                        🏀 NBA
                    </Text>
                </TouchableOpacity>
                <TouchableOpacity
                    style={[styles.selectorBtn, sport === 'football' && styles.selectorActive]}
                    onPress={() => setSport('football')}
                    activeOpacity={0.7}
                >
                    <Text style={[styles.selectorText, sport === 'football' && styles.selectorTextActive]}>
                        ⚽ Futbol
                    </Text>
                </TouchableOpacity>
            </View>

            {/* Section Tabs */}
            <View style={[styles.tabRow, { backgroundColor: colors.bgMuted }]}>
                <TouchableOpacity
                    style={[styles.tabBtn, section === 'predictions' && styles.tabActive]}
                    onPress={() => setSection('predictions')}
                    activeOpacity={0.7}
                >
                    <Text style={[styles.tabText, { color: colors.textSecondary }, section === 'predictions' && styles.tabTextActive]}>
                        Predicciones
                    </Text>
                </TouchableOpacity>
                <TouchableOpacity
                    style={[styles.tabBtn, section === 'history' && styles.tabActive]}
                    onPress={() => setSection('history')}
                    activeOpacity={0.7}
                >
                    <Text style={[styles.tabText, { color: colors.textSecondary }, section === 'history' && styles.tabTextActive]}>
                        Historial
                    </Text>
                </TouchableOpacity>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    header: {
        paddingTop: 54,
        paddingBottom: 12,
        paddingHorizontal: 16,
        borderBottomWidth: 1,
        gap: 10,
    },
    topRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    logo: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    logoIcon: { fontSize: 26 },
    logoText: { fontSize: 22, fontWeight: '800', letterSpacing: -0.5 },
    themeBtn: {
        width: 44,
        height: 44,
        borderRadius: 22,
        justifyContent: 'center',
        alignItems: 'center',
    },
    selectorRow: {
        flexDirection: 'row',
        borderRadius: 99,
        padding: 3,
    },
    selectorBtn: {
        flex: 1,
        paddingVertical: 8,
        borderRadius: 99,
        alignItems: 'center',
    },
    selectorActive: {
        backgroundColor: '#0071e3',
        shadowColor: '#0071e3',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.3,
        shadowRadius: 4,
        elevation: 3,
    },
    selectorText: {
        fontSize: 13,
        fontWeight: '600',
        color: '#86868b',
    },
    selectorTextActive: { color: '#fff' },
    tabRow: {
        flexDirection: 'row',
        borderRadius: 12,
        padding: 3,
    },
    tabBtn: {
        flex: 1,
        paddingVertical: 10,
        borderRadius: 10,
        alignItems: 'center',
    },
    tabActive: {
        backgroundColor: '#0071e3',
    },
    tabText: {
        fontSize: 14,
        fontWeight: '500',
    },
    tabTextActive: {
        color: '#fff',
        fontWeight: '600',
    },
});
