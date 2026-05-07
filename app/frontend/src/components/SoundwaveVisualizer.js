import React, { useEffect, useRef, useState } from 'react';
import './SoundwaveVisualizer.css';

/**
 * SoundwaveVisualizer
 * Animated moving soundwave that can sync with audio input or display decoratively
 * Matches the dark glossy theme of the Open Camera component
 */
const SoundwaveVisualizer = ({
  isActive = false,
  audioContext = null,
  analyser = null,
  width = 300,
  height = 120,
  barCount = 64,
  color = 'rgba(100, 225, 255, 0.8)', // Cyan to match eyebrow
  secondaryColor = 'rgba(255, 255, 255, 0.4)', // White overlay
  animationSpeed = 0.05,
  className = '',
}) => {
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const dataArrayRef = useRef(null);
  const phaseRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas resolution
    canvas.width = width;
    canvas.height = height;

    // Initialize data array for frequency data if analyser exists
    if (analyser && !dataArrayRef.current) {
      const bufferLength = analyser.frequencyBinCount;
      dataArrayRef.current = new Uint8Array(bufferLength);
    }

    const animate = () => {
      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      const centerY = height / 2;
      const barWidth = width / barCount;
      const maxHeight = height * 0.4;

      // Get audio data if available
      let audioData = null;
      if (analyser && isActive) {
        analyser.getByteFrequencyData(dataArrayRef.current);
        audioData = dataArrayRef.current;
      }

      // Draw waveform bars
      for (let i = 0; i < barCount; i++) {
        const x = (i / barCount) * width;
        
        // Get frequency value if available, otherwise use animated sine wave
        let heightMultiplier = 0.3;
        if (audioData && isActive) {
          // Map frequency data to bar height
          const dataIndex = Math.floor((i / barCount) * audioData.length);
          heightMultiplier = (audioData[dataIndex] / 255) * 0.9 + 0.1;
        } else {
          // Decorative sine wave animation
          const wavePhase = (i / barCount) * Math.PI * 2 + phaseRef.current;
          heightMultiplier = (Math.sin(wavePhase) + 1) / 2 * 0.7 + 0.2;
        }

        const barHeight = maxHeight * heightMultiplier;
        const barY = centerY - barHeight / 2;

        // Main bar with gradient
        const gradient = ctx.createLinearGradient(x, barY, x, barY + barHeight);
        gradient.addColorStop(0, 'rgba(100, 225, 255, 0.3)');
        gradient.addColorStop(0.5, color);
        gradient.addColorStop(1, 'rgba(100, 225, 255, 0.3)');

        ctx.fillStyle = gradient;
        ctx.fillRect(x, barY, barWidth * 0.7, barHeight);

        // Add subtle glow/reflection
        ctx.fillStyle = secondaryColor;
        ctx.fillRect(x + barWidth * 0.7, barY, barWidth * 0.15, barHeight);
      }

      // Draw center line
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, centerY);
      ctx.lineTo(width, centerY);
      ctx.stroke();

      // Update phase for decorative animation
      if (!isActive) {
        phaseRef.current += animationSpeed;
      }

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isActive, analyser, width, height, barCount, color, secondaryColor, animationSpeed]);

  return (
    <canvas
      ref={canvasRef}
      className={`soundwave-visualizer ${isActive ? 'active' : 'inactive'} ${className}`}
      aria-hidden="true"
    />
  );
};

export default SoundwaveVisualizer;
