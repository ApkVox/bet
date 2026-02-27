import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { spacing, radius } from '../theme/theme';

export default function Header({ sport, setSport, section, setSection, isDark, toggleTheme, colors }) {
    return (
        <View style={[styles.header, { backgroundColor: colors.bgSecondary, borderBottomColor: colors.border }]}>
            <View style={styles.topRow}>
                <View style={styles.logo}>
                    <Text style={styles.logoIcon}>{'\uD83C\uDFC0'}</Text>
                    <Text style={[styles.logoText, { color: colors.text }]}>La Fija</Text>
                </View>
                <TouchableOpacity
                    style={[styles.themeBtn, { backgroundColor: colors.bgMuted, borderColor: colors.border }]}
                    onPress={toggleTheme}
                    activeOpacity={0.7}
                >
                    <Text style={{ fontSize: 20 }}>{isDark ? '\u2600\uFE0F' : '\u263E'}</Text>
                </TouchableOpacity>
            </View>

            <View style={[styles.selectorRow, { backgroundColor: colors.bgMuted }]}>
                <TouchableOpacity
                    style={[styles.selectorBtn, sport === 'nba' && { backgroundColor: colors.accent }]}
                    onPress={() => setSport('nba')}
                    activeOpacity={0.7}
                >
                    <Text style={[styles.selectorText, { color: colors.textSecondary }, sport === 'nba' && styles.selectorTextActive]}>
                        {'\uD83C\uDFC0'} NBA
                    </Text>
                </TouchableOpacity>
                <TouchableOpacity
                    style={[styles.selectorBtn, sport === 'football' && { backgroundColor: colors.accent }]}
                    onPress={() => setSport('football')}
                    activeOpacity={0.7}
                >
                    <Text style={[styles.selectorText, { color: colors.textSecondary }, sport === 'football' && styles.selectorTextActive]}>
                        {'\u26BD'} Futbol
                    </Text>
                </TouchableOpacity>
            </View>

            <View style={[styles.tabRow, { backgroundColor: colors.bgMuted }]}>
                <TouchableOpacity
                    style={[styles.tabBtn, section === 'predictions' && { backgroundColor: colors.accent }]}
                    onPress={() => setSection('predictions')}
                    activeOpacity={0.7}
                >
                    <Text style={[styles.tabText, { color: colors.textSecondary }, section === 'predictions' && styles.tabTextActive]}>
                        Predicciones
                    </Text>
                </TouchableOpacity>
                <TouchableOpacity
                    style={[styles.tabBtn, section === 'history' && { backgroundColor: colors.accent }]}
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
        paddingBottom: spacing.md,
        paddingHorizontal: spacing.md,
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
        gap: spacing.sm,
    },
    logoIcon: { fontSize: 28 },
    logoText: { fontSize: 22, fontWeight: '900', letterSpacing: -0.5 },
    themeBtn: {
        width: 44,
        height: 44,
        borderRadius: 22,
        justifyContent: 'center',
        alignItems: 'center',
        borderWidth: 1,
    },
    selectorRow: {
        flexDirection: 'row',
        borderRadius: radius.pill,
        padding: 3,
    },
    selectorBtn: {
        flex: 1,
        paddingVertical: spacing.sm,
        borderRadius: radius.pill,
        alignItems: 'center',
    },
    selectorText: {
        fontSize: 13,
        fontWeight: '700',
    },
    selectorTextActive: { color: '#fff' },
    tabRow: {
        flexDirection: 'row',
        borderRadius: radius.md,
        padding: 3,
    },
    tabBtn: {
        flex: 1,
        paddingVertical: 10,
        borderRadius: 10,
        alignItems: 'center',
    },
    tabText: {
        fontSize: 13,
        fontWeight: '600',
    },
    tabTextActive: {
        color: '#fff',
        fontWeight: '700',
    },
});
