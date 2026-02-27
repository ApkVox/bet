import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { theme } from '../theme/theme';
import { Sun, Moon, Basketball, Tally1 as SoccerBall } from 'lucide-react-native';

export default function Header({ sport, setSport, section, setSection, isDark, setIsDark }) {
    const colors = isDark ? theme.dark : theme.light;

    return (
        <View style={[styles.header, { backgroundColor: colors.bgSecondary, borderBottomColor: colors.border }]}>
            <View style={styles.topRow}>
                <View style={styles.logo}>
                    <Text style={styles.logoIcon}>🏀</Text>
                    <Text style={[styles.logoText, { color: colors.textPrimary }]}>La Fija</Text>
                </View>
                <TouchableOpacity
                    style={[styles.themeToggle, { backgroundColor: colors.bgPrimary }]}
                    onPress={() => setIsDark(!isDark)}
                >
                    {isDark ? <Sun size={20} color={colors.textPrimary} /> : <Moon size={20} color={colors.textPrimary} />}
                </TouchableOpacity>
            </View>

            <View style={styles.bottomRow}>
                <View style={[styles.selector, { backgroundColor: colors.bgPrimary }]}>
                    <TouchableOpacity
                        style={[styles.selBtn, sport === 'nba' && { backgroundColor: theme.light.accent }]}
                        onPress={() => setSport('nba')}
                    >
                        <Text style={[styles.selText, sport === 'nba' && { color: 'white' }]}>🏀 NBA</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                        style={[styles.selBtn, sport === 'football' && { backgroundColor: theme.light.accent }]}
                        onPress={() => setSport('football')}
                    >
                        <Text style={[styles.selText, sport === 'football' && { color: 'white' }]}>⚽ Fútbol</Text>
                    </TouchableOpacity>
                </View>

                <View style={[styles.nav, { backgroundColor: colors.bgPrimary }]}>
                    <TouchableOpacity
                        style={[styles.navBtn, section === 'predictions' && { backgroundColor: theme.light.accent }]}
                        onPress={() => setSection('predictions')}
                    >
                        <Text style={[styles.navText, section === 'predictions' && { color: 'white' }]}>Predicciones</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                        style={[styles.navBtn, section === 'history' && { backgroundColor: theme.light.accent }]}
                        onPress={() => setSection('history')}
                    >
                        <Text style={[styles.navText, section === 'history' && { color: 'white' }]}>Historial</Text>
                    </TouchableOpacity>
                </View>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    header: {
        paddingTop: 50,
        paddingBottom: 15,
        paddingHorizontal: 16,
        borderBottomWidth: 1,
    },
    topRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 15,
    },
    logo: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    logoIcon: {
        fontSize: 24,
    },
    logoText: {
        fontSize: 20,
        fontWeight: '700',
    },
    themeToggle: {
        width: 44,
        height: 44,
        borderRadius: 22,
        justifyContent: 'center',
        alignItems: 'center',
    },
    bottomRow: {
        gap: 12,
    },
    selector: {
        flexDirection: 'row',
        borderRadius: 99,
        padding: 4,
    },
    selBtn: {
        flex: 1,
        paddingVertical: 8,
        borderRadius: 99,
        alignItems: 'center',
    },
    selText: {
        fontSize: 13,
        fontWeight: '600',
        color: '#86868b',
    },
    nav: {
        flexDirection: 'row',
        borderRadius: 12,
        padding: 4,
    },
    navBtn: {
        flex: 1,
        paddingVertical: 10,
        borderRadius: 10,
        alignItems: 'center',
    },
    navText: {
        fontSize: 14,
        fontWeight: '500',
        color: '#86868b',
    },
});
