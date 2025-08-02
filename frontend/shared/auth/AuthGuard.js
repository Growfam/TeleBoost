import React, { useEffect, useState } from 'react';

// SVG Icons
const ShieldIcon = ({ size = 24, color = '#a855f7' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path
      d="M12 2L4 7V12C4 16.5 6.84 20.74 11 21.92C11.35 22.03 11.65 22.03 12 21.92C16.16 20.74 20 16.5 20 12V7L12 2Z"
      fill={color}
      fillOpacity="0.1"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M9 12L11 14L15 10"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const LockIcon = ({ size = 20, color = '#fff' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <rect x="5" y="11" width="14" height="10" rx="2" fill={color} fillOpacity="0.1" stroke={color} strokeWidth="2"/>
    <path d="M7 11V7C7 4.23858 9.23858 2 12 2C14.7614 2 17 4.23858 17 7V11" stroke={color} strokeWidth="2" strokeLinecap="round"/>
    <circle cx="12" cy="16" r="1" fill={color}/>
  </svg>
);

const AlertIcon = ({ size = 20, color = '#ef4444' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path
      d="M12 2L2 20H22L12 2Z"
      fill={color}
      fillOpacity="0.1"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path d="M12 9V13" stroke={color} strokeWidth="2" strokeLinecap="round"/>
    <circle cx="12" cy="17" r="0.5" fill={color} stroke={color}/>
  </svg>
);

// Styles
const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #000 0%, #1a0033 50%, #000 100%)',
    position: 'relative',
    overflow: 'hidden',
  },

  particles: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
  },

  particle: {
    position: 'absolute',
    width: '4px',
    height: '4px',
    background: 'rgba(168, 85, 247, 0.4)',
    borderRadius: '50%',
    animation: 'float 15s infinite linear',
  },

  card: {
    width: '90%',
    maxWidth: '400px',
    padding: '40px',
    background: 'rgba(255, 255, 255, 0.05)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '24px',
    position: 'relative',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
    animation: 'slideUp 0.6s ease-out',
  },

  iconContainer: {
    width: '80px',
    height: '80px',
    margin: '0 auto 24px',
    background: 'rgba(168, 85, 247, 0.1)',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    animation: 'pulse 2s ease-in-out infinite',
  },

  iconGlow: {
    position: 'absolute',
    inset: '-20px',
    background: 'radial-gradient(circle, rgba(168, 85, 247, 0.2) 0%, transparent 70%)',
    borderRadius: '50%',
    animation: 'rotate 10s linear infinite',
  },

  title: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#fff',
    textAlign: 'center',
    marginBottom: '12px',
    background: 'linear-gradient(135deg, #fff 0%, #a78bfa 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text',
  },

  subtitle: {
    fontSize: '16px',
    color: 'rgba(255, 255, 255, 0.7)',
    textAlign: 'center',
    marginBottom: '32px',
    lineHeight: '1.5',
  },

  loader: {
    width: '40px',
    height: '40px',
    margin: '0 auto',
    border: '3px solid rgba(255, 255, 255, 0.1)',
    borderTop: '3px solid #a855f7',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },

  errorContainer: {
    background: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '12px',
    padding: '16px',
    marginBottom: '24px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },

  errorText: {
    color: '#fff',
    fontSize: '14px',
    flex: 1,
  },

  button: {
    width: '100%',
    padding: '14px 24px',
    background: 'linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)',
    border: 'none',
    borderRadius: '12px',
    color: '#fff',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    position: 'relative',
    overflow: 'hidden',
  },

  buttonHover: {
    transform: 'translateY(-2px)',
    boxShadow: '0 10px 30px rgba(168, 85, 247, 0.4)',
  },

  buttonDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },

  progressBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    height: '3px',
    background: 'linear-gradient(90deg, #a855f7, #ec4899)',
    animation: 'progress 2s ease-out',
  },
};

// Keyframes
const keyframes = `
  @keyframes float {
    0% {
      transform: translateY(100vh) translateX(0);
      opacity: 0;
    }
    10% {
      opacity: 1;
    }
    90% {
      opacity: 1;
    }
    100% {
      transform: translateY(-100vh) translateX(100px);
      opacity: 0;
    }
  }

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
      transform: scale(1);
      opacity: 1;
    }
    50% {
      transform: scale(1.05);
      opacity: 0.8;
    }
  }

  @keyframes rotate {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
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

  @keyframes progress {
    from {
      width: 0%;
    }
    to {
      width: 100%;
    }
  }
`;

