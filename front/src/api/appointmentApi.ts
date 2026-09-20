import axiosInstance from './axiosInstance';

export interface AppointmentStatus {
  id: number;
  code: string;
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
    filters?: { patient_id?: number; doctor_id?: number; status?: string }
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

  async delete(id: number) {
    const response = await axiosInstance.delete(`/appointments/${id}`);
    return response.data;
  },

  async getStatuses(): Promise<AppointmentStatus[]> {
    const response = await axiosInstance.get('/appointment-statuses/');
    return response.data;
  },
};
