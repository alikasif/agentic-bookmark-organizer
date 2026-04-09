import type { BookmarkOperation } from '../types/api';

/** Applies bookmark operations to Chrome bookmarks */
export class BookmarkWriter {
  private folderCache: Map<string, string> = new Map();

  /** Apply a list of bookmark operations */
  async applyOperations(operations: BookmarkOperation[]): Promise<void> {
    this.folderCache.clear();

    const createOps = operations.filter((op) => op.op === 'create_folder');
    const otherOps = operations.filter((op) => op.op !== 'create_folder');

    for (const op of createOps) {
      await this.createFolder(op.folder_path);
    }

    for (const op of otherOps) {
      if (op.op === 'move' && op.bookmark_id !== null) {
        await this.moveBookmark(op.bookmark_id, op.folder_path, op.new_title);
      } else if (op.op === 'rename' && op.bookmark_id !== null) {
        await this.renameBookmark(op.bookmark_id, op.new_title);
      }
    }
  }

  private async createFolder(path: string[]): Promise<string> {
    const cacheKey = path.join('/');
    const cached = this.folderCache.get(cacheKey);
    if (cached !== undefined) {
      return cached;
    }

    let parentId: string | undefined;
    for (let i = 0; i < path.length; i++) {
      const partialPath = path.slice(0, i + 1).join('/');
      const existing = this.folderCache.get(partialPath);
      if (existing !== undefined) {
        parentId = existing;
        continue;
      }
      const folder = await chrome.bookmarks.create({
        parentId,
        title: path[i],
      });
      this.folderCache.set(partialPath, folder.id);
      parentId = folder.id;
    }

    return this.folderCache.get(cacheKey) ?? '';
  }

  private async moveBookmark(
    bookmarkId: string,
    folderPath: string[],
    newTitle: string | null,
  ): Promise<void> {
    const parentId = await this.createFolder(folderPath);
    await chrome.bookmarks.move(bookmarkId, { parentId });
    if (newTitle !== null) {
      await chrome.bookmarks.update(bookmarkId, { title: newTitle });
    }
  }

  private async renameBookmark(
    bookmarkId: string,
    newTitle: string | null,
  ): Promise<void> {
    if (newTitle === null) return;
    await chrome.bookmarks.update(bookmarkId, { title: newTitle });
  }
}
