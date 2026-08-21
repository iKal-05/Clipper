import { useEffect, useRef, useState } from 'react';
import type { ProgressEvent } from '../lib/api';

export function useJobSocket(jobId: string | null) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [stage, setStage] = useState<string>('queued');
  const [pct, setPct] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectingRef = useRef(false);

  function connect() {
    if (!jobId || reconnectingRef.current) return;
    reconnectingRef.current = true;

    const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
    const ws = new WebSocket(`${WS_BASE}/api/jobs/${jobId}/stream`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] Connected');
      reconnectingRef.current = false;
    };
    ws.onmessage = (msg) => {
      try {
        const event: ProgressEvent = JSON.parse(msg.data);
        setEvents((prev) => [...prev, event]);
        if (event.type === 'stage') {
          setStage(event.stage);
          setPct(event.pct);
        }
        if (event.type === 'error') {
          setError(event.message);
        }
      } catch (e) {
        console.warn('[WS] Parse error', e);
      }
    };
    ws.onclose = () => {
      console.log('[WS] Closed');
      // Reconnect after 2s if job not done/error and not intentionally closed
      if (!reconnectingRef.current && stage !== 'done' && stage !== 'error') {
        reconnectTimeoutRef.current = window.setTimeout(() => {
          reconnectingRef.current = false;
          connect();
        }, 2000);
      }
    };
    ws.onerror = (e) => console.error('[WS] Error', e);
  }

  useEffect(() => {
    if (!jobId) return;
    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [jobId]);

  return { events, stage, pct, error };
}