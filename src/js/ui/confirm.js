// Promise-based confirm dialog on #confirm-modal. Resolves true on confirm,
// false on cancel, Esc, backdrop click or the close button.
import { byId } from '../dom.js';
import { openModal, closeModal, isModalOpen, onModalClose } from './modal.js';

let pending = null;
let bound = false;

function settle(value) {
  if (!pending) return;
  const current = pending;
  pending = null;
  if (isModalOpen('confirm-modal')) closeModal('confirm-modal');
  current.resolve(value);
}

function bind() {
  if (bound) return;
  bound = true;
  byId('confirm-modal-confirm').addEventListener('click', () => settle(true));
  byId('confirm-modal-cancel').addEventListener('click', () => settle(false));
  onModalClose('confirm-modal', () => settle(false));
}

export function confirmDialog({ title = 'Are you sure?', body = '', confirmLabel = 'Confirm', cancelLabel = 'Cancel', danger = true } = {}) {
  bind();
  if (pending) settle(false);
  byId('confirm-modal-title').textContent = title;
  byId('confirm-modal-body').textContent = body;
  const confirmButton = byId('confirm-modal-confirm');
  confirmButton.textContent = confirmLabel;
  confirmButton.className = danger ? 'btn-danger' : 'btn-primary';
  const cancelButton = byId('confirm-modal-cancel');
  cancelButton.textContent = cancelLabel;
  return new Promise((resolve) => {
    pending = { resolve };
    openModal('confirm-modal', { focus: cancelButton });
  });
}
