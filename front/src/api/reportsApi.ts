import axiosInstance from './axiosInstance';

export interface DashboardSummary {
  total_patients: number;
  total_doctors: number;
  total_appointments_today: number;
  total_appointments_week: number;
  total_appointments_month: number;
  appointments_pending: number;
  appointments_confirmed: number;
  appointments_completed_today: number;
  appointments_cancelled_month: number;
}

export const reportsApi = {
  async getDashboardSummary(): Promise<DashboardSummary> {
    const response = await axiosInstance.get('/reports/dashboard/summary');
    return response.data;
  },

  async getAppointmentsByDay() {
    const response = await axiosInstance.get('/reports/appointments-by-day');
    return response.data;
  },

  async getAppointmentsByDoctor() {
    const response = await axiosInstance.get('/reports/appointments-by-doctor');
    return response.data;
  },

  async getNoShowRate() {
    const response = await axiosInstance.get('/reports/no-show-rate');
    return response.data;
  },
};
