import React, { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import type { Variants } from 'framer-motion';
import { apiResetPassword } from '../../api/auth';
import AuthHeader from '../../components/layout/AuthHeader';
import './reset-password.css';

type View = 'form' | 'done';

const panelVariants: Variants = {
  hidden:  { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' } },
  exit:    { opacity: 0, y: -10, transition: { duration: 0.15, ease: 'easeIn' } },
};

const ResetPasswordPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';

  const [view, setView] = useState<View>('form');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!token) {
      setError('Enlace inválido. Solicita uno nuevo desde la pantalla de inicio de sesión.');
      return;
    }
    if (newPassword.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Las contraseñas no coinciden.');
      return;
    }

    setLoading(true);
    try {
      await apiResetPassword(token, newPassword);
      setView('done');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'El enlace ha expirado o ya fue utilizado.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      className="resetPage"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.25, ease: 'easeOut' } }}
    >
      <AuthHeader />

      <div className="resetPage__body">
        <div className="resetPage__card">
          <AnimatePresence mode="wait">

            {view === 'form' && (
              <motion.div key="form" variants={panelVariants} initial="hidden" animate="visible" exit="exit">
                <h1 className="resetPage__title">Nueva contraseña</h1>
                <p className="resetPage__subtitle">Introduce tu nueva contraseña. Mínimo 8 caracteres.</p>

                {!token && (
                  <p className="resetPage__errorMsg">
                    Enlace inválido. <Link to="/login">Solicita uno nuevo</Link>.
                  </p>
                )}

                <form onSubmit={handleSubmit} noValidate>
                  <div className="resetPage__field">
                    <label className="resetPage__label" htmlFor="newPassword">Nueva contraseña</label>
                    <input
                      id="newPassword" type="password"
                      className={`resetPage__input${error ? ' resetPage__input--error' : ''}`}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      autoComplete="new-password"
                      autoFocus
                      required
                      disabled={!token}
                    />
                  </div>

                  <div className="resetPage__field">
                    <label className="resetPage__label" htmlFor="confirmPassword">Confirmar contraseña</label>
                    <input
                      id="confirmPassword" type="password"
                      className={`resetPage__input${error ? ' resetPage__input--error' : ''}`}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      autoComplete="new-password"
                      required
                      disabled={!token}
                    />
                  </div>

                  <p className="resetPage__errorMsg">{error}</p>

                  <button
                    type="submit"
                    className="resetPage__submit"
                    disabled={loading || !newPassword || !confirmPassword || !token}
                  >
                    {loading ? 'Guardando...' : 'Guardar contraseña'}
                  </button>
                </form>

                <Link to="/login" className="resetPage__backLink">← Volver al inicio de sesión</Link>
              </motion.div>
            )}

            {view === 'done' && (
              <motion.div key="done" variants={panelVariants} initial="hidden" animate="visible" exit="exit">
                <h1 className="resetPage__title">¡Contraseña actualizada!</h1>
                <p className="resetPage__subtitle">
                  Tu contraseña se ha cambiado correctamente. Ya puedes acceder con tus nuevas credenciales.
                </p>
                <button className="resetPage__submit" onClick={() => navigate('/login')} style={{ marginTop: 'var(--size-8)' }}>
                  Ir al inicio de sesión
                </button>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
};

export default ResetPasswordPage;
