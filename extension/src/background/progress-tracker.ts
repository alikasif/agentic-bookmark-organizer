export type JobStatus =
  | 'idle'
  | 'fetching'
  | 'analyzing'
  | 'preview'
  | 'applying'
  | 'done'
  | 'error';

export interface JobState {
  status: JobStatus;
  progress: number;
  total: number;
  errors: string[];
  message?: string;
}

const STORAGE_KEY = 'job_state';

/** Persists job state to chrome.storage.local */
export class ProgressTracker {
  /** Get current job state from storage */
  async getState(): Promise<JobState> {
    const result = await chrome.storage.local.get(STORAGE_KEY);
    return (result[STORAGE_KEY] as JobState | undefined) ?? {
      status: 'idle',
      progress: 0,
      total: 0,
      errors: [],
    };
  }

  /** Update job state in storage */
  async setState(state: Partial<JobState>): Promise<void> {
    const current = await this.getState();
    const updated: JobState = { ...current, ...state };
    await chrome.storage.local.set({ [STORAGE_KEY]: updated });
  }

  /** Reset job state to idle */
  async reset(): Promise<void> {
    await this.setState({
      status: 'idle',
      progress: 0,
      total: 0,
      errors: [],
      message: undefined,
    });
  }
}
