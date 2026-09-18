import axiosInstance from './axiosInstance';

export interface Branch {
  id: number;
  name: string;
  address?: string | null;
  phone?: string | null;
  deleted_at?: string | null;
}

export const branchApi = {
  async getAll(): Promise<Branch[]> {
    const response = await axiosInstance.get('/api/v1/branches');
    return response.data.branches || response.data;
  },
};
