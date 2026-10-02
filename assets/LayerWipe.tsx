import {Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {revealProgress} from './easing';

type LayerWipeProps = {
  src: string;
  startFrame: number;
  durationFrames: number;
  opacity?: number;
  zIndex: number;
  treatment?: 'bw' | 'detail' | 'color';
};

const treatmentFilter = {
  bw: 'grayscale(1) contrast(1.72) brightness(1.12)',
  detail: 'grayscale(1) contrast(1.28) brightness(1.055)',
  color: 'brightness(1.035) contrast(1.04)',
} as const;

export const LayerWipe: React.FC<LayerWipeProps> = ({
  src,
  startFrame,
  durationFrames,
  opacity = 1,
  zIndex,
  treatment = 'color',
}) => {
  const frame = useCurrentFrame();
  const {width} = useVideoConfig();
  const progress = revealProgress(frame, startFrame, durationFrames);
  // Product rule: every drawing plate is revealed left-to-right. Keeping one
  // mask direction across bw/detail/color prevents the composition from
  // appearing to jump when a new plate takes over.
  const clipPath = `inset(0 ${100 - progress * 100}% 0 0)`;

  // 16:9 storybook layout: artwork occupies the right panel, leaving a left
  // column for the caption. Portrait keeps the original stacked arrangement.
  const wide = width >= 1600;

  return (
    <div
      style={{
        position: 'absolute',
        zIndex,
        left: wide ? 700 : 74,
        right: wide ? 84 : 74,
        top: wide ? 70 : 382,
        bottom: wide ? 70 : 42,
        clipPath,
        opacity,
      }}
    >
      <Img
        src={staticFile(src)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          objectPosition: 'center center',
          filter: treatmentFilter[treatment],
        }}
      />
    </div>
  );
};
