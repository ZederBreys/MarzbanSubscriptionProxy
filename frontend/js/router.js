/**
 * Hash-based SPA router.
 *
 * Usage:
 *   router.on('configs', () => renderConfigsPage());
 *   router.navigate('configs');
 */

const router = (() => {
    const routes = new Map();
    let currentRoute = null;

    function on(name, handler) {
        routes.set(name, handler);
    }

    function navigate(name) {
        if (window.location.hash !== `#${name}`) {
            window.location.hash = name;
        } else {
            _handleRoute(name);
        }
    }

    function _handleRoute(name) {
        const handler = routes.get(name);
        if (!handler) {
            _showPlaceholder(name);
            return;
        }
        currentRoute = name;
        _updateSidebar(name);
        handler();
    }

    function _showPlaceholder(name) {
        currentRoute = name;
        _updateSidebar(name);
        const content = document.getElementById('content');
        if (content) {
            content.textContent = '';
            const div = document.createElement('div');
            div.className = 'content-placeholder';
            div.textContent = 'Page: ' + name;
            content.appendChild(div);
        }
    }

    function _updateSidebar(name) {
        document.querySelectorAll('.sidebar-link').forEach((link) => {
            const linkRoute = link.getAttribute('data-route');
            if (linkRoute === name) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }

    function init() {
        const hash = window.location.hash.replace('#', '') || 'configs';
        _handleRoute(hash);

        window.addEventListener('hashchange', () => {
            const newHash = window.location.hash.replace('#', '') || 'configs';
            _handleRoute(newHash);
        });
    }

    function getCurrentRoute() {
        return currentRoute;
    }

    return { on, navigate, init, getCurrentRoute };
})();
