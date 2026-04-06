/**
 * CRA dev-server proxy configuration.
 * All requests to /api are forwarded to the target backend,
 * so there are no CORS issues during local development.
 *
 * To use your LOCAL backend instead of the remote one, set:
 *   REACT_APP_PROXY_TARGET=http://localhost:8000
 * in your .env.development.local file (or change the default below).
 */
const { createProxyMiddleware } = require('http-proxy-middleware');

const PROXY_TARGET =
  process.env.REACT_APP_PROXY_TARGET || 'http://127.0.0.1:5000';

module.exports = function (app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: PROXY_TARGET,
      changeOrigin: true,
      secure: false,
      // Remove cookie Domain attribute so browser scopes cookies to current host
      // (works for both localhost and 127.0.0.1 in local dev).
      cookieDomainRewrite: '',
      on: {
        error: (err, req, res) => {
          console.error('[proxy error]', err.message);
          res.status(502).json({ error: 'Proxy error', detail: err.message });
        },
      },
    })
  );
};
