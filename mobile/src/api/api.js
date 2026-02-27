import axios from 'axios';

const API_BASE_URL = 'https://bet-7b8l.onrender.com';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const getPredictionsToday = async () => {
    try {
        const response = await apiClient.get('/predict-today');
        return response.data;
    } catch (error) {
        console.error('Error fetching today predictions:', error);
        throw error;
    }
};

export const getHistoryFull = async (days = 30) => {
    try {
        const response = await apiClient.get(`/history/full?days=${days}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching history:', error);
        throw error;
    }
};

export const getFootballPredictions = async () => {
    try {
        const response = await apiClient.get('/predict-football');
        return response.data;
    } catch (error) {
        console.error('Error fetching football predictions:', error);
        throw error;
    }
};

export const getFootballHistory = async (days = 30) => {
    try {
        const response = await apiClient.get(`/history/football?days=${days}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching football history:', error);
        throw error;
    }
};

export default apiClient;
