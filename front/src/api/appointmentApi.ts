import axiosInstance from './axiosInstance';

export interface AppointmentStatus {
  id: number;
  code: string;
  description?: string | null;
}

export interface AppointmentStatusCreate {
  code: string;
  description?: string | null;
}

export interface AppointmentStatusUpdate {
  code?: string | null;
  description?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Appointment {
  id: number;
  patient_id: number;
  doctor_id: number;
  status_id: number;
  start_datetime: string;
  end_datetime: string;
  reason: string;
  created_at?: string;
  status?: AppointmentStatus | null;
}

export interface AppointmentCreate {
  patient_id: number;
  doctor_id: number;
  start_datetime: string;
  end_datetime: string;
  reason: string;
}

export interface AppointmentUpdate {
  start_datetime?: string;
  end_datetime?: string;
  reason?: string;
}

export const appointmentApi = {
  async getAll(
    page = 1,
    pageSize = 20,
    filters?: { patient_id?: number; doctor_id?: number; status?: string; assistant_specialist_ids?: string }
  ): Promise<PaginatedResponse<Appointment>> {
    const params = { page, page_size: pageSize, ...filters };
    const response = await axiosInstance.get('/appointments/', { params });
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

  async changeStatus(id: number, status: string) {
    const response = await axiosInstance.patch(`/appointments/${id}/status`, { status });
    return response.data;
  },

  async confirmAppointment(id: number) {
    const response = await axiosInstance.post(`/appointments/${id}/confirm`);
    return response.data;
  },

  async waitAppointment(id: number) {
    const response = await axiosInstance.post(`/appointments/${id}/wait`);
    return response.data;
  },

  async startAppointment(id: number) {
    const response = await axiosInstance.post(`/appointments/${id}/start`);
    return response.data;
  },

  async attendAppointment(id: number, notes?: string, duration_minutes?: number) {
    const response = await axiosInstance.post(`/appointments/${id}/attend`, { notes, duration_minutes });
    return response.data;
  },

  async suspendAppointment(id: number, reason: string) {
    const response = await axiosInstance.post(`/appointments/${id}/suspend`, { reason });
    return response.data;
  },

  async cancelAppointment(id: number, reason: string) {
    const response = await axiosInstance.post(`/appointments/${id}/cancel`, { reason });
    return response.data;
  },

  async reactivateAppointment(id: number) {
    const response = await axiosInstance.post(`/appointments/${id}/reactivate`);
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

  async createStatus(data: AppointmentStatusCreate): Promise<AppointmentStatus> {
    const response = await axiosInstance.post('/appointment-statuses/', data);
    return response.data;
  },

  async updateStatus(id: number, data: AppointmentStatusUpdate): Promise<AppointmentStatus> {
    const response = await axiosInstance.patch(`/appointment-statuses/${id}`, data);
    return response.data;
  },

  async deleteStatus(id: number): Promise<void> {
    await axiosInstance.delete(`/appointment-statuses/${id}`);
  },
};
