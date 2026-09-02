/**
 * Reusable data table.
 *
 * Usage:
 *   tableComponent.render(container, {
 *       columns: [
 *           { key: 'name', label: 'Name', sortable: true },
 *           { key: 'size', label: 'Size', formatter: (v) => formatBytes(v) },
 *       ],
 *       data: items,
 *       actions: [
 *           { label: 'Edit', className: 'btn-small btn-primary', handler: (row) => edit(row) },
 *       ],
 *       onSort: (key, direction) => reload(key, direction),
 *       sortBy: 'name',
 *       sortOrder: 'asc',
 *       emptyText: 'No items found.',
 *   });
 */

const tableComponent = (() => {
    function render(container, options) {
        const {
            columns = [],
            data = [],
            actions = [],
            getActions = null,
            onSort = null,
            sortBy = null,
            sortOrder = 'asc',
            emptyText = 'No items.',
        } = options;

        if (!data || data.length === 0) {
            container.innerHTML = `<div class="table-empty">${emptyText}</div>`;
            return;
        }

        const hasActions = getActions || actions.length > 0;

        const wrapper = document.createElement('div');
        wrapper.className = 'table-wrapper';

        const table = document.createElement('table');
        table.className = 'data-table';

        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');

        columns.forEach((col) => {
            const th = document.createElement('th');
            th.textContent = col.label || col.key;

            if (col.sortable && onSort) {
                th.classList.add('sortable');
                th.setAttribute('data-sort-key', col.key);

                if (sortBy === col.key) {
                    th.classList.add('sorted');
                    th.setAttribute('data-sort-dir', sortOrder);
                }

                th.addEventListener('click', () => {
                    const currentKey = th.getAttribute('data-sort-key');
                    const currentDir = th.getAttribute('data-sort-dir') || 'asc';
                    const newDir = currentDir === 'asc' ? 'desc' : 'asc';
                    onSort(currentKey, newDir);
                });
            }

            headerRow.appendChild(th);
        });

        if (hasActions) {
            const th = document.createElement('th');
            th.textContent = 'Действия';
            th.className = 'actions-column';
            headerRow.appendChild(th);
        }

        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');

        data.forEach((row, index) => {
            const tr = document.createElement('tr');
            tr.setAttribute('data-index', index);

            columns.forEach((col) => {
                const td = document.createElement('td');
                let value = row[col.key];

                if (value === null || value === undefined) {
                    value = '';
                }

                if (col.formatter) {
                    if (col.html) {
                        td.innerHTML = col.formatter(value, row);
                    } else {
                        td.textContent = col.formatter(value, row);
                    }
                } else {
                    td.textContent = String(value);
                }

                tr.appendChild(td);
            });

            if (hasActions) {
                const td = document.createElement('td');
                td.className = 'actions-cell';

                const rowActions = getActions ? getActions(row, index) : actions;

                rowActions.forEach((action) => {
                    const btn = document.createElement('button');
                    btn.className = action.className || 'btn-small';
                    btn.textContent = action.label;
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        action.handler(row, index);
                    });
                    td.appendChild(btn);
                });

                tr.appendChild(td);
            }

            tbody.appendChild(tr);
        });

        table.appendChild(tbody);
        wrapper.appendChild(table);

        container.innerHTML = '';
        container.appendChild(wrapper);
    }

    return { render };
})();
