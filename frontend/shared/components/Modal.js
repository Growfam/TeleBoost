import React, { useState, useEffect, useRef, memo, useCallback } from 'react';
import ReactDOM from 'react-dom';

// Styles object
const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.8)',
    backdropFilter: 'blur(10px)',
    WebkitBackdropFilter: 'blur(10px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '20px',
    opacity: 0,
    visibility: 'hidden',
    transition: 'all 0.3s ease',
  },

  overlayActive: {
    opacity: 1,
    visibility: 'visible',
  },

  modal: {
    background: 'rgba(255, 255, 255, 0.05)',
    backdropFilter: 'blur(40px)',
    WebkitBackdropFilter: 'blur(40px)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '24px',
    padding: '32px',
    maxWidth: '430px',
    width: '100%',
    maxHeight: '90vh',
    overflow: 'auto',
    transform: 'scale(0.9) translateY(20px)',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    position: 'relative',
    boxShadow: '0 25px 50px rgba(0, 0, 0, 0.5)',
  },

  modalActive: {
    transform: 'scale(1) translateY(0)',
  },

  glowEffect: {
    position: 'absolute',
    top: '-50%',
    left: '-50%',
    width: '200%',
    height: '200%',
    background: 'radial-gradient(circle, rgba(168, 85, 247, 0.1) 0%, transparent 70%)',
    animation: 'rotate 20s linear infinite',
    pointerEvents: 'none',
  },

  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
    position: 'relative',
    zIndex: 1,
  },

  title: {
    fontSize: '24px',
    fontWeight: 700,
    background: 'linear-gradient(135deg, #fff, #a78bfa)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text',
    margin: 0,
    lineHeight: 1.2,
  },

  closeButton: {
    width: '36px',
    height: '36px',
    background: 'rgba(255, 255, 255, 0.1)',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    borderRadius: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    fontSize: '20px',
    color: '#fff',
    outline: 'none',
    flexShrink: 0,
  },

  closeButtonHover: {
    background: 'rgba(239, 68, 68, 0.2)',
    borderColor: 'rgba(239, 68, 68, 0.3)',
    transform: 'rotate(90deg)',
  },

  body: {
    marginBottom: '24px',
    position: 'relative',
    zIndex: 1,
    color: 'rgba(255, 255, 255, 0.9)',
    lineHeight: 1.6,
  },

  footer: {
    display: 'flex',
    gap: '12px',
    position: 'relative',
    zIndex: 1,
  },

  button: {
    flex: 1,
    padding: '12px 24px',
    border: 'none',
    borderRadius: '12px',
    fontWeight: 600,
    fontSize: '16px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    outline: 'none',
    fontFamily: 'inherit',
  },

  primaryButton: {
    background: 'linear-gradient(135deg, #a855f7, #6366f1)',
    color: '#fff',
  },

  primaryButtonHover: {
    transform: 'translateY(-2px)',
    boxShadow: '0 10px 30px rgba(168, 85, 247, 0.4)',
  },

  secondaryButton: {
    background: 'rgba(255, 255, 255, 0.1)',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    color: '#fff',
  },

  secondaryButtonHover: {
    background: 'rgba(255, 255, 255, 0.15)',
    transform: 'translateY(-1px)',
  },

  // Size variants
  sizeSmall: {
    maxWidth: '320px',
    padding: '24px',
  },

  sizeLarge: {
    maxWidth: '600px',
    padding: '40px',
  },

  // Additional content styles
  text: {
    color: 'rgba(255, 255, 255, 0.8)',
    fontSize: '16px',
    marginBottom: '16px',
  },

  highlight: {
    fontSize: '32px',
    fontWeight: 700,
    textAlign: 'center',
    margin: '20px 0',
    background: 'linear-gradient(135deg, #fbbf24, #f59e0b)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text',
  },

  subtitle: {
    textAlign: 'center',
    opacity: 0.7,
    fontSize: '14px',
    marginTop: '-10px',
    marginBottom: '20px',
  },
};

// Keyframes
const keyframes = `
  @keyframes rotate {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes slideUp {
    from { transform: translateY(20px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
`;

