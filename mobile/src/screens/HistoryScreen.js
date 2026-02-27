import React, { useEffect, useState, useCallback } from 'react';
import {
    StyleSheet, View, Text, SectionList, ActivityIndicator,
    RefreshControl, TouchableOpacity, Image
} from 'react-native';
import { getHistoryFull, getFootballHistory } from '../api/api';
import { NBA_TEAM_LOGOS } from '../theme/theme';

export default function HistoryScreen({ sport, colors }) {
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [sections, setSections] = useState([]);
    const [filter, setFilter] = useState('all');
    const [error, setError] = useState(null);
    const [stats, setStats] = useState({ total: 0, wins: 0, losses: 0, pending: 0 });

    const fetchData = useCallback(async (isRefresh = false) => {
        if (isRefresh) setRefreshing(true); else setLoading(true);
        setError(null);
        try {
            const result = sport === 'nba'
                ? await getHistoryFull(30)
                : await getFootballHistory(30);

            const rawHistory = result.history || [];

            // Normalize fields: API returns `match`, `predicted_winner`, `probability`
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

            // Compute stats
            const wins = history.filter(h => h.result === 'WIN').length;
            const losses = history.filter(h => h.result === 'LOSS').length;
            const pending = history.filter(h => !h.result || h.result === 'PENDING').length;
            setStats({ total: history.length, wins, losses, pending });

            // Group by date
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
                <Text style={[styles.loadText, { color: colors.textSecondary }]}>
                    Cargando historial...
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
        if (!teamName) return { uri: `https://ui-avatars.com/api/?name=%3F&background=555&color=fff&rounded=true&bold=true&size=100` };
        if (sport === 'nba') {
            const url = NBA_TEAM_LOGOS[teamName];
            if (url) return { uri: url };
            return { uri: `https://ui-avatars.com/api/?name=${encodeURIComponent(teamName.substring(0, 2))}&background=1d428a&color=fff&rounded=true&bold=true&size=100` };
        } else {
            return { uri: `https://ui-avatars.com/api/?name=${encodeURIComponent(teamName.substring(0, 2))}&background=2d6a4f&color=fff&rounded=true&bold=true&size=100` };
        }
    };

    const renderItem = ({ item }) => {
        const isWin = item.result === 'WIN';
        const isLoss = item.result === 'LOSS';
        const isPending = !item.result || item.result === 'PENDING';

        const leagueLogoUrl = sport === 'football'
            ? 'https://media.api-sports.io/football/leagues/39.png'
            : 'https://cdn.nba.com/logos/nba/nba-logoman-word-white.svg';

        const colorScheme = useColorScheme();
        const isLightMode = colorScheme === 'light';

        return (
            <View style={[styles.card, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
                {/* League Badge Header */}
                <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8, paddingBottom: 8, borderBottomWidth: 1, borderBottomColor: colors.border }}>
                    <Image
                        source={{ uri: leagueLogoUrl }}
                        style={{ width: sport === 'football' ? 16 : 30, height: 16, marginRight: 6, tintColor: sport === 'nba' ? (isLightMode ? '#000' : '#fff') : undefined }}
                        resizeMode="contain"
                    />
                    <Text style={{ fontSize: 10, color: colors.textTertiary, textTransform: 'uppercase', fontWeight: 'bold' }}>
                        {sport === 'football' ? 'Premier League' : 'NBA'}
                    </Text>
                </View>

                <View style={styles.cardContent}>
                    <View style={styles.matchInfo}>
                        <View style={styles.teamRow}>
                            <Image source={item.home_logo ? { uri: item.home_logo } : getTeamLogo(item.home_team)} style={styles.teamLogoSmall} resizeMode="contain" />
                            <Text style={[styles.matchTeams, { color: colors.text }]} numberOfLines={1}>
                                {item.home_team || 'N/A'}
                            </Text>
                            {(item.home_score != null) && (
                                <Text style={[styles.scoreText, { color: colors.text }]}>{item.home_score}</Text>
                            )}
                        </View>
                        <View style={styles.teamRow}>
                            <Image source={item.away_logo ? { uri: item.away_logo } : getTeamLogo(item.away_team)} style={styles.teamLogoSmall} resizeMode="contain" />
                            <Text style={[styles.matchTeams, { color: colors.text }]} numberOfLines={1}>
                                {item.away_team || 'N/A'}
                            </Text>
                            {(item.away_score != null) && (
                                <Text style={[styles.scoreText, { color: colors.text }]}>{item.away_score}</Text>
                            )}
                        </View>

                        <Text style={[styles.predLabel, { color: colors.textSecondary }]}>
                            Pred: {item.winner || 'N/A'} ({(item.win_probability || 0).toFixed(1)}%)
                        </Text>
                    </View>
                    <View style={[
                        styles.resultBadge,
                        { backgroundColor: isWin ? colors.successLight : isLoss ? colors.dangerLight : colors.warningLight }
                    ]}>
                        <Text style={[
                            styles.resultText,
                            { color: isWin ? colors.success : isLoss ? colors.danger : colors.warning }
                        ]}>
                            {isWin ? '✓' : isLoss ? '✗' : '⏳'} {isWin ? 'Ganada' : isLoss ? 'Perdida' : 'Pendiente'}
                        </Text>
                    </View>
                </View>
            </View>
        );
    };

    const filters = [
        { key: 'all', label: `Todas (${stats.total})` },
        { key: 'win', label: `Ganadas (${stats.wins})` },
        { key: 'loss', label: `Perdidas (${stats.losses})` },
        { key: 'pending', label: `Pendientes (${stats.pending})` },
    ];

    const winRate = stats.wins + stats.losses > 0
        ? ((stats.wins / (stats.wins + stats.losses)) * 100).toFixed(1)
        : '0';

    return (
        <View style={[styles.container, { backgroundColor: colors.bg }]}>
            <SectionList
                sections={filteredSections}
                keyExtractor={(_, i) => i.toString()}
                renderItem={renderItem}
                renderSectionHeader={({ section }) => (
                    <View style={[styles.sectionHeader, { backgroundColor: colors.bg }]}>
                        <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
                            {section.title}
                        </Text>
                    </View>
                )}
                contentContainerStyle={styles.list}
                showsVerticalScrollIndicator={false}
                stickySectionHeadersEnabled
                refreshControl={
                    <RefreshControl
                        refreshing={refreshing}
                        onRefresh={() => fetchData(true)}
                        tintColor={colors.accent}
                        colors={[colors.accent]}
                    />
                }
                ListHeaderComponent={
                    <View style={styles.header}>
                        <Text style={[styles.mainTitle, { color: colors.text }]}>Historial</Text>

                        {/* Stats Banner */}
                        <View style={[styles.statsRow, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
                            <View style={styles.statItem}>
                                <Text style={[styles.statValue, { color: colors.accent }]}>{winRate}%</Text>
                                <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Acierto</Text>
                            </View>
                            <View style={[styles.statDivider, { backgroundColor: colors.border }]} />
                            <View style={styles.statItem}>
                                <Text style={[styles.statValue, { color: colors.success }]}>{stats.wins}</Text>
                                <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Ganadas</Text>
                            </View>
                            <View style={[styles.statDivider, { backgroundColor: colors.border }]} />
                            <View style={styles.statItem}>
                                <Text style={[styles.statValue, { color: colors.danger }]}>{stats.losses}</Text>
                                <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Perdidas</Text>
                            </View>
                            <View style={[styles.statDivider, { backgroundColor: colors.border }]} />
                            <View style={styles.statItem}>
                                <Text style={[styles.statValue, { color: colors.warning }]}>{stats.pending}</Text>
                                <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Pend.</Text>
                            </View>
                        </View>

                        {/* Filters */}
                        <View style={styles.filterRow}>
                            {filters.map(f => (
                                <TouchableOpacity
                                    key={f.key}
                                    style={[
                                        styles.filterBtn,
                                        { borderColor: colors.border, backgroundColor: colors.bgCard },
                                        filter === f.key && { backgroundColor: colors.accent, borderColor: colors.accent },
                                    ]}
                                    onPress={() => setFilter(f.key)}
                                >
                                    <Text style={[
                                        styles.filterText,
                                        { color: colors.textSecondary },
                                        filter === f.key && { color: '#fff' },
                                    ]}>{f.label}</Text>
                                </TouchableOpacity>
                            ))}
                        </View>
                    </View>
                }
                ListEmptyComponent={
                    <View style={styles.emptyState}>
                        <Text style={{ fontSize: 48, marginBottom: 8 }}>📋</Text>
                        <Text style={[styles.emptyText, { color: colors.textSecondary }]}>
                            No hay resultados para este filtro
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
    retryText: { color: '#fff', fontWeight: '600' },
    list: { padding: 16, paddingBottom: 100 },
    header: { marginBottom: 8 },
    mainTitle: { fontSize: 22, fontWeight: '700', marginBottom: 12 },
    statsRow: {
        flexDirection: 'row',
        borderRadius: 16,
        padding: 14,
        marginBottom: 12,
        borderWidth: 1,
        alignItems: 'center',
    },
    statItem: { flex: 1, alignItems: 'center' },
    statValue: { fontSize: 20, fontWeight: '800' },
    statLabel: { fontSize: 10, marginTop: 2 },
    statDivider: { width: 1, height: 30 },
    filterRow: { flexDirection: 'row', gap: 6, marginBottom: 8, flexWrap: 'wrap' },
    filterBtn: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 10, borderWidth: 1 },
    filterText: { fontSize: 12, fontWeight: '600' },
    sectionHeader: { paddingVertical: 8 },
    sectionTitle: { fontSize: 14, fontWeight: '600' },
    card: {
        borderRadius: 16,
        padding: 14,
        marginBottom: 8,
        borderWidth: 1,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.04,
        shadowRadius: 6,
        elevation: 2,
    },
    cardContent: { flexDirection: 'row', alignItems: 'center' },
    matchInfo: { flex: 1, paddingRight: 10 },
    teamRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
    teamLogoSmall: { width: 20, height: 20, marginRight: 8 },
    matchTeams: { flex: 1, fontSize: 13, fontWeight: '600' },
    scoreText: { fontSize: 13, fontWeight: '700', marginLeft: 8 },
    predLabel: { fontSize: 12, marginTop: 4 },
    resultBadge: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8 },
    resultText: { fontSize: 11, fontWeight: '700' },
    emptyState: { alignItems: 'center', paddingTop: 60 },
    emptyText: { fontSize: 15 },
});
