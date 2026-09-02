/**
 * Authentication state management.
 *
 * Usage:
 *   await auth.checkAuth();  // returns true if authenticated
 *   await auth.login(login, password);
 *   await auth.logout();
 *   auth.renderLoginPage();
 */

const auth = (() => {
    let _authenticated = false;
    let _user = null;

    async function checkAuth() {
        try {
            const data = await api.get('/admin/auth/profile');
            _authenticated = true;
            _user = data;
            _updateSidebarUser(data.login);
            return true;
        } catch (e) {
            _authenticated = false;
            _user = null;
            return false;
        }
    }

    function isAuthenticated() {
        return _authenticated;
    }

    function getUser() {
        return _user;
    }

    async function login(login, password) {
        const data = await api.post('/admin/auth/login', { login, password });
        _authenticated = true;
        _user = data.admin;
        _updateSidebarUser(data.admin.login);
        return data;
    }

    async function logout() {
        try {
            await api.post('/admin/auth/logout');
        } catch (e) {
            // ignore errors during logout
        }
        _authenticated = false;
        _user = null;
        _updateSidebarUser(null);
    }

    async function logoutAll() {
        await api.post('/admin/auth/logout-all');
        _authenticated = false;
        _user = null;
        _updateSidebarUser(null);
    }

    async function changePassword(oldPassword, newPassword) {
        return await api.post('/admin/auth/change-password', {
            old_password: oldPassword,
            new_password: newPassword,
        });
    }

    function _updateSidebarUser(login) {
        const el = document.getElementById('sidebar-username');
        if (el) {
            el.textContent = login || '';
        }
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

    function renderLoginPage() {
        _showSidebar(false);

        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="login-wrapper">
                <div class="login-card">
                    <div class="login-header">
                        <h1>Config panel</h1>
                        <p>Введите данные для входа</p>
                    </div>
                    <form class="login-form" id="login-form">
                        <div class="form-group">
                            <label class="form-label" for="login-input">Логин</label>
                            <input class="form-input" type="text" id="login-input"
                                   autocomplete="username" autofocus>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="password-input">Пароль</label>
                            <input class="form-input" type="password" id="password-input"
                                   autocomplete="current-password">
                        </div>
                        <div class="form-error" id="login-error" style="display: none;"></div>
                        <div class="form-actions">
                            <button type="submit" class="btn btn-primary" id="login-btn">
                                Войти
                            </button>
                        </div>
                    </form>
                </div>
            </div>`;

        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const loginVal = document.getElementById('login-input').value.trim();
            const passVal = document.getElementById('password-input').value;
            const errorEl = document.getElementById('login-error');
            const btnEl = document.getElementById('login-btn');

            if (!loginVal || !passVal) {
                errorEl.textContent = 'Логин и пароль обязательны.';
                errorEl.style.display = 'block';
                return;
            }

            btnEl.disabled = true;
            btnEl.textContent = 'Вход...';
            errorEl.style.display = 'none';

            try {
                await login(loginVal, passVal);
                _showSidebar(true);
                router.navigate('configs');
            } catch (err) {
                if (err.status === 401) {
                    errorEl.textContent = 'Неверный логин или пароль.';
                } else {
                    errorEl.textContent = err.message || 'Ошибка аутентификации.';
                }
                errorEl.style.display = 'block';
            } finally {
                btnEl.disabled = false;
                btnEl.textContent = 'Войти';
            }
        });
    }

    return {
        checkAuth,
        isAuthenticated,
        getUser,
        login,
        logout,
        logoutAll,
        changePassword,
        renderLoginPage,
    };
})();
