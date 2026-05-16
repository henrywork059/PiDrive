const frontStatus = document.getElementById('fpStatusJson');
const frontCode = document.getElementById('fpGlobalCode');

async function frontApi(method, path, body = undefined) {
  const options = { method, headers: {} };
  if (body !== undefined && method !== 'GET') {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const payload = await response.json();
  if (frontCode && payload.code) frontCode.textContent = payload.code;
  if (frontStatus) frontStatus.textContent = JSON.stringify(payload, null, 2);
  return payload;
}

document.getElementById('fpRefreshStatus')?.addEventListener('click', () => frontApi('GET', '/api/status'));
document.getElementById('fpStopAll')?.addEventListener('click', () => frontApi('POST', '/api/control/stop', {}));
