import axios, { AxiosInstance } from 'axios';
import { API_BASE_URL } from '../config';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export function useApi(): AxiosInstance {
  return api;
} 