// AuthGuard Component
const AuthGuard = ({
  children,
  isAuthenticated,
  isLoading = false,
  error = null,
  onRetry = null,
  redirectTo = '/login'
}) => {
  const [showContent, setShowContent] = useState(false);
  const [particles] = useState(Array.from({ length: 5 }, (_, i) => ({
    id: i,
    left: Math.random() * 100,
    delay: Math.random() * 10,
    duration: 10 + Math.random() * 10,
  })));

  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      // Delay to show animation
      setTimeout(() => setShowContent(true), 500);
    }
  }, [isAuthenticated, isLoading]);

  // If authenticated, show children
  if (isAuthenticated && showContent) {
    return children;
  }

  // Show loading/error/redirect UI
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: keyframes }} />

      <div style={styles.container}>
        {/* Background particles */}
        <div style={styles.particles}>
          {particles.map(p => (
            <div
              key={p.id}
              style={{
                ...styles.particle,
                left: `${p.left}%`,
                animationDelay: `${p.delay}s`,
                animationDuration: `${p.duration}s`,
              }}
            />
          ))}
        </div>

        <div style={styles.card}>
          {/* Progress bar */}
          {isLoading && <div style={styles.progressBar} />}

          {/* Icon */}
          <div style={styles.iconContainer}>
            <div style={styles.iconGlow} />
            {error ? (
              <AlertIcon size={40} />
            ) : isLoading ? (
              <ShieldIcon size={40} />
            ) : (
              <LockIcon size={40} />
            )}
          </div>

          {/* Content */}
          {error ? (
            <>
              <h2 style={styles.title}>Access Error</h2>
              <div style={styles.errorContainer}>
                <AlertIcon size={20} />
                <p style={styles.errorText}>{error}</p>
              </div>
              {onRetry && (
                <button
                  style={styles.button}
                  onClick={onRetry}
                  onMouseEnter={(e) => {
                    e.target.style.transform = styles.buttonHover.transform;
                    e.target.style.boxShadow = styles.buttonHover.boxShadow;
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.transform = 'none';
                    e.target.style.boxShadow = 'none';
                  }}
                >
                  Try Again
                </button>
              )}
            </>
          ) : isLoading ? (
            <>
              <h2 style={styles.title}>Authenticating</h2>
              <p style={styles.subtitle}>
                Verifying your access credentials...
              </p>
              <div style={styles.loader} />
            </>
          ) : (
            <>
              <h2 style={styles.title}>Authentication Required</h2>
              <p style={styles.subtitle}>
                Please login to access this page
              </p>
              <button
                style={styles.button}
                onClick={() => window.location.href = redirectTo}
                onMouseEnter={(e) => {
                  e.target.style.transform = styles.buttonHover.transform;
                  e.target.style.boxShadow = styles.buttonHover.boxShadow;
                }}
                onMouseLeave={(e) => {
                  e.target.style.transform = 'none';
                  e.target.style.boxShadow = 'none';
                }}
              >
                Go to Login
              </button>
            </>
          )}
        </div>
      </div>
    </>
  );
};

// HOC для захисту компонентів
export const withAuth = (Component) => {
  return (props) => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
      checkAuth();
    }, []);

    const checkAuth = async () => {
      try {
        // Check localStorage for token
        const token = localStorage.getItem('auth_token');

        if (!token) {
          setIsAuthenticated(false);
          setIsLoading(false);
          return;
        }

        // Verify token with API
        const response = await fetch('/api/auth/verify', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        const data = await response.json();

        if (data.success && data.data.valid) {
          setIsAuthenticated(true);
        } else {
          setIsAuthenticated(false);
          localStorage.removeItem('auth_token');
        }
      } catch (err) {
        setError('Failed to verify authentication');
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    return (
      <AuthGuard
        isAuthenticated={isAuthenticated}
        isLoading={isLoading}
        error={error}
        onRetry={checkAuth}
      >
        <Component {...props} />
      </AuthGuard>
    );
  };
};

export default AuthGuard;