import axiosInstance from './axiosInstance';

export interface Specialty {
  id: number;
  name: string;
  description?: string | null;
}

export const specialtyApi = {
  async getAll(skip = 0, limit = 100): Promise<Specialty[]> {
    const response = await axiosInstance.get('/specialties/', {
      params: { skip, limit },
    });
    return response.data;
  },
};
