import React from 'react';
import {AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';

export type VideoProps = {
  source?: string;
  title?: string;
  subtitle?: string;
  accent?: string;
  watermark?: string;
  fit?: 'contain' | 'cover';
};

export const VIDEO_WIDTH = 1080;
export const VIDEO_HEIGHT = 1920;
export const VIDEO_FPS = 30;
export const VIDEO_DURATION_IN_FRAMES = 30 * 30;

export const Video = ({
  source = 'input/source.mp4',
  title = 'VARIS',
  subtitle = 'Work with AI',
  accent = '#f2b544',
  watermark = '@varis.kr',
  fit = 'cover',
}: VideoProps) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const progress = interpolate(frame, [0, Math.min(18, durationInFrames - 1)], [0, 1], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#111'}}>
      <AbsoluteFill style={{overflow: 'hidden'}}>
        <OffthreadVideo
          src={staticFile(source)}
          muted
          style={{
            width: '100%',
            height: '100%',
            objectFit: fit,
            transform: 'scale(1.02)',
          }}
        />
        <AbsoluteFill
          style={{
            background: 'linear-gradient(180deg, rgba(0,0,0,.62) 0%, rgba(0,0,0,0) 30%, rgba(0,0,0,.72) 100%)',
          }}
        />
      </AbsoluteFill>

      <div style={{position: 'absolute', top: 82, left: 68, right: 68, opacity: progress}}>
        <div style={{display: 'inline-block', padding: '10px 18px', borderRadius: 999, backgroundColor: accent, color: '#111', fontSize: 28, fontWeight: 800, letterSpacing: 1}}>
          {subtitle}
        </div>
      </div>

      <div style={{position: 'absolute', left: 68, right: 68, bottom: 170, color: 'white', opacity: progress}}>
        <div style={{fontSize: 76, lineHeight: 1.05, fontWeight: 900, letterSpacing: -2, textShadow: '0 4px 20px rgba(0,0,0,.5)'}}>
          {title}
        </div>
        <div style={{marginTop: 24, width: 120, height: 8, borderRadius: 99, backgroundColor: accent}} />
      </div>

      <div style={{position: 'absolute', right: 68, bottom: 70, color: 'rgba(255,255,255,.85)', fontSize: 24, fontWeight: 700}}>
        {watermark}
      </div>
    </AbsoluteFill>
  );
};
