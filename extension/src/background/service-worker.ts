import type { BookmarkOperation, ExtensionMessage, OrganizeResponse } from '../types/api';
import { BackendClient } from './backend-client';
import { BookmarkReader } from './bookmark-reader';
import { BookmarkWriter } from './bookmark-writer';
import { ProgressTracker } from './progress-tracker';

const client = new BackendClient();
const reader = new BookmarkReader();
const writer = new BookmarkWriter();
const tracker = new ProgressTracker();

let pendingOperations: BookmarkOperation[] = [];
let cancelled = false;

chrome.runtime.onMessage.addListener(
  (message: ExtensionMessage, _sender, sendResponse) => {
    if (message.type === 'START_ORGANIZE') {
      cancelled = false;
      void handleStartOrganize();
      sendResponse({ ok: true });
    } else if (message.type === 'CONFIRM') {
      void handleConfirm();
      sendResponse({ ok: true });
    } else if (message.type === 'CANCEL') {
      cancelled = true;
      void tracker.setState({ status: 'idle' });
      sendResponse({ ok: true });
    }
    return false;
  },
);

async function handleStartOrganize(): Promise<void> {
  try {
    await tracker.setState({ status: 'fetching', progress: 0 });
    sendToPopup({ type: 'PROGRESS', payload: { status: 'fetching' } });

    const bookmarks = await reader.readAll();
    await tracker.setState({ total: bookmarks.length });

    if (cancelled) return;

    await tracker.setState({ status: 'analyzing' });
    sendToPopup({ type: 'PROGRESS', payload: { status: 'analyzing' } });

    const response: OrganizeResponse = await client.organize(bookmarks, true, 20);
    pendingOperations = response.operations;

    await tracker.setState({ status: 'preview' });
    sendToPopup({ type: 'PREVIEW', payload: response });
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    await tracker.setState({ status: 'error', errors: [msg] });
    sendToPopup({ type: 'ERROR', payload: { message: msg } });
  }
}

async function handleConfirm(): Promise<void> {
  try {
    await tracker.setState({ status: 'applying', progress: 0 });
    sendToPopup({ type: 'PROGRESS', payload: { status: 'applying' } });

    await writer.applyOperations(pendingOperations);

    await tracker.setState({
      status: 'done',
      progress: pendingOperations.length,
    });
    sendToPopup({ type: 'DONE', payload: { count: pendingOperations.length } });
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    await tracker.setState({ status: 'error', errors: [msg] });
    sendToPopup({ type: 'ERROR', payload: { message: msg } });
  }
}

function sendToPopup(message: ExtensionMessage): void {
  chrome.runtime.sendMessage(message).catch(() => {
    // Popup may not be open — ignore
  });
}
