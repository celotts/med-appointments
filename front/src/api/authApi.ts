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

    // Guardar token en localStorage para persistencia
    if (response.data.access_token) {
      localStorage.setItem('auth_token', response.data.access_token);
      localStorage.setItem('token_type', response.data.token_type || 'bearer');
    }

    return response.data;
  },

  async logout(): Promise<void> {
    // Backend doesn't have logout endpoint, just clear local storage
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
    localStorage.removeItem('token_type');
  },

  async getMe(): Promise<any> {
    const response = await axiosInstance.get('/api/v1/me');
    return response.data;
  },
};