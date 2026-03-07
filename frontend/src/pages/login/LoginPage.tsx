import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import { apiLogin, decodeJwtPayload } from '../../api/auth';
import { useAuthStore, type Role } from '../../store/auth';
import './login.css';

const pageVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.25, ease: 'easeOut' } },
};

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { access_token } = await apiLogin(username, password);
      const payload = decodeJwtPayload(access_token);
      const role = (payload.role ?? 'manufacturer') as Role;
      const sub = (payload.sub ?? username) as string;
      setAuth(access_token, role, sub);
      navigate('/dashboard');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      className="loginPage"
      initial="hidden"
      animate="visible"
      variants={pageVariants}
    >
      {/* Panel izquierdo — imagen */}
      <div className="loginPage__image">
        <div className="loginPage__imageBrand">
          <span className="loginPage__imageBrandName">Packaging Optimizer</span>
        </div>
      </div>

      {/* Panel derecho — formulario */}
      <div className="loginPage__form">
        <div className="loginPage__formInner">
          <h1 className="loginPage__title">Bienvenido</h1>
          <p className="loginPage__subtitle">Introduce tus credenciales para acceder</p>

          <form onSubmit={handleSubmit} noValidate>
            <div className="loginPage__field">
              <label className="loginPage__label" htmlFor="username">
                Usuario
              </label>
              <input
                id="username"
                type="text"
                className={`loginPage__input${error ? ' loginPage__input--error' : ''}`}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
                required
              />
            </div>

            <div className="loginPage__field">
              <label className="loginPage__label" htmlFor="password">
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                className={`loginPage__input${error ? ' loginPage__input--error' : ''}`}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>

            <p className="loginPage__errorMsg">{error}</p>

            <button
              type="submit"
              className="loginPage__submit"
              disabled={loading || !username || !password}
            >
              {loading ? 'Accediendo...' : 'Acceder'}
            </button>
          </form>
        </div>
      </div>
    </motion.div>
  );
};

export default LoginPage;
