import type {
  BookmarkItem,
  ContentFetchResponse,
  HealthResponse,
  OrganizeResponse,
} from '../types/api';

const BACKEND_URL = 'http://localhost:8765';

/** Client for communicating with the Python backend API */
export class BackendClient {
  private readonly baseUrl: string;

  constructor(baseUrl: string = BACKEND_URL) {
    this.baseUrl = baseUrl;
  }

  /** Check if the backend is running */
  async checkHealth(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }
    return response.json() as Promise<HealthResponse>;
  }

  /** Request AI organization of bookmarks */
  async organize(
    bookmarks: BookmarkItem[],
    dryRun: boolean = true,
    maxFolders: number = 20,
  ): Promise<OrganizeResponse> {
    const response = await fetch(`${this.baseUrl}/organize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bookmarks,
        dry_run: dryRun,
        max_folders: maxFolders,
      }),
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(
        `Organize request failed: ${response.status} ${error}`,
      );
    }
    return response.json() as Promise<OrganizeResponse>;
  }

  /** Fetch content metadata for a list of URLs */
  async fetchContent(urls: string[]): Promise<ContentFetchResponse> {
    const response = await fetch(`${this.baseUrl}/content/fetch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ urls }),
    });
    if (!response.ok) {
      throw new Error(`Content fetch failed: ${response.status}`);
    }
    return response.json() as Promise<ContentFetchResponse>;
  }
}
