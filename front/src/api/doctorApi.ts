import axiosInstance from './axiosInstance';

export interface Doctor {
  id: number;
  first_name: string;
  last_name: string;
  specialty_id: number;
  license_number: string;
  email: string;
  phone: string;
  active: boolean;
  specialty_name?: string;
  user_id?: number;
}

export interface DoctorCreate {
  first_name: string;
  last_name: string;
  specialty_id: number;
  license_number: string;
  email: string;
  phone: string;
  active?: boolean;
  user_id?: number;
}

export interface DoctorUpdate extends Partial<DoctorCreate> {}

export const doctorApi = {
  async getAll(skip = 0, limit = 100) {
    const user_id = localStorage.getItem('user_id');
    const response = await axiosInstance.get('/doctors/', {
      params: { skip, limit, user_id },
    });
    return response.data;
  },

  async getById(id: number, user_id?: number) {
    const uid = user_id || localStorage.getItem('user_id');
    const response = await axiosInstance.get(`/doctors/${id}?user_id=${uid}`);
    return response.data;
  },

  async create(data: DoctorCreate) {
    const user_id = localStorage.getItem('user_id');
    const response = await axiosInstance.post('/doctors/', { ...data, user_id: Number(user_id) || undefined });
    return response.data;
  },

  async update(id: number, data: DoctorUpdate) {
    const user_id = localStorage.getItem('user_id');
    const response = await axiosInstance.put(`/doctors/${id}`, { ...data, user_id: Number(user_id) || undefined });
    return response.data;
  },

  async delete(id: number) {
    const user_id = localStorage.getItem('user_id');
    const response = await axiosInstance.delete(`/doctors/${id}?user_id=${user_id}`);
    return response.data;
  },
};
