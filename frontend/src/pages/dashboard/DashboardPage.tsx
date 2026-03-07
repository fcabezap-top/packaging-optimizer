import React from 'react';
import { useAuthStore } from '../../store/auth';
import AppShell from '../../components/layout/AppShell';

const DashboardPage: React.FC = () => {
  const { username, fullName, role } = useAuthStore();

  return (
    <AppShell>
      <div className="pageHeader">
        <h1 className="pageHeader__title">Dashboard</h1>
        <span className="pageHeader__subtitle">Bienvenido, {fullName ?? username}</span>
      </div>
      <p style={{ fontSize: 'var(--font-size-s)', color: 'var(--color-content-3)' }}>
        Rol activo: <strong style={{ color: 'var(--color-content-1)' }}>{role}</strong>
      </p>
    </AppShell>
  );
};

export default DashboardPage;

