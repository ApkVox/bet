import axios from 'axios';

const API_BASE_URL = 'https://bet-7b8l.onrender.com';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 15000,
    headers: { 'Content-Type': 'application/json' },
});

export const checkHealth = async () => {
    const { data } = await apiClient.get('/api/health');
    return data;
};

export const getPredictionsToday = async () => {
    const { data } = await apiClient.get('/predict-today');
    return data;
};

export const getFootballPredictions = async () => {
    const { data } = await apiClient.get('/predict-football');
    return data;
};

export const getHistoryFull = async (days = 30) => {
    const { data } = await apiClient.get(`/history/full?days=${days}`);
    return data;
};

export const getFootballHistory = async (days = 30) => {
    const { data } = await apiClient.get(`/history/football?days=${days}`);
    return data;
};

export default apiClient;
