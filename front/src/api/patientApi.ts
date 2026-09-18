import axiosInstance from './axiosInstance';

export interface Patient {
  id: number;
  first_name: string;
  last_name: string;
  document_number: string;
  birth_date: string;
  email: string;
  phone: string;
  user_id?: number;
}

export interface PatientCreate {
  first_name: string;
  last_name: string;
  document_number: string;
  birth_date: string;
  email: string;
  phone: string;
  user_id?: number;
}

export interface PatientUpdate extends Partial<PatientCreate> {}

export const patientApi = {
  async getAll(skip = 0, limit = 100) {
    const user_id = localStorage.getItem('user_id');
    const response = await axiosInstance.get('/patients/', {
      params: { skip, limit, user_id },
    });
    return response.data;
  },

  async getById(id: number, user_id?: number) {
    const uid = user_id || localStorage.getItem('user_id');
    const response = await axiosInstance.get(`/patients/${id}?user_id=${uid}`);
    return response.data;
  },

  async create(data: PatientCreate) {
    const user_id = localStorage.getItem('user_id');
    const response = await axiosInstance.post('/patients/', { ...data, user_id: Number(user_id) || undefined });
    return response.data;
  },

  async update(id: number, data: PatientUpdate) {
    const user_id = localStorage.getItem('user_id');
    const response = await axiosInstance.put(`/patients/${id}`, { ...data, user_id: Number(user_id) || undefined });
    return response.data;
  },

  async delete(id: number) {
    const user_id = localStorage.getItem('user_id');
    const response = await axiosInstance.delete(`/patients/${id}?user_id=${user_id}`);
    return response.data;
  },
};
