import axiosInstance from './axiosInstance';

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export const authApi = {
  async login(data: { email: string; password: string }): Promise<LoginResponse> {
    // Backend expects OAuth2PasswordRequestForm (form-data)
    const params = new URLSearchParams();
    params.append('username', data.email);
    params.append('password', data.password);

    const response = await axiosInstance.post('/login/access-token', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  },

  async logout(): Promise<void> {
    // Backend doesn't have logout endpoint, just clear local storage
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
  },

  async getMe(): Promise<any> {
    const response = await axiosInstance.get('/users/me');
    return response.data;
  },
};
