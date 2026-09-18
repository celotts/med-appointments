import axiosInstance from './axiosInstance';

export interface DoctorSchedule {
  id: string;
  doctor_id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number;
  created_at?: string;
}

export interface DoctorScheduleCreate {
  doctor_id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number;
}

export interface DoctorScheduleUpdate {
  doctor_id?: string;
  day_of_week?: number;
  start_time?: string;
  end_time?: string;
  slot_duration_minutes?: number;
}

const DAYS = [
  { value: 1, label: 'Lunes' },
  { value: 2, label: 'Martes' },
  { value: 3, label: 'Miércoles' },
  { value: 4, label: 'Jueves' },
  { value: 5, label: 'Viernes' },
  { value: 6, label: 'Sábado' },
  { value: 7, label: 'Domingo' },
];

export const DAYS_OF_WEEK = DAYS;

export const doctorScheduleApi = {
  async getAll(skip = 0, limit = 100) {
    const response = await axiosInstance.get('/doctor-schedules/', {
      params: { skip, limit },
    });
    return response.data;
  },

  async getById(id: string) {
    const response = await axiosInstance.get(`/doctor-schedules/${id}`);
    return response.data;
  },

  async create(data: DoctorScheduleCreate) {
    const response = await axiosInstance.post('/doctor-schedules/', data);
    return response.data;
  },

  async update(id: string, data: { doctor_id?: string; day_of_week?: number; start_time?: string; end_time?: string; slot_duration_minutes?: number }) {
    const response = await axiosInstance.put(`/doctor-schedules/${id}`, data);
    return response.data;
  },

  async delete(id: string) {
    await axiosInstance.delete(`/doctor-schedules/${id}`);
  },

  async getByDoctor(doctorId: string) {
    const response = await axiosInstance.get('/doctor-schedules/', {
      params: { doctor_id: doctorId },
    });
    return response.data;
  },
};
