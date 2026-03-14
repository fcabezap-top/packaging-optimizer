import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/login/LoginPage';
import ProductPage from './pages/product/ProductPage';
import ContainersPage from './pages/containers/ContainersPage';
import RulesPage from './pages/rules/RulesPage';
import ResetPasswordPage from './pages/reset-password/ResetPasswordPage';
import ManufacturerPage from './pages/manufacturer/ManufacturerPage';
import ProposalPage from './pages/proposals/ProposalPage';
import ProposalResultPage from './pages/proposals/ProposalResultPage';
import { useAuthStore } from './store/auth';

const PrivateRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const token = useAuthStore((s) => s.token);
  const hydrated = useAuthStore((s) => s._hasHydrated);
  if (!hydrated) return null;
  return token ? <>{children}</> : <Navigate to="/login" replace />;
};

const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const token = useAuthStore((s) => s.token);
  const role  = useAuthStore((s) => s.role);
  const hydrated = useAuthStore((s) => s._hasHydrated);
  if (!hydrated) return null;
  if (!token) return <>{children}</>;
  return <Navigate to={role === 'manufacturer' ? '/manufacturer' : '/product'} replace />;
};

const SmartRedirect: React.FC = () => {
  const token = useAuthStore((s) => s.token);
  const role  = useAuthStore((s) => s.role);
  const hydrated = useAuthStore((s) => s._hasHydrated);
  if (!hydrated) return null;
  if (!token) return <Navigate to="/login" replace />;
  return <Navigate to={role === 'manufacturer' ? '/manufacturer' : '/product'} replace />;
};

const AppRouter: React.FC = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
      <Route path="/product"      element={<PrivateRoute><ProductPage /></PrivateRoute>} />
      <Route path="/containers"   element={<PrivateRoute><ContainersPage /></PrivateRoute>} />
      <Route path="/rules"        element={<PrivateRoute><RulesPage /></PrivateRoute>} />
      <Route path="/manufacturer" element={<PrivateRoute><ManufacturerPage /></PrivateRoute>} />
      <Route path="/proposals"        element={<PrivateRoute><ProposalPage /></PrivateRoute>} />
      <Route path="/proposals/result"  element={<PrivateRoute><ProposalResultPage /></PrivateRoute>} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="*" element={<SmartRedirect />} />
    </Routes>
  </BrowserRouter>
);

export default AppRouter;

