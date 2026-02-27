import React, { useEffect, useState } from 'react';
import { StyleSheet, View, Text, FlatList, ActivityIndicator, SafeAreaView } from 'react-native';
import { getHistoryFull, getFootballHistory } from '../api/api';
import { theme } from '../theme/theme';
import { Check, X, Clock } from 'lucide-react-native';

const HistoryItem = ({ item, isDark }) => {
    const colors = isDark ? theme.dark : theme.light;
    const isWin = item.result === 'WIN';
    const isLoss = item.result === 'LOSS';

    return (
        <View style={[styles.card, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
            <View style={styles.info}>
                <Text style={[styles.matchName, { color: colors.textPrimary }]}>{item.match_id}</Text>
                <Text style={[styles.prediction, { color: colors.textSecondary }]}>
                    Pred: {item.winner} ({item.win_probability ? item.win_probability.toFixed(1) : '0'}%)
                </Text>
            </View>

            <View style={[
                styles.badge,
                isWin ? styles.winBg : isLoss ? styles.lossBg : styles.pendingBg
            ]}>
                {isWin ? <Check size={14} color={theme.light.success} /> :
                    isLoss ? <X size={14} color={theme.light.danger} /> :
                        <Clock size={14} color={theme.light.warning} />}
                <Text style={[
                    styles.badgeText,
                    { color: isWin ? theme.light.success : isLoss ? theme.light.danger : theme.light.warning }
                ]}>
                    {item.result}
                </Text>
            </View>
        </View>
    );
};

export default function HistoryScreen({ sport = 'nba', isDark }) {
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState([]);
    const colors = isDark ? theme.dark : theme.light;

    const fetchData = async () => {
        setLoading(true);
        try {
            const result = sport === 'nba' ? await getHistoryFull(30) : await getFootballHistory(30);
            setData(result.history || []);
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
                renderItem={({ item }) => <HistoryItem item={item} isDark={isDark} />}
                contentContainerStyle={styles.list}
                ListEmptyComponent={
                    <View style={styles.empty}>
                        <Text style={{ color: colors.textSecondary }}>No hay historial disponible</Text>
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
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        borderRadius: 20,
        marginBottom: 10,
        borderWidth: 1,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 5,
        elevation: 2,
    },
    info: {
        flex: 1,
    },
    matchName: {
        fontSize: 14,
        fontWeight: '600',
        marginBottom: 2,
    },
    prediction: {
        fontSize: 12,
    },
    badge: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 10,
        paddingVertical: 6,
        borderRadius: 8,
        gap: 4,
    },
    badgeText: {
        fontSize: 11,
        fontWeight: '700',
    },
    winBg: { backgroundColor: 'rgba(52, 199, 89, 0.15)' },
    lossBg: { backgroundColor: 'rgba(255, 59, 48, 0.15)' },
    pendingBg: { backgroundColor: 'rgba(255, 149, 0, 0.15)' },
    empty: {
        alignItems: 'center',
        marginTop: 40,
    }
});
