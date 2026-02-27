import React, { useEffect, useState } from 'react';
import { StyleSheet, View, Text, FlatList, ActivityIndicator, TouchableOpacity, Image, SafeAreaView } from 'react-native';
import { getPredictionsToday, getFootballPredictions } from '../api/api';
import { theme } from '../theme/theme';
import { Trophy, Clock } from 'lucide-react-native';

const PredictionCard = ({ item, isDark }) => {
    const colors = isDark ? theme.dark : theme.light;

    return (
        <View style={[styles.card, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
            <View style={styles.matchHeader}>
                <View style={styles.team}>
                    <Text style={[styles.teamName, { color: colors.textPrimary }]}>{item.away_team}</Text>
                </View>
                <View style={styles.vsBadge}>
                    <Text style={styles.vsText}>VS</Text>
                </View>
                <View style={styles.team}>
                    <Text style={[styles.teamName, { color: colors.textPrimary }]}>{item.home_team}</Text>
                </View>
            </View>

            <View style={[styles.resultContainer, { backgroundColor: colors.bgPrimary }]}>
                <Text style={styles.winnerLabel}>{item.winner}</Text>
                <Text style={[styles.probabilityText, { color: colors.textPrimary }]}>
                    {(item.win_probability).toFixed(1)}%
                </Text>
                <Text style={styles.probLabel}>Probabilidad</Text>
            </View>

            <View style={styles.meta}>
                <View style={[styles.badge, { backgroundColor: colors.bgPrimary }]}>
                    <Text style={[styles.badgeText, { color: colors.textSecondary }]}>
                        {item.warning_level || 'NORMAL'}
                    </Text>
                </View>
            </View>
        </View>
    );
};

export default function PredictionsScreen({ sport = 'nba', isDark }) {
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState([]);
    const colors = isDark ? theme.dark : theme.light;

    const fetchData = async () => {
        setLoading(true);
        try {
            const result = sport === 'nba' ? await getPredictionsToday() : await getFootballPredictions();
            setData(result.predictions || []);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [sport]);

    if (loading) {
        return (
            <View style={[styles.center, { backgroundColor: colors.bgPrimary }]}>
                <ActivityIndicator size="large" color={colors.accent} />
            </View>
        );
    }

    return (
        <SafeAreaView style={[styles.container, { backgroundColor: colors.bgPrimary }]}>
            <FlatList
                data={data}
                keyExtractor={(item, index) => index.toString()}
                renderItem={({ item }) => <PredictionCard item={item} isDark={isDark} />}
                contentContainerStyle={styles.list}
                ListEmptyComponent={
                    <View style={styles.empty}>
                        <Text style={{ color: colors.textSecondary }}>No hay partidos disponibles hoy</Text>
                    </View>
                }
            />
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    center: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    list: {
        padding: 16,
    },
    card: {
        borderRadius: 24,
        padding: 20,
        marginBottom: 16,
        borderWidth: 1,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 10,
        elevation: 3,
    },
    matchHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 16,
    },
    team: {
        flex: 1,
        alignItems: 'center',
    },
    teamName: {
        fontSize: 14,
        fontWeight: '600',
        textAlign: 'center',
    },
    vsBadge: {
        paddingHorizontal: 10,
        paddingVertical: 4,
        backgroundColor: 'rgba(0,0,0,0.05)',
        borderRadius: 8,
        marginHorizontal: 10,
    },
    vsText: {
        fontSize: 10,
        fontWeight: '700',
        color: '#888',
    },
    resultContainer: {
        borderRadius: 16,
        padding: 14,
        alignItems: 'center',
        marginBottom: 12,
    },
    winnerLabel: {
        fontSize: 14,
        fontWeight: '700',
        color: '#0071e3',
        marginBottom: 2,
    },
    probabilityText: {
        fontSize: 26,
        fontWeight: '700',
    },
    probLabel: {
        fontSize: 11,
        color: '#86868b',
    },
    meta: {
        flexDirection: 'row',
    },
    badge: {
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 8,
    },
    badgeText: {
        fontSize: 11,
        fontWeight: '500',
    },
    empty: {
        alignItems: 'center',
        marginTop: 40,
    }
});
