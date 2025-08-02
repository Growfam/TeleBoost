import React, { memo, useEffect, useState } from 'react';

// Styles object
const styles = {
  // Container styles
  container: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(0, 0, 0, 0.8)',
    backdropFilter: 'blur(10px)',
    WebkitBackdropFilter: 'blur(10px)',
    zIndex: 9999,
    animation: 'fadeIn 0.3s ease-out',
  },

  // Inner wrapper for proper centering
  wrapper: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '24px',
  },

  // Dots container
  dotsContainer: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    padding: '20px',
    background: 'rgba(255, 255, 255, 0.05)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    borderRadius: '20px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
  },

  // Individual dot
  dot: {
    width: '16px',
    height: '16px',
    background: 'linear-gradient(135deg, #a855f7, #ec4899)',
    borderRadius: '50%',
    animation: 'morph 1.5s ease-in-out infinite',
    position: 'relative',
    boxShadow: '0 0 20px rgba(168, 85, 247, 0.5)',
  },

  // Loading text
  loadingText: {
    fontSize: '14px',
    fontWeight: 500,
    color: 'rgba(255, 255, 255, 0.8)',
    letterSpacing: '0.5px',
    animation: 'pulse 2s ease-in-out infinite',
  },

  // Progress bar container
  progressContainer: {
    width: '200px',
    height: '4px',
    background: 'rgba(255, 255, 255, 0.1)',
    borderRadius: '2px',
    overflow: 'hidden',
    position: 'relative',
  },

  // Progress bar fill
  progressBar: {
    height: '100%',
    background: 'linear-gradient(90deg, #a855f7, #ec4899)',
    borderRadius: '2px',
    transition: 'width 0.3s ease-out',
    boxShadow: '0 0 10px rgba(168, 85, 247, 0.5)',
  },

  // Inline loader styles
  inline: {
    container: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '8px',
      padding: '8px 16px',
      background: 'rgba(255, 255, 255, 0.05)',
      backdropFilter: 'blur(10px)',
      WebkitBackdropFilter: 'blur(10px)',
      borderRadius: '12px',
      border: '1px solid rgba(255, 255, 255, 0.1)',
    },
    dotsContainer: {
      display: 'flex',
      gap: '6px',
    },
    dot: {
      width: '8px',
      height: '8px',
      background: 'linear-gradient(135deg, #a855f7, #ec4899)',
      borderRadius: '50%',
      animation: 'morphSmall 1.5s ease-in-out infinite',
    },
    text: {
      fontSize: '12px',
      color: 'rgba(255, 255, 255, 0.7)',
    },
  },

  // Button loader styles
  button: {
    container: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '8px',
    },
    dotsContainer: {
      display: 'flex',
      gap: '4px',
    },
    dot: {
      width: '6px',
      height: '6px',
      background: '#fff',
      borderRadius: '50%',
      animation: 'morphButton 1.2s ease-in-out infinite',
    },
  },

  // Skeleton loader styles
  skeleton: {
    container: {
      width: '100%',
      borderRadius: '12px',
      background: 'rgba(255, 255, 255, 0.05)',
      backdropFilter: 'blur(10px)',
      WebkitBackdropFilter: 'blur(10px)',
      overflow: 'hidden',
      position: 'relative',
    },
    shimmer: {
      position: 'absolute',
      top: 0,
      left: '-100%',
      width: '100%',
      height: '100%',
      background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent)',
      animation: 'shimmer 2s infinite',
    },
  },
};

// Keyframes
const keyframes = `
  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  @keyframes morph {
    0%, 100% {
      transform: scale(1) translateY(0);
      filter: blur(0);
      opacity: 1;
    }
    50% {
      transform: scale(1.5) translateY(-20px);
      filter: blur(2px);
      opacity: 0.7;
    }
  }

  @keyframes morphSmall {
    0%, 100% {
      transform: scale(1) translateY(0);
      opacity: 1;
    }
    50% {
      transform: scale(1.3) translateY(-8px);
      opacity: 0.6;
    }
  }

  @keyframes morphButton {
    0%, 100% {
      transform: scale(1);
      opacity: 0.5;
    }
    50% {
      transform: scale(1.2);
      opacity: 1;
    }
  }

  @keyframes pulse {
    0%, 100% {
      opacity: 0.8;
    }
    50% {
      opacity: 0.4;
    }
  }

  @keyframes shimmer {
    0% {
      left: -100%;
    }
    100% {
      left: 200%;
    }
  }
`;

