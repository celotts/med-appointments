import axiosInstance from './axiosInstance';

export interface AppointmentStatus {
  id: number;
  code: string;
  description?: string | null;
}

export const appointmentStatusApi = {
  async getAll(): Promise<AppointmentStatus[]> {
    const response = await axiosInstance.get('/appointment-statuses/');
    return response.data;
  },
};
