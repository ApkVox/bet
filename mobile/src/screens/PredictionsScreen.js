import React, { useEffect, useState, useCallback } from 'react';
import {
    StyleSheet, View, Text, FlatList, ActivityIndicator,
    RefreshControl, TouchableOpacity, Animated, Image
} from 'react-native';
import { getPredictionsToday, getFootballPredictions } from '../api/api';
import { NBA_TEAM_LOGOS } from '../theme/theme';

export default function PredictionsScreen({ sport, colors }) {
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [predictions, setPredictions] = useState([]);
    const [dateStr, setDateStr] = useState('');
    const [status, setStatus] = useState('');
    const [error, setError] = useState(null);

    const fetchData = useCallback(async (isRefresh = false) => {
        if (isRefresh) setRefreshing(true); else setLoading(true);
        setError(null);
        try {
            const result = sport === 'nba'
                ? await getPredictionsToday()
                : await getFootballPredictions();
            setPredictions(result.predictions || []);
            setDateStr(result.date || '');
            setStatus(result.status || '');
        } catch (err) {
            setError('No se pudo conectar al servidor. Verifica tu conexion.');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [sport]);

    useEffect(() => { fetchData(); }, [fetchData]);

    if (loading) {
        return (
            <View style={[styles.center, { backgroundColor: colors.bg }]}>
                <ActivityIndicator size="large" color={colors.accent} />
                <Text style={[styles.loadText, { color: colors.textSecondary }]}>
                    Conectando con el servidor...
                </Text>
            </View>
        );
    }

    if (error) {
        return (
            <View style={[styles.center, { backgroundColor: colors.bg }]}>
                <Text style={{ fontSize: 40, marginBottom: 12 }}>📡</Text>
                <Text style={[styles.errorText, { color: colors.danger }]}>{error}</Text>
                <TouchableOpacity
                    style={[styles.retryBtn, { backgroundColor: colors.accent }]}
                    onPress={() => fetchData()}
                >
                    <Text style={styles.retryText}>Reintentar</Text>
                </TouchableOpacity>
            </View>
        );
    }

    const getTeamLogo = (teamName) => {
        if (sport === 'nba') {
            const url = NBA_TEAM_LOGOS[teamName];
            if (url) return { uri: url };
            return { uri: `https://ui-avatars.com/api/?name=${encodeURIComponent((teamName || '?').substring(0, 2))}&background=1d428a&color=fff&rounded=true&bold=true&size=100` };
        } else {
            return { uri: `https://ui-avatars.com/api/?name=${encodeURIComponent((teamName || '?').substring(0, 2))}&background=2d6a4f&color=fff&rounded=true&bold=true&size=100` };
        }
    };

    const renderCard = ({ item, index }) => {
        const leagueLogoUrl = sport === 'football'
            ? 'https://media.api-sports.io/football/leagues/39.png'
            : 'https://cdn.nba.com/logos/nba/nba-logoman-word-white.svg';

        const isLightMode = colorScheme === 'light';

        return (
            <Animated.View style={[styles.card, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
                {/* League Badge Header */}
                <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 12, paddingBottom: 8, borderBottomWidth: 1, borderBottomColor: colors.border }}>
                    <Image
                        source={{ uri: leagueLogoUrl }}
                        style={{ width: sport === 'football' ? 20 : 36, height: 20, marginRight: 8, tintColor: sport === 'nba' ? (isLightMode ? '#000' : '#fff') : undefined }}
                        resizeMode="contain"
                    />
                    <Text style={{ fontSize: 11, color: colors.textSecondary, textTransform: 'uppercase', fontWeight: 'bold' }}>
                        {sport === 'football' ? 'Premier League' : 'NBA'}
                    </Text>
                </View>

                {/* Match Header */}
                <View style={[styles.matchHeader, { marginTop: 16 }]}>
                    <View style={styles.teamBox}>
                        {item.home_logo ? (
                            <Image source={{ uri: item.home_logo }} style={styles.teamLogo} resizeMode="contain" />
                        ) : (
                            <View style={[styles.teamLogo, { backgroundColor: '#334155', justifyContent: 'center', alignItems: 'center' }]}>
                                <Text style={{ color: '#fff', fontWeight: 'bold' }}>{item.home_team?.substring(0, 2)}</Text>
                            </View>
                        )}
                        <Text style={[styles.teamName, { color: (item.prediction === '1' || item.prediction === item.home_team) ? colors.accent : colors.text, fontWeight: (item.prediction === '1' || item.prediction === item.home_team) ? 'bold' : 'normal' }]} numberOfLines={2}>
                            {item.home_team}
                        </Text>
                    </View>
                    <View style={[styles.vsBadge, { backgroundColor: colors.bgMuted }]}>
                        <Text style={[styles.vsText, { color: colors.textTertiary }]}>VS</Text>
                    </View>
                    <View style={styles.teamBox}>
                        {item.away_logo ? (
                            <Image source={{ uri: item.away_logo }} style={styles.teamLogo} resizeMode="contain" />
                        ) : (
                            <View style={[styles.teamLogo, { backgroundColor: '#334155', justifyContent: 'center', alignItems: 'center' }]}>
                                <Text style={{ color: '#fff', fontWeight: 'bold' }}>{item.away_team?.substring(0, 2)}</Text>
                            </View>
                        )}
                        <Text style={[styles.teamName, { color: (item.prediction === '2' || item.prediction === item.away_team) ? colors.accent : colors.text, fontWeight: (item.prediction === '2' || item.prediction === item.away_team) ? 'bold' : 'normal' }]} numberOfLines={2}>
                            {item.away_team}
                        </Text>
                    </View>
                </View>

                {/* Prediction Result */}
                {sport === 'football' ? (
                    <View style={{ marginTop: 20, flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}>
                        <View style={{ flex: 1, padding: 8, alignItems: 'center', borderRadius: 8, borderWidth: 1, borderColor: (item.prediction === '1' || item.prediction === item.home_team) ? colors.accent : colors.border, backgroundColor: (item.prediction === '1' || item.prediction === item.home_team) ? (isLightMode ? 'rgba(0,113,227,0.05)' : 'rgba(0,113,227,0.15)') : colors.bgMuted }}>
                            <Text style={{ fontSize: 11, color: colors.textSecondary, marginBottom: 4, textTransform: 'uppercase', fontWeight: 'bold' }}>Local</Text>
                            <Text style={{ fontSize: 16, fontWeight: 'bold', color: (item.prediction === '1' || item.prediction === item.home_team) ? colors.accent : colors.text }}>
                                {(item.probs?.home || 0).toFixed(0)}%
                            </Text>
                        </View>
                        <View style={{ flex: 1, padding: 8, alignItems: 'center', borderRadius: 8, borderWidth: 1, borderColor: (item.prediction === 'X' || item.prediction === 'Draw') ? colors.accent : colors.border, backgroundColor: (item.prediction === 'X' || item.prediction === 'Draw') ? (isLightMode ? 'rgba(0,113,227,0.05)' : 'rgba(0,113,227,0.15)') : colors.bgMuted }}>
                            <Text style={{ fontSize: 11, color: colors.textSecondary, marginBottom: 4, textTransform: 'uppercase', fontWeight: 'bold' }}>Empate</Text>
                            <Text style={{ fontSize: 16, fontWeight: 'bold', color: (item.prediction === 'X' || item.prediction === 'Draw') ? colors.accent : colors.text }}>
                                {(item.probs?.draw || 0).toFixed(0)}%
                            </Text>
                        </View>
                        <View style={{ flex: 1, padding: 8, alignItems: 'center', borderRadius: 8, borderWidth: 1, borderColor: (item.prediction === '2' || item.prediction === item.away_team) ? colors.accent : colors.border, backgroundColor: (item.prediction === '2' || item.prediction === item.away_team) ? (isLightMode ? 'rgba(0,113,227,0.05)' : 'rgba(0,113,227,0.15)') : colors.bgMuted }}>
                            <Text style={{ fontSize: 11, color: colors.textSecondary, marginBottom: 4, textTransform: 'uppercase', fontWeight: 'bold' }}>Visita</Text>
                            <Text style={{ fontSize: 16, fontWeight: 'bold', color: (item.prediction === '2' || item.prediction === item.away_team) ? colors.accent : colors.text }}>
                                {(item.probs?.away || 0).toFixed(0)}%
                            </Text>
                        </View>
                    </View>

                ) : (
                    <View style={[styles.resultBox, { backgroundColor: colors.bgMuted }]}>
                        <Text style={[styles.winnerName, { color: colors.accent }]}>{item.winner}</Text>
                        <Text style={[styles.probability, { color: colors.text }]}>
                            {(item.win_probability || 0).toFixed(1)}%
                        </Text>
                        <Text style={[styles.probLabel, { color: colors.textSecondary }]}>Probabilidad</Text>
                    </View>
                )}

                {/* Meta Tags */}
                <View style={[styles.metaRow, { marginTop: sport === 'football' ? 12 : 0 }]}>
                    {sport === 'football' ? (
                        <View style={[styles.metaTag, { backgroundColor: colors.bgMuted }]}>
                            <Text style={[styles.metaText, { color: colors.textSecondary }]}>
                                Pronóstico: <Text style={{ color: colors.accent, fontWeight: 'bold' }}>{item.prediction}</Text>
                            </Text>
                        </View>
                    ) : (
                        item.under_over && (
                            <View style={[styles.metaTag, { backgroundColor: colors.bgMuted }]}>
                                <Text style={[styles.metaText, { color: colors.textSecondary }]}>
                                    {item.under_over} {item.ou_line || ''}
                                </Text>
                            </View>
                        )
                    )}
                    {item.ev_score != null && item.ev_score > 0 && (
                        <View style={[styles.metaTag, { backgroundColor: colors.successLight }]}>
                            <Text style={[styles.metaText, { color: colors.success }]}>
                                +EV {item.ev_score.toFixed(1)}
                            </Text>
                        </View>
                    )}
                    {item.game_status && (
                        <View style={[styles.metaTag, {
                            backgroundColor: item.game_status === 'WIN' ? colors.successLight
                                : item.game_status === 'LOSS' ? colors.dangerLight : colors.warningLight
                        }]}>
                            <Text style={[styles.metaText, {
                                color: item.game_status === 'WIN' ? colors.success
                                    : item.game_status === 'LOSS' ? colors.danger : colors.warning
                            }]}>
                                {item.game_status === 'WIN' ? '✓ Ganada' : item.game_status === 'LOSS' ? '✗ Perdida' : '⏳ Pendiente'}
                            </Text>
                        </View>
                    )}
                </View>
            </Animated.View>
        );
    };

    return (
        <View style={[styles.container, { backgroundColor: colors.bg }]}>
            <FlatList
                data={predictions}
                keyExtractor={(_, i) => i.toString()}
                renderItem={renderCard}
                contentContainerStyle={styles.list}
                showsVerticalScrollIndicator={false}
                refreshControl={
                    <RefreshControl
                        refreshing={refreshing}
                        onRefresh={() => fetchData(true)}
                        tintColor={colors.accent}
                        colors={[colors.accent]}
                    />
                }
                ListHeaderComponent={
                    <View style={styles.headerInfo}>
                        <Text style={[styles.sectionTitle, { color: colors.text }]}>
                            {sport === 'nba' ? 'Partidos de Hoy' : 'Partidos de Futbol'}
                        </Text>
                        {dateStr ? (
                            <Text style={[styles.dateLabel, { color: colors.textSecondary }]}>{dateStr}</Text>
                        ) : null}
                        {status === 'pending_github_actions' && (
                            <View style={[styles.pendingBanner, { backgroundColor: colors.warningLight }]}>
                                <Text style={[styles.pendingText, { color: colors.warning }]}>
                                    Las predicciones se estan generando. Vuelve pronto.
                                </Text>
                            </View>
                        )}
                    </View>
                }
                ListEmptyComponent={
                    <View style={styles.emptyState}>
                        <Text style={{ fontSize: 48, marginBottom: 8 }}>
                            {sport === 'nba' ? '🏀' : '⚽'}
                        </Text>
                        <Text style={[styles.emptyText, { color: colors.textSecondary }]}>
                            No hay partidos disponibles
                        </Text>
                    </View>
                }
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1 },
    center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
    loadText: { marginTop: 12, fontSize: 14 },
    errorText: { fontSize: 15, textAlign: 'center', marginBottom: 16 },
    retryBtn: { paddingHorizontal: 24, paddingVertical: 12, borderRadius: 12 },
    retryText: { color: '#fff', fontWeight: '600', fontSize: 14 },
    list: { padding: 16, paddingBottom: 100 },
    headerInfo: { marginBottom: 12 },
    sectionTitle: { fontSize: 22, fontWeight: '700' },
    dateLabel: { fontSize: 13, marginTop: 4 },
    pendingBanner: { padding: 12, borderRadius: 12, marginTop: 12 },
    pendingText: { fontSize: 13, fontWeight: '500', textAlign: 'center' },
    card: {
        borderRadius: 24,
        padding: 20,
        marginBottom: 14,
        borderWidth: 1,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.08,
        shadowRadius: 12,
        elevation: 3,
    },
    matchHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 14,
    },
    teamBox: { flex: 1, alignItems: 'center' },
    teamLogo: { width: 44, height: 44, marginBottom: 6 },
    teamName: { fontSize: 13, fontWeight: '600', textAlign: 'center' },
    vsBadge: { paddingHorizontal: 12, paddingVertical: 4, borderRadius: 10, marginHorizontal: 8 },
    vsText: { fontSize: 11, fontWeight: '700' },
    resultBox: { borderRadius: 16, padding: 16, alignItems: 'center', marginBottom: 10 },
    winnerName: { fontSize: 14, fontWeight: '700', marginBottom: 2 },
    probability: { fontSize: 28, fontWeight: '800' },
    probLabel: { fontSize: 11, marginTop: 2 },
    metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
    metaTag: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8 },
    metaText: { fontSize: 11, fontWeight: '600' },
    emptyState: { alignItems: 'center', paddingTop: 60 },
    emptyText: { fontSize: 15 },
});
