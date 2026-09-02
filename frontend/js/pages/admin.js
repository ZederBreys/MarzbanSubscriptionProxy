const adminPage = (() => {
    async function render() {
        const user = auth.getUser();
        const content = document.getElementById('content');

        const createdInfo = user?.created_at
            ? new Date(user.created_at * 1000).toLocaleString()
            : '-';

        const lastLoginInfo = user?.last_login_at
            ? `${new Date(user.last_login_at * 1000).toLocaleString()}`
            : 'не зафиксировано';

        const lastLoginIp = user?.last_login_ip || '-';

        content.innerHTML = `
            <div class="page-header">
                <h2>Профиль</h2>
            </div>

            <div class="profile-grid">

                <div class="profile-card">
                    <div class="profile-card-header">
                        <span class="profile-card-icon">👤</span>
                        <h3>Аккаунт</h3>
                    </div>
                    <div class="profile-card-body">
                        <div class="profile-row">
                            <span class="profile-label">Логин</span>
                            <span class="profile-value">${_escapeHtml(user?.login || '')}</span>
                        </div>
                        <div class="profile-row">
                            <span class="profile-label">Последний вход</span>
                            <span class="profile-value">${_escapeHtml(lastLoginInfo)}</span>
                        </div>
                        <div class="profile-row">
                            <span class="profile-label">IP последнего входа</span>
                            <span class="profile-value">${_escapeHtml(lastLoginIp)}</span>
                        </div>
                        <div class="profile-row">
                            <span class="profile-label">Дата создания</span>
                            <span class="profile-value">${_escapeHtml(createdInfo)}</span>
                        </div>
                    </div>
                </div>

                <div class="profile-card">
                    <div class="profile-card-header">
                        <span class="profile-card-icon">🔐</span>
                        <h3>Сменить пароль</h3>
                    </div>
                    <div class="profile-card-body">
                        <form id="password-form">
                            <div class="form-group">
                                <label class="form-label" for="old-password">Текущий пароль</label>
                                <input class="form-input" type="password" id="old-password"
                                       autocomplete="current-password">
                            </div>
                            <div class="form-group">
                                <label class="form-label" for="new-password">Новый пароль</label>
                                <input class="form-input" type="password" id="new-password"
                                       autocomplete="new-password">
                            </div>
                            <div class="form-group">
                                <label class="form-label" for="confirm-password">Подтвердите пароль</label>
                                <input class="form-input" type="password" id="confirm-password"
                                       autocomplete="new-password">
                            </div>
                            <div class="form-error" id="password-error" style="display: none;"></div>
                            <div class="form-actions" style="border-top: none; padding-top: 0; margin-top: var(--spacing-md);">
                                <button type="submit" class="btn btn-primary">Обновить пароль</button>
                            </div>
                        </form>
                    </div>
                </div>

                <div class="profile-card">
                    <div class="profile-card-header">
                        <span class="profile-card-icon">🖥</span>
                        <h3>Активные сессии</h3>
                    </div>
                    <div class="profile-card-body">
                        <p style="color: var(--text-secondary); margin-bottom: var(--spacing-md); line-height: 1.6;">
                            Завершить все активные сессии на всех устройствах. После этого потребуется повторный вход.
                        </p>
                        <button class="btn btn-danger" id="logout-all-btn">Выйти на всех устройствах</button>
                    </div>
                </div>

            </div>`;

        document.getElementById('password-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const oldPass = document.getElementById('old-password').value;
            const newPass = document.getElementById('new-password').value;
            const confirmPass = document.getElementById('confirm-password').value;
            const errorEl = document.getElementById('password-error');

            if (!oldPass || !newPass || !confirmPass) {
                errorEl.textContent = 'Все поля обязательны.';
                errorEl.style.display = 'block';
                return;
            }

            if (newPass !== confirmPass) {
                errorEl.textContent = 'Новые пароли не совпадают.';
                errorEl.style.display = 'block';
                return;
            }

            if (newPass.length < 8) {
                errorEl.textContent = 'Новый пароль должен содержать не менее 8 символов.';
                errorEl.style.display = 'block';
                return;
            }

            try {
                await auth.changePassword(oldPass, newPass);
                toast.success('Пароль обновлён.');
                document.getElementById('password-form').reset();
                errorEl.style.display = 'none';
            } catch (err) {
                errorEl.textContent = err.message;
                errorEl.style.display = 'block';
            }
        });

        document.getElementById('logout-all-btn').addEventListener('click', async () => {
            const confirmed = await confirmDialog.show(
                'Выйти везде?',
                'Все ваши активные сессии на всех устройствах будут завершены.'
            );
            if (!confirmed) return;
            try {
                await auth.logoutAll();
                toast.success('Все сессии завершены.');
                router.navigate('login');
            } catch (err) {
                toast.error('Ошибка завершения сессий.');
            }
        });
    }

    function _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    return { render };
})();
