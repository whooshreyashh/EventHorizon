'use client';

import { useEffect, useState, useRef } from 'react';
import dynamic from 'next/dynamic';
import { createClient } from '@supabase/supabase-js';

const Globe3D = dynamic(() => import('@/app/components/Globe3D'), { ssr: false });

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
  event_type?: string;
  source?: string;
}

function CustomDropdown({ value, onChange, options }: { 
  value: string; 
  onChange: (val: string) => void; 
  options: string[] 
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const displayValue = value === 'all' ? 'ALL' : value.toUpperCase();

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="bg-[rgba(8,15,28,0.9)] border border-[rgba(59,130,246,0.3)] rounded-full pl-4 pr-10 py-1.5 text-xs text-white/80 cursor-pointer hover:bg-[rgba(59,130,246,0.15)] hover:border-[rgba(59,130,246,0.5)] transition-all duration-200 relative"
      >
        {displayValue}
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-white/60 text-xs">▼</span>
      </button>
      
      {isOpen && (
        <div className="absolute right-0 mt-2 w-32 bg-[rgba(8,15,28,0.95)] backdrop-blur-md border border-[rgba(59,130,246,0.3)] rounded-xl overflow-hidden z-50 shadow-xl">
          {options.map((opt) => {
            const optDisplay = opt === 'all' ? 'ALL' : opt.toUpperCase();
            return (
              <button
                key={opt}
                onClick={() => {
                  onChange(opt);
                  setIsOpen(false);
                }}
                className={`w-full text-left px-4 py-2 text-xs transition-colors ${
                  value === opt 
                    ? 'bg-[rgba(59,130,246,0.3)] text-white' 
                    : 'text-white/70 hover:bg-[rgba(59,130,246,0.15)] hover:text-white'
                }`}
              >
                {optDisplay}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [trackedEvent, setTrackedEvent] = useState<Event | null>(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [autoRotate, setAutoRotate] = useState(true);
  const [satView, setSatView] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [mounted, setMounted] = useState(false);
  
  const [globeFilter, setGlobeFilter] = useState('all');
  const [feedFilter, setFeedFilter] = useState('all');

  const eventTypes = ['all', 'earthquake', 'wildfire', 'volcano', 'storm', 'flood', 'tsunami'];

  const fetchEvents = async () => {
    setRefreshing(true);
    const { data, error } = await supabase
      .from('events')
      .select('*')
      .order('event_time', { ascending: false })
      .limit(200);

    if (!error && data) {
      setEvents(data);
      setLastUpdate(new Date());
    }
    setTimeout(() => setRefreshing(false), 700);
  };

  useEffect(() => {
    fetchEvents();
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!autoRotate) return;
    const interval = setInterval(fetchEvents, 30000);
    return () => clearInterval(interval);
  }, [autoRotate]);

  const cycleGlobeFilter = () => {
    const currentIndex = eventTypes.indexOf(globeFilter);
    const nextIndex = (currentIndex + 1) % eventTypes.length;
    setGlobeFilter(eventTypes[nextIndex]);
  };

  const handleFeedItemClick = (event: Event) => {
    setSelectedEvent(event);
    setTrackedEvent(event);
  };

  const highCount = events.filter(e => e.severity === 'high').length;
  const mediumCount = events.filter(e => e.severity === 'medium').length;
  const lowCount = events.filter(e => e.severity === 'low').length;

  const filteredFeedEvents = feedFilter === 'all' 
    ? events 
    : events.filter(e => (e.event_type || 'earthquake') === feedFilter);

  const getEventColor = (event: Event) => {
    const type = event.event_type || 'earthquake';
    switch (type) {
      case 'earthquake': return '#ff5533';
      case 'wildfire': return '#ff4400';
      case 'volcano': return '#ff6600';
      case 'storm': return '#44aaff';
      case 'flood': return '#3399ff';
      case 'tsunami': return '#00e5ff';
      default: return '#ffe082';
    }
  };

  return (
    <main className="relative w-screen h-screen overflow-hidden bg-[#02050A] text-white">
      <Globe3D
        events={events}
        onEventClick={setSelectedEvent}
        autoRotate={autoRotate}
        satView={satView}
        filterType={globeFilter}
        trackedEvent={trackedEvent}
      />

      <div className="scanlines pointer-events-none" />
      <div className="vignette pointer-events-none" />
      
      {/* HUD Frame - visible on both desktop and mobile */}
      <div className="hud-frame pointer-events-none">
        <div className="corner top-left" />
        <div className="corner top-right" />
        <div className="corner bottom-left" />
        <div className="corner bottom-right" />
      </div>

      {/* ===== DESKTOP LAYOUT (md and above) ===== */}
      
      {/* TOP LEFT - Desktop */}
      <div className="absolute top-7 left-7 z-20 hidden md:block">
        <div className="hud-panel w-[350px]">
          <div className="flex items-center justify-between">
            <div>
              <p className="hud-label">GLOBAL SYSTEM</p>
              <h1 className="hud-title">EVENTHORIZON</h1>
            </div>
            <div className="status-ping" />
          </div>
          <div className="mt-7 space-y-3 text-sm text-white/70">
            <div className="flex justify-between"><span>SATELLITE LINK</span><span className="text-[#4ADE80]">ACTIVE</span></div>
            <div className="flex justify-between"><span>THREAT MONITOR</span><span className="text-[#4ADE80]">ONLINE</span></div>
            <div className="flex justify-between"><span>LIVE FEED</span><span className="text-[#4ADE80]">STABLE</span></div>
          </div>
        </div>
      </div>

      {/* TOP RIGHT - Desktop */}
      <div className="absolute top-7 right-7 z-20 hidden md:block">
        <div className="hud-panel w-[320px]">
          <div className="flex items-center justify-between">
            <div>
              <p className="hud-label">THREAT ANALYTICS</p>
              <h2 className="text-4xl font-bold mt-2">{events.length}</h2>
            </div>
            <div className="threat-ring"><span>{Math.min(100, highCount * 10 + mediumCount * 3)}%</span></div>
          </div>
          <div className="mt-6"><div className="threat-bar"><div className="threat-fill" style={{ width: `${Math.min(100, highCount * 10 + mediumCount * 3)}%` }} /></div></div>
          <div className="mt-6 flex gap-8">
            <div><p className="text-[#ff5533] text-sm font-semibold">HIGH</p><p className="text-3xl font-bold">{highCount}</p></div>
            <div><p className="text-[#ffb347] text-sm font-semibold">MED</p><p className="text-3xl font-bold">{mediumCount}</p></div>
            <div><p className="text-[#ffe082] text-sm font-semibold">LOW</p><p className="text-3xl font-bold">{lowCount}</p></div>
          </div>
        </div>
      </div>

      {/* LIVE FEED - Desktop */}
      <div className="absolute left-7 bottom-7 z-20 hidden md:block">
        <div className="hud-panel w-[390px] h-[360px] flex flex-col">
          <div className="flex items-center justify-between mb-5">
            <div>
              <p className="hud-label">LIVE EVENT STREAM</p>
              <h2 className="text-2xl font-semibold mt-2">
                {feedFilter === 'all' ? 'ALL SIGNALS' : feedFilter.toUpperCase()}
              </h2>
            </div>
            <CustomDropdown value={feedFilter} onChange={setFeedFilter} options={eventTypes} />
          </div>
          <div className="flex-1 overflow-y-auto overflow-x-hidden pr-2 custom-scroll">
            <div className="space-y-3">
              {filteredFeedEvents.map((event) => (
                <button
                  key={event.id}
                  onClick={() => handleFeedItemClick(event)}
                  className="feed-item w-full text-left group"
                >
                  <div className="feed-indicator shrink-0 mt-1" style={{ backgroundColor: getEventColor(event), boxShadow: `0 0 12px ${getEventColor(event)}` }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white/90 break-words leading-relaxed">{event.title}</p>
                    <div className="flex justify-between mt-2 text-xs text-white/40">
                      <span className="uppercase truncate">{(event.event_type || 'EARTHQUAKE')}</span>
                      <span className="shrink-0 ml-2">{new Date(event.event_time).toLocaleTimeString()}</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* DOCK - Desktop */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 hidden md:block">
        <div className="dock-panel">
          <button onClick={() => setAutoRotate(!autoRotate)} className={`dock-btn ${autoRotate ? 'active-dock' : ''}`}>
            {autoRotate ? 'AUTO' : 'MANUAL'}
          </button>
          <button onClick={fetchEvents} className={`dock-btn ${refreshing ? 'active-dock' : ''}`}>
            {refreshing ? 'SYNCING...' : 'REFRESH'}
          </button>
          <button onClick={() => setSatView(!satView)} className={`dock-btn ${satView ? 'active-dock' : ''}`}>
            {satView ? 'SAT VIEW' : 'DAY VIEW'}
          </button>
          <button onClick={cycleGlobeFilter} className={`dock-btn ${globeFilter !== 'all' ? 'active-dock' : ''}`}>
            🌍 {globeFilter === 'all' ? 'ALL' : globeFilter.toUpperCase()}
          </button>
        </div>
      </div>

      {/* EVENT CARD - Desktop */}
      {selectedEvent && (
        <div className="absolute right-7 bottom-7 z-20 hidden md:block">
          <div className="hud-panel w-[360px]">
            <div className="flex items-start justify-between">
              <div>
                <p className="hud-label">EVENT INTELLIGENCE</p>
                <h2 className="text-xl font-semibold mt-2 leading-tight">{selectedEvent.title}</h2>
              </div>
              <button onClick={() => setSelectedEvent(null)} className="text-white/40 hover:text-white transition shrink-0 ml-4">✕</button>
            </div>
            <div className="mt-7 space-y-4">
              <div className="intel-row"><span>TYPE</span><span className="uppercase">{selectedEvent.event_type || 'EARTHQUAKE'}</span></div>
              {selectedEvent.magnitude && <div className="intel-row"><span>MAGNITUDE</span><span>{selectedEvent.magnitude}</span></div>}
              <div className="intel-row"><span>SEVERITY</span><span className={selectedEvent.severity === 'high' ? 'text-[#ff5533]' : selectedEvent.severity === 'medium' ? 'text-[#ffb347]' : 'text-[#ffe082]'}>{selectedEvent.severity.toUpperCase()}</span></div>
              <div className="intel-row"><span>COORDINATES</span><span>{selectedEvent.latitude.toFixed(2)}°, {selectedEvent.longitude.toFixed(2)}°</span></div>
              <div className="intel-row"><span>LAST UPDATE</span><span>{new Date(selectedEvent.event_time).toLocaleString()}</span></div>
            </div>
          </div>
        </div>
      )}

      {/* ===== MOBILE LAYOUT (below md screens) ===== */}
      
      {/* Mobile: Top Left - Compact Event Horizon */}
      <div className="absolute top-3 left-3 z-20 md:hidden">
        <div className="bg-black/40 backdrop-blur-md rounded-xl px-3 py-1.5 border border-white/10">
          <div className="flex items-center gap-2">
            <div className="status-ping w-1.5 h-1.5" />
            <p className="text-[8px] text-white/50 font-mono tracking-wider">GLOBAL SYSTEM</p>
          </div>
          <h1 className="text-sm font-bold tracking-wider mt-0.5 bg-gradient-to-r from-white to-blue-400 bg-clip-text text-transparent">EVENTHORIZON</h1>
        </div>
      </div>

      {/* Mobile: Top Right - Threat Analytics with High/Med/Low counts */}
      <div className="absolute top-3 right-3 z-20 md:hidden">
        <div className="bg-black/40 backdrop-blur-md rounded-xl px-3 py-1.5 border border-white/10">
          <p className="text-[8px] text-white/50 font-mono tracking-wider text-right">THREAT</p>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-lg font-bold text-white/90">{events.length}</span>
            <div className="flex gap-2">
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-[#ff5533]" />
                <span className="text-[10px] font-bold text-white/80">{highCount}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-[#ffb347]" />
                <span className="text-[10px] font-bold text-white/80">{mediumCount}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-[#ffe082]" />
                <span className="text-[10px] font-bold text-white/80">{lowCount}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile: Live Feed */}
      <div className="absolute left-3 right-3 bottom-16 z-20 md:hidden">
        <div className="bg-black/40 backdrop-blur-md rounded-xl border border-white/10 overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-white/10">
            <div className="flex items-center gap-2">
              <div className="live-dot w-1.5 h-1.5" />
              <span className="text-[9px] font-mono text-white/50 tracking-wider">LIVE FEED</span>
              <span className="text-[9px] text-white/30">•</span>
              <span className="text-[9px] text-white/70 font-medium">{feedFilter === 'all' ? 'ALL' : feedFilter.toUpperCase()}</span>
            </div>
            <CustomDropdown value={feedFilter} onChange={setFeedFilter} options={eventTypes} />
          </div>
          <div className="h-36 overflow-y-auto">
            {filteredFeedEvents.slice(0, 8).map((event) => (
              <button
                key={event.id}
                onClick={() => handleFeedItemClick(event)}
                className="w-full text-left px-3 py-2 border-b border-white/5 hover:bg-white/5 transition-colors"
              >
                <div className="flex gap-2">
                  <div className="w-1.5 h-1.5 rounded-full mt-1 shrink-0" style={{ backgroundColor: getEventColor(event) }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] text-white/80 leading-tight line-clamp-1">{event.title}</p>
                    <div className="flex justify-between mt-1">
                      <span className="text-[7px] text-white/30 uppercase">{(event.event_type || 'QUAKE')?.substring(0, 4)}</span>
                      <span className="text-[7px] text-white/30">{new Date(event.event_time).toLocaleTimeString()}</span>
                    </div>
                  </div>
                </div>
              </button>
            ))}
            {filteredFeedEvents.length === 0 && (
              <div className="text-center text-white/30 py-6 text-[10px]">No events</div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile: Dock - with full text labels, tighter spacing */}
<div className="absolute bottom-3 left-3 right-3 z-20 md:hidden">
  <div className="bg-black/40 backdrop-blur-md rounded-full border border-white/10 px-1 py-1 flex justify-center gap-0.5">
    <button 
      onClick={() => setAutoRotate(!autoRotate)} 
      className={`px-3 py-1.5 rounded-full text-[10px] font-mono transition-all flex-1 text-center ${autoRotate ? 'bg-blue-500/20 text-blue-400' : 'text-white/60'}`}
    >
      {autoRotate ? 'AUTO' : 'MANUAL'}
    </button>
    
    <button 
      onClick={fetchEvents} 
      className="px-3 py-1.5 rounded-full text-[10px] font-mono text-white/60 hover:text-white/80 transition-all flex-1 text-center"
    >
      {refreshing ? 'SYNC' : 'REFRESH'}
    </button>
    
    <button 
      onClick={() => setSatView(!satView)} 
      className={`px-3 py-1.5 rounded-full text-[10px] font-mono transition-all flex-1 text-center ${satView ? 'bg-blue-500/20 text-blue-400' : 'text-white/60'}`}
    >
      {satView ? 'SAT' : 'DAY'}
    </button>
    
    <button 
      onClick={cycleGlobeFilter} 
      className="px-3 py-1.5 rounded-full text-[10px] font-mono text-white/60 hover:text-white/80 transition-all flex-1 text-center"
    >
      {globeFilter === 'all' ? 'ALL' : globeFilter.toUpperCase().substring(0, 3)}
    </button>
  </div>
</div>

      {/* Mobile: Event Card */}
      {selectedEvent && (
        <div className="fixed bottom-20 left-3 right-3 z-30 md:hidden">
          <div className="bg-black/80 backdrop-blur-md rounded-xl border border-white/15 p-2.5">
            <div className="flex justify-between items-start mb-1.5">
              <h3 className="text-[10px] font-bold text-white/80 flex-1 leading-tight">{selectedEvent.title.length > 60 ? selectedEvent.title.substring(0, 60) + '...' : selectedEvent.title}</h3>
              <button onClick={() => setSelectedEvent(null)} className="text-white/40 text-sm ml-2">✕</button>
            </div>
            <div className="flex justify-between text-[9px]">
              <span className="text-white/40 uppercase">{selectedEvent.event_type || 'QUAKE'}</span>
              {selectedEvent.magnitude && <span className="text-white/60">M {selectedEvent.magnitude}</span>}
              <span className={selectedEvent.severity === 'high' ? 'text-[#ff5533]' : selectedEvent.severity === 'medium' ? 'text-[#ffb347]' : 'text-[#ffe082]'}>{selectedEvent.severity.toUpperCase()}</span>
            </div>
          </div>
        </div>
      )}

      {/* TIME - Both layouts */}
      {mounted && (
        <div className="absolute bottom-1 right-1 text-[6px] text-white/20 z-20 md:bottom-4 md:right-5 md:text-xs md:text-white/30">
          {lastUpdate.toLocaleTimeString()}
        </div>
      )}
    </main>
  );
}