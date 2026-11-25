const frontStatus = document.getElementById('fpStatusJson');
const frontCode = document.getElementById('fpGlobalCode');

async function frontApi(method, path, body = undefined) {
  const options = { method, headers: {} };
  if (body !== undefined && method !== 'GET') {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  const message = document.getElementById('fpActionStatus');
  const stopping = method === 'POST' && path === '/api/control/stop';
  if (message) message.textContent = stopping ? 'Sending STOP request…' : 'Refreshing status…';
  try {
    const response = await fetch(path, options);
    const payload = await response.json();
    if (frontStatus) frontStatus.textContent = JSON.stringify(payload, null, 2);
    if (!response.ok || payload?.ok === false) throw new Error('Request rejected');
    if (frontCode && payload.code) frontCode.textContent = payload.code;
    if (message) message.textContent = stopping ? 'STOP request acknowledged. Verify physical state.' : 'Status received.';
    return payload;
  } catch (_error) {
    if (frontCode) frontCode.textContent = 'Unverified';
    if (message) message.textContent = stopping ? 'STOP request not confirmed. Verify physical state immediately.' : 'Status unavailable. Retry Refresh status.';
    return null;
  }
}

document.getElementById('fpRefreshStatus')?.addEventListener('click', () => frontApi('GET', '/api/status'));
document.getElementById('fpStopAll')?.addEventListener('click', () => frontApi('POST', '/api/control/stop', {}));
