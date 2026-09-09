import axiosInstance from './axiosInstance';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  message: string;
  history?: ChatMessage[];
}

export interface ChatResponse {
  response: string;
}

export interface DocumentSearchResult {
  id: number;
  reference_type: string;
  reference_id: number | null;
  title: string;
  content: string;
  similarity: number;
}

export interface HealthCheck {
  ollama: string;
  embedding_model: string;
  llm_model: string;
  vector_count: number;
}

export const ragApi = {
  async chat(message: string, history?: ChatMessage[]): Promise<ChatResponse> {
    const response = await axiosInstance.post('/rag/chat', { message, history });
    return response.data;
  },

  async chatStream(message: string, history?: ChatMessage[], onToken?: (token: string) => void): Promise<string> {
    const token = localStorage.getItem('auth_token');
    const response = await fetch('/api/v1/rag/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ message, history }),
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let fullResponse = '';

    if (reader) {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.token) {
                fullResponse += data.token;
                onToken?.(fullResponse);
              }
              if (data.error) {
                fullResponse = `Error: ${data.error}`;
                onToken?.(fullResponse);
              }
            } catch {}
          }
        }
      }
    }
    return fullResponse;
  },

  async search(query: string, k = 5, referenceType?: string): Promise<DocumentSearchResult[]> {
    const response = await axiosInstance.post('/rag/search', {
      query,
      k,
      reference_type: referenceType,
    });
    return response.data;
  },

  async health(): Promise<HealthCheck> {
    const response = await axiosInstance.get('/rag/health');
    return response.data;
  },

  async ingest(data: { reference_type: string; reference_id?: number; title: string; content: string }) {
    const response = await axiosInstance.post('/rag/ingest', data);
    return response.data;
  },
};
