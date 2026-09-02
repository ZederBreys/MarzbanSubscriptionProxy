/**
 * Users page — list, create, edit, delete subscription users.
 */

const usersPage = (() => {
    let _sortBy = 'sud_id';
    let _sortOrder = 'asc';
    let _search = '';
    let _selectedConfigFilter = '';
    var _escHandler = null;

    async function render() {
        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="page-header">
                <h2>Пользователи</h2>
                <div class="page-toolbar">
                    <input class="form-input" type="text" id="users-search"
                           placeholder="Поиск..." style="width: 180px;">
                    <select class="form-select" id="users-config-filter" style="width: 150px;">
                        <option value="">Все конфиги</option>
                    </select>
                    <button class="btn btn-primary" id="users-create-btn">Создать</button>
                </div>
            </div>
            <div class="page-body" id="users-body">
                <div class="table-loading">Loading...</div>
            </div>`;

        document.getElementById('users-search').addEventListener('input', (e) => {
            _search = e.target.value.trim();
            _loadList();
        });

        document.getElementById('users-config-filter').addEventListener('change', (e) => {
            _selectedConfigFilter = e.target.value;
            _loadList();
        });

        document.getElementById('users-create-btn').addEventListener('click', () => {
            _showCreateModal();
        });

        await _loadConfigFilter();
        await _loadList();
    }

    async function _loadConfigFilter() {
        const select = document.getElementById('users-config-filter');
        if (!select) return;
        try {
            const data = await api.get('/admin/configs');
            const configs = data.configs || [];
            configs.forEach((c) => {
                const opt = document.createElement('option');
                opt.value = c.name;
                opt.textContent = c.name;
                select.appendChild(opt);
            });
        } catch (err) {
            // ignore
        }
    }

    async function _loadList() {
        const body = document.getElementById('users-body');
        try {
            let url = `/admin/users?sort_by=${_sortBy}&order=${_sortOrder}`;
            if (_search) {
                url += `&search=${encodeURIComponent(_search)}`;
            }
            if (_selectedConfigFilter) {
                url += `&config=${encodeURIComponent(_selectedConfigFilter)}`;
            }
            const data = await api.get(url);
            const users = data.users || [];

            const columns = [
                { key: 'sud_id', label: 'ID подписки', sortable: true },
                { key: 'config', label: 'Конфиг', sortable: true },
                { key: 'profile_title', label: 'Название профиля', sortable: true },
                { key: 'profile_update_interval', label: 'Обновление (ч)', sortable: true },
            ];

            tableComponent.render(body, {
                columns,
                data: users,
                getActions: (row) => [
                    { label: 'Редактировать', className: 'btn-small btn-primary', handler: () => _showEditModal(row) },
                    { label: 'Удалить', className: 'btn-small btn-danger', handler: () => _deleteUser(row) },
                ],
                onSort: (key, dir) => {
                    _sortBy = key;
                    _sortOrder = dir;
                    _loadList();
                },
                sortBy: _sortBy,
                sortOrder: _sortOrder,
                emptyText: '<span class="table-empty-icon">👤</span> Пользователи не найдены',
            });
        } catch (err) {
            body.innerHTML = `<div class="table-error">Ошибка загрузки пользователей: ${err.message}</div>`;
        }
    }

    async function _showCreateModal() {
        const container = document.createElement('div');

        const sudIdGroup = document.createElement('div');
        sudIdGroup.className = 'form-group';
        sudIdGroup.innerHTML = `
            <label class="form-label">ID подписки <span class="required">*</span></label>
            <input class="form-input" type="text" id="user-sud-id"
                   placeholder="идентификатор-подписки" required>`;

        const configGroup = document.createElement('div');
        configGroup.className = 'form-group';
        configGroup.innerHTML = `
            <label class="form-label">Конфиг</label>
            <select class="form-select" id="user-config-select">
                <option value="default">default</option>
            </select>`;

        const titleGroup = document.createElement('div');
        titleGroup.className = 'form-group';
        titleGroup.innerHTML = `
            <label class="form-checkbox-label">
                <input type="checkbox" id="user-title-check" class="form-checkbox">
                Установить название подписки
            </label>
            <input class="form-input" type="text" id="user-title-input"
                   maxlength="30" placeholder="Название профиля" style="display:none;">`;

        const intervalGroup = document.createElement('div');
        intervalGroup.className = 'form-group';
        intervalGroup.innerHTML = `
            <label class="form-checkbox-label">
                <input type="checkbox" id="user-interval-check" class="form-checkbox">
                Установить интервал обновления
            </label>
            <input class="form-input" type="number" id="user-interval-input"
                   min="1" placeholder="12" style="display:none;">`;

        const errorEl = document.createElement('div');
        errorEl.className = 'form-error';
        errorEl.style.display = 'none';
        errorEl.id = 'user-error';

        container.appendChild(sudIdGroup);
        container.appendChild(configGroup);
        container.appendChild(titleGroup);
        container.appendChild(intervalGroup);
        container.appendChild(errorEl);

        modal.show('Создать пользователя', container, [
            { text: 'Отмена', className: 'btn btn-secondary', handler: () => modal.close() },
            { text: 'Сохранить', className: 'btn btn-primary', handler: () => _saveNewUser() },
        ]);

        await _loadConfigOptions('user-config-select', 'default');

        document.getElementById('user-title-check').addEventListener('change', (e) => {
            document.getElementById('user-title-input').style.display =
                e.target.checked ? '' : 'none';
        });
        document.getElementById('user-interval-check').addEventListener('change', (e) => {
            document.getElementById('user-interval-input').style.display =
                e.target.checked ? '' : 'none';
        });
    }

    async function _showEditModal(row) {
        const container = document.createElement('div');

        const sudIdGroup = document.createElement('div');
        sudIdGroup.className = 'form-group';
        sudIdGroup.innerHTML = `
            <label class="form-label">ID подписки <span class="required">*</span></label>
            <input class="form-input" type="text" id="user-sud-id" value="${_escapeHtml(row.sud_id || '')}">`;

        const configGroup = document.createElement('div');
        configGroup.className = 'form-group';
        configGroup.innerHTML = `
            <label class="form-label">Конфиг</label>
            <select class="form-select" id="user-config-select"></select>`;

        const titleCheck = row.profile_title ? 'checked' : '';
        const titleDisplay = row.profile_title ? '' : 'style="display:none;"';
        const intervalCheck = row.profile_update_interval && row.profile_update_interval !== 12 ? 'checked' : '';
        const intervalDisplay = row.profile_update_interval && row.profile_update_interval !== 12 ? '' : 'style="display:none;"';
        const intervalVal = row.profile_update_interval || 12;

        container.innerHTML += `
            <div class="form-group">
                <label class="form-checkbox-label">
                    <input type="checkbox" id="user-title-check" class="form-checkbox" ${titleCheck}>
                    Установить название подписки
                </label>
                <input class="form-input" type="text" id="user-title-input"
                       maxlength="30" value="${_escapeHtml(row.profile_title || '')}" ${titleDisplay}>
            </div>
            <div class="form-group">
                <label class="form-checkbox-label">
                    <input type="checkbox" id="user-interval-check" class="form-checkbox" ${intervalCheck}>
                    Установить интервал обновления
                </label>
                <input class="form-input" type="number" id="user-interval-input"
                       min="1" value="${intervalVal}" ${intervalDisplay}>
            </div>`;

        const errorEl = document.createElement('div');
        errorEl.className = 'form-error';
        errorEl.style.display = 'none';
        errorEl.id = 'user-error';

        container.appendChild(sudIdGroup);
        container.appendChild(configGroup);
        container.appendChild(errorEl);

        modal.show('Редактировать пользователя', container, [
            { text: 'Отмена', className: 'btn btn-secondary', handler: () => modal.close() },
            { text: 'Сохранить', className: 'btn btn-primary', handler: () => _saveEditUser(row.sud_id) },
        ]);

        await _loadConfigOptions('user-config-select', row.config);

        document.getElementById('user-title-check').addEventListener('change', (e) => {
            document.getElementById('user-title-input').style.display =
                e.target.checked ? '' : 'none';
        });
        document.getElementById('user-interval-check').addEventListener('change', (e) => {
            document.getElementById('user-interval-input').style.display =
                e.target.checked ? '' : 'none';
        });
    }

    async function _loadConfigOptions(selectId, selectedValue) {
        const select = document.getElementById(selectId);
        if (!select) return;
        try {
            const data = await api.get('/admin/configs');
            const configs = data.configs || [];
            configs.forEach((c) => {
                const opt = document.createElement('option');
                opt.value = c.name;
                opt.textContent = c.name;
                if (c.name === selectedValue) opt.selected = true;
                select.appendChild(opt);
            });
        } catch (err) {
            // keep default option
        }
    }

    function _showError(message) {
        const el = document.getElementById('user-error');
        if (el) {
            el.textContent = message;
            el.style.display = 'block';
        }
    }

    function _getUserFormData() {
        const sudId = (document.getElementById('user-sud-id')?.value || '').trim();
        const config = document.getElementById('user-config-select')?.value || 'default';

        const titleCheck = document.getElementById('user-title-check');
        const profileTitle = titleCheck?.checked
            ? (document.getElementById('user-title-input')?.value || '').trim() || null
            : null;

        const intervalCheck = document.getElementById('user-interval-check');
        const intervalVal = intervalCheck?.checked
            ? parseInt(document.getElementById('user-interval-input')?.value, 10)
            : 12;

        return { sudId, config, profileTitle, updateInterval: intervalVal || 12 };
    }

    function _validateUserForm(data) {
        if (!data.sudId) {
            _showError('ID подписки обязателен.');
            return false;
        }

        if (data.profileTitle !== null && data.profileTitle !== undefined && data.profileTitle.length > 30) {
            _showError('Название профиля не более 30 символов.');
            return false;
        }

        if (isNaN(data.updateInterval) || data.updateInterval < 1) {
            _showError('Интервал обновления должен быть положительным числом.');
            return false;
        }

        return true;
    }

    async function _saveNewUser() {
        const data = _getUserFormData();
        if (!_validateUserForm(data)) return;

        const body = {
            sud_id: data.sudId,
            config: data.config,
        };
        if (data.profileTitle !== null) body.profile_title = data.profileTitle;
        if (data.updateInterval !== 12) body.profile_update_interval = data.updateInterval;

        try {
            await api.post('/admin/users', body);
            toast.success(`Пользователь "${data.sudId}" создан.`);
            modal.close();
            await _loadList();
        } catch (err) {
            _showError(err.message);
        }
    }

    async function _saveEditUser(sudId) {
        const data = _getUserFormData();
        if (!_validateUserForm(data)) return;

        const body = {};
        if (data.sudId !== sudId) body.sud_id = data.sudId;
        body.config = data.config;
        body.profile_title = data.profileTitle;
        body.profile_update_interval = data.updateInterval;

        try {
            await api.put(`/admin/users/${encodeURIComponent(sudId)}`, body);
            toast.success('Пользователь обновлён.');
            modal.close();
            await _loadList();
        } catch (err) {
            _showError(err.message);
        }
    }

    async function _deleteUser(row) {
        let message = `Удалить пользователя "${row.sud_id}"?`;
        let detail = 'Это действие нельзя отменить.';

        const showConfigCheck = row.config !== 'default';

        const confirmed = await _userDeleteConfirm(message, detail, showConfigCheck, row);
        if (!confirmed.result) return;

        let url = `/admin/users/${encodeURIComponent(row.sud_id)}`;
        if (confirmed.deleteConfig) {
            url += '?delete_config=true';
        }

        try {
            await api.del(url);
            toast.success(`Пользователь "${row.sud_id}" удалён.`);
            await _loadList();
        } catch (err) {
            toast.error(`Ошибка удаления: ${err.message}`);
        }
    }

    function _userDeleteConfirm(message, detail, showConfigCheck, row) {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'confirm-overlay';

            const dialog = document.createElement('div');
            dialog.className = 'confirm-dialog';

            const body = document.createElement('div');
            body.className = 'confirm-body';
            body.innerHTML = `<p class="confirm-message">${message}</p><p class="confirm-detail">${detail}</p>`;

            let configCheckLabel = null;
            if (showConfigCheck) {
                configCheckLabel = document.createElement('label');
                configCheckLabel.className = 'form-checkbox-label';
                configCheckLabel.style.marginTop = '12px';
                configCheckLabel.innerHTML = `
                    <input type="checkbox" class="form-checkbox" id="confirm-delete-config" checked>
                    Также удалить конфиг "${_escapeHtml(row.config)}"`;
                body.appendChild(configCheckLabel);
            }

            const actions = document.createElement('div');
            actions.className = 'confirm-actions';

            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'btn btn-secondary';
            cancelBtn.textContent = 'Отмена';

            const confirmBtn = document.createElement('button');
            confirmBtn.className = 'btn btn-danger';
            confirmBtn.textContent = 'Удалить';

            actions.appendChild(cancelBtn);
            actions.appendChild(confirmBtn);
            dialog.appendChild(body);
            dialog.appendChild(actions);
            overlay.appendChild(dialog);
            document.body.appendChild(overlay);

            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    _dismiss(overlay, resolve, { result: false, deleteConfig: false });
                }
            });

            cancelBtn.addEventListener('click', () => {
                _dismiss(overlay, resolve, { result: false, deleteConfig: false });
            });

            confirmBtn.addEventListener('click', () => {
                const deleteConfig = showConfigCheck
                    ? document.getElementById('confirm-delete-config')?.checked || false
                    : false;
                _dismiss(overlay, resolve, { result: true, deleteConfig });
            });

            if (_escHandler) {
                document.removeEventListener('keydown', _escHandler);
                _escHandler = null;
            }
            _escHandler = function (e) {
                if (e.key === 'Escape') {
                    _dismiss(overlay, resolve, { result: false, deleteConfig: false });
                }
            };
            document.addEventListener('keydown', _escHandler);

            requestAnimationFrame(() => {
                overlay.classList.add('confirm-overlay-visible');
                dialog.classList.add('confirm-dialog-visible');
            });
            confirmBtn.focus();
        });
    }

    function _dismiss(overlay, resolve, result) {
        if (_escHandler) {
            document.removeEventListener('keydown', _escHandler);
            _escHandler = null;
        }

        const dialog = overlay.querySelector('.confirm-dialog');
        overlay.classList.remove('confirm-overlay-visible');
        if (dialog) dialog.classList.remove('confirm-dialog-visible');
        overlay.addEventListener('transitionend', () => {
            if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
            resolve(result);
        });
    }

    function _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    return { render };
})();
