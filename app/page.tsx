'use client';

import { useEffect, useState } from 'react';

import dynamic from 'next/dynamic';

import { createClient } from '@supabase/supabase-js';

const Globe3D = dynamic(
  () => import('@/app/components/Globe3D'),
  {
    ssr: false,
  }
);

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

interface Event {
  id: number;
  title: string;
  severity: string;
  latitude: number;
  longitude: number;
  magnitude: number;
  event_time: string;
}

export default function Home() {
  const [events, setEvents] = useState<Event[]>([]);

  const [selectedEvent, setSelectedEvent] =
    useState<Event | null>(null);

  const [trackedEvent, setTrackedEvent] =
    useState<Event | null>(null);

  const [lastUpdate, setLastUpdate] = useState(
    new Date()
  );

  const [autoRotate, setAutoRotate] =
    useState(true);

  const [satView, setSatView] = useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const fetchEvents = async () => {
    setRefreshing(true);

    const { data, error } = await supabase
      .from('events')
      .select('*')
      .order('event_time', {
        ascending: false,
      })
      .limit(100);

    if (!error && data) {
      setEvents(data);

      setLastUpdate(new Date());
    }

    setTimeout(() => {
      setRefreshing(false);
    }, 700);
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  useEffect(() => {
    if (!autoRotate) return;

    const interval = setInterval(fetchEvents, 30000);

    return () => clearInterval(interval);
  }, [autoRotate]);

  const highCount = events.filter(
    (e) => e.severity === 'high'
  ).length;

  const mediumCount = events.filter(
    (e) => e.severity === 'medium'
  ).length;

  const lowCount = events.filter(
    (e) => e.severity === 'low'
  ).length;

  return (
    <main className="relative w-screen h-screen overflow-hidden bg-[#02050A] text-white">
      {/* GLOBE */}
      <Globe3D
        events={events}
        onEventClick={(event) => {
          setSelectedEvent(event);

          setTrackedEvent(event);
        }}
        autoRotate={autoRotate}
        satView={satView}
        trackedEvent={trackedEvent}
      />

      {/* SCANLINES */}
      <div className="scanlines pointer-events-none" />

      {/* VIGNETTE */}
      <div className="vignette pointer-events-none" />

      {/* HUD FRAME */}
      <div className="hud-frame pointer-events-none">
        <div className="corner top-left" />
        <div className="corner top-right" />
        <div className="corner bottom-left" />
        <div className="corner bottom-right" />
      </div>

      {/* TOP LEFT */}
      <div className="absolute top-7 left-7 z-20">
        <div className="hud-panel w-[350px]">
          <div className="flex items-center justify-between">
            <div>
              <p className="hud-label">
                GLOBAL SYSTEM
              </p>

              <h1 className="hud-title">
                EVENTHORIZON
              </h1>
            </div>

            <div className="status-ping" />
          </div>

          <div className="mt-7 space-y-3 text-sm text-white/70">
            <div className="flex justify-between">
              <span>SATELLITE LINK</span>

              <span className="text-[#4ADE80]">
                ACTIVE
              </span>
            </div>

            <div className="flex justify-between">
              <span>THREAT MONITOR</span>

              <span className="text-[#4ADE80]">
                ONLINE
              </span>
            </div>

            <div className="flex justify-between">
              <span>LIVE FEED</span>

              <span className="text-[#4ADE80]">
                STABLE
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* TOP RIGHT */}
      <div className="absolute top-7 right-7 z-20">
        <div className="hud-panel w-[320px]">
          <div className="flex items-center justify-between">
            <div>
              <p className="hud-label">
                THREAT ANALYTICS
              </p>

              <h2 className="text-4xl font-bold mt-2">
                {events.length}
              </h2>
            </div>

            <div className="threat-ring">
              <span>
                {Math.min(
                  100,
                  highCount * 10 +
                    mediumCount * 3
                )}
                %
              </span>
            </div>
          </div>

          <div className="mt-6">
            <div className="threat-bar">
              <div
                className="threat-fill"
                style={{
                  width: `${Math.min(
                    100,
                    highCount * 10 +
                      mediumCount * 3
                  )}%`,
                }}
              />
            </div>
          </div>

          <div className="mt-6 flex gap-8">
            <div>
              <p className="text-[#ff5533] text-sm font-semibold">
                HIGH
              </p>

              <p className="text-3xl font-bold">
                {highCount}
              </p>
            </div>

            <div>
              <p className="text-[#ffb347] text-sm font-semibold">
                MED
              </p>

              <p className="text-3xl font-bold">
                {mediumCount}
              </p>
            </div>

            <div>
              <p className="text-[#ffe082] text-sm font-semibold">
                LOW
              </p>

              <p className="text-3xl font-bold">
                {lowCount}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* LIVE FEED */}
      <div className="absolute left-7 bottom-7 z-20">
        <div className="hud-panel w-[390px] h-[360px]">
          <div className="flex items-center justify-between mb-5">
            <div>
              <p className="hud-label">
                LIVE EVENT STREAM
              </p>

              <h2 className="text-2xl font-semibold mt-2">
                INCOMING SIGNALS
              </h2>
            </div>

            <div className="live-dot" />
          </div>

          <div className="space-y-3 overflow-y-auto h-[250px] pr-2 custom-scroll">
            {events.slice(0, 12).map((event) => (
              <button
                key={event.id}
                onClick={() => {
                  setSelectedEvent(event);

                  setTrackedEvent(event);
                }}
                className="feed-item w-full text-left"
              >
                <div
                  className={`feed-indicator ${
                    event.severity === 'high'
                      ? 'bg-[#ff5533]'
                      : event.severity ===
                        'medium'
                      ? 'bg-[#ffb347]'
                      : 'bg-[#ffe082]'
                  }`}
                />

                <div className="flex-1">
                  <p className="text-sm text-white/90 truncate">
                    {event.title}
                  </p>

                  <div className="flex justify-between mt-2 text-xs text-white/40">
                    <span>
                      M {event.magnitude}
                    </span>

                    <span>
                      {new Date(
                        event.event_time
                      ).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* DOCK */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20">
        <div className="dock-panel">
          <button
            onClick={() =>
              setAutoRotate(!autoRotate)
            }
            className={`dock-btn ${
              autoRotate ? 'active-dock' : ''
            }`}
          >
            {autoRotate ? 'AUTO' : 'MANUAL'}
          </button>

          <button
            onClick={fetchEvents}
            className={`dock-btn ${
              refreshing ? 'active-dock' : ''
            }`}
          >
            {refreshing
              ? 'SYNCING...'
              : 'REFRESH'}
          </button>

          <button
            onClick={() =>
              setSatView(!satView)
            }
            className={`dock-btn ${
              satView ? 'active-dock' : ''
            }`}
          >
            {satView
              ? 'SAT VIEW'
              : 'DAY VIEW'}
          </button>

          <button
            onClick={() => {
              if (selectedEvent) {
                setTrackedEvent(selectedEvent);
              }
            }}
            className={`dock-btn ${
              trackedEvent
                ? 'active-dock'
                : ''
            }`}
          >
            TRACK
          </button>
        </div>
      </div>

      {/* EVENT CARD */}
      {selectedEvent && (
        <div className="absolute right-7 bottom-7 z-20">
          <div className="hud-panel w-[360px]">
            <div className="flex items-start justify-between">
              <div>
                <p className="hud-label">
                  EVENT INTELLIGENCE
                </p>

                <h2 className="text-2xl font-semibold mt-2">
                  {selectedEvent.title}
                </h2>
              </div>

              <button
                onClick={() =>
                  setSelectedEvent(null)
                }
                className="text-white/40 hover:text-white transition"
              >
                ✕
              </button>
            </div>

            <div className="mt-7 space-y-4">
              <div className="intel-row">
                <span>MAGNITUDE</span>

                <span>
                  {selectedEvent.magnitude}
                </span>
              </div>

              <div className="intel-row">
                <span>SEVERITY</span>

                <span
                  className={
                    selectedEvent.severity ===
                    'high'
                      ? 'text-[#ff5533]'
                      : selectedEvent.severity ===
                        'medium'
                      ? 'text-[#ffb347]'
                      : 'text-[#ffe082]'
                  }
                >
                  {selectedEvent.severity.toUpperCase()}
                </span>
              </div>

              <div className="intel-row">
                <span>LATITUDE</span>

                <span>
                  {selectedEvent.latitude.toFixed(
                    2
                  )}
                </span>
              </div>

              <div className="intel-row">
                <span>LONGITUDE</span>

                <span>
                  {selectedEvent.longitude.toFixed(
                    2
                  )}
                </span>
              </div>

              <div className="intel-row">
                <span>LAST UPDATE</span>

                <span>
                  {new Date(
                    selectedEvent.event_time
                  ).toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TIME */}
      <div className="absolute bottom-4 right-5 text-xs text-white/30 z-20 tracking-[0.25em]">
        LAST SYNC •{' '}
        {lastUpdate.toLocaleTimeString()}
      </div>
    </main>
  );
}