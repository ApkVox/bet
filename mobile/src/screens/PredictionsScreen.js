import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
    StyleSheet, View, Text, FlatList, ActivityIndicator,
    RefreshControl, TouchableOpacity, Animated, Image, useColorScheme
} from 'react-native';
import { getPredictionsToday, getFootballPredictions } from '../api/api';
import { NBA_TEAM_LOGOS, spacing, fontSize, radius, cardShadow } from '../theme/theme';

function AnimatedCard({ children, index, style }) {
    const anim = useRef(new Animated.Value(0)).current;
    useEffect(() => {
        Animated.timing(anim, {
            toValue: 1,
            duration: 450,
            delay: index * 80,
            useNativeDriver: true,
        }).start();
    }, [anim, index]);

    return (
        <Animated.View style={[style, {
            opacity: anim,
            transform: [{ translateY: anim.interpolate({ inputRange: [0, 1], outputRange: [24, 0] }) },
                         { scale: anim.interpolate({ inputRange: [0, 1], outputRange: [0.97, 1] }) }],
        }]}>
            {children}
        </Animated.View>
    );
}

function ProbBar({ label, value, isHighlighted, colors }) {
    const barAnim = useRef(new Animated.Value(0)).current;
    useEffect(() => {
        Animated.timing(barAnim, { toValue: value, duration: 800, delay: 300, useNativeDriver: false }).start();
    }, [barAnim, value]);

    return (
        <View style={[styles.probItem, { borderColor: isHighlighted ? colors.accent : colors.border, backgroundColor: isHighlighted ? colors.accentGlow : 'transparent' }]}>
            <Text style={[styles.probLabel, { color: colors.textTertiary }]}>{label}</Text>
            <Text style={[styles.probValue, { color: isHighlighted ? colors.accent : colors.text }]}>{value.toFixed(0)}%</Text>
            <View style={[styles.probBarTrack, { backgroundColor: colors.border }]}>
                <Animated.View style={[styles.probBarFill, { backgroundColor: colors.accent, width: barAnim.interpolate({ inputRange: [0, 100], outputRange: ['0%', '100%'] }) }]} />
            </View>
        </View>
    );
}

