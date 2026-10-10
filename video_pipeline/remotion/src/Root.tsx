import React from 'react';
import {Composition} from 'remotion';
import {Video, VIDEO_DURATION_IN_FRAMES, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH, VideoProps} from './Video';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Vertical"
        component={Video}
        durationInFrames={VIDEO_DURATION_IN_FRAMES}
        fps={VIDEO_FPS}
        width={VIDEO_WIDTH}
        height={VIDEO_HEIGHT}
        defaultProps={{
          source: 'input/source.mp4',
          title: 'VARIS',
          subtitle: 'Work with AI',
          accent: '#f2b544',
          watermark: '@varis.kr',
          fit: 'cover',
        }}
      />
      <Composition
        id="Landscape"
        component={Video}
        durationInFrames={VIDEO_DURATION_IN_FRAMES}
        fps={VIDEO_FPS}
        width={1920}
        height={1080}
        defaultProps={{
          source: 'input/source.mp4',
          title: 'VARIS',
          subtitle: 'Work with AI',
          accent: '#f2b544',
          watermark: '@varis.kr',
          fit: 'contain',
        }}
      />
      <Composition
        id="Square"
        component={Video}
        durationInFrames={VIDEO_DURATION_IN_FRAMES}
        fps={VIDEO_FPS}
        width={1080}
        height={1080}
        defaultProps={{
          source: 'input/source.mp4',
          title: 'VARIS',
          subtitle: 'Work with AI',
          accent: '#f2b544',
          watermark: '@varis.kr',
          fit: 'cover',
        }}
      />
    </>
  );
};
