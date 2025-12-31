import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = (import.meta.env.VITE_API_BASE as string) || (import.meta.env.REACT_APP_API_URL as string) || 'http://localhost:8000';

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
  llm_summary?: string | null;
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
  recompute_prediction: boolean;
  // Optional persisted UI/workflow flags (added to match backend state keys)
  restore_prediction_index?: number;
  problem_statement?: string;
  problem_statement_saved_at?: string;
  evidence_files?: string[];
  facts_approved_and_locked?: boolean;
}

// Case endpoints
export const caseAPI = {
  list: async () => {
    const response = await apiClient.get<any[]>('/cases');
    // Backend may return a list of case IDs (string[]) or full CaseInfo objects.
    return response.data.map((item) =>
      typeof item === 'string'
        ? ({ case_id: item, case_name: item, status: 'in_progress', created_at: new Date().toISOString(), updated_at: new Date().toISOString(), fact_count: 0, argument_count: 0 } as CaseInfo)
        : (item as CaseInfo)
    );
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
  compute: async (
    caseId: string,
    payload: { question: string; evidence_files?: string[]; enable_web_search?: boolean; enable_research_papers?: boolean; pdf_directory?: string }
  ) => {
    const response = await apiClient.post(`/cases/${caseId}/compute`, payload);
    return response.data;
  },
  generateDraft: async (caseId: string) => {
    const response = await apiClient.post(`/cases/${caseId}/draft`);
    return response.data as { status: string; draft: string; case_id: string };
  },
  uploadEvidence: async (caseId: string, files: File[]) => {
    if (!caseId) throw new Error('caseId is required for evidence upload');
    const form = new FormData();
    files.forEach((f) => form.append('files', f));
    const response = await apiClient.post(`/cases/${caseId}/evidence`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data as { status: string; saved: string[] };
  },
  saveProblem: async (caseId: string, problem: string) => {
    if (!caseId) throw new Error('caseId is required to save problem statement');
    const response = await apiClient.post(`/cases/${caseId}/problem`, { problem_statement: problem });
    return response.data as { status: string; problem_statement: string };
  },
};

// Fact endpoints
export const factAPI = {
  // Helper: adapt backend FactResponse -> frontend FactItem
  _mapFactResponse: (caseId: string, resp: any): FactItem => {
    return {
      fact_id: resp.id,
      case_id: caseId,
      fact: resp.content,
      source: resp.source || 'manual',
      status: resp.status || 'pending',
      timestamp: resp.created_at || new Date().toISOString(),
      edited_at: resp.approved_at || resp.updated_at || undefined,
      llm_summary: resp.llm_summary || (resp.source_details && resp.source_details.llm_summary) || null,
    };
  },

  list: async (caseId: string) => {
    if (!caseId || caseId === 'undefined') throw new Error('caseId is required for fact list');
    const response = await apiClient.get<any[]>(`/cases/${caseId}/facts`);
    return response.data.map((r) => factAPI._mapFactResponse(caseId, r));
  },

  get: async (caseId: string, factId: string) => {
    if (!caseId || caseId === 'undefined') throw new Error('caseId is required for fact get');
    const response = await apiClient.get<any>(`/cases/${caseId}/facts/${factId}`);
    return factAPI._mapFactResponse(caseId, response.data);
  },
  // frontend sends { fact } field; backend expects { content }
  create: async (caseId: string, factData: { fact: string; source?: string; source_details?: any }) => {
    if (!caseId || caseId === 'undefined') throw new Error('caseId is required for fact create');
    const payload = {
      content: factData.fact,
      source: factData.source || 'manual',
      source_details: factData.source_details || undefined,
    };
    const response = await apiClient.post<any>(`/cases/${caseId}/facts`, payload);
    return factAPI._mapFactResponse(caseId, response.data);
  },
  update: async (caseId: string, factId: string, factData: { fact: string; source?: string }) => {
    if (!caseId || caseId === 'undefined') throw new Error('caseId is required for fact update');
    const payload = {
      content: factData.fact,
      source: factData.source || 'manual',
    };
    const response = await apiClient.put<any>(`/cases/${caseId}/facts/${factId}`, payload);
    return factAPI._mapFactResponse(caseId, response.data);
  },
  approve: async (caseId: string, factId: string) => {
    if (!caseId || caseId === 'undefined') throw new Error('caseId is required for fact approve');
    const response = await apiClient.post<any>(`/cases/${caseId}/facts/${factId}/approve`);
    return factAPI._mapFactResponse(caseId, response.data);
  },
  reject: async (caseId: string, factId: string) => {
    if (!caseId || caseId === 'undefined') throw new Error('caseId is required for fact reject');
    const response = await apiClient.post<any>(`/cases/${caseId}/facts/${factId}/reject`);
    return factAPI._mapFactResponse(caseId, response.data);
  },
  lock: async (caseId: string, factId: string) => {
    if (!caseId || caseId === 'undefined') throw new Error('caseId is required for fact lock');
    // Backend lock endpoint may return a minimal payload; fetch the full fact after locking
    await apiClient.post<any>(`/cases/${caseId}/facts/${factId}/lock`);
    const refreshed = await apiClient.get<any>(`/cases/${caseId}/facts/${factId}`);
    return factAPI._mapFactResponse(caseId, refreshed.data);
  },
  lockAll: async (caseId: string) => {
    if (!caseId || caseId === 'undefined') throw new Error('caseId is required for fact lock-all');
    const response = await apiClient.post<any>(`/cases/${caseId}/facts/lock`);
    return response.data as { status: string; count: number };
  },
};

// Argument endpoints
export const argumentAPI = {
  list: async (caseId: string) => {
    if (!caseId) throw new Error('caseId is required for argument list');
    const response = await apiClient.get<any[]>(`/cases/${caseId}/arguments`);
    return response.data.map((r) => argumentAPI._mapArgumentResponse(caseId, r));
  },
  get: async (caseId: string, argumentId: string) => {
    if (!caseId) throw new Error('caseId is required for argument get');
    const response = await apiClient.get<any>(`/cases/${caseId}/arguments/${argumentId}`);
    return argumentAPI._mapArgumentResponse(caseId, response.data);
  },
  create: async (caseId: string, argData: { argument: string; fact_ids?: string[]; legal_basis?: string }) => {
    if (!caseId) throw new Error('caseId is required for argument create');
    const payload = {
      content: argData.argument,
      legal_basis: argData.legal_basis || '',
      fact_ids: argData.fact_ids || [],
    };
    const response = await apiClient.post<any>(`/cases/${caseId}/arguments`, payload);
    return argumentAPI._mapArgumentResponse(caseId, response.data);
  },
  update: async (caseId: string, argumentId: string, argData: { argument: string; fact_ids?: string[]; legal_basis?: string }) => {
    if (!caseId) throw new Error('caseId is required for argument update');
    const payload = {
      content: argData.argument,
      legal_basis: argData.legal_basis || '',
      fact_ids: argData.fact_ids || [],
    };
    const response = await apiClient.put<any>(`/cases/${caseId}/arguments/${argumentId}`, payload);
    return argumentAPI._mapArgumentResponse(caseId, response.data);
  },
  approve: async (caseId: string, argumentId: string) => {
    if (!caseId) throw new Error('caseId is required for argument approve');
    const response = await apiClient.post<any>(`/cases/${caseId}/arguments/${argumentId}/approve`);
    return argumentAPI._mapArgumentResponse(caseId, response.data);
  },
  reject: async (caseId: string, argumentId: string) => {
    if (!caseId) throw new Error('caseId is required for argument reject');
    const response = await apiClient.post<any>(`/cases/${caseId}/arguments/${argumentId}/reject`);
    return argumentAPI._mapArgumentResponse(caseId, response.data);
  },
  lock: async (caseId: string, argumentId: string) => {
    if (!caseId) throw new Error('caseId is required for argument lock');
    const response = await apiClient.post<any>(`/cases/${caseId}/arguments/${argumentId}/lock`);
    return argumentAPI._mapArgumentResponse(caseId, response.data);
  },
  // Helper to adapt backend ArgumentResponse -> frontend ArgumentItem
  _mapArgumentResponse: (caseId: string, resp: any): ArgumentItem => {
    return {
      argument_id: resp.id,
      case_id: caseId,
      argument: resp.content,
      fact_ids: resp.fact_ids || [],
      status: resp.status || 'pending',
      timestamp: resp.created_at || new Date().toISOString(),
      edited_at: resp.approved_at || resp.updated_at || undefined,
    };
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
