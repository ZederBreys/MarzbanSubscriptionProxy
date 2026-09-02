/**
 * Centralized HTTP client for admin panel API.
 *
 * Usage:
 *   const data = await api.get('/admin/users?search=test');
 *   const result = await api.post('/admin/configs', { name: 'new', json: {...} });
 *   const result = await api.put('/admin/configs/mypc', { json: {...} });
 *   const result = await api.del('/admin/configs/mypc');
 */

const api = (() => {
    function _getCSRFToken() {
        const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
        return match ? match[1] : null;
    }

    async function request(method, url, body) {
        const headers = {
            'Origin': window.location.origin,
        };

        if (!['GET', 'HEAD'].includes(method)) {
            const csrf = _getCSRFToken();
            if (csrf) {
                headers['X-CSRF-Token'] = csrf;
            }
        }

        if (body && !(body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }

        const options = { method, headers, credentials: 'same-origin' };

        if (body) {
            options.body = body instanceof FormData ? body : JSON.stringify(body);
        }

        const response = await fetch(url, options);

        if (response.status === 401 && !url.includes('/auth/login')) {
            router.navigate('login');
            throw new Error('Not authenticated');
        }

        const text = await response.text();
        let data;
        try {
            data = JSON.parse(text);
        } catch {
            data = { detail: text };
        }

        if (!response.ok) {
            const err = new Error(data.detail || `HTTP ${response.status}`);
            err.status = response.status;
            err.data = data;
            throw err;
        }

        return data;
    }

    return {
        get: (url) => request('GET', url),
        post: (url, body) => request('POST', url, body),
        put: (url, body) => request('PUT', url, body),
        del: (url) => request('DELETE', url),
    };
})();
