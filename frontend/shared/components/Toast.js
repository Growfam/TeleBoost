import React, { useState, useEffect, useCallback, createContext, useContext } from 'react';

// Toast types
const TOAST_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
  LOADING: 'loading'
};

// SVG Icons
const Icons = {
  success: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M10 0C4.48 0 0 4.48 0 10s4.48 10 10 10 10-4.48 10-10S15.52 0 10 0zm-1 15l-5-5 1.41-1.41L9 12.17l7.59-7.59L18 6l-9 9z" fill="#30D158"/>
    </svg>
  ),
  error: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M10 0C4.48 0 0 4.48 0 10s4.48 10 10 10 10-4.48 10-10S15.52 0 10 0zm1 15H9v-2h2v2zm0-4H9V5h2v6z" fill="#FF3B30"/>
    </svg>
  ),
  warning: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M10 2a8 8 0 100 16 8 8 0 000-16zm1 11h-2v-2h2v2zm0-4h-2V5h2v4z" fill="#FF9500"/>
    </svg>
  ),
  info: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M10 0C4.5 0 0 4.5 0 10s4.5 10 10 10 10-4.5 10-10S15.5 0 10 0zm1 15h-2v-6h2v6zm0-8h-2V5h2v2z" fill="#007AFF"/>
    </svg>
  ),
  loading: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="toast-spinner">
      <path d="M10 0C4.5 0 0 4.5 0 10h2c0-4.4 3.6-8 8-8V0z" fill="#007AFF"/>
    </svg>
  )
};

// Styles
const styles = {
  container: {
    position: 'fixed',
    top: '20px',
    left: '50%',
    transform: 'translateX(-50%)',
    zIndex: 9999,
    pointerEvents: 'none',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '12px',
    maxWidth: '430px',
    width: '100%',
    padding: '0 20px',
  },

  toast: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '12px',
    padding: '16px 20px',
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    borderRadius: '16px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    boxShadow: '0 4px 24px rgba(0, 0, 0, 0.1)',
    pointerEvents: 'all',
    cursor: 'pointer',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    position: 'relative',
    overflow: 'hidden',
  },

  toastEntering: {
    animation: 'slideDown 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards',
  },

  toastExiting: {
    animation: 'slideUp 0.4s cubic-bezier(0.4, 0, 1, 1) forwards',
  },

  icon: {
    width: '20px',
    height: '20px',
    flexShrink: 0,
  },

  message: {
    fontSize: '15px',
    fontWeight: 500,
    color: 'rgba(255, 255, 255, 0.9)',
    letterSpacing: '-0.01em',
    margin: 0,
    lineHeight: '1.4',
  },

  progressBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    height: '3px',
    background: 'rgba(255, 255, 255, 0.3)',
    borderRadius: '0 0 16px 16px',
    transition: 'width linear',
  }
};

// Animations keyframes
const animationStyles = `
  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateY(-100%);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes slideUp {
    from {
      opacity: 1;
      transform: translateY(0);
    }
    to {
      opacity: 0;
      transform: translateY(-100%);
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

  .toast-spinner {
    animation: spin 1s linear infinite;
  }
`;

// Toast Context
const ToastContext = createContext(null);

