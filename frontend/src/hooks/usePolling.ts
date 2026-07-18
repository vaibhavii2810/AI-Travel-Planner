/**
 * Generic polling hook.
 * Calls `fn` every `intervalMs` while `active` is true.
 * Cleans up on unmount or when active becomes false.
 */
import { useEffect, useRef } from 'react';

export function usePolling(fn: () => void, intervalMs: number, active: boolean): void {
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    if (!active) return;

    const id = setInterval(() => {
      fnRef.current();
    }, intervalMs);

    return () => clearInterval(id);
  }, [active, intervalMs]);
}
