import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';
import './AppShell.css';

interface Tab {
  label: string;
  path: string;
  roles?: string[];
}

const TABS: Tab[] = [
  { label: 'Producto',     path: '/product' },
  { label: 'Contenedores', path: '/containers', roles: ['reviewer', 'admin'] },
  { label: 'Reglas',       path: '/rules',      roles: ['reviewer', 'admin'] },
];

interface AppShellProps {
  children: React.ReactNode;
}

const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const { username, fullName, role, clearAuth } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  const visibleTabs = TABS.filter(
    (tab) => !tab.roles || (role && tab.roles.includes(role))
  );

  const activeTab = visibleTabs.find((t) => location.pathname.startsWith(t.path));
  const sectionLabel = activeTab?.label ?? visibleTabs[0]?.label ?? '';

  return (
    <div className="shell">
      <header className="shell__header">
        <span className="shell__logo">Packaging Optimizer</span>
        <span className="shell__section">{sectionLabel}</span>
        <div className="shell__user">
          <span className="shell__username">{fullName ?? username} · {role}</span>
          <button className="shell__logout" onClick={clearAuth}>Salir</button>
        </div>
      </header>

      <div className="shell__tabs">
        {visibleTabs.map((tab) => (
          <button
            key={tab.path}
            className={`shell__tab${location.pathname.startsWith(tab.path) ? ' shell__tab--active' : ''}`}
            onClick={() => navigate(tab.path)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <main className="shell__content">
        {children}
      </main>
    </div>
  );
};

export default AppShell;

