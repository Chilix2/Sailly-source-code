'use client';

import React, { createContext, useContext, useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, Settings } from 'lucide-react';

interface AudioPlayerContextType {
  isPlaying: boolean;
  duration: number;
  currentTime: number;
  playbackRate: number;
  play: () => void;
  pause: () => void;
  seek: (time: number) => void;
  setPlaybackRate: (rate: number) => void;
  audioRef: React.RefObject<HTMLAudioElement>;
}

const AudioPlayerContext = createContext<AudioPlayerContextType | undefined>(undefined);

export function AudioPlayerProvider({ children }: { children: React.ReactNode }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleLoadedMetadata = () => setDuration(audio.duration);
    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);

    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate', handleTimeUpdate);

    return () => {
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, []);

  return (
    <AudioPlayerContext.Provider
      value={{
        isPlaying,
        duration,
        currentTime,
        playbackRate,
        play: () => audioRef.current?.play(),
        pause: () => audioRef.current?.pause(),
        seek: (time) => {
          if (audioRef.current) audioRef.current.currentTime = time;
        },
        setPlaybackRate: (rate) => {
          setPlaybackRate(rate);
          if (audioRef.current) audioRef.current.playbackRate = rate;
        },
        audioRef,
      }}
    >
      {children}
    </AudioPlayerContext.Provider>
  );
}

export function useAudioPlayer() {
  const context = useContext(AudioPlayerContext);
  if (!context) throw new Error('useAudioPlayer must be used within AudioPlayerProvider');
  return context;
}

export function AudioPlayerButton() {
  const { isPlaying, play, pause } = useAudioPlayer();
  return (
    <button
      onClick={isPlaying ? pause : play}
      className="p-2 hover:bg-[#e8d8d2] rounded-md transition-colors"
    >
      {isPlaying ? <Pause size={20} /> : <Play size={20} />}
    </button>
  );
}

export function AudioPlayerProgress() {
  const { currentTime, duration, seek } = useAudioPlayer();
  return (
    <input
      type="range"
      min="0"
      max={duration}
      value={currentTime}
      onChange={(e) => seek(parseFloat(e.target.value))}
      className="flex-1 h-1 bg-brand-cream rounded-lg appearance-none cursor-pointer"
      style={{
        background: `linear-gradient(to right, hsl(192, 100%, 50%) 0%, hsl(192, 100%, 50%) ${(currentTime / duration) * 100}%, rgb(39 39 42) ${(currentTime / duration) * 100}%, rgb(39 39 42) 100%)`,
      }}
    />
  );
}

export function AudioPlayerTime() {
  const { currentTime } = useAudioPlayer();
  const minutes = Math.floor(currentTime / 60);
  const seconds = Math.floor(currentTime % 60);
  return <span className="text-sm text-text-dim">{minutes}:{seconds.toString().padStart(2, '0')}</span>;
}

export function AudioPlayerDuration() {
  const { duration } = useAudioPlayer();
  const minutes = Math.floor(duration / 60);
  const seconds = Math.floor(duration % 60);
  return <span className="text-sm text-text-dim">{minutes}:{seconds.toString().padStart(2, '0')}</span>;
}

export function AudioPlayerSpeed() {
  const { playbackRate, setPlaybackRate } = useAudioPlayer();
  const speeds = [0.5, 1, 1.5, 2];

  return (
    <div className="relative inline-block group">
      <button className="p-2 hover:bg-[#e8d8d2] rounded-md transition-colors flex items-center gap-1 text-sm">
        <Settings size={16} />
        {playbackRate}x
      </button>
      <div className="absolute hidden group-hover:block right-0 bg-white shadow-sm border border-brand-cream rounded-md shadow-lg z-10">
        {speeds.map((speed) => (
          <button
            key={speed}
            onClick={() => setPlaybackRate(speed)}
            className={`block w-full text-left px-4 py-2 text-sm hover:bg-[#e8d8d2] transition-colors ${
              playbackRate === speed ? 'bg-brand-cream text-brand-pink' : ''
            }`}
          >
            {speed}x
          </button>
        ))}
      </div>
    </div>
  );
}