export default function PredictionsScreen({ sport, colors }) {
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [predictions, setPredictions] = useState([]);
    const [dateStr, setDateStr] = useState('');
    const [status, setStatus] = useState('');
    const [error, setError] = useState(null);
    const colorScheme = useColorScheme();
    const isLightMode = colorScheme === 'light';

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
                <Text style={[styles.loadText, { color: colors.textSecondary }]}>Conectando con el servidor...</Text>
            </View>
        );
    }

    if (error) {
        return (
            <View style={[styles.center, { backgroundColor: colors.bg }]}>
                <Text style={{ fontSize: 48, marginBottom: spacing.md }}>{'\uD83D\uDCE1'}</Text>
                <Text style={[styles.errorText, { color: colors.danger }]}>{error}</Text>
                <TouchableOpacity style={[styles.retryBtn, { backgroundColor: colors.accent }]} onPress={() => fetchData()}>
                    <Text style={styles.retryText}>Reintentar</Text>
                </TouchableOpacity>
            </View>
        );
    }

    const renderCard = ({ item, index }) => {
        const leagueLogoUrl = sport === 'football'
            ? 'https://media.api-sports.io/football/leagues/39.png'
            : 'https://cdn.nba.com/logos/nba/nba-logoman-word-white.svg';

        const isHomeFavored = item.prediction === '1' || item.prediction === item.home_team;
        const isAwayFavored = item.prediction === '2' || item.prediction === item.away_team;
        const isDraw = item.prediction === 'Draw' || item.prediction === 'X';

        return (
            <AnimatedCard index={index} style={[styles.card, cardShadow, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
                <View style={[styles.leagueBadge, { borderBottomColor: colors.border }]}>
                    <Image
                        source={{ uri: leagueLogoUrl }}
                        style={{ width: sport === 'football' ? 18 : 32, height: 18, marginRight: spacing.sm, tintColor: sport === 'nba' ? (isLightMode ? '#000' : '#fff') : undefined }}
                        resizeMode="contain"
                    />
                    <Text style={[styles.leagueText, { color: colors.textTertiary }]}>
                        {sport === 'football' ? 'Premier League' : 'NBA'}
                    </Text>
                </View>

                <View style={styles.matchHeader}>
                    <View style={styles.teamBox}>
                        {item.home_logo ? (
                            <Image source={{ uri: item.home_logo }} style={styles.teamLogo} resizeMode="contain" />
                        ) : (
                            <View style={[styles.teamLogo, styles.teamLogoFallback, { backgroundColor: colors.bgMuted }]}>
                                <Text style={[styles.teamLogoFallbackText, { color: colors.textSecondary }]}>{item.home_team?.substring(0, 2)}</Text>
                            </View>
                        )}
                        <Text style={[styles.teamName, { color: isHomeFavored ? colors.accent : colors.text, fontWeight: isHomeFavored ? '800' : '600' }]} numberOfLines={2}>
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
                            <View style={[styles.teamLogo, styles.teamLogoFallback, { backgroundColor: colors.bgMuted }]}>
                                <Text style={[styles.teamLogoFallbackText, { color: colors.textSecondary }]}>{item.away_team?.substring(0, 2)}</Text>
                            </View>
                        )}
                        <Text style={[styles.teamName, { color: isAwayFavored ? colors.accent : colors.text, fontWeight: isAwayFavored ? '800' : '600' }]} numberOfLines={2}>
                            {item.away_team}
                        </Text>
                    </View>
                </View>

                {sport === 'football' ? (
                    <View style={styles.probRow}>
                        <ProbBar label="Local" value={item.probs?.home || 0} isHighlighted={isHomeFavored} colors={colors} />
                        <ProbBar label="Empate" value={item.probs?.draw || 0} isHighlighted={isDraw} colors={colors} />
                        <ProbBar label="Visita" value={item.probs?.away || 0} isHighlighted={isAwayFavored} colors={colors} />
                    </View>
                ) : (
                    <View style={[styles.resultBox, { backgroundColor: colors.bgMuted }]}>
                        <Text style={[styles.winnerName, { color: colors.accent }]}>{item.winner}</Text>
                        <Text style={[styles.probability, { color: colors.text }]}>{(item.win_probability || 0).toFixed(1)}%</Text>
                        <Text style={[styles.probLabelText, { color: colors.textSecondary }]}>Probabilidad</Text>
                    </View>
                )}

                <View style={styles.metaRow}>
                    {sport === 'football' ? (
                        <View style={[styles.footerBox, { borderColor: colors.border }]}>
                            <Text style={[styles.footerLabel, { color: colors.textTertiary }]}>Prediccion</Text>
                            <Text style={[styles.footerValue, { color: colors.accent }]}>
                                {isHomeFavored ? item.home_team : isAwayFavored ? item.away_team : 'Empate'}
                            </Text>
                        </View>
                    ) : (
                        <>
                            {item.ev_score != null && item.ev_score > 0 && (
                                <View style={[styles.metaTag, { backgroundColor: colors.successLight }]}>
                                    <Text style={[styles.metaText, { color: colors.success }]}>+EV {item.ev_score.toFixed(1)}</Text>
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
                                        {item.game_status === 'WIN' ? '\u2713 Ganada' : item.game_status === 'LOSS' ? '\u2717 Perdida' : '\u23F3 Pendiente'}
                                    </Text>
                                </View>
                            )}
                        </>
                    )}
                </View>
            </AnimatedCard>
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
                    <RefreshControl refreshing={refreshing} onRefresh={() => fetchData(true)} tintColor={colors.accent} colors={[colors.accent]} />
                }
                ListHeaderComponent={
                    <View style={styles.headerInfo}>
                        <Text style={[styles.sectionTitle, { color: colors.text }]}>
                            {sport === 'nba' ? 'Partidos de Hoy' : 'Partidos de Futbol'}
                        </Text>
                        {dateStr ? <Text style={[styles.dateLabel, { color: colors.textSecondary }]}>{dateStr}</Text> : null}
                        {status === 'pending_github_actions' && (
                            <View style={[styles.pendingBanner, { backgroundColor: colors.warningLight }]}>
                                <Text style={[styles.pendingText, { color: colors.warning }]}>Las predicciones se estan generando. Vuelve pronto.</Text>
                            </View>
                        )}
                    </View>
                }
                ListEmptyComponent={
                    <View style={styles.emptyState}>
                        <Text style={{ fontSize: 48, marginBottom: spacing.sm }}>{sport === 'nba' ? '\uD83C\uDFC0' : '\u26BD'}</Text>
                        <Text style={[styles.emptyText, { color: colors.textSecondary }]}>No hay partidos disponibles</Text>
                    </View>
                }
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1 },
    center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: spacing.lg },
    loadText: { marginTop: spacing.md, fontSize: fontSize.body },
    errorText: { fontSize: 15, textAlign: 'center', marginBottom: spacing.md },
    retryBtn: { paddingHorizontal: spacing.lg, paddingVertical: spacing.md, borderRadius: radius.md },
    retryText: { color: '#fff', fontWeight: '700', fontSize: fontSize.body },
    list: { padding: spacing.md, paddingBottom: 100 },
    headerInfo: { marginBottom: spacing.md },
    sectionTitle: { fontSize: fontSize.hero, fontWeight: '900', letterSpacing: -0.5 },
    dateLabel: { fontSize: fontSize.small, marginTop: spacing.xs },
    pendingBanner: { padding: spacing.md, borderRadius: radius.md, marginTop: spacing.md },
    pendingText: { fontSize: fontSize.small, fontWeight: '600', textAlign: 'center' },
    card: {
        borderRadius: radius.xl,
        padding: spacing.lg,
        marginBottom: spacing.md,
        borderWidth: 1,
    },
    leagueBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: spacing.md,
        paddingBottom: spacing.sm,
        borderBottomWidth: 1,
    },
    leagueText: { fontSize: fontSize.caption, textTransform: 'uppercase', fontWeight: '700', letterSpacing: 1 },
    matchHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: spacing.md,
    },
    teamBox: { flex: 1, alignItems: 'center', gap: spacing.sm },
    teamLogo: { width: 52, height: 52 },
    teamLogoFallback: { borderRadius: 26, justifyContent: 'center', alignItems: 'center' },
    teamLogoFallbackText: { fontWeight: '800', fontSize: fontSize.body },
    teamName: { fontSize: fontSize.small, textAlign: 'center', lineHeight: 16, maxWidth: 110 },
    vsBadge: { paddingHorizontal: spacing.md, paddingVertical: spacing.xs, borderRadius: radius.pill, marginHorizontal: spacing.sm },
    vsText: { fontSize: 10, fontWeight: '800', letterSpacing: 1 },
    probRow: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.lg },
    probItem: { flex: 1, padding: spacing.sm, alignItems: 'center', borderRadius: radius.sm, borderWidth: 1 },
    probLabel: { fontSize: 10, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: spacing.xs },
    probValue: { fontSize: 20, fontWeight: '800', letterSpacing: -0.5 },
    probBarTrack: { height: 3, borderRadius: 99, width: '100%', marginTop: spacing.sm, overflow: 'hidden' },
    probBarFill: { height: '100%', borderRadius: 99 },
    resultBox: { borderRadius: radius.lg, padding: spacing.md, alignItems: 'center', marginBottom: spacing.sm },
    winnerName: { fontSize: fontSize.body, fontWeight: '700', marginBottom: 2 },
    probability: { fontSize: 32, fontWeight: '900', letterSpacing: -1 },
    probLabelText: { fontSize: fontSize.caption, marginTop: 2, textTransform: 'uppercase', letterSpacing: 0.5 },
    metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.md },
    metaTag: { paddingHorizontal: spacing.md, paddingVertical: 6, borderRadius: radius.pill },
    metaText: { fontSize: fontSize.caption, fontWeight: '700' },
    footerBox: { flex: 1, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: spacing.md, borderRadius: radius.sm, borderWidth: 1 },
    footerLabel: { fontSize: fontSize.caption, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
    footerValue: { fontWeight: '800', fontSize: fontSize.body },
    emptyState: { alignItems: 'center', paddingTop: 80 },
    emptyText: { fontSize: 15, fontWeight: '500' },
});
