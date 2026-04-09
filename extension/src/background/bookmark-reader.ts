import type { BookmarkItem } from '../types/api';

/** Reads all bookmarks from Chrome and flattens to a list */
export class BookmarkReader {
  /** Get all bookmarks as a flat list, skipping synthetic root nodes */
  async readAll(): Promise<BookmarkItem[]> {
    const tree = await chrome.bookmarks.getTree();
    const items: BookmarkItem[] = [];
    for (const root of tree) {
      this.flatten(root, null, 0, items, true);
    }
    return items;
  }

  private flatten(
    node: chrome.bookmarks.BookmarkTreeNode,
    parentId: string | null,
    depth: number,
    result: BookmarkItem[],
    isRoot: boolean,
  ): void {
    // Skip the synthetic root nodes (depth 0 roots added by Chrome)
    if (!isRoot) {
      result.push({
        id: node.id,
        parent_id: parentId,
        title: node.title,
        url: node.url ?? null,
        depth,
      });
    }
    if (node.children) {
      for (const child of node.children) {
        this.flatten(
          child,
          node.id,
          isRoot ? 0 : depth + 1,
          result,
          false,
        );
      }
    }
  }
}
