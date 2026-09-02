const confirmDialog = (() => {
    var _currentEscHandler = null;

    function show(message, detail) {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'confirm-overlay';

            const dialog = document.createElement('div');
            dialog.className = 'confirm-dialog';

            const body = document.createElement('div');
            body.className = 'confirm-body';

            const messageEl = document.createElement('p');
            messageEl.className = 'confirm-message';
            messageEl.textContent = message;

            body.appendChild(messageEl);

            if (detail) {
                const detailEl = document.createElement('p');
                detailEl.className = 'confirm-detail';
                detailEl.textContent = detail;
                body.appendChild(detailEl);
            }

            const actions = document.createElement('div');
            actions.className = 'confirm-actions';

            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'btn btn-secondary';
            cancelBtn.textContent = 'Отмена';
            cancelBtn.addEventListener('click', function () {
                _dismiss(overlay, resolve, false);
            });

            const confirmBtn = document.createElement('button');
            confirmBtn.className = 'btn btn-danger';
            confirmBtn.textContent = 'Подтвердить';
            confirmBtn.addEventListener('click', function () {
                _dismiss(overlay, resolve, true);
            });

            actions.appendChild(cancelBtn);
            actions.appendChild(confirmBtn);

            dialog.appendChild(body);
            dialog.appendChild(actions);
            overlay.appendChild(dialog);

            overlay.addEventListener('click', function (e) {
                if (e.target === overlay) {
                    _dismiss(overlay, resolve, false);
                }
            });

            if (_currentEscHandler) {
                document.removeEventListener('keydown', _currentEscHandler);
                _currentEscHandler = null;
            }

            _currentEscHandler = function (e) {
                if (e.key === 'Escape') {
                    _dismiss(overlay, resolve, false);
                }
            };
            document.addEventListener('keydown', _currentEscHandler);

            document.body.appendChild(overlay);

            requestAnimationFrame(function () {
                overlay.classList.add('confirm-overlay-visible');
                dialog.classList.add('confirm-dialog-visible');
            });

            confirmBtn.focus();
        });
    }

    function _dismiss(overlay, resolve, result) {
        if (_currentEscHandler) {
            document.removeEventListener('keydown', _currentEscHandler);
            _currentEscHandler = null;
        }

        const dialog = overlay.querySelector('.confirm-dialog');
        overlay.classList.remove('confirm-overlay-visible');
        if (dialog) {
            dialog.classList.remove('confirm-dialog-visible');
        }
        overlay.addEventListener('transitionend', function () {
            if (overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
            if (resolve) {
                resolve(result);
            }
        });
    }

    return { show };
})();
