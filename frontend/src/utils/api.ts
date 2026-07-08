// Lightweight typed wrapper around axios responses.
// Adds a unified error shape (ApiError) and tracks request_id.

import type { AxiosError, AxiosResponse } from 'axios';
import type { ApiError } from '../types';

export interface RequestResult<T> {
  data: T;
  request_id?: string;
}

export function unwrap<T>(promise: Promise<AxiosResponse<T>>): Promise<RequestResult<T>> {
  return promise.then(r => ({
    data: r.data,
    request_id: r.headers['x-request-id'] as string | undefined,
  }));
}

export function formatApiError(err: unknown): string {
  if (err && typeof err === 'object' && 'isAxiosError' in err) {
    const axErr = err as AxiosError<ApiError>;
    if (axErr.response?.data?.message) {
      const rid = axErr.response.data.request_id;
      return rid ? `${axErr.response.data.message} (request_id: ${rid})` : axErr.response.data.message;
    }
    if (axErr.message) return axErr.message;
  }
  if (err instanceof Error) return err.message;
  return 'Unknown error';
}
