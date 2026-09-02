/**
 * Logs page — tabs for Requests/Responses/App/Admin with Monaco read-only viewer.
 */

const logsPage = (() => {
    const TABS = [
        { id: 'requests', label: 'Запросы' },
        { id: 'responses', label: 'Ответы' },
        { id: 'app', label: 'Приложение' },
        { id: 'admin', label: 'Админ' },
    ];

    let _activeTab = 'requests';
    let _monacoEditor = null;
    let _lines = 500;

    async function render() {
        const content = document.getElementById('content');
        content.innerHTML = `
            <div class="page-header">
                <h2>Логи</h2>
                <div class="page-toolbar">
                    <label class="form-label" for="logs-lines-input" style="margin: 0; white-space: nowrap;">Строки:</label>
                    <input class="form-input" type="number" id="logs-lines-input"
                           value="${_lines}" min="1" max="50000"
                           style="width: 100px;">
                    <button class="btn btn-primary" id="logs-refresh-btn">Обновить</button>
                </div>
            </div>
            <div class="tabs" id="logs-tabs">${_renderTabs()}</div>
            <div class="editor-wrapper" id="logs-editor" style="height: calc(100vh - 180px);">
                <div class="table-loading">Loading...</div>
            </div>`;

        document.querySelectorAll('#logs-tabs .tab-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                _activeTab = btn.getAttribute('data-tab');
                _updateTabStyles();
                _loadLogContent();
            });
        });

        document.getElementById('logs-refresh-btn').addEventListener('click', () => {
            _loadLogContent();
        });

        document.getElementById('logs-lines-input').addEventListener('change', (e) => {
            var val = parseInt(e.target.value, 10);
            if (isNaN(val) || val < 1) val = 1;
            if (val > 50000) val = 50000;
            e.target.value = val;
            _lines = val;
            _loadLogContent();
        });

        document.getElementById('logs-lines-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('logs-refresh-btn').click();
            }
        });

        _updateTabStyles();
        await _loadLogContent();
    }

    function _renderTabs() {
        return TABS.map((tab) => {
            const activeClass = tab.id === _activeTab ? ' active' : '';
            return `<button class="tab-btn${activeClass}" data-tab="${tab.id}">${tab.label}</button>`;
        }).join('');
    }

    function _updateTabStyles() {
        document.querySelectorAll('#logs-tabs .tab-btn').forEach((btn) => {
            if (btn.getAttribute('data-tab') === _activeTab) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    async function _loadLogContent() {
        const editorWrapper = document.getElementById('logs-editor');
        if (!editorWrapper) return;

        try {
            const data = await api.get(`/admin/logs/${_activeTab}?lines=${_lines}`);

            const content = data.content || '';
            const lineCount = data.returned_lines || 0;

            if (!content) {
                if (_monacoEditor) {
                    _monacoEditor.dispose();
                    _monacoEditor = null;
                }
                editorWrapper.innerHTML = '<div class="table-empty">Лог пуст.</div>';
                return;
            }

            _initOrUpdateMonaco(content, lineCount);
        } catch (err) {
            if (_monacoEditor) {
                _monacoEditor.dispose();
                _monacoEditor = null;
            }
            editorWrapper.innerHTML = `<div class="table-error">Ошибка загрузки: ${err.message}</div>`;
        }
    }

    function _initOrUpdateMonaco(content, _lineCount) {
        const editorWrapper = document.getElementById('logs-editor');
        if (!editorWrapper) return;

        if (typeof monaco === 'undefined') {
            const pre = document.createElement('pre');
            pre.className = 'log-content-fallback';
            pre.textContent = content;
            editorWrapper.innerHTML = '';
            editorWrapper.appendChild(pre);
            return;
        }

        if (_monacoEditor) {
            _monacoEditor.setValue(content);
            return;
        }

        editorWrapper.innerHTML = '';
        const el = document.createElement('div');
        el.className = 'monaco-container';
        el.style.height = '100%';
        editorWrapper.appendChild(el);

        _monacoEditor = monaco.editor.create(el, {
            value: content,
            language: _detectLanguage(_activeTab),
            theme: 'vs-dark',
            readOnly: true,
            automaticLayout: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 12,
            lineNumbers: 'on',
            wordWrap: 'off',
        });
    }

    function _detectLanguage(tab) {
        if (tab === 'requests' || tab === 'responses') {
            return 'json';
        }
        return 'plaintext';
    }

    function dispose() {
        if (_monacoEditor) {
            _monacoEditor.dispose();
            _monacoEditor = null;
        }
    }

    return { render, dispose };
})();
