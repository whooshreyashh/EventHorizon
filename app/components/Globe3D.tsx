'use client';

import Globe from 'react-globe.gl';
import { useEffect, useRef, useState } from 'react';

interface Event {
  id: number;
  latitude: number;
  longitude: number;
  severity: string;
  title: string;
  magnitude: number;
  event_time: string;
  event_type?: string;
  source?: string;
}

interface Globe3DProps {
  events: Event[];
  onEventClick: (event: Event) => void;
  autoRotate: boolean;
  satView: boolean;
  trackedEvent: Event | null;
}

export default function Globe3D({
  events,
  onEventClick,
  autoRotate,
  satView,
  trackedEvent,
}: Globe3DProps) {
  const globeRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 1200, height: 900 });

  useEffect(() => {
    const updateSize = () => {
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    };
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  // AUTO ROTATION
  useEffect(() => {
    if (!globeRef.current) return;
    globeRef.current.controls().autoRotate = autoRotate;
    globeRef.current.controls().autoRotateSpeed = 0.28;
  }, [autoRotate]);

  // INITIAL CAMERA
  useEffect(() => {
    if (!globeRef.current) return;
    globeRef.current.pointOfView({ lat: 18, lng: 10, altitude: 2.05 }, 0);
  }, []);

  // TRACK EVENT
  useEffect(() => {
    if (!trackedEvent || !globeRef.current) return;
    globeRef.current.pointOfView(
      { lat: trackedEvent.latitude, lng: trackedEvent.longitude, altitude: 1.18 },
      1800
    );
  }, [trackedEvent]);

  // Get color based on event type and severity
  const getEventColor = (event: Event): string => {
    const eventType = event.event_type || 'earthquake';
    
    switch (eventType) {
      case 'wildfire':
        return '#ff4400';  // Bright red-orange
      case 'volcano':
        return '#ff6600';  // Magma orange
      case 'storm':
      case 'cyclone':
        return '#44aaff';  // Storm blue
      case 'flood':
        return '#3399ff';  // Water blue
      case 'earthquake':
      default:
        if (event.severity === 'high') return '#ff5533';
        if (event.severity === 'medium') return '#ffb347';
        return '#ffe082';
    }
  };

  // Get size based on severity
  const getEventSize = (event: Event): number => {
    if (event.severity === 'high') return 90;
    if (event.severity === 'medium') return 65;
    return 42;
  };

  // Get blur based on severity
  const getEventBlur = (event: Event): number => {
    if (event.severity === 'high') return 60;
    if (event.severity === 'medium') return 42;
    return 28;
  };

  // SURFACE GLOW HOTSPOTS
  const glowData = events.map((event) => ({
    ...event,
    size: getEventSize(event),
    blur: getEventBlur(event),
    color: getEventColor(event),
  }));

  return (
    <div
      style={{
        width: '100%',
        height: '100vh',
        overflow: 'hidden',
        background: `radial-gradient(circle at center, #020816 0%, #01040d 48%, #000308 75%, #000000 100%)`,
      }}
    >
      <Globe
        ref={globeRef}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="rgba(0,0,0,0)"
        globeImageUrl={
          satView
            ? '//unpkg.com/three-globe/example/img/earth-night.jpg'
            : '//unpkg.com/three-globe/example/img/earth-blue-marble.jpg'
        }
        bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
        atmosphereColor="#2563eb"
        atmosphereAltitude={0.12}
        htmlElementsData={glowData}
        htmlLat={(d: any) => d.latitude}
        htmlLng={(d: any) => d.longitude}
        htmlElement={(d: any) => {
          const el = document.createElement('div');
          el.style.width = '1px';
          el.style.height = '1px';
          el.style.pointerEvents = 'auto';
          el.style.cursor = 'pointer';

          el.innerHTML = `
            <div
              class="surface-hotspot"
              style="
                --glow-color:${d.color};
                --glow-size:${d.size}px;
                --glow-blur:${d.blur}px;
              "
            >
              <div class="surface-core"></div>
              <div class="surface-glow"></div>
            </div>
          `;

          el.onclick = () => {
            onEventClick(d);
            globeRef.current.pointOfView(
              { lat: d.latitude, lng: d.longitude, altitude: 1.18 },
              1600
            );
          };

          return el;
        }}
      />
    </div>
  );
}