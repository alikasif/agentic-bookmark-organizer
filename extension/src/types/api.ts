/** TypeScript interfaces matching the backend Pydantic models */

export interface BookmarkItem {
  id: string;
  parent_id: string | null;
  title: string;
  url: string | null;
  depth: number;
}

export interface OrganizeRequest {
  bookmarks: BookmarkItem[];
  dry_run: boolean;
  max_folders: number;
}

export interface FolderNode {
  name: string;
  children: FolderNode[];
  bookmark_ids: string[];
}

export interface BookmarkOperation {
  op: 'create_folder' | 'move' | 'rename';
  bookmark_id: string | null;
  folder_path: string[];
  new_title: string | null;
}

export interface OrganizeResponse {
  proposed_structure: FolderNode;
  operations: BookmarkOperation[];
  stats: {
    total_bookmarks: number;
    folders_created: number;
    bookmarks_moved: number;
  };
  warnings: string[];
}

export interface HealthResponse {
  status: string;
  version: string;
}

export interface FetchedContent {
  url: string;
  title: string;
  description: string;
  success: boolean;
}

export interface ContentFetchResponse {
  results: FetchedContent[];
}

export type MessageType =
  | 'START_ORGANIZE'
  | 'CANCEL'
  | 'CONFIRM'
  | 'PREVIEW'
  | 'PROGRESS'
  | 'DONE'
  | 'ERROR';

export interface ExtensionMessage {
  type: MessageType;
  payload?: unknown;
}
