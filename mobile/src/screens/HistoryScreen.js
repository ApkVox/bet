import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
    StyleSheet, View, Text, SectionList, ActivityIndicator,
    RefreshControl, TouchableOpacity, Image, Animated, useColorScheme
} from 'react-native';
import { getHistoryFull, getFootballHistory } from '../api/api';
import { NBA_TEAM_LOGOS, spacing, fontSize, radius, cardShadow } from '../theme/theme';

function AnimatedCard({ children, index, style }) {
    const anim = useRef(new Animated.Value(0)).current;
    useEffect(() => {
        Animated.timing(anim, {
            toValue: 1,
            duration: 400,
            delay: index * 60,
            useNativeDriver: true,
        }).start();
    }, [anim, index]);

    return (
        <Animated.View style={[style, {
            opacity: anim,
            transform: [{ translateY: anim.interpolate({ inputRange: [0, 1], outputRange: [20, 0] }) }],
        }]}>
            {children}
        </Animated.View>
    );
}

function AnimatedStat({ value, color, label, labelColor }) {
    const anim = useRef(new Animated.Value(0)).current;
    useEffect(() => {
        Animated.timing(anim, { toValue: 1, duration: 600, delay: 200, useNativeDriver: true }).start();
    }, [anim]);

    return (
        <Animated.View style={[styles.statItem, { opacity: anim, transform: [{ translateY: anim.interpolate({ inputRange: [0, 1], outputRange: [10, 0] }) }] }]}>
            <Text style={[styles.statValue, { color }]}>{value}</Text>
            <Text style={[styles.statLabel, { color: labelColor }]}>{label}</Text>
        </Animated.View>
    );
}

