import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import type { Variants } from 'framer-motion';
import { apiLogin, apiForgotPassword, decodeJwtPayload } from '../../api/auth';
import { useAuthStore, type Role } from '../../store/auth';
import AuthHeader from '../../components/layout/AuthHeader';
import loginVideo from '../../assets/start-video.mp4';
import './login.css';

type View = 'login' | 'forgot' | 'done';

const panelVariants: Variants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' } },
  exit:   { opacity: 0, y: -10, transition: { duration: 0.15, ease: 'easeIn' } },
};

const pageVariants: Variants = {
  hidden:  { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.25, ease: 'easeOut' } },
};

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [view, setView] = useState<View>('login');

  // login
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);

  // forgot
  const [email, setEmail] = useState('');
  const [forgotError, setForgotError] = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    setLoginLoading(true);
    try {
      const { access_token } = await apiLogin(username, password);
      const payload = decodeJwtPayload(access_token);
      const role = (payload.role ?? 'manufacturer') as Role;
      const sub = (payload.sub ?? username) as string;
      const fullName = [payload.first_name, payload.last_name].filter(Boolean).join(' ') || sub;
      setAuth(access_token, role, sub, fullName);
      navigate('/dashboard');
    } catch (err: unknown) {
      setLoginError(err instanceof Error ? err.message : 'Error al iniciar sesión');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleForgot = async (e: React.FormEvent) => {
    e.preventDefault();
    setForgotError('');
    setForgotLoading(true);
    try {
      await apiForgotPassword(email);
      setView('done');
    } catch (err: unknown) {
      setForgotError(err instanceof Error ? err.message : 'Error al enviar el correo');
    } finally {
      setForgotLoading(false);
    }
  };

  return (
    <motion.div className="loginPage" initial="hidden" animate="visible" variants={pageVariants}>
      <AuthHeader />

      <div className="loginPage__body">
        {/* Panel izquierdo — video */}
        <div className="loginPage__video">
          <video className="loginPage__videoBg" src={loginVideo} autoPlay loop muted playsInline />
          <div className="loginPage__videoOverlay" />
        </div>

        {/* Panel derecho — formulario dinámico */}
        <div className="loginPage__form">
          <div className="loginPage__formInner">
            <AnimatePresence mode="wait">

              {view === 'login' && (
                <motion.div key="login" variants={panelVariants} initial="hidden" animate="visible" exit="exit">
                  <h1 className="loginPage__title">Bienvenido</h1>
                  <p className="loginPage__subtitle">Introduce tus credenciales para acceder</p>

                  <form onSubmit={handleLogin} noValidate>
                    <div className="loginPage__field">
                      <label className="loginPage__label" htmlFor="username">Usuario</label>
                      <input
                        id="username" type="text"
                        className={`loginPage__input${loginError ? ' loginPage__input--error' : ''}`}
                        value={username} onChange={(e) => setUsername(e.target.value)}
                        autoComplete="username" autoFocus required
                      />
                    </div>

                    <div className="loginPage__field">
                      <label className="loginPage__label" htmlFor="password">Contraseña</label>
                      <input
                        id="password" type="password"
                        className={`loginPage__input${loginError ? ' loginPage__input--error' : ''}`}
                        value={password} onChange={(e) => setPassword(e.target.value)}
                        autoComplete="current-password" required
                      />
                    </div>

                    <p className="loginPage__errorMsg">{loginError}</p>

                    <button type="submit" className="loginPage__submit"
                      disabled={loginLoading || !username || !password}>
                      {loginLoading ? 'Accediendo...' : 'Acceder'}
                    </button>
                  </form>

                  <button className="loginPage__forgotLink" onClick={() => setView('forgot')}>
                    ¿No recuerdas tu contraseña?
                  </button>
                </motion.div>
              )}

              {view === 'forgot' && (
                <motion.div key="forgot" variants={panelVariants} initial="hidden" animate="visible" exit="exit">
                  <h1 className="loginPage__title">Recuperar acceso</h1>
                  <p className="loginPage__subtitle">
                    Introduce tu email y te enviaremos un enlace para restablecer tu contraseña.
                  </p>

                  <form onSubmit={handleForgot} noValidate>
                    <div className="loginPage__field">
                      <label className="loginPage__label" htmlFor="email">Email</label>
                      <input
                        id="email" type="email"
                        className={`loginPage__input${forgotError ? ' loginPage__input--error' : ''}`}
                        value={email} onChange={(e) => setEmail(e.target.value)}
                        autoComplete="email" autoFocus required
                      />
                    </div>

                    <p className="loginPage__errorMsg">{forgotError}</p>

                    <button type="submit" className="loginPage__submit"
                      disabled={forgotLoading || !email}>
                      {forgotLoading ? 'Enviando...' : 'Enviar enlace'}
                    </button>
                  </form>

                  <button className="loginPage__forgotLink" onClick={() => setView('login')}>
                    ← Volver al inicio de sesión
                  </button>
                </motion.div>
              )}

              {view === 'done' && (
                <motion.div key="done" variants={panelVariants} initial="hidden" animate="visible" exit="exit">
                  <h1 className="loginPage__title">Revisa tu correo</h1>
                  <p className="loginPage__subtitle">
                    Si el email está registrado, recibirás un enlace para restablecer tu contraseña en breve.
                    El enlace expira en 1 hora.
                  </p>
                  <button className="loginPage__forgotLink" style={{ marginTop: 'var(--size-8)' }}
                    onClick={() => { setView('login'); setEmail(''); }}>
                    ← Volver al inicio de sesión
                  </button>
                </motion.div>
              )}

            </AnimatePresence>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default LoginPage;

