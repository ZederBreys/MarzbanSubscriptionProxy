/**
 * Configs page — list, create, edit, delete JSON configurations.
 */

const configsPage = (() => {
    let _monacoEditor = null;
    let _sortBy = 'name';
    let _sortOrder = 'asc';
    let _search = '';

    async function render() {
        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="page-header">
                <h2>Конфиги</h2>
                <div class="page-toolbar">
                    <input class="form-input" type="text" id="configs-search"
                           placeholder="Поиск..." style="width: 200px;">
                    <button class="btn btn-primary" id="configs-create-btn">Создать</button>
                </div>
            </div>
            <div class="page-body" id="configs-body">
                <div class="table-loading">Loading...</div>
            </div>`;

        document.getElementById('configs-search').addEventListener('input', (e) => {
            _search = e.target.value.trim();
            _loadList();
        });

        document.getElementById('configs-create-btn').addEventListener('click', () => {
            _showCreateModal();
        });

        await _loadList();
    }

    async function _loadList() {
        const body = document.getElementById('configs-body');
        try {
            let url = `/admin/configs?sort_by=${_sortBy}&order=${_sortOrder}`;
            if (_search) {
                url += `&search=${encodeURIComponent(_search)}`;
            }
            const data = await api.get(url);
            const configs = data.configs || [];

            const columns = [
                { key: 'name', label: 'Имя', sortable: true },
                { key: 'is_default', label: 'По умолчанию', formatter: (v) => v ? 'Да' : 'Нет' },
                { key: 'users_count', label: 'Пользователи', sortable: true },
                { key: 'size_bytes', label: 'Размер', formatter: _formatBytes, sortable: true },
            ];

            tableComponent.render(body, {
                columns,
                data: configs,
                getActions: (row) => {
                    const acts = [
                        { label: 'Редактировать', className: 'btn-small btn-primary', handler: () => _showEditModal(row.name) },
                    ];
                    if (!row.is_default) {
                        acts.push({ label: 'Удалить', className: 'btn-small btn-danger', handler: () => _deleteConfig(row) });
                    }
                    return acts;
                },
                onSort: (key, dir) => {
                    _sortBy = key;
                    _sortOrder = dir;
                    _loadList();
                },
                sortBy: _sortBy,
                sortOrder: _sortOrder,
                emptyText: '<span class="table-empty-icon">📂</span> Конфиги не найдены',
            });
        } catch (err) {
            body.innerHTML = `<div class="table-error">Ошибка загрузки конфигов: ${err.message}</div>`;
        }
    }

    function _formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    async function _showCreateModal() {
        const container = document.createElement('div');

        const nameGroup = document.createElement('div');
        nameGroup.className = 'form-group';
        nameGroup.innerHTML = `
            <label class="form-label">Имя конфига</label>
            <input class="form-input" type="text" id="cfg-name-input"
                   placeholder="my-config" pattern="[A-Za-z0-9_-]+">
            <span class="form-help">Только буквы, цифры, дефисы и подчёркивания.</span>`;

        const templateGroup = document.createElement('div');
        templateGroup.className = 'form-group';
        templateGroup.innerHTML = `
            <label class="form-label">Шаблон (необязательно)</label>
            <select class="form-select" id="cfg-template-select">
                <option value="">Пустой</option>
            </select>
            <span class="form-help">Скопировать существующий конфиг как основу.</span>`;

        const editorWrapper = document.createElement('div');
        editorWrapper.className = 'monaco-container';
        editorWrapper.style.height = '400px';
        editorWrapper.id = 'cfg-editor-wrapper';

        const errorEl = document.createElement('div');
        errorEl.className = 'form-error';
        errorEl.style.display = 'none';
        errorEl.id = 'cfg-error';

        container.appendChild(nameGroup);
        container.appendChild(templateGroup);
        container.appendChild(editorWrapper);
        container.appendChild(errorEl);

        modal.show('Создать конфиг', container, [
            { text: 'Отмена', className: 'btn btn-secondary', handler: () => _closeEditorAndModal() },
            { text: 'Сохранить', className: 'btn btn-primary', handler: () => _saveNewConfig() },
        ], () => _disposeMonaco());

        await _loadTemplates();
        _initMonaco('cfg-editor-wrapper', '');

        document.getElementById('cfg-template-select').addEventListener('change', async (e) => {
            const templateName = e.target.value;
            if (!templateName) {
                if (_monacoEditor) _monacoEditor.setValue('');
                return;
            }
            try {
                const data = await api.get(`/admin/configs/${templateName}`);
                _monacoEditor.setValue(data.config.json);
            } catch (err) {
                toast.error('Не удалось загрузить шаблон.');
            }
        });
    }

    async function _showEditModal(name) {
        try {
            const data = await api.get(`/admin/configs/${name}`);

            const container = document.createElement('div');

            const nameDisplay = document.createElement('div');
            nameDisplay.className = 'editor-filename';
            nameDisplay.textContent = name;

            const editorWrapper = document.createElement('div');
            editorWrapper.className = 'monaco-container';
            editorWrapper.style.height = 'calc(100vh - 260px)';
            editorWrapper.id = 'cfg-editor-wrapper';

            const errorEl = document.createElement('div');
            errorEl.className = 'form-error';
            errorEl.style.display = 'none';
            errorEl.id = 'cfg-error';

            container.appendChild(nameDisplay);
            container.appendChild(editorWrapper);
            container.appendChild(errorEl);

            modal.show(`Редактирование: ${name}`, container, [
                { text: 'Отмена', className: 'btn btn-secondary', handler: () => _closeEditorAndModal() },
                { text: 'Сохранить', className: 'btn btn-primary', handler: () => _saveEditConfig(name) },
            ], () => _disposeMonaco());

            _initMonaco('cfg-editor-wrapper', data.config.json);
        } catch (err) {
            toast.error('Не удалось загрузить конфиг.');
        }
    }

    async function _loadTemplates() {
        const select = document.getElementById('cfg-template-select');
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
            // silently ignore
        }
    }

    function _initMonaco(wrapperId, content) {
        _disposeMonaco();

        if (typeof monaco === 'undefined') {
            var fallbackEl = document.getElementById(wrapperId);
            if (fallbackEl) {
                fallbackEl.innerHTML =
                    '<div class="editor-fallback">Редактор не загружен. Обновите страницу.</div>';
            }
            return;
        }

        var el = document.getElementById(wrapperId);
        if (!el) return;

        _monacoEditor = monaco.editor.create(el, {
            value: content,
            language: 'json',
            theme: 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 13,
            lineNumbers: 'on',
            renderLineHighlight: 'line',
            tabSize: 2,
        });
    }

    function _disposeMonaco() {
        if (_monacoEditor) {
            _monacoEditor.dispose();
            _monacoEditor = null;
        }
    }

    function _closeEditorAndModal() {
        _disposeMonaco();
        modal.close();
    }

    async function _saveNewConfig() {
        const nameInput = document.getElementById('cfg-name-input');
        const name = nameInput ? nameInput.value.trim() : '';
        const errorEl = document.getElementById('cfg-error');

        if (!name) {
            errorEl.textContent = 'Имя конфига обязательно.';
            errorEl.style.display = 'block';
            return;
        }

        if (!/^[A-Za-z0-9_-]+$/.test(name)) {
            errorEl.textContent = 'Недопустимое имя. Используйте A-Z, 0-9, дефисы и подчёркивания.';
            errorEl.style.display = 'block';
            return;
        }

        let jsonContent;
        try {
            jsonContent = JSON.parse(_monacoEditor.getValue());
        } catch (e) {
            errorEl.textContent = `Некорректный JSON: ${e.message}`;
            errorEl.style.display = 'block';
            return;
        }

        try {
            await api.post('/admin/configs', { name, json: jsonContent });
            toast.success(`Конфиг "${name}" создан.`);
            _closeEditorAndModal();
            await _loadList();
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.style.display = 'block';
        }
    }

    async function _saveEditConfig(name) {
        const errorEl = document.getElementById('cfg-error');
        let jsonContent;
        try {
            jsonContent = JSON.parse(_monacoEditor.getValue());
        } catch (e) {
            errorEl.textContent = `Некорректный JSON: ${e.message}`;
            errorEl.style.display = 'block';
            return;
        }

        try {
            await api.put(`/admin/configs/${name}`, { json: jsonContent });
            toast.success(`Конфиг "${name}" обновлён.`);
            _closeEditorAndModal();
            await _loadList();
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.style.display = 'block';
        }
    }

    async function _deleteConfig(row) {
        let detail = `Это действие нельзя отменить.`;
        if (row.users_count > 0) {
            detail += ` ${row.users_count} пользователей используют этот конфиг.`;
        }

        const confirmed = await confirmDialog.show(
            `Удалить конфиг "${row.name}"?`,
            detail
        );

        if (!confirmed) return;

        try {
            await api.del(`/admin/configs/${row.name}`);
            toast.success(`Конфиг "${row.name}" удалён.`);
            await _loadList();
        } catch (err) {
            toast.error(`Ошибка удаления: ${err.message}`);
        }
    }

    function dispose() {
        _disposeMonaco();
    }

    window.addEventListener('monaco-ready', function () {
        var wrapper = document.getElementById('cfg-editor-wrapper');
        if (wrapper && wrapper.childNodes.length === 1 && wrapper.querySelector('.editor-fallback')) {
            var content = _monacoEditor ? _monacoEditor.getValue() : '';
            _disposeMonaco();
            _initMonaco('cfg-editor-wrapper', content);
        }
    });

    return { render, dispose };
})();
