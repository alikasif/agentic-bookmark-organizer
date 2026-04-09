import type { ExtensionMessage, FolderNode, OrganizeResponse } from '../types/api';

type PopupState =
  | 'idle'
  | 'fetching'
  | 'analyzing'
  | 'preview'
  | 'applying'
  | 'done'
  | 'error';

function getElement<T extends HTMLElement>(id: string): T {
  const el = document.getElementById(id);
  if (el === null) throw new Error(`Element #${id} not found`);
  return el as T;
}

function showState(state: PopupState): void {
  const states: PopupState[] = [
    'idle',
    'fetching',
    'analyzing',
    'preview',
    'applying',
    'done',
    'error',
  ];
  for (const s of states) {
    const el = document.getElementById(`state-${s}`);
    if (el !== null) {
      el.classList.toggle('hidden', s !== state);
    }
  }
}

function renderFolderTree(
  node: FolderNode,
  container: HTMLElement,
  depth = 0,
): void {
  if (depth > 0) {
    const item = document.createElement('div');
    item.className = 'folder-item';
    item.style.paddingLeft = `${depth * 12}px`;

    const icon = document.createElement('span');
    icon.className = 'folder-icon';
    icon.textContent = '\uD83D\uDCC1';

    const label = document.createElement('span');
    label.textContent = node.name;

    const count = document.createElement('span');
    count.className = 'folder-count';
    count.textContent = String(node.bookmark_ids.length);

    item.appendChild(icon);
    item.appendChild(label);
    item.appendChild(count);
    container.appendChild(item);
  }
  for (const child of node.children) {
    renderFolderTree(child, container, depth + 1);
  }
}

async function checkBackendStatus(): Promise<void> {
  const chip = getElement<HTMLDivElement>('backend-status');
  const organizeBtn = getElement<HTMLButtonElement>('btn-organize');
  try {
    const response = await fetch('http://localhost:8765/health');
    if (response.ok) {
      chip.textContent = 'Backend: Online';
      chip.className = 'status-chip status-ok';
      organizeBtn.disabled = false;
    } else {
      throw new Error('Not ok');
    }
  } catch {
    chip.textContent = 'Backend: Offline';
    chip.className = 'status-chip status-error';
    organizeBtn.disabled = true;
  }
}

function setupMessageListener(): void {
  chrome.runtime.onMessage.addListener((message: ExtensionMessage) => {
    if (message.type === 'PROGRESS') {
      const payload = message.payload as { status: PopupState };
      showState(payload.status);
    } else if (message.type === 'PREVIEW') {
      const response = message.payload as OrganizeResponse;
      showState('preview');
      const tree = getElement<HTMLDivElement>('folder-tree');
      tree.innerHTML = '';
      renderFolderTree(response.proposed_structure, tree);
      const stats = getElement<HTMLSpanElement>('preview-stats-text');
      stats.textContent = `${response.stats.total_bookmarks} bookmarks \u2192 ${response.stats.folders_created} folders`;
    } else if (message.type === 'DONE') {
      const payload = message.payload as { count: number };
      showState('done');
      const doneStats = getElement<HTMLDivElement>('done-stats');
      doneStats.textContent = `${payload.count} operations applied`;
    } else if (message.type === 'ERROR') {
      const payload = message.payload as { message: string };
      showState('error');
      getElement<HTMLParagraphElement>('error-message').textContent =
        payload.message;
    }
  });
}

function setupButtons(): void {
  getElement<HTMLButtonElement>('btn-organize').addEventListener('click', () => {
    showState('fetching');
    void chrome.runtime.sendMessage({ type: 'START_ORGANIZE' });
  });

  getElement<HTMLButtonElement>('btn-apply').addEventListener('click', () => {
    showState('applying');
    void chrome.runtime.sendMessage({ type: 'CONFIRM' });
  });

  getElement<HTMLButtonElement>('btn-cancel').addEventListener('click', () => {
    void chrome.runtime.sendMessage({ type: 'CANCEL' });
    showState('idle');
  });

  getElement<HTMLButtonElement>('btn-retry').addEventListener('click', () => {
    showState('idle');
    void checkBackendStatus();
  });

  getElement<HTMLButtonElement>('btn-restart').addEventListener('click', () => {
    showState('idle');
    void checkBackendStatus();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  showState('idle');
  setupMessageListener();
  setupButtons();
  void checkBackendStatus();
});
