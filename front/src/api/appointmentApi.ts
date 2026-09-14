import axiosInstance from './axiosInstance';

export interface Appointment {
  id: number;
  patient_id: number;
  doctor_id: number;
  status_id: number;
  appointment_date: string;
  reason: string;
  notes?: string;
  patient_name?: string;
  doctor_name?: string;
  status_name?: string;
  user_id?: number;
}

export interface AppointmentCreate {
  patient_id: number;
  doctor_id: number;
  status_id: number;
  appointment_date: string;
  reason: string;
  notes?: string;
  user_id?: number;
}

export interface AppointmentUpdate extends Partial<AppointmentCreate> {}

export interface AppointmentStatus {
  id: number;
  name: string;
}

export const appointmentApi = {
  async getAll(skip = 0, limit = 100, filters?: { patient_id?: number; doctor_id?: number; status_id?: number; user_id?: number }) {
    const user_id = localStorage.getItem('user_id');
    const response = await axiosInstance.get('/appointments/', {
      params: { skip, limit, ...filters, user_id },
    });
    return response.data;
  },

  async getById(id: number, user_id?: number) {
    const uid = user_id || localStorage.getItem('user_id');
    const response = await axiosInstance.get(`/appointments/${id}?user_id=${uid}`);
    return response.data;
  },

  async create(data: AppointmentCreate) {
    const user_id = localStorage.getItem('user_id');
    const response = await axiosInstance.post('/appointments/', { ...data, user_id: Number(user_id) || undefined });
    return response.data;
  },

  async update(id: number, data: AppointmentUpdate) {
    const user_id = localStorage.getItem('user_id');
    const response = await axiosInstance.put(`/appointments/${id}`, { ...data, user_id: Number(user_id) || undefined });
    return response.data;
  },

  async changeStatus(id: number, statusId: number) {
    const user_id = localStorage.getItem('user_id');
    const response = await axiosInstance.patch(`/appointments/${id}/status`, { status_id: statusId, user_id: Number(user_id) || undefined });
    return response.data;
  },

  async delete(id: number) {
    const user_id = localStorage.getItem('user_id');
    const response = await axiosInstance.delete(`/appointments/${id}?user_id=${user_id}`);
    return response.data;
  },

  async getStatuses(): Promise<AppointmentStatus[]> {
    const response = await axiosInstance.get('/appointment-statuses/');
    return response.data;
  },
};
