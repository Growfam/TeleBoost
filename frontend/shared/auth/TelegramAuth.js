import React, { useEffect, useState, useCallback } from 'react';

// SVG Icons
const TelegramIcon = ({ size = 32, color = '#fff' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path
      d="M21.198 2.433a2.242 2.242 0 0 0-1.022.215l-8.609 3.33c-2.068.8-4.133 1.598-5.724 2.21a405.15 405.15 0 0 1-2.849 1.09c-.42.147-.99.332-1.473.901-.728.968.193 1.798.919 2.112 1.058.46 2.06.745 3.059 1.122 1.074.409 2.156.842 3.23 1.295l-.138-.03c.265.624.535 1.239.804 1.858.382.883.761 1.769 1.137 2.663.19.448.521 1.05 1.08 1.246.885.32 1.694-.244 2.122-.715l1.358-1.493c.858.64 1.708 1.271 2.558 1.921l.033.025c1.153.865 1.805 1.354 2.495 1.592.728.25 1.361.151 1.88-.253.506-.395.748-.987.818-1.486.308-2.17.63-4.335.919-6.507.316-2.378.63-4.764.867-7.158.094-.952.187-1.912.272-2.875.046-.523.153-1.308-.327-1.83a1.743 1.743 0 0 0-.965-.465z"
      fill={color}
    />
    <path
      d="M8.554 11.638c1.128-.528 2.259-1.025 3.396-1.518 1.655-.719 3.318-1.421 4.986-2.108.769-.316 1.542-.625 2.318-.925.206-.08.424-.148.61-.288-.012.008-.195.133-.293.196a83.332 83.332 0 0 0-3.038 2.506c-1.218 1.053-2.418 2.128-3.583 3.242-.698.668-1.39 1.34-2.062 2.034-.595.615-1.161 1.288-1.541 2.077-.23.478-.232.942-.045 1.433.324.851.72 1.671 1.094 2.502.278.616.549 1.235.83 1.85.078.169.156.338.235.506.007.015-.138-.11-.165-.136-.8-.78-1.606-1.551-2.414-2.321-.155-.148-.312-.294-.47-.439-.268-.246-.608-.524-1.015-.432-.408.091-.662.485-.714.894-.053.414-.01.816.036 1.229.018.16-.095-.002-.155-.027l-3.772-1.582c-.26-.109-1.212-.467-1.054-.72.088-.142.377-.191.528-.241z"
      fill={color}
      fillOpacity="0.6"
    />
  </svg>
);

const CheckIcon = ({ size = 20, color = '#22c55e' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path
      d="M20 6L9 17L4 12"
      stroke={color}
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const UserIcon = ({ size = 24, color = '#a855f7' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="8" r="3" fill={color} fillOpacity="0.2" stroke={color} strokeWidth="2"/>
    <path
      d="M6 21V19C6 16.7909 7.79086 15 10 15H14C16.2091 15 18 16.7909 18 19V21"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
    />
  </svg>
);

const LoadingIcon = ({ size = 24, color = '#a855f7' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ animation: 'spin 1s linear infinite' }}>
    <path
      d="M12 2V6M12 18V22M4.93 4.93L7.76 7.76M16.24 16.24L19.07 19.07M2 12H6M18 12H22M4.93 19.07L7.76 16.24M16.24 7.76L19.07 4.93"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      opacity="0.3"
    />
    <path
      d="M12 2V6"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
    />
  </svg>
);

// Styles
const styles = {
  container: {
    maxWidth: '400px',
    margin: '0 auto',
    padding: '20px',
  },

  card: {
    background: 'rgba(255, 255, 255, 0.05)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '24px',
    padding: '32px',
    position: 'relative',
    overflow: 'hidden',
    animation: 'slideUp 0.6s ease-out',
  },

  glow: {
    position: 'absolute',
    top: '-50%',
    left: '-50%',
    width: '200%',
    height: '200%',
    background: 'radial-gradient(circle at center, rgba(168, 85, 247, 0.1) 0%, transparent 70%)',
    animation: 'pulse 4s ease-in-out infinite',
  },

  header: {
    textAlign: 'center',
    marginBottom: '32px',
    position: 'relative',
    zIndex: 1,
  },

  iconContainer: {
    width: '64px',
    height: '64px',
    margin: '0 auto 20px',
    background: 'linear-gradient(135deg, #0088cc 0%, #0077bb 100%)',
    borderRadius: '16px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 8px 24px rgba(0, 136, 204, 0.3)',
    animation: 'float 3s ease-in-out infinite',
  },

  title: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#fff',
    marginBottom: '8px',
  },

  subtitle: {
    fontSize: '14px',
    color: 'rgba(255, 255, 255, 0.6)',
    lineHeight: '1.5',
  },

  userInfo: {
    background: 'rgba(255, 255, 255, 0.03)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '16px',
    padding: '20px',
    marginBottom: '24px',
    position: 'relative',
    zIndex: 1,
  },

  userRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    marginBottom: '16px',
  },

  avatar: {
    width: '48px',
    height: '48px',
    background: 'linear-gradient(135deg, #a855f7 0%, #ec4899 100%)',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '20px',
    fontWeight: '700',
    color: '#fff',
    flexShrink: 0,
  },

  userDetails: {
    flex: 1,
  },

  userName: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#fff',
    marginBottom: '4px',
  },

  userId: {
    fontSize: '14px',
    color: 'rgba(255, 255, 255, 0.5)',
  },

  infoRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 0',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
  },

  infoLabel: {
    fontSize: '14px',
    color: 'rgba(255, 255, 255, 0.6)',
  },

  infoValue: {
    fontSize: '14px',
    color: '#fff',
    fontWeight: '500',
  },

  button: {
    width: '100%',
    padding: '16px 24px',
    background: 'linear-gradient(135deg, #0088cc 0%, #0077bb 100%)',
    border: 'none',
    borderRadius: '12px',
    color: '#fff',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    position: 'relative',
    overflow: 'hidden',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
  },

  buttonHover: {
    transform: 'translateY(-2px)',
    boxShadow: '0 10px 30px rgba(0, 136, 204, 0.4)',
  },

  buttonDisabled: {
    opacity: 0.7,
    cursor: 'not-allowed',
    background: 'rgba(255, 255, 255, 0.1)',
  },

  buttonSuccess: {
    background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
  },

  loadingText: {
    fontSize: '16px',
    color: 'rgba(255, 255, 255, 0.7)',
    textAlign: 'center',
    marginTop: '20px',
  },

  error: {
    background: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '12px',
    padding: '16px',
    marginTop: '16px',
    color: '#fff',
    fontSize: '14px',
    textAlign: 'center',
  },

  premiumBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    background: 'linear-gradient(135deg, rgba(251, 191, 36, 0.1), rgba(245, 158, 11, 0.1))',
    border: '1px solid rgba(251, 191, 36, 0.3)',
    borderRadius: '8px',
    padding: '4px 8px',
    fontSize: '12px',
    fontWeight: '600',
    color: '#fbbf24',
  },
};

