/**
 * Audit Log page — view, filter, paginate admin action history with detail modal.
 */

const auditPage = (() => {
    const ACTIONS = [
        'LOGIN', 'LOGOUT', 'LOGOUT_ALL', 'CHANGE_PASSWORD',
        'CREATE_CONFIG', 'EDIT_CONFIG', 'DELETE_CONFIG',
        'CREATE_USER', 'EDIT_USER', 'DELETE_USER',
        'BULK_DNS_UPDATE', 'BULK_ADD_DOMAIN', 'BULK_REMOVE_DOMAIN',
    ];

    const RESULTS = ['SUCCESS', 'FAILURE', 'PARTIAL'];

    let _page = 1;
    let _limit = 50;
    let _total = 0;
    let _actionFilter = '';
    let _adminFilter = '';
    let _resultFilter = '';
    let _detailEditors = [];

    async function render() {
        _cleanupDetailEditors();
        _page = 1;

        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="page-header">
                <h2>Аудит</h2>
                <div class="page-toolbar" id="audit-toolbar">
                    <select class="form-select" id="audit-action-filter" style="width: 180px;">
                        <option value="">Все действия</option>
                        ${ACTIONS.map(function (a) { return '<option value="' + a + '">' + a + '</option>'; }).join('')}
                    </select>
                    <input class="form-input" type="text" id="audit-admin-filter"
                           placeholder="Админ..." style="width: 140px;">
                    <select class="form-select" id="audit-result-filter" style="width: 130px;">
                        <option value="">Все результаты</option>
                        ${RESULTS.map(function (r) { return '<option value="' + r + '">' + r + '</option>'; }).join('')}
                    </select>
                    <button class="btn btn-primary" id="audit-apply-btn">Применить</button>
                    <button class="btn btn-secondary" id="audit-reset-btn">Сбросить</button>
                </div>
            </div>
            <div class="page-body" id="audit-body">
                <div class="table-loading">Loading...</div>
            </div>
            <div class="pagination" id="audit-pagination" style="display: none;"></div>`;

        document.getElementById('audit-apply-btn').addEventListener('click', function () {
            _actionFilter = document.getElementById('audit-action-filter').value;
            _adminFilter = document.getElementById('audit-admin-filter').value.trim();
            _resultFilter = document.getElementById('audit-result-filter').value;
            _page = 1;
            _loadList();
        });

        document.getElementById('audit-reset-btn').addEventListener('click', function () {
            document.getElementById('audit-action-filter').value = '';
            document.getElementById('audit-admin-filter').value = '';
            document.getElementById('audit-result-filter').value = '';
            _actionFilter = '';
            _adminFilter = '';
            _resultFilter = '';
            _page = 1;
            _loadList();
        });

        await _loadList();
    }

    function _apiError(err) {
        return (err.data && err.data.detail) ? err.data.detail : err.message;
    }

    function _formatTimestamp(ts) {
        if (!ts) return '-';
        var d = new Date(ts * 1000);
        var pad = function (n) { return n < 10 ? '0' + n : '' + n; };
        return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
            ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
    }

    function _escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    async function _loadList() {
        var body = document.getElementById('audit-body');
        var paginationEl = document.getElementById('audit-pagination');

        try {
            var query = 'page=' + _page + '&limit=' + _limit;
            if (_actionFilter) query += '&action=' + encodeURIComponent(_actionFilter);
            if (_adminFilter) query += '&admin=' + encodeURIComponent(_adminFilter);
            if (_resultFilter) query += '&result=' + encodeURIComponent(_resultFilter);

            var data = await api.get('/admin/audit?' + query);
            _total = data.total || 0;
            var items = data.items || [];

            var columns = [
                { key: 'timestamp', label: 'Время', formatter: function (v) { return _formatTimestamp(v); } },
                { key: 'admin_login', label: 'Админ' },
                { key: 'action', label: 'Действие' },
                { key: 'object_type', label: 'Тип' },
                { key: 'object_id', label: 'Объект', formatter: function (v) { return _escapeHtml(v || '-'); } },
                { key: 'result', label: 'Результат' },
            ];

            body.innerHTML = '';

            var tableDiv = document.createElement('div');
            body.appendChild(tableDiv);

            tableComponent.render(tableDiv, {
                columns: columns,
                data: items,
                emptyText: '<span class="table-empty-icon">📋</span> Записи аудита не найдены',
                getActions: function (row) {
                    return [{ label: 'Просмотр', className: 'btn-small btn-primary', handler: function () { _showDetail(row.id); } }];
                },
            });

            _renderPagination(paginationEl);
        } catch (err) {
            body.innerHTML = '<div class="table-error">Ошибка загрузки: ' + _escapeHtml(_apiError(err)) + '</div>';
            paginationEl.style.display = 'none';
        }
    }

    function _renderPagination(el) {
        if (_total === 0) {
            el.style.display = 'none';
            return;
        }

        var totalPages = Math.ceil(_total / _limit);
        el.style.display = 'flex';
        el.innerHTML =
            '<button class="btn btn-small btn-secondary" id="audit-prev-btn" ' + (_page <= 1 ? 'disabled' : '') + '>Назад</button>' +
            '<span class="pagination-info">Страница ' + _page + ' из ' + totalPages + ' (' + _total + ' всего)</span>' +
            '<button class="btn btn-small btn-secondary" id="audit-next-btn" ' + (_page >= totalPages ? 'disabled' : '') + '>Вперёд</button>';

        if (_page > 1) {
            document.getElementById('audit-prev-btn').addEventListener('click', function () {
                if (_page > 1) { _page--; _loadList(); }
            });
        }
        if (_page < totalPages) {
            document.getElementById('audit-next-btn').addEventListener('click', function () {
                if (_page < totalPages) { _page++; _loadList(); }
            });
        }
    }

    async function _showDetail(id) {
        _cleanupDetailEditors();

        var container = document.createElement('div');

        var loadingEl = document.createElement('div');
        loadingEl.className = 'table-loading';
        loadingEl.textContent = 'Загрузка...';
        container.appendChild(loadingEl);

        modal.show('Запись аудита #' + id, container, [
            { text: 'Закрыть', className: 'btn btn-secondary', handler: function () { _closeDetail(); } },
        ], function () { _cleanupDetailEditors(); });

        try {
            var record = await api.get('/admin/audit/' + id);

            container.innerHTML = '';

            var meta = document.createElement('div');
            meta.className = 'audit-detail-meta';
            meta.innerHTML =
                '<div class="audit-detail-row"><span class="audit-detail-label">ID:</span><span>' + record.id + '</span></div>' +
                '<div class="audit-detail-row"><span class="audit-detail-label">Время:</span><span>' + _formatTimestamp(record.timestamp) + '</span></div>' +
                '<div class="audit-detail-row"><span class="audit-detail-label">Админ:</span><span>' + _escapeHtml(record.admin_login) + '</span></div>' +
                '<div class="audit-detail-row"><span class="audit-detail-label">IP:</span><span>' + _escapeHtml(record.ip_address || '-') + '</span></div>' +
                '<div class="audit-detail-row"><span class="audit-detail-label">Действие:</span><span>' + _escapeHtml(record.action) + '</span></div>' +
                '<div class="audit-detail-row"><span class="audit-detail-label">Тип:</span><span>' + _escapeHtml(record.object_type) + '</span></div>' +
                '<div class="audit-detail-row"><span class="audit-detail-label">Объект:</span><span>' + _escapeHtml(record.object_id || '-') + '</span></div>' +
                '<div class="audit-detail-row"><span class="audit-detail-label">Результат:</span><span>' + _escapeHtml(record.result) + '</span></div>' +
                '<div class="audit-detail-row"><span class="audit-detail-label">Описание:</span><span>' + _escapeHtml(record.description || '-') + '</span></div>';
            container.appendChild(meta);

            if (record.old_value_json) {
                var oldHeader = document.createElement('h4');
                oldHeader.className = 'audit-detail-section-title';
                oldHeader.textContent = 'Старое значение';
                container.appendChild(oldHeader);

                var oldEditor = document.createElement('div');
                oldEditor.className = 'monaco-container';
                oldEditor.style.height = '200px';
                oldEditor.id = 'audit-old-editor';
                container.appendChild(oldEditor);

                _initDetailEditor('audit-old-editor', _formatJson(record.old_value_json));
            }

            if (record.new_value_json) {
                var newHeader = document.createElement('h4');
                newHeader.className = 'audit-detail-section-title';
                newHeader.textContent = 'Новое значение';
                container.appendChild(newHeader);

                var newEditor = document.createElement('div');
                newEditor.className = 'monaco-container';
                newEditor.style.height = '200px';
                newEditor.id = 'audit-new-editor';
                container.appendChild(newEditor);

                _initDetailEditor('audit-new-editor', _formatJson(record.new_value_json));
            }

            if (!record.old_value_json && !record.new_value_json) {
                var noJson = document.createElement('p');
                noJson.className = 'form-help';
                noJson.textContent = 'Снимки значений для этой записи отсутствуют.';
                container.appendChild(noJson);
            }
        } catch (err) {
            container.innerHTML = '<div class="table-error">Ошибка загрузки: ' + _escapeHtml(_apiError(err)) + '</div>';
        }
    }

    function _formatJson(raw) {
        try {
            var parsed = JSON.parse(raw);
            return JSON.stringify(parsed, null, 2);
        } catch (_) {
            return raw;
        }
    }

    function _initDetailEditor(wrapperId, content) {
        if (typeof monaco === 'undefined') {
            var el = document.getElementById(wrapperId);
            if (el) {
                var pre = document.createElement('pre');
                pre.className = 'log-content-fallback';
                pre.textContent = content;
                el.innerHTML = '';
                el.appendChild(pre);
            }
            return;
        }

        var el = document.getElementById(wrapperId);
        if (!el) return;
        el.innerHTML = '';

        var editor = monaco.editor.create(el, {
            value: content,
            language: 'json',
            theme: 'vs-dark',
            readOnly: true,
            automaticLayout: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 12,
            lineNumbers: 'on',
            tabSize: 2,
        });

        _detailEditors.push(editor);
    }

    function _closeDetail() {
        _cleanupDetailEditors();
        modal.close();
    }

    function _cleanupDetailEditors() {
        _detailEditors.forEach(function (ed) { ed.dispose(); });
        _detailEditors = [];
    }

    function dispose() {
        _cleanupDetailEditors();
    }

    return { render: render, dispose: dispose };
})();
