/**
 * Reusable modal dialog.
 *
 * Usage:
 *   modal.show('Create Config', bodyElement, [
 *       { text: 'Cancel', className: 'btn-secondary', handler: () => modal.close() },
 *       { text: 'Save', className: 'btn-primary', handler: () => onSave() },
 *   ]);
 *   modal.close();
 *   modal.setBody(element);
 */

const modal = (() => {
    let _overlay = null;
    let _onClose = null;

    function show(title, bodyElement, buttons, onClose) {
        _close();
        _onClose = onClose || null;

        _overlay = document.createElement('div');
        _overlay.className = 'modal-overlay';
        _overlay.addEventListener('click', (e) => {
            if (e.target === _overlay) {
                close();
            }
        });

        const container = document.createElement('div');
        container.className = 'modal-container';

        const header = document.createElement('div');
        header.className = 'modal-header';

        const titleEl = document.createElement('h3');
        titleEl.textContent = title;

        const closeBtn = document.createElement('button');
        closeBtn.className = 'modal-close';
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', close);

        header.appendChild(titleEl);
        header.appendChild(closeBtn);

        const body = document.createElement('div');
        body.className = 'modal-body';
        body.id = 'modal-body';
        if (bodyElement) {
            body.appendChild(bodyElement);
        }

        const footer = document.createElement('div');
        footer.className = 'modal-footer';

        if (buttons && buttons.length > 0) {
            buttons.forEach((btn) => {
                const btnEl = document.createElement('button');
                btnEl.className = btn.className || 'btn btn-secondary';
                btnEl.textContent = btn.text;
                btnEl.addEventListener('click', btn.handler);
                footer.appendChild(btnEl);
            });
        }

        container.appendChild(header);
        container.appendChild(body);
        container.appendChild(footer);
        _overlay.appendChild(container);

        document.body.appendChild(_overlay);

        requestAnimationFrame(() => {
            _overlay.classList.add('modal-overlay-visible');
            container.classList.add('modal-container-visible');
        });

        document.addEventListener('keydown', _onKeyDown);
    }

    function _onKeyDown(e) {
        if (e.key === 'Escape') {
            close();
        }
    }

    function close() {
        if (!_overlay) return;

        const container = _overlay.querySelector('.modal-container');
        _overlay.classList.remove('modal-overlay-visible');
        if (container) {
            container.classList.remove('modal-container-visible');
        }

        document.removeEventListener('keydown', _onKeyDown);

        var _timer = setTimeout(function () {
            _fireOnClose();
            _close();
        }, 300);

        _overlay.addEventListener('transitionend', function () {
            clearTimeout(_timer);
            _fireOnClose();
            _close();
        });
    }

    function _fireOnClose() {
        if (_onClose) {
            _onClose();
            _onClose = null;
        }
    }

    function _close() {
        if (_overlay && _overlay.parentNode) {
            _overlay.parentNode.removeChild(_overlay);
        }
        _overlay = null;
    }

    function setBody(element) {
        const body = document.getElementById('modal-body');
        if (body) {
            body.innerHTML = '';
            body.appendChild(element);
        }
    }

    return { show, close, setBody };
})();
