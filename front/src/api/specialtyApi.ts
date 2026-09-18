import axiosInstance from './axiosInstance';

export interface Specialty {
  id: number;
  name: string;
  description?: string | null;
}

export interface SpecialtyCreate {
  name: string;
  description?: string | null;
}

export interface SpecialtyUpdate {
  name?: string;
  description?: string | null;
}

export const specialtyApi = {
  async getAll(skip = 0, limit = 100): Promise<Specialty[]> {
    const response = await axiosInstance.get('/specialties/', {
      params: { skip, limit },
    });
    return response.data;
  },

  async create(data: SpecialtyCreate): Promise<Specialty> {
    const response = await axiosInstance.post('/specialties/', data);
    return response.data;
  },

  async update(id: number, data: Partial<Specialty>): Promise<Specialty> {
    const response = await axiosInstance.put(`/specialties/${id}`, data);
    return response.data;
  },

  async delete(id: number): Promise<void> {
    await axiosInstance.delete(`/specialties/${id}`);
  },
};