// Main Loader Component
const Loader = memo(({
  fullScreen = true,
  text = 'Loading...',
  showProgress = false,
  progress = 0,
  size = 'medium',
  dots = 4,
}) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!fullScreen) {
    return null;
  }

  const dotElements = Array.from({ length: dots }, (_, i) => (
    <div
      key={i}
      style={{
        ...styles.dot,
        animationDelay: `${i * 0.15}s`,
        ...(size === 'small' ? { width: '12px', height: '12px' } : {}),
        ...(size === 'large' ? { width: '20px', height: '20px' } : {}),
      }}
    />
  ));

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: keyframes }} />

      <div style={styles.container}>
        <div style={styles.wrapper}>
          <div style={styles.dotsContainer}>
            {dotElements}
          </div>

          {text && (
            <div style={styles.loadingText}>{text}</div>
          )}

          {showProgress && (
            <div style={styles.progressContainer}>
              <div
                style={{
                  ...styles.progressBar,
                  width: `${Math.min(100, Math.max(0, progress))}%`,
                }}
              />
            </div>
          )}
        </div>
      </div>
    </>
  );
});

Loader.displayName = 'Loader';

// Inline Loader Component
export const InlineLoader = memo(({ text = 'Loading', dots = 3 }) => {
  const dotElements = Array.from({ length: dots }, (_, i) => (
    <div
      key={i}
      style={{
        ...styles.inline.dot,
        animationDelay: `${i * 0.15}s`,
      }}
    />
  ));

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: keyframes }} />

      <div style={styles.inline.container}>
        <div style={styles.inline.dotsContainer}>
          {dotElements}
        </div>
        {text && <span style={styles.inline.text}>{text}</span>}
      </div>
    </>
  );
});

InlineLoader.displayName = 'InlineLoader';

// Button Loader Component
export const ButtonLoader = memo(({ text = '' }) => {
  const dotElements = Array.from({ length: 3 }, (_, i) => (
    <div
      key={i}
      style={{
        ...styles.button.dot,
        animationDelay: `${i * 0.1}s`,
      }}
    />
  ));

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: keyframes }} />

      <div style={styles.button.container}>
        <div style={styles.button.dotsContainer}>
          {dotElements}
        </div>
        {text && <span style={{ marginLeft: '8px', color: '#fff' }}>{text}</span>}
      </div>
    </>
  );
});

ButtonLoader.displayName = 'ButtonLoader';

// Skeleton Loader Component
export const SkeletonLoader = memo(({
  height = '20px',
  width = '100%',
  borderRadius = '12px'
}) => {
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: keyframes }} />

      <div
        style={{
          ...styles.skeleton.container,
          height,
          width,
          borderRadius,
        }}
      >
        <div style={styles.skeleton.shimmer} />
      </div>
    </>
  );
});

SkeletonLoader.displayName = 'SkeletonLoader';

// Loading Overlay Component
export const LoadingOverlay = memo(({
  visible = false,
  text = 'Loading...',
  blur = true,
}) => {
  if (!visible) return null;

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: keyframes }} />

      <div
        style={{
          ...styles.container,
          background: blur ? 'rgba(0, 0, 0, 0.5)' : 'transparent',
          backdropFilter: blur ? 'blur(5px)' : 'none',
          WebkitBackdropFilter: blur ? 'blur(5px)' : 'none',
        }}
      >
        <div style={styles.wrapper}>
          <div style={styles.dotsContainer}>
            {Array.from({ length: 4 }, (_, i) => (
              <div
                key={i}
                style={{
                  ...styles.dot,
                  animationDelay: `${i * 0.15}s`,
                }}
              />
            ))}
          </div>
          {text && <div style={styles.loadingText}>{text}</div>}
        </div>
      </div>
    </>
  );
});

LoadingOverlay.displayName = 'LoadingOverlay';

// Export default
export default Loader;