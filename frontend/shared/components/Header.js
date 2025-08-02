import React, { useState, useEffect, memo } from 'react';

// Styles object - всі стилі в одному місці
const styles = {
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px',
    background: 'rgba(255, 255, 255, 0.05)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)', // Safari support
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '20px',
    position: 'relative',
    overflow: 'hidden',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    margin: '0 auto',
    maxWidth: '430px',
  },

  sweepAnimation: {
    content: '""',
    position: 'absolute',
    top: 0,
    left: '-100%',
    width: '100%',
    height: '100%',
    background: 'linear-gradient(90deg, transparent, rgba(168, 85, 247, 0.2), transparent)',
    animation: 'sweep 3s infinite',
    pointerEvents: 'none',
  },

  logo: {
    fontSize: '24px',
    fontWeight: 700,
    background: 'linear-gradient(135deg, #a78bfa 0%, #c084fc 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text',
    textFillColor: 'transparent',
    letterSpacing: '-0.02em',
    cursor: 'pointer',
    userSelect: 'none',
    position: 'relative',
    zIndex: 1,
    transition: 'transform 0.3s ease',
  },

  logoHover: {
    transform: 'scale(1.05)',
  },

  menuButton: {
    width: '40px',
    height: '40px',
    background: 'rgba(255, 255, 255, 0.1)',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    borderRadius: '12px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '4px',
    cursor: 'pointer',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    position: 'relative',
    zIndex: 1,
    outline: 'none',
  },

  menuButtonHover: {
    background: 'rgba(168, 85, 247, 0.2)',
    transform: 'scale(1.05)',
    borderColor: 'rgba(168, 85, 247, 0.3)',
  },

  menuButtonActive: {
    transform: 'scale(0.95)',
  },

  menuLine: {
    width: '20px',
    height: '2px',
    background: '#fff',
    borderRadius: '1px',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    transformOrigin: 'center',
  },

  menuLineTop: {
    transform: 'translateY(-2px)',
  },

  menuLineBottom: {
    transform: 'translateY(2px)',
  },

  // Стилі для відкритого меню
  menuOpen: {
    menuLineTop: {
      transform: 'rotate(45deg) translateY(0)',
    },
    menuLineMiddle: {
      opacity: 0,
      transform: 'scaleX(0)',
    },
    menuLineBottom: {
      transform: 'rotate(-45deg) translateY(0)',
    },
  },

  // Notification badge
  notificationBadge: {
    position: 'absolute',
    top: '-4px',
    right: '-4px',
    width: '12px',
    height: '12px',
    background: '#ef4444',
    borderRadius: '50%',
    border: '2px solid rgba(0, 0, 0, 0.5)',
    animation: 'pulse 2s ease-in-out infinite',
  },
};

// Keyframes для анімацій
const keyframes = `
  @keyframes sweep {
    0% { left: -100%; }
    100% { left: 100%; }
  }

  @keyframes pulse {
    0%, 100% {
      transform: scale(1);
      opacity: 1;
    }
    50% {
      transform: scale(1.2);
      opacity: 0.8;
    }
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(-20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
`;

