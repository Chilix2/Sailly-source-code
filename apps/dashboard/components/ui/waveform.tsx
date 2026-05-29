'use client';

import React, { useEffect, useRef } from 'react';

interface WaveformProps {
  data: number[];
  height?: number;
  barWidth?: number;
  barGap?: number;
  barColor?: string;
  onBarClick?: (index: number, value: number) => void;
}

export function Waveform({
  data,
  height = 100,
  barWidth = 4,
  barGap = 2,
  barColor = 'hsl(192, 100%, 50%)',
  onBarClick,
}: WaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data.length) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.clientWidth * window.devicePixelRatio;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width;
    canvas.height = height * dpr;

    ctx.scale(dpr, dpr);
    ctx.fillStyle = barColor;

    const barCount = Math.floor(width / (barWidth + barGap));
    const step = Math.ceil(data.length / barCount);

    for (let i = 0; i < barCount; i++) {
      const index = i * step;
      const value = Math.min(data[index] || 0, 1);
      const barHeight = value * height;
      const x = i * (barWidth + barGap);
      const y = height - barHeight;

      ctx.fillRect(x, y, barWidth, barHeight);
    }
  }, [data, height, barWidth, barGap, barColor]);

  const handleClick = (e: React.MouseEvent) => {
    if (!canvasRef.current || !onBarClick) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const index = Math.floor(x / (barWidth + barGap));
    const value = data[index] || 0;
    onBarClick(index, value);
  };

  return (
    <canvas
      ref={canvasRef}
      onClick={handleClick}
      className="w-full cursor-pointer"
      style={{ height: `${height}px`, display: 'block' }}
    />
  );
}

export function AudioScrubber({
  data,
  currentTime,
  duration,
  onSeek,
  height = 60,
  barWidth = 3,
  barGap = 1,
}: WaveformProps & {
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
}) {
  const handleClick = (_index: number, value: number) => {
    const time = (value / Math.max(...data, 1)) * duration;
    onSeek(time);
  };

  return (
    <div className="space-y-2">
      <Waveform
        data={data}
        height={height}
        barWidth={barWidth}
        barGap={barGap}
        onBarClick={handleClick}
      />
      <div className="flex justify-between text-xs text-text-muted">
        <span>{Math.floor(currentTime / 60)}:{Math.floor(currentTime % 60).toString().padStart(2, '0')}</span>
        <span>{Math.floor(duration / 60)}:{Math.floor(duration % 60).toString().padStart(2, '0')}</span>
      </div>
    </div>
  );
}