export default function HistoryScreen({ sport, colors }) {
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [sections, setSections] = useState([]);
    const [filter, setFilter] = useState('all');
    const [error, setError] = useState(null);
    const [stats, setStats] = useState({ total: 0, wins: 0, losses: 0, pending: 0 });
    const colorScheme = useColorScheme();
    const isLightMode = colorScheme === 'light';

    const fetchData = useCallback(async (isRefresh = false) => {
        if (isRefresh) setRefreshing(true); else setLoading(true);
        setError(null);
        try {
            const result = sport === 'nba'
                ? await getHistoryFull(30)
                : await getFootballHistory(30);

            const rawHistory = result.history || [];
            const history = rawHistory.map(item => {
                let home_team = item.home_team || '';
                let away_team = item.away_team || '';
                if (!home_team && item.match) {
                    const parts = item.match.split(' vs ');
                    home_team = parts[0] || '';
                    away_team = parts[1] || '';
                }
                return {
                    ...item,
                    home_team,
                    away_team,
                    winner: item.winner || item.predicted_winner || '',
                    win_probability: item.win_probability != null ? item.win_probability : (item.probability != null ? item.probability : 0),
                };
            });

            const wins = history.filter(h => h.result === 'WIN').length;
            const losses = history.filter(h => h.result === 'LOSS').length;
            const pending = history.filter(h => !h.result || h.result === 'PENDING').length;
            setStats({ total: history.length, wins, losses, pending });

            const grouped = {};
            history.forEach(item => {
                const date = item.date || 'Sin fecha';
                if (!grouped[date]) grouped[date] = [];
                grouped[date].push(item);
            });

            const sectionData = Object.keys(grouped)
                .sort((a, b) => b.localeCompare(a))
                .map(date => ({ title: date, data: grouped[date] }));

            setSections(sectionData);
        } catch (err) {
            setError('No se pudo conectar al servidor.');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [sport]);

    useEffect(() => { fetchData(); }, [fetchData]);

    const filteredSections = sections.map(section => ({
        ...section,
        data: section.data.filter(item => {
            if (filter === 'all') return true;
            if (filter === 'win') return item.result === 'WIN';
            if (filter === 'loss') return item.result === 'LOSS';
            if (filter === 'pending') return !item.result || item.result === 'PENDING';
            return true;
        }),
    })).filter(s => s.data.length > 0);

    if (loading) {
        return (
            <View style={[styles.center, { backgroundColor: colors.bg }]}>
                <ActivityIndicator size="large" color={colors.accent} />
                <Text style={[styles.loadText, { color: colors.textSecondary }]}>Cargando historial...</Text>
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

    let cardIdx = 0;

    const renderItem = ({ item }) => {
        const isWin = item.result === 'WIN';
        const isLoss = item.result === 'LOSS';
        const isPending = !item.result || item.result === 'PENDING';
        const resultClass = isWin ? 'win' : isLoss ? 'loss' : 'pending';

        const leagueLogoUrl = sport === 'football'
            ? 'https://media.api-sports.io/football/leagues/39.png'
            : 'https://cdn.nba.com/logos/nba/nba-logoman-word-white.svg';

        const cardBorderColor = isWin ? 'rgba(52, 199, 89, 0.2)' : isLoss ? 'rgba(255, 69, 58, 0.2)' : colors.border;
        const leftAccent = isWin ? colors.success : isLoss ? colors.danger : colors.warning;

        const isHomeFavored = item.prediction === '1' || item.prediction === item.home_team;
        const isAwayFavored = item.prediction === '2' || item.prediction === item.away_team;

        const winner = item.winner || item.predicted_winner || item.prediction || '-';
        const prob = item.prob_model ? (item.prob_model * 100).toFixed(0) :
            (item.probs?.home && isHomeFavored ? item.probs.home.toFixed(0) :
                (item.probs?.away && isAwayFavored ? item.probs.away.toFixed(0) :
                    (item.probs?.draw && (item.prediction === 'Draw' || item.prediction === 'X') ? item.probs.draw.toFixed(0) :
                        (item.win_probability || item.probability || 0))));

        const resultColor = isWin ? colors.success : isLoss ? colors.danger : colors.accent;
        const currentIdx = cardIdx++;

        return (
            <AnimatedCard index={currentIdx} style={[styles.card, cardShadow, { backgroundColor: colors.bgCard, borderColor: cardBorderColor }]}>
                <View style={[styles.leftAccent, { backgroundColor: leftAccent }]} />

                <View style={[styles.leagueBadge, { borderBottomColor: colors.border }]}>
                    <Image
                        source={{ uri: leagueLogoUrl }}
                        style={{ width: sport === 'football' ? 18 : 32, height: 18, marginRight: spacing.sm, tintColor: sport === 'nba' ? (isLightMode ? '#000' : '#fff') : undefined }}
                        resizeMode="contain"
                    />
                    <Text style={[styles.leagueText, { color: colors.textTertiary }]}>{sport === 'football' ? 'Premier League' : 'NBA'}</Text>
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
                        <Text style={[styles.teamName, { color: isHomeFavored ? colors.accent : colors.text }]} numberOfLines={2}>{item.home_team || 'N/A'}</Text>
                        {item.home_score != null && <Text style={[styles.scoreText, { color: colors.text }]}>{item.home_score}</Text>}
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
                        <Text style={[styles.teamName, { color: isAwayFavored ? colors.accent : colors.text }]} numberOfLines={2}>{item.away_team || 'N/A'}</Text>
                        {item.away_score != null && <Text style={[styles.scoreText, { color: colors.text }]}>{item.away_score}</Text>}
                    </View>
                </View>

                <View style={[styles.resultBox, { backgroundColor: isWin ? colors.successLight : isLoss ? colors.dangerLight : colors.bgMuted }]}>
                    <Text style={[styles.winnerName, { color: resultColor }]}>{winner}</Text>
                    <Text style={[styles.probability, { color: colors.text }]}>{prob}%</Text>
                    <Text style={[styles.probLabelText, { color: colors.textSecondary }]}>Probabilidad</Text>
                </View>

                <View style={styles.metaRow}>
                    <View style={[styles.resultBadge, { backgroundColor: isWin ? colors.successLight : isLoss ? colors.dangerLight : colors.warningLight }]}>
                        <Text style={[styles.resultBadgeText, { color: isWin ? colors.success : isLoss ? colors.danger : colors.warning }]}>
                            {isWin ? '\u2713 Ganada' : isLoss ? '\u2717 Perdida' : '\u23F3 Pendiente'}
                        </Text>
                    </View>
                    {item.ev != null && item.ev > 0 && (
                        <View style={[styles.metaTag, { backgroundColor: colors.successLight }]}>
                            <Text style={[styles.metaText, { color: colors.success }]}>+EV {item.ev.toFixed(1)}</Text>
                        </View>
                    )}
                </View>
            </AnimatedCard>
        );
    };

    const filters = [
        { key: 'all', label: `Todas (${stats.total})` },
        { key: 'win', label: `Ganadas (${stats.wins})` },
        { key: 'loss', label: `Perdidas (${stats.losses})` },
        { key: 'pending', label: `Pend. (${stats.pending})` },
    ];

    const winRate = stats.wins + stats.losses > 0 ? ((stats.wins / (stats.wins + stats.losses)) * 100).toFixed(1) : '0';

    return (
        <View style={[styles.container, { backgroundColor: colors.bg }]}>
            <SectionList
                sections={filteredSections}
                keyExtractor={(_, i) => i.toString()}
                renderItem={renderItem}
                renderSectionHeader={({ section }) => (
                    <View style={[styles.sectionHeader, { backgroundColor: colors.bg }]}>
                        <Text style={[styles.sectionTitle, { color: colors.textTertiary }]}>{section.title}</Text>
                    </View>
                )}
                contentContainerStyle={styles.list}
                showsVerticalScrollIndicator={false}
                stickySectionHeadersEnabled
                refreshControl={
                    <RefreshControl refreshing={refreshing} onRefresh={() => fetchData(true)} tintColor={colors.accent} colors={[colors.accent]} />
                }
                ListHeaderComponent={
                    <View style={styles.header}>
                        <Text style={[styles.mainTitle, { color: colors.text }]}>Historial</Text>

                        <View style={[styles.statsRow, cardShadow, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
                            <AnimatedStat value={`${winRate}%`} color={colors.accent} label="Acierto" labelColor={colors.textSecondary} />
                            <View style={[styles.statDivider, { backgroundColor: colors.border }]} />
                            <AnimatedStat value={stats.wins} color={colors.success} label="Ganadas" labelColor={colors.textSecondary} />
                            <View style={[styles.statDivider, { backgroundColor: colors.border }]} />
                            <AnimatedStat value={stats.losses} color={colors.danger} label="Perdidas" labelColor={colors.textSecondary} />
                            <View style={[styles.statDivider, { backgroundColor: colors.border }]} />
                            <AnimatedStat value={stats.pending} color={colors.warning} label="Pend." labelColor={colors.textSecondary} />
                        </View>

                        <View style={styles.filterRow}>
                            {filters.map(f => (
                                <TouchableOpacity
                                    key={f.key}
                                    style={[
                                        styles.filterBtn,
                                        { borderColor: colors.border, backgroundColor: colors.bgCard },
                                        filter === f.key && { backgroundColor: colors.accent, borderColor: colors.accent },
                                    ]}
                                    onPress={() => { setFilter(f.key); cardIdx = 0; }}
                                    activeOpacity={0.7}
                                >
                                    <Text style={[styles.filterText, { color: colors.textSecondary }, filter === f.key && { color: '#fff' }]}>{f.label}</Text>
                                </TouchableOpacity>
                            ))}
                        </View>
                    </View>
                }
                ListEmptyComponent={
                    <View style={styles.emptyState}>
                        <Text style={{ fontSize: 48, marginBottom: spacing.sm }}>{'\uD83D\uDCCB'}</Text>
                        <Text style={[styles.emptyText, { color: colors.textSecondary }]}>No hay resultados para este filtro</Text>
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
    retryText: { color: '#fff', fontWeight: '700' },
    list: { padding: spacing.md, paddingBottom: 100 },
    header: { marginBottom: spacing.sm },
    mainTitle: { fontSize: fontSize.hero, fontWeight: '900', letterSpacing: -0.5, marginBottom: spacing.md },
    statsRow: {
        flexDirection: 'row',
        borderRadius: radius.lg,
        padding: spacing.md,
        marginBottom: spacing.md,
        borderWidth: 1,
        alignItems: 'center',
    },
    statItem: { flex: 1, alignItems: 'center' },
    statValue: { fontSize: 22, fontWeight: '900' },
    statLabel: { fontSize: 10, marginTop: 2, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
    statDivider: { width: 1, height: 32 },
    filterRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.sm, flexWrap: 'wrap' },
    filterBtn: { paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderRadius: radius.pill, borderWidth: 1 },
    filterText: { fontSize: fontSize.small, fontWeight: '700' },
    sectionHeader: { paddingVertical: spacing.sm },
    sectionTitle: { fontSize: fontSize.small, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
    card: {
        borderRadius: radius.xl,
        padding: spacing.lg,
        marginBottom: spacing.md,
        borderWidth: 1,
        overflow: 'hidden',
        position: 'relative',
    },
    leftAccent: {
        position: 'absolute',
        left: 0,
        top: 0,
        bottom: 0,
        width: 3,
        borderTopLeftRadius: radius.xl,
        borderBottomLeftRadius: radius.xl,
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
    teamBox: { flex: 1, alignItems: 'center', gap: spacing.xs },
    teamLogo: { width: 44, height: 44 },
    teamLogoFallback: { borderRadius: 22, justifyContent: 'center', alignItems: 'center' },
    teamLogoFallbackText: { fontWeight: '800', fontSize: fontSize.body },
    teamName: { fontSize: fontSize.small, fontWeight: '700', textAlign: 'center', lineHeight: 16 },
    vsBadge: { paddingHorizontal: spacing.md, paddingVertical: spacing.xs, borderRadius: radius.pill, marginHorizontal: spacing.sm },
    vsText: { fontSize: 10, fontWeight: '800', letterSpacing: 1 },
    resultBox: { borderRadius: radius.lg, padding: spacing.md, alignItems: 'center', marginBottom: spacing.sm },
    winnerName: { fontSize: fontSize.body, fontWeight: '700', marginBottom: 2 },
    probability: { fontSize: 26, fontWeight: '900', letterSpacing: -0.5 },
    probLabelText: { fontSize: fontSize.caption, marginTop: 2, textTransform: 'uppercase', letterSpacing: 0.5 },
    metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.sm },
    resultBadge: { paddingHorizontal: spacing.md, paddingVertical: 6, borderRadius: radius.pill },
    resultBadgeText: { fontSize: fontSize.caption, fontWeight: '700' },
    metaTag: { paddingHorizontal: spacing.md, paddingVertical: 6, borderRadius: radius.pill },
    metaText: { fontSize: fontSize.caption, fontWeight: '700' },
    scoreText: { fontSize: 18, fontWeight: '900', marginTop: spacing.xs },
    emptyState: { alignItems: 'center', paddingTop: 80 },
    emptyText: { fontSize: 15, fontWeight: '500' },
});