// Header Component
const Header = memo(({
  onMenuClick,
  showNotification = false,
  userName = 'Guest',
  balance = 0,
  currency = 'USDT'
}) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isHoveringLogo, setIsHoveringLogo] = useState(false);
  const [isHoveringMenu, setIsHoveringMenu] = useState(false);
  const [isMenuActive, setIsMenuActive] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Animation on mount
  useEffect(() => {
    setMounted(true);
  }, []);

  // Handle menu click
  const handleMenuClick = () => {
    setIsMenuOpen(!isMenuOpen);
    onMenuClick?.(!isMenuOpen);
  };

  return (
    <>
      {/* Inject keyframes */}
      <style dangerouslySetInnerHTML={{ __html: keyframes }} />

      {/* Header */}
      <header
        style={{
          ...styles.header,
          animation: mounted ? 'slideIn 0.6s ease-out' : 'none',
        }}
      >
        {/* Sweep animation effect */}
        <div style={styles.sweepAnimation} />

        {/* Logo */}
        <div
          style={{
            ...styles.logo,
            ...(isHoveringLogo ? styles.logoHover : {}),
          }}
          onMouseEnter={() => setIsHoveringLogo(true)}
          onMouseLeave={() => setIsHoveringLogo(false)}
          onClick={() => window.location.href = '/'}
          role="button"
          tabIndex={0}
          aria-label="TeleBoost Home"
        >
          TeleBoost
        </div>

        {/* Menu Button */}
        <button
          style={{
            ...styles.menuButton,
            ...(isHoveringMenu ? styles.menuButtonHover : {}),
            ...(isMenuActive ? styles.menuButtonActive : {}),
          }}
          onMouseEnter={() => setIsHoveringMenu(true)}
          onMouseLeave={() => setIsHoveringMenu(false)}
          onMouseDown={() => setIsMenuActive(true)}
          onMouseUp={() => setIsMenuActive(false)}
          onMouseLeave={() => setIsMenuActive(false)}
          onClick={handleMenuClick}
          aria-label="Menu"
          aria-expanded={isMenuOpen}
        >
          {/* Notification Badge */}
          {showNotification && (
            <div style={styles.notificationBadge} aria-label="New notifications" />
          )}

          {/* Menu Lines */}
          <div
            style={{
              ...styles.menuLine,
              ...styles.menuLineTop,
              ...(isMenuOpen ? styles.menuOpen.menuLineTop : {}),
            }}
          />
          <div
            style={{
              ...styles.menuLine,
              ...(isMenuOpen ? styles.menuOpen.menuLineMiddle : {}),
            }}
          />
          <div
            style={{
              ...styles.menuLine,
              ...styles.menuLineBottom,
              ...(isMenuOpen ? styles.menuOpen.menuLineBottom : {}),
            }}
          />
        </button>
      </header>
    </>
  );
});

Header.displayName = 'Header';

// Extended Header with user info (optional variant)
export const HeaderWithUserInfo = memo(({
  onMenuClick,
  showNotification = false,
  userName = 'Guest',
  balance = 0,
  currency = 'USDT'
}) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const extendedStyles = {
    ...styles,
    header: {
      ...styles.header,
      padding: '16px 20px',
    },
    userInfo: {
      display: 'flex',
      alignItems: 'center',
      gap: '16px',
      position: 'relative',
      zIndex: 1,
    },
    balanceContainer: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '8px 16px',
      background: 'rgba(255, 255, 255, 0.05)',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      borderRadius: '12px',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
    },
    balanceIcon: {
      fontSize: '16px',
    },
    balanceText: {
      fontSize: '14px',
      fontWeight: 600,
      color: '#fff',
    },
    balanceAmount: {
      fontSize: '16px',
      fontWeight: 700,
      background: 'linear-gradient(135deg, #fbbf24, #f59e0b)',
      WebkitBackgroundClip: 'text',
      WebkitTextFillColor: 'transparent',
      backgroundClip: 'text',
    },
  };

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: keyframes }} />

      <header style={extendedStyles.header}>
        <div style={styles.sweepAnimation} />

        <div style={styles.logo}>TeleBoost</div>

        <div style={extendedStyles.userInfo}>
          <div style={extendedStyles.balanceContainer}>
            <span style={extendedStyles.balanceIcon}>💰</span>
            <span style={extendedStyles.balanceText}>Balance:</span>
            <span style={extendedStyles.balanceAmount}>
              {balance.toFixed(2)} {currency}
            </span>
          </div>

          <button
            style={{
              ...styles.menuButton,
              ...(isMenuOpen ? { background: 'rgba(168, 85, 247, 0.2)' } : {}),
            }}
            onClick={() => {
              setIsMenuOpen(!isMenuOpen);
              onMenuClick?.(!isMenuOpen);
            }}
          >
            {showNotification && <div style={styles.notificationBadge} />}
            <div style={{ ...styles.menuLine, ...styles.menuLineTop }} />
            <div style={styles.menuLine} />
            <div style={{ ...styles.menuLine, ...styles.menuLineBottom }} />
          </button>
        </div>
      </header>
    </>
  );
});

HeaderWithUserInfo.displayName = 'HeaderWithUserInfo';

// Export default
export default Header;