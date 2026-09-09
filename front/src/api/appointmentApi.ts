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
}

export interface AppointmentCreate {
  patient_id: number;
  doctor_id: number;
  status_id: number;
  appointment_date: string;
  reason: string;
  notes?: string;
}

export interface AppointmentUpdate extends Partial<AppointmentCreate> {}

export interface AppointmentStatus {
  id: number;
  name: string;
}

export const appointmentApi = {
  async getAll(skip = 0, limit = 100, filters?: { patient_id?: number; doctor_id?: number; status_id?: number }) {
    const response = await axiosInstance.get('/appointments/', {
      params: { skip, limit, ...filters },
    });
    return response.data;
  },

  async getById(id: number) {
    const response = await axiosInstance.get(`/appointments/${id}`);
    return response.data;
  },

  async create(data: AppointmentCreate) {
    const response = await axiosInstance.post('/appointments/', data);
    return response.data;
  },

  async update(id: number, data: AppointmentUpdate) {
    const response = await axiosInstance.put(`/appointments/${id}`, data);
    return response.data;
  },

  async changeStatus(id: number, statusId: number) {
    const response = await axiosInstance.patch(`/appointments/${id}/status`, {
      status_id: statusId,
    });
    return response.data;
  },

  async delete(id: number) {
    const response = await axiosInstance.delete(`/appointments/${id}`);
    return response.data;
  },

  async getStatuses(): Promise<AppointmentStatus[]> {
    const response = await axiosInstance.get('/appointment-statuses/');
    return response.data;
  },
};
