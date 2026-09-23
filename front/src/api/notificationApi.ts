import axiosInstance from './axiosInstance';

export interface Notification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  related_appointment_id: number | null;
  created_at: string;
}

export const notificationApi = {
  getNotifications: async (skip = 0, limit = 20): Promise<Notification[]> => {
    const { data } = await axiosInstance.get(`/notifications?skip=${skip}&limit=${limit}`);
    return data;
  },

  getUnreadCount: async (): Promise<number> => {
    const { data } = await axiosInstance.get('/notifications/unread-count');
    return data.count;
  },

  markAsRead: async (notificationId: string): Promise<void> => {
    await axiosInstance.patch(`/notifications/${notificationId}/read`);
  },

  markAllAsRead: async (): Promise<void> => {
    await axiosInstance.patch('/notifications/read-all');
  },
};
