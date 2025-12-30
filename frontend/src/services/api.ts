import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface FactItem {
  fact_id: string;
  case_id: string;
  fact: string;
  source: string;
  status: 'pending' | 'approved' | 'rejected' | 'locked';
  timestamp: string;
  edited_at?: string;
}

export interface ArgumentItem {
  argument_id: string;
  case_id: string;
  argument: string;
  fact_ids: string[];
  status: 'pending' | 'approved' | 'rejected' | 'locked';
  timestamp: string;
  edited_at?: string;
}

export interface PredictionHistoryItem {
  index: number;
  prediction: string;
  confidence: number;
  timestamp: string;
  based_on_facts: string[];
  based_on_arguments: string[];
}

export interface CaseInfo {
  case_id: string;
  case_name: string;
  status: string;
  created_at: string;
  updated_at: string;
  fact_count: number;
  argument_count: number;
  current_prediction?: string;
}

export interface StateFlags {
  facts_edited: boolean;
  arguments_edited: boolean;
  restore_prediction_index?: number;
  recompute_prediction: boolean;
}

// Case endpoints
export const caseAPI = {
  list: async () => {
    const response = await apiClient.get<CaseInfo[]>('/cases');
    return response.data;
  },
  get: async (caseId: string) => {
    const response = await apiClient.get<CaseInfo>(`/cases/${caseId}`);
    return response.data;
  },
  create: async (caseData: { case_name: string; case_type?: string }) => {
    const response = await apiClient.post<CaseInfo>('/cases', caseData);
    return response.data;
  },
  delete: async (caseId: string) => {
    await apiClient.delete(`/cases/${caseId}`);
  },
};

// Fact endpoints
export const factAPI = {
  list: async (caseId: string) => {
    const response = await apiClient.get<FactItem[]>(`/cases/${caseId}/facts`);
    return response.data;
  },
  get: async (caseId: string, factId: string) => {
    const response = await apiClient.get<FactItem>(`/cases/${caseId}/facts/${factId}`);
    return response.data;
  },
  create: async (caseId: string, factData: { fact: string; source: string }) => {
    const response = await apiClient.post<FactItem>(`/cases/${caseId}/facts`, factData);
    return response.data;
  },
  update: async (caseId: string, factId: string, factData: { fact: string; source: string }) => {
    const response = await apiClient.put<FactItem>(`/cases/${caseId}/facts/${factId}`, factData);
    return response.data;
  },
  approve: async (caseId: string, factId: string) => {
    const response = await apiClient.post(`/cases/${caseId}/facts/${factId}/approve`);
    return response.data;
  },
  reject: async (caseId: string, factId: string) => {
    const response = await apiClient.post(`/cases/${caseId}/facts/${factId}/reject`);
    return response.data;
  },
  lock: async (caseId: string, factId: string) => {
    const response = await apiClient.post(`/cases/${caseId}/facts/${factId}/lock`);
    return response.data;
  },
};

// Argument endpoints
export const argumentAPI = {
  list: async (caseId: string) => {
    const response = await apiClient.get<ArgumentItem[]>(`/cases/${caseId}/arguments`);
    return response.data;
  },
  get: async (caseId: string, argumentId: string) => {
    const response = await apiClient.get<ArgumentItem>(`/cases/${caseId}/arguments/${argumentId}`);
    return response.data;
  },
  create: async (caseId: string, argData: { argument: string; fact_ids: string[] }) => {
    const response = await apiClient.post<ArgumentItem>(`/cases/${caseId}/arguments`, argData);
    return response.data;
  },
  update: async (caseId: string, argumentId: string, argData: { argument: string; fact_ids: string[] }) => {
    const response = await apiClient.put<ArgumentItem>(`/cases/${caseId}/arguments/${argumentId}`, argData);
    return response.data;
  },
  approve: async (caseId: string, argumentId: string) => {
    const response = await apiClient.post(`/cases/${caseId}/arguments/${argumentId}/approve`);
    return response.data;
  },
  reject: async (caseId: string, argumentId: string) => {
    const response = await apiClient.post(`/cases/${caseId}/arguments/${argumentId}/reject`);
    return response.data;
  },
  lock: async (caseId: string, argumentId: string) => {
    const response = await apiClient.post(`/cases/${caseId}/arguments/${argumentId}/lock`);
    return response.data;
  },
};

// Prediction endpoints
export const predictionAPI = {
  getHistory: async (caseId: string) => {
    const response = await apiClient.get<PredictionHistoryItem[]>(`/cases/${caseId}/predictions`);
    return response.data;
  },
  restore: async (caseId: string, index: number) => {
    const response = await apiClient.post(`/cases/${caseId}/predictions/restore/${index}`);
    return response.data;
  },
};

// State endpoints
export const stateAPI = {
  getFlags: async (caseId: string) => {
    const response = await apiClient.get<StateFlags>(`/cases/${caseId}/state`);
    return response.data;
  },
  setFlag: async (caseId: string, flagKey: string, value: boolean | number) => {
    const response = await apiClient.post(`/cases/${caseId}/state/${flagKey}`, { value });
    return response.data;
  },
  clearFlag: async (caseId: string, flagKey: string) => {
    await apiClient.delete(`/cases/${caseId}/state/${flagKey}`);
  },
};

export default apiClient;
