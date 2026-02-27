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
            return { uri: NBA_TEAM_LOGOS[teamName] || 'https://cdn.nba.com/logos/nba/1610616834/primary/L/logo.svg' };
        } else {
            // URL genérica de fútbol basada en el ID del equipo no la tenemos, pero podemos usar el nombre en un placeholder
            // Lo ideal sería que la API enviara el logo o el ID, pero como usamos sbrscrape (Scraped Data) para fútbol en la web,
            // la web de La Fija obtiene el ID del equipo y carga desde media.api-sports.io
            // Pero en la respuesta actual de la API no tenemos el logo_url directamente a menos que la web haga el mapeo.
            // Voy a crear una función que imite la lógica de la web (o provea un fallback visual).
            // (En la versión web, para la predicción del día usa una clase CSS o un logo dummy si no tiene el ID).
            return { uri: `https://ui-avatars.com/api/?name=${encodeURIComponent(teamName)}&background=random&color=fff&rounded=true&bold=true` };
        }
    };

    const renderCard = ({ item, index }) => (
        <Animated.View style={[styles.card, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
            {/* Match Header */}
            <View style={styles.matchHeader}>
                <View style={styles.teamBox}>
                    <Image source={item.home_logo ? { uri: item.home_logo } : getTeamLogo(item.home_team)} style={styles.teamLogo} resizeMode="contain" />
                    <Text style={[styles.teamName, { color: colors.text }]} numberOfLines={2}>
                        {item.home_team}
                    </Text>
                </View>
                <View style={[styles.vsBadge, { backgroundColor: colors.bgMuted }]}>
                    <Text style={[styles.vsText, { color: colors.textTertiary }]}>VS</Text>
                </View>
                <View style={styles.teamBox}>
                    <Image source={item.away_logo ? { uri: item.away_logo } : getTeamLogo(item.away_team)} style={styles.teamLogo} resizeMode="contain" />
                    <Text style={[styles.teamName, { color: colors.text }]} numberOfLines={2}>
                        {item.away_team}
                    </Text>
                </View>
            </View>

            {/* Prediction Result */}
            <View style={[styles.resultBox, { backgroundColor: colors.bgMuted }]}>
                <Text style={[styles.winnerName, { color: colors.accent }]}>{item.winner}</Text>
                <Text style={[styles.probability, { color: colors.text }]}>
                    {(item.win_probability || 0).toFixed(1)}%
                </Text>
                <Text style={[styles.probLabel, { color: colors.textSecondary }]}>Probabilidad</Text>
            </View>

            {/* Meta Tags */}
            <View style={styles.metaRow}>
                {item.under_over && (
                    <View style={[styles.metaTag, { backgroundColor: colors.bgMuted }]}>
                        <Text style={[styles.metaText, { color: colors.textSecondary }]}>
                            {item.under_over} {item.ou_line || ''}
                        </Text>
                    </View>
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
