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
}

export interface DoctorCreate {
  first_name: string;
  last_name: string;
  specialty_id: number;
  license_number: string;
  email: string;
  phone: string;
  active?: boolean;
}

export interface DoctorUpdate extends Partial<DoctorCreate> {}

export const doctorApi = {
  async getAll(skip = 0, limit = 100) {
    const response = await axiosInstance.get('/doctors/', {
      params: { skip, limit },
    });
    return response.data;
  },

  async getById(id: number) {
    const response = await axiosInstance.get(`/doctors/${id}`);
    return response.data;
  },

  async create(data: DoctorCreate) {
    const response = await axiosInstance.post('/doctors/', data);
    return response.data;
  },

  async update(id: number, data: DoctorUpdate) {
    const response = await axiosInstance.put(`/doctors/${id}`, data);
    return response.data;
  },

  async delete(id: number) {
    const response = await axiosInstance.delete(`/doctors/${id}`);
    return response.data;
  },
};