// Modal Component
const Modal = memo(({
  isOpen = false,
  onClose,
  title,
  children,
  footer,
  size = 'medium', // small, medium, large
  showCloseButton = true,
  closeOnOverlay = true,
  closeOnEsc = true,
  className = '',
  preventScroll = true,
  onOpen,
  onAfterOpen,
  onAfterClose,
}) => {
  const [isActive, setIsActive] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [isHoveringClose, setIsHoveringClose] = useState(false);
  const modalRef = useRef(null);
  const previousActiveElement = useRef(null);

  // Handle open/close animations
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement;
      onOpen?.();

      // Small delay for animation
      requestAnimationFrame(() => {
        setIsActive(true);
        onAfterOpen?.();
      });

      // Prevent body scroll
      if (preventScroll) {
        document.body.style.overflow = 'hidden';
      }
    } else if (isActive) {
      setIsClosing(true);
      setIsActive(false);

      // Cleanup after animation
      setTimeout(() => {
        setIsClosing(false);
        onAfterClose?.();

        // Restore body scroll
        if (preventScroll) {
          document.body.style.overflow = '';
        }

        // Restore focus
        if (previousActiveElement.current) {
          previousActiveElement.current.focus();
        }
      }, 300);
    }
  }, [isOpen, isActive, preventScroll, onOpen, onAfterOpen, onAfterClose]);

  // Handle ESC key
  useEffect(() => {
    if (!closeOnEsc || !isOpen) return;

    const handleEsc = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };

    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [isOpen, closeOnEsc, onClose]);

  // Handle overlay click
  const handleOverlayClick = useCallback((e) => {
    if (closeOnOverlay && e.target === e.currentTarget) {
      onClose?.();
    }
  }, [closeOnOverlay, onClose]);

  // Get size styles
  const getSizeStyles = () => {
    switch (size) {
      case 'small':
        return styles.sizeSmall;
      case 'large':
        return styles.sizeLarge;
      default:
        return {};
    }
  };

  // Don't render if not open and not closing
  if (!isOpen && !isClosing) return null;

  // Portal render
  return ReactDOM.createPortal(
    <>
      <style dangerouslySetInnerHTML={{ __html: keyframes }} />

      <div
        style={{
          ...styles.overlay,
          ...(isActive ? styles.overlayActive : {}),
        }}
        onClick={handleOverlayClick}
        className={className}
      >
        <div
          ref={modalRef}
          style={{
            ...styles.modal,
            ...getSizeStyles(),
            ...(isActive ? styles.modalActive : {}),
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? 'modal-title' : undefined}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Glow effect */}
          <div style={styles.glowEffect} />

          {/* Header */}
          {(title || showCloseButton) && (
            <div style={styles.header}>
              {title && (
                <h2 id="modal-title" style={styles.title}>
                  {title}
                </h2>
              )}

              {showCloseButton && (
                <button
                  style={{
                    ...styles.closeButton,
                    ...(isHoveringClose ? styles.closeButtonHover : {}),
                  }}
                  onClick={onClose}
                  onMouseEnter={() => setIsHoveringClose(true)}
                  onMouseLeave={() => setIsHoveringClose(false)}
                  aria-label="Close modal"
                  type="button"
                >
                  ✕
                </button>
              )}
            </div>
          )}

          {/* Body */}
          <div style={styles.body}>
            {children}
          </div>

          {/* Footer */}
          {footer && (
            <div style={styles.footer}>
              {footer}
            </div>
          )}
        </div>
      </div>
    </>,
    document.body
  );
});

Modal.displayName = 'Modal';

// Button components for footer
export const ModalButton = memo(({
  children,
  variant = 'primary',
  onClick,
  disabled = false,
  ...props
}) => {
  const [isHovering, setIsHovering] = useState(false);

  const buttonStyle = variant === 'primary'
    ? {
        ...styles.button,
        ...styles.primaryButton,
        ...(isHovering && !disabled ? styles.primaryButtonHover : {}),
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }
    : {
        ...styles.button,
        ...styles.secondaryButton,
        ...(isHovering && !disabled ? styles.secondaryButtonHover : {}),
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      };

  return (
    <button
      style={buttonStyle}
      onClick={disabled ? undefined : onClick}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
      disabled={disabled}
      type="button"
      {...props}
    >
      {children}
    </button>
  );
});

ModalButton.displayName = 'ModalButton';

// Helper components for common content patterns
export const ModalText = ({ children, ...props }) => (
  <p style={styles.text} {...props}>{children}</p>
);

export const ModalHighlight = ({ children, ...props }) => (
  <div style={styles.highlight} {...props}>{children}</div>
);

export const ModalSubtitle = ({ children, ...props }) => (
  <div style={styles.subtitle} {...props}>{children}</div>
);

// Usage example component
export const ConfirmModal = memo(({ isOpen, onClose, onConfirm, amount = 100, currency = 'USDT' }) => {
  const handleConfirm = () => {
    onConfirm?.();
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Підтвердження оплати"
      footer={
        <>
          <ModalButton variant="secondary" onClick={onClose}>
            Скасувати
          </ModalButton>
          <ModalButton variant="primary" onClick={handleConfirm}>
            Підтвердити
          </ModalButton>
        </>
      }
    >
      <ModalText>Ви збираєтесь поповнити баланс на суму:</ModalText>
      <ModalHighlight>{amount.toFixed(2)} {currency}</ModalHighlight>
      <ModalSubtitle>Комісія: 0%</ModalSubtitle>
    </Modal>
  );
});

ConfirmModal.displayName = 'ConfirmModal';

// Export default
export default Modal;