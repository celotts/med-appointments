import axiosInstance from './axiosInstance';

export interface Branch {
  id: number;
  name: string;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  is_active?: boolean;
  deleted_at?: string | null;
}

export interface BranchCreate {
  name: string;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  is_active?: boolean;
}

export interface BranchUpdate {
  name?: string;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  is_active?: boolean;
}

export const branchApi = {
  async getAll(): Promise<Branch[]> {
    const response = await axiosInstance.get('/branches');
    return response.data.branches || response.data;
  },

  async create(data: BranchCreate): Promise<Branch> {
    const response = await axiosInstance.post('/branches', data);
    return response.data;
  },

  async update(id: number, data: BranchUpdate): Promise<Branch> {
    const response = await axiosInstance.put(`/branches/${id}`, data);
    return response.data;
  },

  async delete(id: number): Promise<void> {
    await axiosInstance.delete(`/branches/${id}`);
  },
};