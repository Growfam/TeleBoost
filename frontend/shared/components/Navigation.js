import React, { useState, useEffect, useRef, memo } from 'react';

// SVG Icons as components
const HomeIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" width="24" height="24">
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    <polyline points="9 22 9 12 15 12 15 22" />
  </svg>
);

const ServicesIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" width="24" height="24">
    <rect x="3" y="3" width="7" height="7" />
    <rect x="14" y="3" width="7" height="7" />
    <rect x="14" y="14" width="7" height="7" />
    <rect x="3" y="14" width="7" height="7" />
  </svg>
);

const OrdersIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" width="24" height="24">
    <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
    <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
    <line x1="8" y1="12" x2="16" y2="12" />
    <line x1="8" y1="16" x2="13" y2="16" />
  </svg>
);

const BalanceIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" width="24" height="24">
    <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
    <line x1="1" y1="10" x2="23" y2="10" />
  </svg>
);

const ProfileIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" width="24" height="24">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

// Styles
const styles = {
  navigation: {
    position: 'fixed',
    bottom: '20px',
    left: '50%',
    transform: 'translateX(-50%)',
    background: 'rgba(20, 20, 20, 0.9)',
    backdropFilter: 'blur(30px)',
    WebkitBackdropFilter: 'blur(30px)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '20px',
    padding: '4px',
    display: 'flex',
    zIndex: 1000,
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
    maxWidth: '400px',
    width: 'calc(100% - 40px)',
  },

  indicator: {
    position: 'absolute',
    height: 'calc(100% - 8px)',
    background: 'linear-gradient(135deg, #a855f7, #6366f1)',
    borderRadius: '16px',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    top: '4px',
    boxShadow: '0 4px 20px rgba(168, 85, 247, 0.4)',
    pointerEvents: 'none',
  },

  navItem: {
    position: 'relative',
    width: '80px',
    height: '56px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '4px',
    cursor: 'pointer',
    zIndex: 1,
    transition: 'all 0.3s ease',
    color: 'rgba(255, 255, 255, 0.5)',
    backgroundColor: 'transparent',
    border: 'none',
    outline: 'none',
    WebkitTapHighlightColor: 'transparent',
  },

  navItemActive: {
    color: '#fff',
  },

  navIcon: {
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: '2',
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  },

  navIconActive: {
    filter: 'drop-shadow(0 0 8px rgba(168, 85, 247, 0.6))',
    transform: 'scale(1.1)',
  },

  navLabel: {
    fontSize: '11px',
    fontWeight: '600',
    letterSpacing: '0.3px',
    transition: 'all 0.3s ease',
    userSelect: 'none',
  },

  badge: {
    position: 'absolute',
    top: '8px',
    right: '8px',
    background: '#ef4444',
    color: '#fff',
    fontSize: '10px',
    fontWeight: '700',
    padding: '2px 6px',
    borderRadius: '10px',
    minWidth: '18px',
    textAlign: 'center',
    boxShadow: '0 2px 8px rgba(239, 68, 68, 0.3)',
    animation: 'badgePulse 2s ease-in-out infinite',
  },

  dot: {
    position: 'absolute',
    top: '10px',
    right: '10px',
    width: '8px',
    height: '8px',
    background: '#ef4444',
    borderRadius: '50%',
    boxShadow: '0 0 0 2px rgba(20, 20, 20, 0.9)',
    animation: 'pulse 2s ease-in-out infinite',
  },
};

// Keyframes
const keyframes = `
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

  @keyframes badgePulse {
    0%, 100% {
      transform: scale(1);
    }
    50% {
      transform: scale(1.05);
    }
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateX(-50%) translateY(100%);
    }
    to {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
  }
`;

// Navigation items configuration
const navigationItems = [
  { id: 'home', label: 'Головна', icon: HomeIcon, path: '/' },
  { id: 'services', label: 'Послуги', icon: ServicesIcon, path: '/services' },
  { id: 'orders', label: 'Замовлення', icon: OrdersIcon, path: '/orders', badge: 3 },
  { id: 'balance', label: 'Баланс', icon: BalanceIcon, path: '/balance' },
  { id: 'profile', label: 'Профіль', icon: ProfileIcon, path: '/profile', dot: true },
];

// Navigation Component
const Navigation = memo(({
  activeItem = 'home',
  onNavigate,
  notifications = { orders: 3, profile: true }
}) => {
  const [active, setActive] = useState(activeItem);
  const [indicatorStyle, setIndicatorStyle] = useState({});
  const navRef = useRef(null);
  const itemRefs = useRef({});
  const [mounted, setMounted] = useState(false);

  // Calculate indicator position
  const updateIndicator = (itemId) => {
    const itemElement = itemRefs.current[itemId];
    if (itemElement && navRef.current) {
      const navRect = navRef.current.getBoundingClientRect();
      const itemRect = itemElement.getBoundingClientRect();

      setIndicatorStyle({
        left: `${itemRect.left - navRect.left}px`,
        width: `${itemRect.width}px`,
      });
    }
  };

  // Initialize indicator position
  useEffect(() => {
    setMounted(true);
    updateIndicator(active);

    // Update on window resize
    const handleResize = () => updateIndicator(active);
    window.addEventListener('resize', handleResize);

    return () => window.removeEventListener('resize', handleResize);
  }, [active]);

  // Handle navigation
  const handleNavigate = (item) => {
    setActive(item.id);
    updateIndicator(item.id);
    onNavigate?.(item);
  };

  return (
    <>
      {/* Inject keyframes */}
      <style dangerouslySetInnerHTML={{ __html: keyframes }} />

      {/* Navigation */}
      <nav
        ref={navRef}
        style={{
          ...styles.navigation,
          animation: mounted ? 'slideUp 0.6s ease-out' : 'none',
        }}
        role="navigation"
        aria-label="Main navigation"
      >
        {/* Background indicator */}
        <div
          style={{
            ...styles.indicator,
            ...indicatorStyle,
          }}
          aria-hidden="true"
        />

        {/* Navigation items */}
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.id;
          const showBadge = item.badge && notifications.orders > 0;
          const showDot = item.dot && notifications.profile;

          return (
            <button
              key={item.id}
              ref={(el) => itemRefs.current[item.id] = el}
              style={{
                ...styles.navItem,
                ...(isActive ? styles.navItemActive : {}),
              }}
              onClick={() => handleNavigate(item)}
              aria-label={item.label}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon
                className="nav-icon"
                style={{
                  ...styles.navIcon,
                  ...(isActive ? styles.navIconActive : {}),
                }}
              />
              <span style={styles.navLabel}>{item.label}</span>

              {/* Badge */}
              {showBadge && (
                <span style={styles.badge} aria-label={`${item.badge} new items`}>
                  {item.badge}
                </span>
              )}

              {/* Notification dot */}
              {showDot && (
                <span style={styles.dot} aria-label="New notification" />
              )}
            </button>
          );
        })}
      </nav>
    </>
  );
});

Navigation.displayName = 'Navigation';

// Compact variant without labels
export const NavigationCompact = memo(({ activeItem = 'home', onNavigate }) => {
  const compactStyles = {
    ...styles,
    navigation: {
      ...styles.navigation,
      padding: '6px',
      borderRadius: '18px',
    },
    navItem: {
      ...styles.navItem,
      width: '60px',
      height: '48px',
      gap: '0',
    },
    indicator: {
      ...styles.indicator,
      top: '6px',
      borderRadius: '12px',
    },
  };

  return <Navigation {...arguments[0]} styles={compactStyles} showLabels={false} />;
});

NavigationCompact.displayName = 'NavigationCompact';

// Export default
export default Navigation;