// Keyframes
const keyframes = `
  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(30px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes pulse {
    0%, 100% {
      opacity: 0.3;
    }
    50% {
      opacity: 0.5;
    }
  }

  @keyframes float {
    0%, 100% {
      transform: translateY(0);
    }
    50% {
      transform: translateY(-10px);
    }
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
`;

// TelegramAuth Component
const TelegramAuth = ({
  onSuccess,
  onError,
  botUsername = 'TeleeBoost_bot',
  buttonText = 'Login with Telegram',
  showUserInfo = true,
  autoLogin = true,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Initialize Telegram WebApp
  useEffect(() => {
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;

      // Expand to full height
      tg.expand();

      // Set theme
      tg.setHeaderColor('#1a0033');
      tg.setBackgroundColor('#000000');

      // Ready
      tg.ready();

      // Auto login if enabled
      if (autoLogin && tg.initDataUnsafe?.user) {
        handleAuth();
      }
    }
  }, [autoLogin]);

  const handleAuth = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const tg = window.Telegram.WebApp;

      if (!tg || !tg.initData) {
        throw new Error('Telegram WebApp not available');
      }

      // Get user data
      const userData = tg.initDataUnsafe.user;

      if (!userData) {
        throw new Error('User data not found');
      }

      // Send to backend
      const response = await fetch('/api/auth/telegram', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          initData: tg.initData,
          referralCode: tg.initDataUnsafe.start_param,
        }),
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Authentication failed');
      }

      // Save token
      localStorage.setItem('auth_token', data.data.tokens.access_token);
      localStorage.setItem('refresh_token', data.data.tokens.refresh_token);

      // Update state
      setUser(data.data.user);
      setIsAuthenticated(true);

      // Callback
      onSuccess?.(data.data);

      // Show success button briefly
      setTimeout(() => {
        // Close or redirect
        if (tg.close) {
          tg.close();
        } else {
          window.location.href = '/';
        }
      }, 1500);

    } catch (err) {
      setError(err.message);
      onError?.(err);
    } finally {
      setIsLoading(false);
    }
  }, [onSuccess, onError]);

  const formatUserId = (id) => {
    return `#${String(id).padStart(9, '0')}`;
  };

  const getInitials = (user) => {
    const first = user.first_name?.[0] || '';
    const last = user.last_name?.[0] || '';
    return (first + last).toUpperCase() || '?';
  };

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: keyframes }} />

      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.glow} />

          {/* Header */}
          <div style={styles.header}>
            <div style={styles.iconContainer}>
              <TelegramIcon size={32} />
            </div>
            <h2 style={styles.title}>
              {isAuthenticated ? 'Welcome!' : 'Telegram Login'}
            </h2>
            <p style={styles.subtitle}>
              {isAuthenticated
                ? 'You have successfully logged in'
                : 'Secure authentication via Telegram'
              }
            </p>
          </div>

          {/* User Info */}
          {showUserInfo && user && (
            <div style={styles.userInfo}>
              <div style={styles.userRow}>
                <div style={styles.avatar}>
                  {getInitials(user)}
                </div>
                <div style={styles.userDetails}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={styles.userName}>
                      {user.first_name} {user.last_name}
                    </div>
                    {user.is_premium && (
                      <div style={styles.premiumBadge}>
                        ⭐ Premium
                      </div>
                    )}
                  </div>
                  <div style={styles.userId}>
                    {formatUserId(user.telegram_id)}
                  </div>
                </div>
              </div>

              <div>
                {user.username && (
                  <div style={styles.infoRow}>
                    <span style={styles.infoLabel}>Username</span>
                    <span style={styles.infoValue}>@{user.username}</span>
                  </div>
                )}
                <div style={{ ...styles.infoRow, borderBottom: 'none' }}>
                  <span style={styles.infoLabel}>Language</span>
                  <span style={styles.infoValue}>
                    {user.language_code?.toUpperCase() || 'EN'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Button */}
          {!isAuthenticated && (
            <button
              style={{
                ...styles.button,
                ...(isLoading ? styles.buttonDisabled : {}),
              }}
              onClick={handleAuth}
              disabled={isLoading}
              onMouseEnter={(e) => {
                if (!isLoading) {
                  e.target.style.transform = styles.buttonHover.transform;
                  e.target.style.boxShadow = styles.buttonHover.boxShadow;
                }
              }}
              onMouseLeave={(e) => {
                e.target.style.transform = 'none';
                e.target.style.boxShadow = 'none';
              }}
            >
              {isLoading ? (
                <>
                  <LoadingIcon size={20} />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <TelegramIcon size={20} />
                  <span>{buttonText}</span>
                </>
              )}
            </button>
          )}

          {isAuthenticated && (
            <button
              style={{
                ...styles.button,
                ...styles.buttonSuccess,
              }}
            >
              <CheckIcon size={20} />
              <span>Authenticated</span>
            </button>
          )}

          {/* Error */}
          {error && (
            <div style={styles.error}>
              {error}
            </div>
          )}

          {/* Loading text */}
          {isLoading && (
            <p style={styles.loadingText}>
              Please wait while we verify your Telegram account...
            </p>
          )}
        </div>
      </div>
    </>
  );
};

// Hook for Telegram auth
export const useTelegramAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const token = localStorage.getItem('auth_token');

      if (!token) {
        setIsAuthenticated(false);
        setIsLoading(false);
        return;
      }

      const response = await fetch('/api/auth/verify', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();

      if (data.success && data.data.valid) {
        setIsAuthenticated(true);
        setUser(data.data.user);
      } else {
        setIsAuthenticated(false);
        localStorage.removeItem('auth_token');
      }
    } catch (err) {
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async () => {
    // Trigger Telegram auth
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.openTelegramLink(`https://t.me/${botUsername}?start=auth`);
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
    setIsAuthenticated(false);
    setUser(null);
  };

  return {
    isAuthenticated,
    user,
    isLoading,
    login,
    logout,
    checkAuth,
  };
};

export default TelegramAuth;