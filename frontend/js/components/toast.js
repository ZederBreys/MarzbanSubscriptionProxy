/**
 * Toast notification system.
 *
 * Usage:
 *   toast.success('Config saved.');
 *   toast.error('Failed to delete.');
 *   toast.info('Processing...');
 */

const toast = (() => {
    const DURATION = 4000;

    function _create(type, message) {
        const container = document.getElementById('toast-container') || _createContainer();

        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.textContent = message;

        el.addEventListener('click', () => _remove(el));

        container.appendChild(el);

        requestAnimationFrame(() => {
            el.classList.add('toast-visible');
        });

        setTimeout(() => _remove(el), DURATION);
    }

    function _createContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }

    function _remove(el) {
        el.classList.remove('toast-visible');
        el.addEventListener('transitionend', () => {
            if (el.parentNode) {
                el.parentNode.removeChild(el);
            }
        });
    }

    function success(message) {
        _create('success', message);
    }

    function error(message) {
        _create('error', message);
    }

    function info(message) {
        _create('info', message);
    }

    return { success, error, info };
})();
