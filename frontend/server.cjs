const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');

const app = express();
const port = process.env.PORT || 8080;

// API proxy to Azure Functions
app.use('/api', createProxyMiddleware({
  target: 'https://functionapp-dnpzb5eh5nrsy.azurewebsites.net',
  changeOrigin: true,
  logLevel: 'debug'
}));

// Serve static files from React build
app.use(express.static(path.join(__dirname, 'dist')));

// SPA fallback - serve index.html for all non-API routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});