import { ReactNode, useEffect } from 'react';
import './Modal.css';

interface ModalProps {
  isOpen: boolean;
  title?: string;
  width?: string;
  onClose?: () => void;
  children: ReactNode;
}

const Modal = ({ isOpen, title, width = '520px', onClose, children }: ModalProps) => {
  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose?.();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="modal__backdrop" role="dialog" aria-modal="true">
      <div className="modal__container" style={{ width }}>
        {onClose && (
          <button className="modal__close" aria-label="关闭" onClick={onClose}>
            ×
          </button>
        )}
        {title && <h3 className="modal__title">{title}</h3>}
        <div className="modal__content">{children}</div>
      </div>
    </div>
  );
};

export default Modal;