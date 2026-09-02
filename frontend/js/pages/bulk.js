/**
 * Bulk Operations page — DNS update, domain add / remove across all configs.
 */
const bulkPage = (() => {
    function _apiError(err) {
        return (err.data && err.data.detail) ? err.data.detail : err.message;
    }

    function _renderSection({ title, description, inputHtml, btnId, btnClass, btnLabel, resultId }) {
        return `<div class="bulk-section">
            <h3>${title}</h3>
            <p class="form-help">${description}</p>
            <div class="form-group">
                ${inputHtml}
            </div>
            <button class="btn ${btnClass}" id="${btnId}">${btnLabel}</button>
            <div id="${resultId}" class="bulk-result-container"></div>
        </div>`;
    }

    async function render() {
        const content = document.getElementById('content');
        content.innerHTML = `<div class="page-header"><h2>Массовые операции</h2></div><div class="page-body">
            ${_renderSection({
                title: 'Обновление DNS',
                description: 'Заменяет DNS серверы во всех конфигурационных файлах. Введите по одному серверу на строку или через запятую.',
                inputHtml: '<label class="form-label" for="bulk-dns-input">DNS серверы</label><textarea class="form-input" id="bulk-dns-input" rows="3" placeholder="1.1.1.1&#10;8.8.8.8"></textarea>',
                btnId: 'bulk-dns-btn', btnClass: 'btn-primary', btnLabel: 'Обновить DNS', resultId: 'bulk-dns-result',
            })}
            ${_renderSection({
                title: 'Добавить домен',
                description: 'Добавить домен во все конфигурационные файлы. Форматы: <code>domain:example.com</code> и <code>regexp:(^|\\.)example\\.com$</code>.',
                inputHtml: '<label class="form-label" for="bulk-add-domain-input">Домен</label><input class="form-input monospace" type="text" id="bulk-add-domain-input" placeholder="domain:example.com">',
                btnId: 'bulk-add-domain-btn', btnClass: 'btn-primary', btnLabel: 'Добавить домен', resultId: 'bulk-add-domain-result',
            })}
            ${_renderSection({
                title: 'Удалить домен',
                description: 'Удалить домен из всех конфигурационных файлов.',
                inputHtml: '<label class="form-label" for="bulk-remove-domain-input">Домен</label><input class="form-input monospace" type="text" id="bulk-remove-domain-input" placeholder="domain:example.com">',
                btnId: 'bulk-remove-domain-btn', btnClass: 'btn-danger', btnLabel: 'Удалить домен', resultId: 'bulk-remove-domain-result',
            })}
        </div>`;

        document.getElementById('bulk-dns-btn').addEventListener('click', _handleDnsUpdate);
        document.getElementById('bulk-add-domain-btn').addEventListener('click', _handleAddDomain);
        document.getElementById('bulk-remove-domain-btn').addEventListener('click', _handleRemoveDomain);
    }

    async function _runBulkOperation({ inputId, btnId, resultId, endpoint, buildBody, emptyMessage, confirmMessage, confirmDetail, loadingLabel, btnLabel, successLabel, errorLabel }) {
        const input = document.getElementById(inputId);
        const btn = document.getElementById(btnId);
        const resultEl = document.getElementById(resultId);

        const raw = input.value.trim();
        if (!raw) {
            toast.error(emptyMessage);
            return;
        }

        let body;
        try {
            body = buildBody(raw);
        } catch (e) {
            toast.error(e.message);
            return;
        }

        const confirmed = await confirmDialog.show(confirmMessage, confirmDetail);
        if (!confirmed) return;

        btn.disabled = true;
        btn.textContent = loadingLabel;

        try {
            const data = await api.post(endpoint, body);
            _renderBulkResult(resultEl, data);
            toast.success(successLabel + ': ' + (data.modified || 0) + ' изменено, ' + (data.failed || 0) + ' ошибок');
            input.value = '';
        } catch (err) {
            toast.error(errorLabel + ': ' + _apiError(err));
        } finally {
            btn.disabled = false;
            btn.textContent = btnLabel;
        }
    }

    async function _handleDnsUpdate() {
        await _runBulkOperation({
            inputId: 'bulk-dns-input',
            btnId: 'bulk-dns-btn',
            resultId: 'bulk-dns-result',
            endpoint: '/admin/bulk/dns',
            buildBody: function (raw) {
                var servers = raw.split(/[\n,]+/).map(function (s) { return s.trim(); }).filter(Boolean);
                if (servers.length === 0) throw new Error('Нет валидных DNS серверов.');
                if (servers.length > 20) throw new Error('Максимум 20 DNS серверов.');
                return { servers: servers };
            },
            emptyMessage: 'Введите хотя бы один DNS сервер.',
            confirmMessage: 'Обновить DNS серверы во всех конфигах?',
            confirmDetail: 'DNS серверы во всех конфигурационных файлах будут заменены.',
            loadingLabel: 'Обновление...',
            btnLabel: 'Обновить DNS',
            successLabel: 'DNS обновлён',
            errorLabel: 'Ошибка обновления DNS',
        });
    }

    async function _handleAddDomain() {
        await _runBulkOperation({
            inputId: 'bulk-add-domain-input',
            btnId: 'bulk-add-domain-btn',
            resultId: 'bulk-add-domain-result',
            endpoint: '/admin/bulk/domain/add',
            buildBody: function (raw) { return { domain: raw }; },
            emptyMessage: 'Введите домен.',
            confirmMessage: 'Добавить домен во все конфиги?',
            confirmDetail: 'Домен будет добавлен во все конфигурационные файлы.',
            loadingLabel: 'Добавление...',
            btnLabel: 'Добавить домен',
            successLabel: 'Домен добавлен',
            errorLabel: 'Ошибка добавления домена',
        });
    }

    async function _handleRemoveDomain() {
        await _runBulkOperation({
            inputId: 'bulk-remove-domain-input',
            btnId: 'bulk-remove-domain-btn',
            resultId: 'bulk-remove-domain-result',
            endpoint: '/admin/bulk/domain/remove',
            buildBody: function (raw) { return { domain: raw }; },
            emptyMessage: 'Введите домен.',
            confirmMessage: 'Удалить домен из всех конфигов?',
            confirmDetail: 'Домен будет удалён из всех конфигурационных файлов.',
            loadingLabel: 'Удаление...',
            btnLabel: 'Удалить домен',
            successLabel: 'Домен удалён',
            errorLabel: 'Ошибка удаления домена',
        });
    }

    function _renderBulkResult(container, data) {
        var details = data.details || [];

        container.innerHTML = '<div class="bulk-result-header">' +
            '<span>Обработано: <strong>' + (data.processed || 0) + '</strong></span>' +
            '<span class="bulk-status-modified">Изменено: <strong>' + (data.modified || 0) + '</strong></span>' +
            '<span class="bulk-status-skipped">Пропущено: <strong>' + (data.skipped || 0) + '</strong></span>' +
            '<span class="bulk-status-failed">Ошибок: <strong>' + (data.failed || 0) + '</strong></span>' +
            '</div>';
        container.style.display = 'block';

        var tableDiv = document.createElement('div');
        container.appendChild(tableDiv);

        tableComponent.render(tableDiv, {
            columns: [
                { key: 'config', label: 'Конфиг' },
                {
                    key: 'status', label: 'Статус', html: true,
                    formatter: function (v) {
                        if (v === 'modified') return '<span class="bulk-status-modified">Изменено</span>';
                        if (v === 'skipped') return '<span class="bulk-status-skipped">Пропущено</span>';
                        if (v === 'failed') return '<span class="bulk-status-failed">Ошибка</span>';
                        return v;
                    },
                },
                { key: 'reason', label: 'Причина', formatter: function (v) { return v || '-'; } },
            ],
            data: details,
            emptyText: '<span class="table-empty-icon">⚙️</span> Конфиги не обработаны',
        });
    }

    return { render: render };
})();
