import axiosInstance from './axiosInstance';

export interface ConsultingRoom {
  id: string;
  name: string;
  address?: string | null;
  phone_number?: string | null;
  created_at?: string;
}

export interface ConsultingRoomCreate {
  name: string;
  address?: string | null;
  phone_number?: string | null;
}

export interface ConsultingRoomUpdate {
  name?: string;
  address?: string | null;
  phone_number?: string | null;
}

export const consultingRoomApi = {
  async getAll(skip = 0, limit = 100) {
    const response = await axiosInstance.get('/consulting-rooms/', {
      params: { skip, limit },
    });
    return response.data;
  },

  async getById(id: string) {
    const response = await axiosInstance.get(`/consulting-rooms/${id}`);
    return response.data;
  },

  async create(data: ConsultingRoomCreate) {
    const response = await axiosInstance.post('/consulting-rooms/', data);
    return response.data;
  },

  async update(id: string, data: { name?: string; address?: string | null; phone_number?: string | null }) {
    const response = await axiosInstance.put(`/consulting-rooms/${id}`, data);
    return response.data;
  },

  async delete(id: string) {
    await axiosInstance.delete(`/consulting-rooms/${id}`);
  },
};
