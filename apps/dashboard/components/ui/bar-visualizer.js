'use client';
import React, { useEffect, useRef } from 'react';
export function BarVisualizer({ isActive, height = 80, barCount = 12, barColor = 'hsl(192, 100%, 50%)', sensitivity = 1.5, }) {
    const canvasRef = useRef(null);
    const animationRef = useRef();
    const barsRef = useRef(Array(barCount).fill(0));
    const audioContextRef = useRef();
    const analyserRef = useRef();
    useEffect(() => {
        if (!isActive)
            return;
        const initAudio = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                audioContextRef.current = audioContext;
                const analyser = audioContext.createAnalyser();
                analyser.fftSize = 256;
                analyserRef.current = analyser;
                const source = audioContext.createMediaStreamSource(stream);
                source.connect(analyser);
                const animate = () => {
                    const dataArray = new Uint8Array(analyser.frequencyBinCount);
                    analyser.getByteFrequencyData(dataArray);
                    const step = Math.floor(dataArray.length / barCount);
                    for (let i = 0; i < barCount; i++) {
                        const value = dataArray[i * step] / 255;
                        barsRef.current[i] = Math.max(barsRef.current[i] * 0.8, value * sensitivity);
                    }
                    drawBars();
                    animationRef.current = requestAnimationFrame(animate);
                };
                animate();
            }
            catch (error) {
                console.error('Microphone access error:', error);
            }
        };
        initAudio();
        return () => {
            if (animationRef.current)
                cancelAnimationFrame(animationRef.current);
            if (audioContextRef.current)
                audioContextRef.current.close();
        };
    }, [isActive, barCount, sensitivity]);
    const drawBars = () => {
        const canvas = canvasRef.current;
        if (!canvas)
            return;
        const ctx = canvas.getContext('2d');
        if (!ctx)
            return;
        const width = canvas.clientWidth;
        const dpr = window.devicePixelRatio || 1;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        ctx.scale(dpr, dpr);
        ctx.fillStyle = barColor;
        const barWidth = (width / barCount) * 0.8;
        const barGap = (width / barCount) * 0.2;
        for (let i = 0; i < barCount; i++) {
            const value = barsRef.current[i] || 0;
            const barHeight = value * height;
            const x = i * (barWidth + barGap) + barGap / 2;
            const y = height - barHeight;
            ctx.fillRect(x, y, barWidth, barHeight);
        }
    };
    return <canvas ref={canvasRef} className="w-full" style={{ height: `${height}px`, display: 'block' }}/>;
}
