import axiosInstance from './axiosInstance';

export interface Patient {
  id: number;
  first_name: string;
  last_name: string;
  birth_date: string;
  email: string;
  phone: string;
}

export interface PatientCreate {
  first_name: string;
  last_name: string;
  birth_date: string;
  email: string;
  phone: string;
}

export interface PatientUpdate extends Partial<PatientCreate> {}

export const patientApi = {
  async getAll(skip = 0, limit = 100) {
    const response = await axiosInstance.get('/patients/', {
      params: { skip, limit },
    });
    return response.data;
  },

  async getById(id: number) {
    const response = await axiosInstance.get(`/patients/${id}`);
    return response.data;
  },

  async create(data: PatientCreate) {
    const response = await axiosInstance.post('/patients/', data);
    return response.data;
  },

  async update(id: number, data: PatientUpdate) {
    const response = await axiosInstance.put(`/patients/${id}`, data);
    return response.data;
  },

  async delete(id: number) {
    const response = await axiosInstance.delete(`/patients/${id}`);
    return response.data;
  },
};
