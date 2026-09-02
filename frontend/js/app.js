/**
 * Application entry point.
 * Initializes navigation, auth, sidebar, router, and page handlers.
 */

(function () {
    let _initialized = false;
    var _currentPage = null;

    async function init() {
        if (_initialized) return;
        _initialized = true;

        _setupNavigationHandlers();
        _registerRoutes();
        router.init();
    }

    function _disposeCurrentPage() {
        if (_currentPage && _currentPage.dispose) {
            _currentPage.dispose();
        }
        _currentPage = null;
    }

    function _setupNavigationHandlers() {
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;

        sidebar.addEventListener('click', (e) => {
            const link = e.target.closest('.sidebar-link[data-route]');
            if (!link) return;
            e.preventDefault();
            const route = link.getAttribute('data-route');
            if (route) {
                if (!auth.isAuthenticated() && route !== 'login') {
                    router.navigate('login');
                    return;
                }
                router.navigate(route);
            }
        });
    }

    async function _renderRoute(name, pageModule) {
        if (pageModule && pageModule !== _currentPage) {
            _disposeCurrentPage();
        }
        _currentPage = pageModule || null;
        if (pageModule) {
            pageModule.render();
        }
    }

    function _registerRoutes() {
        router.on('login', function () {
            _disposeCurrentPage();
            auth.renderLoginPage();
        });

        router.on('configs', async function () {
            var ok = await _requireAuth();
            if (ok) _renderRoute('configs', configsPage);
        });

        router.on('users', async function () {
            var ok = await _requireAuth();
            if (ok) _renderRoute('users', usersPage);
        });

        router.on('logs', async function () {
            var ok = await _requireAuth();
            if (ok) _renderRoute('logs', logsPage);
        });

        router.on('bulk', async function () {
            var ok = await _requireAuth();
            if (ok) _renderRoute('bulk', bulkPage);
        });

        router.on('audit', async function () {
            var ok = await _requireAuth();
            if (ok) _renderRoute('audit', auditPage);
        });

        router.on('profile', async function () {
            var ok = await _requireAuth();
            if (ok) _renderRoute('profile', adminPage);
        });
    }

    function _showSidebar(visible) {
        var layout = document.querySelector('.app-layout');
        if (layout) {
            if (visible) {
                layout.classList.remove('sidebar-hidden');
            } else {
                layout.classList.add('sidebar-hidden');
            }
        }
    }

    async function _requireAuth() {
        if (auth.isAuthenticated()) {
            _showSidebar(true);
            return true;
        }

        const ok = await auth.checkAuth();
        if (!ok) {
            _showSidebar(false);
            router.navigate('login');
            return false;
        }
        _showSidebar(true);
        return true;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
