import React from 'react';
import { useAuthStore } from '../../store/auth';

const DashboardPage: React.FC = () => {
  const { username, role, clearAuth } = useAuthStore();

  return (
    <div style={{ padding: 32 }}>
      <h1>Dashboard</h1>
      <p>Bienvenido, <strong>{username}</strong> ({role})</p>
      <button onClick={clearAuth} style={{ marginTop: 16 }}>Cerrar sesión</button>
    </div>
  );
};

export default DashboardPage;
