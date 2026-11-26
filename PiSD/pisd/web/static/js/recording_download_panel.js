(() => {
  'use strict';

  const registry = {};

  function api(path, options = {}) {
    return fetch(path, {
      method: options.method || 'GET',
      headers: { 'Content-Type': 'application/json' },
      body: options.body ? JSON.stringify(options.body) : undefined,
      cache: 'no-store',
    }).then(async (response) => {
      const data = await response.json().catch(() => ({ ok: false, message: `HTTP ${response.status}` }));
      if (!response.ok || data.ok === false) {
        throw Object.assign(new Error(data.message || `Request failed: ${path}`), { payload: data, status: response.status });
      }
      return data;
    });
  }

  function shortPath(value, max = 60) {
    const text = String(value || '');
    if (text.length <= max) return text || 'n/a';
    return `…${text.slice(-(max - 1))}`;
  }

  function formatBytes(bytes) {
    const value = Number(bytes || 0);
    if (!Number.isFinite(value) || value <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let scaled = value;
    let unit = 0;
    while (scaled >= 1024 && unit < units.length - 1) {
      scaled /= 1024;
      unit += 1;
    }
    return `${scaled >= 10 || unit === 0 ? scaled.toFixed(0) : scaled.toFixed(1)} ${units[unit]}`;
  }

  function formatDateTime(value) {
    const parsed = Date.parse(String(value || ''));
    if (!Number.isFinite(parsed)) return 'n/a';
    return new Date(parsed).toLocaleString(undefined, { hour12: false });
  }

  function folderDisplayName(item, kind) {
    if (!item) return 'No folder selected';
    const prefix = kind === 'snapshot' ? 'Snapshot' : 'Recording';
    return `${prefix}: ${item.label || item.date || item.id || 'folder'}`;
  }

  function initPanel(panel) {
    const prefix = panel.dataset.recordingDownloadPanel || '';
    if (!prefix) return null;
    const id = (suffix) => document.getElementById(`${prefix}${suffix}`);
    const els = {
      kind: id('FileKind'),
      select: id('FileSelect'),
      summary: id('FileSummary'),
      name: id('FileSummaryName'),
      frames: id('FileSummaryFrames'),
      size: id('FileSummarySize'),
      modified: id('FileSummaryModified'),
      folderId: id('FileSummaryId'),
      zip: id('FileSummaryZip'),
      refresh: id('RefreshFiles'),
      download: id('DownloadZip'),
      delete: id('DeleteFolder'),
      notice: id('FilesNotice'),
    };
    let collections = { recordings: [], snapshots: [] };
    const folderReader = window.PiSDRecordingReader.createReader();

    function setNotice(message, code = 'PISD-OK-000') {
      if (!els.notice) return;
      els.notice.textContent = message;
      els.notice.dataset.state = String(code).startsWith('PISD-OK') ? 'ok' : 'error';
    }

    function selectedItem() {
      const kind = els.kind?.value || 'recording';
      const itemId = els.select?.value || '';
      const list = kind === 'snapshot' ? collections.snapshots : collections.recordings;
      const item = list.find((entry) => entry.id === itemId) || null;
      return { kind, id: itemId, item };
    }

    function setButtons(item) {
      const hasItem = folderReader.verified() && Boolean(item && item.id);
      const running = Boolean(item?.running);
      if (els.download) els.download.disabled = !hasItem;
      if (els.delete) {
        els.delete.disabled = !hasItem || running || window.PiDriveDestructive.busy(els.delete);
        els.delete.title = running ? 'Stop the active recording before deleting this folder.' : 'Delete the selected folder inside the PiSD recordings root.';
      }
    }

    function updateDetails() {
      const { kind, id: itemId, item } = selectedItem();
      if (els.summary) els.summary.dataset.state = !item ? 'empty' : (!folderReader.verified() ? 'unverified' : (item.running ? 'running' : 'ready'));
      if (els.name) els.name.textContent = folderDisplayName(item, kind);
      if (els.frames) els.frames.textContent = item ? String(Number(item.frame_count || 0)) : '0';
      if (els.size) els.size.textContent = item ? formatBytes(item.bytes) : '0 B';
      if (els.modified) els.modified.textContent = item ? formatDateTime(item.modified_at_utc || item.started_at_utc) : 'n/a';
      if (els.folderId) els.folderId.textContent = item ? shortPath(itemId || item.id) : 'n/a';
      if (els.zip) els.zip.textContent = item ? shortPath(item.download_name || `PiSD_${kind}_${String(itemId || item.id).replaceAll('/', '_')}.zip`) : 'n/a';
      setButtons(item);
      return { kind, id: itemId, item };
    }

    function renderOptions() {
      if (!els.select) return;
      const kind = els.kind?.value || 'recording';
      const list = kind === 'snapshot' ? collections.snapshots : collections.recordings;
      const previous = els.select.value;
      els.select.innerHTML = '';
      if (!list.length) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = kind === 'snapshot' ? 'No snapshot folders' : 'No recording folders';
        els.select.appendChild(option);
        updateDetails();
        if (folderReader.verified()) setNotice(kind === 'snapshot' ? 'No snapshot folders found.' : 'No recording folders found.');
        return;
      }
      for (const item of list) {
        const option = document.createElement('option');
        option.value = item.id;
        const count = Number(item.frame_count || 0);
        const running = item.running ? ' ACTIVE' : '';
        option.textContent = `${item.date || ''}  ${item.label || item.id}  (${count} frames, ${formatBytes(item.bytes)})${running}`;
        els.select.appendChild(option);
      }
      if (previous && list.some((item) => item.id === previous)) els.select.value = previous;
      const selected = updateDetails();
      if (folderReader.verified()) setNotice(`Selected ${kind}: ${selected.item?.id || selected.item?.label || 'folder'}`);
    }

    async function refresh() {
      const pending = folderReader.read();
      updateDetails();
      setNotice('Refreshing saved folders; actions unavailable until confirmed.');
      const result = await pending;
      if (!result || !folderReader.isCurrent(result.token)) return;
      if (result.error) {
        updateDetails();
        setNotice(result.error + ' Check the Pi connection, then Refresh.', 'PISD-REC-007');
        return;
      }
      const payload = result.payload;
      collections = payload.collections;
      renderOptions();
      const visible = els.kind?.value === 'snapshot' ? collections.snapshots : collections.recordings;
      if (visible.length) setNotice(`Loaded ${collections.recordings.length} recordings and ${collections.snapshots.length} snapshot folders.`, payload.code);
    }

    function download() {
      const { kind, id: itemId, item } = updateDetails();
      if (!folderReader.verified()) return;
      if (!itemId || !item) {
        setNotice('Select a folder before downloading.', 'PISD-REC-008');
        return;
      }
      const url = `/api/recording/download.zip?kind=${encodeURIComponent(kind)}&id=${encodeURIComponent(itemId)}`;
      setNotice(`Preparing ${kind} zip: ${itemId} (${formatBytes(item.bytes)}). Browser download should start shortly.`);
      window.location.assign(url);
    }

    async function deleteFolder() {
      if (!folderReader.verified() || window.PiDriveDestructive.busy(els.delete)) return;
      const { kind, id: itemId, item } = updateDetails();
      if (!itemId || !item) {
        setNotice('Select a folder before deleting.', 'PISD-REC-008');
        return;
      }
      if (item.running) {
        setNotice('Stop the active recording before deleting its folder.', 'PISD-REC-009');
        return;
      }
      const details = `${Number(item.frame_count || 0)} frames, ${formatBytes(item.bytes)}, modified ${formatDateTime(item.modified_at_utc)}`;
      const ok = await window.PiDriveDestructive.confirm(els.delete, `Delete ${kind} folder?\n\n${item.label || itemId}\n${itemId}\n${details}\n\nOnly this selected PiSD recordings folder will be removed. This cannot be undone.`);
      if (!ok) { updateDetails(); return; }
      try {
        const current = selectedItem();
        if (!folderReader.verified() || current.kind !== kind || current.id !== itemId || !current.item || current.item.running) {
          setNotice('Folder selection or availability changed. Refresh and confirm again.', 'PISD-REC-009');
          return;
        }
        if (els.delete) els.delete.disabled = true;
        const data = await api('/api/recording/delete', { method: 'POST', body: { kind, id: itemId, confirm: true } });
        if (data.ok !== true) throw new Error('Delete was not confirmed.');
        folderReader.invalidate();
        const key = kind === 'snapshot' ? 'snapshots' : 'recordings';
        collections[key] = collections[key].filter(entry => entry.id !== itemId);
        renderOptions();
        await refresh();
        if (!folderReader.verified() && !folderReader.loading()) setNotice(`Deleted ${kind}: ${itemId}; folder refresh unconfirmed. Refresh to continue.`, 'PISD-REC-007');
      } catch (err) {
        setNotice(`Delete failed: ${String(err.message || err)}`, 'PISD-REC-009');
      } finally {
        window.PiDriveDestructive.finish(els.delete);
        updateDetails();
      }
    }

    els.refresh?.addEventListener('click', refresh);
    els.download?.addEventListener('click', download);
    els.delete?.addEventListener('click', deleteFolder);
    els.kind?.addEventListener('change', renderOptions);
    els.select?.addEventListener('change', () => {
      const selected = updateDetails();
      if (folderReader.verified() && selected.item) {
        setNotice(`Selected ${selected.kind}: ${selected.id}${selected.item.running ? ' (active recording; deletion unavailable)' : ''}`);
      }
    });
    updateDetails();

    const apiObject = { refresh, updateDetails, renderOptions };
    registry[prefix] = apiObject;
    return apiObject;
  }

  function initAll() {
    document.querySelectorAll('[data-recording-download-panel]').forEach(initPanel);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initAll, { once: true });
  else initAll();

  window.PiSDRecordingDownloadPanels = registry;
})();
