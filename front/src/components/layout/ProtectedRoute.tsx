import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Loader2 } from 'lucide-react';

const ProtectedRoute: React.FC = () => {
  const { isAuthenticated, isLoading, isTokenValid } = useAuth();

  if (isLoading) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-center bg-medical-background gap-3">
        <Loader2 className="animate-spin text-medical-primary" size={32} />
        <p className="text-medical-textMuted text-sm">Verificando sesion...</p>
      </div>
    );
  }

  if (!isAuthenticated || !isTokenValid()) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};

export default ProtectedRoute;
