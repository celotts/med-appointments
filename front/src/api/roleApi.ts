import axiosInstance from './axiosInstance';

export interface Role {
  id: number;
  name: string;
}

export const roleApi = {
  async getAll(): Promise<Role[]> {
    const response = await axiosInstance.get('/api/v1/roles');
    return response.data.roles || response.data;
  },
};