// Toast Provider Component
export const ToastProvider = ({ children, position = 'top', maxToasts = 3 }) => {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = TOAST_TYPES.INFO, duration = 3000) => {
    const id = Date.now() + Math.random();
    const newToast = {
      id,
      message,
      type,
      duration,
      createdAt: Date.now(),
    };

    setToasts(prev => {
      const updated = [...prev, newToast];
      // Keep only the latest maxToasts
      return updated.slice(-maxToasts);
    });

    // Auto remove toast after duration
    if (duration > 0 && type !== TOAST_TYPES.LOADING) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }

    return id;
  }, [maxToasts]);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.map(toast =>
      toast.id === id ? { ...toast, removing: true } : toast
    ));

    // Remove from DOM after animation
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== id));
    }, 400);
  }, []);

  const removeAllToasts = useCallback(() => {
    setToasts([]);
  }, []);

  const updateToast = useCallback((id, updates) => {
    setToasts(prev => prev.map(toast =>
      toast.id === id ? { ...toast, ...updates } : toast
    ));
  }, []);

  const value = {
    toasts,
    addToast,
    removeToast,
    removeAllToasts,
    updateToast,
    // Helper methods
    success: (message, duration) => addToast(message, TOAST_TYPES.SUCCESS, duration),
    error: (message, duration) => addToast(message, TOAST_TYPES.ERROR, duration),
    warning: (message, duration) => addToast(message, TOAST_TYPES.WARNING, duration),
    info: (message, duration) => addToast(message, TOAST_TYPES.INFO, duration),
    loading: (message) => addToast(message, TOAST_TYPES.LOADING, 0),
  };

  const containerStyle = {
    ...styles.container,
    ...(position === 'bottom' && {
      top: 'auto',
      bottom: '20px',
    }),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <style dangerouslySetInnerHTML={{ __html: animationStyles }} />
      <div style={containerStyle}>
        {toasts.map(toast => (
          <Toast
            key={toast.id}
            toast={toast}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
};

// Individual Toast Component
const Toast = ({ toast, onClose }) => {
  const [progress, setProgress] = useState(100);
  const { message, type, duration, removing, createdAt } = toast;

  useEffect(() => {
    if (duration > 0 && type !== TOAST_TYPES.LOADING) {
      const interval = 100; // Update every 100ms
      const decrement = (interval / duration) * 100;

      const timer = setInterval(() => {
        setProgress(prev => {
          const newProgress = prev - decrement;
          if (newProgress <= 0) {
            clearInterval(timer);
            return 0;
          }
          return newProgress;
        });
      }, interval);

      return () => clearInterval(timer);
    }
  }, [duration, type]);

  const toastStyle = {
    ...styles.toast,
    ...(removing ? styles.toastExiting : styles.toastEntering),
  };

  return (
    <div
      style={toastStyle}
      onClick={onClose}
      role="alert"
      aria-live="polite"
    >
      <div style={styles.icon}>
        {Icons[type] || Icons.info}
      </div>
      <p style={styles.message}>{message}</p>

      {duration > 0 && type !== TOAST_TYPES.LOADING && (
        <div
          style={{
            ...styles.progressBar,
            width: `${progress}%`,
            transitionDuration: '100ms',
          }}
        />
      )}
    </div>
  );
};

// Hook to use toast
export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
};

// Standalone toast function for use outside React components
let globalToastInstance = null;

export const toast = {
  setInstance: (instance) => {
    globalToastInstance = instance;
  },
  success: (message, duration) => {
    globalToastInstance?.success(message, duration);
  },
  error: (message, duration) => {
    globalToastInstance?.error(message, duration);
  },
  warning: (message, duration) => {
    globalToastInstance?.warning(message, duration);
  },
  info: (message, duration) => {
    globalToastInstance?.info(message, duration);
  },
  loading: (message) => {
    return globalToastInstance?.loading(message);
  },
  dismiss: (id) => {
    globalToastInstance?.removeToast(id);
  },
  dismissAll: () => {
    globalToastInstance?.removeAllToasts();
  }
};

// Example usage component
export const ToastDemo = () => {
  const { success, error, warning, info, loading, removeToast } = useToast();

  // Set global instance
  useEffect(() => {
    toast.setInstance({ success, error, warning, info, loading, removeToast, removeAllToasts: toast.dismissAll });
  }, [success, error, warning, info, loading, removeToast]);

  const handleLoadingDemo = async () => {
    const loadingId = loading('Processing payment...');

    // Simulate async operation
    setTimeout(() => {
      removeToast(loadingId);
      success('Payment completed successfully!');
    }, 3000);
  };

  return (
    <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <button onClick={() => success('Operation completed successfully!')}>
        Show Success
      </button>
      <button onClick={() => error('Something went wrong. Please try again.')}>
        Show Error
      </button>
      <button onClick={() => warning('Your session will expire in 5 minutes')}>
        Show Warning
      </button>
      <button onClick={() => info('New update available. Refresh to see changes.')}>
        Show Info
      </button>
      <button onClick={handleLoadingDemo}>
        Show Loading
      </button>
    </div>
  );
};

// Export everything
export default Toast;