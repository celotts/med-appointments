import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { authApi } from '../api/authApi';
import { toast } from 'react-hot-toast';
import { Lock, Mail, Loader2, Eye, EyeOff } from 'lucide-react';
import { useForm } from 'react-hook-form';

interface LoginForm {
  email: string;
  password: string;
}

const LoginPage: React.FC = () => {
  const [showPassword, setShowPassword] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>();

  const onSubmit = async (data: LoginForm) => {
    try {
      const tokenData = await authApi.login(data);

      let userData;
      try {
        const me = await authApi.getMe();
        userData = {
          id: me.id,
          email: me.email,
          full_name: me.full_name || me.email.split('@')[0],
          role: me.role || 'user',
        };
      } catch {
        userData = {
          id: '',
          email: data.email,
          full_name: data.email.split('@')[0],
          role: 'user',
        };
      }

      login(tokenData.access_token, userData);
      toast.success('Bienvenido!');
      navigate('/');
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Credenciales incorrectas';
      toast.error(errorMessage);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-medical-background px-4">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-2xl shadow-xl border border-slate-200">
        <div className="text-center">
          <div className="mx-auto h-14 w-14 bg-medical-primary rounded-xl flex items-center justify-center text-white mb-4">
            <Lock size={28} />
          </div>
          <h2 className="text-3xl font-bold text-medical-textMain">MedAppointments</h2>
          <p className="mt-2 text-medical-textMuted">Inicia sesion en tu cuenta</p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1.5">Email</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-medical-textMuted">
                  <Mail size={18} />
                </div>
                <input
                  type="email"
                  {...register('email', {
                    required: 'Email requerido',
                    pattern: { value: /^\S+@\S+$/i, message: 'Email invalido' }
                  })}
                  className="block w-full pl-10 pr-3 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none transition-all text-sm"
                  placeholder="admin@medapi.com"
                />
              </div>
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-medical-textMain mb-1.5">Contrasena</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-medical-textMuted">
                  <Lock size={18} />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  {...register('password', {
                    required: 'Contrasena requerida',
                    minLength: { value: 6, message: 'Minimo 6 caracteres' }
                  })}
                  className="block w-full pl-10 pr-10 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-medical-secondary focus:border-transparent outline-none transition-all text-sm"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-medical-textMuted hover:text-medical-textMain"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>}
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-medical-primary hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-medical-primary transition-all disabled:opacity-70"
          >
            {isSubmitting ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              'Iniciar Sesion'
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
